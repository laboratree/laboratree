"use client";

import { useState } from "react";
import type { TreeNode, XGBNode } from "@/lib/api";
import { useSubstep } from "../clock";
import { TrialsBoard } from "./split-trials";
import type { LessonStageProps } from "./types";

/** A tree grows branch by branch under the clock — nodes appear in breadth-first order.
 *  When the exact-math boosting trace is present, every node is CLICKABLE: it replays that
 *  node's own split auditions below, and γ-pruned leaves wear a ✂ badge. */
export default function TreeGrowStage({ lesson, step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const ref = step.anim?.ref ?? {};
  const round = typeof ref.round === "number" ? ref.round : 0;
  const maxDepth = typeof ref.max_depth === "number" ? ref.max_depth : Infinity;
  const xgbRoot = lesson.trace.boosting?.rounds?.[round]?.root;
  const tree = xgbRoot
    ? xgbToTree(xgbRoot)
    : (lesson.trace.rounds?.[round]?.tree ?? lesson.trace.tree) as GNode | null;

  const nodes = layout(tree, maxDepth);
  const shown = useSubstep(clock, entryIdx, Math.max(1, nodes.length));
  const visible = reducedMotion ? nodes.length : shown;
  const [selected, setSelected] = useState<string | null>(null);
  const selectedNode = selected != null ? nodes.find((n) => n.node.id === selected)?.node : null;

  if (!tree || nodes.length === 0)
    return <p className="text-xs text-muted">No tree to draw for this round.</p>;

  const W = 520;
  const H = 40 + (Math.max(...nodes.map((n) => n.depth)) + 1) * 74;
  return (
    <div>
      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ minWidth: 380, maxHeight: 300 }}
             role="img" aria-label="tree growing split by split">
          {nodes.map((n, i) =>
            n.parent == null ? null : (
              <line
                key={`e${i}`}
                x1={nodes[n.parent].x * W} y1={nodes[n.parent].y + 18}
                x2={n.x * W} y2={n.y - 16}
                stroke={i < visible ? "#9DB8A5" : "transparent"} strokeWidth={1.4}
                style={{ transition: "stroke .4s" }}
              />
            ),
          )}
          {nodes.map((n, i) => {
            const clickable = Boolean(n.node.trials?.length);
            const sel = selected === n.node.id && selected != null;
            return (
              <g
                key={i}
                style={{ opacity: i < visible ? 1 : 0, transition: "opacity .4s", cursor: clickable ? "pointer" : undefined }}
                onClick={clickable ? () => setSelected(sel ? null : (n.node.id ?? null)) : undefined}
              >
                {n.node.leaf ? (
                  <>
                    <rect x={n.x * W - 34} y={n.y - 14} width={68} height={30} rx={7}
                          fill="#EAF4E2" stroke={sel ? "#C9A227" : "#6DB33F"} strokeWidth={sel ? 2 : 1} />
                    <text x={n.x * W} y={n.y + 5} textAnchor="middle" fontSize={10} fill="#14342A">
                      {String(n.node.prediction ?? "leaf")}
                    </text>
                    {n.node.pruned && (
                      <text x={n.x * W + 30} y={n.y - 16} textAnchor="middle" fontSize={9}>
                        ✂
                      </text>
                    )}
                  </>
                ) : (
                  <>
                    <rect x={n.x * W - 62} y={n.y - 16} width={124} height={34} rx={8}
                          fill="white" stroke="#C9A227" strokeWidth={sel ? 2.5 : 1} />
                    <text x={n.x * W} y={n.y - 2} textAnchor="middle" fontSize={10} fill="#14342A">
                      {n.node.feature} ≤ {n.node.threshold}
                    </text>
                    <text x={n.x * W} y={n.y + 12} textAnchor="middle" fontSize={8.5} fill="#5B6B60">
                      gain {n.node.gain} · {n.node.samples} rows
                    </text>
                  </>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <div className="flex items-center justify-between">
        <p className="text-[10px] text-muted">
          {xgbRoot ? "click any node to replay ITS split auditions · ✂ = γ-pruned" : ""}
        </p>
        <p className="text-right font-mono text-[10px] text-muted">
          {Math.min(visible, nodes.length)} / {nodes.length} nodes
        </p>
      </div>
      {selectedNode?.trials?.length ? (
        <div className="mt-2 rounded-lg border border-[#C9A227]/40 bg-[#FFFDF5] p-2">
          <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wide text-[#8a6d1a]">
            node {selectedNode.id} — its {selectedNode.trials.length} auditions
            {selectedNode.pruned ? " (all lost to γ — pruned into a leaf)" : ""}
          </p>
          <TrialsBoard
            trials={selectedNode.trials}
            gamma={lesson.trace.boosting?.gamma ?? 0}
            seen={selectedNode.trials.length}
          />
        </div>
      ) : null}
    </div>
  );
}

/** Normalized node the layout renders: legacy TreeNode fields + optional exact-math extras. */
type GNode = TreeNode & { id?: string; trials?: XGBNode["trials"]; pruned?: boolean; left?: GNode; right?: GNode };

function xgbToTree(n: XGBNode): GNode {
  return {
    leaf: n.leaf,
    samples: n.stats.n,
    prediction: n.value ?? undefined,
    feature: n.feature ?? undefined,
    threshold: n.threshold ?? undefined,
    gain: n.gain ?? undefined,
    id: n.id,
    trials: n.trials,
    pruned: n.pruned,
    left: n.left ? xgbToTree(n.left) : undefined,
    right: n.right ? xgbToTree(n.right) : undefined,
  };
}

type Laid = { node: GNode; depth: number; x: number; y: number; parent: number | null };

/** Breadth-first layout: x from the leaf-slot span, y from depth. */
function layout(root: GNode | null, maxDepth: number): Laid[] {
  if (!root) return [];
  const clip = (n: GNode, d: number): GNode =>
    d >= maxDepth && !n.leaf
      ? { leaf: true, samples: n.samples, prediction: "…" }
      : n.leaf
        ? n
        : { ...n, left: clip(n.left!, d + 1), right: clip(n.right!, d + 1) };
  const t = clip(root, 0);
  const leaves = (n: GNode): number => (n.leaf ? 1 : leaves(n.left!) + leaves(n.right!));
  const total = leaves(t);
  const out: Laid[] = [];
  const queue: { n: GNode; d: number; lo: number; hi: number; parent: number | null }[] = [
    { n: t, d: 0, lo: 0, hi: total, parent: null },
  ];
  while (queue.length) {
    const { n, d, lo, hi, parent } = queue.shift()!;
    const idx = out.length;
    out.push({ node: n, depth: d, x: (lo + hi) / 2 / total, y: 34 + d * 74, parent });
    if (!n.leaf && n.left && n.right) {
      const ll = leaves(n.left);
      queue.push({ n: n.left, d: d + 1, lo, hi: lo + ll, parent: idx });
      queue.push({ n: n.right, d: d + 1, lo: lo + ll, hi, parent: idx });
    }
  }
  return out;
}
