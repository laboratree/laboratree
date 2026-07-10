"use client";

import type { ClusterMechanism, DbscanPoint, DendroMerge } from "@/lib/api";
import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

const PAL = ["#2E6C8E", "#6DB33F", "#7D3C98", "#B8860B", "#C0392B", "#16A085", "#E67E22", "#2C3E50"];
const clr = (c: number) => (c < 0 ? "#9AA59C" : PAL[c % PAL.length]);

function mechOf(series: Record<string, unknown> | null | undefined): ClusterMechanism | null {
  return (series?.mechanism as ClusterMechanism | undefined) ?? null;
}

/** Map real data coords into an SVG box, with a small margin. */
function scaler(xs: number[], ys: number[], w = 280, h = 130, pad = 12) {
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys), ymax = Math.max(...ys);
  const sx = (v: number) => pad + ((v - xmin) / (xmax - xmin || 1)) * (w - 2 * pad);
  const sy = (v: number) => h - pad - ((v - ymin) / (ymax - ymin || 1)) * (h - 2 * pad);
  return { sx, sy };
}

/* ---- DBSCAN: real points, core/border/noise, density growth ------------------------------ */

export function DbscanRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series);
  if (m?.kind !== "dbscan") return <p className="text-xs text-muted">No DBSCAN mechanism for this data.</p>;
  const total = m.total_steps || m.points.length;
  const k = useSubstep(clock, entryIdx, Math.max(1, total));
  const grown = reducedMotion ? total : k;

  const { sx, sy } = scaler(m.points.map((p) => p.x), m.points.map((p) => p.y));
  const lit = (p: DbscanPoint) => p.role === "noise" || p.step < grown;
  const igniting = m.points.find((p) => p.step === grown - 1 && p.role === "core");

  return (
    <div>
      <svg viewBox="0 0 280 150" width="100%" style={{ maxHeight: 250 }}
           role="img" aria-label="DBSCAN growing on your real points">
        {igniting && (
          <circle cx={sx(igniting.x)} cy={sy(igniting.y)}
                  r={18} fill={clr(igniting.cluster)} opacity={0.15}
                  stroke={clr(igniting.cluster)} strokeOpacity={0.5} />
        )}
        {m.points.map((p, i) => {
          const on = lit(p);
          const c = p.role === "noise" ? "#9AA59C" : clr(p.cluster);
          return p.role === "border" ? (
            <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={4} fill="none"
                    stroke={on ? c : "#D9E1DA"} strokeWidth={2} style={{ transition: "stroke .3s" }} />
          ) : p.role === "noise" ? (
            <text key={i} x={sx(p.x)} y={sy(p.y) + 3} textAnchor="middle" fontSize={9}
                  fill={grown >= total ? "#9AA59C" : "#D9E1DA"}>×</text>
          ) : (
            <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={4.5}
                    fill={on ? c : "#D9E1DA"} style={{ transition: "fill .3s" }} />
          );
        })}
      </svg>
      <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-muted">
        <span>
          ε = {m.eps} · min neighbours = {m.min_samples} · <b className="text-forest">{m.n_clusters}</b> clusters ·{" "}
          <b>{m.n_noise}</b> noise
        </span>
        <span>
          ● core · ○ border · × noise — grown {Math.min(grown, total)}/{total}
        </span>
      </div>
    </div>
  );
}

/* ---- GMM: real ellipses + responsibilities ----------------------------------------------- */

export function GmmRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series);
  if (m?.kind !== "gmm") return <p className="text-xs text-muted">No GMM mechanism for this data.</p>;
  const k = useSubstep(clock, entryIdx, Math.max(1, m.points.length));
  const hi = Math.max(0, Math.min(m.points.length, reducedMotion ? m.points.length : k) - 1);

  const xs = [...m.points.map((p) => p.x), ...m.ellipses.map((e) => e.cx)];
  const ys = [...m.points.map((p) => p.y), ...m.ellipses.map((e) => e.cy)];
  const { sx, sy } = scaler(xs, ys);
  const cur = m.points[hi];
  // ellipse radii are in data units; scale by the axis span ratio (approx isotropic)
  const spanX = Math.max(...xs) - Math.min(...xs) || 1;
  const rscale = (256 / spanX) * 0.5;

  return (
    <div className="flex flex-wrap items-start gap-3">
      <svg viewBox="0 0 280 150" width={280} role="img" aria-label="GMM ellipses on your real points">
        {m.ellipses.map((e, c) => (
          <ellipse key={c} cx={sx(e.cx)} cy={sy(e.cy)} rx={e.rx * rscale} ry={e.ry * rscale}
                   transform={`rotate(${-e.angle} ${sx(e.cx)} ${sy(e.cy)})`}
                   fill={clr(c)} fillOpacity={0.12} stroke={clr(c)} strokeWidth={1.4} />
        ))}
        {m.points.map((p, i) => (
          <circle key={i} cx={sx(p.x)} cy={sy(p.y)} r={i === hi ? 5.5 : 3.5}
                  fill={clr(p.cluster)} stroke={i === hi ? "#C9A227" : "none"} strokeWidth={2} />
        ))}
      </svg>
      {cur && (
        <div className="min-w-[150px] flex-1 rounded-lg border border-[#C9A227]/50 bg-[#FFFDF5] p-2.5">
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-[#8a6d1a]">
            this point's soft membership
          </p>
          {cur.resp.map((r, c) => (
            <div key={c} className="mb-1 flex items-center gap-1.5">
              <span className="w-14 text-[10px] text-ink">cluster {c + 1}</span>
              <div className="h-2.5 flex-1 rounded bg-bg">
                <div className="h-2.5 rounded" style={{ width: `${r * 100}%`, background: clr(c) }} />
              </div>
              <span className="w-8 text-right font-mono text-[10px] text-muted">{Math.round(r * 100)}%</span>
            </div>
          ))}
          <p className="mt-1 text-[10px] text-muted">
            every point belongs a little to each cluster — that's the &quot;soft&quot; in GMM
          </p>
        </div>
      )}
    </div>
  );
}

