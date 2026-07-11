"use client";

import { useEffect, useState } from "react";
import type { ModelTrace, TestRow } from "@/lib/api";
import type { TestProps, TrainProps } from "./shared";

/** Transformer family — the REAL learned self-attention on this data: features become tokens,
 *  and the k×k heatmap shows how much each token listens to every other (per head, animated). */

type Attn = number[][][]; // [head][from][to]

function attnOf(x: unknown): Attn | null {
  if (!Array.isArray(x) || !x.length) return null;
  return x as Attn;
}

function topPair(m: number[][], toks: string[]): string {
  let best = { i: 0, j: 0, v: -1 };
  m.forEach((row, i) =>
    row.forEach((v, j) => {
      if (i !== j && v > best.v) best = { i, j, v };
    }),
  );
  return `${toks[best.i]} listens hardest to ${toks[best.j]} (weight ${best.v.toFixed(2)})`;
}

function TokenStrip({ toks, values }: { toks: string[]; values?: Record<string, number> }) {
  return (
    <div className="flex flex-wrap gap-1">
      {toks.map((t) => (
        <span key={t} className="rounded-full bg-[#EAF2F8] px-2 py-0.5 text-[11px] text-[#2E6C8E]">
          {t}
          {values && values[t] != null && <b className="ml-1 text-ink">{values[t]}</b>}
        </span>
      ))}
    </div>
  );
}

const SWEEP_MS_PER_ROW = 380;

function AttentionHeatmap({
  attn,
  toks,
  animate,
}: {
  attn: Attn;
  toks: string[];
  animate: boolean;
}) {
  const heads = attn.length;
  const [head, setHead] = useState(0);
  const [litRows, setLitRows] = useState(animate ? -1 : Infinity);
  const [run, setRun] = useState(0);
  const m = attn[Math.min(head, heads - 1)];
  const k = toks.length;

  useEffect(() => {
    if (!animate) return;
    setLitRows(-1);
    const id = setInterval(() => {
      setLitRows((r) => {
        if (r >= k - 1) {
          clearInterval(id);
          return r;
        }
        return r + 1;
      });
    }, SWEEP_MS_PER_ROW);
    return () => clearInterval(id);
  }, [animate, head, run, k]);

  const CELL = 30;
  const LBL = 62;
  const W = LBL + k * CELL + 6;
  const H = LBL + k * CELL + 6;
  const maxV = Math.max(0.01, ...m.flat());

  return (
    <div className="rounded-lg border border-line bg-white p-2">
      <div className="mb-1 flex items-center gap-1 text-[11px]">
        {heads > 1 &&
          Array.from({ length: heads }, (_, h) => (
            <button
              key={h}
              onClick={() => setHead(h)}
              className={`rounded-full px-2 py-0.5 transition ${
                head === h ? "bg-forest text-white" : "border border-line text-forest hover:bg-bg"
              }`}
            >
              Head {h + 1}
            </button>
          ))}
        {heads > 1 && (
          <span className="ml-1 text-muted">each head learns a different relationship</span>
        )}
        {animate && (
          <button
            onClick={() => setRun((r) => r + 1)}
            className="ml-auto rounded border border-line px-2 py-0.5 text-forest hover:bg-bg"
          >
            ↻ replay
          </button>
        )}
      </div>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ minWidth: Math.min(W, 420), maxWidth: W }} role="img" aria-label="attention heatmap">
          {/* column labels (listened to) */}
          {toks.map((t, j) => (
            <text
              key={`c${j}`}
              x={LBL + j * CELL + CELL / 2}
              y={LBL - 6}
              fontSize={8.5}
              fill="#7C8A80"
              textAnchor="start"
              transform={`rotate(-45 ${LBL + j * CELL + CELL / 2} ${LBL - 6})`}
            >
              {t}
            </text>
          ))}
          {/* row labels (looking) + cells */}
          {m.map((row, i) => (
            <g key={`r${i}`} opacity={i <= litRows ? 1 : 0.12} style={{ transition: "opacity .3s" }}>
              <text x={LBL - 6} y={LBL + i * CELL + CELL / 2 + 3} fontSize={8.5} fill="#7C8A80" textAnchor="end">
                {toks[i]}
              </text>
              {row.map((v, j) => (
                <g key={j}>
                  <rect
                    x={LBL + j * CELL + 1}
                    y={LBL + i * CELL + 1}
                    width={CELL - 2}
                    height={CELL - 2}
                    rx={4}
                    fill="#14342A"
                    opacity={0.06 + 0.94 * (v / maxV)}
                  />
                  <text
                    x={LBL + j * CELL + CELL / 2}
                    y={LBL + i * CELL + CELL / 2 + 3}
                    fontSize={7.5}
                    textAnchor="middle"
                    fill={v / maxV > 0.5 ? "#fff" : "#14342A"}
                  >
                    {v.toFixed(2)}
                  </text>
                </g>
              ))}
            </g>
          ))}
          <text x={LBL - 6} y={12} fontSize={8.5} fill="#B8860B" textAnchor="end">
            looking ↓
          </text>
          <text x={LBL} y={12} fontSize={8.5} fill="#B8860B">
            listened to →
          </text>
        </svg>
      </div>
      <p className="mt-1 text-[10px] text-muted">{topPair(m, toks)}</p>
    </div>
  );
}

