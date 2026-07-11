"use client";

import type { ModelTrace } from "@/lib/api";
import { ContribBlock, type TestProps, type TrainProps } from "./shared";

/** Time-series family (ARIMA-style AR): the series + fitted line, then per-step lag contributions. */

type Series = {
  history?: number[];
  fitted?: (number | null)[];
  coef?: { c: number; phi: number[] };
  split?: number;
};

function LineChart({ trace }: { trace: ModelTrace }) {
  const s = (trace.series ?? {}) as Series;
  const hist = s.history ?? [];
  const fitted = s.fitted ?? [];
  if (!hist.length) return null;
  const W = 330;
  const H = 150;
  const PAD = 14;
  const all = hist.concat(fitted.filter((v): v is number => v != null));
  const [v0, v1] = [Math.min(...all), Math.max(...all)];
  const px = (i: number) => PAD + (i / Math.max(1, hist.length - 1)) * (W - 2 * PAD);
  const py = (v: number) => H - PAD - ((v - v0) / (v1 - v0 || 1)) * (H - 2 * PAD);
  const path = (vals: (number | null)[]) =>
    vals
      .map((v, i) => (v == null ? null : `${i === 0 || vals[i - 1] == null ? "M" : "L"}${px(i)},${py(v)}`))
      .filter(Boolean)
      .join(" ");
  const split = s.split ?? hist.length;

  return (
    <div className="rounded-lg border border-line bg-white p-2">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="time series">
        {/* holdout shading */}
        <rect x={px(split)} y={PAD / 2} width={Math.max(0, W - PAD - px(split))} height={H - PAD} fill="#FFFBEA" />
        <path d={path(hist)} fill="none" stroke="#14342A" strokeWidth={1.6} />
        <path d={path(fitted)} fill="none" stroke="#6DB33F" strokeWidth={1.6} strokeDasharray="4 3" />
        <text x={PAD} y={10} fontSize={9} fill="#14342A">— actual series</text>
        <text x={PAD + 90} y={10} fontSize={9} fill="#6DB33F">- - model&apos;s one-step predictions</text>
        <text x={px(split) + 4} y={H - 4} fontSize={9} fill="#B8860B">test window</text>
      </svg>
    </div>
  );
}

export function Train({ trace }: TrainProps) {
  const s = (trace.series ?? {}) as Series;
  const phi = s.coef?.phi ?? [];
  return (
    <div className="space-y-2">
      <p className="text-[11px] text-muted">
        A time-series model predicts the <b>next value from the previous ones</b>. Training slides
        along the history and finds the weights (φ) that best turn &quot;yesterday + the day
        before&quot; into &quot;today&quot;:
      </p>
      <div className="rounded-lg bg-leaf/10 p-2 text-[11px]">
        value(t) ≈ <b>{s.coef?.c}</b>
        {phi.map((p, i) => (
          <span key={i}>
            {" "}
            + <b>{p}</b> × value(t−{i + 1})
          </span>
        ))}
      </div>
      <LineChart trace={trace} />
      <p className="text-[11px] text-muted">
        The dashed line is the model re-predicting each step — the closer it hugs the solid line,
        the better it captured the pattern. The gold band is data it never saw during training.
      </p>
    </div>
  );
}

/** The sliding window made literal: the recent stretch of the series with THIS step's input
 *  window highlighted gold and the point being predicted outlined — step to the next row and
 *  watch the window slide one step forward. */
function WindowStrip({ trace, row }: { trace: ModelTrace; row: TestProps["row"] }) {
  const s = (trace.series ?? {}) as Series;
  const hist = s.history ?? [];
  const split = s.split ?? hist.length;
  const lags = trace.features.length;
  const j = Math.max(0, (trace.test_rows ?? []).indexOf(row));
  const pos = split + j; // index in `hist` of the value being predicted
  const start = Math.max(0, pos - 14);
  const seg = hist.slice(start, Math.min(hist.length, pos + 2));
  if (!seg.length) return null;
  const [lo, hi] = [Math.min(...seg), Math.max(...seg)];
  const barH = (v: number) => 8 + ((v - lo) / (hi - lo || 1)) * 34;

  return (
    <div className="rounded-lg border border-line bg-white p-2">
      <div className="flex items-end gap-[3px]" style={{ height: 52 }}>
        {seg.map((v, i) => {
          const gi = start + i;
          const inWindow = gi >= pos - lags && gi < pos;
          const isPred = gi === pos;
          return (
            <div
              key={gi}
              title={`t=${gi}: ${v}`}
              className="flex-1 rounded-t transition-all duration-500"
              style={{
                height: barH(v),
                background: isPred ? "transparent" : inWindow ? "#C9A227" : "#C7D4CC",
                border: isPred ? "2px dashed #14342A" : undefined,
              }}
            />
          );
        })}
      </div>
      <p className="mt-1 text-[10px] text-muted">
        <span className="text-[#8a6d1a]">■ gold = the {lags}-value window</span> feeding this
        prediction · <span className="text-ink">▢ dashed = the value being predicted</span>. Move to
        the next test row and the window slides one step forward — that&apos;s forecasting.
      </p>
    </div>
  );
}

export function Test(props: TestProps) {
  return (
    <div className="space-y-2">
      <WindowStrip trace={props.trace} row={props.row} />
      <p className="text-[11px] text-muted">
        this step is predicted only from its recent past (lags × learned weights):
      </p>
      <ContribBlock {...props} />
    </div>
  );
}
