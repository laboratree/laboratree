"use client";

import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

/** A held-out row walks every tree: base → +η·leaf₁ → +η·leaf₂ → … → score → probability. */
export default function BoostingAssemblyStage({ lesson, step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const ref = step.anim?.ref ?? {};
  const rowIdx = typeof ref.row === "number" ? ref.row : 0;
  const row = lesson.trace.test_rows?.[rowIdx];
  const contribs = row?.rounds ?? [];
  const base = lesson.trace.baseline ?? 0;
  const cls = lesson.trace.task === "classification";
  const total = contribs.length + (cls ? 2 : 1); // base+trees, then score, then sigmoid (cls)
  const shown = useSubstep(clock, entryIdx, Math.max(1, total + 1));
  const k = reducedMotion ? total + 1 : shown;
  if (!row || !contribs.length)
    return <p className="text-xs text-muted">No held-out row to assemble.</p>;

  const running = (upto: number) =>
    base + contribs.slice(0, upto).reduce((s, c) => s + c.value, 0);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-1.5">
        <Card show={k >= 1} label="base" value={fmt(base)} tone="muted" />
        {contribs.map((c, i) => (
          <span key={i} className="flex items-center gap-1.5">
            <span className={`text-muted transition-opacity ${k >= i + 2 ? "opacity-100" : "opacity-0"}`}>+</span>
            <Card
              show={k >= i + 2}
              label={`η·tree ${i + 1}`}
              value={fmt(c.value)}
              tone={c.value >= 0 ? "leaf" : "red"}
            />
          </span>
        ))}
        <span className={`text-muted transition-opacity ${k >= contribs.length + 2 ? "opacity-100" : "opacity-0"}`}>=</span>
        <Card
          show={k >= contribs.length + 2}
          label="raw score F"
          value={fmt(row.boost_score ?? running(contribs.length))}
          tone="gold"
        />
      </div>

      {cls && k >= total + 1 && (
        <div className="flex items-center gap-2 rounded-lg border border-[#C9A227]/50 bg-[#FFFDF5] px-3 py-2">
          <span className="font-mono text-[12px] text-ink">
            sigmoid({fmt(row.boost_score ?? 0)}) = <b>{fmt(row.boost_prob ?? 0)}</b>
          </span>
          <span className="text-[11px] text-muted">→ predicts</span>
          <span className="rounded-full bg-forest px-2 py-0.5 text-[11px] font-medium text-white">
            {String(row.boost_pred ?? row.predicted)}
          </span>
          <span className="text-[11px] text-muted">actual:</span>
          <span className={`text-[11px] font-semibold ${row.correct ? "text-green-700" : "text-red-600"}`}>
            {String(row.actual)} {row.correct ? "✓" : "✗"}
          </span>
        </div>
      )}
      {!cls && k >= total + 1 && (
        <div className="rounded-lg border border-[#C9A227]/50 bg-[#FFFDF5] px-3 py-2 text-[12px] text-ink">
          prediction <b>{fmt(row.boost_score ?? 0)}</b> vs actual <b>{String(row.actual)}</b>{" "}
          <span className="text-muted">(error {String(row.error ?? "—")})</span>
        </div>
      )}
      <p className="text-[10px] text-muted">
        The same walk happens for every row in the Testing chapter — click any row there to
        replay its assembly.
      </p>
    </div>
  );
}

const TONES: Record<string, string> = {
  muted: "border-line bg-white text-ink",
  leaf: "border-leaf/60 bg-[#F6FAF2] text-forest",
  red: "border-red-300 bg-red-50 text-red-700",
  gold: "border-[#C9A227] bg-[#FFFDF5] text-[#8a6d1a]",
};

function Card({ show, label, value, tone }: { show: boolean; label: string; value: string; tone: string }) {
  return (
    <span
      className={`rounded-lg border px-2 py-1 ${TONES[tone]}`}
      style={{ opacity: show ? 1 : 0, transform: show ? "none" : "translateY(4px)", transition: "opacity .4s, transform .4s" }}
    >
      <span className="block text-[9px] uppercase tracking-wide opacity-70">{label}</span>
      <span className="font-mono text-[12px] font-semibold">{value}</span>
    </span>
  );
}

function fmt(v: number): string {
  return (v >= 0 ? "" : "") + String(Math.round(v * 1000) / 1000);
}
