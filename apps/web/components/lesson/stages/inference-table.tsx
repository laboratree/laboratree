"use client";

import type { InferenceTable } from "@/lib/api";
import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

/** The econometrics inference table — coefficient, SE, t/z, p, and an animated 95% CI bar.
 *  Intervals that cross zero glow red: 'no effect' can't be ruled out. */
export default function InferenceTableStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const inf = (lesson.trace.series as { inference?: InferenceTable } | null)?.inference;
  const rows = (inf?.rows ?? []).filter((r) => r.feature !== "intercept");
  const shown = useSubstep(clock, entryIdx, Math.max(1, rows.length));
  const visible = reducedMotion ? rows.length : shown;
  if (!inf || !rows.length)
    return <p className="text-xs text-muted">No inference table for this fit.</p>;

  const span = Math.max(0.0001, ...rows.map((r) => Math.max(Math.abs(r.ci_lo), Math.abs(r.ci_hi))));
  const X = (v: number) => 50 + (v / span) * 45; // −span..span → 5..95 (%)

  return (
    <div>
      <p className="mb-1 text-[10px] text-muted">
        n = {inf.n} · {inf.fit.name} = {inf.fit.value} · statistic = {inf.stat_name}
        {inf.exp_reading ? ` · e^β = ${inf.exp_reading}` : ""}
      </p>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="min-w-full text-[11px]">
          <thead className="bg-bg">
            <tr>
              {["variable", "coef", "SE", inf.stat_name, "p", "95% CI", ...(inf.exp_reading ? [inf.exp_reading] : [])].map(
                (h) => (
                  <th key={h} className="whitespace-nowrap px-2 py-1 text-left font-medium text-muted">
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const crosses = r.ci_lo <= 0 && r.ci_hi >= 0;
              const sig = r.p < 0.001 ? "***" : r.p < 0.01 ? "**" : r.p < 0.05 ? "*" : "";
              return (
                <tr
                  key={r.feature}
                  className="border-t border-line/60"
                  style={{
                    opacity: i < visible ? 1 : 0,
                    transition: reducedMotion ? undefined : "opacity .4s ease",
                  }}
                >
                  <td className="whitespace-nowrap px-2 py-1 font-medium text-forest">{r.feature}</td>
                  <td className="px-2 py-1 font-mono text-ink">{r.coef}</td>
                  <td className="px-2 py-1 font-mono text-muted">{r.se}</td>
                  <td className="px-2 py-1 font-mono text-ink">{r.stat}</td>
                  <td className={`px-2 py-1 font-mono ${r.p < 0.05 ? "text-green-700" : "text-red-600"}`}>
                    {r.p}
                    {sig}
                  </td>
                  <td className="px-2 py-1" style={{ minWidth: 130 }}>
                    <svg viewBox="0 0 100 12" width={130} height={14} aria-label="confidence interval">
                      <line x1={50} y1={0} x2={50} y2={12} stroke="#E4EBE1" />
                      <line
                        x1={X(r.ci_lo)} y1={6} x2={X(r.ci_hi)} y2={6}
                        stroke={crosses ? "#C0392B" : "#6DB33F"} strokeWidth={3} strokeLinecap="round"
                        style={{ transition: "x1 .5s, x2 .5s" }}
                      />
                      <circle cx={X(r.coef)} cy={6} r={2.6} fill={crosses ? "#C0392B" : "#14342A"} />
                    </svg>
                  </td>
                  {inf.exp_reading && (
                    <td className="px-2 py-1 font-mono text-[#8a6d1a]">{r.exp_coef ?? "—"}</td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-1 text-[10px] text-muted">
        <span className="text-green-700">green CI</span> = zero excluded ·{" "}
        <span className="text-red-600">red CI crosses zero</span> = can&apos;t rule out no effect ·
        stars: * p&lt;.05 ** p&lt;.01 *** p&lt;.001
      </p>
    </div>
  );
}
