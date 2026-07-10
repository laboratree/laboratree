"use client";

import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { labTabLabel } from "@/lib/labTabs";
import { CARD_H, CARD_W } from "./layout";
import { KIND_META, stageStatusMeta, type StageNodeData } from "./types";

type StageFlowNode = Node<StageNodeData, "stage">;

function StageNodeComponent({ data }: NodeProps<StageFlowNode>) {
  const { stage, phaseNumber, selected } = data;
  const kind = KIND_META[stage.kind];
  const status = stageStatusMeta(stage);
  const running = stage.status === "running";
  const failed = stage.status === "failed";

  const border = running
    ? "border-amber-400 bg-amber-50 animate-stage-pulse"
    : failed
      ? "border-red-400 bg-white"
      : "border-line bg-white";

  return (
    <div
      title={kind.hint}
      style={{ width: CARD_W, height: CARD_H }}
      className={[
        "cursor-pointer overflow-hidden rounded-xl border p-2.5 shadow-sm transition",
        stage.kind === "manual" ? "border-dashed" : "",
        border,
        selected ? "ring-2 ring-leaf" : "hover:shadow",
      ].join(" ")}
    >
      <Handle type="target" position={Position.Left} className="!bg-sprout" />
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-bold tracking-wider text-muted">
          PHASE {phaseNumber}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-[9px] font-semibold ${kind.badgeClass}`}>
          {kind.badge}
        </span>
      </div>
      <div className="mt-0.5 truncate text-xs font-semibold text-forest">{stage.label}</div>
      <div className="mt-0.5 line-clamp-2 text-[10px] leading-snug text-muted">
        {stage.description}
      </div>
      <div className="mt-1 flex items-center justify-between text-[10px]">
        <span className={`font-semibold ${status.className}`}>{status.label}</span>
        {stage.kind === "lab" && stage.labTab && (
          <span className="text-[#2563EB]">{labTabLabel(stage.labTab)} ↗</span>
        )}
        {stage.kind === "component" && stage.result?.evidence_count != null && (
          <span className="text-muted">🔒 {stage.result.evidence_count} evidence</span>
        )}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-sprout" />
    </div>
  );
}

export const StageNode = memo(StageNodeComponent);
