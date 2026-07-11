// Pre-configured end-to-end flows for the Pipeline canvas — the three use-case flows.
// Node kinds: "component" runs a registered component; "agent" is fulfilled by the DeepAgent
// (supervised runs); "lab" deep-links a stage owned by a Lab tab; "manual" is a human stage.
// Stage ids MATCH the server's flow definitions (api/flows.py) so supervised reports map 1:1.

import type { LabTabKey } from "@/lib/labTabs";

export type FlowNodeKind = "component" | "lab" | "manual" | "agent";

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
  // task-specific picker: only these components are offered for this stage (drawer)
  suggestedComponents?: string[];
  labTab?: LabTabKey;                   // kind === "lab" → workspace tab key
};

export type FlowTemplate = {
  key: string;
  name: string;
  tagline: string;
  phases: FlowPhase[];
  stages: FlowStage[];
};

const CLEAN_SUGGESTIONS = ["transform.mean_impute", "transform.drop_duplicates"];
const EDA_SUGGESTIONS = ["analyzer.eda_profile"];
const TAB_SUGGESTIONS = ["analyzer.crosstab", "analyzer.survey_metrics"];
const MODEL_SUGGESTIONS = [
  "model.ml.logistic_regression", "model.ml.random_forest", "model.ml.gradient_boosting",
];
const DECIDE_SUGGESTIONS = ["decision.expected_value", "decision.threshold_rule"];
const SEGMENT_SUGGESTIONS = [
  "model.clustering.kmeans", "model.clustering.gmm", "model.clustering.hierarchical",
];

