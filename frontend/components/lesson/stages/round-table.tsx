"use client";

import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

const GH_HINT: Record<string, string> = {
  actual: "the truth",
  current: "prediction so far",
  residual: "truth − prediction",
  g: "gradient (the push)",
  h: "hessian (the weight)",
};

/** The training table as one boosting round actually sees it — rows surface one by one with
 *  actual / current / residual / g / h computed live. */
export default function RoundTableStage({ lesson, step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const ref = step.anim?.ref ?? {};
  const round = typeof ref.round === "number" ? ref.round : 0;
  const table = lesson.trace.boosting?.rounds?.[round]?.table ?? [];
  const shown = useSubstep(clock, entryIdx, Math.max(1, table.length));
  const visible = reducedMotion ? table.length : shown;
  if (!table.length) return <p className="text-xs text-muted">No round table available.</p>;

  const cols = Object.keys(table[0]);
  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-line bg-white">
        <table className="min-w-full text-[11px]">
          <thead className="bg-bg">
            <tr>
              {cols.map((c) => (
                <th
                  key={c}
                  title={GH_HINT[c]}
                  className={`whitespace-nowrap px-2 py-1 text-left font-medium ${
                    c === "residual" ? "text-red-700"
                      : c === "g" || c === "h" ? "text-[#8a6d1a]"
                        : c === "current" ? "text-[#B8860B]"
                          : c === "actual" ? "text-forest" : "text-muted"
                  }`}
                >
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.map((row, i) => (
              <tr
                key={i}
                className="border-t border-line/60"
                style={{
                  opacity: i < visible ? 1 : 0,
                  transition: reducedMotion ? undefined : "opacity .4s ease",
                }}
              >
                {cols.map((c) => (
                  <td
                    key={c}
                    className={`whitespace-nowrap px-2 py-1 font-mono ${
                      c === "residual"
                        ? Math.abs(Number(row[c])) < 0.15 ? "text-green-700" : "text-red-600"
                        : c === "g" || c === "h" ? "text-[#8a6d1a]" : "text-ink"
                    }`}
                  >
                    {String(row[c])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-1 text-[10px] text-muted">
        <b className="text-[#8a6d1a]">g</b> and <b className="text-[#8a6d1a]">h</b> are computed
        per row from the current prediction — hover the headers for what each column means.
      </p>
    </div>
  );
}
