"use client";

/**
 * Concept widgets — small, self-contained SVG scenes scrubbed by lesson progress (0..1).
 * Reused across many lessons: the hessian bowl, the sigmoid squeeze, the 3-balls gini story,
 * the impurity inverted-U, the entropy surprise curve. Register new ones in WIDGETS.
 */

import type { ComponentType } from "react";

export type WidgetProps = { progress: number; reducedMotion: boolean };

const GOLD = "#C9A227";
const LEAF = "#6DB33F";
const RED = "#C0392B";
const INK = "#1E2A22";
const MUTED = "#5B6B60";

/* ---- hessian-bowl: loss curve → slope → curvature ------------------------------------- */

function HessianBowl({ progress }: WidgetProps) {
  const p = progress;
  // ball position on the bowl y = (x-0.5)^2 scaled; x sweeps 0.08 → 0.5 as p goes 0→1
  const bx = 0.08 + 0.42 * Math.min(1, p * 1.4);
  const by = (bx - 0.5) ** 2;
  const X = (u: number) => 30 + u * 240;
  const Y = (v: number) => 130 - v * 380;
  const slope = 2 * (bx - 0.5);
  const phase = p < 0.34 ? 0 : p < 0.67 ? 1 : 2;
  const pts = Array.from({ length: 41 }, (_, i) => {
    const u = i / 40;
    return `${X(u)},${Y((u - 0.5) ** 2)}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="loss curve, slope, curvature">
      <polyline points={pts} fill="none" stroke={INK} strokeWidth={1.6} />
      {/* tangent (the gradient) */}
      {phase >= 1 && (
        <line
          x1={X(bx - 0.14)} y1={Y(by - 0.14 * slope)}
          x2={X(bx + 0.14)} y2={Y(by + 0.14 * slope)}
          stroke={LEAF} strokeWidth={2}
        />
      )}
      {/* curvature hint (the hessian) */}
      {phase >= 2 && (
        <path
          d={`M ${X(0.38)} ${Y((0.38 - 0.5) ** 2) - 12} Q ${X(0.5)} ${Y(0) - 26} ${X(0.62)} ${Y((0.62 - 0.5) ** 2) - 12}`}
          fill="none" stroke={GOLD} strokeWidth={2} strokeDasharray="4 3"
        />
      )}
      <circle cx={X(bx)} cy={Y(by) - 5} r={6} fill={GOLD} stroke="#8a6d1a" />
      <text x={X(0.5)} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {phase === 0 ? "the loss is a curve — the ball rolls downhill"
          : phase === 1 ? "gradient g = the SLOPE where the ball stands"
          : "hessian h = how fast the slope changes (the bend)"}
      </text>
    </svg>
  );
}

/* ---- sigmoid-squeeze: raw score → probability ------------------------------------------ */

function SigmoidSqueeze({ progress }: WidgetProps) {
  const z = -6 + 12 * progress;
  const sig = (v: number) => 1 / (1 + Math.exp(-v));
  const X = (v: number) => 150 + v * 22;
  const Y = (pr: number) => 125 - pr * 100;
  const pts = Array.from({ length: 61 }, (_, i) => {
    const v = -6 + (12 * i) / 60;
    return `${X(v)},${Y(sig(v))}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="sigmoid squeezes score to probability">
      <line x1={X(-6)} y1={Y(0.5)} x2={X(6)} y2={Y(0.5)} stroke="#E4EBE1" />
      <polyline points={pts} fill="none" stroke={INK} strokeWidth={1.6} />
      <circle cx={X(z)} cy={Y(sig(z))} r={6} fill={GOLD} stroke="#8a6d1a" />
      <text x={X(z)} y={Y(sig(z)) - 10} textAnchor="middle" fontSize={10} fill="#8a6d1a">
        F={z.toFixed(1)} → p={sig(z).toFixed(2)}
      </text>
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        any raw score, squeezed into a 0–1 probability
      </text>
    </svg>
  );
}

/* ---- gini-balls: draw two balls — the chance they disagree IS gini ---------------------- */

const PAIRS: [number, number][] = [[0, 1], [0, 2], [1, 2], [0, 1], [1, 2], [0, 2]];

function GiniBalls({ progress }: WidgetProps) {
  // 3 balls, 2 green 1 red → p(green)=2/3: gini = 1 − (4/9 + 1/9) = 4/9 ≈ 0.44
  const colors = [LEAF, LEAF, RED];
  const k = Math.min(PAIRS.length - 1, Math.floor(progress * PAIRS.length));
  const [a, bIdx] = PAIRS[k];
  const disagree = colors[a] !== colors[bIdx];
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="gini as the two-draw disagreement game">
      {colors.map((c, i) => (
        <circle
          key={i} cx={90 + i * 60} cy={50} r={16} fill={c}
          stroke={i === a || i === bIdx ? GOLD : "transparent"} strokeWidth={3}
        />
      ))}
      <text x={150} y={95} textAnchor="middle" fontSize={11} fill={INK}>
        draw two at random → {disagree ? "they DISAGREE" : "they agree"}
      </text>
      <text x={150} y={116} textAnchor="middle" fontSize={10} fill={MUTED}>
        gini = P(disagree) = 1 − (⅔² + ⅓²) = 0.44 — pure group ⇒ gini 0
      </text>
      <text x={150} y={134} textAnchor="middle" fontSize={10} fill="#8a6d1a">
        a split is good when both sides play this game and rarely disagree
      </text>
    </svg>
  );
}