export const RESEARCH_FLOW: FlowTemplate = {
  key: "research",
  name: "Research — end to end",
  tagline: "Brief → literature → hypotheses → personas → field → analysis → report",
  phases: [
    { key: "understand", title: "Understand", blurb: "brief → literature → hypotheses" },
    { key: "design", title: "Design", blurb: "method → personas → instrument" },
    { key: "field", title: "Field", blurb: "collect in the real world" },
    { key: "analyze", title: "Analyze", blurb: "clean → explore → model" },
    { key: "monitor", title: "Deliver", blurb: "recommend → track" },
  ],
  stages: [
    { id: "intake", label: "Problem intake", kind: "lab", labTab: "signal", phase: "understand",
      description: "Signal Lab: ingest the brief, data, and prior documents." },
    { id: "literature", label: "Literature review", kind: "agent", phase: "understand",
      description: "DeepAgent: scholarly search (OpenAlex/arXiv) → synthesized, cited review." },
    { id: "hypotheses", label: "Hypotheses", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Co-Scientist: grounded, falsifiable hypotheses — tested against the data." },
    { id: "design", label: "Research design", kind: "lab", labTab: "collection", phase: "design",
      description: "Collection: design + power/sample-size planning." },
    { id: "personas", label: "Persona simulation", kind: "lab", labTab: "personas", phase: "design",
      description: "Persona Lab: synthetic respondents stress-test the instrument." },
    { id: "questionnaire", label: "Questionnaire", kind: "lab", labTab: "field", phase: "design",
      description: "Field Lab: build + publish the instrument (prereg frozen)." },
    { id: "field", label: "Field survey", kind: "lab", labTab: "field", phase: "field",
      description: "Collect responses with quotas and quality flags." },
    { id: "clean", label: "Clean data", kind: "component", phase: "analyze",
      componentId: "transform.mean_impute", params: {}, suggestedComponents: CLEAN_SUGGESTIONS,
      description: "Impute missing values in the unified dataset." },
    { id: "eda", label: "Exploratory analysis", kind: "component", phase: "analyze",
      componentId: "analyzer.eda_profile", params: {}, suggestedComponents: EDA_SUGGESTIONS,
      description: "Distributions, missingness, correlations — Evidence-locked." },
    { id: "crosstab", label: "Crosstabs", kind: "component", phase: "analyze",
      componentId: "analyzer.crosstab", params: { banner: "gender", stub: "dropout" },
      suggestedComponents: TAB_SUGGESTIONS,
      description: "Weighted crosstabs with significance letters." },
    { id: "model", label: "Model", kind: "component", phase: "analyze",
      componentId: "model.ml.logistic_regression", params: { target: "dropout" },
      suggestedComponents: MODEL_SUGGESTIONS,
      description: "Fit the primary model; red-team before acceptance." },
    { id: "recommend", label: "Recommendations", kind: "lab", labTab: "deliver", phase: "monitor",
      description: "Deliverables: Evidence-bound recommendations report." },
    { id: "monitor", label: "Monitor", kind: "lab", labTab: "deliver", phase: "monitor",
      description: "Share the live report; track follow-up waves." },
  ],
};

export const POLICY_RESEARCH_FLOW: FlowTemplate = {
  key: "policy-research",
  name: "Policy research",
  tagline: "Problem → evidence → design → personas → field → analysis → impact → recommend",
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
      description: "Paper Lab: reports and studies → knowledge base of drivers." },
    { id: "questions", label: "Research questions", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Ideation: what causes the outcome? which intervention has highest impact?" },
    { id: "hypotheses", label: "Hypotheses", kind: "lab", labTab: "ideation", phase: "understand",
      description: "Co-Scientist: candidate drivers — tested against the data." },
    { id: "design", label: "Research design", kind: "lab", labTab: "collection", phase: "design",
      description: "Collection: survey + interview + sampling + ethics + power/sample-size." },
    { id: "personas", label: "Persona simulation", kind: "lab", labTab: "personas", phase: "design",
      description: "Persona Lab: synthetic respondents stress-test the survey before fielding." },
    { id: "questionnaire", label: "Questionnaire", kind: "lab", labTab: "field", phase: "design",
      description: "Field Lab: build the KAP survey, skip logic, translation, validation." },
    { id: "field", label: "Field survey", kind: "lab", labTab: "field", phase: "field",
      description: "Collect responses; interviews → Qual Studio; photos/GPS; fraud checks." },
    { id: "clean", label: "Clean data", kind: "component", phase: "analyze",
      componentId: "transform.mean_impute", params: {}, suggestedComponents: CLEAN_SUGGESTIONS,
      description: "Impute missing values in the unified dataset." },
    { id: "eda", label: "Exploratory analysis", kind: "component", phase: "analyze",
      componentId: "analyzer.eda_profile", params: {}, suggestedComponents: EDA_SUGGESTIONS,
      description: "Distributions, missingness, correlations — Evidence-locked." },
    { id: "crosstab", label: "Outcome crosstab", kind: "component", phase: "analyze",
      componentId: "analyzer.crosstab", params: { banner: "gender", stub: "dropout" },
      suggestedComponents: TAB_SUGGESTIONS,
      description: "Outcome by segment with significance letters." },
    { id: "model", label: "Outcome model", kind: "component", phase: "analyze",
      componentId: "model.ml.logistic_regression", params: { target: "dropout" },
      suggestedComponents: MODEL_SUGGESTIONS,
      description: "Predict the outcome from its drivers; red-team the model." },
    { id: "prioritize", label: "Prioritize problems", kind: "component", phase: "decide",
      componentId: "decision.expected_value",
      params: { options: [
        { label: "Free bicycles (transport)", value: 0.75, probability: 0.85 },
        { label: "Scholarships (cost)", value: 0.65, probability: 0.70 },
        { label: "Libraries", value: 0.40, probability: 0.90 },
      ] },
      suggestedComponents: DECIDE_SUGGESTIONS,
      description: "Cost-impact ranking of candidate interventions." },
    { id: "intervention", label: "Intervention design", kind: "manual", phase: "decide",
      description: "Design the intervention portfolio (cost/reach/risk) — human judgment, gated." },
    { id: "pilot", label: "Pilot", kind: "lab", labTab: "field", phase: "decide",
      description: "Field a pilot; monitor uptake, outcomes, cost, satisfaction." },
    { id: "impact", label: "Impact evaluation", kind: "lab", labTab: "field", phase: "monitor",
      description: "DiD on before/after pilot panel data (the demo seed runs model.causal.did)." },
    { id: "recommend", label: "Recommendations", kind: "lab", labTab: "deliver", phase: "monitor",
      description: "Deliverables: Evidence-bound recommendations + budget allocation + scaling plan." },
    { id: "monitor", label: "Monitor & improve", kind: "lab", labTab: "deliver", phase: "monitor",
      description: "Live dashboard: KPI tracking, trends, quarterly + impact reports." },
  ],
};

