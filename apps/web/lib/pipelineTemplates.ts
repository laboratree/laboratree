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
