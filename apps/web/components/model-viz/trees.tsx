"use client";

import { useEffect, useState } from "react";
import type { SplitScan, SplitScanFeature, TreeNode } from "@/lib/api";
import type { TestProps, TrainProps } from "./shared";

/** Trees family — a LITERAL tree diagram (SVG): question nodes branch yes/no down to colored
 *  leaf predictions; during testing the row's root-to-leaf path lights up gold. */

const NODE_W = 104;
const NODE_H = 34;
const LEAF_W = 92;
const X_GAP = 12;
const Y_GAP = 64;
const PALETTE = ["#6DB33F", "#C0392B", "#2E6C8E", "#B8860B", "#7D3C98"];

type Laid = {
  node: TreeNode;
  x: number; // center x
  y: number; // top y
  onPath: boolean;
  children: Laid[];
};

function countLeaves(n: TreeNode): number {
  if (n.leaf || (!n.left && !n.right)) return 1;
  return (n.left ? countLeaves(n.left) : 0) + (n.right ? countLeaves(n.right) : 0);
}

function depthOf(n: TreeNode): number {
  if (n.leaf || (!n.left && !n.right)) return 0;
  return 1 + Math.max(n.left ? depthOf(n.left) : 0, n.right ? depthOf(n.right) : 0);
}

/** Assign x by leaf slots (each leaf gets a column; parents sit midway over their children). */
function layout(node: TreeNode, path: string[] | undefined, depth: number, leafStart: number, onPath: boolean): Laid {
  const slotW = LEAF_W + X_GAP;
  if (node.leaf || (!node.left && !node.right)) {
    return { node, x: (leafStart + 0.5) * slotW, y: depth * Y_GAP, onPath, children: [] };
  }
  const go = path?.[depth];
  const leftLeaves = node.left ? countLeaves(node.left) : 0;
  const kids: Laid[] = [];
  if (node.left)
    kids.push(layout(node.left, path, depth + 1, leafStart, onPath && go === "left"));
  if (node.right)
    kids.push(layout(node.right, path, depth + 1, leafStart + leftLeaves, onPath && go === "right"));
  const x = kids.length ? (kids[0].x + kids[kids.length - 1].x) / 2 : (leafStart + 0.5) * slotW;
  return { node, x, y: depth * Y_GAP, onPath, children: kids };
}

function collectPredictions(n: TreeNode, out: string[]) {
  if (n.leaf || (!n.left && !n.right)) {
    const p = String(n.prediction);
    if (!out.includes(p)) out.push(p);
    return;
  }
  if (n.left) collectPredictions(n.left, out);
  if (n.right) collectPredictions(n.right, out);
}

function renderEdges(l: Laid, out: React.ReactNode[], key = "e") {
  l.children.forEach((c, i) => {
    const hot = l.onPath && c.onPath;
    const x1 = l.x;
    const y1 = l.y + NODE_H;
    const x2 = c.x;
    const y2 = c.y;
    out.push(
      <g key={`${key}${i}`}>
        <path
          d={`M${x1},${y1} C${x1},${y1 + 22} ${x2},${y2 - 22} ${x2},${y2}`}
          fill="none"
          stroke={hot ? "#C9A227" : "#C7D4CC"}
          strokeWidth={hot ? 2.5 : 1.4}
        />
        <text
          x={(x1 + x2) / 2 + (i === 0 ? -6 : 6)}
          y={(y1 + y2) / 2}
          fontSize={9}
          fill={hot ? "#B8860B" : "#7C8A80"}
          textAnchor={i === 0 ? "end" : "start"}
          fontWeight={hot ? 700 : 400}
        >
          {i === 0 ? "yes" : "no"}
        </text>
      </g>,
    );
    renderEdges(c, out, `${key}${i}.`);
  });
}

