"use client";

import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

const COLORS: Record<string, string> = { sgd: "#5B6B60", momentum: "#2E6C8E", adam: "#C9A227" };
const LABELS: Record<string, string> = {
  sgd: "plain SGD",
  momentum: "SGD + momentum",
  adam: "Adam",
};

/** Three REAL training runs of the same net race downhill — the curves draw in together. */
export default function OptimizerRaceStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const opts = ((lesson.trace.series as { optimizers?: Record<string, number[]> } | null)
    ?.optimizers ?? {}) as Record<string, number[]>;
  const names = Object.keys(opts).filter((n) => (opts[n]?.length ?? 0) >= 2);
  const maxLen = Math.max(1, ...names.map((n) => opts[n].length));
  const k = useSubstep(clock, entryIdx, maxLen);
  const upto = reducedMotion ? maxLen : k;
  if (names.length < 2)
    return <p className="text-xs text-muted">No optimizer comparison for this fit.</p>;

  const all = names.flatMap((n) => opts[n]);
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const X = (i: number, len: number) => 34 + (i / Math.max(1, len - 1)) * 250;
  const Y = (v: number) => 12 + (hi > lo ? ((v - lo) / (hi - lo)) * 108 : 54);

  return (
    <div>
      <svg viewBox="0 0 300 140" width="100%" style={{ maxHeight: 240 }}
           role="img" aria-label="three optimizers' real loss curves">
        <line x1={34} y1={122} x2={288} y2={122} stroke="#E4EBE1" />
        <line x1={34} y1={10} x2={34} y2={122} stroke="#E4EBE1" />
        <text x={30} y={16} textAnchor="end" fontSize={8} fill="#5B6B60">{hi}</text>
        <text x={30} y={122} textAnchor="end" fontSize={8} fill="#5B6B60">{lo}</text>
        <text x={160} y={136} textAnchor="middle" fontSize={9} fill="#5B6B60">epochs →</text>
        {names.map((n) => {
          const curve = opts[n].slice(0, Math.max(2, Math.min(upto, opts[n].length)));
          const pts = curve.map((v, i) => `${X(i, opts[n].length)},${Y(v)}`).join(" ");
          const last = curve[curve.length - 1];
          return (
            <g key={n}>
              <polyline points={pts} fill="none" stroke={COLORS[n] ?? "#1E2A22"} strokeWidth={2} />
              <circle cx={X(curve.length - 1, opts[n].length)} cy={Y(last)} r={3.5}
                      fill={COLORS[n] ?? "#1E2A22"} />
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex flex-wrap gap-3">
        {names.map((n) => (
          <span key={n} className="flex items-center gap-1.5 text-[11px] text-ink">
            <span className="h-2 w-4 rounded" style={{ background: COLORS[n] }} />
            {LABELS[n] ?? n}
            <span className="font-mono text-[10px] text-muted">
              final {opts[n][opts[n].length - 1]}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
