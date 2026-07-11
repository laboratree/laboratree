"use client";

import { useEffect, useState } from "react";
import type { ModelTrace } from "@/lib/api";
import { Scatter } from "./knn";
import type { TestProps, TrainProps } from "./shared";

/** Clustering family — groups discovered on the map; tests join the nearest centre.
 *  Training shows the LITERAL k-means loop: step through the recorded iterations and watch the
 *  ✕ centres move, the rows recolor, and the total distance (inertia) fall until it settles. */

type Iter = { centers: { x: number; y: number }[]; assign: string[]; inertia: number };

const PALETTE = ["#6DB33F", "#C0392B", "#2E6C8E", "#B8860B", "#7D3C98", "#148F77", "#AF601A", "#5D6D7E"];

function IterMap({ trace, iter }: { trace: ModelTrace; iter: Iter }) {
  const pts = trace.points ?? [];
  const xs = pts.map((p) => p.x).concat(iter.centers.map((c) => c.x));
  const ys = pts.map((p) => p.y).concat(iter.centers.map((c) => c.y));
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  const W = 320;
  const H = 190;
  const PAD = 18;
  const sx = (v: number) => PAD + ((v - x0) / (x1 - x0 || 1)) * (W - 2 * PAD);
  const sy = (v: number) => H - PAD - ((v - y0) / (y1 - y0 || 1)) * (H - 2 * PAD);
  const clusters = Array.from(new Set(iter.assign)).sort();
  const axes = (trace.series ?? {}) as { x?: string; y?: string };

  return (
    <div className="rounded-lg border border-line bg-white p-2">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="k-means iteration">
        {pts.map((p, i) => (
          <circle
            key={i}
            cx={sx(p.x)}
            cy={sy(p.y)}
            r={3}
            fill={PALETTE[clusters.indexOf(iter.assign[i] ?? "") % PALETTE.length]}
            opacity={0.55}
            style={{ transition: "fill .5s" }}
          />
        ))}
        {iter.centers.map((c, ci) => (
          <g key={ci} style={{ transition: "transform .6s" }} transform={`translate(${sx(c.x)},${sy(c.y)})`}>
            <line x1={-6} y1={-6} x2={6} y2={6} stroke={PALETTE[ci % PALETTE.length]} strokeWidth={3.5} />
            <line x1={-6} y1={6} x2={6} y2={-6} stroke={PALETTE[ci % PALETTE.length]} strokeWidth={3.5} />
            <circle r={9} fill="none" stroke="#14342A" strokeWidth={1} opacity={0.5} />
          </g>
        ))}
        <text x={W / 2} y={H - 3} fontSize={9} fill="#7C8A80" textAnchor="middle">{axes.x ?? "x"}</text>
        <text x={8} y={H / 2} fontSize={9} fill="#7C8A80" transform={`rotate(-90 8 ${H / 2})`} textAnchor="middle">
          {axes.y ?? "y"}
        </text>
      </svg>
    </div>
  );
}

export function Train({ trace }: TrainProps) {
  const s = (trace.series ?? {}) as { k?: number; sizes?: number[]; iterations?: Iter[] };
  const iters = s.iterations ?? [];
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    if (step >= iters.length - 1) {
      setPlaying(false);
      return;
    }
    const id = setTimeout(() => setStep((x) => x + 1), 1300);
    return () => clearTimeout(id);
  }, [playing, step, iters.length]);

  if (!iters.length) {
    return (
      <div>
        <p className="mb-1 text-[11px] text-muted">
          k-means grouped the rows into {s.k ?? "k"} clusters.
          {s.sizes ? ` Group sizes: ${s.sizes.join(" · ")}.` : ""}
        </p>
        <Scatter trace={trace} />
      </div>
    );
  }
  const it = iters[Math.min(step, iters.length - 1)];
  const last = step >= iters.length - 1;

  return (
    <div className="space-y-1.5">
      <p className="text-[11px] text-muted">
        The LITERAL k-means loop, recorded on this data: ✕ = the {s.k} centres.{" "}
        <b>Each iteration:</b> every row joins its nearest ✕ (colors), then each ✕ moves to the
        middle of its rows. <b>Inertia</b> = total distance from rows to their centres — watch it
        fall until the centres stop moving.
      </p>
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        <span className="font-medium text-forest">Iteration {step + 1} / {iters.length}</span>
        <span className="rounded-full bg-leaf/15 px-2 py-0.5 text-forest">inertia {it.inertia}</span>
        {last && <span className="rounded-full bg-[#FBF3D6] px-2 py-0.5 text-[#8a6d1a]">settled ✓</span>}
        <div className="ml-auto flex gap-1">
          <button onClick={() => { setPlaying(false); setStep((x) => Math.max(0, x - 1)); }} disabled={step === 0}
            className="rounded border border-line px-2 py-0.5 text-forest disabled:opacity-40">◀</button>
          <button
            onClick={() => { if (last) { setStep(0); setPlaying(true); } else setPlaying((p) => !p); }}
            className="rounded bg-forest px-2.5 py-0.5 text-white"
          >
            {playing ? "❚❚" : last ? "↻ Replay" : "▶ Play"}
          </button>
          <button onClick={() => { setPlaying(false); setStep((x) => Math.min(iters.length - 1, x + 1)); }} disabled={last}
            className="rounded border border-line px-2 py-0.5 text-forest disabled:opacity-40">▶</button>
        </div>
      </div>
      <IterMap trace={trace} iter={it} />
    </div>
  );
}

export function Test({ trace, row }: TestProps) {
  return (
    <div className="space-y-2">
      <Scatter trace={trace} row={row} />
      {row.distances && (
        <div className="rounded-lg border border-line bg-white p-2 text-[11px]">
          <p className="mb-1 text-muted">distance from this row to each cluster centre:</p>
          {row.distances.map((d, i) => (
            <div key={i} className="flex justify-between border-t border-line/50 py-0.5 first:border-t-0">
              <span className={i === 0 ? "font-medium text-forest" : "text-muted"}>
                {d.cluster}
                {i === 0 ? " ← closest" : ""}
              </span>
              <span className="text-ink">{d.distance}</span>
            </div>
          ))}
          <p className="mt-1 rounded bg-leaf/10 p-1.5">
            joins <b className="text-forest">{String(row.predicted)}</b> (the nearest centre)
          </p>
        </div>
      )}
    </div>
  );
}
