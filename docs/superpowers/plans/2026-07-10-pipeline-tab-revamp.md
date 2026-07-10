# Pipeline Tab Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Pipeline tab as a phase-grouped React Flow canvas ("calm editorial" style) with rich stage cards, a "closer look" drawer, and real lab deep-links that switch the workspace tab.

**Architecture:** The 341-line `apps/web/components/PipelineLab.tsx` is split into a `components/pipeline/` package: a container (state + API calls), two custom React Flow node components (stage card, phase lane), a detail drawer, a pure layout function, and shared types. Phase grouping comes from a new `FlowPhase` layer in `lib/pipelineTemplates.ts`; the lab deep-link contract is a new typed `lib/labTabs.ts` registry consumed by both the workspace page and the pipeline.

**Tech Stack:** Next.js 15, React, TypeScript 5.7 (strict), Tailwind 3.4, `@xyflow/react` v12, papaparse. Spec: `docs/superpowers/specs/2026-07-10-pipeline-tab-revamp-design.md`.

## Global Constraints

- **Zero new dependencies.** Animations are CSS keyframes in `apps/web/app/globals.css`; icons are emoji/unicode as in the existing code.
- **Theme tokens** (from `apps/web/tailwind.config.ts`): `bg #FBFDF9`, `forest #14342A`, `leaf #6DB33F`, `sprout #A8D08D`, `ink #1E2A22`, `muted #5B6B60`, `line #E4EBE1`. Fixed accents used by the design: lab-blue `#2563EB` on `#EDF4FB`, run-green `#3E7D32` on `#EAF4E2`, running-amber `#F59E0B`/`amber-50`.
- **No backend changes.** All state is client-side and resets on template load (same lifetime as today).
- **`apps/web` has no unit-test runner** and the no-new-deps rule forbids adding one. The per-task verification cycle is: `npx tsc --noEmit` + `npm run lint` (both from `apps/web`), plus the end-to-end Playwright smoke in Task 7.
- **Commits:** conventional messages. **Never add a `Co-Authored-By: Claude` trailer in this repo.**
- All commands below run from the repo root `c:\Users\Sourav Mondal\Desktop\Projects\Laboratree` unless the step says otherwise.

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `apps/web/lib/labTabs.ts` | Create | Single typed registry of workspace tabs (key + label) |
| `apps/web/app/projects/[id]/page.tsx` | Modify | Consume `LAB_TABS`; pass `onOpenLab` into PipelineLab |
| `apps/web/lib/pipelineTemplates.ts` | Modify | Add `FlowPhase`, `phases` per template, `phase` per stage |
| `apps/web/components/pipeline/types.ts` | Create | `StageState`, `StepStatus`, node-data types, kind/status meta |
| `apps/web/components/pipeline/layout.ts` | Create | Pure `buildFlowGraph(stages, phases, …) → {nodes, edges}` |
| `apps/web/components/pipeline/StageNode.tsx` | Create | Custom React Flow node: the phase card |
| `apps/web/components/pipeline/LaneNode.tsx` | Create | Custom React Flow node: phase-lane background + header |
| `apps/web/components/pipeline/StageDrawer.tsx` | Create | "Closer look" panel |
| `apps/web/components/pipeline/PipelineLab.tsx` | Create | Container: state, API calls, header strip, canvas + drawer grid |
| `apps/web/components/PipelineLab.tsx` | Delete | Replaced by the package above |
| `apps/web/app/globals.css` | Modify | `stage-pulse` and `drawer-in` keyframes |

---

### Task 1: Typed lab-tab registry

**Files:**
- Create: `apps/web/lib/labTabs.ts`
- Modify: `apps/web/app/projects/[id]/page.tsx` (lines 30–45: the `TABS` const and `TabKey` type)

**Interfaces:**
- Consumes: nothing.
- Produces: `LAB_TABS: readonly {key, label}[]`, `type LabTabKey` (union of tab keys), `labTabLabel(key: string): string`. Later tasks import all three from `@/lib/labTabs`.

- [ ] **Step 1: Create `apps/web/lib/labTabs.ts`**

```ts
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
```

- [ ] **Step 2: Replace the inline tab list in `apps/web/app/projects/[id]/page.tsx`**

Delete the `TABS` const and `TabKey` type (currently lines 30–45) and use the registry. The
diff is exactly:

```tsx
// add to imports:
import { LAB_TABS, type LabTabKey } from "@/lib/labTabs";

// delete the whole `const TABS = [...] as const;` block and
// `type TabKey = (typeof TABS)[number]["key"];`, then:
type TabKey = LabTabKey;
```

In the JSX, change `{TABS.map((t) => (` to `{LAB_TABS.map((t) => (`. Nothing else changes in
this task (the `onOpenLab` wiring happens in Task 6).

- [ ] **Step 3: Typecheck and lint**

Run (in `apps/web`): `npx tsc --noEmit && npm run lint`
Expected: no errors (lint may print pre-existing warnings; only new errors block).

- [ ] **Step 4: Commit**

```bash
git add apps/web/lib/labTabs.ts "apps/web/app/projects/[id]/page.tsx"
git commit -m "refactor(web): extract typed lab-tab registry to lib/labTabs"
```

---

### Task 2: Phase layer in the flow templates

**Files:**
- Modify: `apps/web/lib/pipelineTemplates.ts` (full-file rewrite below)

**Interfaces:**
- Consumes: `LabTabKey` from Task 1.
- Produces: `type FlowPhase = { key; title; blurb }`, `CUSTOM_PHASE: FlowPhase`,
  `FlowTemplate.phases: FlowPhase[]`, `FlowStage.phase: string`,
  `FlowStage.labTab?: LabTabKey`. Everything else (`FlowNodeKind`, `FLOW_TEMPLATES`,
  template exports) keeps its current name and shape.

- [ ] **Step 1: Rewrite `apps/web/lib/pipelineTemplates.ts`**

Full new content (stage ids, componentIds, params, and descriptions are unchanged from the
current file; NGO labels lose their hardcoded `"1 · "` prefixes because the node card now
renders a derived phase number):

