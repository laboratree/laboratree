"use client";

import type { CausalMechanism, DidMech, IvMech, RctMech, RddMech } from "@/lib/api";
import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

const LEAF = "#6DB33F";
const BLUE = "#2E6C8E";
const GOLD = "#C9A227";
const RED = "#C0392B";

function mechOf(series: Record<string, unknown> | null | undefined): CausalMechanism | null {
  return (series?.mechanism as CausalMechanism | undefined) ?? null;
}

/* ---- RCT: two clouds + their means, the gap is the effect ---------------------------------- */

export function RctRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series) as RctMech | null;
  if (m?.kind !== "rct") return <p className="text-xs text-muted">No RCT scenario for this data.</p>;
  const n = Math.max(m.treated_pts.length, m.control_pts.length);
  const k = useSubstep(clock, entryIdx, Math.max(1, n));
  const shown = reducedMotion ? n : k;

  const all = [...m.treated_pts, ...m.control_pts, m.ci_low, m.ci_high];
  const lo = Math.min(...all), hi = Math.max(...all);
  const Y = (v: number) => 120 - ((v - lo) / (hi - lo || 1)) * 100;

  return (
    <div>
      <svg viewBox="0 0 280 140" width="100%" style={{ maxHeight: 230 }}
           role="img" aria-label="RCT: treated vs control earnings">
        {/* control cloud (left) */}
        {m.control_pts.slice(0, shown).map((v, i) => (
          <circle key={`c${i}`} cx={40 + (i % 8) * 7} cy={Y(v)} r={2.6} fill={BLUE} opacity={0.6} />
        ))}
        {/* treated cloud (right) */}
        {m.treated_pts.slice(0, shown).map((v, i) => (
          <circle key={`t${i}`} cx={170 + (i % 8) * 7} cy={Y(v)} r={2.6} fill={LEAF} opacity={0.6} />
        ))}
        {/* means */}
        <line x1={34} y1={Y(m.control_mean)} x2={102} y2={Y(m.control_mean)} stroke={BLUE} strokeWidth={2} />
        <line x1={164} y1={Y(m.treated_mean)} x2={232} y2={Y(m.treated_mean)} stroke={LEAF} strokeWidth={2} />
        {/* the gap */}
        <line x1={133} y1={Y(m.control_mean)} x2={133} y2={Y(m.treated_mean)} stroke={GOLD}
              strokeWidth={2.5} markerEnd="url(#arr)" />
        <text x={68} y={134} textAnchor="middle" fontSize={9} fill={BLUE}>control</text>
        <text x={198} y={134} textAnchor="middle" fontSize={9} fill={LEAF}>treated</text>
        <text x={140} y={(Y(m.control_mean) + Y(m.treated_mean)) / 2} fontSize={10} fill="#8a6d1a">
          +{m.ate}
        </text>
      </svg>
      <p className="text-[10px] text-muted">
        ATE = {m.treated_mean} − {m.control_mean} = <b className="text-forest">{m.ate}</b> {m.unit}{" "}
        · 95% CI [{m.ci_low}, {m.ci_high}] · p = {m.p_value} · true effect {m.true_effect}. Random
        assignment is what makes this gap causal.
      </p>
    </div>
  );
}

/* ---- DiD: two lines, the gap-of-gaps ------------------------------------------------------- */

