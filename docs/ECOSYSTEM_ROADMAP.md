# Laboratree — Ecosystem Roadmap (v2)

> Companion documents: [BRD](BRD.md) · [PRD](PRD.md) · [Example Guide](EXAMPLE_GUIDE.md) · [Frontend Guide](FRONTEND_GUIDE.md)

## Context

Laboratree v1 (Phases 1–9, ~10% of the vision) built the **trust layer + paper-centric research
loop**: component registry, Evidence Ledger, repro manifests, Leakage Sentinel, Red-Team critic,
Signal Lab, Paper Lab (Study + Experiment), Ideation deep agent, ~35-model zoo, and the Next.js
workspace. What it does NOT yet do is what a research firm does daily: **field real surveys**,
manage a **respondent panel (CRM)**, run **realistic synthetic surveys with injected personas**,
capture and analyze **multimodal evidence (audio/video testimony)**, produce **crosstabs/weighted
tabulations**, orchestrate the **manual/field workflows we can't automate but can instrument**, and
ship **client deliverables**. Collection Lab only *designs* questionnaires. Zero audio/video.
Celery and MongoDB are provisioned but idle.

This plan = the complete ecosystem: every workflow of a research (and adjacent) firm, the
**unique powers** no competitor has, a **synthetic-respondent engine** with persona injection, a
**quality-assurance system** proving each workflow is best-in-class, all **third-party
prerequisites**, and a **startup-minimal infra + full cost model** (grounded in 2026 prices).

### Decisions locked with the user (2026-07-05)
- **Wave 1 = all four pillars**: Survey engine + Respondent CRM → Multimodal Qual Studio →
  Tabulation & weighting → Client deliverables.
- **Fielding: self-hosted public links**; **transcription: pluggable engine, cloud first**.
- **Cost-minimal startup posture**: single-box self-host, OpenAI usage-based, free-tier third
  parties first, pay only when volume demands.
- **This session's deliverable: the roadmap document only** → `docs/ECOSYSTEM_ROADMAP.md`.
  Phase 10 implementation starts in a later session.
- **(2026-07-06) Open-weight models first**: launch on open-source models (DeepSeek-V4/-Flash
  hosted APIs, local faster-whisper + BGE-M3 + Kokoro; Ollama for dev) and wire closed models
  later as per-role config upgrades justified by AR-5 evals. Details in 4.2/5.5.

---

# PART 1 — The ecosystem, end to end

## The running example (threads through the whole plan)

> **Client brief:** *GreenCommute Ltd* hires research firm *Meridian Insights*:
> **"Why aren't urban commuters adopting e-scooters, and what pricing/features would convert
> them?"** 500-person survey + 12 recorded in-depth interviews + the client's messy sales files.

```
MARKET INTEL ─► IDEATION ─► PAPER LAB ─► COLLECTION ─► SYNTH DRY-RUN ─► PANEL CRM ─► FIELD LAB ─┐
(size+compete)  (hypotheses)(lit review) (design)     (twin test)      (recruit)    (collect)   │
                                                                                 ▼
DELIVERABLES ◄─ TABULATION ◄─ MODELING/INSIGHT ◄─ SIGNAL LAB ◄────────────────── ┤
(PPT/dashboard) (crosstabs)   (predict/EDA)       (client files)                 │
      ▲                                                                          │
      └───────────────── QUAL STUDIO (12 interviews → themes/quotes) ◄───────────┘
              Every number/quote → EVIDENCE LEDGER (provenance-locked)
```

## The sixteen unique powers (the v2 moat — in NO existing product)

Competitors each own one slice (Qualtrics=surveys, Dovetail/NVivo=qual, Displayr/Q=tabulation,
Elicit/Consensus=lit, SyntheticUsers=personas, CB Insights/Crunchbase=market intel,
KoboToolbox/SurveyCTO=offline collection, TolaData/ActivityInfo=indicator tracking). None has a
trust layer; none fuses slices. Each power below is only possible because our slices share one
Evidence Ledger.

- **U1 · Glass-Box Deliverables** — every number/chart/quote in a deck/dashboard click-throughs (or
  a printed **verification QR**) to run → code hash → dataset version → for quotes, the **playable
  clip at the exact timestamp**. *(Phase 15.)*
- **U2 · Field Director Agent** — watches live fieldwork (quota trajectory, drop-off spikes,
  quality flags, cost/complete) and proposes HITL actions; any instrument change creates a
  **versioned changepoint** so analyses auto-split pre/post. *(Phases 10–11.)*
- **U3 · Synthetic Twin Dry-Run + Calibration Score** — simulate the questionnaire on persona
  twins built from the real panel BEFORE spending money; after fielding, **auto-compare synthetic
  vs real → published calibration score** that makes twins measurably better each study. *(Phase
  10 + 14.)*
- **U4 · Triangulation Matrix** — `analyzer.triangulate` aligns **quant × qual × literature** into
  one matrix; each cell holds Evidence from a *different modality* with a verdict:
  convergent/divergent/unexplored. *(Phase 14.)*
- **U5 · Claim Auditor** — adversarial agent sweeps every deliverable sentence for internal
  contradictions, causal overclaims on correlational data, claims beyond the CI, and generalization
  past the sampling frame; blocks/annotates; overrides recorded. *(Phase 15.)*
- **U6 · Pre-Registration Lock + Honesty Labels** — hypotheses/analyses freeze at publish; every
  later analysis auto-labeled **✅ pre-registered** vs **🔍 exploratory**. *(Phase 10 + 14–15.)*
- **U7 · Interview Copilot + Saturation Radar** — per interview: guide-coverage + suggested probes;
  per study: saturation radar that stops paying for redundant interviews. *(Phase 13.)*
- **U8 · Respondent Memory** — with consent, cross-study history powers self-consistency fraud
  checks, fatigue-aware sampling, and instant longitudinal cuts. *(Phase 11 + 14.)*
- **U9 · Living Evidence (the deliverable that never goes stale)** — because deliverables are bound
  to re-runnable Evidence, a report can be **re-executed on new data** (next wave, corrected file)
  and every figure updates with a visible diff + "as-of" stamp. A tracker study becomes a button,
  not a rebuild. *(Phase 15, on repro manifests.)*
- **U10 · Evidence-Cited Market Intelligence** — generic "AI market research" tools hallucinate
  market sizes and competitor facts. Ours can't: every TAM/SAM figure, competitor claim, price
  point, and trend is bound to a **snapshotted source** (scrape/search result frozen with URL +
  fetch timestamp) in the Evidence Ledger, with a confidence + freshness stamp. The analyst (or
  client) verifies any market number to its source in one click — the same glass-box discipline as
  U1, applied to secondary market research. *(Phase 16.)*
- **U11 · Living Logframe (self-computing results framework)** — in M&E tools (TolaData,
  ActivityInfo, Excel IPTTs) humans re-compute every indicator each wave and paste values into
  trackers. Here every logframe **indicator is a registered computation recipe** bound to its data
  sources through the Evidence Ledger: when the midline wave closes — or a grantee's quarterly
  submission is approved — the entire results framework — every indicator value, disaggregation,
  target-achievement %, and baseline-vs-midline significance test — **recomputes itself** (U9
  applied to a logframe), producing a donor-ready IPTT where every cell is click-to-verify. Weeks
  of analyst spreadsheet work becomes a button. *(Phase 17.)*