export function Train({ trace }: TrainProps) {
  const series = trace.series as Record<string, unknown> | null;
  const attn = attnOf(series?.attention);
  const stages = (series?.attention_stages ?? []) as { epoch: number; attention: unknown }[];
  const [stageIdx, setStageIdx] = useState(Math.max(0, stages.length - 1));
  if (!attn) return null;
  const stageAttn = stages.length ? attnOf(stages[Math.min(stageIdx, stages.length - 1)]?.attention) : null;
  const stageName = (j: number) =>
    j === 0 ? "untrained" : j === stages.length - 1 ? "trained" : `epoch ${stages[j].epoch}`;
  return (
    <div className="space-y-2">
      <p className="text-[11px] text-muted">
        A transformer first turns each feature into a <b>token</b>:
      </p>
      <TokenStrip toks={trace.features} />
      <div className="grid grid-cols-3 gap-1.5 text-[10.5px]">
        <div className="rounded-lg bg-[#EAF2F8] p-1.5">
          <b className="text-[#2E6C8E]">Q — the question.</b> Each token asks: &quot;who here is
          relevant to me?&quot;
        </div>
        <div className="rounded-lg bg-[#E4F3DA] p-1.5">
          <b className="text-[#3F8F5B]">K — the key.</b> Each token also advertises what it holds.
        </div>
        <div className="rounded-lg bg-[#FBF3D6] p-1.5">
          <b className="text-[#B8860B]">Q·K → attention.</b> Good question–key matches get high
          weight (softmax makes each row sum to 1).
        </div>
      </div>
      <p className="text-[11px] text-muted">
        These are the <b>real attention weights this model learned on this data</b> — watch each
        token&apos;s row light up as it decides who to listen to:
      </p>
      {stages.length > 1 && (
        <div className="flex flex-wrap items-center gap-1 text-[11px]">
          <span className="font-medium text-[#8a6d1a]">Attention sharpening:</span>
          {stages.map((s, j) => (
            <button
              key={j}
              onClick={() => setStageIdx(j)}
              className={`rounded-full px-2 py-0.5 ${
                j === stageIdx ? "bg-forest text-white" : "border border-line text-forest hover:bg-bg"
              }`}
            >
              {stageName(j)}
            </button>
          ))}
          <span className="text-muted">— untrained attention is a blur; training focuses it.</span>
        </div>
      )}
      <AttentionHeatmap attn={stageAttn ?? attn} toks={trace.features} animate />
      <p className="text-[11px] text-muted">
        The tokens are then blended by these weights and pooled into a prediction. BERT/GPT/ViT run
        exactly this mechanism — over words or image patches instead of features, stacked many
        layers deep.
      </p>
    </div>
  );
}

export function Test({ trace, row }: TestProps) {
  const attn = attnOf((row as TestRow & { attention?: unknown }).attention);
  return (
    <div className="space-y-2">
      <p className="text-[11px] text-muted">
        THIS row&apos;s tokens flow through the trained attention — this is its own (not averaged)
        attention pattern:
      </p>
      {attn ? <AttentionHeatmap attn={attn} toks={trace.features} animate={false} /> : null}
      <p className="rounded-lg bg-leaf/10 p-1.5 text-[11px]">
        tokens blended by these weights → pooled → head →{" "}
        <b className="text-forest">{String(row.predicted)}</b>
      </p>
    </div>
  );
}
