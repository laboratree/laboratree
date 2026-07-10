# Laboratree — Product Requirements Document (PRD)

| | |
|---|---|
| **Version** | 1.0 (draft) |
| **Date** | 2026-07-05 |
| **Owner** | Sourav Mondal |
| **Status** | For approval |
| **Related** | `docs/BRD.md` (business case), `docs/ECOSYSTEM_ROADMAP.md` (phases & architecture) |

## 1. Overview, goals, non-goals
**Product:** the research & advisory firm's operating system — 16 Labs on a shared trust layer
(Evidence Ledger, repro manifests, HITL gates, component registry) driven by an **agentic runtime**
(deep agents + watchers + Org Brain memory + Study Navigator, autonomy-dialed, always gated).
**Goals:** implement BR-01…BR-23 across Phases 10–20 + AR-1…5. **Non-goals (this horizon):**
billing automation, marketplace, native mobile apps (offline = PWA), on-prem, CATI telephony,
full clinical compliance, being a full CMS (we export/share posts; the firm's website stays
theirs), ungated full autonomy (every autonomous flow has declared human checkpoints).

## 2. Personas
| Persona | Role in product |
|---|---|
| **Priya — Research Director** (firm principal) | scopes studies, approves HITL gates (codebooks, Director proposals, claim-audit overrides), owns client delivery |
| **Arjun — Quant Analyst** | weighting, crosstabs, drivers, models; consumes Field/Signal datasets |
| **Sofia — Qual Researcher** | interviews, transcript review, coding, synthesis, quote curation |
| **Marco — Field & Panel Manager** | panel imports, consent, invitations, quotas, live field monitoring |
| **Client stakeholder (external)** | receives deliverables; verifies via QR/links; watches live dashboard |
| **Respondent (public)** | answers surveys on any device without an account; records testimony |
| **Amara — MLE Lead** (grant-program firm) | MEL plans, logframes, waves, DQAs, learning agenda, DiD/PSM, donor reports |
| **Enumerator (field worker)** | assigned clusters; collects offline on a phone; syncs when connected |
| **Grantee / implementing partner (external)** | submits routine monitoring data via the portal; responds to review feedback |
| **Devraj — Strategy Consultant** (advisory firm) | value chains, canvas + assumptions, WTP studies, unit economics, pilots, DD packs |
| **Impact investor (external)** | receives deal screens + glass-box diligence packs; verifies claims |
| **Nadia — Knowledge & Comms Manager** | runs Sector Watch curation, newsletters, blog posts, publications |
| **Newsletter subscriber (external)** | receives curated sector scans; consent + preferences managed |
| **Org Owner/Admin** | tenancy, members, roles (exists) |

## 3. Functional requirements — existing Labs (current state + deltas)
| Lab | Current state (✅ shipped, Phases 1–9) | Planned deltas |
|---|---|---|
| Ideation | Co-Scientist, Evidence Hunt, Data Hunt, auto-experiment | consume Market Intel briefs (P16) |
| Paper | adaptive card, simplify, chat-RAG, Experiment canvas, demo data | PRISMA funnel (P17+) |
| Collection | questionnaire design, bias check, Cochran, synthetic pilots | Methodology Advisor (P14); twin dry-run entry (P10) |
| Signal | multi-format extract → master workbook | none this horizon |
| Insight/Modeling/Trend/Decision | EDA, charts, 35-model zoo, Red-Team, Leakage, trend/decision tools | receive survey Datasets (P14); `chart.choropleth` geo maps (P19) |
| Intelligence | report card + trust score | seal embedded in Deliverables exports (P15) |

## 4. Functional requirements — new Labs
Format: **FR-id (BR, Phase)** requirement — *acceptance criteria (AC)*.

### 4.1 Field Lab (`labs/fieldwork/`) — Phase 10
- **FR-FLD-01 (BR-01,03; P10)** Survey builder: sections; question types single/multi/scale/
  matrix/open-text/number/date/media-upload; skip & screen-out logic; translations. *AC: golden
  logic fixtures — no path mis-routes.*
- **FR-FLD-02 (BR-01)** One-click import of a Collection-Lab questionnaire into a Survey draft.
- **FR-FLD-03 (BR-10)** Publish gate: bias check re-run + **pre-registration lock (U6)** freezing
  hypotheses/planned analyses. *AC: post-publish prereg edits impossible; amendments create
  changepoints.*
- **FR-FLD-04 (BR-03)** Publish mints public HMAC URL + QR; respondents need no account.
- **FR-FLD-05 (BR-03)** Public runtime: mobile-first, autosave/resume. *AC: kill browser
  mid-survey → resume restores all answers.*
- **FR-FLD-06 (BR-03)** Quota engine with atomic cell increments. *AC: two concurrent completes on
  the last slot → exactly one accepted, one polite close-out.*
