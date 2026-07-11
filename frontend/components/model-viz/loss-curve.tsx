"use client";

import { useEffect, useState } from "react";
import type { ModelTrace } from "@/lib/api";

/** Shared "loss descends" animation — gradient descent made visible: the model's error curve drawn
 *  as a hill, with a gold ball rolling down it (~4s, replayable). Used by the nn family (its REAL
 *  per-epoch training loss) and the linear family (an illustrative SGD curve). */

/** Narrow `trace.series.loss_curve` (loosely typed extras) to a usable number[]. */
export function lossCurveOf(trace: ModelTrace): number[] | null {
  const c = trace.series?.loss_curve;
  if (!Array.isArray(c) || c.length < 2) return null;
  return c.every((v) => typeof v === "number" && Number.isFinite(v)) ? (c as number[]) : null;
}

const DUR_MS = 4000;
const W = 380;
const H = 185;
const PL = 42; // room for the rotated y-axis label
const PR = 58; // room for the "converged" label
const PT = 18;
const PB = 34;

export function LossDescent({ curve, caption }: { curve: number[]; caption: string }) {
  const [t, setT] = useState(0); // eased 0..1 progress of the ball
  const [run, setRun] = useState(0); // bump to replay

  useEffect(() => {
    let raf = 0;
    let start: number | null = null;
    const tick = (now: number) => {
      if (start == null) start = now;
      const p = Math.min(1, (now - start) / DUR_MS);
      const eased = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2; // ease-in-out
      setT(eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    setT(0);
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [run, curve]);

  if (curve.length < 2) return null;
  const lo = Math.min(...curve);
  const hi = Math.max(...curve);
  const span = hi - lo || 1;
  const px = (i: number) => PL + (i / (curve.length - 1)) * (W - PL - PR);
  const py = (v: number) => PT + ((hi - v) / span) * (H - PT - PB);
  const path = curve.map((v, i) => `${i ? "L" : "M"}${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(" ");

  // the ball: interpolate between the two surrounding curve points
  const fi = t * (curve.length - 1);
  const i0 = Math.floor(fi);
  const i1 = Math.min(curve.length - 1, i0 + 1);
  const fr = fi - i0;
  const bx = px(i0) + (px(i1) - px(i0)) * fr;
  const by = py(curve[i0]) + (py(curve[i1]) - py(curve[i0])) * fr;
  const cur = curve[i0] + (curve[i1] - curve[i0]) * fr;
  const done = t >= 0.999;
  const endX = px(curve.length - 1);
  const endY = py(curve[curve.length - 1]);

  return (
    <div className="rounded-lg border border-line bg-white p-2">
      <div className="mb-1 flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium text-forest">
          watch the error roll downhill{" "}
          <span className="font-normal text-muted">
            — error now: <b className="text-forest">{cur.toFixed(3)}</b>
            {done && <span className="text-[#8a6d1a]"> · converged ✓</span>}
          </span>
        </span>
        <button
          onClick={() => setRun((r) => r + 1)}
          className="shrink-0 rounded border border-line px-2 py-0.5 text-forest hover:bg-bg"
        >
          ↻ replay
        </button>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="loss descending during training">
        {/* axes */}
        <line x1={PL} y1={PT} x2={PL} y2={H - PB} stroke="#C7D4CC" />
        <line x1={PL} y1={H - PB} x2={W - PR + 30} y2={H - PB} stroke="#C7D4CC" />
        <text
          transform={`rotate(-90 12 ${(PT + H - PB) / 2})`}
          x={12}
          y={(PT + H - PB) / 2}
          fontSize={8.5}
          fill="#7C8A80"
          textAnchor="middle"
        >
          how wrong the model is (loss)
        </text>
        <text x={(PL + W - PR) / 2} y={H - 4} fontSize={8.5} fill="#7C8A80" textAnchor="middle">
          training steps →
        </text>
        {/* the error surface still ahead of the ball (light), and the part already descended (dark) */}
        <path d={path} fill="none" stroke="#C7D4CC" strokeWidth={1.6} />
        <path
          d={path}
          fill="none"
          stroke="#14342A"
          strokeWidth={2.2}
          pathLength={1}
          strokeDasharray={`${t} 1`}
          strokeLinecap="round"
        />
        {/* start marker: where training begins (big error) */}
        <circle cx={px(0)} cy={py(curve[0])} r={3} fill="#C0392B" />
        <text x={px(0) + 6} y={py(curve[0]) - 5} fontSize={8.5} fill="#C0392B">
          start — big error
        </text>
        {/* the end of the slope: converged */}
        <circle
          cx={endX}
          cy={endY}
          r={done ? 6 : 3}
          fill={done ? "none" : "#6DB33F"}
          stroke={done ? "#C9A227" : "none"}
          strokeWidth={2.5}
        />
        <text x={endX + 8} y={endY + 3} fontSize={9} fill={done ? "#8a6d1a" : "#7C8A80"} fontWeight={done ? 700 : 400}>
          converged
        </text>
        {/* the ball */}
        <circle cx={bx} cy={by} r={6.5} fill="#C9A227" stroke="#fff" strokeWidth={2} />
      </svg>
      <p className="px-1 pt-1 text-[10px] text-muted">{caption}</p>
    </div>
  );
}