```ts
// Pre-configured end-to-end flows for the Pipeline canvas (n8n-style).
// Node kinds: "component" runs a registered component in the pipeline executor;
// "lab" deep-links a stage owned by a Lab tab; "manual" is a human/offline stage.
// Stages are grouped into FlowPhases — the canvas renders one lane per phase.

import type { LabTabKey } from "@/lib/labTabs";

export type FlowNodeKind = "component" | "lab" | "manual";

export type FlowPhase = {
  key: string;
  title: string;
  blurb: string;
};

// Lane for user-added stages (blank canvas / "+ stage" buttons) and unknown phase keys.
export const CUSTOM_PHASE: FlowPhase = {
  key: "custom",
  title: "Custom",
  blurb: "stages you added",
};

export type FlowStage = {
  id: string;
  label: string;
  kind: FlowNodeKind;
  description: string;
  phase: string;                        // FlowPhase.key
  componentId?: string;                 // kind === "component"
  params?: Record<string, unknown>;
  labTab?: LabTabKey;                   // kind === "lab" → workspace tab key
};

export type FlowTemplate = {
  key: string;
  name: string;
  tagline: string;
  phases: FlowPhase[];
  stages: FlowStage[];
};

export const RESEARCH_FIRM_FLOW: FlowTemplate = {
  key: "research-firm",
  name: "Research firm — end to end",
  tagline: "Client brief → hypotheses → survey → analysis → recommendation",
  phases: [
    { key: "understand", title: "Understand", blurb: "brief → questions → evidence" },
    { key: "design", title: "Design", blurb: "method → instrument → pilot" },
    { key: "field", title: "Field", blurb: "recruit → collect → interviews" },
    { key: "analyze", title: "Analyze", blurb: "clean → explore → model → red-team" },
    { key: "decide", title: "Decide", blurb: "insights → recommendations" },
    { key: "monitor", title: "Deliver & Monitor", blurb: "present → decide → track" },
  ],
  stages: [
    { id: "brief", label: "Client requirement", kind: "manual", phase: "understand",
      description: "Capture the business problem, budget, timeline, target population." },
    { id: "problem", label: "Problem definition", kind: "manual", phase: "understand",
      description: "Translate the business question into testable research questions." },
    { id: "market", label: "Market & competitor scan", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Evidence Hunt: industry reports, competitor pricing, trends — cited sources." },
    { id: "lit", label: "Literature review", kind: "lab", labTab: "papers", phase: "understand",
      description: "Paper Lab: upload/understand prior papers; chat with the evidence." },
    { id: "hypo", label: "Hypothesis formation", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Ideation Lab: Co-Scientist generates and Elo-ranks grounded hypotheses." },
    { id: "design", label: "Research design", kind: "lab", labTab: "collection", phase: "design",
      description: "Collection Lab: choose design; power/sample-size planning." },
    { id: "quest", label: "Questionnaire design", kind: "lab", labTab: "collection", phase: "design",
      description: "Collection Lab: draft the instrument, run the bias check." },
    { id: "pilot", label: "Pilot / twin dry-run", kind: "lab", labTab: "field", phase: "design",
      description: "Field Lab: synthetic-twin dry-run predicts drop-off and confusion pre-spend." },
    { id: "sampling", label: "Sampling & panel", kind: "lab", labTab: "panel", phase: "field",
      description: "Panel: recruit/import respondents, record consent, segment." },
    { id: "collect", label: "Data collection", kind: "lab", labTab: "field", phase: "field",
      description: "Field Lab: publish the survey; quotas, fraud flags, live monitor." },
    { id: "qual", label: "Interviews & testimony", kind: "lab", labTab: "qual", phase: "field",
      description: "Qual Studio: transcribe, code, extract Evidence-locked quotes." },
    { id: "clean", label: "Data cleaning", kind: "component", phase: "analyze",
      componentId: "transform.mean_impute", params: {},
      description: "Impute missing values (runnable — swap for any transform)." },
    { id: "dedupe", label: "Deduplicate", kind: "component", phase: "analyze",
      componentId: "transform.drop_duplicates", params: {},
      description: "Drop duplicate rows before analysis." },
    { id: "eda", label: "Exploratory analysis", kind: "component", phase: "analyze",
      componentId: "analyzer.eda_profile", params: {},
      description: "Distributions, missingness, correlations — Evidence-locked." },
    { id: "model", label: "Statistical / ML model", kind: "component", phase: "analyze",
      componentId: "model.ml.logistic_regression", params: {},
      description: "Fit the primary model (swap for any of the ~35 zoo models)." },
    { id: "redteam", label: "Red-team the model", kind: "component", phase: "analyze",
      componentId: "critic.red_team", params: {},
      description: "Adversarial robustness/subgroup/leakage checks gate acceptance." },
    { id: "viz", label: "Visualization", kind: "lab", labTab: "insight", phase: "decide",
      description: "Insight Lab: charts, trend decomposition, decision tools." },
    { id: "insights", label: "Business insights", kind: "manual", phase: "decide",
      description: "Answer the 'so what?' — drivers, sizes, contrasts, caveats." },
    { id: "reco", label: "Recommendations", kind: "manual", phase: "decide",
      description: "Evidence-backed actions; every number traces to a run." },
    { id: "present", label: "Client presentation", kind: "lab", labTab: "llm", phase: "monitor",
      description: "Report card + deliverables; trust score on the back page." },
    { id: "decide", label: "Client decision", kind: "manual", phase: "monitor",
      description: "The client acts; log the decision for the learning loop." },
    { id: "tracking", label: "Post-launch tracking", kind: "lab", labTab: "field", phase: "monitor",
      description: "Follow-up waves measure outcomes (sales lift, satisfaction, ROI) over time." },
  ],
};

export const POLICY_FIRM_FLOW: FlowTemplate = {
  key: "policy-firm",
  name: "Policy research — end to end",
  tagline: "Policy problem → theory of change → evaluation → brief → M&E",
  phases: [
    { key: "understand", title: "Understand", blurb: "problem → stakeholders → objectives" },
    { key: "design", title: "Design", blurb: "evaluation design" },
    { key: "field", title: "Field", blurb: "surveys → interviews" },
    { key: "analyze", title: "Analyze", blurb: "clean → estimate → impact" },
    { key: "decide", title: "Decide", blurb: "CBA → scenarios → recommendation" },
    { key: "monitor", title: "Deliver & Monitor", blurb: "brief → decision → M&E" },
  ],
  stages: [
    { id: "problem", label: "Policy problem", kind: "manual", phase: "understand",
      description: "Identify the public issue and the commissioning body's question." },
    { id: "stakeholders", label: "Stakeholder mapping", kind: "manual", phase: "understand",
      description: "Map citizens, operators, government, business — who gains, who bears cost." },
    { id: "lit", label: "Literature & policy review", kind: "lab", labTab: "papers", phase: "understand",
      description: "Paper Lab: prior evaluations, case studies, 'has this worked elsewhere?'" },
    { id: "objectives", label: "Policy objectives", kind: "manual", phase: "understand",
      description: "Define measurable objectives the policy must achieve." },
    { id: "toc", label: "Theory of change", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Make the causal chain explicit; assumptions become testable hypotheses." },
    { id: "design", label: "Research design", kind: "lab", labTab: "collection", phase: "design",
      description: "Surveys, admin data, RCT/quasi-experimental design, mixed methods." },
    { id: "collect", label: "Primary collection", kind: "lab", labTab: "field", phase: "field",
      description: "Field Lab + Panel: household surveys with quotas and quality flags." },
    { id: "interviews", label: "Interviews & focus groups", kind: "lab", labTab: "qual", phase: "field",
      description: "Qual Studio: stakeholder interviews, coded themes, verbatim quotes." },
    { id: "clean", label: "Validation & cleaning", kind: "component", phase: "analyze",
      componentId: "transform.mean_impute", params: {},
      description: "Impute/clean before estimation (swap for any transform)." },
    { id: "eda", label: "Exploratory analysis", kind: "component", phase: "analyze",
      componentId: "analyzer.eda_profile", params: {},
      description: "Know the data before estimating effects." },
    { id: "econ", label: "Econometric analysis", kind: "component", phase: "analyze",
      componentId: "model.econometrics.ols", params: {},
      description: "Regression/panel methods (swap for logit/probit/ARIMA/DiD when built)." },
    { id: "impact", label: "Impact evaluation", kind: "component", phase: "analyze",
      componentId: "analyzer.causal_impact", params: {},
      description: "Did the policy move the outcome? Counterfactual vs actual." },
    { id: "cba", label: "Cost–benefit analysis", kind: "component", phase: "decide",
      componentId: "decision.expected_value", params: {},
      description: "Benefits vs costs under explicit assumptions — inspectable arithmetic." },
    { id: "scenarios", label: "Scenario simulation", kind: "component", phase: "decide",
      componentId: "decision.threshold_rule", params: {},
      description: "Compare policy variants A/B/C against decision rules." },
    { id: "reco", label: "Policy recommendation", kind: "manual", phase: "decide",
      description: "Expand / modify / pilot further / end — grounded in the evidence above." },
    { id: "consult", label: "Stakeholder consultation", kind: "manual", phase: "decide",
      description: "Review findings with officials, NGOs, experts; capture objections." },
    { id: "brief", label: "Policy brief", kind: "lab", labTab: "llm", phase: "monitor",
      description: "Report card + brief: summary, evidence, recommendations, limitations." },
    { id: "decision", label: "Government decision", kind: "manual", phase: "monitor",
      description: "Implement, revise, delay, reject, or scale." },
    { id: "mne", label: "Monitoring & evaluation", kind: "lab", labTab: "field", phase: "monitor",
      description: "Follow-up waves track implementation and outcomes over time." },
  ],
};

// The full NGO policy-research lifecycle (Bright Future Foundation education example).
// Every phase maps to a runnable component, a Lab tab, or a human stage — one activatable flow.
export const NGO_POLICY_FLOW: FlowTemplate = {
  key: "ngo-policy",
  name: "NGO policy research (education)",
  tagline: "Problem → evidence → design → personas → field → analysis → impact → recommend → monitor",
  phases: [
    { key: "understand", title: "Understand", blurb: "problem → evidence → hypotheses" },
    { key: "design", title: "Design", blurb: "method → personas → instrument" },
    { key: "field", title: "Field", blurb: "collect in the real world" },
    { key: "analyze", title: "Analyze", blurb: "clean → explore → model" },
    { key: "decide", title: "Decide", blurb: "prioritize → design → pilot" },
    { key: "monitor", title: "Impact & Monitor", blurb: "evaluate → recommend → track" },
  ],
  stages: [
    { id: "intake", label: "Problem intake", kind: "lab", labTab: "signal", phase: "understand",
      description: "Signal Lab: ingest the proposal, budget, meeting notes → mission, goal, budget, timeline." },
    { id: "stakeholders", label: "Stakeholder mapping", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Map students, parents, teachers, schools, government, NGOs and their relationships." },
    { id: "background", label: "Background research", kind: "lab", labTab: "papers", phase: "understand",
      description: "Paper Lab: UDISE+/ASER/UNICEF reports → knowledge base of dropout drivers." },
    { id: "questions", label: "Research questions", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Ideation: why are students absent? what causes dropout? highest-impact intervention?" },
    { id: "hypotheses", label: "Hypotheses", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Co-Scientist: financial hardship / distance / teacher absenteeism drive dropout." },
    { id: "design", label: "Research design", kind: "lab", labTab: "collection", phase: "design",
      description: "Collection: survey + interview + sampling + ethics + power/sample-size." },
    { id: "personas", label: "Persona simulation", kind: "lab", labTab: "personas", phase: "design",
      description: "Persona Lab: synthetic students/families stress-test the survey before fielding." },
    { id: "questionnaire", label: "Questionnaire", kind: "lab", labTab: "field", phase: "design",
      description: "Field Lab: build the KAP survey, skip logic, translation, validation." },
    { id: "field", label: "Field survey", kind: "lab", labTab: "field", phase: "field",
      description: "Collect responses; interviews → Qual Studio; photos/GPS; fraud checks." },
    { id: "clean", label: "Clean data", kind: "component", phase: "analyze",
      componentId: "transform.mean_impute", params: {},
      description: "Impute missing values in the unified dataset." },
    { id: "eda", label: "Exploratory analysis", kind: "component", phase: "analyze",
      componentId: "analyzer.eda_profile", params: {},
      description: "Distributions, missingness, correlations — Evidence-locked." },
    { id: "crosstab", label: "Dropout crosstab", kind: "component", phase: "analyze",
      componentId: "analyzer.crosstab", params: { banner: "gender", stub: "dropout" },
      description: "Dropout by gender with significance letters (girls far from school hit hardest)." },
    { id: "model", label: "Dropout model", kind: "component", phase: "analyze",
      componentId: "model.ml.logistic_regression", params: { target: "dropout" },
      description: "Predict dropout from distance/income/attendance; red-team the model." },
    { id: "prioritize", label: "Prioritize problems", kind: "component", phase: "decide",
      componentId: "decision.expected_value",
      params: { options: [
        { label: "Free bicycles (transport)", value: 0.75, probability: 0.85 },
        { label: "Scholarships (cost)", value: 0.65, probability: 0.70 },
        { label: "Libraries", value: 0.40, probability: 0.90 },
      ] },
      description: "Cost-impact ranking: transport vs scholarships vs libraries." },
    { id: "intervention", label: "Intervention design", kind: "manual", phase: "decide",
      description: "Design the intervention portfolio (bicycles, scholarships, tutoring) with cost/reach/risk." },
    { id: "pilot", label: "Pilot", kind: "lab", labTab: "field", phase: "decide",
      description: "Field a pilot; monitor attendance, learning, cost, satisfaction." },
    { id: "impact", label: "Impact evaluation", kind: "lab", labTab: "field", phase: "monitor",
      description: "DiD on before/after pilot panel data (the demo seed runs model.causal.did on the bicycle pilot — see Evidence). Real studies: field a second wave first." },
    { id: "recommend", label: "Recommendations", kind: "lab", labTab: "deliver", phase: "monitor",
      description: "Deliverables: Evidence-bound recommendations + budget allocation + scaling plan." },
    { id: "monitor", label: "Monitor & improve", kind: "lab", labTab: "deliver", phase: "monitor",
      description: "Live dashboard: KPI tracking, trends, quarterly + impact reports." },
  ],
};

export const FLOW_TEMPLATES: FlowTemplate[] = [
  NGO_POLICY_FLOW, RESEARCH_FIRM_FLOW, POLICY_FIRM_FLOW,
];
```

