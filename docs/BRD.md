# Laboratree — Business Requirements Document (BRD)

| | |
|---|---|
| **Version** | 1.0 (draft) |
| **Date** | 2026-07-05 |
| **Owner** | Sourav Mondal (Founder) |
| **Status** | For approval |
| **Related** | `docs/PRD.md` (product spec), `docs/ECOSYSTEM_ROADMAP.md` (engineering plan) |

## 1. Executive summary
Laboratree is a **trustworthy, agentic, human-in-the-loop research lab SaaS**: one platform where a
research firm runs an entire study — market scan → hypotheses → literature → instrument design →
respondent panel → live fielding → interviews/testimony (audio/video) → weighted tabulation →
modeling → client deliverables. Its differentiation is a **provenance trust layer**: every number,
chart, and quote in any output is bound to a re-runnable Evidence record; unbacked claims are
technically impossible to ship. Autonomous "AI data-science" tools are documented to hallucinate
metrics and leak data; single-slice incumbents (survey tools, qual tools, tab tools) don't talk to
each other. Laboratree fuses the slices on one trust layer and sells **verifiable research**.

## 2. Business context & problem
Research firms (market research, academic, policy/M&E, UX, consulting) run fragmented stacks:
Qualtrics for surveys, Excel/Q for tabs, NVivo/Dovetail for qual, PowerPoint by hand, spreadsheets
as a "CRM." Consequences: swivel-chair cost, no cross-slice provenance, quality failures surface at
the client meeting, and juniors spend days on mechanical work (crosstabs, transcription, coding).
Meanwhile clients increasingly demand AI-speed turnarounds AND auditability. The gap: **no product
does the whole lifecycle, and no product can prove its outputs.**

## 3. Business objectives & success metrics
| # | Objective | Metric / target (first 12 months post-GA) |
|---|---|---|
| O1 | Prove end-to-end value | 3 paying research firms running full studies in-platform |
| O2 | Cost discipline | Variable COGS ≤ $30/study; fixed infra ≤ $50/mo at MVP |
| O3 | Trust as brand | 100% of delivered claims Evidence-backed; trust score on every deliverable |
| O4 | Speed | Brief → fielded survey ≤ 2 days; field close → client-ready tabs ≤ 1 hour |
| O5 | Qual efficiency | Interview → coded transcript ≤ 24 h incl. human review |
| O6 | Compounding assets | Twin calibration score improves study-over-study for a returning client |

## 4. Market opportunity & competitive landscape
Every incumbent owns one slice; none has provenance; none fuses slices:
| Slice | Incumbents | What they lack |
|---|---|---|
| Survey platforms | Qualtrics, Forsta/Confirmit, Alchemer, SurveyMonkey | no qual, no tabs-grade stats, no provenance, no agents |
| Qual analysis | Dovetail, Condens, NVivo, Atlas.ti, Marvin | no quant, no fielding, AI summaries unverifiable |
| Tabulation | Displayr, Q, SPSS, MarketSight | no collection, no qual, manual pipelines |
| Literature/AI research | Elicit, Consensus, SciSpace | no primary research at all |
| Synthetic respondents | SyntheticUsers, Fairgen | no real fielding → no calibration loop |
| Market intel | CB Insights, Crunchbase, AlphaSense | analyst-oriented feeds, no study workflow, uncited AI summaries |
| M&E / development data | KoboToolbox, SurveyCTO, TolaData, ActivityInfo, DHIS2 | collection OR indicator-tracking only; no qual, no impact estimation, no provenance, humans re-compute every wave |
| Strategy / business-model tools | Strategyzer, Miro/canvas templates, bespoke consulting decks | opinion canvases with zero evidence linkage; no field research, no WTP studies, no assumption tracking |
| Impact measurement (IMM) | Sopact, UpMetrics, B-Analytics | metric dashboards fed by hand; no primary research engine, no provenance, no pilots |
| Content/newsletter ops | Mailchimp/Beehiiv + manual scanning + generic AI writers | zero linkage to the firm's research; curation is manual; AI drafts hallucinate uncited stats |
| Experimentation / RCTs | Optimizely, Statsig, Eppo (digital A/B only); SurveyCTO+Stata (manual field stacks); AgentSociety/GPLab (research prototypes) | no product runs field policy RCTs end-to-end; digital tools can't do offline fieldwork; simulators ship without validation discipline |
**Positioning:** "The research firm's operating system — every claim provable." Wedge = small/mid
MR firms drowning in tool costs; expand via the 8 segments (§5). **Second wedge:** M&E/impact-
evaluation firms — fragmented Kobo+Excel+NVivo+Word stacks, donor pressure for auditability, and
the Impact Lab cuts their human effort ~60% (Roadmap 2.5).

