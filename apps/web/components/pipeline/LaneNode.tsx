"use client";

import { memo } from "react";
import type { Node, NodeProps } from "@xyflow/react";
import type { LaneNodeData } from "./types";

type LaneFlowNode = Node<LaneNodeData, "lane">;

function LaneNodeComponent({ data }: NodeProps<LaneFlowNode>) {
  const complete = data.done === data.total;
  return (
    <div
      className="h-full w-full rounded-2xl border px-4 pt-2.5"
      style={{
        borderColor: `${data.accent}33`,
        background: `linear-gradient(180deg, ${data.accent}12, ${data.accent}05)`,
      }}
    >
      <div className="flex items-baseline justify-between">
        <span className="font-display text-xs font-semibold tracking-[0.16em] text-forest">
          <span style={{ color: data.accent }}>◆ </span>
          {data.title.toUpperCase()}
        </span>
        <span className="flex items-baseline gap-2">
          <span className="text-[10px] text-muted">{data.blurb}</span>
          <span
            className="rounded-full border bg-white px-2 py-0.5 text-[9px] font-bold"
            style={{ borderColor: `${data.accent}44`, color: data.accent }}
          >
            {complete ? `${data.total}/${data.total} ✓` : `${data.done}/${data.total} done`}
          </span>
        </span>
      </div>
    </div>
  );
}

export const LaneNode = memo(LaneNodeComponent);