- [ ] **Step 2: Typecheck**

Run (in `apps/web`): `npx tsc --noEmit`
Expected: **errors only in `components/PipelineLab.tsx` are NOT acceptable here** — the old
component still compiles because `FlowStage` only gained a field and `labTab` narrowed to
`LabTabKey` (a string subtype). If `tsc` reports errors in `components/PipelineLab.tsx`
about `labTab`, they are pre-existing-usage breaks — fix by importing nothing; the old file
uses `labTab` read-only, so expect **no errors at all**.

- [ ] **Step 3: Commit**

```bash
git add apps/web/lib/pipelineTemplates.ts
git commit -m "feat(web): phase groups in pipeline flow templates"
```

---

### Task 3: Pipeline types, layout function, CSS keyframes

**Files:**
- Create: `apps/web/components/pipeline/types.ts`
- Create: `apps/web/components/pipeline/layout.ts`
- Modify: `apps/web/app/globals.css` (append)

**Interfaces:**
- Consumes: `FlowStage`, `FlowPhase`, `FlowNodeKind`, `CUSTOM_PHASE` from `@/lib/pipelineTemplates`; `PipelineStepResult` from `@/lib/api`.
- Produces (used by Tasks 4–6):
  - `type StepStatus = "idle" | "running" | "succeeded" | "failed"`
  - `type StageState = FlowStage & { status: StepStatus; markedDone: boolean; result?: PipelineStepResult }`
  - `type StageNodeData = { stage: StageState; phaseNumber: number; selected: boolean }`
  - `type LaneNodeData = { title: string; blurb: string; done: number; total: number }`
  - `KIND_META: Record<FlowNodeKind, { badge; hint; badgeClass }>`
  - `stageStatusMeta(s: StageState): { label: string; className: string }`
  - `isStageComplete(s: StageState): boolean`
  - `buildFlowGraph({ stages, phases, selectedId, runInFlight }): { nodes: Node[]; edges: Edge[] }`
  - CSS classes `animate-stage-pulse`, `animate-drawer-in`