/* ---- impurity-curve: the inverted U --------------------------------------------------- */

function ImpurityCurve({ progress }: WidgetProps) {
  const p = 0.02 + 0.96 * progress;
  const gini = (v: number) => 2 * v * (1 - v);
  const X = (v: number) => 40 + v * 220;
  const Y = (g: number) => 125 - g * 180;
  const pts = Array.from({ length: 51 }, (_, i) => {
    const v = i / 50;
    return `${X(v)},${Y(gini(v))}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="gini vs class share — an inverted U">
      <polyline points={pts} fill="none" stroke={INK} strokeWidth={1.6} />
      <circle cx={X(p)} cy={Y(gini(p))} r={6} fill={GOLD} stroke="#8a6d1a" />
      <text x={X(p)} y={Y(gini(p)) - 10} textAnchor="middle" fontSize={10} fill="#8a6d1a">
        p={p.toFixed(2)} → gini {gini(p).toFixed(2)}
      </text>
      <text x={40} y={140} fontSize={10} fill={MUTED}>all class B</text>
      <text x={260} y={140} textAnchor="end" fontSize={10} fill={MUTED}>all class A</text>
      <text x={150} y={140} textAnchor="middle" fontSize={10} fill={MUTED}>50/50 = messiest</text>
    </svg>
  );
}

/* ---- surprise-curve: entropy = expected surprise ---------------------------------------- */

function SurpriseCurve({ progress }: WidgetProps) {
  const p = 0.03 + 0.94 * progress;
  const X = (v: number) => 40 + v * 220;
  const Y = (s: number) => 125 - Math.min(s, 5) * 22;
  const pts = Array.from({ length: 60 }, (_, i) => {
    const v = 0.03 + (0.97 * i) / 59;
    return `${X(v)},${Y(-Math.log2(v))}`;
  }).join(" ");
  const s = -Math.log2(p);
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="surprise −log2 p">
      <polyline points={pts} fill="none" stroke={INK} strokeWidth={1.6} />
      <circle cx={X(p)} cy={Y(s)} r={6} fill={GOLD} stroke="#8a6d1a" />
      <text x={X(p)} y={Y(s) - 10} textAnchor="middle" fontSize={10} fill="#8a6d1a">
        p={p.toFixed(2)} → surprise {s.toFixed(1)} bits
      </text>
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        rare events are surprising; entropy = the AVERAGE surprise of a group
      </text>
    </svg>
  );
}

/* ---- g-cancel: gradients cancel in mixed groups, stack in pure ones --------------------- */

const G_MIXED = [0.5, -0.5, 0.5, -0.5, 0.5, -0.5];
const G_PURE = [0.5, 0.5, 0.5, -0.5, -0.5, -0.5]; // regrouped: lefts agree, rights agree

function GCancel({ progress }: WidgetProps) {
  const grouped = progress >= 0.5;
  const gs = grouped ? G_PURE : G_MIXED;
  const half = gs.length / 2;
  const sum = (a: number[]) => a.reduce((s, v) => s + v, 0);
  const groups = grouped ? [gs.slice(0, half), gs.slice(half)] : [gs];
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="gradients cancel vs stack">
      {groups.map((g, gi) => {
        const x0 = grouped ? 40 + gi * 140 : 75;
        const total = sum(g);
        return (
          <g key={gi}>
            {g.map((v, i) => (
              <rect
                key={i}
                x={x0 + i * 24}
                y={v > 0 ? 60 - v * 60 : 60}
                width={16}
                height={Math.abs(v) * 60}
                rx={2}
                fill={v > 0 ? LEAF : RED}
                style={{ transition: "x .6s, y .6s" }}
              />
            ))}
            <text x={x0 + (g.length * 24) / 2 - 4} y={118} textAnchor="middle" fontSize={10}
                  fill={Math.abs(total) > 0.6 ? "#8a6d1a" : MUTED}>
              Σg = {total > 0 ? "+" : ""}{total.toFixed(1)} → sim {grouped ? "grows" : "≈ 0"}
            </text>
          </g>
        );
      })}
      <text x={150} y={140} textAnchor="middle" fontSize={10} fill={MUTED}>
        {grouped
          ? "gathered by a good split: pushes STACK — similarity rewards agreement"
          : "mixed group: pushes point both ways and CANCEL — nothing to learn"}
      </text>
    </svg>
  );
}

/* ---- fe-demean: the panel within-transform — the confounder vanishes -------------------- */

const FE_GROUPS = [
  { cx: 70, cy: 105, color: "#2E6C8E" },
  { cx: 150, cy: 75, color: LEAF },
  { cx: 230, cy: 45, color: "#7D3C98" },
];
const FE_OFFSETS: [number, number][] = [[-18, 12], [-6, 2], [6, -4], [18, -14]];

function FEDemean({ progress }: WidgetProps) {
  // phase 0→1: groups slide from their own centres onto the common centre (demeaning)
  const t = Math.min(1, Math.max(0, (progress - 0.35) / 0.4));
  const C = { x: 150, y: 75 };
  // pooled line chases the BETWEEN-group trend (steep); within slope is gentler
  const slope = 0.55 * (1 - t) + 0.18 * t;
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="fixed-effects demeaning">
      <line
        x1={40} y1={95 + slope * 90} x2={260} y2={95 - slope * 90}
        stroke={GOLD} strokeWidth={2} style={{ transition: "y1 .3s, y2 .3s" }}
      />
      {FE_GROUPS.map((g, gi) => {
        const cx = g.cx + (C.x - g.cx) * t;
        const cy = g.cy + (C.y - g.cy) * t;
        return (
          <g key={gi}>
            {FE_OFFSETS.map(([dx, dy], i) => (
              <circle key={i} cx={cx + dx} cy={cy + dy - dx * 0.18} r={4.5} fill={g.color}
                      opacity={0.85} />
            ))}
          </g>
        );
      })}
      <text x={150} y={140} textAnchor="middle" fontSize={10} fill={MUTED}>
        {t < 0.5
          ? "pooled: the line chases differences BETWEEN entities (their baggage)"
          : "demeaned: entities share one centre — the line re-fits on WITHIN changes"}
      </text>
    </svg>
  );
}

/* =====================================================================================
 * Per-model MECHANISM widgets — every model's own core move, scrubbable.
 * Canned point sets keep them deterministic; each caption states the mechanism honestly.
 * =================================================================================== */

const sub = (p: number, lo: number, hi: number) => Math.min(1, Math.max(0, (p - lo) / (hi - lo)));

/* bootstrap-hat: rows drawn WITH replacement — duplicates and misses, visible */
const BAG = [2, 0, 2, 5, 3, 5, 5, 1]; // which of rows 0..7 each draw picks (row 4,6,7 never drawn)
function BootstrapHat({ progress }: WidgetProps) {
  const drawn = Math.floor(progress * BAG.length);
  const counts = new Map<number, number>();
  BAG.slice(0, drawn).forEach((r) => counts.set(r, (counts.get(r) ?? 0) + 1));
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="bootstrap sampling with replacement">
      {Array.from({ length: 8 }, (_, i) => (
        <g key={i}>
          <rect x={20} y={10 + i * 15} width={90} height={11} rx={3}
                fill={counts.has(i) ? "#EAF4E2" : "#FBFDF9"} stroke={counts.has(i) ? LEAF : "#E4EBE1"} />
          <text x={25} y={19 + i * 15} fontSize={8} fill={MUTED}>row {i + 1}</text>
          {counts.get(i) ? (
            <text x={100} y={19 + i * 15} fontSize={8} fill="#8a6d1a" textAnchor="end">
              ×{counts.get(i)}
            </text>
          ) : null}
        </g>
      ))}
      <text x={150} y={70} fontSize={18} textAnchor="middle">🎩</text>
      {Array.from({ length: drawn }, (_, d) => (
        <rect key={d} x={190} y={12 + d * 15} width={90} height={11} rx={3} fill="#FFFDF5" stroke={GOLD} />
      ))}
      <text x={235} y={8} fontSize={8} fill={MUTED} textAnchor="middle">this tree's bag ({drawn}/8 draws)</text>
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        drawn WITH replacement: some rows repeat, ~⅓ never appear (they become the free OOB test)
      </text>
    </svg>
  );
}

/* vote-box: trees stamp votes; majority wins */
const VOTES = [1, 1, 0, 1, 0]; // five trees' votes for the demo row
function VoteBox({ progress }: WidgetProps) {
  const cast = Math.floor(progress * VOTES.length);
  const yes = VOTES.slice(0, cast).filter(Boolean).length;
  const done = cast >= VOTES.length;
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="the forest votes">
      {VOTES.map((v, i) => (
        <g key={i} opacity={i < cast ? 1 : 0.25} style={{ transition: "opacity .4s" }}>
          <text x={35 + i * 55} y={45} fontSize={22} textAnchor="middle">🌳</text>
          <rect x={20 + i * 55} y={56} width={30} height={14} rx={4}
                fill={i < cast ? (v ? "#EAF4E2" : "#FDECEA") : "#FBFDF9"}
                stroke={i < cast ? (v ? LEAF : RED) : "#E4EBE1"} />
          <text x={35 + i * 55} y={66} fontSize={9} textAnchor="middle" fill={INK}>
            {i < cast ? (v ? "yes" : "no") : "…"}
          </text>
        </g>
      ))}
      <text x={150} y={100} textAnchor="middle" fontSize={12} fill={INK}>
        tally: {yes} yes · {cast - yes} no
      </text>
      <text x={150} y={122} textAnchor="middle" fontSize={11} fill={done ? "#8a6d1a" : MUTED}>
        {done ? `majority says YES (${yes}/${VOTES.length}) — one jumpy tree can't flip the crowd` : "each tree votes from its own bag + feature menu…"}
      </text>
    </svg>
  );
}

/* weight-grow (adaboost): misclassified rows inflate between rounds */
const ADA = [
  { wrong: false }, { wrong: true }, { wrong: false }, { wrong: true },
  { wrong: false }, { wrong: false },
];
function WeightGrow({ progress }: WidgetProps) {
  const round2 = progress >= 0.5;
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="adaboost reweighting">
      {ADA.map((r, i) => {
        const h = round2 && r.wrong ? 26 : round2 ? 8 : 14;
        return (
          <g key={i}>
            <rect x={30 + i * 42} y={70 - h / 2} width={32} height={h} rx={4}
                  fill={r.wrong ? "#FDECEA" : "#EAF4E2"} stroke={r.wrong ? RED : LEAF}
                  style={{ transition: "y .6s, height .6s" }} />
            <text x={46 + i * 42} y={74} fontSize={8} textAnchor="middle" fill={INK}>
              row {i + 1}
            </text>
            {round2 && r.wrong && (
              <text x={46 + i * 42} y={44} fontSize={9} textAnchor="middle" fill={RED}>↑ weight</text>
            )}
          </g>
        );
      })}
      <text x={150} y={130} textAnchor="middle" fontSize={10} fill={MUTED}>
        {round2
          ? "after round 1: the rows stump 1 got WRONG grow — stump 2 must face them"
          : "round 1: every row carries equal weight"}
      </text>
    </svg>
  );
}