- **FR-FLD-07 (BR-03,10)** Quality flags (speeder/straightliner/duplicate-fingerprint) mark, never
  delete. *AC: labeled fixture set meets precision/recall threshold.*
- **FR-FLD-08 (BR-03)** Live monitor: completes vs target, quota bars, per-question drop-off,
  flag rate; pause/close.
- **FR-FLD-09 (BR-03,10; U2)** Field Director v1: detects quota lag/drop-off spikes/quality
  drift → HITL proposals; approved instrument edits bump `instrument_version`. *AC: analyses
  auto-split pre/post changepoint.*
- **FR-FLD-10 (BR-01)** Responses export as a versioned `Dataset` consumable by all analysis Labs.
- **FR-FLD-11 (BR-05)** Media-upload answers create `MediaAsset`s (→ Qual Studio).
- **FR-FLD-12 (BR-03)** Public routes rate-limited; optional Turnstile. *AC: isolation tests — no
  authenticated data reachable from public namespace.*

### 4.2 Panel CRM (`labs/panel/`) — Phase 11
- **FR-PAN-01 (BR-04)** Respondent CRUD + CSV/Excel import with dedupe + column mapping (reuses
  Signal extraction).
- **FR-PAN-02 (BR-04)** Append-only ConsentRecords; inviting without valid consent is blocked.
- **FR-PAN-03 (BR-04)** Segments = saved attribute/engagement filters.
- **FR-PAN-04 (BR-04)** Batch invitations: unique tokens, throttled email via `core/notify`,
  scheduled reminders. *AC: completion ties to its Invitation; response rows contain no PII.*
- **FR-PAN-05 (BR-04)** IncentiveLedger (promised/earned/paid) + payout export.
- **FR-PAN-06 (BR-04)** GDPR: per-respondent data export and delete. *AC: delete keeps the
  pseudonymous response row.*
- **FR-PAN-07 (BR-03)** `analyzer.panel_health`: churn, response rate, fatigue; fatigue-aware
  sampling hints.
- **FR-PAN-08 (BR-03,10; U8)** Cross-study respondent history: self-consistency checks feed
  response quality; longitudinal cuts.
- **FR-PAN-09 (BR-04)** Public opt-in sign-up page (recruit inlet).

### 4.3 Qual Studio (`labs/qual/`, `core/transcribe`, `core/media`) — Phases 12–13
- **FR-QUA-01 (BR-05; P12)** Capture: file upload, in-browser recorder, Field media answers.
- **FR-QUA-02 (BR-05; P12)** Background pipeline (Celery): ffmpeg probe/chunk → pluggable
  `TranscriptionEngine` → speaker-turn pass → transcript (Mongo) → embeddings. *AC: job progress
  via API/SSE; fake-engine offline tests pass.*
- **FR-QUA-03 (BR-05; P12)** Transcript viewer synced to player (click segment → seek); in-place
  human correction, recorded.
- **FR-QUA-04 (BR-05; P13)** LLM-proposed codebook → **HITL GateTask** (merge/rename/approve);
  coding blocked on unapproved codebooks.
- **FR-QUA-05 (BR-05; P13)** `analyzer.thematic_coding` with confidence + supporting text; manual
  overrides recorded. *AC: inter-rater agreement vs human sample ≥ threshold.*
- **FR-QUA-06 (P13)** `analyzer.transcript_sentiment` per segment/speaker.
- **FR-QUA-07 (BR-02,05; P13)** `analyzer.quote_extraction`: verbatim + timestamp + speaker →
  Evidence records. *AC: quote text verbatim-matches transcript span.*
- **FR-QUA-08 (BR-05; P13)** `analyzer.qual_synthesis`: themes × sources matrix, saturation curve,
  cited narrative.
- **FR-QUA-09 (U7; P13)** Copilot: guide-coverage per interview, suggested probes, study
  saturation radar. *AC: radar flips a theme to saturated on fixtures.*
- **FR-QUA-10 (P13)** Open-end coding of survey text answers with the same engine.
- **FR-QUA-11 (P12)** Semantic search across project transcripts.

### 4.4 Synthetic Respondents (`labs/synth/`) — Phase 10 (+14 calibration)
- **FR-SYN-01 (BR-08)** Persona frame via IPF to target margins (census or Panel CRM marginals).
- **FR-SYN-02 (BR-08)** Personality injection: OCEAN traits + bio-sketches; optional grounding
  (ANES/WVS/GSS/PersonaHub); panel-conditioned when panel exists.
- **FR-SYN-03 (BR-08)** Twins traverse the real instrument honoring skip logic; scale answers via
  semantic-similarity elicitation; ensemble/de-bias controls.
- **FR-SYN-04 (BR-14)** Cost preview + hard cap before any twin run.
- **FR-SYN-05 (BR-08)** Dry-run report: predicted drop-off, confusing items, expected
  distributions.
