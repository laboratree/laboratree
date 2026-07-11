"use client";

import { memo } from "react";
import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { labTabLabel } from "@/lib/labTabs";
import { CARD_H, CARD_W } from "./layout";
import { KIND_META, stageStatusMeta, type StageNodeData } from "./types";

type StageFlowNode = Node<StageNodeData, "stage">;

function StageNodeComponent({ data }: NodeProps<StageFlowNode>) {
  const { stage, phaseNumber, selected, accent } = data;
  const kind = KIND_META[stage.kind];
  const status = stageStatusMeta(stage);
  const running = stage.status === "running";
  const failed = stage.status === "failed";

  const chipColor = running ? "#F59E0B" : failed ? "#DC2626" : accent;

  return (
    <div
      title={kind.hint}
      style={{
        width: CARD_W,
        height: CARD_H,
        borderTop: `3px solid ${chipColor}`,
        boxShadow: running
          ? "0 0 14px rgba(245, 158, 11, 0.35)"
          : `0 2px 8px ${accent}1F`,
      }}
      className={[
        "relative cursor-pointer overflow-hidden rounded-xl border p-2.5 transition duration-150",
        stage.kind === "manual" ? "border-dashed" : "",
        running
          ? "animate-stage-pulse border-amber-400 bg-amber-50"
          : failed
            ? "border-red-400 bg-white"
            : "border-line bg-white hover:-translate-y-0.5 hover:shadow-lg",
        selected ? "ring-2 ring-leaf ring-offset-1" : "",
      ].join(" ")}
    >
      <Handle type="target" position={Position.Left} className="!bg-sprout" />
      <div className="flex items-center gap-1.5">
        <span
          className="inline-flex h-[18px] min-w-[18px] flex-none items-center justify-center rounded-full px-1 text-[9px] font-extrabold text-white"
          style={{ background: chipColor }}
        >
          {phaseNumber}
        </span>
        <span className="truncate text-xs font-bold text-forest">{stage.label}</span>
      </div>
      <div className="mt-1 line-clamp-2 text-[10px] leading-snug text-muted">
        {stage.description}
      </div>
      <div className="absolute inset-x-2.5 bottom-2 flex items-center justify-between text-[10px]">
        <span
          className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${kind.badgeClass}`}
        >
          {stage.kind === "lab" && stage.labTab
            ? `🧪 ${labTabLabel(stage.labTab)} ↗`
            : stage.kind === "component" && stage.result?.evidence_count != null
              ? `⚙ RUN · 🔒 ${stage.result.evidence_count}`
              : stage.kind === "agent" && stage.result?.evidence_count != null
                ? `🤖 AGENT · 🔒 ${stage.result.evidence_count}`
                : kind.badge}
        </span>
        <span className={`font-bold ${status.className}`}>{status.label}</span>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-sprout" />
    </div>
  );
}

export const StageNode = memo(StageNodeComponent);