## 5. Target customers
Anchor: **small/mid market-research & insights firms (5–50 staff)** — highest tool fragmentation,
price-sensitive, deliverable-driven; one platform replaces 4–6 subscriptions.
Second wedge (own vertical, Phase 17): **MLE firms for grant-funded programs** (donors, development
organizations) — MEL plans, grantee monitoring portals, DQAs, learning agendas, multi-wave
evaluations, offline fieldwork, donor auditability; the Impact & MLE Lab cuts their human effort
~60%. Third wedge (own vertical, Phase 18): **inclusive-business / business-model advisory firms**
(impact enterprises + investors) — evidence-linked business model design, WTP pricing studies,
unit economics, pilots, IRIS+/SDG impact measurement, diligence packs. **Archetype validated
against a real prospect** (an 18-year, 120-project, 18-country inclusive-business + MLE firm):
its entire public portfolio — 22 projects plus a blog/publication/newsletter operation — maps to
platform workflows (Roadmap 2.6), which is the sales narrative for this segment. Adjacent
(config, not code): academic labs (pre-registration + reproducibility), UX research teams,
data-science consultancies, competitive-intel/strategy consultancies, light clinical/health
research. Buyer = firm principal/research director; users = analysts, qual
researchers, field managers; external stakeholders = the firm's clients (verification links,
dashboards).

## 6. Business scope
**In scope (this horizon):** the 16 Labs (incl. new Field, Panel CRM, Qual Studio, Tabulation,
Deliverables, Market Intel, **Impact & MLE**, **Strategy**, **Knowledge & Content Studio**,
**Trials/RCT**), 16 unique powers U1–U16, the **agentic runtime** (deep agents, watchers, Org
Brain memory, Study Navigator, autonomy dial), synthetic-respondent engine, enumerator/offline
collection, grantee portal, advisory playbooks, QA framework + security threat-model hardening,
multi-tenant SaaS on cost-minimal infra, staged launch (alpha → design-partner beta → GA).
**Out of scope (this horizon):** billing/subscription automation, plugin marketplace, native mobile
apps (offline = PWA, not native), on-prem, full clinical GxP compliance, white-label multi-brand,
live CATI telephony.

## 7. Business requirements
| BR | Requirement | Labs / powers |
|---|---|---|
| BR-01 | A firm can execute a complete study (design→field→analyze→deliver) without leaving the platform | all Labs |
| BR-02 | Any delivered number/quote is independently verifiable by the end client to its source (run/code/data/timestamp) | U1, Evidence |
| BR-03 | Field real surveys to real respondents with industry-grade quality control (fraud/speeders/dupes/quotas) | Field Lab, U2 |
| BR-04 | Maintain a consented respondent panel: recruit, consent, invite, remind, incentivize; GDPR floor (export/delete, pseudonymous analysis) | Panel CRM |
| BR-05 | Capture audio/video testimony and produce defensible qual findings (transcripts, themes, verbatim quotes with timestamps) | Qual Studio, U7 |
| BR-06 | Produce MR-standard quantitative deliverables: weighted crosstabs with significance testing, survey metrics, drivers, segments | Tabulation |
| BR-07 | Export client-grade branded deliverables (PPT/PDF) and live dashboards | Deliverables, U1, U9 |
| BR-08 | De-risk instrument spend via realistic synthetic dry-runs with persona injection, calibrated against real waves | Synth engine, U3 |
| BR-09 | Deliver market assessments & competitor analyses where every figure is cited to a snapshotted source | Market Intel, U10 |
| BR-10 | Honesty is enforced: synthetic data, exploratory analyses, and mid-field changes are always labeled/versioned | U2, U6, honesty rules |
| BR-11 | Multi-tenant with role-based access; org isolation provable by test | platform |
| BR-12 | Serve ≥3 distinct firm types via configuration only | registry architecture |
| BR-13 | Manual/offline research workflows are instrumentable (capture forms, ops dashboards, ingest pipelines) | Field/Signal/Jobs |
| BR-14 | Per-study LLM spend visible and cappable; unit economics known per workflow | LLM observability |
| BR-15 | Each workflow's quality is measurable and regression-tested (golden sets, calibration, WER, inter-rater) | QA framework |
| BR-16 | New capability = a registry component with zero frontend code (extensibility economics) | plugin SDK |
| BR-17 | Support grant-funded-program MLE end-to-end: MEL plans + results frameworks with self-computing indicators, multi-wave panel studies with attrition tracking, offline enumerator collection with fraud analytics, **continuous partner monitoring via a grantee portal with review gates**, formal DQAs with spot-check verification, **self-answering learning agendas**, portfolio roll-ups for donors, rigorous impact estimation (DiD/PSM) and VfM/cost-effectiveness, multi-language instruments/testimony, donor-format (IPTT/OECD-DAC) reporting — cutting evaluator human effort ~60% | Impact & MLE Lab, U11, U13, U2/U8/U9 |
| BR-18 | Support inclusive-business / business-model advisory end-to-end: cited market & value-chain assessment, evidence-linked business model design with tracked assumptions, WTP/pricing studies on target (incl. BoP/offline) populations, unit-economics & scenario modeling with workbook export, assumption-driven pilots that update the model, IRIS+/IMP/SDG impact measurement, investor deal screens and glass-box diligence packs | Strategy Lab, U12, U10/U1 |
| BR-19 | External stakeholders participate under scoped roles: grantees/partners submit routine data through review gates; investors/donors receive verifiable (glass-box) outputs — without accessing the firm's internal workspace | grantee portal, U1, RBAC |
| BR-20 | Support the firm's knowledge & content operation: continuous sector monitoring with human curation, branded curated newsletters to a consented subscriber base with engagement analytics, data-driven blog posts with verifiable embedded figures and audio narration, and donor-co-branded publications/policy briefs assembled from project evidence — drafted by an agentic ghostwriter in the firm's own voice | Content Studio, Ghostwriter, U5/U10/U13 |
| BR-21 | The platform operates as an agentic system, not feature-AI: a firm's historical archive becomes queryable institutional memory that every agent consults (day-1 onboarding value); an orchestrator agent can plan and drive an entire engagement across Labs under human gates; autonomy is a per-stage dial the firm controls; all agent work is traced, budgeted, and evaluated | Org Brain U14, Study Navigator U15, AR track |
| BR-22 | Security is a stated posture: a maintained threat model covering prompt injection, malicious uploads, public-endpoint abuse, cross-tenant leakage, PII exposure, and agent runaway — each with a tested mitigation in CI; field-level encryption for respondent contact data; audit logging on external-facing surfaces | security 3.3, AR-1 guardrails |
| BR-23 | Support true randomized controlled trials of policies/programs end-to-end: reproducible randomization with balance checks, pre-registered analysis plans, offline field waves with compliance/attrition/spillover monitoring, rigorous causal estimation (ITT/LATE), CONSORT-grade reporting — and pre-trial synthetic simulation that is **validated** (retrodiction benchmark on published RCTs + post-trial calibration) and structurally barred from being presented as evidence | Trials Lab, U16, U3/U6 |