export const MARKET_RESEARCH_FLOW: FlowTemplate = {
  key: "market-research",
  name: "Market research",
  tagline: "Market intel (deep agents) → survey → segmentation → pricing → recommend",
  phases: [
    { key: "understand", title: "Market intel", blurb: "sizing → competitors → trends" },
    { key: "design", title: "Design", blurb: "instrument for primary research" },
    { key: "field", title: "Field", blurb: "collect responses" },
    { key: "analyze", title: "Analyze", blurb: "clean → explore → segment → price" },
    { key: "decide", title: "Decide & Deliver", blurb: "prioritize → recommend → track" },
  ],
  stages: [
    { id: "intake", label: "Brief intake", kind: "lab", labTab: "signal", phase: "understand",
      description: "Signal Lab: ingest the client brief and any market data files." },
    { id: "market-sizing", label: "Market sizing", kind: "agent", phase: "understand",
      description: "DeepAgent: TAM/SAM/SOM from triangulated public sources, method + confidence stated." },
    { id: "competitor-scan", label: "Competitor scan", kind: "agent", phase: "understand",
      description: "DeepAgent: main competitors — offerings, public pricing, positioning; every claim cited." },
    { id: "trend-scan", label: "Trend scan", kind: "agent", phase: "understand",
      description: "DeepAgent: consequential market trends incl. community sentiment (Reddit) + analyses." },
    { id: "design", label: "Research design", kind: "lab", labTab: "collection", phase: "design",
      description: "Collection: design the primary study; sample-size planning." },
    { id: "questionnaire", label: "Questionnaire", kind: "lab", labTab: "field", phase: "design",
      description: "Field Lab: build + publish the survey." },
    { id: "field", label: "Field survey", kind: "lab", labTab: "field", phase: "field",
      description: "Collect responses with quotas and quality flags." },
    { id: "clean", label: "Clean data", kind: "component", phase: "analyze",
      componentId: "transform.mean_impute", params: {}, suggestedComponents: CLEAN_SUGGESTIONS,
      description: "Impute missing values." },
    { id: "eda", label: "Exploratory analysis", kind: "component", phase: "analyze",
      componentId: "analyzer.eda_profile", params: {}, suggestedComponents: EDA_SUGGESTIONS,
      description: "Know the data before segmenting." },
    { id: "segmentation", label: "Segmentation", kind: "component", phase: "analyze",
      componentId: "model.clustering.kmeans", params: { n_clusters: 3 },
      suggestedComponents: SEGMENT_SUGGESTIONS,
      description: "Cluster respondents into named segments." },
    { id: "pricing-analysis", label: "Pricing analysis", kind: "agent", phase: "analyze",
      description: "DeepAgent: pricing structures + willingness-to-pay signals from public sources." },
    { id: "prioritize", label: "Prioritize opportunities", kind: "component", phase: "decide",
      componentId: "decision.expected_value",
      params: { options: [
        { label: "Segment A focus", value: 0.7, probability: 0.8 },
        { label: "Segment B focus", value: 0.5, probability: 0.9 },
      ] },
      suggestedComponents: DECIDE_SUGGESTIONS,
      description: "Rank go-to-market options by expected value." },
    { id: "recommend", label: "Recommendations", kind: "lab", labTab: "deliver", phase: "decide",
      description: "Deliverables: Evidence-bound market entry recommendations." },
    { id: "monitor", label: "Monitor", kind: "lab", labTab: "deliver", phase: "decide",
      description: "Share the live report; schedule tracking waves." },
  ],
};

export const FLOW_TEMPLATES: FlowTemplate[] = [
  RESEARCH_FLOW, POLICY_RESEARCH_FLOW, MARKET_RESEARCH_FLOW,
];