function renderNodes(l: Laid, preds: string[], out: React.ReactNode[], key = "n") {
  const n = l.node;
  const isLeaf = n.leaf || (!n.left && !n.right);
  if (isLeaf) {
    const color = PALETTE[preds.indexOf(String(n.prediction)) % PALETTE.length];
    out.push(
      <g key={key}>
        <rect
          x={l.x - LEAF_W / 2}
          y={l.y}
          width={LEAF_W}
          height={NODE_H}
          rx={16}
          fill={color}
          opacity={l.onPath ? 1 : 0.72}
          stroke={l.onPath ? "#C9A227" : "none"}
          strokeWidth={3}
        />
        <text x={l.x} y={l.y + 14} fontSize={9.5} fill="#fff" textAnchor="middle" fontWeight={700}>
          {String(n.prediction)}
        </text>
        <text x={l.x} y={l.y + 26} fontSize={8} fill="#fff" textAnchor="middle" opacity={0.9}>
          {n.confidence != null ? `${Math.round(n.confidence * 100)}% of ${n.samples}` : `${n.samples} rows`}
        </text>
      </g>,
    );
    return;
  }
  out.push(
    <g key={key}>
      <rect
        x={l.x - NODE_W / 2}
        y={l.y}
        width={NODE_W}
        height={NODE_H}
        rx={8}
        fill={l.onPath ? "#FFFBEA" : "#fff"}
        stroke={l.onPath ? "#C9A227" : "#14342A"}
        strokeWidth={l.onPath ? 2.5 : 1.2}
      />
      <text x={l.x} y={l.y + 14} fontSize={9.5} fill="#14342A" textAnchor="middle" fontWeight={700}>
        {n.feature} ≤ {n.threshold}
      </text>
      <text x={l.x} y={l.y + 26} fontSize={8} fill="#7C8A80" textAnchor="middle">
        gain {n.gain} · {n.samples} rows
      </text>
    </g>,
  );
  l.children.forEach((c, i) => renderNodes(c, preds, out, `${key}${i}`));
}

export function TreeDiagram({ root, path }: { root: TreeNode; path?: string[] }) {
  const leaves = countLeaves(root);
  const depth = depthOf(root);
  const W = leaves * (LEAF_W + X_GAP);
  const H = depth * Y_GAP + NODE_H + 8;
  const laid = layout(root, path, 0, 0, path != null);
  const edges: React.ReactNode[] = [];
  const nodes: React.ReactNode[] = [];
  const preds: string[] = [];
  collectPredictions(root, preds);
  renderEdges(laid, edges);
  renderNodes(laid, preds, nodes);
  return (
    <div className="overflow-x-auto rounded-lg border border-line bg-white p-2">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ minWidth: Math.min(W, 560) }}
        role="img"
        aria-label="decision tree"
      >
        {edges}
        {nodes}
      </svg>
    </div>
  );
}

const isBoostHint = (hint?: string) => /(boost|xgb|gbm|gbdt|lightgbm|catboost)/i.test(hint ?? "");

/** The "transformed table" BETWEEN boosting stages: what this round receives as its input —
 *  each row's current prediction so far and the leftover error (residual) the next tree must fix. */
