"use client";

import { useSmoothProgress } from "../clock";
import type { LessonStageProps } from "./types";

/** The table TRANSFORMS between rounds: predictions move, residuals shrink, and the residual
 *  column takes the gold "new target" crown — this is what the next tree trains on. */
export default function ResidualMorphStage({ lesson, step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const ref = step.anim?.ref ?? {};
  const fromIdx = typeof ref.from === "number" ? ref.from : 0;
  const toIdx = typeof ref.to === "number" ? ref.to : fromIdx + 1;
  const rounds = lesson.trace.boosting?.rounds ?? [];
  const from = rounds[fromIdx]?.table ?? [];
  const to = rounds[toIdx]?.table ?? from;
  const progress = useSmoothProgress(clock, entryIdx);
  const p = reducedMotion ? 1 : progress;
  const morphed = p >= 0.5; // first half: before; second half: after the η update
  const table = morphed ? to : from;
  if (!from.length) return <p className="text-xs text-muted">No round tables available.</p>;

  const cols = Object.keys(from[0]).filter((c) => c !== "g" && c !== "h");
  return (
    <div>
      <p className="mb-1 text-[11px] font-medium text-[#8a6d1a]">
        {morphed
          ? `AFTER tree ${fromIdx + 1} (× η): predictions moved, residuals shrank — the residual column IS round ${toIdx + 1}'s target`
          : `BEFORE the update: what round ${fromIdx + 1} trained on`}
      </p>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="min-w-full text-[11px]">
          <thead className="bg-bg">
            <tr>
              {cols.map((c) => (
                <th
                  key={c}
                  className={`whitespace-nowrap px-2 py-1 text-left font-medium transition-colors duration-500 ${
                    c === "residual" && morphed
                      ? "bg-[#FBF3D6] text-[#B8860B]"
                      : c === "residual" ? "text-red-700"
                        : c === "current" ? "text-[#B8860B]"
                          : c === "actual" ? "text-forest" : "text-muted"
                  }`}
                >
                  {c === "residual" && morphed ? "★ residual (new target)" : c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.map((row, i) => (
              <tr key={i} className="border-t border-line/60">
                {cols.map((c) => {
                  const changed =
                    morphed && String(from[i]?.[c]) !== String(to[i]?.[c]);
                  return (
                    <td
                      key={c}
                      className={`whitespace-nowrap px-2 py-1 font-mono transition-colors duration-500 ${
                        c === "residual" && morphed ? "bg-[#FFFDF5] font-semibold text-[#8a6d1a]"
                          : changed ? "bg-leaf/10 text-forest" : "text-ink"
                      }`}
                    >
                      {String(row[c])}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-1 h-1.5 w-full rounded bg-bg">
        <div className="h-1.5 rounded bg-[#C9A227] transition-all" style={{ width: `${p * 100}%` }} />
      </div>
    </div>
  );
}
