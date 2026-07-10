import type { PipelineStepResult } from "@/lib/api";
import type { FlowNodeKind, FlowStage } from "@/lib/pipelineTemplates";

export type StepStatus = "idle" | "running" | "succeeded" | "failed";

export type StageState = FlowStage & {
  status: StepStatus;          // run lifecycle — only component stages ever leave "idle"
  markedDone: boolean;         // lab/manual completion, owned by the user (never set by runs)
  result?: PipelineStepResult;
};

// Data payloads for the custom React Flow nodes (type aliases, not interfaces — they need
// the implicit index signature to satisfy React Flow's Record<string, unknown> constraint).
export type StageNodeData = { stage: StageState; phaseNumber: number; selected: boolean };
export type LaneNodeData = { title: string; blurb: string; done: number; total: number };

export const KIND_META: Record<
  FlowNodeKind,
  { badge: string; hint: string; badgeClass: string }
> = {
  component: {
    badge: "⚙ RUN",
    hint: "Runnable — executes as an Evidence-locked run",
    badgeClass: "bg-[#EAF4E2] text-[#3E7D32]",
  },
  lab: {
    badge: "🧪 LAB",
    hint: "Lab stage — do this work in its Lab tab",
    badgeClass: "bg-[#EDF4FB] text-[#2563EB]",
  },
  manual: {
    badge: "👤 MANUAL",
    hint: "Manual stage — human work outside the platform",
    badgeClass: "bg-[#F1F3F0] text-muted",
  },
};

const STATUS_META: Record<StepStatus, { label: string; className: string }> = {
  idle: { label: "○ idle", className: "text-muted" },
  running: { label: "● running…", className: "text-amber-700" },
  succeeded: { label: "✓ done", className: "text-[#3E7D32]" },
  failed: { label: "✕ failed", className: "text-red-600" },
};

export function stageStatusMeta(s: StageState): { label: string; className: string } {
  if (s.kind !== "component") {
    return s.markedDone ? STATUS_META.succeeded : { label: "○ to do", className: "text-muted" };
  }
  return STATUS_META[s.status];
}

export function isStageComplete(s: StageState): boolean {
  return s.kind === "component" ? s.status === "succeeded" : s.markedDone;
}
