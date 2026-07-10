"use client";

import { useState, type ComponentType } from "react";
import type { ModelTrace, TestRow } from "@/lib/api";

/** ONE results table of all held-out rows; click a row to watch its prediction being made below
 *  (renders the family's per-row Test walkthrough). Shared by the lesson player and classic view. */
export function TestTable({
  trace,
  rows,
  rowIdx,
  setRowIdx,
  Test,
  hint,
}: {
  trace: ModelTrace;
  rows: TestRow[];
  rowIdx: number;
  setRowIdx: (i: number) => void;
  Test: ComponentType<{ trace: ModelTrace; row: TestRow; hint?: string }>;
  hint?: string;
}) {
  const [wave, setWave] = useState(0); // bump to replay the reveal animation
  // every feature column the rows carry (the table scrolls horizontally)
  const feats = Object.keys(rows[0]?.values ?? {});
  const row = rows[Math.min(rowIdx, rows.length - 1)];
  const unsupervised = rows.every((r) => r.actual == null);

  const resultCell = (r: TestRow) => {
    if (r.actual == null)
      return <span className="font-medium text-forest">{String(r.predicted)}</span>;
    if (r.correct != null)
      return (
        <span className={`font-semibold ${r.correct ? "text-green-700" : "text-red-600"}`}>
          {r.correct ? "✓ correct" : "✗ wrong"}
        </span>
      );
    const e = r.error ?? 0;
    return (
      <span className={`font-semibold ${Math.abs(e) < 5 ? "text-green-700" : "text-red-600"}`}>
        {e > 0 ? "+" : ""}
        {e}
      </span>
    );
  };

  return (
    <div className="space-y-2">
      <style>{`@keyframes mvRowIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }`}</style>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted">
          All {rows.length} held-out rows at a glance — <b>click a row</b> to watch its prediction
          being made below.
        </span>
        <button
          onClick={() => setWave((w) => w + 1)}
          className="rounded border border-line px-2 py-0.5 text-forest hover:bg-bg"
        >
          ↻ replay
        </button>
      </div>

      <div className="overflow-auto rounded-lg border border-line bg-white" style={{ maxHeight: 230 }}>
        <table className="min-w-full text-[11px]">
          <thead className="sticky top-0 bg-bg">
            <tr>
              <th className="px-2 py-1 text-left font-medium text-muted">#</th>
              {feats.map((f) => (
                <th key={f} className="whitespace-nowrap px-2 py-1 text-left font-medium text-forest">
                  {f}
                </th>
              ))}
              <th className="whitespace-nowrap px-2 py-1 text-left font-medium text-[#B8860B]">
                predicted
              </th>
              {!unsupervised && (
                <th className="whitespace-nowrap px-2 py-1 text-left font-medium text-[#B8860B]">
                  actual
                </th>
              )}
              <th className="whitespace-nowrap px-2 py-1 text-left font-medium text-muted">
                {unsupervised ? "" : trace.task === "classification" ? "result" : "error"}
              </th>
            </tr>
          </thead>
          <tbody key={wave}>
            {rows.map((r, i) => {
              const sel = i === rowIdx;
              const tint =
                r.actual == null
                  ? ""
                  : (r.correct ?? Math.abs(r.error ?? 0) < 5)
                    ? "bg-green-50/60"
                    : "bg-red-50/60";
              return (
                <tr
                  key={i}
                  onClick={() => setRowIdx(i)}
                  className={`cursor-pointer border-t border-line/60 transition hover:bg-bg ${tint} ${
                    sel ? "outline outline-2 -outline-offset-2 outline-[#C9A227]" : ""
                  }`}
                  style={{ animation: "mvRowIn .35s both", animationDelay: `${i * 130}ms` }}
                >
                  <td className="px-2 py-1 text-muted">{i + 1}</td>
                  {feats.map((f) => (
                    <td key={f} className="whitespace-nowrap px-2 py-1 text-ink">
                      {r.values[f] ?? "—"}
                    </td>
                  ))}
                  <td className="whitespace-nowrap px-2 py-1 font-medium text-ink">
                    {String(r.predicted)}
                  </td>
                  {!unsupervised && (
                    <td className="whitespace-nowrap px-2 py-1 text-ink">{String(r.actual)}</td>
                  )}
                  <td className="whitespace-nowrap px-2 py-1">{resultCell(r)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {row && (
        <div className="rounded-lg border border-[#C9A227]/50 bg-[#FFFDF5] p-2">
          <p className="mb-1.5 text-[11px] font-medium text-[#8a6d1a]">
            How row {rowIdx + 1} was predicted:
          </p>
          <Test trace={trace} row={row} hint={hint} />
        </div>
      )}
    </div>
  );
}
