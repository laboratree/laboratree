// Pre-configured end-to-end flows for the Pipeline canvas (n8n-style).
// Node kinds: "component" runs a registered component in the pipeline executor;
// "lab" deep-links a stage owned by a Lab tab; "manual" is a human/offline stage.

export type FlowNodeKind = "component" | "lab" | "manual";

export type FlowStage = {
  id: string;
  label: string;
  kind: FlowNodeKind;
  description: string;
  componentId?: string;                 // kind === "component"
  params?: Record<string, unknown>;
  labTab?: string;                      // kind === "lab" → workspace tab key
};

export type FlowTemplate = {
  key: string;
  name: string;
  tagline: string;
  stages: FlowStage[];
};

export const RESEARCH_FIRM_FLOW: FlowTemplate = {
  key: "research-firm",
  name: "Research firm — end to end",
  tagline: "Client brief → hypotheses → survey → analysis → recommendation",
  stages: [
    { id: "brief", label: "Client requirement", kind: "manual",
      description: "Capture the business problem, budget, timeline, target population." },
    { id: "problem", label: "Problem definition", kind: "manual",
      description: "Translate the business question into testable research questions." },
    { id: "market", label: "Market & competitor scan", kind: "lab", labTab: "ideation",
      description: "Evidence Hunt: industry reports, competitor pricing, trends — cited sources." },
    { id: "lit", label: "Literature review", kind: "lab", labTab: "papers",
      description: "Paper Lab: upload/understand prior papers; chat with the evidence." },
    { id: "hypo", label: "Hypothesis formation", kind: "lab", labTab: "ideation",
      description: "Ideation Lab: Co-Scientist generates and Elo-ranks grounded hypotheses." },
    { id: "design", label: "Research design", kind: "lab", labTab: "collection",
      description: "Collection Lab: choose design; power/sample-size planning." },
    { id: "quest", label: "Questionnaire design", kind: "lab", labTab: "collection",
      description: "Collection Lab: draft the instrument, run the bias check." },
    { id: "pilot", label: "Pilot / twin dry-run", kind: "lab", labTab: "field",
      description: "Field Lab: synthetic-twin dry-run predicts drop-off and confusion pre-spend." },
    { id: "sampling", label: "Sampling & panel", kind: "lab", labTab: "panel",
      description: "Panel: recruit/import respondents, record consent, segment." },
    { id: "collect", label: "Data collection", kind: "lab", labTab: "field",
      description: "Field Lab: publish the survey; quotas, fraud flags, live monitor." },
    { id: "qual", label: "Interviews & testimony", kind: "lab", labTab: "qual",
      description: "Qual Studio: transcribe, code, extract Evidence-locked quotes." },
    { id: "clean", label: "Data cleaning", kind: "component",
      componentId: "transform.mean_impute", params: {},
      description: "Impute missing values (runnable — swap for any transform)." },
    { id: "dedupe", label: "Deduplicate", kind: "component",
      componentId: "transform.drop_duplicates", params: {},
      description: "Drop duplicate rows before analysis." },
    { id: "eda", label: "Exploratory analysis", kind: "component",
      componentId: "analyzer.eda_profile", params: {},
      description: "Distributions, missingness, correlations — Evidence-locked." },
    { id: "model", label: "Statistical / ML model", kind: "component",
      componentId: "model.ml.logistic_regression", params: {},
      description: "Fit the primary model (swap for any of the ~35 zoo models)." },
    { id: "redteam", label: "Red-team the model", kind: "component",
      componentId: "critic.red_team", params: {},
      description: "Adversarial robustness/subgroup/leakage checks gate acceptance." },
    { id: "viz", label: "Visualization", kind: "lab", labTab: "insight",
      description: "Insight Lab: charts, trend decomposition, decision tools." },
    { id: "insights", label: "Business insights", kind: "manual",
      description: "Answer the 'so what?' — drivers, sizes, contrasts, caveats." },
    { id: "reco", label: "Recommendations", kind: "manual",
      description: "Evidence-backed actions; every number traces to a run." },
    { id: "present", label: "Client presentation", kind: "lab", labTab: "llm",
      description: "Report card + deliverables; trust score on the back page." },
    { id: "decide", label: "Client decision", kind: "manual",
      description: "The client acts; log the decision for the learning loop." },
    { id: "tracking", label: "Post-launch tracking", kind: "lab", labTab: "field",
      description: "Follow-up waves measure outcomes (sales lift, satisfaction, ROI) over time." },
  ],
};

