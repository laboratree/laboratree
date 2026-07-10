"use client";

import type { XGBNode } from "@/lib/api";
import { useSubstep } from "../clock";
import type { LessonStageProps } from "./types";

/** Each leaf's output computed in the open: −Σg/(Σh+λ), card by card. */
export default function LeafValuesStage({ lesson, step, clock, entryIdx, reducedMotion }: LessonStageProps) {
  const ref = step.anim?.ref ?? {};
  const round = typeof ref.round === "number" ? ref.round : 0;
  const b = lesson.trace.boosting;
  const leaves = collectLeaves(b?.rounds?.[round]?.root);
  const shown = useSubstep(clock, entryIdx, Math.max(1, leaves.length));
  const visible = reducedMotion ? leaves.length : shown;
  if (!b || !leaves.length) return <p className="text-xs text-muted">No leaves this round.</p>;

  return (
    <div className="grid gap-1.5 sm:grid-cols-2">
      {leaves.map((leaf, i) => (
        <div
          key={leaf.id}
          className="rounded-lg border border-leaf/50 bg-[#F6FAF2] px-2.5 py-2"
          style={{
            opacity: i < visible ? 1 : 0,
            transform: i < visible ? "none" : "translateY(6px)",
            transition: reducedMotion ? undefined : "opacity .4s ease, transform .4s ease",
          }}
        >
          <p className="text-[10px] uppercase tracking-wide text-muted">
            leaf {i + 1} · {leaf.stats.n} rows{leaf.pruned ? " · γ-pruned branch" : ""}
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-ink">
            −({leaf.stats.sum_g}) / ({leaf.stats.sum_h} + {b.reg_lambda})
          </p>
          <p className="font-mono text-[15px] font-semibold text-forest">= {leaf.value}</p>
        </div>
      ))}
    </div>
  );
}

function collectLeaves(root: XGBNode | null | undefined): XGBNode[] {
  if (!root) return [];
  if (root.leaf) return [root];
  return [...collectLeaves(root.left), ...collectLeaves(root.right)];
}