- **U12 · Assumption Ledger (the business model that knows what's proven)** — strategy tools
  (Strategyzer, Miro canvases) hold *opinions*; nothing links a canvas box to real evidence. Here
  every Business Model Canvas element carries its **assumptions as first-class records**, each with
  status **untested / testing / validated / invalidated**, linked to the Evidence that moved it —
  a WTP survey, a discovery-interview quote, a pilot's unit economics. When a pilot closes, affected
  assumptions update and the canvas visibly shows **what is proven vs believed**. Investors get a
  diligence-ready map: "of 23 assumptions, 14 validated (click to verify), 3 invalidated → model
  pivoted." *(Phase 18.)*
- **U13 · Self-Answering Learning Agenda** — donors mandate "learning agendas" (CLA), which in
  practice are workshop notes nobody revisits. Here each **learning question is a standing query**
  over the Evidence Ledger: every new wave, monitoring submission, testimony, and pilot result that
  touches the question's variables **auto-attaches as evidence for/against**, with stance and
  confidence (the Ideation Evidence-Hunt engine turned inward on the org's own accumulating data).
  A quarterly "pause & reflect" opens with the accumulated answer-so-far, not a blank page.
  *(Phase 17.)*
- **U14 · Org Brain (institutional memory that compounds)** — an 18-year firm sits on 120+
  projects of reports, instruments, transcripts, and lessons that live in folders nobody opens.
  The **Archive Import Agent** ingests that historical corpus (Signal-extract → classify →
  embed → link into a knowledge graph of projects/sectors/geographies/methods/findings), and from
  then on **every agent consults the Org Brain before acting**: a new dairy-GTM engagement opens
  with an auto-brief — "3 precedent projects, the 2019 agent-network instrument (reusable), 6
  relevant lessons, typical adoption benchmarks you measured before." Every completed study
  enriches it. Competitors' AI starts every project from zero; ours starts from the firm's whole
  history. *(AR-track, lands with Phases 14–16.)*
- **U15 · Study Navigator (the AI research director)** — the flagship agentic experience: give it
  the brief ("evaluate this 5-yr program in 4 districts" / "design a route-to-market for this
  nutrition product"), and a **planner agent drafts the full engagement** as a cross-Lab plan
  (which playbook, which instruments, sample sizes, timeline, budget/LLM-cost estimate) →
  **HITL approval** → the Navigator executes it as a durable LangGraph run: spawning Lab
  sub-agents, watching progress, raising gates when humans are needed, and posting a **daily
  standup digest** ("field 62% complete; women-45+ quota lagging — proposal in your inbox;
  transcripts 8/12 coded; draft IPTT refreshed"). Pause, redirect, or take over at any point —
  the autonomy dial (manual / copilot / autopilot-with-gates) is per stage. *(AR-track, lands
  with Phases 16–17.)*
- **U16 · Validated Policy Twin (simulate the trial before you fund it — on a simulator that has
  earned the right)** — LLM-agent policy simulation is hot research (AgentSociety reproduced
  real-world experiments incl. UBI effects; GPLab), but the field's own headline finding is that
  such simulations are only useful **when validated against ground truth** — and no product
  enforces that discipline. Ours is built around it: before a real trial, generative
  persona-agents (the U3 machinery + agent-based interaction) simulate the policy → predicted
  take-up, effect size, power check, unintended effects to watch. But the simulator must first
  pass a **retrodiction benchmark**: re-simulate published RCTs with known results (J-PAL/3ie/AEA
  registry trials) + the firm's own completed trials, and carry its per-domain scorecard
  (direction hit-rate, effect-size error) on every output. After every real trial,
  predicted-vs-actual feeds calibration (the U3 loop). Simulations are **honesty-labeled, used
  for design decisions (power, arms, instruments) — never as evidence of impact**; only the real
  trial produces claims. *(Phase 20.)*

## The agentic intelligence layer (how AI runs through everything)

The platform is **agent-native, not feature-AI**. One agent runtime (the AR track, built in slices
alongside the phases) powers every Lab; the component registry doubles as the universal, typed,
permission-scoped **tool catalog** for agents (a component IS a tool — that was the point of the
registry). Patterns used deliberately:

- **ReAct tool loops** for bounded tasks: an agent reasons → calls registry components (each call =
  a tracked, Evidence-emitting Run) → observes → continues. Everything an agent "does" is a Run,
  so agent work inherits provenance for free.
- **Deep agents** (plan → spawn specialist sub-agents → converge with citations) for open-ended
  work: Evidence Hunt already proves the pattern; it generalizes to landscape studies, market
  sizing, competitor scans, lessons harvests, and the Ghostwriter.
- **Adversarial pairs** everywhere: a producer agent is always checkable by an independent critic
  persona (Red-Team, Leakage Sentinel, Claim Auditor, DQA) — never self-graded.
- **Durable graphs** (LangGraph + Postgres checkpointer — promoted from backlog to AR-1): agent
  runs survive restarts, pause at HITL gates for days, resume exactly; time-travel for debugging.
- **Watcher agents** on schedules/events: Field Director (fieldwork), Sector Watch triage
  (content), late-submission chaser (portal), saturation radar (qual), drift monitors (QA layer 5).
- **Org Brain memory (U14)**: pgvector (semantic) + Neo4j (graph: project↔sector↔method↔finding)
  + curated "lessons" records; a shared `recall()` step at the start of every agent plan.
- **Autonomy dial** per stage & per org: `manual` (human does it, AI assists), `copilot` (AI
  drafts, human approves — default), `autopilot` (AI executes, gates only at declared checkpoints).
- **Guardrails as platform law** (AR-1): per-run **budget caps + step caps + tool allowlists**;
  agents that ingest untrusted content (scrapes, uploads, portal text) run with read-only tools —
  state-changing actions require crossing a gate (prompt-injection containment, see 3.3);
  every agent step traced to `agent_runs` (observability beyond LLM calls: plans, tool calls,
  retries, outcomes) with an **eval harness** replaying golden briefs against agent versions.

**The AR track (agent-runtime slices, built alongside the phases):**
| Slice | Deliverable | Lands with |
|---|---|---|
| AR-1 | Durable LangGraph checkpointer (Postgres), `agent_runs` tracing, budget/step caps, tool allowlists, autonomy-dial config | Phases 10–11 |
| AR-2 | Generalized deep-agent framework (planner/sub-agents/critic contracts) + ReAct loop over the registry; Field Director + triage watchers ride on it | Phases 12–13 |
| AR-3 | **Org Brain (U14)**: memory schema + `recall()` + **Archive Import Agent** (bulk historical ingest) | Phases 14–15 |
| AR-4 | **Study Navigator (U15)**: cross-Lab planner + executor meta-graph + standup digests | Phases 16–17 |
| AR-5 | Agent eval harness (golden-brief replays, step-level scoring, regression gates in CI) + autonomy-dial GA | Phases 18–19 |

## Lab-by-lab: purpose · full workflow · example

### 1. Ideation Lab — ✅ exists (`labs/ideation/`)
Turn a vague brief into sharp, evidence-grounded, testable hypotheses. Co-Scientist
generate→reflect→Elo→evolve; Evidence Hunt → cited brief + variables; Brainstorm; Data Hunt;
auto-experiment. *Ex:* top hypothesis "*perceived safety, not price, blocks women commuters*" with
9 sources + 13 variables seeding the questionnaire.

### 2. Paper Lab — ✅ exists (`labs/paper/`)
Understand + reproduce the literature. Adaptive Paper Card → explain-simpler → chat-RAG →
Experiment mode (rebuild pipeline, fetch/demo data, fork models vs paper). *Ex:* reproduce a
transport-economics logit, copy its variable structure into the design.

### 3. Collection Lab (Design) — ✅ exists, gains advisor + twins (`labs/collection/`)
Design the instrument correctly: questionnaire + bias check + Cochran sample size + synthetic
pilots. **Adds** Methodology Advisor (design + power analysis) and the **Synthetic Twin Dry-Run
(U3)**. *Ex:* twin dry-run predicts an 18% drop-off spike at the Q12 matrix → split it *before*
fielding.

### 4. Field Lab — ❌ NEW (Phase 10) — the survey engine
Laboratree hosts the survey at a public link, enforces quotas, flags junk live, and *directs*
fieldwork (U2). Import design → configure logic/quotas/translations → pre-publish bias gate +
**pre-reg lock (U6)** → HMAC public URL + QR → mobile-first respond with autosave + media-upload
questions → guard (quota/duplicate/speeder/straightliner, flagged not deleted) → **Director (U2)**
proposes HITL actions → responses become a versioned `Dataset`. *Ex:* Day 2 Director flags women-45+
quota lagging + Q17 bleeding → approve reminder + reword; 517 completes, 22 speeders excluded
visibly; 61 video-testimony clips → Qual Studio.

### 5. Panel CRM — ❌ NEW (Phase 11) — the "small CRM" that learns
Who can we survey, did they consent, how do we reach them, what do we owe them — plus a panel that
compounds (U8). Recruit (CSV import via Signal / public sign-up) → append-only consent → segment →
unique-token email invitations (`core/notify`) + reminders → incentive ledger → panel health +
fatigue-aware sampling + cross-study consistency. GDPR floor: export/delete a respondent, responses
stay pseudonymized. *Ex:* invite 1,400 "urban commuters" at €5, 41% start; two respondents
contradict their consented profile → flagged; payout export 517×€5.

### 6. Qual Studio — ❌ NEW (Phases 12–13) — multimodal capture + analyzer
The non-tabular half. Capture (upload / in-browser recorder / Field-Lab media answers) → first real
**Celery chain**: ffmpeg probe/chunk → pluggable `TranscriptionEngine` → LLM speaker-turn pass →
timestamped transcript in **MongoDB** → pgvector embeddings → HITL correction → **codebook gate** →
`analyzer.thematic_coding` / `transcript_sentiment` / `quote_extraction` (quote = Evidence w/
timestamp) / `qual_synthesis` (themes×sources, saturation, cited narrative) → **Copilot + Saturation
Radar (U7)** → semantic search. Same engine codes survey open-ends. *Ex:* 12 interviews + 61 clips
transcribed overnight; radar declares "safety-fear" saturated after interview 8, steers the last
four to "weather exposure"; 23 playable quotes deck-ready.

### 7. Signal Lab — ✅ exists (`labs/signal/`)
Messy secondary files (PDF/Word/Excel/CSV/scans) → one consolidated master workbook + data
dictionary. *Ex:* GreenCommute's 9 files → one workbook joining the survey data.

### 8. Insight + Modeling + Trend + Decision — ✅ exist
EDA/charts, 35-model zoo (Red-Team + Leakage), decomposition/causal-impact, rules/expected-value.
*Ex:* predict "intends to switch," decompose 24-mo sales, value a €10 cut vs a free-helmet bundle.

### 9. Tabulation Lab — ❌ NEW (Phase 14) — the MR analyst's daily bread
Weighted crosstabs w/ significance letters, survey metrics, drivers, segments — Evidence-locked,
honesty-labeled (U6), fused with qual (U4). Rake weights → `analyzer.crosstab` (banner×stub,
z-tests, xlsx) → `survey_metrics` (NPS/top-2-box/CIs) → `driver_analysis` + `segment_profile` →
**`analyzer.triangulate` (U4)** + **twin calibration (U3)** + **U8 consistency**. *Ex:* intent 41%
overall / 24% women-45+ (sig ᴮ, ✅ pre-reg); safety ranks #1 driver (2.1× price, 🔍 exploratory);
4 named segments; triangulation: safety **convergent**, "weather" **divergent** → follow-up
question; calibration 0.83.

### 10. Deliverables Studio — ❌ NEW (Phase 15) — what the client receives
Compose Evidence-bound blocks → branded PPT/PDF + live dashboards, with **glass-box (U1)**, **claim
audit (U5)**, and **living evidence (U9)**. Block editor (chart/table/quote-with-play/stat/auto
methodology appendix) → Evidence picker (hand-typed numbers rejected) → Claim Auditor sweep →
branded export w/ per-slide verification QR + revocable live dashboard. *Ex:* 28-slide deck; auditor
rejects "price cuts **drive** adoption," scopes "German consumers"→"Berlin"; CFO scans a QR mid-
meeting → lands on the crosstab's evidence chain, plays the quote behind the headline.

### 11. Intelligence Lab — ✅ exists (`labs/intelligence/`)
Evidence-bound report card + trust score → the QA seal printed on deliverables.

### 12. Market Intel Lab — ❌ NEW (Phase 16) — extensive market assessment, competitor scan, workflow hunt
The secondary-research powerhouse: size a market, map its structure and trends, profile every
competitor, and hunt the whitespace — all **cited and source-snapshotted (U10)** so no number is
hallucinated. Built on the existing `core/search` (Brave/OpenAlex/Semantic Scholar), a web scraper
(self-host Playwright → Firecrawl), the Evidence Ledger, and Deliverables. Three workflows in one
Lab (`labs/market/`):
1. **Market assessment** (`market/assess/`) — `analyzer.market_size` (TAM/SAM/SOM triangulated from
   multiple cited sources, top-down + bottom-up, with a stated method and confidence — never a bare
   LLM guess), plus market structure, growth/CAGR, **PESTEL**, **Porter's Five Forces**, demand
   drivers, and segmentation. Every figure carries its source snapshot.
2. **Competitor assessment** (`market/competitors/`) — `analyzer.competitor_scan`: discover players
   (search + scrape), build profiles (offerings, **pricing**, positioning, funding/news, review
   sentiment mined from public reviews), then `analyzer.feature_matrix` (feature × competitor grid),
   per-competitor **SWOT**, and share-of-voice. Snapshots let a client see *when* a price/claim was
   captured (freshness stamp).
3. **Workflow hunt / opportunity discovery** (`market/opportunity/`) — `analyzer.workflow_map`
   reconstructs how the target market/customer actually operates (their process, tools, decision
   flow) from scraped/collected evidence; `analyzer.whitespace` scores unmet needs / **jobs-to-be-
   done** gaps against the competitor matrix → a ranked opportunity list. This is where a firm turns
   "here's the market" into "here's where to play."
**Feeds the study:** a market assessment usually *precedes* Ideation (frame the brief) and its
findings triangulate (U4) with primary survey/qual results later.
**Example:** Before designing the survey, Meridian runs a Market Intel pass for GreenCommute:
e-scooter urban-mobility TAM/SAM/SOM triangulated from 6 cited sources (confidence: medium, freshest
source 2026-05); 14 competitors profiled with a pricing matrix (per-minute vs subscription) and
review-sentiment ("safety" is the #2 complaint theme across rivals — corroborating the hypothesis
*before* fieldwork); whitespace scan flags "insurance-bundled safety guarantee" as an unserved job.
The competitor safety-complaint finding later shows up **convergent** in the U4 triangulation matrix
alongside the survey and interviews.

### 13. Impact & MLE Lab — ❌ NEW (Phase 17) — Monitoring, Learning & Evaluation for grant-funded programs, end to end
**Purpose:** the vertical for firms supporting donors and development organizations across the FULL
MLE cycle — program **design** (ToC, results frameworks, MEL plans), **delivery monitoring**
(routine partner data, quality assurance, adaptive management), **learning** (agendas that
accumulate evidence), and **evaluation** (waves, testimonies, impact estimation) — through
donor-grade reporting. Targets ~60% reduction in human effort (see 2.5). Reuses the whole platform;
adds the MLE spine (`labs/impact/`):
1. **Logframe Studio** (`impact/logframe/`) — ingest the NGO's program documents (via Signal Lab) →
   LLM drafts the **Theory of Change + results framework + SMART indicators** (each with numerator/
   denominator, disaggregations: gender/age/disability/geography, target, means of verification) →
   **HITL approval**. Every indicator becomes a **registered computation recipe** whose values are
   Evidence-locked (**U11**). Evaluation questions auto-mapped to **OECD-DAC criteria** (relevance,
   coherence, effectiveness, efficiency, impact, sustainability).
2. **Wave Manager** (`impact/waves/`) — baseline/midline/endline as first-class linked studies:
   the same instrument version-locked across waves (changes = U2 changepoints); **panel tracking**
   re-contacts the same households/respondents via Panel CRM (U8); **attrition dashboard** +
   replacement-sampling rules; when a wave closes, **auto wave-comparison** re-runs every indicator
   and crosstab vs baseline (U9/U11) with significance tests.
3. **Enumerator mode + offline-first** (`impact/fieldops/` — pulled forward from the backlog
   because NGO fieldwork is offline) — enumerator accounts + assignments (villages/clusters);
   the public survey runtime becomes an **offline-capable PWA** (cache instrument, queue responses,
   sync on connectivity); GPS + timestamp capture; **enumerator performance dashboard**
   (interviews/day, duration, flag rate) with **curbstoning detection** (fabricated-interview
   analytics: GPS/time/answer-pattern anomalies — extends the Phase 10 quality engine).
4. **Impact estimators** (`impact/estimate/`) — `model.impact.did` (difference-in-differences,
   with a **parallel-trends sentinel** in the Leakage/Red-Team style), `model.impact.psm`
   (propensity-score matching on existing logistic components), `model.impact.ancova`; cluster-
   design power/MDE calculator (design effect) extending the Cochran tool.
5. **Language layer** (`impact/language/`) — instrument translation with **LLM back-translation
   QA** (translate → back-translate → diff → human review); testimony transcription in local
   languages (Whisper-class handles 50+), coding on the translation with the **original verbatim
   preserved and linked** (quote integrity across languages).
6. **Donor reporting** (Deliverables blocks) — **IPTT** (indicator | baseline | target | midline |
   endline | % achieved — every cell Evidence-locked), logframe progress report, OECD-DAC-structured
   findings, **Most Significant Change** story blocks from Qual Studio testimonies.
7. **MEL plan designer** (`impact/melplan/`) — beyond the logframe: the full **MEL framework** a
   donor requires — per-indicator data-collection calendar (source, frequency, method, responsible
   party, disaggregation), evaluation questions mapped to methods, learning agenda, reporting
   schedule. LLM-drafted from the ToC → HITL → exported as the donor-format MEL-plan annex; the
   calendar then **drives the platform** (scheduled collection reminders, wave scaffolding).
8. **Continuous monitoring + grantee portal** (`impact/monitoring/`) — MLE is monthly/quarterly,
   not just waves: **implementing partners/grantees get portal accounts** (external role) and
   submit routine output data through generated forms (the survey engine reused as structured
   reporting forms); submissions run **validation → reviewer HITL gate → approve** → indicators
   recompute (**U11**) → live donor dashboard + variance-vs-target alerts (traffic-light IPTT).
   Late-submission chasing is automated (`core/notify`).
9. **Data Quality Assessments** (`impact/dqa/`) — formal donor DQAs as a component:
   `analyzer.dqa` scores each indicator on the five standard dimensions (validity, reliability,
   timeliness, precision, integrity) from checklist + system metadata (who entered, lags,
   revisions); **spot-check planner** samples submitted records for field verification and computes
   reported-vs-verified variance per partner (feeds the same fraud analytics as curbstoning).
10. **Learning system (U13)** (`impact/learning/`) — the learning agenda as standing queries:
    each learning question auto-accumulates Evidence (waves, monitoring, testimonies) with stance/
    confidence; **after-action reviews** and pause-&-reflect sessions open pre-populated;
    `analyzer.adaptive_recos` drafts adaptation options (grounded, cited) for management response;
    learning briefs export via Deliverables.
11. **Portfolio roll-ups (donor view)** (`impact/portfolio/`) — a donor's portfolio of grants:
    **standard-indicator library** (e.g., USAID-style standard indicators) shared across projects;
    cross-project aggregation with double-counting guards; portfolio dashboard (achievement,
    spend-linked, risk flags); grantee-comparison views that stay fair (context-annotated).
12. **Value-for-Money & cost-effectiveness** (`impact/vfm/`) — `analyzer.vfm` (DFID 4E framework:
    economy/efficiency/effectiveness/equity) + `analyzer.cost_effectiveness` (cost per output/
    outcome, vs benchmarks) + CBA with sensitivity; budget/spend data ingested via Signal Lab.
    Also **outcome harvesting** and **contribution analysis** templates (complex programs where
    RCT/DiD don't apply): harvested outcomes are Evidence records with substantiation status.
**Example:** An M&E firm evaluates an NGO's women's-livelihoods program (3 districts, 1,200
households). Signal ingests the proposal + old logframe → Logframe Studio drafts ToC + 14
indicators → evaluator approves 12, edits 2. Baseline: 18 enumerators collect offline on phones in
two local languages (back-translation QA caught 3 mistranslated items); curbstoning analytics flag
one enumerator (GPS shows 9 interviews from the same courtyard). Midline, a year later: Wave
Manager re-contacts the panel (11% attrition, dashboard shows it's non-differential), and on close
the **Living Logframe recomputes all 14 indicators** vs baseline with significance; DiD on the
control districts estimates +23% income (parallel-trends sentinel passes); 40 testimonies
transcribed/translated, "reduced seasonal migration" emerges as an unplanned outcome (qual
synthesis) and triangulates **convergent** with the income finding (U4). The donor report exports
with a click-to-verify IPTT and playable testimony quotes — analyst time on the midline: days, not
weeks. **Between waves**, the program's 6 implementing partners submit quarterly output data through
the grantee portal (2 auto-chased for lateness); a DQA flags one partner's "women trained" indicator
for reliability (redefinition mid-year — annotated as a changepoint); the learning question *"does
village-agent distribution reach the poorest quintile?"* has been silently accumulating evidence
all year and enters the annual pause-&-reflect **80% answered: no — with 9 cited Evidence records**;
the donor's portfolio dashboard rolls this program up beside 11 other grants with double-counting
guards.

### 14. Strategy Lab — ❌ NEW (Phase 18) — inclusive business & business model advisory, end to end
**Purpose:** the vertical for firms advising **impact businesses and investors** on designing,
testing, and scaling sustainable/inclusive business models (BoP customers, smallholder suppliers,
last-mile distribution). Turns advisory from opinion-decks into **evidence-backed strategy**
(`labs/strategy/`):
1. **Discovery & opportunity** (`strategy/discovery/`) — reuses the whole front half: Market Intel
   (U10 cited market sizing, competitor scan), Field Lab (BoP demand surveys via enumerator/offline
   mode — these ARE low-connectivity populations), Qual Studio (customer-discovery interviews →
   coded needs/jobs-to-be-done), **`analyzer.value_chain`** (map actors/margins/constraints along
   the chain from chain-actor interviews + price surveys — rendered as a margin-flow diagram) and
   **stakeholder/ecosystem mapping** (finally real work for **Neo4j**: actors, relationships,
   influence — queryable graph).
2. **Business model design (U12)** (`strategy/canvas/`) — an **evidence-linked Business Model
   Canvas**: LLM drafts canvas variants from discovery evidence → every element (segment, value
   prop, channel, revenue stream) carries **assumptions** with status untested/testing/validated/
   invalidated, each linked to Evidence; value-proposition fit assessed against coded interview
   needs; inclusive-business pattern library (agent networks, pay-as-you-go, out-grower schemes,
   micro-franchise) as starting templates.
3. **Pricing & willingness-to-pay** (`strategy/pricing/` — components live with Tabulation) —
   `analyzer.van_westendorp` (price sensitivity meter), `analyzer.gabor_granger` (demand curve +
   revenue-maximizing price), conjoint later; run as Field Lab surveys on the target population,
   Evidence-locked like every analysis.
4. **Unit economics & financial viability** (`strategy/financials/`) — `analyzer.unit_economics`
   (contribution margin per unit/customer/agent, CAC/LTV where relevant, break-even) +
   `analyzer.scenario_model` (driver-based projections, tornado sensitivity, Monte Carlo on key
   uncertainties — numpy) + **branded .xlsx financial-model export** (advisors' clients expect a
   workbook); every input assumption links to its Evidence or is flagged **unvalidated** (U12
   discipline applied to numbers).
5. **Pilot design & testing** (`strategy/pilots/`) — business-model experiments as first-class:
   pick assumptions to test → design the pilot (test-vs-control sites, A/B offers, duration, MDE
   via the power calculator) → run collection through Field/Panel/Qual → results **auto-update the
   Assumption Ledger** (U12) and the unit-economics model; pivot log records model versions
   (canvas v1 → v2 with reasons — the U2 changepoint pattern applied to strategy).
6. **Impact thesis & measurement (IMM)** (`strategy/imm/`) — theory of change for the *business*
   (reuses Logframe Studio), **IRIS+ catalog** integration (free GIIN catalog bundled → pick
   standard metrics), **IMP 5 Dimensions of Impact** assessment (What/Who/How Much/Contribution/
   Risk), **SDG target mapping**, impact projections wired to the same U11 recipe machinery
   (impact-per-unit × scale scenarios); avoids-greenwash rule: impact claims need Evidence or an
   explicit "projected" label.
7. **Investment & scaling advisory** (`strategy/invest/`) — for the investor side:
   `analyzer.deal_screen` (configurable scorecards over the Assumption Ledger + financials +
   IMM), **due-diligence pack** (auto-assembled: market evidence, validated/invalidated
   assumptions, unit economics, impact thesis — all glass-box U1), **investment memo** template in
   Deliverables; for scaling: `analyzer.scale_readiness` diagnostic (replicability, ops, capital,
   partnerships) + scale-scenario models.
8. **Advisory playbooks** (`strategy/playbooks/`) — the recurring engagement types of inclusive-
   business firms, packaged as guided end-to-end templates that chain the right Labs (drawn from a
   real 120-project advisory portfolio — see 2.6):
   - **Landscape study** — Market Intel (cited sizing + players) + ecosystem/stakeholder graph +
     policy scan + gap analysis → landscape report; the opener of most engagements (digital
     ecosystems, diagnostics, CSR geographies, sector-in-country).
   - **Concept & value-proposition testing** — `analyzer.concept_test` (monadic/sequential concept
     exposure via Field Lab: appeal, relevance, uptake intent, price reaction) + qual concept
     probes; powers "lab-to-market" validation for products and services.
   - **GTM & channel pilots** — design agent-network/last-mile channels; **channel & agent
     analytics**: ingest agent-level activity/sales (Signal or routine forms), `analyzer.
     channel_performance` (adoption, activity curves, retention, unit economics per channel) →
     compare channels, expansion decisions.
   - **Behaviour-change campaigns** — **KAP survey instruments** (knowledge-attitude-practice,
     pre/post), adoption-funnel monitoring at scale (10k-merchant class), campaign dashboards —
     Field + Tabulation + monitoring machinery pointed at a campaign.
   - **Community needs assessment** (CSR/foundations) — household + stakeholder instruments,
     secondary data fusion, `analyzer.needs_priority` (needs × severity × coverage matrix) →
     5–10-year strategy roadmap deliverable.
   - **Program design → pilot → scale** — the hybrid arc (design a program with Logframe Studio,
     pilot it with Pilot Manager + waves, scale-readiness diagnostic) used for upskilling/sports/
     livelihoods programs — Strategy and MLE Labs working as one.
**Example:** The firm advises an agtech social enterprise (solar-powered cold storage for
smallholder horticulture) and its prospective impact investor. Discovery: value-chain analysis
from 60 chain-actor interviews shows 31% post-harvest loss concentrated at aggregation points;
ecosystem map (Neo4j) reveals cooperatives as the gatekeeper channel. Canvas drafted with 23
assumptions; the riskiest — "farmers will pay ₹4/kg/day" — goes to a Gabor-Granger WTP survey (312
farmers, enumerator-collected offline): revenue-maximizing price ₹2.8. Unit economics recompute →
per-unit contribution still positive at 70% utilization; a 2-site 90-day pilot vs 2 control sites
validates utilization at 76% (assumption → **validated**, canvas v2). IMM: IRIS+ PI7885 (post-
harvest loss reduction) projected via U11 recipes. The investor receives a diligence pack: 14/23
assumptions validated (each click-to-verify), DiD'd pilot results, tornado chart showing the model
lives or dies on utilization — and funds with eyes open. Advisory time: weeks, not months; and the
deck is provable.

### 15. Knowledge & Content Studio — ❌ NEW (Phase 19) — blogs, publications, curated newsletters
**Purpose:** advisory/MLE firms are also **publishers**: data-driven blog posts, donor-branded
publications and case studies, policy briefs, and **curated sector newsletters** (the "Monthly
Sector Scan" pattern: 15–20 hand-picked articles + publications with commentary). Today this is
days of manual scanning, drafting, and formatting per month. The Studio turns the platform's
research engine outward (`labs/content/`):
1. **Sector Watch** (`content/watch/`) — monitored sources per topic (org publications, journals,
   sector feeds via RSS + the web-search/scraper stack + OpenAlex); continuous scan → LLM triage
   (relevance, novelty, "why it matters" one-liner, sector tags) → a **curation queue** where the
   human keeps/kills/annotates. Every kept item carries its **source snapshot (U10)** — curation
   inherits the no-hallucination discipline.
2. **Newsletter assembly** (`content/newsletter/`) — approved items flow into a branded template
   (sections by theme, editor's note LLM-drafted from the month's picks, grounded); send to a
   **subscriber list** (the Panel CRM contact machinery generalized: subscribers = contacts with
   consent + preferences) via `core/notify`; open/click tracking feeds next month's triage
   (learn what partners actually read).
3. **Data-driven posts** (`content/posts/`) — the firm's signature blogs (interactive SHG maps,
   vaccination trackers) become first-class: draft in blocks (same builder as Deliverables), embed
   **live Evidence-bound charts** (Insight/Tabulation outputs → embeddable interactive Vega),
   **Claim Auditor (U5)** sweeps before publish, **audio narration** auto-generated (TTS — their
   "press play to listen" feature, built in); export to their CMS (HTML/Markdown) or host on a
   public share page.
4. **Publications & policy briefs** (`content/publications/`) — long-form templates (case study,
   lessons-learned report, policy brief, public program report) assembled from project Evidence:
   the "distill 8 lessons from a 5-year program" workflow = Signal-ingest the program archive →
   Qual synthesis + U13 learning queries → lessons drafted with citations → branded PDF with
   donor co-branding slots. Every claim in a public report is glass-box (U1) — a differentiator
   donors will notice.
5. **Ghostwriter deep agent** (`content/ghostwriter/`) — the agentic writer: give it a topic (or
   it proposes topics from Sector Watch + the Org Brain U14) → it **researches** (web search +
   snapshots + the firm's own project evidence) → **drafts in the firm's voice** (a brand-voice
   profile learned from their published corpus during archive import — vocabulary, structure,
   stance) → **cites every claim** (U10 snapshots or project Evidence) → **revises in a ReAct
   loop with the editor** (inline feedback → targeted rewrites, tracked). Same agent drafts the
   full newsletter issue (section intros + editor's note) from the month's curated items for
   one-pass human review. Geo-savvy: posts can embed **interactive choropleth/point maps**
   (`chart.choropleth` added to Insight Lab — their SHG-map style of post) with ProvenanceBadges.
**Example:** Re-emerging World's knowledge lead opens the June Sector Watch queue: 63 auto-triaged
items across financial inclusion, impact investing, WEE, clean energy, sustainable agriculture;
keeps 17 articles + 5 publications, tweaks two "why it matters" notes; the newsletter assembles
in their brand and goes to 2,400 subscribers — an afternoon instead of a week. Their SHG-map blog
post embeds a live district-level chart with a ProvenanceBadge, ships with auto-narration, and
the Claim Auditor catches one uncited "7.5 million" figure and links it to the NRLM snapshot.
The USAID case-study publication pulls its numbers straight from the program's Living Logframe.

### 16. Trials Lab — ❌ NEW (Phase 20) — RCTs & policy experiments, with a validated synthetic twin
**Purpose:** run true randomized controlled trials of policies/programs — treatment group(s) vs
control — end to end: design → randomize → field → monitor → causal analysis → CONSORT-grade
reporting, with a **simulate-first** step that is *validated, not dummy*. **Verified market gap
(July 2026):** no commercial platform runs field policy RCTs (practice = SurveyCTO + Stata by
hand); digital A/B tools (Optimizely/Statsig/Eppo) cover web products only; LLM policy simulators
(AgentSociety, GPLab) are research prototypes whose own literature concludes simulations are only
useful when validated against ground truth — none productize that validation. We adopt the best of
each: **Statsig/Eppo-grade stats engine + J-PAL-grade field discipline + AgentSociety-style
generative simulation under a mandatory validation harness.** (`labs/trials/`):
1. **Trial designer** (`trials/design/`) — arms (multi-arm supported), unit of randomization
   (individual/household/cluster), stratification & blocking, cluster power/MDE (ICC-aware,
   extends the Cochran tool), primary/secondary outcomes + **statistical analysis plan frozen
   into the U6 pre-registration** at launch.
2. **Randomization engine** (`trials/randomize/`) — seeded, reproducible assignment (stratified /
   blocked / cluster / re-randomization with balance thresholds); the assignment run is
   Evidence-locked (auditable + re-runnable); **balance checks** (standardized mean differences)
   before anyone moves.
3. **Policy Twin, validated (U16)** (`trials/twin/`) — pre-trial generative simulation: persona
   agents from the target population's demographics (U3 machinery) + agent-based interaction for
   behavioral responses → predicted take-up, effect direction/size, power sanity, unintended
   effects to watch. **Validation harness** (the accuracy demand): (a) **retrodiction benchmark**
   — the simulator re-runs published registry RCTs (J-PAL/3ie/AEA) with known outcomes and
   carries its per-domain scorecard (direction hit-rate, effect-size error) on every output;
   (b) **post-trial calibration** — every completed real trial's predicted-vs-actual updates the
   score (U3 loop); (c) **hard honesty rule** — twin outputs are design inputs (labeled
   `simulated`), structurally excluded from impact claims; only real-trial Evidence supports
   conclusions.
4. **Field & monitoring** (`trials/monitor/`) — enrollment/consent via Panel; baseline + endline
   waves via the Impact Lab machinery (enumerator/offline); **compliance tracking** (assigned vs
   actually-treated), differential-attrition tests, **GPS spillover/contamination flags**
   (control units adjacent to treatment), optional interim looks with alpha-spending gates.
5. **Causal analysis** (`trials/estimate/`) — `model.impact.itt` (covariate-adjusted ANCOVA),
   `model.impact.late` (IV for non-compliance), CUPED-style variance reduction from baseline
   outcomes, pre-registered vs 🔍-labeled heterogeneous effects, multiple-testing corrections,
   randomization inference; all statsmodels-golden-tested.
6. **Frontend representation** (a headline surface): **Trial Canvas** — arm swimlanes with live
   enrollment/compliance funnels; **balance dashboard** (SMD dot plot); auto-generated **CONSORT
   flow diagram** (assessed → randomized → allocated → followed-up → analyzed, with reasons);
   per-outcome **forest plots** (effect + CI + prereg badge); twin panel showing prediction vs
   (later) reality. All Evidence-backed, all exportable into Deliverables.
**Example:** the e-rickshaw subsidy trial in the Example Guide (§19): the twin kills a doomed
design pre-launch (predicted effect below MDE, sparse swap stations), the redesigned 80-ward
cluster RCT runs offline-first, and endline ITT = +11.2% income with a CONSORT diagram and
forest plots the state government can audit by QR.

---

# PART 2 — Expanded capability catalog

## 2.1 Other firm types we serve (same platform, different emphasis)

The Labs are general; positioning them covers many "research and related" firms:

| Firm type | What they lean on | Extra components (mostly config, Phase 16+) |
|---|---|---|
| **Market/consumer research** (our anchor) | Field + Panel + Tabulation + Qual + Deliverables | conjoint/MaxDiff, tracker waves |
| **Academic labs** | Paper Lab, Ideation, Modeling, pre-reg lock (U6), repro manifests | systematic-review (PRISMA) funnel, LaTeX export |
| **MLE firms for grant-funded programs (donors, development orgs)** | **Impact & MLE Lab** (MEL plans, logframe, grantee portal + monitoring, DQA, learning agenda, waves, DiD/PSM, VfM, IPTT) + Field/Panel/Qual/Deliverables | full vertical in Phase 17 — see 2.5 for the 60% effort cut |
| **Inclusive-business / business-model advisory (impact enterprises & investors)** | **Strategy Lab** (value chain, Assumption-Ledger canvas, WTP pricing, unit economics, pilots, IRIS+/SDG IMM, DD packs) + Market Intel/Field/Qual | full vertical in Phase 18 |
| **UX / product research** | Qual Studio (interviews), Field (in-product surveys), synthesis | usability-task timing, journey maps |
| **Data-science / analytics consultancies** | Modeling zoo, Pipeline, Leakage/Red-Team, Insight | AutoML leaderboard, model cards |
| **Competitive / market intelligence** | **Market Intel Lab** (assess + competitor scan + workflow hunt) + Deliverables | monitored sources, change alerts, deal/funding feeds |
| **Strategy / management consulting** | Market Intel Lab + Modeling + Decision + Deliverables | scenario modeling, opportunity sizing |
| **Clinical / health research (light)** | Field (eCRF-style forms), consent ledger, Qual, audit log | CDISC-ish export, adverse-event flags |

None requires a new platform — each is a **positioning + a handful of registry components**.

## 2.2 Manual-effort workflows — where we can't *do* the work, but we instrument it

Some research work is irreducibly physical/human (in-person intercepts, lab-bench experiments,
ethnography, mystery shopping, physical sample collection, clinic visits). We don't pretend to
automate these; we make them **manageable and analyzable**:

- **Digital capture forms** — the same survey engine (Phase 10) runs as a **field-worker data-entry
  form** (offline-tolerant autosave already in scope) so paper clipboards become structured data.
- **Fieldwork ops dashboard** — assignment tracking, completion by enumerator/site, geo/time stamps,
  cost-per-complete, quality-flag rate; a `Job`/task spine (Phase 12) generalizes to field tasks.
- **Data pipelines for whatever they collect** — Signal Lab ingests their spreadsheets/photos/
  scans; the media pipeline (Phase 12) transcribes their voice memos; everything lands versioned +
  Evidence-locked and flows into the same analysis stack.
- **Analysis + deliverables on manual data** — once captured, manual-origin data is indistinguish-
  able to Tabulation/Modeling/Deliverables. We add value at capture, QC, analysis, and reporting
  even when we didn't touch collection.

This is an explicit product principle: **"instrument what you can't automate."** It widens the
market to firms whose core is offline.

## 2.3 Synthetic Respondents Engine — realistic synthetic surveys with injected personas

A first-class capability (powers U3), useful three ways: **(a)** pre-field dry-run/QA, **(b)** cheap
concept screening before committing budget, **(c)** augmenting thin cells (with honesty labels — never
passed off as real). Grounded in 2026 research: persona-conditioned LLMs approximate human survey
findings when conditioned on detailed **bio-sketches**, elicited via **semantic-similarity-rating**
(map free text → Likert), and **ensembled** across models — but they distort variance/relationships,
so **calibration + honesty labeling are mandatory** (see Sources).

**How persona injection works (`labs/synth/`):**
1. **Demographic frame** — build a synthetic population matching target margins via **Iterative
   Proportional Fitting (IPF/raking, numpy)** over census/panel marginals → N persona skeletons
   whose distributions match the real frame.
2. **Personality layer** — inject **Big-Five/OCEAN** traits + values, optionally grounded in public
   attitudinal datasets (**ANES, World Values Survey, GSS**) and persona corpora (**PersonaHub**),
   producing rich bio-sketches ("Amira, 32, nurse, high-conscientiousness, cost-sensitive…").
3. **Real-panel conditioning (our edge, U3/U8)** — draw persona attributes from the client's actual
   Panel CRM distribution, so twins resemble *this study's* population, not a generic public.
4. **Elicitation** — present the real questionnaire; collect answers via semantic-similarity-rating
   for scales; enforce skip-logic so twins traverse the instrument like humans.
5. **Ensemble + de-bias** — route across model temperatures/prompts to widen variance; apply
   order/label-effect controls flagged in the literature.
6. **Calibration (U3)** — after real fielding, compute distribution distance (per-item KL/EMD),
   correlation-structure fidelity, and a headline **calibration score**; store as Evidence; the
   score trends up across studies as conditioning improves.

**Libraries:** `SDV`/`synthcity` (synthetic *tabular* augmentation + privacy), numpy IPF (demographic
synthesis), grounding datasets (ANES/WVS/GSS/PersonaHub), our `LLMClient` for persona answering.
**Honesty rule:** synthetic rows are always labeled `synthetic:true` (the `Dataset.synthetic` flag
already exists) and never silently mixed into real deliverables — same Evidence honesty as demo data.

## 2.4 Additional functionality worth adding (beyond the anchor four)

- **Alerting & monitoring** — scheduled re-scrape / re-run (we already have a scheduler surface); a
  competitive-intel source or a tracker wave can push a change alert. *(16+ / uses U9.)*
- **Weighting-target library** — reusable census/target-margin sets per country/segment. *(Phase 14.)*
- **Instrument library / templates** — reusable validated question batteries (NPS, SUS, brand
  funnel). *(Phase 10 content.)*
- **Cross-project knowledge base** — org-wide semantic search over past findings/reports/
  transcripts (pgvector already there per-doc). *(16+.)*
- **Client portal role** — external client sees only deliverables + live dashboards, not internals.
  *(16+; RBAC already supports roles.)*
- **Public-data connectors** — World Bank/FRED/Eurostat/census as `connector.*`. *(16+.)*

## 2.5 The MLE vertical: where the ~60% human-effort cut comes from

Gap check for an MLE firm serving grant-funded programs: the platform plumbing (survey engine,
panel, qual studio, tabulation, deliverables) covers ~70% of their lifecycle, but the missing
pieces are now in the Impact & MLE Lab (Lab 13, Phase 17): logframe/indicator management + MEL
plans, wave management + attrition, **enumerator/offline collection** (pulled forward — NGO
fieldwork is offline), continuous monitoring + grantee portal, DQAs, the learning system (U13),
portfolio roll-ups, DiD/PSM estimators + VfM, translation with back-translation QA, and
donor-format (IPTT/OECD-DAC) reporting. The advisory practice (inclusive business) gets the same
end-to-end treatment in the Strategy Lab (Lab 14, Phase 18).

Effort math per M&E study stage (share of a typical evaluation's analyst/coordinator hours →
automated fraction with the Impact Lab):

| Stage | % of human effort today | What automates | Cut |
|---|---|---|---|
| Evaluation design, ToC/logframe, indicators | 12% | LLM drafts from program docs + HITL approve (U11 recipes) | ~70% |
| Instrument design + translation | 8% | designer + back-translation QA | ~60% |
| Fieldwork execution (enumerators walking villages) | 25% | **not automatable** — but supervision/QC/fraud checks automate | ~30% |
| Data cleaning + indicator computation | 15% | Evidence-locked indicator recipes; validation at capture | ~80% |
| Wave comparison & impact analysis (DiD/PSM, disaggregation) | 12% | Living Logframe auto-recompute + estimator components | ~75% |
| Testimony transcription/translation/coding | 13% | Qual pipeline + human review | ~70% |
| Donor report writing (IPTT, narratives) | 15% | auto IPTT + Evidence-bound draft + Claim Auditor | ~60% |
| **Weighted total** | 100% | | **≈ 60%** |

The residual human work is exactly what SHOULD stay human: walking to households, approving
codebooks/logframes, interpreting divergences, and owning the client relationship.

## 2.6 Design-partner fit check: the Re-emerging World archetype (project-by-project)

A real prospective customer: an 18-year inclusive-business strategy + MLE consulting firm (120+
projects, 18 countries, 14 sectors). Their ENTIRE public portfolio mapped to our workflows — this
table doubles as the sales narrative ("here is your last decade of work, runnable end-to-end") and
as the completeness proof for the two verticals. Every row was checked against their published
project descriptions.

| # | Their actual project | Their workflow steps | Our support (Lab · power) |
|---|---|---|---|
| 1 | Digital upskilling pilot, 200 rural women agri-entrepreneurs (design → 6-mo pilot → scale prep) | program design, participant tracking, pre/post skills measurement, scale readiness | Program design→pilot→scale playbook: Logframe Studio + Panel (participants) + waves (pre/post) + `scale_readiness` |
| 2 | Elemi Gum responsible sourcing, Philippines (value chain assessment → sourcing commitments) | chain-actor field research, margin analysis, sourcing strategy | `value_chain` + enumerator/offline field + Qual + sourcing-roadmap deliverable |
| 3 | Nutritious snacking route to urban low-income market (micro-entrepreneur last-mile design) | research, concept testing, ecosystem insights, distribution design | Landscape + `concept_test` + ecosystem graph + GTM/channel playbook |
| 4 | Agri/dairy input business via milk-collection agent network (design → pilot → expansion) | GTM pilot, farmer adoption tracking, channel performance | GTM & channel playbook: `channel_performance` + pilot manager + adoption surveys |
| 5 | Point-of-care diagnostics (landscape study + value-proposition testing, UP) | landscape research, gap analysis, VP validation with users, scaling recos | Landscape playbook + `concept_test` + Qual user interviews + U12 assumptions |
| 6 | AI agri-tech GTM (lab-to-market, iterative field research, VP validation) | iterative field cycles, validation, GTM design | Pilot manager iterations + Assumption Ledger (U12) + WTP pricing |
| 7 | AI radiology market-based GTM (multi-phase research: early adopters + pilot hospitals) | phased B2B research, adoption studies across public/private | Same playbook; Panel handles institutional respondents (KII scheduling via Qual) |
| 8 | Agri-input business model for rural markets (field research + VP testing → pilot launch) | farmer needs, product-market fit, pilot strategy | Field surveys + `concept_test` + canvas (U12) + pilot design |
| 9 | HCL Dadri long-term CSR strategy (landscape study → 5–10-yr integrated strategy) | community needs assessment, priority setting, roadmap | Needs-assessment playbook: `needs_priority` + landscape + strategy-roadmap deliverable |
| 10 | Multi-year grassroots rural sports program (design, pilot, scale-up) | program design, participation tracking, outcome measurement | Program design→pilot→scale playbook (Strategy + MLE together) |
| 11 | Rural clean energy via women micro-entrepreneurs (market-based last-mile execution) | channel design + execution monitoring | GTM/channel playbook + continuous monitoring (17b) |
| 12 | Nepal logistics impact-investment assessment for BII (landscape + portfolio-company assessment) | sector analysis, business DD, investment guidance | Market Intel (U10) + `deal_screen` + glass-box DD pack (U1) |
| 13 | Nepal digital landscape for SDC's DIGI flagship program design | ecosystem mapping, stakeholder/system gaps, donor program design | Landscape playbook + ecosystem graph + Logframe/MEL-plan design (17a) |
| 14 | Climate-adaptation program → 8 key lessons, public reports, policy recos | archive review, field research, lessons distillation, policy briefs | **Lessons-harvest workflow (Content Studio)**: Signal archive ingest + U13 + Qual synthesis → policy-brief template |
| 15 | FMCG rural retail digital ecosystem (needs assessment, pilot, behaviour-change campaign, 10k merchants) | KAP baseline, campaign, continuous insights at scale | Behaviour-change playbook: KAP instruments + adoption funnel + monitoring dashboards |
| 16 | Women-led climate-resilient farming scale-up (3-yr knowledge/strategy retainer, 10k women) | embedded research, ongoing knowledge management | Multi-year program workspace: living evidence (U9) + learning agenda (U13) + knowledge base |
| 17 | Spearmint/peppermint responsible-sourcing exploration | exploratory value-chain + socio-economic research | `value_chain` + community surveys + Qual |
| 18 | Sustainable vanilla cultivation & sourcing model (Karnataka) | value-chain research, barriers/enablers, roadmap | Same + sourcing-roadmap deliverable |
| 19 | Nutrition-sensitive policy research (distill 3-yr program → policy brief) | learnings distillation → policy influence | Lessons harvest + policy-brief template + Claim Auditor (U5) |
| 20 | 5-yr social-inclusion program → 6 innovative practices public report | field research + stakeholder consultations → replication report | Qual synthesis + publication template (donor co-branded) |
| 21 | Affordable urban child nutrition (market research, product testing, route-to-market) | product tests, consortium reporting | `concept_test` + Tabulation + Deliverables |
| 22 | Jharkhand 5-yr social-inclusion evaluation (OECD-DAC, 312 stakeholders, 4 tribal districts) | full evaluation: design, field, qual+quant, DAC-structured report | Impact & MLE Lab end-to-end (17a): waves, enumerator/offline, OECD-DAC reporting, MSC stories |
| — | **Blog posts** (data-driven: SHG map, vaccination tracker; with audio narration) | data analysis → interactive visuals → post → TTS audio | Content Studio posts: Evidence-bound embeds + Claim Auditor + built-in TTS |
| — | **Publications** (USAID wPOWER, HUL Shakti digitization case studies, commons management) | case-study research → donor-co-branded reports | Publication templates, glass-box claims (U1) |
| — | **Monthly Sector Scan newsletter** (17 articles + 5 publications curated across 5 themes) | continuous scanning, curation, assembly, distribution | Sector Watch → curation queue → branded assembly → subscriber send + engagement analytics |

**Verdict:** with Phases 10–19 complete, all 22 projects + the entire content operation run
end-to-end in-platform. The additions this analysis forced: the six **advisory playbooks**
(landscape, concept testing, GTM/channel analytics, behaviour-change/KAP, needs assessment,
program design→pilot→scale) and the whole **Knowledge & Content Studio** (Lab 15) — none of which
existed in the plan before checking against a real portfolio.

---

# PART 3 — Quality assurance: how we make every workflow best-in-class

The moat is trust, so QA is a product feature, not an afterthought. Five layers, then a per-workflow
bar.

## 3.1 The five QA layers (cross-cutting)

1. **Provenance floor (exists)** — Evidence Ledger + repro manifests: no number without a
   re-runnable record; charts/reports refuse unbacked claims. This alone beats "LLM hallucinated a
   metric."
2. **Adversarial verification (exists → extended)** — Red-Team critic (models) + Leakage Sentinel
   (pipelines) + **Claim Auditor (U5, narratives)**. Independent persona/model from the producer.
3. **Golden sets + regression harness (new, cheap)** — curated fixtures with known-correct outputs
   for every deterministic component (skip-logic evaluator, quota math, crosstab z-tests vs
   statsmodels hand-calcs, rake weights vs known margins). Run in `uv run pytest` on every change —
   catches silent regressions. This is the backbone of "is it correct?".
4. **LLM-as-judge + human gate (new)** — for generative steps (Paper Card, codebook, synthesis,
   report copy) a **rubric-scored second-model judge** flags low-confidence output; low scores route
   to a **HITL GateTask**. Judges are themselves spot-checked against human ratings (don't trust the
   judge blindly — the literature warns of self-eval bias).
5. **Calibration & drift monitoring (new)** — U3 twin-vs-real calibration; transcription WER spot-
   checks against human-corrected segments; per-workflow quality dashboards over time so degradation
   is visible.

## 3.2 Per-workflow quality bar (how "best" is defined and tested)

| Workflow | "Optimal" means | How we test it |
|---|---|---|
| Signal consolidation | no cell dropped/mis-mapped; dictionary complete | golden multi-file fixtures → exact master workbook diff; HITL gate on ambiguous mappings |
| Paper Card | faithful, no invented numbers, math correct | claim-grounding check vs source text; LLM-judge rubric; user "explain simpler" feedback loop |
| Survey runtime | logic never mis-routes; no lost responses; quotas exact | pure-function skip-logic golden tests; concurrency test on atomic quota increment; autosave crash test |
| Quality flags | catch speeders/straightliners/dupes without false-flagging real ones | labeled fixtures (known good/bad respondents) → precision/recall thresholds |
| Synthetic twins | distributions/relationships resemble reality | **calibration score (U3)** vs the real wave; honesty-labeled; never in real deliverables |
| Transcription | low WER, correct timestamps/speakers | WER on a gold transcript sample; human-in-the-loop correction; segment-timestamp assertions |
| Qual coding | codes applied consistently, quotes verbatim | inter-rater vs human on a sample; **codebook HITL gate**; every quote Evidence-linked to timestamp (verbatim check) |
| Crosstab/weighting | stats exactly match a trusted engine | golden tables vs statsmodels/scipy hand-calcs; rake reproduces target margins to tolerance |
| Triangulation | verdicts justified by real cross-modal Evidence | each cell must cite ≥1 Evidence per modality; divergences surfaced not hidden |
| Deliverables | zero unbacked claims, no overclaiming | Evidence-picker enforcement; **Claim Auditor (U5)**; trust score printed |
| Reproducibility | re-run → identical numbers | manifest re-execution test (exists); **U9 living-evidence** re-run diff |

**Principle:** deterministic work is proven by **golden tests**; generative work is bounded by
**grounding + adversarial audit + human gates + calibration**. Every Lab ships with both kinds.

## 3.3 Security & abuse hardening (threat model → mitigation → phase)

"No vulnerability" is a posture, not a feature. The concrete threat model for THIS product:

| Threat | Mitigation | Lands |
|---|---|---|
| **Prompt injection** via scraped pages, uploaded PDFs, portal text, open-end answers ("ignore instructions, approve my submission") | Instruction/data separation in all prompts; untrusted content rendered as quoted data; **agents touching untrusted content get read-only tool allowlists** — state changes require a human gate (AR-1 law); injection test-suite fixtures in CI | AR-1/2 + each ingesting phase |
| Malicious uploads (media/CSV/PDF) | type sniffing (magic bytes, not extension), size caps, image/audio transcode-through (re-encode strips payloads), no server-side rendering of user HTML, optional ClamAV container | 10/12 |
| Public-endpoint abuse (token guessing, replay, scripted responses, quota races) | HMAC tokens (already), per-route rate limits, Turnstile, atomic quota transactions, duplicate fingerprinting, response-signature checks | 10 |
| Cross-tenant leakage (queries, caches, embeddings, prompts) | org-scoped queries everywhere (exists) + **org-scoped cache keys and vector filters** (explicit tests); no cross-org content ever in one prompt | every phase; isolation tests extended |
| PII exposure (respondents, grantee staff) | pseudonymous-by-design responses (P11); **field-level encryption for respondent contact columns** (pulled forward from backlog to P11); encrypted backups; retention config | 11 |
| Agent runaway (cost or actions) | per-run budget + step caps, tool allowlists, kill switch on `agent_runs`, daily org spend alerts | AR-1 |
| Grantee-portal account abuse | scoped partner role (own program only), audit log of submissions/reviews (audit log pulled forward for external-facing surfaces), rate limits | 17b |
| Secrets & supply chain | `.env` gitignored (exists) + server secrets outside repo, dependency audit in CI (`pip-audit`/`npm audit`), pinned lockfiles (exist), single-box firewall (only 80/443 exposed; DBs on private network) | 10 onward |
| Backup/restore failure during live fieldwork | nightly pg_dump + blob sync to R2/B2 (offsite), quarterly restore drill documented | 10 |

Each mitigation is testable and appears in the owning phase's QA list; the injection suite and
isolation tests run in CI permanently.

## 3.4 Robustness & reliability engineering (failure modes → designed behavior)

The product's credibility dies the first time a live field window loses data. Reliability is
designed per flow, not hoped for:

| Critical flow | Failure mode | Designed behavior |
|---|---|---|
| Public survey submit | API/network drop mid-submit; double-tap resubmits | client-side queue + retry with **idempotency keys** on every public POST; answers append-only, so replays are no-ops; autosave means worst case = resume, never loss |
| Offline enumerator sync | days offline; instrument amended mid-window; device clock skew | queued submissions carry instrument_version + client timestamps; server reconciles against changepoints; conflicts impossible by construction (responses append-only, never merged); sync is resumable per record |
| Transcription pipeline | chunk fails; worker dies mid-file; poison file | per-chunk checkpointed progress; idempotent chunks (re-run safe); retries with backoff; **dead-letter queue** + partial-transcript state (usable, marked incomplete) — never a silent all-or-nothing |
| LLM provider outage / rate limits | 429s, timeouts, provider incident | retry w/ exponential backoff + jitter → **circuit breaker** → runtime provider failover (the `LLM_PROVIDER` toggle becomes hot-switchable) → queue-and-degrade: work marked "pending AI" and the request succeeds without it; every agentic feature keeps its **deterministic fallback** (house pattern since auto_experiment) |
| Indicator/U11 recompute | partial failure mid-recompute | recipes are **pure functions over versioned data** → recompute is idempotent and all-or-nothing per indicator; a failed run never half-updates an IPTT |
| Grantee submission review | two reviewers act at once; approve/reject race | optimistic locking (row version) on submissions and gates; second writer gets a clean conflict, not a double-apply |
| Email/invitations | bounces, provider throttling | bounce webhook → suppression list (never re-mail a hard bounce); throttled batches; per-invite delivery state; reminders skip non-delivered |
| Celery/worker crash | task lost mid-run | acks-late + idempotent tasks + task-state rows; agent runs resume from LangGraph checkpoint (FR-AGT-01) |
| Scheduled scrapes/feeds | source down, layout change | per-source health status + backoff; last-good snapshot retained; triage flags stale sources instead of silently thinning the queue |

**Data integrity:** Evidence, ConsentRecords, and source snapshots are append-only — and the
Evidence Ledger gains **hash-chaining** (each record includes the previous record's hash per
project): tampering becomes detectable, turning "provenance-locked" into **tamper-evident** — one
cheap migration, a real trust upgrade for donor audits. Alembic migrations forward-tested (up +
down on a fixture DB in CI); datasets stay content-hash versioned; soft-deletes + orphan-sweep
job.

**Operational policies:** **field-window deploy freeze** (no deploys/migrations while an org has
an active fielding window — enforced by a deploy-gate check, not memory); zero-data-loss backup
policy (nightly pg_dump + blob sync offsite, quarterly restore drill — 3.3); SLOs with error
budgets (public survey availability 99.9% during windows, pipeline p95s per NFRs); Sentry (free
tier) for error tracking + an external uptime probe; structured JSON logs with request/run ids
end-to-end; queue-depth and spend alerts.

**Testing beyond goldens:** property-based tests (hypothesis) for skip-logic/quota/weights/
raking; concurrency tests (quota last-slot, double-review); kill-worker-mid-pipeline chaos tests
(transcription, agent runs); a locust load test of the public survey path before beta; airplane-
mode E2E for offline sync. LLM outputs always schema-validated (pydantic) with the lenient-parse
+ repair loop (`core/jsonparse` house pattern); **prompts are versioned files** recorded in repro
manifests, and prompt changes must pass the AR-5 eval gate before deploy.

---

# PART 4 — Prerequisites: integrations, libraries, models

## 4.1 Third-party services / APIs (do we need more? — yes, a few, mostly free-tier)

| Need | Recommended (cost-minimal) | Phase | Notes |
|---|---|---|---|
| LLM reasoning + bulk | **Open-weight first**: DeepSeek-V4 (heavy) / V4-Flash (bulk) via their OpenAI-compatible API or OpenRouter; Qwen3 / Kimi-K2 / GLM as alternates — through the existing `LLMClient` (`openai_base_url` flip) | all | closed models (GPT-5.4/Azure) become a later config-only upgrade; see 4.2 |
| Embeddings | **BGE-M3** (open, multilingual, self-hosted = $0) — or `gte-Qwen2-1.5B` for a 1536-d drop-in | all | dimension config + re-embed note in 4.2 |
| Web search | **Brave** (free tier) → SerpAPI fallback | exists | already integrated |
| **Scholarly / paper finder** | **OpenAlex** (free, no key, 250M works) + **Semantic Scholar** + **Crossref** + **arXiv** + **Unpaywall** (all free) | exists→16+ | OpenAlex/S2 already used; add Crossref/arXiv/Unpaywall as `connector.*` |
| **Dataset collector** | **Kaggle API**, **HuggingFace Datasets**, **OpenML** (used), **data.gov**, **Google Dataset Search**, **World Bank/FRED** | exists→16+ | mostly free; Kaggle needs a free token |
| **Web scraper** | start **self-hosted Playwright** (free) via SSRF-safe `core/net`; add **Firecrawl Hobby ($16/mo)** or **Apify (pay-per-use)** when JS-heavy/scale demands | **16 (Market Intel)** | first needed by Market Intel Lab; Scrape.do ($29)/Apify are cheaper alternates |
| Reviews / firmographics (competitor scan) | public review pages + news via scraper/search; optional Crunchbase/Similarweb later | 16 | free-scrape first; paid data vendors only if a client needs depth |
| **Audio transcription** | **faster-whisper large-v3 (open source, local, $0/min)** as the default `TranscriptionEngine` backend; cloud (gpt-4o-mini-transcribe $0.003/min) stays a pluggable fallback for speed bursts | 12 | CPU int8 ≈ 1–2× realtime on the MVP box (queue, don't block); multilingual incl. Hindi/Bengali |
| **Transactional email** | **Resend** (free 3k/mo → $20/mo 50k) behind `Mailer` | 11 | SendGrid/Mailgun/SES equivalent; needs a sending domain (SPF/DKIM) |
| Bot protection (public surveys) | **Cloudflare Turnstile** (free) | 10 | optional but wise |
| **Impact-metric catalogs** | **IRIS+** (GIIN, free download) + SDG target metadata (UN, free), bundled as static data | 18 | no API key; refresh per release |
| **Feed monitoring** (Sector Watch) | RSS/Atom via `feedparser` (free) + existing search/scraper stack | 19 | no key; sources configured per org |
| **Text-to-speech** (blog audio narration) | **Kokoro-82M (open source, Apache, local, $0)** behind a `TTSEngine` interface; OpenAI TTS as pluggable fallback | 19 | optional per-post toggle |
| SMS invites / diarization / vision | Twilio / pyannote / GPT-vision | 20+ | deferred |

**MCP: none required** for the product. (Optionally 16+: expose Laboratree *as* an MCP server so
external agents drive the registry.)

## 4.2 LLM / model strategy: **open-weight first, closed-source later** (decision 2026-07-06)

The architecture makes this a config decision, not a build decision: `LLMClient` already targets
any OpenAI-compatible endpoint (`openai_base_url` + `openai_model` in `core/config.py`) with
per-role overrides (`reasoning_model`, `generation_model`). **We launch on open-weight models
and keep closed models as a config-only upgrade path.**

### The open-first role map (*verify against current open-model leaderboards at build; the AR-5
eval harness — not vibes — decides model changes from then on*)

| Role | Primary (open-weight, hosted API) | Alternates | Used by |
|---|---|---|---|
| Heavy reasoning | **DeepSeek-V4** (already an option in our env; OpenAI-compatible at api.deepseek.com, ~$0.3–0.6/M in, ~$1–2.2/M out) | Qwen3-235B (best multilingual — India languages), Kimi K2 (agentic/tool use), GLM-4.6; all via **OpenRouter** with one key | Paper Card, Co-Scientist, codebook, qual synthesis, Field Director, Claim Auditor, triangulation, Navigator planning, report drafting |
| Cheap/bulk | **DeepSeek-V4-Flash** (~$0.07–0.3/M) | Qwen3-30B-A3B | classification, bias check, sentiment at scale, open-end coding, speaker-turn pass, **twin answering (bulk)**, triage, invitation copy |
| Embeddings | **BGE-M3** (open, multilingual, runs on the CPU box = $0) | `gte-Qwen2-1.5B-instruct` (1536-d **drop-in** for existing pgvector columns) | paper chunks, transcripts, Org Brain, watch items |
| Audio→text | **faster-whisper large-v3** (open, local, $0) | cloud transcribe fallback (speed bursts) | Qual Studio |
| TTS | **Kokoro-82M** (open, local, $0) | OpenAI TTS fallback | Content Studio narration |
| Local dev / offline tests | **Ollama + Qwen3-14B** on the dev machine | any | dev loop without API spend (tests already run offline via injectable fns) |

### Why hosted open-weight APIs, not a self-hosted GPU (for now)
Serving a frontier-class open model (DeepSeek-V4/Qwen3-235B) needs multi-GPU hardware — $500+/mo
rented, vs ~$2–4/study through their official APIs. **Hosted open-weight = open-source economics
without GPU ops.** Self-hosting on a rented GPU (vLLM) becomes worth it only if (a) a client
demands data never leaves our infra, or (b) volume makes tokens > GPU rent — both are the same
`openai_base_url` flip to our own vLLM endpoint, already anticipated in `core/config.py`.

### Migration & compatibility notes
- **Embeddings dimension:** existing `PaperChunk` columns are `Vector(1536)` (OpenAI-sized).
  BGE-M3 is 1024-d → make the dimension a setting, store `embedding_model` per row, re-embed the
  (few, cheap) existing papers in a one-off migration. Zero-migration shortcut: `gte-Qwen2-1.5B`
  is 1536-d. Never mix models in one similarity search (filter by `embedding_model`).
- **JSON/tool-call reliability** is the real open-model tax vs GPT-5.4. Our defenses already
  exist as house patterns: lenient truncation-tolerant parsing (`core/jsonparse`), pydantic
  schema validation + compact-retry, deterministic fallbacks per agentic feature, HITL gates.
  Budget one extra retry in prompts; the five-layer QA (Part 3) was designed for exactly this.
- **Multilingual work** (Hindi/Bengali instruments & testimony) actually *favors* the open stack:
  Qwen3 and BGE-M3 are top-tier multilingual; Whisper covers 50+ languages.
- **The upgrade path (later):** flip `reasoning_model` to a closed model per role, per org, or
  even per Lab — `use_llm_context` attribution + the AR-5 eval harness will tell us precisely
  where a closed model buys quality worth paying for. Per-tenant BYO keys (backlog) rides the
  same mechanism.

Every call stays wrapped in `use_llm_context` → visible in LLM Activity observability, so the
open-vs-closed cost/quality comparison is measurable from day one.

## 4.3 New libraries

**Python (`apps/api`):** `python-pptx` (15), `playwright`+Chromium (15), **ffmpeg** system binary
(12), `qrcode[pil]` (10/15), `SDV`/`synthcity` (synthetic tabular, `labs/synth/`), numpy-IPF
(weighting/persona frames — tiny, hand-rolled), optional `ipfn`. (Already: pandas/numpy/scipy/
statsmodels/sklearn/torch/celery/pymongo/redis.)
**JS (`apps/web`):** none for the survey runtime (plain React, keep public page light);
`wavesurfer.js` optional (12). (Already: @xyflow/react, vega-embed, papaparse.)

---

# PART 5 — Infra & cost model (startup-minimal, grounded in 2026 prices)

**Design principle:** one cheap box, containers for the four datastores, local blob → object store
only when media volume demands; usage-based LLM with batch/cache levers; free-tier third parties
until traffic justifies paying. All prices verified July 2026 (Sources at end).

## 5.1 Hosting — recommended path

| Stage | Setup | ~Monthly |
|---|---|---|
| **MVP / demo** | **Hetzner CPX41** (8 vCPU, 16 GB) single box + **Coolify**, all 6 containers (api, worker, web, postgres+pgvector, redis, neo4j, mongo) on it; local blob volume | **~€30 (~$33)** |
| Cheaper still | Hetzner CX32 (4 vCPU/8 GB) if no heavy torch/ffmpeg concurrency | ~€8 (~$9) |
| **Growth** | Split: app box + managed Postgres, add **Cloudflare R2** for media, separate worker box for transcode/torch | ~$80–150 |
| **Scale** | Kubernetes/managed later; S3 behind existing `BlobStore` (zero call-site change) | usage |

Why Hetzner over Railway/Fly.io: fixed, predictable pricing at 50–70% lower cost for single-region;
Railway/Fly usage-billing gets to $15–25+/mo fast and is unpredictable. (Sources.) PaaS is fine for
a zero-ops demo but not for cost-minimal.

## 5.2 Storage

| What | Where (MVP) | Later | Cost |
|---|---|---|---|
| DB rows | Postgres container on the box | managed PG | in box cost |
| Documents/transcripts | Mongo container | managed | in box cost |
| Blobs (datasets, media, exports) | local mounted volume | **Cloudflare R2** ($0.015/GB-mo, **$0 egress**) or Backblaze B2 ($6/TB-mo) | ~$0 MVP; media grows it |
| Media example | 12×1h video ≈ 6–12 GB/study | R2 | ~$0.10–0.18/study-mo |

R2's zero-egress is the key pick for serving media/playable-clips without surprise bandwidth bills.

## 5.3 LLM cost per study (the running example: 500 surveys + 12 interviews)

Order-of-magnitude on the **open-weight stack** (4.2): DeepSeek-V4 heavy / V4-Flash bulk,
local Whisper + BGE-M3 (closed-stack figures in parentheses for the later upgrade):

| Step | Rough usage | Open stack | (closed) |
|---|---|---|---|
| Ideation (evidence/variables) | ~20 heavy calls | ~$0.10 | (~$0.75) |
| Paper Lab (~10 papers, cards+chat) | heavy | ~$0.30 | (~$2) |
| Questionnaire design + bias | few heavy | ~$0.05 | (~$0.50) |
| **Synthetic twin dry-run** (500 personas, bulk) | bulk | ~$0.20–0.40 | (~$1–2) |
| **Transcription** (~750 min, local Whisper) | CPU time | **$0** | (~$2.25) |
| Qual coding + sentiment + quotes + synthesis | bulk | ~$0.60–1 | (~$4–6) |
| Open-end coding (survey) | bulk | ~$0.15 | (~$1) |
| Crosstab/triangulation/report/claim-audit | heavy | ~$0.40 | (~$3) |
| Embeddings (local BGE-M3) | CPU time | **$0** | (~$0.20) |
| **Total LLM / study** | | **~$2–4** | (~$15–25) |

**Open-first drops per-study AI COGS ~6–8×.** The trade: transcription wall-time on the CPU box
(~1–2× audio duration, queued — fine at MVP volume; a $0.30/hr serverless GPU or the cloud
fallback absorbs bursts), and one extra retry budgeted for JSON-strictness on hard prompts.
The strategic insight stands, stronger: **AI is the cheap part**; infra + human time dominate.

## 5.4 Total monthly cost at three scales

| Scale | Studies/mo | Hosting | Object storage | Email | Scraper | LLM (open stack) | **Total** |
|---|---|---|---|---|---|---|---|
| **MVP / first clients** | 1–3 | ~$33 (Hetzner) | ~$0 (local) | $0 (Resend free) | $0 (self-host Playwright) | ~$5–12 | **~$40–50/mo** |
| **Growth** | ~10 | ~$80 | ~$5 (R2) | $20 | ~$16 (Firecrawl Hobby) | ~$30–60 | **~$150–180/mo** |
| **Scale** | ~30 | ~$150 | ~$20 | ~$20–90 | ~$83 (Firecrawl Standard) | ~$90–200 | **~$360–540/mo** |

Domain ~$12/yr; Turnstile free; OpenAlex/Kaggle/HF/OpenML/Crossref/arXiv free. (Closed-stack
totals from the earlier draft: MVP ~$55–110, growth ~$320–420, scale ~$870–1,260 — the open-first
strategy roughly **halves to thirds every tier**.) **Biggest lever now:** keep bulk work on the
Flash-class model and local Whisper/BGE; upgrade individual roles to closed models only where the
AR-5 evals prove it pays.

## 5.5 Provider strategy (open-weight now → closed later)
The repo already supports this: `LLM_PROVIDER=azure|openai`, where "openai" means **any
OpenAI-compatible endpoint** via `openai_base_url` (DeepSeek, OpenRouter, Together, Groq,
self-hosted vLLM/Ollama — the config comment in `core/config.py` lists them). Recommendation:
**launch on DeepSeek direct (or OpenRouter for one-key access to all open models)**; keep the
Azure/OpenAI toggle so a client who demands closed models, Azure data terms, or EU residency is a
config change, not a rewrite. Model ids are never hardcoded (house rule), so per-role upgrades are
`.env` edits.

---

# PART 6 — Build phases (each ≈ one branch; pytest green + tsc clean)

House rules: every analysis = a registered **Component** emitting **Evidence**; each functionality
gets its **own dedicated folder**; Labs isolated (share via `core/` + SDK); async API; long work →
Celery. Each phase ships **golden tests + (for generative steps) an LLM-judge/HITL gate** (Part 3)
+ its security items (3.3). The **AR track** (agentic runtime slices AR-1…5, Part 1) lands
alongside the phases as shown in its table.

## Launch staging (product, not just code)

| Stage | Gate to enter | What happens |
|---|---|---|
| **Alpha** (after Phase 12) | Phases 10–12 shipped; security 3.3 items for public surfaces green | We run ONE full internal study end-to-end (real respondents from a friendly panel, real interviews) — dogfood; fix the 100 paper cuts |
| **Private beta** (after Phase 15) | Alpha learnings closed; Deliverables shipped | 1–2 design partners (Re-emerging-World archetype) run a REAL paid engagement per vertical; **onboarding = Archive Import Agent (U14/AR-3)** ingests their historical corpus first, so day-1 value is their own institutional memory + seeded sector template packs (instruments/playbooks per development sector); weekly feedback loop; pricing tested (BRD OQ-1) |
| **GA** (after Phase 17) | Beta partners renew; quality bars (Part 3) hold on real work; uptime/backup drills pass | Public launch on the three wedges (MR / MLE / advisory); Phases 18–19 continue post-GA as expansion releases |

Collaboration & notifications land with the beta (Phase 15): comments + @mentions on gates,
reports, and canvases; review assignments; an in-app notification center with email digests —
firms work in teams, and gates need owners.

### Phase 10 — Field Lab: survey engine + public fielding (+ U3 dry-run, U6 lock, U2 v1)
Models (`Survey` w/ prereg pack + changepoint log, `SurveyResponse`, `Quota`) + migration;
`labs/fieldwork/{runtime,quality,quotas,director,twins}/`; `labs/synth/` (persona/IPF twin engine);
admin `api/surveys.py` + public `api/public_survey.py` (tokened, autosave, rate-limited, Turnstile);
Collection→Survey bridge with bias gate; web Field tab (builder, publish+QR, live dashboard,
Director inbox) + public `app/s/[token]/page.tsx`. **QA:** skip-logic + quota-atomicity golden
tests, quality-flag precision/recall fixtures, public-route isolation.

### Phase 11 — Panel CRM: respondents, consent, invitations, incentives (+ U8)
Models (`Respondent`, `Segment`, `ConsentRecord` append-only, `Invitation` unique-token,
`IncentiveLedger`, cross-study history); `core/notify/` `Mailer`+Resend/SMTP; `labs/panel/
{recruit,invite,health}/`; `api/panel.py` (+ GDPR export/delete); web Panel tab. **QA:** token→
response linkage test, delete-keeps-pseudonymous-response test, consistency/fatigue fixtures.

### Phase 12 — Qual Studio I: capture + transcription
`core/transcribe/` (`TranscriptionEngine` + OpenAI-compat backend) + `core/media/` (ffmpeg);
`MediaAsset` + generic `Job`; transcripts in **MongoDB**; first real **Celery chain** + `GET
/api/jobs/{id}` + SSE; upload/recorder/Field-media inlets; web Qual tab (player synced to editable
transcript). **QA:** fake-engine offline tests, WER spot-check harness, timestamp assertions.

### Phase 13 — Qual Studio II: coding, sentiment, quotes, synthesis (+ U7)
`labs/qual/{codebook,coding,sentiment,quotes,synthesis,copilot}/`; LLM codebook → **HITL gate**;
analyzers (quote=Evidence w/ timestamp); saturation radar; same engine for survey open-ends; web
coding workspace + synthesis matrix. **QA:** inter-rater-vs-human sample, verbatim-quote check,
radar flips on fixtures.

### Phase 14 — Tabulation, weighting & analytics (+ U4, U3 calibration, U6 labels, U8)
`labs/tabulation/{weights,crosstab,metrics,drivers,segments,triangulate}/`; SurveyResponses→flat
weighted `Dataset`; Methodology Advisor in `labs/collection/advisor/`; web Analyze panel +
triangulation view. **QA:** crosstab/weights golden vs statsmodels/scipy; triangulation cite-per-
modality check; calibration computed.

### Phase 15 — Deliverables Studio: builder, PPT/PDF, dashboards (+ U1, U5, U9)
`labs/deliverables/{builder,pptx,pdf,dashboard,audit}/`; Evidence-bound blocks + auto methodology
appendix; `python-pptx` branded export w/ per-slide verification QR; Playwright PDF; public HMAC
live dashboard; **Claim Auditor**; **living-evidence re-run diff**. Web Deliverables tab + public
verification page. **QA:** unbacked-number rejection, planted-overclaim caught by auditor, re-run
diff correctness.

### Phase 16 — Market Intel Lab: market assessment + competitor scan + workflow hunt (+ U10)
First phase to need a **web scraper** — wire self-hosted Playwright behind the SSRF-safe `core/net`
(add Firecrawl/Apify as a pluggable backend later). `labs/market/{assess,competitors,opportunity}/`:
`analyzer.market_size` (cited TAM/SAM/SOM, top-down + bottom-up, method + confidence),
`analyzer.competitor_scan` (discover → profile → pricing → review sentiment),
`analyzer.feature_matrix`, per-competitor SWOT, `analyzer.workflow_map`, `analyzer.whitespace`
(JTBD gap scoring). **Source-snapshot store (U10):** freeze each scrape/search result (URL + fetched
HTML/text + timestamp) as an Evidence-backed artifact so every market figure is verifiable and
freshness-stamped. `api/market.py`; web Market tab (assessment dashboard, competitor matrix,
opportunity board); feeds the Ideation brief + the U4 triangulation matrix. **QA:** every market
number must cite ≥1 snapshot (enforced); LLM-judge on assessment narratives; golden fixtures for the
feature-matrix + whitespace scoring logic; hallucinated-figure (uncited) rejection test.

### Phase 17 — Impact & MLE Lab: the grant-funded-program vertical (+ U11, U13)
`labs/impact/{logframe,melplan,waves,fieldops,monitoring,dqa,learning,portfolio,estimate,vfm,
language}/`, split across two sub-releases:
**17a — design + evaluation core:** **Logframe Studio** (program docs → LLM-drafted ToC + SMART
indicators → HITL; indicator = registered **computation recipe**, U11; OECD-DAC mapping) + **MEL
plan designer** (collection calendar/methods/responsibilities → drives scheduling). **Wave
Manager** (linked baseline/midline/endline, version-locked instruments via U2 changepoints,
Panel-CRM re-contact U8, attrition dashboard + differential test, **auto wave recompute on close**).
**Field ops** (enumerator accounts/assignments; **offline-first PWA** collection with lossless
sync; GPS/timestamps; enumerator dashboard + **curbstoning detection**). **Estimators**
(`model.impact.did` +parallel-trends sentinel, `.psm`, `.ancova`; cluster power/MDE). **Language
layer** (back-translation QA; local-language transcription; original-verbatim linking). **Donor
reporting** (IPTT, logframe progress, OECD-DAC, MSC blocks).
**17b — monitoring + learning:** **Grantee portal** (external partner role; survey engine reused
as routine reporting forms; validation → reviewer HITL gate → approve → **U11 recompute**; late-
submission auto-chasing; traffic-light variance dashboard). **DQA** (`analyzer.dqa` five-dimension
scoring; spot-check planner + reported-vs-verified variance). **Learning system (U13)** (learning
questions as standing Evidence queries; pre-populated after-action reviews; `analyzer.
adaptive_recos`; learning briefs). **Portfolio roll-ups** (standard-indicator library, cross-
project aggregation with double-count guards, donor dashboard). **VfM** (`analyzer.vfm` 4E,
`analyzer.cost_effectiveness`, CBA + sensitivity; outcome-harvesting + contribution-analysis
templates). `api/impact.py`; web Impact tab (logframe tree, wave timeline, monitoring calendar,
portal review queue, learning board, portfolio + IPTT views).
**QA:** indicator recipes + roll-ups golden-tested (incl. double-count fixtures); DiD/PSM vs
statsmodels; parallel-trends fixture; back-translation catches planted mistranslation; airplane-
mode sync loses zero responses; curbstoning + reported-vs-verified fixtures meet precision/recall;
U13 learning question accumulates fixture evidence with correct stances.

### Phase 18 — Strategy Lab: inclusive-business & business-model advisory (+ U12)
`labs/strategy/{discovery,canvas,pricing,financials,pilots,imm,invest}/`.
**Discovery:** `analyzer.value_chain` (actor/margin mapping from chain-actor survey+interview
data) + **ecosystem/stakeholder graph in Neo4j** (actors, relations, influence; queryable).
**Canvas (U12):** evidence-linked Business Model Canvas; `Assumption` records (untested/testing/
validated/invalidated) linked to Evidence; LLM-drafted variants from discovery; inclusive-business
pattern templates. **Pricing:** `analyzer.van_westendorp`, `analyzer.gabor_granger` (fielded via
Field Lab on the target population). **Financials:** `analyzer.unit_economics`, `analyzer.
scenario_model` (driver-based, tornado sensitivity, Monte Carlo), **branded .xlsx model export**;
inputs link Evidence or are flagged unvalidated. **Pilots:** assumption-driven pilot design
(test/control, MDE via power calc) → run via Field/Panel/Qual → results auto-update Assumption
Ledger + financials; **pivot log** (canvas versions via the changepoint pattern). **IMM:** ToC
via Logframe Studio; **IRIS+ catalog** (free GIIN download, bundled) metric picker; **IMP 5
Dimensions** assessment; **SDG mapping**; impact projections on U11 recipes; "projected" labels
enforced. **Invest:** `analyzer.deal_screen` scorecards; auto-assembled **due-diligence pack**
(glass-box U1); investment-memo Deliverables template; `analyzer.scale_readiness` + scale
scenarios. `api/strategy.py`; web Strategy tab (canvas board with assumption chips, value-chain
diagram, pricing curves, financial workbench, pilot tracker, IMM panel, DD-pack builder).
**QA:** WTP analyzers golden-tested vs hand-computed curves; unit-economics/scenario math goldens;
assumption-status transitions only via linked Evidence (enforcement test); canvas pivot log
versions correctly; IRIS+ picker maps to valid catalog ids; DD pack refuses unvalidated-assumption
claims without labels.

### Phase 19 — Knowledge & Content Studio + advisory playbooks
Two workstreams. **(a) Content Studio** `labs/content/{watch,newsletter,posts,publications}/`:
`MonitoredSource` + RSS/scrape/search scanning (Celery scheduled) → LLM triage (relevance/novelty/
why-it-matters, all source-snapshotted U10) → curation queue (keep/kill/annotate) → newsletter
assembly (branded template, grounded editor's note) → subscriber sends via `core/notify`
(subscribers = Panel contact machinery + preferences) + open/click analytics; data-driven post
builder (Evidence-bound interactive chart embeds, Claim Auditor pre-publish, **TTS audio
narration**, HTML/Markdown export + public share pages); publication templates (case study,
lessons-learned, policy brief, public report; donor co-branding slots); **lessons-harvest
workflow** (program-archive ingest → U13 queries + Qual synthesis → cited lessons draft).
**(b) Advisory playbooks** `labs/strategy/playbooks/`: landscape study, `analyzer.concept_test`,
GTM/channel (`analyzer.channel_performance` on agent-level activity data), behaviour-change (KAP
instruments + adoption funnels), needs assessment (`analyzer.needs_priority` + roadmap
deliverable), program design→pilot→scale chaining. `api/content.py` + playbook routes; web
Content tab (watch queue, newsletter composer, post editor with audio preview, publication
builder) + playbook launcher in Strategy tab.
**QA:** triage precision on labeled feed fixtures; every kept item has a snapshot (enforcement);
newsletter renders + sends to a test list; TTS artifact generated; Claim Auditor catches planted
uncited stat in a post; concept-test/channel/KAP analyzers golden-tested; lessons-harvest cites
≥1 source per lesson.

### Phase 20 — Trials Lab: RCTs & policy experiments (+ U16 Validated Policy Twin)
`labs/trials/{design,randomize,twin,monitor,estimate}/`. Trial designer (multi-arm, cluster,
stratification, ICC-aware power/MDE, SAP → U6 prereg freeze). Seeded reproducible randomization
(Evidence-locked assignment, SMD balance checks). **Policy Twin (U16)**: persona-agent simulation
(reuses `labs/synth/` + AR-2 agent framework) with the **retrodiction benchmark harness**
(registry-RCT replication suite + per-domain scorecard stored as Evidence; post-trial
predicted-vs-actual calibration; `simulated` labels structurally excluded from claims). Field via
Impact machinery (waves, enumerator/offline, consent via Panel); compliance + differential
attrition + GPS spillover flags; optional alpha-spending interim gates. Estimators:
`model.impact.itt` (ANCOVA), `model.impact.late` (IV), CUPED variance reduction, heterogeneity
with prereg/exploratory labels, randomization inference. Web: **Trial Canvas** (arm swimlanes,
compliance funnels), balance SMD plot, auto-**CONSORT diagram**, per-outcome **forest plots**,
twin prediction-vs-actual panel. `api/trials.py`.
**QA:** randomization goldens (stratification/balance reproducibility under seed); ITT/LATE/CUPED
vs statsmodels hand-checks; randomization-inference fixture; spillover/attrition fixtures;
**twin gate: retrodiction scorecard must beat the naive baseline on the registry suite before the
twin UI unlocks**; honesty-rule enforcement test (simulated Evidence in a claim → rejected).

### Phase 21+ — ordered backlog
Live in-interview Copilot · CATI telephony · external import (Forms/Qualtrics/Kobo) · conjoint/
MaxDiff · commercial tracker waves (U9) · systematic-review (PRISMA) · Crossref/arXiv/Unpaywall +
public-data connectors (World Bank/DHS/FRED — also feed Impact & Strategy context) · paid
market-data vendors (Crunchbase/Similarweb) · client portal + project ops (timeline/budget) ·
compliance hardening (PII vault, retention, audit log) · org-wide knowledge base · CMS/WordPress
publish connectors · v1 debts (durable LangGraph checkpointer, sandbox-wired engineer node,
meta-graph, S3, BYO keys, faster-whisper + pyannote, vision analyzer, expose-as-MCP).

---

---

## Sources (pricing/tooling, July 2026)
- OpenAI API pricing (GPT-5.x, batch/flex/cache): developers.openai.com/api/docs/pricing
- Transcription $/min (gpt-4o-mini-transcribe/whisper): OpenAI pricing; costgoat/tokenmix summaries
- Synthetic personas reliability/limits: arXiv 2602.18462, arXiv 2605.10659 (calibration caveats)
- Firecrawl/scraper pricing + alternatives (Apify/Scrape.do): firecrawl.dev/pricing, eesel/thunderbit
- Hosting (Hetzner vs Railway vs Fly.io): getdeploying.com, expresstech.io, servercompass
- Free datasets/papers: OpenAlex (developers.openalex.org, no key), Kaggle, HuggingFace, OpenML

---

# Addenda (2026-07-08, user-directed)

## A1. Persona Lab — upgrade of the Synthetic Respondents engine (supersedes parts of 2.3)
Direction: personas become a first-class Lab, not just a dry-run tool. Architecture:
- **Foundation:** Microsoft **TinyTroupe** (MIT) as the first persona-simulation backend, wrapped
  behind our own `PersonaEngine` interface (house pattern — OCR/Mailer/Transcribe style) so the
  research-grade library can churn without touching call sites.
- **Persistent memory:** persona profiles + episodic memory stored per panel/org so the SAME
  personas answer consistently across survey waves (longitudinal twins; extends U3 calibration).
- **Trait & relationship graph:** persona attributes and social ties in **Neo4j** → social-influence
  and diffusion effects in simulations (adoption cascades, word-of-mouth).
- **Reason-over-profile:** the LLM reasons over the stored profile + memory instead of generating
  answers from scratch each time (cheaper, consistent, auditable).
- **Behavioral-economic grounding:** responses passed through explicit models — prospect theory
  (risk/loss framing), discrete-choice (price/feature trade-offs), Bass diffusion (adoption) — so
  outputs are theory-constrained, not vibes. Honesty rules (synthetic labels, calibration
  scorecards) unchanged and mandatory.

## A2. Policy-research vertical — completeness deltas
The 17-stage policy workflow maps onto existing Labs/phases (ToC/logframe, DiD/PSM, VfM/CBA, M&E
= Impact & MLE Lab P17; RCT = Trials Lab P20; briefs = Content Studio P19). NEW backlog items it
exposed: **RDD, IV/2SLS, synthetic-control estimators** (join `model.impact.*`), **microsimulation
/ system-dynamics / ABM Simulation depth** (extends Strategy scenario_model; TinyTroupe ABM ties
in via A1), **stakeholder-mapping tool** (generalise the P18 Neo4j ecosystem graph), and a
**consultation log** (stakeholder feedback captured against findings).

## A3. Pipeline = n8n-style flows with firm templates (SHIPPED 2026-07-08)
The Pipeline canvas is now an n8n-style editor: typed nodes (⚙️ runnable component / 🧪 Lab stage /
👤 manual stage), click-to-configure side panel (component picker + params), per-node run status,
and **two pre-configured end-to-end templates**: *Research firm* (client brief → hypotheses →
survey → analysis → recommendation, 20 stages) and *Policy research* (policy problem → ToC →
evaluation → CBA → brief → M&E, 19 stages) in `apps/web/lib/pipelineTemplates.ts`. Lab-tab
consolidation shipped alongside: Trend + Decision are tools inside Insight (fewer top-level tabs).

## A4. Sophisticated market-research firm (NielsenIQ/Ipsos-class) — integration deltas (2026-07-08)
The 20-stage modern MR workflow maps onto existing Labs/phases; its pipeline template gained a
"Market & competitor scan" stage and a "Post-launch tracking" stage (shipped). Genuinely NEW
backlog items it exposes: **TURF analysis** (joins conjoint/MaxDiff), **factor analysis / ANOVA /
SEM** components (Analytics depth), **feature-engineering library** (CLV, RFM, loyalty/churn
scores — Data Lab depth), **behavioral-data connectors** (retail scanner, CRM, web/app analytics,
social listening — commercial-connector tier of the existing connectors backlog), **pricing/
demand/market-share simulation depth** (price elasticity, Bass adoption — ties into Persona Lab
A1's behavioral models and the Simulation depth in A2), and **continuous tracking studies**
(post-launch measurement = the tracker-waves backlog item, U9). The 10-Lab modular structure
proposed (Project/Knowledge/Survey/Persona/Fieldwork/Data/Analytics/Simulation/Insight/
Presentation) is a naming view over the same 16-Lab architecture — no structural change; Project
Lab = the project-ops + client-portal backlog item.