## 8. Revenue & cost model
**Cost structure (validated July 2026, open-weight-first stack):** fixed ~$33/mo MVP (Hetzner
single box) → ~$80–150 growth; variable **~$2–4 LLM** (DeepSeek-class hosted open models) + **$0
transcription/embeddings/TTS** (local Whisper/BGE-M3/Kokoro) + ~$0.2 storage per typical study
(500 survey + 12 interviews) — ≈ **$5/study COGS**, with the closed-model stack (~$20–30/study)
reserved as a per-role upgrade where evals justify it. **Pricing headroom:** MR firms charge
clients $15k–80k per study → >99% gross margin on AI COGS; price as **per-seat + per-study
bundle** (e.g. $99–299/seat/mo + study packs). Synthetic dry-runs and Market Intel are natural
premium add-ons. (Final pricing = open question OQ-1 in PRD.)

## 9. Risks & assumptions
| Risk | Mitigation |
|---|---|
| LLM output quality (hallucination, miscoding) | five-layer QA: provenance floor, adversarial audit, golden tests, judge+HITL gates, calibration (PRD §10) |
| Prompt injection / agent misuse via untrusted content | instruction/data separation; read-only tool allowlists for content-ingesting agents; state changes gated; injection test suite in CI (Roadmap 3.3) |
| Agent runaway (cost or unintended actions) | per-run budget/step caps, kill switch, spend alerts, autonomy dial defaults to copilot (AR-1) |
| Survey fraud / low-quality respondents | fingerprinting, quality flags, U8 consistency checks, Turnstile |
| GDPR/PII exposure | pseudonymous-by-design responses, append-only consent, export/delete, EU hosting option (Hetzner is EU) |
| Synthetic data misused as real | hard `synthetic:true` labeling; excluded from client deliverables by default (BR-10) |
| Single-box infra failure during a live field window | reliability engineering per Roadmap 3.4: idempotent/append-only collection (no data loss even through outages), offsite backups + restore drills, deploy freeze during field windows, SLO monitoring; growth-stage split |
| Incumbent response (Qualtrics adds AI) | moat = cross-slice provenance + calibration loops, which require our architecture, not a feature bolt-on |
**Assumptions:** open-weight model quality keeps pace for our roles (hedged: multi-provider via
OpenAI-compatible APIs + per-role closed-model upgrade path + AR-5 evals detect regressions);
hosted open-model API pricing bands hold; small-firm buyers accept
self-serve onboarding; respondent email deliverability achievable with proper domain setup.

## 10. Compliance & legal
GDPR baseline (consent ledger, right-to-access/erasure, pseudonymization, EU-region hosting
option); recording-consent notices for interview capture (jurisdiction-dependent, surfaced in
product); scraping limited to public pages honoring robots/ToS via the SSRF-safe fetcher; no
special-category data handling promised in this horizon (defers clinical depth).

## 11. KPIs & acceptance (business level)
Time-to-first-crosstab; % claims Evidence-backed (=100% enforced); twin calibration trend/client;
transcription WER on gold samples; flagged-response precision/recall; cost/study vs $30 cap;
studies/firm/quarter (retention proxy); verification-link clicks by end clients (trust engagement).