- **FR-SYN-06 (BR-10)** All synthetic rows `synthetic:true`; excluded from client deliverables by
  default. *AC: attempting to place synthetic-derived Evidence in a report triggers a labeled
  caveat block, not silent inclusion.*
- **FR-SYN-07 (BR-08; U3; P14)** Calibration: per-item distribution distance + correlation
  fidelity vs the real wave → stored score, trended per client.

### 4.5 Tabulation Lab (`labs/tabulation/`) — Phase 14
- **FR-TAB-01 (BR-06)** `transform.rake_weights` to target margins; effective-N + design-effect as
  Evidence. *AC: reproduces margins within tolerance on goldens.*
- **FR-TAB-02 (BR-06)** `analyzer.crosstab`: banner×stub, weighted, column-proportion z-tests with
  letters, chi-square; HTML/Vega + client .xlsx artifact. *AC: matches statsmodels/scipy
  hand-calcs on goldens.*
- **FR-TAB-03 (BR-06)** `analyzer.survey_metrics`: NPS, top/bottom-2-box, means + CIs, gaps.
- **FR-TAB-04 (BR-06)** `analyzer.driver_analysis` (permutation importance over registry models);
  **FR-TAB-05** `analyzer.segment_profile` over clustering components.
- **FR-TAB-06 (BR-10; U6)** Every analysis auto-labeled pre-registered vs exploratory; changepoint
  splits applied.
- **FR-TAB-07 (BR-02; U4)** `analyzer.triangulate`: quant×qual×literature matrix. *AC: each cell
  cites ≥1 Evidence per modality; verdict ∈ {convergent, divergent, unexplored}.*
- **FR-TAB-08 (BR-01)** SurveyResponses → flat weighted `Dataset` bridge.

### 4.6 Deliverables Studio (`labs/deliverables/`) — Phase 15
- **FR-DEL-01 (BR-02,07)** Block-based report builder; numeric/quote blocks must bind Evidence.
  *AC: hand-typed number → rejected.*
- **FR-DEL-02 (BR-07)** Evidence picker across the whole project (charts, tables, quotes, stats).
- **FR-DEL-03 (BR-07)** Auto methodology appendix from repro manifests (n, weights, field dates,
  exclusions, changepoints).
- **FR-DEL-04 (BR-10; U5)** Claim Auditor pre-export sweep (contradictions, causal overclaims,
  frame generalization); block-or-annotate; overrides recorded. *AC: planted overclaim caught on
  fixtures.*
- **FR-DEL-05 (BR-02,07; U1)** Branded .pptx export with per-slide **verification QR** → public
  evidence-chain page (incl. quote playback). **FR-DEL-06** .pdf export (Playwright).
- **FR-DEL-07 (BR-07)** Live HMAC dashboard (field progress + headline metrics), revocable.
- **FR-DEL-08 (BR-07; U9)** Living-evidence re-run: re-execute a report on new data → per-figure
  diff + as-of stamp. *AC: diff correctness on fixture re-runs.*

### 4.7 Market Intel Lab (`labs/market/`) — Phase 16
- **FR-MKT-01 (BR-09; U10)** Source snapshots: every scrape/search hit frozen (URL + content +
  timestamp) as an Evidence-backed artifact with freshness stamp.
- **FR-MKT-02 (BR-09)** `analyzer.market_size`: TAM/SAM/SOM, top-down + bottom-up, stated method +
  confidence. *AC: uncited figure → rejected (enforcement test).*
- **FR-MKT-03 (BR-09)** `analyzer.competitor_scan`: discover → profile (offerings, pricing,
  positioning, news) → review-sentiment mining.
- **FR-MKT-04 (BR-09)** `analyzer.feature_matrix` + per-competitor SWOT + share-of-voice.
- **FR-MKT-05 (BR-09)** `analyzer.workflow_map` (how the target market operates) +
  `analyzer.whitespace` (JTBD gap scoring → ranked opportunities).
- **FR-MKT-06 (BR-01)** Outputs feed Ideation briefs and the U4 triangulation matrix.

### 4.8 Impact Lab (`labs/impact/`) — Phase 17
- **FR-IMP-01 (BR-17; U11)** Logframe Studio: LLM drafts ToC + results framework + SMART
  indicators (numerator/denominator, disaggregations, targets, means of verification) from
  ingested program docs → HITL approval. *AC: unapproved indicators cannot compute.*
- **FR-IMP-02 (BR-17; U11)** Each indicator = a registered computation recipe; values, disaggre-
  gations, and target-achievement % are Evidence records. *AC: golden recipes reproduce
  hand-computed values.*
- **FR-IMP-03 (BR-17)** Wave Manager: baseline/midline/endline as linked studies; instrument
  version-locked across waves (changes = changepoints). *AC: cross-wave indicator comparison
  refuses mismatched instrument versions unless changepoint-annotated.*
- **FR-IMP-04 (BR-17; U8)** Panel re-contact across waves via Panel CRM; attrition dashboard
  (rate, differential-attrition test) + replacement-sampling rules.