/* ---- Hierarchical: the real dendrogram, zipping up ---------------------------------------- */

type Laid = { x: number; y: number; node: number };

function layoutDendro(merges: DendroMerge[], nLeaves: number) {
  const pos = new Map<number, { x: number; y: number }>();
  // in-order leaf x from the merge tree so branches don't cross
  const order: number[] = [];
  const walk = (node: number) => {
    if (node < nLeaves) { order.push(node); return; }
    const mg = merges[node - nLeaves];
    if (mg) { walk(mg.a); walk(mg.b); }
  };
  walk(nLeaves + merges.length - 1);
  order.forEach((leaf, i) => pos.set(leaf, { x: i, y: 0 }));
  const hmax = Math.max(...merges.map((m) => m.height), 1);
  merges.forEach((mg) => {
    const a = pos.get(mg.a), b = pos.get(mg.b);
    if (a && b) pos.set(mg.node, { x: (a.x + b.x) / 2, y: mg.height / hmax });
  });
  return { pos, order, hmax };
}

export function DendrogramRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series);
  if (m?.kind !== "hierarchical") return <p className="text-xs text-muted">No dendrogram for this data.</p>;
  const done = useSubstep(clock, entryIdx, Math.max(1, m.merges.length));
  const shown = reducedMotion ? m.merges.length : done;

  const { pos, order } = layoutDendro(m.merges, m.n_leaves);
  const W = 280, H = 130, padX = 16;
  const X = (gx: number) => padX + (gx / Math.max(1, order.length - 1)) * (W - 2 * padX);
  const Y = (gy: number) => H - 14 - gy * (H - 28);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H + 8}`} width="100%" style={{ maxHeight: 220 }}
           role="img" aria-label="the real dendrogram building">
        {m.merges.slice(0, shown).map((mg, i) => {
          const a = pos.get(mg.a), b = pos.get(mg.b), n = pos.get(mg.node);
          if (!a || !b || !n) return null;
          const last = i === shown - 1;
          const col = last ? "#C9A227" : "#14342A";
          return (
            <g key={i} style={{ transition: "opacity .3s" }}>
              <line x1={X(a.x)} y1={Y(a.y)} x2={X(a.x)} y2={Y(n.y)} stroke={col} strokeWidth={last ? 2 : 1.2} />
              <line x1={X(b.x)} y1={Y(b.y)} x2={X(b.x)} y2={Y(n.y)} stroke={col} strokeWidth={last ? 2 : 1.2} />
              <line x1={X(a.x)} y1={Y(n.y)} x2={X(b.x)} y2={Y(n.y)} stroke={col} strokeWidth={last ? 2 : 1.2} />
            </g>
          );
        })}
        {order.map((leaf) => {
          const pt = pos.get(leaf);
          return pt ? <circle key={leaf} cx={X(pt.x)} cy={Y(0)} r={3} fill="#6DB33F" /> : null;
        })}
      </svg>
      <p className="text-[10px] text-muted">
        linkage: <b className="text-forest">{m.linkage}</b> · merge {Math.min(shown, m.merges.length)}/
        {m.merges.length}
        {shown < m.merges.length
          ? ` — height = how far apart the pair was`
          : " — slide a cut line across to choose the cluster count"}
      </p>
    </div>
  );
}

/* ---- Spectral: real points morph from tangled to embedded -------------------------------- */

export function SpectralRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series);
  if (m?.kind !== "spectral") return <p className="text-xs text-muted">No spectral embedding for this data.</p>;
  const steps = 20;
  const k = useSubstep(clock, entryIdx, steps);
  const t = reducedMotion ? 1 : k / steps;

  const os = scaler(m.points.map((p) => p.x), m.points.map((p) => p.y));
  const es = scaler(m.points.map((p) => p.ex), m.points.map((p) => p.ey));
  return (
    <div>
      <svg viewBox="0 0 280 150" width="100%" style={{ maxHeight: 250 }}
           role="img" aria-label="spectral embedding jump on your real points">
        {m.points.map((p, i) => {
          const x = os.sx(p.x) * (1 - t) + es.sx(p.ex) * t;
          const y = os.sy(p.y) * (1 - t) + es.sy(p.ey) * t;
          return <circle key={i} cx={x} cy={y} r={4} fill={clr(p.cluster)}
                         style={{ transition: "cx .1s linear, cy .1s linear" }} />;
        })}
      </svg>
      <p className="text-[10px] text-muted">
        {t < 0.5
          ? "your points in their original space — clusters can be tangled here"
          : "…moved into the spectral embedding, where the groups pull apart and k-means finishes"}
      </p>
    </div>
  );
}