export const POLICY_FIRM_FLOW: FlowTemplate = {
  key: "policy-firm",
  name: "Policy research — end to end",
  tagline: "Policy problem → theory of change → evaluation → brief → M&E",
  stages: [
    { id: "problem", label: "Policy problem", kind: "manual",
      description: "Identify the public issue and the commissioning body's question." },
    { id: "stakeholders", label: "Stakeholder mapping", kind: "manual",
      description: "Map citizens, operators, government, business — who gains, who bears cost." },
    { id: "lit", label: "Literature & policy review", kind: "lab", labTab: "papers",
      description: "Paper Lab: prior evaluations, case studies, 'has this worked elsewhere?'" },
    { id: "objectives", label: "Policy objectives", kind: "manual",
      description: "Define measurable objectives the policy must achieve." },
    { id: "toc", label: "Theory of change", kind: "lab", labTab: "ideation",
      description: "Make the causal chain explicit; assumptions become testable hypotheses." },
    { id: "design", label: "Research design", kind: "lab", labTab: "collection",
      description: "Surveys, admin data, RCT/quasi-experimental design, mixed methods." },
    { id: "collect", label: "Primary collection", kind: "lab", labTab: "field",
      description: "Field Lab + Panel: household surveys with quotas and quality flags." },
    { id: "interviews", label: "Interviews & focus groups", kind: "lab", labTab: "qual",
      description: "Qual Studio: stakeholder interviews, coded themes, verbatim quotes." },
    { id: "clean", label: "Validation & cleaning", kind: "component",
      componentId: "transform.mean_impute", params: {},
      description: "Impute/clean before estimation (swap for any transform)." },
    { id: "eda", label: "Exploratory analysis", kind: "component",
      componentId: "analyzer.eda_profile", params: {},
      description: "Know the data before estimating effects." },
    { id: "econ", label: "Econometric analysis", kind: "component",
      componentId: "model.econometrics.ols", params: {},
      description: "Regression/panel methods (swap for logit/probit/ARIMA/DiD when built)." },
    { id: "impact", label: "Impact evaluation", kind: "component",
      componentId: "analyzer.causal_impact", params: {},
      description: "Did the policy move the outcome? Counterfactual vs actual." },
    { id: "cba", label: "Cost–benefit analysis", kind: "component",
      componentId: "decision.expected_value", params: {},
      description: "Benefits vs costs under explicit assumptions — inspectable arithmetic." },
    { id: "scenarios", label: "Scenario simulation", kind: "component",
      componentId: "decision.threshold_rule", params: {},
      description: "Compare policy variants A/B/C against decision rules." },
    { id: "reco", label: "Policy recommendation", kind: "manual",
      description: "Expand / modify / pilot further / end — grounded in the evidence above." },
    { id: "consult", label: "Stakeholder consultation", kind: "manual",
      description: "Review findings with officials, NGOs, experts; capture objections." },
    { id: "brief", label: "Policy brief", kind: "lab", labTab: "llm",
      description: "Report card + brief: summary, evidence, recommendations, limitations." },
    { id: "decision", label: "Government decision", kind: "manual",
      description: "Implement, revise, delay, reject, or scale." },
    { id: "mne", label: "Monitoring & evaluation", kind: "lab", labTab: "field",
      description: "Follow-up waves track implementation and outcomes over time." },
  ],
};

export const FLOW_TEMPLATES: FlowTemplate[] = [RESEARCH_FIRM_FLOW, POLICY_FIRM_FLOW];
