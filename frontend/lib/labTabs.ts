// Single source of truth for the project-workspace tabs. The workspace page renders them;
// pipeline stages deep-link to them via FlowStage.labTab.
export const LAB_TABS = [
  { key: "ideation", label: "Ideation Lab", short: "Ideation" },
  { key: "collection", label: "Collection Lab", short: "Collection" },
  { key: "field", label: "Field Lab", short: "Field" },
  { key: "panel", label: "Panel", short: "Panel" },
  { key: "personas", label: "Persona Lab", short: "Personas" },
  { key: "qual", label: "Qual Studio", short: "Qual" },
  { key: "signal", label: "Signal Lab", short: "Signal" },
  { key: "insight", label: "Insight Lab", short: "Insight" },
  { key: "papers", label: "Paper Lab", short: "Papers" },
  { key: "learning", label: "Learning Lab", short: "Learning" },
  { key: "deliver", label: "Deliverables", short: "Deliverables" },
  { key: "artifacts", label: "Artifact Store", short: "Artifacts" },
  { key: "spiderweb", label: "SpiderWeb", short: "SpiderWeb" },
  { key: "pipeline", label: "Pipeline", short: "Pipeline" },
  { key: "llm", label: "LLM Activity", short: "LLM" },
] as const;

export type LabTabKey = (typeof LAB_TABS)[number]["key"];

export function labTabLabel(key: string): string {
  return LAB_TABS.find((t) => t.key === key)?.label ?? key;
}

// Compact name for dense navs (the lifecycle rail) — the group eyebrow carries the context.
export function labTabShort(key: string): string {
  return LAB_TABS.find((t) => t.key === key)?.short ?? key;
}

// The workspace nav groups the labs by research-lifecycle phase, mirroring the pipeline
// canvas lanes (same names, same accents) so the whole app reads as one system.
export type LabTabGroup = {
  key: string;
  title: string;
  accent: string; // matches PHASE_ACCENTS on the pipeline canvas
  tabs: LabTabKey[];
};

export const LAB_TAB_GROUPS: LabTabGroup[] = [
  { key: "understand", title: "Understand", accent: "#5B6ECC",
    tabs: ["signal", "papers", "ideation", "spiderweb"] },
  { key: "design", title: "Design", accent: "#0E8A7D",
    tabs: ["collection", "personas"] },
  { key: "field", title: "Field", accent: "#2563EB",
    tabs: ["field", "panel", "qual"] },
  { key: "analyze", title: "Analyze", accent: "#D97706",
    tabs: ["insight", "learning"] },
  { key: "deliver", title: "Deliver", accent: "#3E7D32",
    tabs: ["deliver", "artifacts"] },
  { key: "orchestrate", title: "Orchestrate", accent: "#8B5CF6",
    tabs: ["pipeline", "llm"] },
];
