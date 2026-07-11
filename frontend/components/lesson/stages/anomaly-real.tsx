"use client";

import type { AnomalyMechanism } from "@/lib/api";
import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

const LEAF = "#6DB33F";
const RED = "#C0392B";

function mechOf(series: Record<string, unknown> | null | undefined): AnomalyMechanism | null {
  return (series?.mechanism as AnomalyMechanism | undefined) ?? null;
}

function scaler(xs: number[], ys: number[], w = 200, h = 130, pad = 12) {
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys), ymax = Math.max(...ys);
  const sx = (v: number) => pad + ((v - xmin) / (xmax - xmin || 1)) * (w - 2 * pad);
  const sy = (v: number) => h - pad - ((v - ymin) / (ymax - ymin || 1)) * (h - 2 * pad);
  return { sx, sy };
}

/* ---- Isolation Forest: real path lengths + histogram ------------------------------------- */

export function IforestRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series);
  if (m?.kind !== "isolation_forest")
    return <p className="text-xs text-muted">No isolation-forest mechanism for this data.</p>;
  const bins = m.hist.length;
  const k = useSubstep(clock, entryIdx, bins);
  const shown = reducedMotion ? bins : k;

  const { sx, sy } = scaler(m.points.map((p) => p.x), m.points.map((p) => p.y));
  const maxH = Math.max(...m.hist, 1);
  const shortThird = m.edges[Math.max(1, Math.floor(bins / 3))];

  return (
    <div className="flex flex-wrap items-start gap-3">
      <svg viewBox="0 0 200 140" width={200} role="img" aria-label="isolation forest on your real points">
        {m.points.map((p, i) => (
          <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={p.anomaly ? 5 : 3.5}
                  fill={p.anomaly ? RED : LEAF} stroke={p.anomaly ? "#7a1f16" : "none"} />
        ))}
        <text x={100} y={138} textAnchor="middle" fontSize={9} fill="#5B6B60">your rows (● anomaly)</text>
      </svg>
      <div className="min-w-[170px] flex-1">
        <p className="text-[10px] font-medium uppercase tracking-wide text-muted">
          path-length histogram
        </p>
        <svg viewBox="0 0 180 90" width="100%" role="img" aria-label="path length distribution">
          {m.hist.map((h, i) => {
            const bw = 180 / bins;
            const isShort = m.edges[i] < shortThird;
            return (
              <rect key={i} x={i * bw + 1} y={80 - (i < shown ? (h / maxH) * 70 : 0)}
                    width={bw - 2} height={i < shown ? (h / maxH) * 70 : 0} rx={2}
                    fill={isShort ? RED : "#9DB8A5"} style={{ transition: "height .35s, y .35s" }} />
            );
          })}
          <line x1={0} y1={80} x2={180} y2={80} stroke="#E4EBE1" />
        </svg>
        <p className="mt-1 text-[10px] text-muted">
          few cuts to isolate (short path, <span className="text-red-600">left/red</span>) = suspicious.
          Expected path for {"n"} rows ≈ <b>{m.c_n}</b> cuts — anomalies fall well below it.
        </p>
      </div>
    </div>
  );
}

/* ---- LOF: real k-neighbourhood + density ratio ------------------------------------------- */

export function LofRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series);
  if (m?.kind !== "lof") return <p className="text-xs text-muted">No LOF mechanism for this data.</p>;
  const nbr = m.focus.neighbors.length;
  const k = useSubstep(clock, entryIdx, Math.max(1, nbr));
  const shown = reducedMotion ? nbr : k;

  const allX = [...m.points.map((p) => p.x), m.focus.x];
  const allY = [...m.points.map((p) => p.y), m.focus.y];
  const { sx, sy } = scaler(allX, allY, 260, 150);
  const rpx = Math.abs(sx(m.focus.x + m.focus.radius) - sx(m.focus.x));

  return (
    <div>
      <svg viewBox="0 0 260 160" width="100%" style={{ maxHeight: 250 }}
           role="img" aria-label="LOF neighbourhood on your real points">
        <circle cx={sx(m.focus.x)} cy={sy(m.focus.y)} r={rpx} fill={RED} fillOpacity={0.06}
                stroke={RED} strokeOpacity={0.5} strokeDasharray="4 3" />
        {m.points.map((p, i) => (
          <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={p.anomaly ? 4.5 : 3}
                  fill={p.anomaly ? RED : LEAF} opacity={0.85} />
        ))}
        {m.focus.neighbors.slice(0, shown).map((nb, i) => (
          <line key={i} x1={sx(m.focus.x)} y1={sy(m.focus.y)} x2={sx(nb.x)} y2={sy(nb.y)}
                stroke="#C9A227" strokeWidth={1} strokeOpacity={0.7} />
        ))}
        <circle cx={sx(m.focus.x)} cy={sy(m.focus.y)} r={6} fill={RED} stroke="#7a1f16" strokeWidth={2} />
        <text x={sx(m.focus.x)} y={sy(m.focus.y) - 10} textAnchor="middle" fontSize={9} fill="#7a1f16">
          LOF {m.focus.lof}
        </text>
      </svg>
      <p className="text-[10px] text-muted">
        the red point needs a big ring to reach its k = {m.k} neighbours — it&apos;s far sparser
        than THEY are. LOF ≈ {m.focus.lof} (≫ 1 = a local outlier the crowd would hide).
      </p>
    </div>
  );
}

/* ---- One-Class SVM: the real learned boundary -------------------------------------------- */

export function OcsvmRealStage({ lesson, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series);
  if (m?.kind !== "one_class_svm")
    return <p className="text-xs text-muted">No one-class SVM boundary for this data.</p>;
  void reducedMotion;
  const g = m.grid.length;
  const { sx, sy } = scaler(m.gx, m.gy, 260, 150);
  const cw = Math.abs(sx(m.gx[1]) - sx(m.gx[0]));
  const ch = Math.abs(sy(m.gy[1]) - sy(m.gy[0]));

  return (
    <div>
      <svg viewBox="0 0 260 160" width="100%" style={{ maxHeight: 250 }}
           role="img" aria-label="one-class SVM boundary on your real points">
        {m.grid.flatMap((row, i) =>
          row.map((v, j) => (
            <rect key={`${i}-${j}`} x={sx(m.gx[j]) - cw / 2} y={sy(m.gy[i]) - ch / 2}
                  width={cw + 0.5} height={ch + 0.5}
                  fill={v >= 0 ? LEAF : RED} fillOpacity={Math.min(0.28, Math.abs(v) * 0.5)} />
          )),
        )}
        {/* the boundary itself: cells straddling zero */}
        {m.grid.flatMap((row, i) =>
          row.map((v, j) =>
            Math.abs(v) < 0.06 ? (
              <rect key={`b${i}-${j}`} x={sx(m.gx[j]) - cw / 2} y={sy(m.gy[i]) - ch / 2}
                    width={cw + 0.5} height={ch + 0.5} fill="#C9A227" fillOpacity={0.7} />
            ) : null,
          ),
        )}
        {m.points.map((p, i) => (
          <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={p.anomaly ? 4.5 : 3}
                  fill={p.anomaly ? "#7a1f16" : "#14342A"} stroke="white" strokeWidth={0.6} />
        ))}
      </svg>
      <p className="text-[10px] text-muted">
        the gold band is the REAL learned boundary; <span className="text-leaf">green</span> is the
        normal region it shrink-wrapped, ν = {m.nu} sets how many rows it leaves outside. Points
        beyond the wrap are flagged.
      </p>
    </div>
  );
}