/* gp-band: prior curves collapse onto data; band narrows near points */
const GP_PTS = [[0.15, 0.62], [0.4, 0.35], [0.75, 0.55]];
function GPBand({ progress }: WidgetProps) {
  const pin = sub(progress, 0.25, 0.7);
  const X = (u: number) => 20 + u * 260;
  const Y = (v: number) => 20 + v * 100;
  const mean = (u: number) => {
    // a smooth curve through the points, weighted by proximity (illustrative kriging-lite)
    let sw = 0, s = 0;
    for (const [px, py] of GP_PTS) {
      const w = Math.exp(-(((u - px) / 0.18) ** 2));
      sw += w; s += w * py;
    }
    return sw > 0.01 ? s / sw : 0.5;
  };
  const width = (u: number) => {
    const d = Math.min(...GP_PTS.map(([px]) => Math.abs(u - px)));
    return (0.05 + 0.4 * Math.min(1, d / 0.35)) * pin + 0.38 * (1 - pin);
  };
  const N = 40;
  const top = Array.from({ length: N + 1 }, (_, i) => {
    const u = i / N;
    return `${X(u)},${Y(mean(u) - width(u))}`;
  });
  const bot = Array.from({ length: N + 1 }, (_, i) => {
    const u = (N - i) / N;
    return `${X(u)},${Y(mean(u) + width(u))}`;
  });
  const mid = Array.from({ length: N + 1 }, (_, i) => {
    const u = i / N;
    return `${X(u)},${Y(mean(u))}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="gaussian process uncertainty band">
      <polygon points={[...top, ...bot].join(" ")} fill="rgba(109,179,63,0.18)" />
      <polyline points={mid} fill="none" stroke="#14342A" strokeWidth={1.6} />
      {GP_PTS.map(([px, py], i) => (
        <circle key={i} cx={X(px)} cy={Y(py)} r={4.5} fill={GOLD} stroke="#8a6d1a"
                opacity={pin > 0.15 ? 1 : 0} style={{ transition: "opacity .4s" }} />
      ))}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {pin < 0.3 ? "the prior: a cloud of plausible functions"
          : "data pins the cloud down — the band NARROWS near points, flares between them"}
      </text>
    </svg>
  );
}

/* margin-street (svm): candidate lines audition → widest street; support vectors ringed */
const SVM_A: [number, number][] = [[50, 40], [75, 55], [60, 75], [95, 45], [85, 80]];
const SVM_B: [number, number][] = [[190, 95], [215, 75], [235, 105], [205, 115], [245, 85]];
function MarginStreet({ progress }: WidgetProps) {
  const settle = sub(progress, 0.3, 0.75);
  const angle = (1 - settle) * 0.5 * Math.sin(progress * 12); // wobbling auditions → settles
  const cx = 150, cy = 75;
  const dx = Math.cos(1.2 + angle), dy = Math.sin(1.2 + angle);
  const street = 12 + settle * 20;
  const line = (off: number, dash?: string, w = 1.5) => (
    <line
      x1={cx - dy * 140 + dx * off} y1={cy + dx * 140 + dy * off}
      x2={cx + dy * 140 + dx * off} y2={cy - dx * 140 + dy * off}
      stroke={off === 0 ? "#14342A" : GOLD} strokeWidth={off === 0 ? 2 : w} strokeDasharray={dash}
    />
  );
  const supports = settle > 0.8 ? [SVM_A[3], SVM_B[1]] : [];
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="widest-street margin">
      {line(-street, "4 3")}
      {line(0)}
      {line(street, "4 3")}
      {SVM_A.map(([x, y], i) => <circle key={`a${i}`} cx={x} cy={y} r={5} fill={LEAF} />)}
      {SVM_B.map(([x, y], i) => <circle key={`b${i}`} cx={x} cy={y} r={5} fill={RED} />)}
      {supports.map(([x, y], i) => (
        <circle key={`s${i}`} cx={x} cy={y} r={9} fill="none" stroke={GOLD} strokeWidth={2.5} />
      ))}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {settle < 0.8
          ? "lines audition — the WIDEST street between the classes wins"
          : "settled: only the ringed SUPPORT VECTORS touch the street; delete the rest, nothing moves"}
      </text>
    </svg>
  );
}

/* kernel-lift: 1-D inseparable points lift onto a parabola — a line separates them up there */
function KernelLift({ progress }: WidgetProps) {
  const lift = sub(progress, 0.25, 0.75);
  const pts = [-0.9, -0.7, -0.15, 0.05, 0.2, 0.65, 0.85];
  const cls = (v: number) => Math.abs(v) < 0.35; // inner = class A — not linearly separable in 1-D
  const X = (v: number) => 150 + v * 120;
  const Y = (v: number) => 120 - lift * (v * v) * 130;
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="the kernel trick lifts points">
      <line x1={20} y1={120} x2={280} y2={120} stroke="#E4EBE1" />
      {lift > 0.6 && <line x1={30} y1={100 - 25 * lift} x2={270} y2={100 - 25 * lift} stroke={GOLD} strokeWidth={2} strokeDasharray="5 3" />}
      {pts.map((v, i) => (
        <circle key={i} cx={X(v)} cy={Y(v)} r={5.5} fill={cls(v) ? LEAF : RED}
                style={{ transition: "cy .5s ease" }} />
      ))}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {lift < 0.3 ? "on the line, no single cut separates green from red"
          : lift < 0.6 ? "the kernel LIFTS each point by x² — no new features ever computed explicitly"
          : "up here one straight cut works; back down it lands as a curved boundary"}
      </text>
    </svg>
  );
}

/* bayes-race: per-feature likelihoods multiply, class vs class */
const NB_STEPS = [
  { f: "age=61", a: 0.8, b: 0.3 },
  { f: "bp=148", a: 0.7, b: 0.4 },
  { f: "chol=270", a: 0.6, b: 0.5 },
];
function BayesRace({ progress }: WidgetProps) {
  const k = Math.max(1, Math.ceil(progress * NB_STEPS.length));
  const prodA = NB_STEPS.slice(0, k).reduce((s, x) => s * x.a, 0.5);
  const prodB = NB_STEPS.slice(0, k).reduce((s, x) => s * x.b, 0.5);
  const W = (v: number) => Math.max(2, v * 240);
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="naive bayes likelihood race">
      {NB_STEPS.map((s, i) => (
        <text key={i} x={150} y={16 + i * 14} textAnchor="middle" fontSize={9}
              fill={i < k ? "#8a6d1a" : "#E4EBE1"}>
          × P({s.f} | class) — sick {s.a} · healthy {s.b}
        </text>
      ))}
      <text x={20} y={80} fontSize={9} fill={INK}>sick</text>
      <rect x={50} y={72} width={W(prodA)} height={12} rx={3} fill={RED}
            style={{ transition: "width .5s" }} />
      <text x={20} y={104} fontSize={9} fill={INK}>healthy</text>
      <rect x={50} y={96} width={W(prodB)} height={12} rx={3} fill={LEAF}
            style={{ transition: "width .5s" }} />
      <text x={150} y={140} textAnchor="middle" fontSize={10} fill={MUTED}>
        prior × each feature's likelihood, one at a time — the taller product wins the argmax
      </text>
    </svg>
  );
}

/* dbscan-grow: ε-circles chain-react through two shapes; loners stamped noise */
const DB_C1: [number, number][] = [[60, 50], [78, 42], [95, 50], [108, 62], [90, 70], [72, 64]];
const DB_C2: [number, number][] = [[190, 100], [208, 92], [225, 100], [210, 112], [193, 110]];
const DB_NOISE: [number, number][] = [[260, 30], [40, 115]];
function DbscanGrow({ progress }: WidgetProps) {
  const total = DB_C1.length + DB_C2.length;
  const lit = Math.floor(sub(progress, 0.1, 0.85) * total);
  const stampNoise = progress > 0.9;
  const pt = ([x, y]: [number, number], i: number, color: string, on: boolean) => (
    <g key={`${x}${y}${i}`}>
      {on && <circle cx={x} cy={y} r={16} fill="none" stroke={color} strokeOpacity={0.35} />}
      <circle cx={x} cy={y} r={5} fill={on ? color : "#C7D2C9"} style={{ transition: "fill .4s" }} />
    </g>
  );
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="dbscan region growing">
      {DB_C1.map((p, i) => pt(p, i, "#2E6C8E", i < lit))}
      {DB_C2.map((p, i) => pt(p, i, LEAF, DB_C1.length + i < lit))}
      {DB_NOISE.map(([x, y], i) => (
        <g key={`n${i}`}>
          <circle cx={x} cy={y} r={5} fill={stampNoise ? "#9AA59C" : "#C7D2C9"} />
          {stampNoise && <text x={x} y={y - 9} fontSize={8} textAnchor="middle" fill={MUTED}>noise</text>}
        </g>
      ))}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {lit < total
          ? "a core point ignites; anything within ε chain-reacts — the cluster GROWS"
          : "two clusters found, any shape — the loners are honestly stamped NOISE"}
      </text>
    </svg>
  );
}

/* gmm-ellipses: E-step responsibilities + M-step ellipses re-fitting */
function GmmEllipses({ progress }: WidgetProps) {
  const t = sub(progress, 0.2, 0.8);
  const share = 0.75 - 0.35 * t; // the border point's soft membership sharpens
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="gaussian mixture EM">
      <ellipse cx={95} cy={70} rx={55 - 12 * t} ry={34 - 6 * t}
               transform={`rotate(${-18 * t} 95 70)`}
               fill="rgba(46,108,142,0.15)" stroke="#2E6C8E" style={{ transition: "all .5s" }} />
      <ellipse cx={205} cy={82} rx={50 - 8 * t} ry={30 - 4 * t}
               transform={`rotate(${14 * t} 205 82)`}
               fill="rgba(109,179,63,0.15)" stroke={LEAF} style={{ transition: "all .5s" }} />
      {[[70, 60], [95, 82], [112, 58]].map(([x, y], i) => <circle key={`a${i}`} cx={x} cy={y} r={4.5} fill="#2E6C8E" />)}
      {[[195, 75], [220, 92], [232, 70]].map(([x, y], i) => <circle key={`b${i}`} cx={x} cy={y} r={4.5} fill={LEAF} />)}
      {/* the border point wears its responsibilities as a pie */}
      <g transform="translate(150,76)">
        <circle r={7} fill={LEAF} />
        <path d={`M0,0 L0,-7 A7,7 0 ${share > 0.5 ? 1 : 0} 1 ${7 * Math.sin(2 * Math.PI * share)},${-7 * Math.cos(2 * Math.PI * share)} Z`} fill="#2E6C8E" />
      </g>
      <text x={150} y={104} textAnchor="middle" fontSize={9} fill={INK}>
        {Math.round(share * 100)}% blue / {Math.round((1 - share) * 100)}% green
      </text>
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        E-step: every point gets SOFT memberships · M-step: ellipses re-centre, re-shape, re-tilt
      </text>
    </svg>
  );
}

/* dendro-zip: closest pairs merge; the dendrogram grows */
const MERGES = [
  { label: "1+2", h: 22 }, { label: "4+5", h: 30 }, { label: "(1,2)+3", h: 55 },
  { label: "(4,5)+6", h: 66 }, { label: "all", h: 100 },
];
function DendroZip({ progress }: WidgetProps) {
  const done = Math.floor(sub(progress, 0.05, 0.95) * MERGES.length);
  const xs = [40, 70, 100, 180, 210, 240];
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="hierarchical dendrogram growing">
      {xs.map((x, i) => <circle key={i} cx={x} cy={120} r={5} fill={i < 3 ? "#2E6C8E" : LEAF} />)}
      {/* merge brackets appear bottom-up */}
      {done >= 1 && <path d="M40 112 V98 H70 V112" fill="none" stroke={INK} />}
      {done >= 2 && <path d="M180 112 V90 H210 V112" fill="none" stroke={INK} />}
      {done >= 3 && <path d="M55 98 V65 H100 V112" fill="none" stroke={INK} />}
      {done >= 4 && <path d="M195 90 V54 H240 V112" fill="none" stroke={INK} />}
      {done >= 5 && <path d="M77 65 V20 H217 V54" fill="none" stroke={GOLD} strokeWidth={2} />}
      <line x1={20} y1={78} x2={280} y2={78} stroke={GOLD} strokeDasharray="5 4" opacity={done >= 4 ? 1 : 0} />
      <text x={276} y={72} fontSize={8} fill="#8a6d1a" textAnchor="end" opacity={done >= 4 ? 1 : 0}>
        cut here → 2 clusters
      </text>
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {done < MERGES.length
          ? `closest pair zips together (merge ${Math.max(1, done)}: ${MERGES[Math.max(0, done - 1)].label}) — height = how far apart they were`
          : "the full dendrogram — slide a cut line to choose your number of clusters"}
      </text>
    </svg>
  );
}

/* spectral-jump: two tangled rings morph into two separable blobs */
function SpectralJump({ progress }: WidgetProps) {
  const t = sub(progress, 0.3, 0.8);
  const N = 10;
  const pts: { x: number; y: number; c: string }[] = [];
  for (let i = 0; i < N; i++) {
    const a = (i / N) * Math.PI * 2;
    // outer ring → left blob; inner ring → right blob
    pts.push({
      x: (150 + 52 * Math.cos(a)) * (1 - t) + (80 + 12 * Math.cos(a)) * t,
      y: (75 + 40 * Math.sin(a)) * (1 - t) + (70 + 12 * Math.sin(a)) * t,
      c: "#2E6C8E",
    });
    pts.push({
      x: (150 + 20 * Math.cos(a)) * (1 - t) + (220 + 12 * Math.cos(a)) * t,
      y: (75 + 15 * Math.sin(a)) * (1 - t) + (78 + 12 * Math.sin(a)) * t,
      c: LEAF,
    });
  }
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="spectral embedding jump">
      {pts.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={4} fill={p.c} style={{ transition: "cx .3s, cy .3s" }} />
      ))}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {t < 0.5
          ? "a ring inside a ring — k-means would cut straight through both"
          : "in the eigenvector embedding the tangle becomes two plain blobs — now k-means finishes"}
      </text>
    </svg>
  );
}

/* isolation-cuts: random slices box the loner fast, the crowd point slowly */
const ISO_CUTS = [
  { v: true, at: 218 }, { v: false, at: 42 }, { v: true, at: 250 },
];
function IsolationCuts({ progress }: WidgetProps) {
  const k = Math.floor(sub(progress, 0.15, 0.85) * ISO_CUTS.length);
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="isolation forest random cuts">
      {[[70, 60], [88, 72], [102, 55], [80, 90], [110, 78], [95, 100]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={5} fill={LEAF} />
      ))}
      <circle cx={235} cy={50} r={6} fill={RED} />
      <text x={235} y={36} fontSize={8} textAnchor="middle" fill={RED}>the loner</text>
      {ISO_CUTS.slice(0, k).map((c, i) =>
        c.v ? (
          <line key={i} x1={c.at} y1={10} x2={c.at} y2={140} stroke={GOLD} strokeWidth={1.6} strokeDasharray="6 4" />
        ) : (
          <line key={i} x1={10} y1={c.at} x2={290} y2={c.at} stroke={GOLD} strokeWidth={1.6} strokeDasharray="6 4" />
        ),
      )}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {k < 2
          ? "random cuts slice the space…"
          : `the loner is boxed in after ${Math.min(k, 3)} cuts — the crowd would need many more. Short path = suspicious`}
      </text>
    </svg>
  );
}

/* density-rings (LOF): my crowdedness vs my neighbours' */
function DensityRings({ progress }: WidgetProps) {
  const on = sub(progress, 0.25, 0.7);
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="local outlier factor densities">
      {[[70, 60], [86, 70], [100, 56], [82, 86], [108, 74]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={5} fill={LEAF} />
      ))}
      {on > 0.3 && <circle cx={89} cy={70} r={30} fill="none" stroke={LEAF} strokeOpacity={0.5} />}
      <circle cx={215} cy={75} r={5.5} fill={RED} />
      {on > 0.6 && <circle cx={215} cy={75} r={52} fill="none" stroke={RED} strokeOpacity={0.5} strokeDasharray="4 3" />}
      {[[245, 45], [255, 100]].map(([x, y], i) => <circle key={`s${i}`} cx={x} cy={y} r={4.5} fill={MUTED} />)}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {on < 0.6
          ? "downtown: everyone's neighbourhood ring is tight"
          : "the red point needs a HUGE ring to find neighbours — much sparser than THEY are → LOF ≫ 1"}
      </text>
    </svg>
  );
}

/* shrink-wrap (one-class svm): the boundary tightens around normal */
function ShrinkWrap({ progress }: WidgetProps) {
  const t = sub(progress, 0.2, 0.8);
  const r = 95 - 42 * t;
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="one-class svm boundary shrinking">
      {[[130, 65], [150, 78], [168, 60], [140, 92], [162, 88], [150, 70]].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={5} fill={LEAF} />
      ))}
      <circle cx={255} cy={40} r={5.5} fill={RED} />
      <ellipse cx={150} cy={76} rx={r} ry={r * 0.62} fill="none" stroke={GOLD} strokeWidth={2}
               strokeDasharray="7 4" style={{ transition: "rx .4s, ry .4s" }} />
      {t > 0.8 && <text x={255} y={26} fontSize={8} textAnchor="middle" fill={RED}>outside → anomaly</text>}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {t < 0.7
          ? "the boundary shrink-wraps the NORMAL cloud (ν controls the looseness)"
          : "settled: whatever falls outside the wrap is flagged — so the training data must be clean"}
      </text>
    </svg>
  );
}

/* decompose-stack (ETS): the series peels into level + trend + season */
function DecomposeStack({ progress }: WidgetProps) {
  const t = sub(progress, 0.2, 0.8);
  const N = 40;
  const path = (fn: (i: number) => number, y0: number, color: string) => (
    <polyline
      points={Array.from({ length: N }, (_, i) => `${20 + i * 6.6},${y0 - fn(i)}`).join(" ")}
      fill="none" stroke={color} strokeWidth={1.6}
    />
  );
  const season = (i: number) => 8 * Math.sin(i / 2.4);
  const trend = (i: number) => i * 0.55;
  const full = (i: number) => 20 + trend(i) * 0.5 + season(i) * 0.8;
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="series decomposing into components">
      {t < 0.35 ? (
        path(full, 110, "#14342A")
      ) : (
        <>
          {path(() => 12, 42, MUTED)}
          <text x={286} y={32} fontSize={8} fill={MUTED} textAnchor="end">level</text>
          {path((i) => trend(i) * 0.5, 92, "#2E6C8E")}
          <text x={286} y={72} fontSize={8} fill="#2E6C8E" textAnchor="end">trend</text>
          {path(season, 128, LEAF)}
          <text x={286} y={116} fontSize={8} fill={LEAF} textAnchor="end">season</text>
        </>
      )}
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {t < 0.35 ? "one tangled series…" : "…is level + trend + season — ETS updates each with fading memory, then re-adds them forward"}
      </text>
    </svg>
  );
}

/* differencing (ARIMA/SARIMA): subtract yesterday, the trend flattens */
function Differencing({ progress }: WidgetProps) {
  const t = sub(progress, 0.25, 0.75);
  const N = 40;
  const raw = (i: number) => 20 + i * 1.7 + 9 * Math.sin(i / 3);
  const diff = (i: number) => (i === 0 ? 0 : raw(i) - raw(i - 1)) * 4;
  const pts = Array.from({ length: N }, (_, i) => {
    const y = raw(i) * (1 - t) + (55 + diff(i)) * t;
    return `${20 + i * 6.6},${130 - y * 0.75}`;
  }).join(" ");
  return (
    <svg viewBox="0 0 300 150" width="100%" role="img" aria-label="differencing flattens the trend">
      <line x1={20} y1={130 - 55 * 0.75} x2={284} y2={130 - 55 * 0.75} stroke="#E4EBE1" />
      <polyline points={pts} fill="none" stroke={t > 0.5 ? LEAF : "#14342A"} strokeWidth={1.8}
                style={{ transition: "stroke .4s" }} />
      <text x={150} y={144} textAnchor="middle" fontSize={10} fill={MUTED}>
        {t < 0.5
          ? "the raw series drifts upward — its mean never settles (non-stationary)"
          : "value(t) − value(t−1): the drift is gone (d = 1) — NOW the AR/MA machinery can see the pattern"}
      </text>
    </svg>
  );
}

export const WIDGETS: Record<string, ComponentType<WidgetProps>> = {
  "hessian-bowl": HessianBowl,
  "sigmoid-squeeze": SigmoidSqueeze,
  "gini-balls": GiniBalls,
  "impurity-curve": ImpurityCurve,
  "surprise-curve": SurpriseCurve,
  "g-cancel": GCancel,
  "fe-demean": FEDemean,
  "bootstrap-hat": BootstrapHat,
  "vote-box": VoteBox,
  "weight-grow": WeightGrow,
  "gp-band": GPBand,
  "margin-street": MarginStreet,
  "kernel-lift": KernelLift,
  "bayes-race": BayesRace,
  "dbscan-grow": DbscanGrow,
  "gmm-ellipses": GmmEllipses,
  "dendro-zip": DendroZip,
  "spectral-jump": SpectralJump,
  "isolation-cuts": IsolationCuts,
  "density-rings": DensityRings,
  "shrink-wrap": ShrinkWrap,
  "decompose-stack": DecomposeStack,
  "differencing": Differencing,
};