- **FR-IMP-05 (BR-17; U9,U11)** On wave close, the Living Logframe auto-recomputes every
  indicator vs baseline with significance tests → refreshed IPTT. *AC: fixture midline close
  produces the expected recomputed IPTT diff.*
- **FR-IMP-06 (BR-17)** Enumerator mode: accounts, cluster assignments, per-enumerator progress;
  collection UI runs as an **offline-first PWA** (cached instrument, queued submissions, sync).
  *AC: airplane-mode collection of N interviews syncs losslessly.*
- **FR-IMP-07 (BR-17,03)** Curbstoning detection: GPS/timestamp/answer-pattern anomalies per
  enumerator, flag-not-delete. *AC: planted fabricated-interview fixtures meet precision/recall
  bar.*
- **FR-IMP-08 (BR-17)** Impact estimators: `model.impact.did` (with parallel-trends sentinel),
  `model.impact.psm`, `model.impact.ancova`; cluster power/MDE calculator. *AC: estimates match
  statsmodels hand-checks; sentinel fails a violated-trends fixture.*
- **FR-IMP-09 (BR-17)** Language layer: instrument translation with back-translation QA diff +
  human review; local-language transcription; coding on translation with original verbatim
  linked. *AC: planted mistranslation caught by back-translation diff.*
- **FR-IMP-10 (BR-17,07)** Donor reporting blocks: IPTT (every cell Evidence-locked), logframe
  progress, OECD-DAC findings, Most-Significant-Change stories with playable testimony.
- **FR-IMP-11 (BR-17)** MEL plan designer: per-indicator collection calendar (source, frequency,
  method, responsible party) LLM-drafted from the ToC → HITL; exports donor-format annex; calendar
  drives scheduled collection reminders and wave scaffolding.
- **FR-IMP-12 (BR-17,19)** Grantee portal: external partner accounts submit routine data via
  generated reporting forms; validation → reviewer HITL gate → approval triggers U11 recompute;
  late submissions auto-chased. *AC: unapproved submissions never touch indicator values; partner
  role sees only its own program surface.*
- **FR-IMP-13 (BR-17)** `analyzer.dqa`: five-dimension indicator quality scoring (validity,
  reliability, timeliness, precision, integrity) from checklist + system metadata; spot-check
  planner samples records for field verification; reported-vs-verified variance per partner.
  *AC: planted inflated-report fixture yields the expected variance flag.*
- **FR-IMP-14 (BR-17; U13)** Learning agenda: learning questions as standing Evidence queries
  (auto-attach stance/confidence as new data lands); pre-populated after-action reviews;
  `analyzer.adaptive_recos` (grounded, cited); learning-brief deliverable blocks. *AC: fixture
  evidence accumulates to a question with correct stances.*
- **FR-IMP-15 (BR-17)** Portfolio roll-ups: shared standard-indicator library; cross-project
  aggregation with double-counting guards; donor portfolio dashboard. *AC: double-count fixture
  is caught; roll-up matches hand aggregation.*
- **FR-IMP-16 (BR-17)** `analyzer.vfm` (4E) + `analyzer.cost_effectiveness` (cost per output/
  outcome + sensitivity) + CBA; outcome-harvesting and contribution-analysis templates with
  substantiation status on harvested outcomes.

### 4.9 Strategy Lab (`labs/strategy/`) — Phase 18
- **FR-STR-01 (BR-18)** `analyzer.value_chain`: actor/margin/constraint mapping from chain-actor
  survey + interview data → margin-flow diagram. *AC: golden chain fixture reproduces margins.*
- **FR-STR-02 (BR-18)** Ecosystem/stakeholder graph (Neo4j): actors, relationships, influence;
  queryable and rendered.
- **FR-STR-03 (BR-18; U12)** Evidence-linked Business Model Canvas: LLM-drafted variants from
  discovery evidence; every element carries Assumption records (untested/testing/validated/
  invalidated) linked to Evidence. *AC: status transitions REQUIRE linked Evidence (enforcement
  test); canvas versions logged via changepoint pattern (pivot log).*
- **FR-STR-04 (BR-18)** Inclusive-business pattern templates (agent network, PAYG, out-grower,
  micro-franchise) as canvas starting points.
- **FR-STR-05 (BR-18)** Pricing/WTP: `analyzer.van_westendorp` + `analyzer.gabor_granger`, fielded
  via Field Lab (incl. offline/enumerator). *AC: outputs match hand-computed curves on goldens.*
- **FR-STR-06 (BR-18)** `analyzer.unit_economics` (contribution margin, CAC/LTV, break-even) +
  `analyzer.scenario_model` (driver-based projections, tornado sensitivity, Monte Carlo); branded
  .xlsx financial-model export; every input links Evidence or is flagged unvalidated. *AC: math
  goldens; unlinked input renders with the unvalidated flag.*