function RoundInputTable({
  table,
  round,
  positive,
  task,
}: {
  table: Record<string, number | string>[];
  round: number;
  positive?: string;
  task: string;
}) {
  const featCols = Object.keys(table[0] ?? {}).filter(
    (k) => !["actual", "current", "residual"].includes(k),
  );
  return (
    <div className="rounded-lg border border-[#C9A227]/40 bg-[#FFFDF5] p-1.5">
      <p className="mb-1 text-[10.5px] text-[#8a6d1a]">
        {round === 0 ? (
          <>Tree 1&apos;s input — everyone starts at the baseline; <b>residual</b> = truth − current guess:</>
        ) : (
          <>
            The table AFTER tree {round} — <b>current</b> ={" "}
            {task === "classification" ? `probability of ${positive ?? "positive"}` : "prediction"} so
            far, <b>residual</b> = the error still left. THIS is what tree {round + 1} trains on:
          </>
        )}
      </p>
      <div className="overflow-x-auto">
        <table className="min-w-full text-[10px]">
          <thead>
            <tr className="text-muted">
              {featCols.map((c) => (
                <th key={c} className="whitespace-nowrap px-1.5 py-0.5 text-left font-medium">{c}</th>
              ))}
              <th className="whitespace-nowrap px-1.5 py-0.5 text-left font-medium text-forest">actual</th>
              <th className="whitespace-nowrap px-1.5 py-0.5 text-left font-medium text-[#B8860B]">current</th>
              <th className="whitespace-nowrap px-1.5 py-0.5 text-left font-medium text-red-700">residual</th>
            </tr>
          </thead>
          <tbody>
            {table.map((row, i) => {
              const resid = Number(row.residual);
              return (
                <tr key={i} className="border-t border-line/50">
                  {featCols.map((c) => (
                    <td key={c} className="whitespace-nowrap px-1.5 py-0.5 text-ink">{String(row[c])}</td>
                  ))}
                  <td className="whitespace-nowrap px-1.5 py-0.5 font-medium text-forest">{String(row.actual)}</td>
                  <td className="whitespace-nowrap px-1.5 py-0.5 text-ink">{String(row.current)}</td>
                  <td className={`whitespace-nowrap px-1.5 py-0.5 font-semibold ${Math.abs(resid) < 0.15 ? "text-green-700" : "text-red-600"}`}>
                    {resid > 0 ? "+" : ""}
                    {String(row.residual)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ---------------- split-scan: watch the tree choose its threshold ---------------- */

const SCAN_MS = 4200;

function ScanChart({ f, run }: { f: SplitScanFeature; run: number }) {
  const [idx, setIdx] = useState(-1); // how far the sweep has reached (candidate index)
  const cands = f.candidates;
  const n = cands.length;

  useEffect(() => {
    let raf = 0;
    let start: number | null = null;
    const tick = (now: number) => {
      if (start == null) start = now;
      const p = Math.min(1, (now - start) / SCAN_MS);
      setIdx(Math.floor(p * (n - 1)));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    setIdx(-1);
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [run, n]);

  const W = 360;
  const H = 170;
  const PL = 34;
  const PR = 12;
  const PT = 16;
  const PB = 30;
  const ts = cands.map((c) => c.t);
  const [t0, t1] = [Math.min(...ts), Math.max(...ts)];
  const gmax = Math.max(1e-9, ...cands.map((c) => c.gain));
  const px = (t: number) => PL + ((t - t0) / (t1 - t0 || 1)) * (W - PL - PR);
  const py = (g: number) => H - PB - (Math.max(0, g) / gmax) * (H - PT - PB);

  // best candidate seen so far during the sweep
  let bestSoFar = -1;
  for (let i = 0; i <= idx && i < n; i++) {
    if (bestSoFar < 0 || cands[i].gain > cands[bestSoFar].gain) bestSoFar = i;
  }
  const done = idx >= n - 1;
  const winner = cands.reduce((a, b) => (b.gain > a.gain ? b : a), cands[0]);
  const cur = idx >= 0 && idx < n ? cands[idx] : null;

  return (
    <div className="rounded-lg border border-line bg-white p-2">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="split scan">
        {/* axes */}
        <line x1={PL} y1={H - PB} x2={W - PR} y2={H - PB} stroke="#C7D4CC" />
        <line x1={PL} y1={PT} x2={PL} y2={H - PB} stroke="#C7D4CC" />
        <text x={(PL + W - PR) / 2} y={H - 4} fontSize={8.5} fill="#7C8A80" textAnchor="middle">
          candidate cut-point for {f.feature}
        </text>
        <text
          x={10}
          y={(PT + H - PB) / 2}
          fontSize={8.5}
          fill="#7C8A80"
          textAnchor="middle"
          transform={`rotate(-90 10 ${(PT + H - PB) / 2})`}
        >
          gain
        </text>
        {/* candidate dots — revealed as the scanner passes */}
        {cands.map((c, i) => (
          <circle
            key={i}
            cx={px(c.t)}
            cy={py(c.gain)}
            r={i === bestSoFar ? 4.5 : 3}
            fill={i === bestSoFar ? "#6DB33F" : "#9DB8A8"}
            opacity={i <= idx ? 1 : 0.12}
          />
        ))}
        {/* scanning line */}
        {cur && !done && (
          <g>
            <line x1={px(cur.t)} y1={PT} x2={px(cur.t)} y2={H - PB} stroke="#C9A227" strokeWidth={1.5} />
            <text x={px(cur.t)} y={PT - 3} fontSize={8.5} fill="#8a6d1a" textAnchor="middle">
              try ≤ {cur.t} → gain {cur.gain}
            </text>
          </g>
        )}
        {/* winner */}
        {done && (
          <g>
            <circle cx={px(winner.t)} cy={py(winner.gain)} r={7} fill="none" stroke="#C9A227" strokeWidth={2.5} />
            <text x={px(winner.t)} y={py(winner.gain) - 11} fontSize={9} fill="#8a6d1a" textAnchor="middle" fontWeight={700}>
              chosen: {f.feature} ≤ {winner.t} (gain {winner.gain})
            </text>
          </g>
        )}
      </svg>
      {cur && !done && (
        <p className="px-1 text-[10px] text-muted">
          splitting at {cur.t} puts {cur.n_left} rows on the yes-side, {cur.n_right} on the no-side
        </p>
      )}
    </div>
  );
}

function SplitScanView({ scan }: { scan: SplitScan }) {
  const [run, setRun] = useState(0);
  const chosen = scan.features.find((f) => f.feature === scan.chosen_feature) ?? scan.features[0];
  const others = scan.features.filter((f) => f !== chosen);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <p className="text-[11px] text-muted">
          Before asking its first question, the tree <b>auditions every cut-point</b>: slide a
          threshold across <b>{chosen.feature}</b>, and for each position measure the <b>gain</b> —
          how much cleaner the two sides get. Watch it scan:
        </p>
        <button
          onClick={() => setRun((r) => r + 1)}
          className="ml-2 shrink-0 rounded border border-line px-2 py-0.5 text-[11px] text-forest hover:bg-bg"
        >
          ↻ replay
        </button>
      </div>
      <ScanChart f={chosen} run={run} />
      {others.length > 0 && (
        <div className="mt-2 rounded-lg border border-line bg-white p-2">
          <p className="mb-1 text-[11px] text-muted">
            It auditioned other features the same way — their best splits scored lower, which is
            exactly why the tree asked about <b className="text-forest">{chosen.feature}</b> first:
          </p>
          {[chosen, ...others].map((f) => (
            <div key={f.feature} className="flex items-center gap-2 text-[11px]">
              <span className="w-20 shrink-0 truncate text-muted">{f.feature}</span>
              <div className="h-2.5 flex-1 rounded bg-bg">
                <div
                  className={`h-full rounded transition-all duration-700 ${f === chosen ? "bg-leaf" : "bg-leaf/40"}`}
                  style={{
                    width: `${Math.max(3, (f.best_gain / Math.max(1e-9, chosen.best_gain)) * 100)}%`,
                  }}
                />
              </div>
              <span className="w-24 shrink-0 text-right tabular-nums text-muted">
                best gain {f.best_gain}
                {f === chosen ? " 🏆" : ""}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

type TreeMode = "single" | "ensemble" | "scan";

function ModeTabs({
  mode,
  setMode,
  withScan,
}: {
  mode: TreeMode;
  setMode: (m: TreeMode) => void;
  withScan?: boolean;
}) {
  const tabs: [TreeMode, string][] = [
    ["single", "One decision tree"],
    ["ensemble", "Boosting — 3 trees stacked"],
  ];
  if (withScan) tabs.push(["scan", "How a split is chosen"]);
  return (
    <div className="mb-1.5 flex flex-wrap gap-1 text-[11px]">
      {tabs.map(([m, label]) => (
        <button
          key={m}
          onClick={() => setMode(m)}
          className={`rounded-full px-2.5 py-0.5 transition ${
            mode === m ? "bg-forest text-white" : "border border-line text-forest hover:bg-bg"
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export function Train({ trace, hint }: TrainProps) {
  const hasEnsemble = !!trace.rounds?.length;
  const hasScan = !!(trace.scan && trace.scan.features?.length);
  const [mode, setMode] = useState<TreeMode>(
    hasEnsemble && isBoostHint(hint) ? "ensemble" : "single",
  );

  if (mode === "scan" && hasScan) {
    return (
      <div>
        <ModeTabs mode={mode} setMode={setMode} withScan={hasScan} />
        <SplitScanView scan={trace.scan as unknown as SplitScan} />
      </div>
    );
  }

  if (mode === "ensemble" && hasEnsemble) {
    return (
      <div>
        <ModeTabs mode={mode} setMode={setMode} withScan={hasScan} />
        <p className="mb-1 text-[11px] text-muted">
          The REAL boosting ensemble fitted on this data. It starts from a baseline score of{" "}
          <b>{trace.baseline}</b>, then each tree is trained on the <b>mistakes left by the previous
          ones</b> — its leaves output score corrections (+pushes toward{" "}
          {trace.labels?.[1] ?? "higher"}, − toward {trace.labels?.[0] ?? "lower"}) that all ADD UP.
        </p>
        <div className="space-y-2">
          {trace.rounds!.map((r, i) => (
            <div key={i}>
              {r.table && (
                <RoundInputTable
                  table={r.table}
                  round={i}
                  positive={trace.labels?.[1]}
                  task={trace.task}
                />
              )}
              <p className="mb-0.5 mt-1 text-[11px] font-medium text-forest">
                Tree {i + 1}
                {i > 0 && <span className="font-normal text-muted"> — trained on the residuals above (the leftover errors)</span>}
              </p>
              <TreeDiagram root={r.tree} />
            </div>
          ))}
        </div>
        <p className="mt-1 rounded-lg bg-leaf/10 p-1.5 text-[11px]">
          final score = {trace.baseline} + tree₁ + tree₂ + tree₃{" "}
          {trace.task === "classification" && <>→ sigmoid → probability → class</>}
        </p>
      </div>
    );
  }

  return (
    <div>
      {(hasEnsemble || hasScan) && <ModeTabs mode={mode} setMode={setMode} withScan={hasScan} />}
      <p className="mb-1 text-[11px] text-muted">
        A literal decision tree, grown from this data. Each box asks a yes/no question about ONE
        feature — chosen because it best separates the groups (<b>gain</b> = how much cleaner the
        split makes them). Follow yes ↙ / no ↘ down to a colored leaf = the prediction.
      </p>
      {trace.tree && <TreeDiagram root={trace.tree} />}
    </div>
  );
}

export function Test({ trace, row, hint }: TestProps) {
  const hasEnsemble = !!(trace.rounds?.length && row.rounds?.length);
  const [mode, setMode] = useState<TreeMode>(
    hasEnsemble && isBoostHint(hint) ? "ensemble" : "single",
  );

  if (mode === "ensemble" && hasEnsemble) {
    let running = trace.baseline ?? 0;
    return (
      <div className="space-y-2">
        <ModeTabs mode={mode} setMode={setMode} />
        <div className="rounded-lg bg-bg p-1.5 text-[11px]">
          start at baseline score <b>{trace.baseline}</b>
        </div>
        {trace.rounds!.map((r, i) => {
          const c = row.rounds![i];
          running = Math.round((running + c.value) * 1000) / 1000;
          return (
            <div key={i}>
              <p className="mb-0.5 text-[11px] font-medium text-forest">
                Tree {i + 1} — this row follows the gold path:
              </p>
              <TreeDiagram root={r.tree} path={c.path.map((s) => s.go)} />
              <p className="mt-0.5 text-[11px]">
                tree {i + 1} outputs{" "}
                <b className={c.value >= 0 ? "text-green-700" : "text-red-600"}>
                  {c.value >= 0 ? "+" : ""}
                  {c.value}
                </b>{" "}
                → running score <b>{running}</b>
              </p>
            </div>
          );
        })}
        <div className="rounded-lg bg-leaf/10 p-2 text-[11px]">
          final score <b>{row.boost_score}</b>
          {row.boost_prob != null && (
            <>
              {" "}
              → sigmoid → probability <b>{row.boost_prob}</b>
            </>
          )}{" "}
          → predicts <b className="text-forest">{String(row.boost_pred ?? row.predicted)}</b>
        </div>
      </div>
    );
  }

  if (!trace.tree) return null;
  const steps = row.path ?? [];
  return (
    <div className="space-y-2">
      {hasEnsemble && <ModeTabs mode={mode} setMode={setMode} />}
      <TreeDiagram root={trace.tree} path={steps.map((s) => s.go)} />
      <div className="rounded-lg border border-line bg-white p-2 text-[11px]">
        <p className="mb-1 text-muted">the gold path, question by question:</p>
        {steps.map((s, i) => (
          <div key={i} className="flex flex-wrap gap-1 border-t border-line/50 py-0.5 first:border-t-0">
            <span className="text-muted">{i + 1}.</span>
            <span>
              {s.feature} = <b>{s.value}</b> — is it ≤ {s.threshold}?
            </span>
            <b className={s.go === "left" ? "text-forest" : "text-red-700"}>
              {s.go === "left" ? "yes ↙" : "no ↘"}
            </b>
          </div>
        ))}
        <p className="mt-1 rounded bg-leaf/10 p-1.5">
          lands on leaf → predicts <b className="text-forest">{String(row.predicted)}</b>
        </p>
      </div>
    </div>
  );
}
