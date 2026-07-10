"use client";

import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

type ConvDemo = {
  grid: number[][];
  kernel: number[][];
  fmap: number[][];
  relu: number[][];
  pooled: number[][];
  feature_names: string[];
};

function convOf(series: Record<string, unknown> | null | undefined): ConvDemo | null {
  const c = series?.conv as ConvDemo | undefined;
  return c?.grid ? c : null;
}

const CELL = 34;

function Grid({
  m,
  x0,
  y0,
  hl,
  tone = "#1E2A22",
  fillFor,
}: {
  m: number[][];
  x0: number;
  y0: number;
  hl?: { i: number; j: number; size: number } | null;
  tone?: string;
  fillFor?: (v: number, visible: boolean) => string;
}) {
  return (
    <>
      {m.map((row, i) =>
        row.map((v, j) => (
          <g key={`${i}-${j}`}>
            <rect
              x={x0 + j * CELL} y={y0 + i * CELL} width={CELL - 2} height={CELL - 2} rx={4}
              fill={fillFor ? fillFor(v, true) : `rgba(109,179,63,${Math.min(1, Math.abs(v))})`}
              stroke="#E4EBE1"
            />
            <text x={x0 + j * CELL + CELL / 2 - 1} y={y0 + i * CELL + CELL / 2 + 3}
                  textAnchor="middle" fontSize={9} fill={tone}>
              {v}
            </text>
          </g>
        )),
      )}
      {hl && (
        <rect
          x={x0 + hl.j * CELL - 2} y={y0 + hl.i * CELL - 2}
          width={hl.size * CELL + 2} height={hl.size * CELL + 2} rx={5}
          fill="none" stroke="#C9A227" strokeWidth={2.5}
          style={{ transition: "x .35s ease, y .35s ease" }}
        />
      )}
    </>
  );
}

/** The kernel physically slides across the (real) grid; each stop's multiply-accumulate is
 *  spelled out and the feature map fills in behind it. */
export function ConvSlideStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const conv = convOf(lesson.trace.series);
  const n = conv ? conv.fmap.length : 0;
  const k = useSubstep(clock, entryIdx, Math.max(1, n * n));
  const pos = reducedMotion ? n * n : k;
  if (!conv) return <p className="text-xs text-muted">No convolution demo for this data.</p>;

  const cur = Math.max(0, Math.min(n * n, pos) - 1);
  const ci = Math.floor(cur / n);
  const cj = cur % n;
  const patch = [conv.grid[ci].slice(cj, cj + 2), conv.grid[ci + 1].slice(cj, cj + 2)];
  const terms = patch.flatMap((r, i) => r.map((v, j) => `${v}·${conv.kernel[i][j]}`));

  return (
    <div className="flex flex-wrap items-start gap-4">
      <svg viewBox="0 0 330 150" width={330} role="img" aria-label="kernel sliding over the grid">
        <Grid m={conv.grid} x0={4} y0={6} hl={{ i: ci, j: cj, size: 2 }} />
        <text x={4} y={150} fontSize={9} fill="#5B6B60">your row as a grid ({conv.feature_names.length} features)</text>
        <Grid
          m={conv.fmap} x0={200} y0={22}
          fillFor={(v, _vis) => `rgba(201,162,39,${Math.min(1, Math.abs(v) / 2)})`}
          hl={null}
        />
        {/* mask not-yet-computed fmap cells */}
        {conv.fmap.map((row, i) =>
          row.map((_v, j) =>
            i * n + j < pos ? null : (
              <rect key={`m${i}${j}`} x={200 + j * CELL} y={22 + i * CELL}
                    width={CELL - 2} height={CELL - 2} rx={4} fill="#FBFDF9" stroke="#E4EBE1" />
            ),
          ),
        )}
        <text x={200} y={150} fontSize={9} fill="#5B6B60">feature map fills in</text>
      </svg>
      <div className="min-w-[190px] flex-1">
        <p className="text-[10px] font-medium uppercase tracking-wide text-[#8a6d1a]">
          stop {Math.min(pos, n * n)} of {n * n}
        </p>
        <div className="mt-1 rounded-lg border border-line bg-white p-2">
          <p className="mb-1 text-[10px] text-muted">the 2×2 kernel (a vertical-edge detector)</p>
          <p className="font-mono text-[11px] text-ink">
            [{conv.kernel[0].join(", ")}] / [{conv.kernel[1].join(", ")}]
          </p>
        </div>
        <p className="mt-2 rounded border border-[#C9A227]/40 bg-[#FFFDF5] px-2 py-1.5 font-mono text-[11px] text-[#8a6d1a]">
          {terms.join(" + ")} = <b>{conv.fmap[ci][cj]}</b>
        </p>
      </div>
    </div>
  );
}

/** ReLU'd feature map → a 2×2 window slides; the max survives, the map shrinks. */
export function MaxPoolStage({ lesson, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const conv = convOf(lesson.trace.series);
  const pn = conv ? conv.pooled.length : 0;
  const k = useSubstep(clock, entryIdx, Math.max(1, pn * pn));
  const pos = reducedMotion ? pn * pn : k;
  if (!conv) return <p className="text-xs text-muted">No pooling demo for this data.</p>;

  const cur = Math.max(0, Math.min(pn * pn, pos) - 1);
  const ci = Math.floor(cur / pn);
  const cj = cur % pn;
  const windowVals = [
    ...conv.relu[ci].slice(cj, cj + 2),
    ...conv.relu[ci + 1].slice(cj, cj + 2),
  ];

  return (
    <div className="flex flex-wrap items-start gap-4">
      <svg viewBox="0 0 300 130" width={300} role="img" aria-label="max pooling window">
        <Grid
          m={conv.relu} x0={4} y0={6} hl={{ i: ci, j: cj, size: 2 }}
          fillFor={(v) => `rgba(201,162,39,${Math.min(1, Math.abs(v) / 2)})`}
        />
        <text x={4} y={126} fontSize={9} fill="#5B6B60">after ReLU (negatives zeroed)</text>
        <Grid
          m={conv.pooled} x0={190} y0={20}
          fillFor={(v) => `rgba(109,179,63,${Math.min(1, Math.abs(v) / 2)})`}
        />
        {conv.pooled.map((row, i) =>
          row.map((_v, j) =>
            i * pn + j < pos ? null : (
              <rect key={`p${i}${j}`} x={190 + j * CELL} y={20 + i * CELL}
                    width={CELL - 2} height={CELL - 2} rx={4} fill="#FBFDF9" stroke="#E4EBE1" />
            ),
          ),
        )}
        <text x={190} y={126} fontSize={9} fill="#5B6B60">pooled: smaller, stronger</text>
      </svg>
      <p className="min-w-[170px] flex-1 rounded border border-[#C9A227]/40 bg-[#FFFDF5] px-2 py-1.5 font-mono text-[11px] text-[#8a6d1a]">
        max({windowVals.join(", ")}) = <b>{conv.pooled[ci][cj]}</b> — only the strongest evidence
        survives
      </p>
    </div>
  );
}

export default ConvSlideStage;