- **FR-STR-07 (BR-18)** Pilot manager: pick assumptions → design (test/control, MDE via power
  calc) → collect via Field/Panel/Qual → results auto-update Assumption Ledger + financials.
  *AC: pilot-close fixture flips the target assumption with linked Evidence.*
- **FR-STR-08 (BR-18)** IMM: ToC via Logframe Studio; bundled IRIS+ catalog picker; IMP 5
  Dimensions assessment; SDG target mapping; impact projections on U11 recipes with enforced
  "projected" labels. *AC: picker maps to valid IRIS+ ids; unlabeled projected claim rejected.*
- **FR-STR-09 (BR-18,19)** Investor tools: `analyzer.deal_screen` (configurable scorecards over
  assumptions + financials + IMM); auto-assembled glass-box due-diligence pack; investment-memo
  template. *AC: DD pack refuses unvalidated-assumption claims without labels.*
- **FR-STR-10 (BR-18)** `analyzer.scale_readiness` diagnostic + scale-scenario models feeding the
  same financial workbench.
- **FR-STR-11 (BR-18; P19)** `analyzer.concept_test`: monadic/sequential concept exposure via
  Field Lab (appeal, relevance, uptake intent, price reaction) + qual probes. *AC: analysis
  matches hand-computed concept scores on goldens.*
- **FR-STR-12 (BR-18; P19)** Landscape-study playbook: Market Intel + ecosystem graph + policy
  scan + gap analysis chained into a landscape-report deliverable.
- **FR-STR-13 (BR-18; P19)** `analyzer.channel_performance`: agent/channel-level activity data
  (via Signal or routine forms) → adoption, activity curves, retention, per-channel unit
  economics; comparison views. *AC: golden agent-ledger fixture reproduces channel rankings.*
- **FR-STR-14 (BR-18,17; P19)** Behaviour-change + needs-assessment playbooks: KAP instrument
  templates (pre/post), adoption-funnel dashboards; `analyzer.needs_priority` (needs × severity ×
  coverage) + strategy-roadmap deliverable template.

### 4.10 Knowledge & Content Studio (`labs/content/`) — Phase 19
- **FR-CNT-01 (BR-20; U10)** Sector Watch: org-configured `MonitoredSource`s (RSS/sites/topics)
  scanned on schedule; LLM triage (relevance, novelty, why-it-matters, tags); every item
  source-snapshotted. *AC: triage precision on labeled feed fixtures ≥ bar; kept item without a
  snapshot is impossible.*
- **FR-CNT-02 (BR-20)** Curation queue: keep/kill/annotate with editor notes; kept items feed
  newsletters and the org knowledge base.
- **FR-CNT-03 (BR-20)** Newsletter composer: branded sections by theme, grounded editor's note,
  test-send, schedule; subscribers = consented contacts with preferences (Panel machinery);
  open/click analytics inform later triage. *AC: send to a test list renders correctly;
  unsubscribe honored platform-wide.*
- **FR-CNT-04 (BR-20; U5)** Data-driven post builder: block editor with Evidence-bound
  interactive chart embeds; Claim Auditor sweep pre-publish; HTML/Markdown export + public share
  page. *AC: planted uncited statistic is blocked/annotated.*
- **FR-CNT-05 (BR-20)** Audio narration: per-post TTS artifact with player on the share page.
- **FR-CNT-06 (BR-20; U13)** Publications: templates (case study, lessons-learned, policy brief,
  public report) with donor co-branding slots; **lessons-harvest** workflow (archive ingest →
  learning queries + qual synthesis → cited lessons). *AC: each harvested lesson cites ≥1
  source; publication claims are Evidence-bound like reports.*
- **FR-CNT-07 (BR-20,21)** Ghostwriter deep agent: topic (given or proposed from Sector Watch +
  Org Brain) → research with snapshots → draft in the firm's **brand-voice profile** (learned
  from their published corpus at archive import) → every claim cited → editor-feedback ReAct
  revision loop, tracked. *AC: draft contains zero uncited factual claims (auditor-checked);
  voice profile measurably shifts style vs a generic draft on fixtures.*
- **FR-CNT-08 (BR-20)** Geo visuals: `chart.choropleth` + point maps (Insight Lab component,
  vega + bundled TopoJSON incl. India states/districts) embeddable in posts/reports with
  ProvenanceBadges.

### 4.11 Agent Runtime (AR track, `agents/` + `core/`)
- **FR-AGT-01 (BR-21; AR-1)** Durable agent runs: LangGraph + Postgres checkpointer; pause at
  gates for days; resume exactly; time-travel debug. *AC: kill worker mid-run at a gate →
  resume completes with identical state.*
- **FR-AGT-02 (BR-21,22; AR-1)** Guardrails: per-run budget caps, step caps, per-agent tool
  allowlists, kill switch; org daily spend alerts. *AC: cap-exceeding fixture halts cleanly with
  a resumable checkpoint.*