export function DidRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series) as DidMech | null;
  if (m?.kind !== "did") return <p className="text-xs text-muted">No DiD scenario for this data.</p>;
  const k = useSubstep(clock, entryIdx, 4);
  const step = reducedMotion ? 4 : k;

  const vals = [m.treated_pre, m.treated_post, m.control_pre, m.control_post];
  const lo = Math.min(...vals) - 2, hi = Math.max(...vals) + 2;
  const Y = (v: number) => 115 - ((v - lo) / (hi - lo || 1)) * 95;
  const XPRE = 70, XPOST = 210;
  // counterfactual: treated would have moved parallel to control
  const cfPost = m.treated_pre + (m.control_post - m.control_pre);

  return (
    <div>
      <svg viewBox="0 0 280 140" width="100%" style={{ maxHeight: 230 }}
           role="img" aria-label="difference-in-differences">
        <text x={XPRE} y={132} textAnchor="middle" fontSize={9} fill="#5B6B60">before</text>
        <text x={XPOST} y={132} textAnchor="middle" fontSize={9} fill="#5B6B60">after</text>
        {/* control line */}
        {step >= 1 && (
          <line x1={XPRE} y1={Y(m.control_pre)} x2={XPOST} y2={Y(m.control_post)} stroke={BLUE} strokeWidth={2} />
        )}
        {/* treated line */}
        {step >= 2 && (
          <line x1={XPRE} y1={Y(m.treated_pre)} x2={XPOST} y2={Y(m.treated_post)} stroke={LEAF} strokeWidth={2} />
        )}
        {/* counterfactual (parallel-trends) */}
        {step >= 3 && (
          <line x1={XPRE} y1={Y(m.treated_pre)} x2={XPOST} y2={Y(cfPost)} stroke={LEAF}
                strokeWidth={1.5} strokeDasharray="4 3" opacity={0.7} />
        )}
        {/* the DiD gap: actual treated_post vs counterfactual */}
        {step >= 4 && (
          <>
            <line x1={XPOST} y1={Y(cfPost)} x2={XPOST} y2={Y(m.treated_post)} stroke={GOLD} strokeWidth={2.5} />
            <text x={XPOST + 6} y={(Y(cfPost) + Y(m.treated_post)) / 2} fontSize={10} fill="#8a6d1a">
              {m.did_effect}
            </text>
          </>
        )}
        {[["T", m.treated_pre, XPRE, LEAF], ["T", m.treated_post, XPOST, LEAF],
          ["C", m.control_pre, XPRE, BLUE], ["C", m.control_post, XPOST, BLUE]].map(([, v, x, c], i) => (
          <circle key={i} cx={x as number} cy={Y(v as number)} r={3.5} fill={c as string} />
        ))}
      </svg>
      <p className="text-[10px] text-muted">
        DiD = ({m.treated_post} − {m.treated_pre}) − ({m.control_post} − {m.control_pre}) ={" "}
        <b className="text-forest">{m.did_effect}</b> (true {m.true_effect}). The dashed line is the
        parallel-trends counterfactual; the gold gap is the causal effect.
      </p>
    </div>
  );
}

/* ---- IV: the two stages, and beating confounded OLS ---------------------------------------- */

export function IvRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series) as IvMech | null;
  if (m?.kind !== "iv") return <p className="text-xs text-muted">No IV scenario for this data.</p>;
  const k = useSubstep(clock, entryIdx, 3);
  const step = reducedMotion ? 3 : k;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-stretch gap-2">
        <Stage on={step >= 1} n={1} title="Instrument → treatment"
               body={`Z (near college) moves schooling: slope ${m.first_stage_slope}`}
               foot={`first-stage F = ${m.first_stage_F}${m.weak_instrument ? " ⚠ weak!" : " ✓ strong"}`}
               tone={m.weak_instrument ? RED : LEAF} />
        <span className="self-center text-muted">→</span>
        <Stage on={step >= 2} n={2} title="Fitted treatment → outcome"
               body="Regress wages on the instrument-driven part of schooling only"
               foot={`IV effect = ${m.iv_effect}`} tone={GOLD} />
      </div>
      {step >= 3 && (
        <div className="rounded-lg border border-line bg-white p-2.5">
          <p className="mb-1 text-[10px] font-medium uppercase tracking-wide text-muted">
            IV vs confounded OLS
          </p>
          <Bar label="naive OLS (biased)" v={m.naive_ols_effect} max={Math.max(m.naive_ols_effect, m.iv_effect, m.true_effect)} tone={RED} />
          <Bar label="IV (2SLS)" v={m.iv_effect} max={Math.max(m.naive_ols_effect, m.iv_effect, m.true_effect)} tone={LEAF} />
          <Bar label="true effect" v={m.true_effect} max={Math.max(m.naive_ols_effect, m.iv_effect, m.true_effect)} tone="#5B6B60" />
          <p className="mt-1 text-[10px] text-muted">
            plain OLS is dragged up by the ability confounder; IV recovers the true return.
          </p>
        </div>
      )}
    </div>
  );
}