- [ ] **Step 1: Create `apps/web/components/pipeline/types.ts`**

```ts
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
```

- [ ] **Step 2: Create `apps/web/components/pipeline/layout.ts`**

```ts
import type { Edge, Node } from "@xyflow/react";
import { CUSTOM_PHASE, type FlowPhase } from "@/lib/pipelineTemplates";
import { isStageComplete, type LaneNodeData, type StageNodeData, type StageState } from "./types";

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
  for (const phase of lanePhases) {
    const members = laneStages.get(phase.key)!;
    if (members.length === 0) continue;
    const rows = Math.ceil(members.length / WRAP_AT);
    const laneH = LANE_HEADER_H + rows * CARD_H + (rows - 1) * GAP_Y + LANE_PAD_BOTTOM;

    const laneData: LaneNodeData = {
      title: phase.title,
      blurb: phase.blurb,
      done: members.filter(isStageComplete).length,
      total: members.length,
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
```

- [ ] **Step 3: Append the keyframes to `apps/web/app/globals.css`**

```css

/* Pipeline canvas motion — used by components/pipeline */
@keyframes stage-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.35); }
  50% { box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); }
}
.animate-stage-pulse { animation: stage-pulse 1.6s ease-out infinite; }

@keyframes drawer-in {
  from { opacity: 0; transform: translateX(12px); }
  to { opacity: 1; transform: translateX(0); }
}
.animate-drawer-in { animation: drawer-in 0.18s ease-out; }
```