- **FR-AGT-03 (BR-21; AR-1)** `agent_runs` tracing: every plan, tool call (as Runs), retry, and
  outcome recorded; UI timeline per agent run. *AC: trace completeness test — no untraced step.*
- **FR-AGT-04 (BR-21; AR-2)** Deep-agent framework: planner/sub-agent/critic contracts +
  ReAct loop over registry components; Field Director, Sector Watch triage, saturation radar,
  and submission chasers re-based onto it. *AC: golden-brief replay produces a valid cited plan.*
- **FR-AGT-05 (BR-21; AR-3)** Org Brain: memory schema (semantic + graph + curated lessons),
  `recall()` consulted at plan start; **Archive Import Agent** bulk-ingests historical project
  folders → classified, embedded, linked; builds the brand-voice profile. *AC: import fixture
  corpus → precedent-project recall returns the planted match; new-study auto-brief cites it.*
- **FR-AGT-06 (BR-21; AR-4)** Study Navigator: brief → cross-Lab engagement plan (playbook,
  instruments, samples, timeline, cost estimate) → HITL approve → durable execution with
  sub-agents, gates, and daily standup digests; pause/redirect/take-over anytime. *AC: fixture
  brief plans and executes a two-Lab mini-study end-to-end under copilot mode.*
- **FR-AGT-07 (BR-21; AR-5)** Agent eval harness: golden-brief replays scored step-level (plan
  quality, tool success, citation coverage); regression gate in CI; autonomy-dial promotion
  (copilot → autopilot) requires passing evals. *AC: a degraded prompt fails the gate.*

### 4.12 Trials Lab (`labs/trials/`) — Phase 20
- **FR-RCT-01 (BR-23)** Trial designer: multi-arm, unit of randomization (individual/household/
  cluster), stratification/blocking, ICC-aware cluster power/MDE; SAP (outcomes + analyses)
  freezes into the U6 pre-registration at launch. *AC: post-launch SAP edits impossible;
  amendments = changepoints.*
- **FR-RCT-02 (BR-23)** Randomization engine: seeded, reproducible (stratified/blocked/cluster/
  re-randomization with balance threshold); assignment stored as an Evidence-locked Run.
  *AC: same seed reproduces the identical assignment; balance SMDs computed and stored.*
- **FR-RCT-03 (BR-23; U16)** Policy Twin simulation: persona agents from target-population
  margins simulate take-up + outcomes pre-trial → predicted effect, power sanity, risk flags;
  cost-capped. *AC: outputs always labeled `simulated`.*
- **FR-RCT-04 (BR-23; U16)** Retrodiction benchmark harness: registry-RCT replication suite
  (known-outcome trials) scores the simulator per domain (direction hit-rate, effect-size error);
  scorecard attaches to every twin output; **twin UI locked until the scorecard beats the naive
  baseline**. *AC: harness runs in CI on fixture trials; a degraded simulator loses the unlock.*
- **FR-RCT-05 (BR-23; U16)** Post-trial calibration: predicted-vs-actual recorded per completed
  trial; trend visible; simulated Evidence structurally excluded from claims (Deliverables +
  report enforcement). *AC: placing twin output as an impact claim → rejected.*
- **FR-RCT-06 (BR-23)** Field integration: enrollment/consent via Panel; baseline/endline waves
  via Impact machinery (offline enumerators); compliance tracking (assigned vs treated).
- **FR-RCT-07 (BR-23)** Monitoring: differential-attrition tests, GPS spillover/contamination
  flags, optional alpha-spending interim looks as HITL gates. *AC: planted adjacent-ward fixture
  raises the spillover flag.*
- **FR-RCT-08 (BR-23)** Estimators: `model.impact.itt` (ANCOVA-adjusted), `model.impact.late`
  (IV), CUPED variance reduction, heterogeneity (prereg vs 🔍 labels), multiple-testing
  correction, randomization inference. *AC: statsmodels hand-check goldens.*
- **FR-RCT-09 (BR-23)** Trial Canvas UI: arm swimlanes (enrollment/compliance funnels), balance
  SMD dot plot, auto-generated CONSORT flow diagram, per-outcome forest plots, twin
  prediction-vs-actual panel. *AC: CONSORT counts reconcile with response statuses.*
- **FR-RCT-10 (BR-23,07)** Reporting: CONSORT diagram + forest plots + prereg appendix export
  into Deliverables with glass-box QRs.

## 5. Platform requirements
- **PL-01 (BR-11)** Tenancy/RBAC/JWT (exists). *AC: org-isolation automated test.*
- **PL-02 (BR-02)** Evidence Ledger invariants: components emit via `ctx.emit`; reports refuse
  unbacked claims (exists; extended to new Labs); ledger becomes **hash-chained per project**
  (tamper-evident — 3.4). *AC: altering a persisted Evidence row breaks chain verification.*