/* ---- RDD: two local lines, the jump at the cutoff ----------------------------------------- */

export function RddRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = mechOf(lesson.trace.series) as RddMech | null;
  if (m?.kind !== "rdd") return <p className="text-xs text-muted">No RDD scenario for this data.</p>;
  const pts = [...m.left, ...m.right];
  const total = pts.length;
  const k = useSubstep(clock, entryIdx, Math.max(1, total));
  const shown = reducedMotion ? total : k;

  const rs = pts.map((p) => p.r), ys = pts.map((p) => p.y);
  const rlo = Math.min(...rs), rhi = Math.max(...rs), ylo = Math.min(...ys), yhi = Math.max(...ys);
  const X = (r: number) => 20 + ((r - rlo) / (rhi - rlo || 1)) * 240;
  const Y = (y: number) => 118 - ((y - ylo) / (yhi - ylo || 1)) * 100;
  const xc = X(0);
  const done = shown >= total;

  return (
    <div>
      <svg viewBox="0 0 280 135" width="100%" style={{ maxHeight: 240 }}
           role="img" aria-label="regression discontinuity jump">
        <line x1={xc} y1={8} x2={xc} y2={122} stroke="#E4EBE1" strokeDasharray="3 3" />
        <text x={xc} y={132} textAnchor="middle" fontSize={8} fill="#5B6B60">cutoff</text>
        {pts.slice(0, shown).map((p, i) => (
          <circle key={i} cx={X(p.r)} cy={Y(p.y)} r={2.4} fill={p.r < 0 ? "#2E6C8E" : "#6DB33F"} opacity={0.6} />
        ))}
        {done && (
          <>
            {/* the two local fits meeting the cutoff at jump_lo / jump_hi */}
            <line x1={X(rlo)} y1={Y(m.jump_lo - 1.2 * rlo * 0)} x2={xc} y2={Y(m.jump_lo)} stroke="#2E6C8E" strokeWidth={2} />
            <line x1={xc} y1={Y(m.jump_hi)} x2={X(rhi)} y2={Y(m.jump_hi + 1.2 * rhi * 0)} stroke="#6DB33F" strokeWidth={2} />
            {/* the gap */}
            <line x1={xc} y1={Y(m.jump_lo)} x2={xc} y2={Y(m.jump_hi)} stroke="#C9A227" strokeWidth={3} />
            <text x={xc + 5} y={(Y(m.jump_lo) + Y(m.jump_hi)) / 2} fontSize={10} fill="#8a6d1a">
              +{m.rd_effect}
            </text>
          </>
        )}
      </svg>
      <p className="text-[10px] text-muted">
        the gold gap at the cutoff = <b className="text-forest">{m.rd_effect}</b> (true {m.true_effect},
        p = {m.p_value}). Units just above vs below the threshold are alike, so the jump is causal.
      </p>
    </div>
  );
}

function Stage({ on, n, title, body, foot, tone }: { on: boolean; n: number; title: string; body: string; foot: string; tone: string }) {
  return (
    <div className="min-w-[140px] flex-1 rounded-lg border p-2"
         style={{ borderColor: on ? tone : "#E4EBE1", opacity: on ? 1 : 0.4, transition: "opacity .4s" }}>
      <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: tone }}>stage {n}</p>
      <p className="text-[11px] font-medium text-forest">{title}</p>
      <p className="mt-0.5 text-[10px] text-muted">{body}</p>
      <p className="mt-1 font-mono text-[10px]" style={{ color: tone }}>{foot}</p>
    </div>
  );
}

function Bar({ label, v, max, tone }: { label: string; v: number; max: number; tone: string }) {
  return (
    <div className="mb-1 flex items-center gap-1.5">
      <span className="w-28 shrink-0 text-[10px] text-ink">{label}</span>
      <div className="h-2.5 flex-1 rounded bg-bg">
        <div className="h-2.5 rounded" style={{ width: `${Math.max(2, (v / (max || 1)) * 100)}%`, background: tone }} />
      </div>
      <span className="w-10 text-right font-mono text-[10px] text-muted">{v}</span>
    </div>
  );
}
