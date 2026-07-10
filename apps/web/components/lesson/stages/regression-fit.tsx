"use client";

import type { RegressionFit } from "@/lib/api";
import { useSmoothProgress } from "../clock";
import type { LessonStageProps } from "./types";

/**
 * The iconic least-squares animation on the real data:
 *  phase 1 (0–0.45): the line sweeps from flat (just-predict-the-mean) into the best fit
 *  phase 2 (0.45–1): a residual segment links every ACTUAL point to its PREDICTED point on
 *                    the line, and the squared-error total shrinks to its minimum.
 */
export default function RegressionFitStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const f = (lesson.trace.series as { regression_fit?: RegressionFit } | null)?.regression_fit;
  const progress = useSmoothProgress(clock, entryIdx);
  const p = reducedMotion ? 1 : progress;
  if (!f || !f.points.length)
    return <p className="text-xs text-muted">No fit geometry for this data.</p>;

  const W = 300, H = 190, pad = 26;
  const xs = f.points.map((q) => q.x);
  const ys = f.points.map((q) => q.y);
  const xlo = Math.min(...xs), xhi = Math.max(...xs);
  const ylo = Math.min(...ys, f.mean_y), yhi = Math.max(...ys, f.mean_y);
  const X = (x: number) => pad + ((x - xlo) / (xhi - xlo || 1)) * (W - 2 * pad);
  const Y = (y: number) => H - pad - ((y - ylo) / (yhi - ylo || 1)) * (H - 2 * pad);

  // phase 1: interpolate the line from flat (slope 0 at mean_y) → the fitted line
  const sweep = Math.min(1, p / 0.45);
  const slope = f.slope * sweep;
  const intercept = f.mean_y * (1 - sweep) + f.intercept * sweep;
  const lineAt = (x: number) => intercept + slope * x;
  // phase 2: residuals stretch in and the SSE meter falls from the mean-baseline to the fitted
  const resid = Math.max(0, Math.min(1, (p - 0.45) / 0.55));
  const sse = f.sse_mean * (1 - resid) + f.sse_line * resid;
  const settled = p > 0.98;

  return (
    <div className="flex flex-wrap items-start gap-3">
      <svg viewBox={`0 0 ${W} ${H}`} width={W} style={{ maxHeight: 260 }}
           role="img" aria-label="fitting the least-squares line with residuals">
        {/* axes */}
        <line x1={pad} y1={H - pad} x2={W - pad} y2={H - pad} stroke="#E4EBE1" />
        <line x1={pad} y1={pad} x2={pad} y2={H - pad} stroke="#E4EBE1" />
        <text x={W / 2} y={H - 4} textAnchor="middle" fontSize={9} fill="#5B6B60">{f.feature}</text>
        <text x={8} y={pad - 8} fontSize={9} fill="#5B6B60">{f.target}</text>

        {/* residual segments: actual point → its predicted point ON the line */}
        {f.points.map((q, i) => {
          const yhat = lineAt(q.x);
          const shown = resid > i / f.points.length; // stretch in one by one
          return (
            <line key={`r${i}`} x1={X(q.x)} y1={Y(q.y)} x2={X(q.x)} y2={Y(yhat)}
                  stroke="#C0392B" strokeWidth={1.2}
                  opacity={reducedMotion || shown ? 0.55 : 0} style={{ transition: "opacity .2s" }} />
          );
        })}

        {/* the line */}
        <line x1={X(xlo)} y1={Y(lineAt(xlo))} x2={X(xhi)} y2={Y(lineAt(xhi))}
              stroke="#14342A" strokeWidth={2} />

        {/* the data points and their predicted point on the line */}
        {f.points.map((q, i) => (
          <g key={i}>
            <circle cx={X(q.x)} cy={Y(q.y)} r={3} fill="#6DB33F" />
            {resid > 0.05 && (
              <circle cx={X(q.x)} cy={Y(lineAt(q.x))} r={1.6} fill="#14342A" opacity={0.7} />
            )}
          </g>
        ))}
      </svg>

      <div className="min-w-[150px] flex-1">
        <p className="text-[10px] font-medium uppercase tracking-wide text-[#8a6d1a]">
          {sweep < 1 ? "sweeping the line into the cloud…"
            : resid < 1 ? "measuring every residual…" : "the best fit"}
        </p>
        <p className="mt-1 font-mono text-[11px] text-ink">
          line: {f.target} ≈ {f.intercept} + {f.slope}·{f.feature}
        </p>
        {/* SSE meter: total squared residual, shrinking to the minimum */}
        <p className="mt-2 text-[10px] text-muted">total squared error (Σ residual²)</p>
        <div className="mt-0.5 h-3 w-full rounded bg-bg">
          <div className="h-3 rounded bg-[#C0392B] transition-[width] duration-200"
               style={{ width: `${Math.round((sse / (f.sse_mean || 1)) * 100)}%` }} />
        </div>
        <p className="mt-0.5 font-mono text-[11px] text-forest">SSE = {Math.round(sse)}</p>
        {settled && (
          <p className="mt-2 text-[10px] text-muted">
            the flat &quot;just predict the mean&quot; line scored {Math.round(f.sse_mean)}; the best
            line cut it to <b className="text-forest">{Math.round(f.sse_line)}</b> — that drop is R²
            = <b className="text-forest">{f.r2}</b>.
          </p>
        )}
      </div>
    </div>
  );
}