- **PL-03** Generic `Job` framework (Celery) + status API + SSE progress (P12).
- **PL-04** `core/notify` Mailer interface (Resend/SMTP first) (P11).
- **PL-05** Public no-auth namespace `/public/*`: HMAC tokens, `core/ratelimit`, optional
  Turnstile (P10).
- **PL-06** Media handling: size caps, content-type validation, ffmpeg in worker image (P12).
- **PL-07 (BR-14)** LLM observability on all new call sites (`use_llm_context`) + per-study budget
  caps + cost preview for bulk ops (P10+).
- **PL-08 (BR-04)** PII posture: respondent identity tables separated; responses keyed by opaque
  tokens; append-only consent (P11).
- **PL-09 (BR-16)** Registry extensibility: new component ⇒ auto tool + auto UI form (exists);
  components double as the agent tool catalog (typed, permission-scoped).
- **PL-10 (BR-22)** Security control suite per threat model 3.3: injection fixtures, upload
  sniffing/transcode-through, org-scoped cache keys + vector filters (tested), field-level
  encryption for respondent contact columns, audit log on external surfaces, offsite encrypted
  backups + restore drill.
- **PL-11 (BR-01)** Collaboration & notifications (P15): comments + @mentions on gates/reports/
  canvases, review assignments, in-app notification center + email digests.
- **PL-12 (BR-21)** Autonomy dial: per-stage, per-org `manual|copilot|autopilot` config; default
  copilot; autopilot requires AR-5 eval pass.
- **PL-13 (BR-22)** Reliability controls per 3.4: idempotency keys on all public/portal POSTs;
  optimistic locking on gates/submissions; dead-letter queues + acks-late tasks; LLM circuit
  breaker + hot provider failover + queue-and-degrade; per-source scrape health; bounce
  suppression; field-window **deploy-freeze gate**; Sentry + uptime probe + structured logs with
  end-to-end run ids.

## 6. Non-functional requirements
| NFR | Requirement |
|---|---|
| NFR-01 | Public survey page p95 < 500 ms server time; light payload for 4G |
| NFR-02 | Autosave: zero answer loss on crash/refresh (tested) |
| NFR-03 | Transcription wall-time ≤ 2× audio duration (chunked, parallel) |
| NFR-04 | Org isolation provable by automated test (PL-01) |
| NFR-05 | Availability target 99.5% during active field windows; daily backups (PG dump + blob sync) + documented restore |
| NFR-06 | Default-config study COGS ≤ $30 (BR-14 telemetry proves it) |
| NFR-07 | Public survey pages meet WCAG 2.1 AA basics (contrast, keyboard, labels) |
| NFR-08 | All generative outputs carry provenance or honesty labels (synthetic/exploratory/AI-draft) |
| NFR-09 | Web tsc clean; `uv run pytest` green per phase; goldens run in CI |
| NFR-10 | Injection + tenant-isolation + upload-security suites green in CI permanently (3.3) |
| NFR-11 | Every agent run bounded (budget/steps/tools) and fully traced; no untraced agent step |
| NFR-12 | Public survey availability 99.9% during active field windows; deploy-freeze gate enforced; zero data loss on submit/sync (idempotency + append-only, chaos-tested) |
| NFR-13 | Every pipeline resumable: no all-or-nothing long jobs (chunk checkpoints, DLQ, partial states); kill-worker chaos tests pass for transcription + agent runs |
| NFR-14 | LLM degradation is graceful: provider outage never fails a user request (queue-and-degrade + deterministic fallbacks); prompt changes eval-gated and versioned in repro manifests |

## 7. Data model overview (new entities)
Postgres: `Survey` (+prereg pack, changepoints), `SurveyResponse`, `Quota`, `Respondent`,
`Segment`, `ConsentRecord`, `Invitation`, `IncentiveLedger`, `MediaAsset`, `Job`, `Report`,
`SourceSnapshot` (P16 metadata); P17: `Logframe`, `Indicator` (recipe + targets + disaggregations),
`StudyWave` (linked surveys + panel links), `Enumerator`/`Assignment`, `MELPlan`, `PartnerOrg` +
`Submission` (portal, review states), `LearningQuestion`, `StandardIndicator` (library); P18:
`Canvas` (versioned), `Assumption` (status + evidence links), `Pilot`, `FinancialModel`,
`DealScreen`; P19: `MonitoredSource`, `WatchItem` (triage + snapshot ref), `NewsletterIssue`,
`Post`, `Publication`, `Subscriber` (contact + preferences); AR: `AgentRun` (trace + checkpoint
refs + caps), Org-Brain records (`MemoryItem`, lessons, `BrandVoiceProfile`); P20: `Trial`
(design + SAP + prereg ref), `TrialArm`, `Assignment` (seeded, Evidence run ref),
`TwinRun` (predictions + scorecard + calibration). Mongo: transcripts
+ coding docs.
Blob: media, exports, snapshot bodies, .xlsx models, TTS audio. Redis: Celery, rate limits,
cache. Neo4j: walkthrough graphs + **stakeholder/ecosystem graphs (P18)**. pgvector: transcript +
knowledge + learning-agenda + watch-item embeddings.

