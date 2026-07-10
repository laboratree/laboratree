"use client";

import type { VolatilityMechanism } from "@/lib/api";
import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

/** Real returns as bars with the fitted conditional-volatility band riding underneath —
 *  it swells in turbulent stretches and settles in calm ones (volatility clustering). */
export default function VolatilityRealStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const m = (lesson.trace.series as { mechanism?: VolatilityMechanism } | null)?.mechanism;
  if (!m) return <p className="text-xs text-muted">No volatility fit for this data.</p>;
  const T = m.returns.length;
  const k = useSubstep(clock, entryIdx, Math.max(1, T));
  const shown = reducedMotion ? T : k;

  const W = 300, H = 130, mid = 70;
  const rmax = Math.max(...m.returns.map(Math.abs), 0.1);
  const vmax = Math.max(...m.vol, 0.1);
  const X = (i: number) => 10 + (i / Math.max(1, T - 1)) * (W - 20);
  const bw = Math.max(1, (W - 20) / T - 0.5);

  // the volatility band as ± area
  const bandTop = m.vol.slice(0, shown).map((v, i) => `${X(i)},${mid - (v / vmax) * 55}`);
  const bandBot = m.vol.slice(0, shown).map((v, i) => `${X(i)},${mid + (v / vmax) * 55}`).reverse();

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ maxHeight: 240 }}
           role="img" aria-label="returns with conditional volatility band">
        {shown > 1 && (
          <polygon points={[...bandTop, ...bandBot].join(" ")} fill="rgba(201,162,39,0.16)"
                   stroke="#C9A227" strokeWidth={0.8} strokeOpacity={0.5} />
        )}
        {m.returns.slice(0, shown).map((r, i) => (
          <rect key={i} x={X(i) - bw / 2} y={r >= 0 ? mid - (r / rmax) * 55 : mid}
                width={bw} height={Math.max(0.5, (Math.abs(r) / rmax) * 55)}
                fill={Math.abs(r) > rmax * 0.55 ? "#C0392B" : "#5B6B60"} opacity={0.75} />
        ))}
        <line x1={10} y1={mid} x2={W - 10} y2={mid} stroke="#E4EBE1" />
        <text x={12} y={12} fontSize={9} fill="#5B6B60">returns (bars) · conditional volatility (gold band)</text>
      </svg>
      <p className="text-[10px] text-muted">
        {m.kind === "garch" ? "GARCH(1,1)" : "ARCH(1)"}: ω={m.omega} · α={m.alpha}
        {m.kind === "garch" ? ` · β=${m.beta}` : ""} · persistence α+β ={" "}
        <b className="text-forest">{m.persistence}</b>{" "}
        {m.persistence > 0.9 ? "→ shocks linger for a long time" : "→ volatility mean-reverts quickly"}.
        The band is a live risk forecast riding the clustering.
      </p>
    </div>
  );
}
