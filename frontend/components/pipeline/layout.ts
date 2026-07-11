import type { Edge, Node } from "@xyflow/react";
import { CUSTOM_PHASE, type FlowPhase } from "@/lib/pipelineTemplates";
import {
  CUSTOM_ACCENT,
  isStageComplete,
  PHASE_ACCENTS,
  type LaneNodeData,
  type StageNodeData,
  type StageState,
} from "./types";

// Card and lane geometry. StageNode renders at exactly CARD_W × CARD_H (see StageNode.tsx);
// lanes are sized from their children so nothing overlaps.
export const CARD_W = 200;
export const CARD_H = 104;
const GAP_X = 28;
const GAP_Y = 16;
const WRAP_AT = 5; // stages per row inside a lane before wrapping
const LANE_PAD_X = 16;
const LANE_HEADER_H = 40;
const LANE_PAD_BOTTOM = 14;
const LANE_GAP = 18;

export type FlowGraph = { nodes: Node[]; edges: Edge[] };

// Pure: (stages, phases, selection, run-state) → positioned React Flow nodes + edges.
// Lanes stack vertically in phase order; stages flow left→right inside their lane and wrap
// after WRAP_AT. Stages with an unknown phase key collect in a trailing "Custom" lane.
export function buildFlowGraph(args: {
  stages: StageState[];
  phases: FlowPhase[];
  selectedId: string | null;
  runInFlight: boolean;
}): FlowGraph {
  const { stages, phases, selectedId, runInFlight } = args;

  const known = new Set(phases.map((p) => p.key));
  const lanePhases: FlowPhase[] = [...phases];
  if (stages.some((s) => !known.has(s.phase))) lanePhases.push(CUSTOM_PHASE);

  const laneStages = new Map<string, StageState[]>(lanePhases.map((p) => [p.key, []]));
  for (const s of stages) {
    laneStages.get(known.has(s.phase) ? s.phase : CUSTOM_PHASE.key)!.push(s);
  }

  const phaseNumber = new Map(stages.map((s, i) => [s.id, i + 1]));
  const counts = lanePhases.map((p) => laneStages.get(p.key)!.length);
  const maxCols = Math.min(WRAP_AT, Math.max(1, ...counts));
  const laneW = LANE_PAD_X * 2 + maxCols * CARD_W + (maxCols - 1) * GAP_X;

  const nodes: Node[] = [];
  let laneY = 0;
  for (const [laneIndex, phase] of lanePhases.entries()) {
    const members = laneStages.get(phase.key)!;
    if (members.length === 0) continue;
    const accent =
      phase.key === CUSTOM_PHASE.key
        ? CUSTOM_ACCENT
        : PHASE_ACCENTS[laneIndex % PHASE_ACCENTS.length];
    const rows = Math.ceil(members.length / WRAP_AT);
    const laneH = LANE_HEADER_H + rows * CARD_H + (rows - 1) * GAP_Y + LANE_PAD_BOTTOM;

    const laneData: LaneNodeData = {
      title: phase.title,
      blurb: phase.blurb,
      done: members.filter(isStageComplete).length,
      total: members.length,
      accent,
    };
    nodes.push({
      id: `lane-${phase.key}`,
      type: "lane",
      position: { x: 0, y: laneY },
      data: laneData,
      style: { width: laneW, height: laneH },
      draggable: false,
      selectable: false,
      zIndex: 0,
    });

    members.forEach((stage, i) => {
      const row = Math.floor(i / WRAP_AT);
      const col = i % WRAP_AT;
      const stageData: StageNodeData = {
        stage,
        phaseNumber: phaseNumber.get(stage.id)!,
        selected: stage.id === selectedId,
        accent,
      };
      nodes.push({
        id: stage.id,
        type: "stage",
        parentId: `lane-${phase.key}`,
        extent: "parent",
        position: {
          x: LANE_PAD_X + col * (CARD_W + GAP_X),
          y: LANE_HEADER_H + row * (CARD_H + GAP_Y),
        },
        data: stageData,
        draggable: false,
        zIndex: 1,
      });
    });

    laneY += laneH + LANE_GAP;
  }

  const edges: Edge[] = stages.slice(1).map((s, i) => ({
    id: `e-${stages[i].id}-${s.id}`,
    source: stages[i].id,
    target: s.id,
    animated: runInFlight,
    style: { stroke: "#A8D08D", strokeWidth: 1.5 },
  }));

  return { nodes, edges };
}