## 8. Integrations & dependencies
As Roadmap Part 4 — **open-weight first (4.2)**: DeepSeek-V4/-Flash via OpenAI-compatible APIs
(closed GPT-5.x = later per-role config upgrade), local faster-whisper + BGE-M3 + Kokoro,
Brave→SerpAPI, OpenAlex/Semantic Scholar (+Crossref/arXiv/Unpaywall later), Kaggle/HF/OpenML,
Resend (email), Cloudflare Turnstile, self-hosted Playwright scraping (Firecrawl/Apify later),
IRIS+ & SDG catalogs (free, bundled static), RSS via feedparser (free), OpenAI TTS (optional),
ffmpeg, python-pptx, SDV/synthcity, qrcode. **No MCP dependencies.**

## 9. Release plan
| Phase | Scope | Exit criteria |
|---|---|---|
| 10 | Field Lab + synth dry-run + prereg lock + Director v1 | FR-FLD-01…12, FR-SYN-01…06; goldens green; live incognito E2E |
| 11 | Panel CRM + notify | FR-PAN-01…09; invite→complete E2E; GDPR export/delete test |
| 12 | Qual capture + transcription | FR-QUA-01…03, 11; PL-03/06; real media E2E |
| 13 | Qual analysis + copilot | FR-QUA-04…10; inter-rater + verbatim tests |
| 14 | Tabulation + triangulation + calibration | FR-TAB-01…08, FR-SYN-07; statsmodels goldens |
| 15 | Deliverables + audit + glass-box + living evidence | FR-DEL-01…08; overclaim + unbacked-number tests |
| 16 | Market Intel + scraper | FR-MKT-01…06; uncited-figure rejection |
| 17a | Impact & MLE Lab — design + evaluation | FR-IMP-01…10; offline-sync + curbstoning + DiD goldens; Living-Logframe recompute E2E |
| 17b | Impact & MLE Lab — monitoring + learning | FR-IMP-11…16; portal review-gate E2E; DQA + roll-up + learning-agenda fixtures |
| 18 | Strategy Lab (advisory vertical) | FR-STR-01…10; WTP/unit-econ goldens; assumption-enforcement + DD-pack label tests |
| 19 | Content Studio + advisory playbooks | FR-CNT-01…08, FR-STR-11…14; triage/snapshot enforcement; newsletter E2E; ghostwriter voice/citation tests; playbook goldens |
| 20 | Trials Lab (RCT + validated twin) | FR-RCT-01…10; randomization/ITT/LATE goldens; retrodiction harness in CI; honesty-rule enforcement |
| 21+ | Backlog (roadmap Phase 21+) | per item |

**AR track lands in parallel:** AR-1 (FR-AGT-01…03) with 10–11 · AR-2 (FR-AGT-04) with 12–13 ·
AR-3 (FR-AGT-05) with 14–15 · AR-4 (FR-AGT-06) with 16–17 · AR-5 (FR-AGT-07) with 18–19.
Launch stages: **Alpha** after 12 (internal dogfood study) → **Private beta** after 15 (design
partners; onboarding = Archive Import) → **GA** after 17.

## 10. QA & acceptance strategy
Five layers (Roadmap Part 3): provenance floor → adversarial verification (Red-Team, Leakage,
Claim Auditor) → golden sets/regression harness for all deterministic math → LLM-judge + HITL
gates for generative steps → calibration & drift monitoring (twin score, WER spot-checks, coding
inter-rater). Per-workflow quality bar table in Roadmap 3.2 = the acceptance reference for each FR.

## 11. Metrics & analytics
Product: time-to-first-crosstab, studies/org/quarter, verification-link clicks, gate turnaround
time, % analyses pre-registered. Quality: calibration trend, WER, flag precision/recall,
inter-rater, % claims Evidence-backed (must be 100%). Cost: LLM $/study by Lab (existing
observability), infra $/mo.

## 12. Open questions
- **OQ-1** Final pricing model (per-seat + study packs vs usage) — decide after first 3 design
  partners.
- **OQ-2** EU-only hosting commitment for GDPR-sensitive clients (Hetzner already EU; formalize?).
- **OQ-3** Recording-consent UX per jurisdiction (one-party vs two-party states).
- **OQ-4** When to split worker box / move media to R2 (thresholds).
- **OQ-5** Whether Phase 16 Market Intel ships before Deliverables for consulting-segment pull.
- **OQ-6** Vertical ordering: Phases 16 (Market Intel), 17 (Impact & MLE), 18 (Strategy) reorder
  freely by whichever design partner signs first — all three depend only on Phases 10–15.
  (Strategy Lab additionally reuses Logframe Studio, so a Strategy-first order pulls that one
  module forward.)
