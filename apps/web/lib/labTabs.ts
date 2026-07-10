// Single source of truth for the project-workspace tabs. The workspace page renders them;
// pipeline stages deep-link to them via FlowStage.labTab.
export const LAB_TABS = [
  { key: "ideation", label: "Ideation Lab" },
  { key: "collection", label: "Collection Lab" },
  { key: "field", label: "Field Lab" },
  { key: "panel", label: "Panel" },
  { key: "personas", label: "Persona Lab" },
  { key: "qual", label: "Qual Studio" },
  { key: "signal", label: "Signal Lab" },
  { key: "insight", label: "Insight Lab" },
  { key: "papers", label: "Paper Lab" },
  { key: "learning", label: "Learning Lab" },
  { key: "deliver", label: "Deliverables" },
  { key: "pipeline", label: "Pipeline" },
  { key: "llm", label: "LLM Activity" },
] as const;

export type LabTabKey = (typeof LAB_TABS)[number]["key"];

export function labTabLabel(key: string): string {
  return LAB_TABS.find((t) => t.key === key)?.label ?? key;
}
