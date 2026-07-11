"use client";

import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

/** The live data table — rows surface one by one under the clock; outcome column in gold. */
export default function DataTableStage({ step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const table = step.table;
  const total = table?.rows.length ?? 0;
  const shown = useSubstep(clock, entryIdx, Math.max(1, total));
  const visible = reducedMotion ? total : shown;

  if (!table || total === 0)
    return <p className="text-xs text-muted">No sample rows available for this dataset.</p>;

  const isTarget = (c: string) => c === table.target_col;
  const isHl = (c: string) => table.highlight_cols.includes(c);

  return (
    <div>
      {table.caption && <p className="mb-1 text-[11px] text-muted">{table.caption}</p>}
      <div className="overflow-auto rounded-lg border border-line bg-white" style={{ maxHeight: 260 }}>
        <table className="min-w-full text-[11px]">
          <thead className="sticky top-0 bg-bg">
            <tr>
              {table.columns.map((c) => (
                <th
                  key={c}
                  className={`whitespace-nowrap px-2 py-1 text-left font-medium ${
                    isTarget(c) ? "bg-[#FBF3D6] text-[#B8860B]" : isHl(c) ? "text-leaf" : "text-forest"
                  }`}
                >
                  {isTarget(c) ? `★ ${c}` : c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((r, i) => (
              <tr
                key={i}
                className="border-t border-line/60"
                style={{
                  opacity: i < visible ? 1 : 0,
                  transform: i < visible ? "none" : "translateY(4px)",
                  transition: reducedMotion ? undefined : "opacity .4s ease, transform .4s ease",
                }}
              >
                {table.columns.map((c) => (
                  <td
                    key={c}
                    className={`whitespace-nowrap px-2 py-1 ${
                      isTarget(c) ? "bg-[#FFFDF5] font-medium text-[#8a6d1a]" : "text-ink"
                    }`}
                  >
                    {r[c] != null ? String(r[c]) : "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-1 text-right font-mono text-[10px] text-muted">
        {Math.min(visible, total)} / {total} rows
      </p>
    </div>
  );
}
