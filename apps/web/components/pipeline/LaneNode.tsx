"use client";

import { memo } from "react";
import type { Node, NodeProps } from "@xyflow/react";
import type { LaneNodeData } from "./types";

type LaneFlowNode = Node<LaneNodeData, "lane">;

function LaneNodeComponent({ data }: NodeProps<LaneFlowNode>) {
  return (
    <div className="h-full w-full rounded-2xl border border-line bg-white/85 px-4 pt-2.5">
      <div className="flex items-baseline justify-between">
        <span className="font-display text-xs tracking-[0.14em] text-forest">
          {data.title.toUpperCase()}
        </span>
        <span className="text-[10px] text-muted">
          {data.blurb} · {data.done}/{data.total} done
        </span>
      </div>
    </div>
  );
}

export const LaneNode = memo(LaneNodeComponent);