- [ ] **Step 4: Typecheck**

Run (in `apps/web`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/pipeline/types.ts apps/web/components/pipeline/layout.ts apps/web/app/globals.css
git commit -m "feat(web): pipeline stage types, lane layout engine, canvas keyframes"
```

---

### Task 4: StageNode and LaneNode custom nodes

**Files:**
- Create: `apps/web/components/pipeline/StageNode.tsx`
- Create: `apps/web/components/pipeline/LaneNode.tsx`

**Interfaces:**
- Consumes: `StageNodeData`, `LaneNodeData`, `KIND_META`, `stageStatusMeta` (Task 3); `labTabLabel` (Task 1); `CARD_W`, `CARD_H` (Task 3 layout).
- Produces: `StageNode`, `LaneNode` — memoized components registered in Task 6 as `nodeTypes = { stage: StageNode, lane: LaneNode }`. Both render React Flow `Handle`s (left target, right source) so the sequential edges attach.

- [ ] **Step 1: Create `apps/web/components/pipeline/StageNode.tsx`**

```tsx
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
```

- [ ] **Step 2: Create `apps/web/components/pipeline/LaneNode.tsx`**

```tsx
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
```

- [ ] **Step 3: Typecheck and lint**

Run (in `apps/web`): `npx tsc --noEmit && npm run lint`
Expected: no errors. (The components are not imported anywhere yet — that's fine; lint may
flag nothing since both files export their component.)

- [ ] **Step 4: Commit**

```bash
git add apps/web/components/pipeline/StageNode.tsx apps/web/components/pipeline/LaneNode.tsx
git commit -m "feat(web): stage card and phase lane custom nodes for pipeline canvas"
```

---

### Task 5: The "closer look" drawer

**Files:**
- Create: `apps/web/components/pipeline/StageDrawer.tsx`

**Interfaces:**
- Consumes: `StageState`, `KIND_META`, `stageStatusMeta` (Task 3); `FlowPhase`, `CUSTOM_PHASE` from `@/lib/pipelineTemplates`; `LabTabKey`, `labTabLabel` (Task 1); `ComponentSpecLite` from `@/lib/api`; existing `@/components/ProvenanceBadge` (props: `{ runId: string }`).
- Produces: default export `StageDrawer` with props:
  ```ts
  type StageDrawerProps = {
    stages: StageState[];
    phases: FlowPhase[];
    selectedId: string;
    components: ComponentSpecLite[];
    onPatch: (id: string, patch: Partial<StageState>) => void;
    onRemove: (id: string) => void;
    onSelect: (id: string) => void;
    onOpenLab?: (tab: LabTabKey) => void;
  };
  ```
  **The container must render it with `key={selectedId}`** so per-stage local state
  (params JSON error) resets when the selection changes.

- [ ] **Step 1: Create `apps/web/components/pipeline/StageDrawer.tsx`**

```tsx
"use client";

import { useMemo, useState } from "react";
import { labTabLabel, type LabTabKey } from "@/lib/labTabs";
import { CUSTOM_PHASE, type FlowPhase } from "@/lib/pipelineTemplates";
import type { ComponentSpecLite } from "@/lib/api";
import ProvenanceBadge from "@/components/ProvenanceBadge";
import { KIND_META, stageStatusMeta, type StageState } from "./types";

export type StageDrawerProps = {
  stages: StageState[];
  phases: FlowPhase[];
  selectedId: string;
  components: ComponentSpecLite[];
  onPatch: (id: string, patch: Partial<StageState>) => void;
  onRemove: (id: string) => void;
  onSelect: (id: string) => void;
  onOpenLab?: (tab: LabTabKey) => void;
};

export default function StageDrawer({
  stages, phases, selectedId, components, onPatch, onRemove, onSelect, onOpenLab,
}: StageDrawerProps) {
  const [paramsError, setParamsError] = useState<string | null>(null);

  const index = stages.findIndex((s) => s.id === selectedId);
  const stage = index >= 0 ? stages[index] : null;

  const componentsByKind = useMemo(() => {
    const groups = new Map<string, ComponentSpecLite[]>();
    for (const c of components) {
      const list = groups.get(c.kind) ?? [];
      list.push(c);
      groups.set(c.kind, list);
    }
    return [...groups.entries()];
  }, [components]);

  if (!stage) return null;

  const kind = KIND_META[stage.kind];
  const status = stageStatusMeta(stage);
  const phase =
    phases.find((p) => p.key === stage.phase) ?? CUSTOM_PHASE;
  const prev = index > 0 ? stages[index - 1] : null;
  const next = index < stages.length - 1 ? stages[index + 1] : null;

  return (
    <div className="animate-drawer-in rounded-2xl border border-line border-l-4 border-l-leaf bg-white p-4">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold tracking-wider text-muted">
          CLOSER LOOK · PHASE {index + 1} · {phase.title.toUpperCase()}
        </span>
        <button
          onClick={() => onRemove(stage.id)}
          className="text-xs text-red-600 hover:underline"
        >
          remove
        </button>
      </div>

      <input
        value={stage.label}
        onChange={(e) => onPatch(stage.id, { label: e.target.value })}
        className="mt-2 w-full rounded-lg border border-line px-2 py-1.5 font-display text-base text-forest"
      />

      <div className="mt-2 flex items-center gap-2">
        <span
          title={kind.hint}
          className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${kind.badgeClass}`}
        >
          {kind.badge}
          {stage.kind === "lab" && stage.labTab ? ` · ${labTabLabel(stage.labTab)}` : ""}
        </span>
        <span className={`text-xs font-semibold ${status.className}`}>{status.label}</span>
      </div>

      <label className="mt-3 block text-xs text-muted">What happens here</label>
      <textarea
        value={stage.description}
        onChange={(e) => onPatch(stage.id, { description: e.target.value })}
        rows={3}
        className="mt-1 w-full rounded-lg border border-line px-2 py-1.5 text-xs"
      />

      {stage.kind === "lab" && stage.labTab && (
        <button
          onClick={() => onOpenLab?.(stage.labTab!)}
          disabled={!onOpenLab}
          className="mt-3 w-full rounded-lg bg-[#2563EB] py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
        >
          Open in {labTabLabel(stage.labTab)} →
        </button>
      )}

      {stage.kind !== "component" && (
        <label className="mt-3 flex items-center gap-2 text-xs text-muted">
          <input
            type="checkbox"
            checked={stage.markedDone}
            onChange={(e) => onPatch(stage.id, { markedDone: e.target.checked })}
            className="h-3.5 w-3.5 accent-leaf"
          />
          Mark stage complete
        </label>
      )}

      {stage.kind === "component" && (
        <div className="mt-3 space-y-2">
          <label className="block text-xs text-muted">Component</label>
          {components.length === 0 ? (
            <p className="text-xs text-muted">No components loaded — is the API running?</p>
          ) : (
            <select
              value={stage.componentId ?? ""}
              onChange={(e) => onPatch(stage.id, { componentId: e.target.value })}
              className="w-full rounded-lg border border-line px-2 py-1.5 text-sm"
            >
              {componentsByKind.map(([groupKind, list]) => (
                <optgroup key={groupKind} label={groupKind}>
                  {list.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          )}

          <label className="block text-xs text-muted">Params (JSON)</label>
          <textarea
            defaultValue={JSON.stringify(stage.params ?? {}, null, 0)}
            onBlur={(e) => {
              try {
                onPatch(stage.id, { params: JSON.parse(e.target.value || "{}") });
                setParamsError(null);
              } catch {
                setParamsError("Invalid JSON — not saved.");
              }
            }}
            rows={3}
            className={`w-full rounded-lg border px-2 py-1.5 font-mono text-xs ${
              paramsError ? "border-red-400" : "border-line"
            }`}
          />
          {paramsError && <p className="text-xs text-red-600">{paramsError}</p>}

          {stage.result && (
            <div className="rounded-lg bg-bg p-2">
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    stage.status === "succeeded"
                      ? "bg-leaf/20 text-forest"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {stage.status}
                  {stage.result.evidence_count != null
                    ? ` · 🔒 ${stage.result.evidence_count} evidence`
                    : ""}
                </span>
                {stage.result.run_id && <ProvenanceBadge runId={stage.result.run_id} />}
              </div>
              {stage.result.error && (
                <p className="mt-1 text-xs text-red-600">{stage.result.error}</p>
              )}
              {stage.result.preview != null && (
                <pre className="mt-2 max-h-40 overflow-auto text-[10px] text-ink">
                  {JSON.stringify(stage.result.preview, null, 1).slice(0, 1000)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      <div className="mt-4 flex items-center justify-between border-t border-line pt-2 text-xs">
        {prev ? (
          <button onClick={() => onSelect(prev.id)} className="text-muted hover:text-forest">
            ← {index} · {prev.label}
          </button>
        ) : (
          <span />
        )}
        {next ? (
          <button onClick={() => onSelect(next.id)} className="text-muted hover:text-forest">
            {index + 2} · {next.label} →
          </button>
        ) : (
          <span />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck and lint**

Run (in `apps/web`): `npx tsc --noEmit && npm run lint`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/pipeline/StageDrawer.tsx
git commit -m "feat(web): closer-look drawer for pipeline stages"
```

---

### Task 6: Container, page wiring, old component removal

**Files:**
- Create: `apps/web/components/pipeline/PipelineLab.tsx`
- Modify: `apps/web/app/projects/[id]/page.tsx` (PipelineLab import + usage)
- Delete: `apps/web/components/PipelineLab.tsx`

**Interfaces:**
- Consumes: everything produced by Tasks 1–5; `Api.listComponents`, `Api.runPipeline`, `demoApi.seed`, `PipelineResult` from `@/lib/api`; `FileDropzone` (props: `{ multiple, accept, hint, onFiles }`); `Papa.parse` from `papaparse`.
- Produces: default export `PipelineLab` with props `{ projectId: string; onOpenLab?: (tab: LabTabKey) => void }`.

- [ ] **Step 1: Create `apps/web/components/pipeline/PipelineLab.tsx`**

```tsx
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Background, Controls, ReactFlow, type NodeTypes } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import Papa from "papaparse";
import { Api, demoApi, type ComponentSpecLite, type PipelineResult } from "@/lib/api";
import { FLOW_TEMPLATES, type FlowNodeKind, type FlowPhase } from "@/lib/pipelineTemplates";
import type { LabTabKey } from "@/lib/labTabs";
import FileDropzone from "@/components/FileDropzone";
import { buildFlowGraph } from "./layout";
import { LaneNode } from "./LaneNode";
import { StageNode } from "./StageNode";
import StageDrawer from "./StageDrawer";
import { isStageComplete, KIND_META, type StageState, type StepStatus } from "./types";

// Registered once at module scope — React Flow requires a stable nodeTypes reference.
const nodeTypes: NodeTypes = { stage: StageNode, lane: LaneNode };

export type PipelineLabProps = {
  projectId: string;
  onOpenLab?: (tab: LabTabKey) => void;
};

export default function PipelineLab({ projectId, onOpenLab }: PipelineLabProps) {
  const [components, setComponents] = useState<ComponentSpecLite[]>([]);
  const [stages, setStages] = useState<StageState[]>([]);
  const [phases, setPhases] = useState<FlowPhase[]>([]);
  const [flowName, setFlowName] = useState("Blank canvas");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Api.listComponents().then((r) => setComponents(r.components)).catch(() => setComponents([]));
  }, []);

  const loadTemplate = useCallback((key: string) => {
    const template = FLOW_TEMPLATES.find((t) => t.key === key);
    if (!template) return;
    setFlowName(template.name);
    setPhases(template.phases);
    setStages(
      template.stages.map((s) => ({ ...s, status: "idle" as StepStatus, markedDone: false })),
    );
    setSelectedId(null);
    setError(null);
  }, []);

  function loadCsv(files: File[]) {
    Papa.parse<Record<string, unknown>>(files[0], {
      header: true, dynamicTyping: true, skipEmptyLines: true,
      complete: (res) => { setRows(res.data); setFileName(files[0].name); },
    });
  }

  function addStage(kind: FlowNodeKind) {
    const id = `n${Date.now()}`;
    const base = { id, phase: "custom", status: "idle" as StepStatus, markedDone: false };
    const stage: StageState = kind === "component"
      ? { ...base, kind, label: components[0]?.name ?? "Component",
          description: "Runnable step.", componentId: components[0]?.id, params: {} }
      : { ...base, kind, label: kind === "lab" ? "Lab stage" : "Manual stage",
          description: "Describe this stage." };
    setStages((s) => [...s, stage]);
    setSelectedId(id);
  }

  function updateStage(id: string, patch: Partial<StageState>) {
    setStages((all) => all.map((s) => (s.id === id ? { ...s, ...patch } : s)));
  }

  function removeStage(id: string) {
    setStages((all) => all.filter((s) => s.id !== id));
    if (selectedId === id) setSelectedId(null);
  }

  async function runFlow() {
    const runnable = stages.filter((s) => s.kind === "component" && s.componentId);
    if (runnable.length === 0) {
      setError("No runnable component stages in this flow.");
      return;
    }
    setBusy(true);
    setError(null);
    // A run only touches component stages — lab/manual completion belongs to the user.
    setStages((all) =>
      all.map((s) =>
        s.kind === "component"
          ? { ...s, status: "running" as StepStatus, result: undefined }
          : s,
      ),
    );
    try {
      const result: PipelineResult = await Api.runPipeline(projectId, {
        steps: runnable.map((s) => ({ component_id: s.componentId!, params: s.params ?? {} })),
        dataset: rows.length ? rows : null,
      });
      setStages((all) => {
        let i = 0;
        return all.map((s) => {
          if (s.kind !== "component" || !s.componentId) return s;
          const step = result.steps[i++];
          return {
            ...s,
            status: (step?.status === "succeeded" ? "succeeded" : "failed") as StepStatus,
            result: step,
          };
        });
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "pipeline run failed");
      setStages((all) =>
        all.map((s) => (s.status === "running" ? { ...s, status: "failed" as StepStatus } : s)),
      );
    } finally {
      setBusy(false);
    }
  }

  async function seedDemo() {
    setBusy(true);
    setError(null);
    try {
      const seed = await demoApi.seed(projectId);
      setRows(seed.rows);
      setFileName(`demo · ${seed.scenario}`);
      loadTemplate("ngo-policy");
    } catch (e) {
      setError(e instanceof Error ? `seed failed: ${e.message}` : "seed failed");
    } finally {
      setBusy(false);
    }
  }

  const graph = useMemo(
    () => buildFlowGraph({ stages, phases, selectedId, runInFlight: busy }),
    [stages, phases, selectedId, busy],
  );

  const runnableCount = stages.filter((s) => s.kind === "component").length;
  const completeCount = stages.filter(isStageComplete).length;
  const progressPct = stages.length
    ? Math.round((completeCount / stages.length) * 100)
    : 0;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-line bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-[240px]">
            <h2 className="font-display text-xl text-forest">
              {flowName}
              <span className="ml-2 text-sm text-muted">
                · {stages.length} phases · {runnableCount} runnable
              </span>
            </h2>
            <div className="mt-2 flex items-center gap-2">
              <div className="h-1.5 w-56 overflow-hidden rounded-full bg-[#EEF3EA]">
                <div
                  className="h-full rounded-full bg-leaf transition-all duration-500"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <span className="text-xs text-muted">
                {completeCount} / {stages.length} complete
              </span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {FLOW_TEMPLATES.map((t) => (
              <button
                key={t.key}
                onClick={() => loadTemplate(t.key)}
                title={t.tagline}
                className="rounded-full border border-leaf px-3 py-1.5 text-sm text-forest hover:bg-leaf/10"
              >
                {t.name}
              </button>
            ))}
            <button
              onClick={seedDemo}
              disabled={busy}
              title="Seed a realistic NGO education scenario (dataset + evidence + survey + personas) and load the flow"
              className="rounded-full bg-forest px-3 py-1.5 text-sm text-white hover:bg-forest/90 disabled:opacity-50"
            >
              🌱 Load demo scenario
            </button>
            <button
              onClick={() => {
                setStages([]); setPhases([]); setFlowName("Blank canvas"); setSelectedId(null);
              }}
              className="rounded-full border border-line px-3 py-1.5 text-sm text-ink/60 hover:bg-bg"
            >
              Clear
            </button>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          <button onClick={() => addStage("component")}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg">
            + ⚙️ Component
          </button>
          <button onClick={() => addStage("lab")}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg">
            + 🧪 Lab stage
          </button>
          <button onClick={() => addStage("manual")}
            className="rounded-lg border border-line px-3 py-1.5 text-forest hover:bg-bg">
            + 👤 Manual stage
          </button>
          <span className="mx-2 h-5 w-px bg-line" />
          <button onClick={runFlow} disabled={busy || runnableCount === 0}
            className="rounded-lg bg-leaf px-4 py-1.5 font-medium text-white hover:opacity-90 disabled:opacity-50">
            {busy ? "Running…" : `▶ Run ${runnableCount} runnable step${runnableCount === 1 ? "" : "s"}`}
          </button>
          <span className="mx-2 h-5 w-px bg-line" />
          {(Object.keys(KIND_META) as (keyof typeof KIND_META)[]).map((k) => (
            <span
              key={k}
              title={KIND_META[k].hint}
              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${KIND_META[k].badgeClass}`}
            >
              {KIND_META[k].badge}
            </span>
          ))}
        </div>

        <div className="mt-3">
          <FileDropzone multiple={false} accept=".csv"
            hint={rows.length ? `${fileName} · ${rows.length} rows` : "Drop a starting CSV for the runnable steps (optional)"}
            onFiles={loadCsv} />
        </div>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </div>

      {stages.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
          <div className="h-[560px] overflow-hidden rounded-2xl border border-line bg-white">
            <ReactFlow
              nodes={graph.nodes}
              edges={graph.edges}
              nodeTypes={nodeTypes}
              nodesDraggable={false}
              nodesConnectable={false}
              onNodeClick={(_, node) => {
                if (node.type === "stage") setSelectedId(node.id);
              }}
              onPaneClick={() => setSelectedId(null)}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background color="#E4EBE1" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>

          {selectedId ? (
            <StageDrawer
              key={selectedId}
              stages={stages}
              phases={phases}
              selectedId={selectedId}
              components={components}
              onPatch={updateStage}
              onRemove={removeStage}
              onSelect={setSelectedId}
              onOpenLab={onOpenLab}
            />
          ) : (
            <div className="rounded-2xl border border-line bg-white p-4">
              <p className="text-sm text-ink/50">
                Select a phase on the canvas for a closer look — its story, controls, and
                results appear here.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Wire the page**

In `apps/web/app/projects/[id]/page.tsx`:

1. Replace the PipelineLab loader line
   `const PipelineLab = dyn(() => import("@/components/PipelineLab"));`
   with a direct `dynamic()` call (the shared `dyn` helper types props as
   `{ projectId: string }` only, which would reject `onOpenLab`):

```tsx
const PipelineLab = dynamic(() => import("@/components/pipeline/PipelineLab"), {
  ssr: false,
  loading: TabLoading,
});
```

2. Replace the usage
   `{tab === "pipeline" && <PipelineLab projectId={projectId} />}`
   with:

```tsx
{tab === "pipeline" && <PipelineLab projectId={projectId} onOpenLab={setTab} />}
```

- [ ] **Step 3: Delete the old component**

```bash
git rm apps/web/components/PipelineLab.tsx
```

- [ ] **Step 4: Typecheck and lint**

Run (in `apps/web`): `npx tsc --noEmit && npm run lint`
Expected: no errors, no references left to `@/components/PipelineLab`.
Verify with: `grep -rn "components/PipelineLab" apps/web --include="*.tsx" --include="*.ts"`
Expected: no matches.

- [ ] **Step 5: Commit**

```bash
git add apps/web/components/pipeline/PipelineLab.tsx "apps/web/app/projects/[id]/page.tsx"
git commit -m "feat(web): phase-grouped pipeline canvas with closer-look drawer and lab deep-links"
```

---

### Task 7: End-to-end verification (Playwright smoke)

**Files:**
- No source changes expected; fixes discovered here are committed with focused messages.

**Interfaces:**
- Consumes: the running app. Use the **webapp-testing skill** for Playwright.

- [ ] **Step 1: Start the stack**

```bash
docker compose -f infra/docker-compose.yml up -d
# terminal 2 (background): cd apps/api && uv run uvicorn laboratree.main:app --port 8000
# terminal 3 (background): cd apps/web && npm run dev
```
Wait for `http://localhost:8000/health` to report all stores OK and `http://localhost:3000` to respond. For login, check `apps/web/app/login/page.tsx` / `apps/web/lib/auth.ts` for the dev auth flow (register a throwaway user if the API exposes registration).

- [ ] **Step 2: Drive the Pipeline tab (Playwright, via webapp-testing skill)**

Checklist (spec §8) — capture a screenshot at each ✦:
1. Open a project → **Pipeline** tab.
2. Click template pill "NGO policy research (education)" → ✦ lanes render (Understand / Design / Field / Analyze / Decide / Impact & Monitor), cards show `PHASE n`, kind badges, statuses.
3. Click the "Field survey" card → ✦ drawer opens: `CLOSER LOOK · PHASE 9 · FIELD`, lab badge, description.
4. Click "Open in Field Lab →" → ✦ workspace switches to the Field Lab tab.
5. Return to Pipeline tab (state resets — expected; note it, don't fail on it), reload the NGO template.
6. In the drawer for a lab stage, tick "Mark stage complete" → lane counter and header progress increase.
7. Click "🌱 Load demo scenario", then "▶ Run 6 runnable steps" → ✦ runnable cards pulse amber then settle to `✓ done` with `🔒 n evidence`; lab/manual stages are untouched (no "skipped").
8. Select a runnable stage → drawer shows status pill, ProvenanceBadge, preview; enter invalid JSON in Params → inline "Invalid JSON — not saved." appears, field border red.
9. "Clear" → empty state; "+ 🧪 Lab stage" → card appears in a "Custom" lane.

- [ ] **Step 3: Fix anything found, re-run the failing checklist item, commit fixes**

```bash
git add -A apps/web
git commit -m "fix(web): pipeline canvas smoke-test fixes"
```
(Skip the commit if nothing needed fixing.)

---

## Self-Review Notes

- **Spec coverage:** §1 data model → Tasks 1–2; §2 architecture/layout → Tasks 3, 6; §3 node card → Task 4; §4 lane → Tasks 3–4; §5 drawer → Task 5; §6 run experience/progress/behavior change → Task 6; §7 error handling → Tasks 5–6; §8 verification → Task 7 + per-task typecheck/lint.
- **Type consistency:** `StageNodeData`/`LaneNodeData` live in `types.ts` (Task 3) and are imported by `layout.ts` (Task 3), `StageNode`/`LaneNode` (Task 4); `buildFlowGraph` signature in Task 3 matches the Task 6 call site; `StageDrawerProps` in Task 5 matches Task 6 usage; `LabTabKey` flows Task 1 → 2 → 5 → 6.
- **Known deviation:** no unit tests — `apps/web` has no test runner and the spec forbids new dependencies; verification is typecheck + lint per task and the Task 7 Playwright smoke.
