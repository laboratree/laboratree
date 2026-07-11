"use client";

import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

type LstmStep = { t: number; feature: string; x: number; i: number; f: number; o: number; c: number; h: number };

/** A REAL trained LSTM cell replayed one timestep at a time: the cell-state conveyor on top,
 *  the three gate dials (forget / input / output) live below. */
export default function LstmGatesStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const lstm = (lesson.trace.series as { lstm?: { steps: LstmStep[] } } | null)?.lstm;
  const steps = lstm?.steps ?? [];
  const k = useSubstep(clock, entryIdx, Math.max(1, steps.length));
  const t = reducedMotion ? steps.length : k;
  if (!steps.length) return <p className="text-xs text-muted">No LSTM replay for this data.</p>;

  const cur = steps[Math.max(0, Math.min(steps.length, t) - 1)];
  const cSpan = Math.max(0.2, ...steps.map((s) => Math.abs(s.c)));

  return (
    <div className="space-y-2">
      {/* the conveyor: cell state c_t flowing left → right */}
      <div className="rounded-lg border border-line bg-white p-2">
        <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted">
          the cell state (memory conveyor)
        </p>
        <div className="flex items-end gap-1">
          {steps.map((s, i) => (
            <div key={s.t} className="flex-1 text-center">
              <div className="flex h-14 items-end justify-center">
                <div
                  className={`w-4 rounded-t transition-all duration-500 ${
                    s.c >= 0 ? "bg-leaf" : "bg-red-400"
                  }`}
                  style={{ height: i < t ? `${(Math.abs(s.c) / cSpan) * 100}%` : 0, minHeight: i < t ? 3 : 0 }}
                  title={`c = ${s.c}`}
                />
              </div>
              <p className={`font-mono text-[9px] ${i < t ? "text-ink" : "text-line"}`}>
                {i < t ? s.c : "·"}
              </p>
              <p className={`truncate text-[8px] ${i + 1 === t ? "text-[#8a6d1a]" : "text-muted"}`}>
                {s.feature}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* the gates at the current step */}
      <div className="rounded-lg border border-[#C9A227]/50 bg-[#FFFDF5] p-2.5">
        <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-[#8a6d1a]">
          step {Math.min(t, steps.length)} of {steps.length} — reading {cur.feature} (x = {cur.x})
        </p>
        <div className="grid grid-cols-3 gap-2">
          <Gate label="forget" hint="keep how much old memory?" value={cur.f} />
          <Gate label="input" hint="write how much new info?" value={cur.i} />
          <Gate label="output" hint="reveal how much memory?" value={cur.o} />
        </div>
        <p className="mt-2 font-mono text-[11px] text-ink">
          c = {cur.f}·c_prev + {cur.i}·(new) → <b>{cur.c}</b> · h = {cur.o}·tanh(c) → <b>{cur.h}</b>
        </p>
      </div>
    </div>
  );
}

function Gate({ label, hint, value }: { label: string; hint: string; value: number }) {
  return (
    <div className="rounded border border-line bg-white px-2 py-1.5" title={hint}>
      <p className="text-[9px] uppercase tracking-wide text-muted">{label} gate</p>
      <div className="mt-1 h-2 w-full rounded bg-bg">
        <div
          className="h-2 rounded bg-[#C9A227] transition-all duration-400"
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
      <p className="mt-0.5 font-mono text-[11px] font-semibold text-forest">{value}</p>
    </div>
  );
}
