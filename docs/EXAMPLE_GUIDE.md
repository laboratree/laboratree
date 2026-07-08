# Laboratree — The Complete Example Guide

One concrete, step-by-step walkthrough for **every Lab and every major functionality**. Two firms
appear throughout:
- **Meridian Insights** — a 12-person market-research firm. Client: *GreenCommute* ("why aren't
  commuters adopting e-scooters?").
- **Sambhav Advisory** — an 18-year inclusive-business strategy + MLE firm (120+ past projects).
  Clients: an NGO women's-livelihoods program (donor-funded), a solar cold-storage agtech
  enterprise + its impact investor, and a foundation's grant portfolio.

Actor labels: **[You]** the researcher · **[AI]** single-shot AI step · **[Agent]** autonomous
agent loop (always budget-capped, always traced) · **[Gate]** human approval checkpoint ·
**[Ext]** external person (respondent/grantee/client).

---

## 1. Ideation Lab — from vague brief to testable hypotheses
**Scenario:** Meridian receives GreenCommute's one-paragraph brief.
1. **[You]** Paste the brief into Ideation → "Run Co-Scientist".
2. **[Agent]** Generates 14 candidate hypotheses → self-critiques → pairwise Elo tournament →
   evolves the winners. Every claim in the reflection is visible in the tournament log.
3. **[You]** Open the top 5. Pick #1: *"Perceived safety, not price, is the primary adoption
   barrier for women commuters."*
4. **[Agent]** "Evidence Hunt" on the hypothesis: plans queries → searches web + OpenAlex →
   returns a cited brief (stance: supported, confidence 0.72, 9 sources) + **13 variables to
   test** (each with a suggested measure and direction) + research gaps.
5. **[You]** Chat in Brainstorm ("what would falsify this?") — answers stay grounded in the brief.
6. **[Agent]** "Data Hunt" finds 6 public datasets; "auto-experiment" sanity-checks the hypothesis
   on one (real model Runs, Evidence-locked) → verdict: plausible, effect size small in proxy data.
**You end up with:** a ranked, cited hypothesis set + a variable list that seeds the questionnaire
+ a proxy-data sanity check — in an afternoon.

## 2. Paper Lab — understand, then reproduce the literature
**Scenario:** Evidence Hunt cited a transport-economics paper (logit mode-choice model).
1. **[You]** Upload the PDF. **[AI]** classifies it (empirical) → generates the **Paper Card**:
   plain-language problem, variables (click a chip → definition + example value), models, math
   with worked examples, results.
2. **[You]** Hit "Explain simpler" on the elasticity section — it steps down a level each press.
3. **[You]** Chat: "what does the price coefficient −0.31 imply for a €10/month price cut?" —
   answer cites the paper's Section 4.2.
4. **[You]** Switch to **Experiment** tab: the paper's pipeline appears as a node graph (data →
   preprocess → logit → results). Auto-fetch can't find the dataset → **[Gate]** honest hand-off:
   exact source link + manual-upload instructions, or one-click **demo data** (synthetic, clearly
   caveated).
5. **[You]** Run the logit node on demo data → metrics beside the paper's reported numbers; fork
   the node to a gradient-boosting variant → leaderboard compares both, every number
   ProvenanceBadged.
**You end up with:** a paper your juniors actually understand, and its variable structure copied
into your study design.

## 3. Collection Lab — design the instrument right
**Scenario:** Meridian turns the 13 variables into a questionnaire.
1. **[You]** "Design questionnaire" from the Ideation variables. **[AI]** drafts 24 questions
   grouped in sections, with scales chosen per variable type.
2. **[AI]** Bias check flags Q7 ("Don't you agree e-scooters are dangerous?") as leading →
   suggests neutral rewording. **[You]** accept.
3. **[You]** Sample-size tool: 5% margin, 95% confidence → n=384; you plan 500. The
   **methodology advisor** confirms cross-sectional design and flags the cluster effect if you
   recruit via campuses (design effect ≈ 1.3 → aim 650 or accept wider CIs).
4. **[AI]** Synthetic pilot: 20 fake respondents traverse the survey to shake out logic dead-ends.
**You end up with:** a debiased, powered instrument ready for the twin dry-run.

## 4. Synthetic Respondents — dry-run before you spend (U3)
**Scenario:** before fielding 500 real people, simulate them.
1. **[You]** "Twin dry-run" → choose the frame: Berlin commuter margins (age × gender × income).
2. **[AI]** IPF builds 500 persona skeletons matching the margins → personality layer (OCEAN +
   bio-sketches, conditioned on Meridian's actual panel attributes) → cost preview: ~$1.80.
   **[You]** approve (hard cap set).
3. **[Agent]** Twins traverse the real instrument (skip logic enforced, scale answers via
   semantic-similarity elicitation, ensembled for variance).
4. Dry-run report: predicted 18% drop-off spike at Q12 (a 6×5 matrix grid); "range anxiety"
   item predicted near-ceiling (little variance — weak discriminator).
5. **[You]** Split Q12 into two short questions; swap the ceiling item.
6. *(Later, Phase 14)* After the real wave: **calibration score 0.83** — twins vs reality —
   stored as Evidence, so next study's twins are provably better.
**You end up with:** instrument fixes that would have cost you 90 real respondents to discover.

## 5. Field Lab — real fieldwork, honestly guarded
**Scenario:** fielding the survey to 500 Berlin commuters.
1. **[You]** Import the questionnaire → set quotas (city × gender × age = 500), screen-outs,
   German + English translations. Add a video-testimony question (Q19).
2. **[Gate]** Pre-publish: bias check re-runs; **pre-registration lock (U6)** freezes the
   hypothesis + planned analyses. Publish mints `laboratree.app/s/8f3ab…` + QR.
3. **[Ext]** Respondents answer on phones — one screen at a time, autosave (a closed browser
   resumes exactly), quota-full gets a polite close-out.
4. Every submit is guarded: device/IP fingerprint dupes, sub-4-minute speeders, straight-line
   patterns → **flagged, never silently deleted**.
5. **[Agent]** **Field Director (U2)**, day 2: "women-45+ quota at 40% of pace; Q17 losing 9% of
   respondents." Proposals in your inbox: targeted reminder batch + Q17 rewording. **[Gate]**
   approve both → the reword creates a **versioned changepoint**; later analyses auto-split.
6. Live dashboard: completes, quota bars, drop-off funnel, flag rate. Close at 517.
**You end up with:** a versioned `Dataset` (real responses, 22 visible exclusions with reasons)
plus 61 video clips flowing to Qual Studio.

## 6. Panel CRM — the respondent relationship (and its memory, U8)
**Scenario:** Meridian's 3,100-person opt-in panel powers recruitment.
1. **[You]** Import the panel CSV → dedupe + column mapping (auto-suggested). Each respondent:
   attributes, consent status, history.
2. **[You]** Segment: "urban commuters, consented, not contacted in 30 days" → 1,400 people.
3. **[You]** Compose invitations (€5 voucher) → throttled send via email; each carries a unique
   token — the response links to the invitation with **no PII in the response row**.
4. Reminders auto-schedule to non-starters; the Field Director's women-45+ top-up reuses this.
5. **Respondent memory (U8):** two respondents claim ages 15 years off their consented 2025
   profiles → consistency-flagged for review. Fatigue scores push over-surveyed members down the
   sampling order.
6. Incentives: 517 completes → "earned" → payout export. A respondent emails a GDPR delete
   request → **[You]** delete them; their pseudonymous answers survive, unlinkable.
**You end up with:** a compounding, consent-clean panel — not a spreadsheet.

## 7. Qual Studio — testimony to defensible findings
**Scenario:** 12 hour-long interviews (Zoom recordings) + 61 survey video clips.
1. **[You]** Drag the 12 mp4s in; the 61 clips are already there (from Q19). For a new interview
   you hit **Record** in the browser.
2. **[Agent]** Pipeline (background jobs, progress bars): ffmpeg extracts audio → chunks →
   transcribes (~13h audio ≈ $2.30) → speaker-turn pass → timestamped transcripts, searchable.
3. **[You]** Review: click a transcript line → the video seeks there; fix two mis-heard words
   (corrections recorded).
4. **[AI]** Proposes an 11-code codebook from all transcripts. **[Gate]** You merge two codes,
   rename one, approve. Nothing codes against an unapproved codebook.
5. **[Agent]** Thematic coding (segment-level, confidence + supporting text) + sentiment per
   speaker + **quote extraction** — every quote verbatim, timestamped, an Evidence record.
6. **[Agent]** **Copilot (U7)**: after interview 8, the saturation radar declares "traffic-safety
   fear" saturated (10/12 sources) and suggests probing "weather exposure" in the remaining four;
   per-interview guide-coverage maps show what you forgot to ask.
7. Synthesis: themes × sources matrix (click a cell → playable quotes), saturation curves, a
   cited narrative. Open-ended survey answers get coded by the same engine.
8. Search: "helmet fear" → every mention across 13 hours, ranked.
**You end up with:** an auditable qual analysis — every theme traceable to spoken words.

## 8. Signal Lab — messy client files → one clean workbook
**Scenario:** GreenCommute sends 9 files: sales xlsx, PDF usage reports, a scanned pricing memo.
1. **[You]** Drop all 9 into Signal. **[AI]** extracts (tables from PDFs, OCR on the scan),
   reconciles headers, infers types.
2. **[Gate]** Two ambiguous column mappings ("rev" vs "revenue_eur") ask you to confirm.
3. Output: one master .xlsx — segregated sheets, a Data Dictionary, text blocks — plus a
   versioned Dataset that joins the survey data downstream.
**You end up with:** analysis-ready data in minutes, with the mapping decisions on record.

## 9. Insight Lab — see the data (now with maps)
1. **[You]** Pick the fused dataset → EDA profile (distributions, missingness, correlations).
2. **[You]** Charts: histogram of intent by gender; scatter of income × willingness;
   correlation heatmap — all Vega, all Evidence-backed, all embeddable later.
3. **`chart.choropleth`**: intent-to-adopt by Berlin district on a map (the same component powers
   Sambhav's India district maps).
**You end up with:** publishable figures whose numbers can't drift from the data.

## 10. Modeling Lab — the model zoo under adversarial guard
1. **[You]** Predict `intends_to_switch` → pick logistic regression + gradient boosting (or let
   auto-experiment choose).
2. Each run: leakage sentinel first (catches an ID-like column you forgot to drop), then train/
   eval → metrics as Evidence, animated model visualizations with tunable hyperparameters.
3. **[Agent]** **Red-Team critic**: noise robustness, ablations, subgroup gaps (model
   underperforms for women-45+ → surfaced, not buried), leakage re-check → PASS/FAIL verdict.
**You end up with:** models you can defend, with their weaknesses documented.

## 11a. Trend Lab — what the time series is really doing
1. **[You]** Load GreenCommute's 24-month sales (from the Signal workbook) → `trend_decompose`:
   trend, seasonality (summer peak), residual — each series a chart with Evidence.
2. **[You]** `causal_impact` around last March's 15% price cut: counterfactual vs actual →
   estimated effect ≈ 0 (CI spans zero). Price wasn't the lever — independently corroborating the
   safety hypothesis from a THIRD data source (feeds the U4 triangulation matrix).
**You end up with:** honest time-series answers ("no effect" is reported as no effect).

## 11b. Decision Lab — from findings to a defensible recommendation
1. **[You]** Frame the client's choice: €10/month price cut vs free-helmet safety bundle.
2. **[You]** `expected_value`: conversion uplift scenarios use the driver analysis's coefficients
   (safety 2.1× price) + Trend's price-cut null result → bundle EV €412k vs cut EV €118k.
3. **[You]** `threshold_rule` encodes the go/no-go ("recommend bundle if EV ratio > 1.5") → the
   recommendation is an Evidence-locked, inspectable rule — not a slide assertion.
**You end up with:** a recommendation whose arithmetic the client can open.

## 12. Tabulation Lab — the numbers clients actually buy
1. **[You]** Weight setup: rake 517 responses to Berlin census margins (age × gender) →
   effective-N and design-effect reported as Evidence.
2. **[You]** Crosstabs: banner (Total | gender | age bands | city) × every question — weighted %,
   significance letters (ᴬᴮ), chi-square; client-ready .xlsx. Each table carries its **U6 label**
   (✅ pre-registered vs 🔍 exploratory) and pre/post-Q17-changepoint splits.
3. Metrics: NPS, top-2-box, means with CIs. Drivers: perceived safety #1 (2.1× price). Segments:
   k-means → 4 profiled, named segments.
4. **Triangulation (U4):** the matrix aligns crosstab findings × qual themes × literature —
   "safety" = **convergent** (3 modalities agree, click any cell for its evidence); "weather" =
   **divergent** (loud in interviews, flat in survey) → flagged as a follow-up, not smoothed over.
5. Twin calibration (U3) computes: 0.83.
**You end up with:** tabs an MR veteran trusts, with honesty labels no other tool prints.

## 13. Deliverables Studio — the glass-box deck
1. **[You]** New report → blocks: title, method appendix (auto-drafted from repro manifests: n,
   weights, field dates, exclusions, changepoints), crosstab tables, driver chart, six playable
   interview quotes, segment strategy, decision analysis.
2. Numbers only enter via the **Evidence picker** — typing "41%" by hand is rejected.
3. **[Agent]** **Claim Auditor (U5)**: rejects "price cuts *drive* adoption" (correlational
   evidence) → reworded; scopes "German consumers" → "Berlin commuters (18–65)". Overrides are
   possible — and recorded.
4. Export branded .pptx / .pdf — each slide carries a **verification QR (U1)**. Share a live
   dashboard link with GreenCommute during fieldwork (revocable).
5. **[Ext]** GreenCommute's CFO scans a QR mid-meeting → the crosstab's evidence chain: run, code
   hash, dataset version, weights — then plays the interview clip behind the headline quote.
6. **Living evidence (U9):** next quarter's wave lands → "re-run report" → every figure updates
   with a visible diff and as-of stamp.
**You end up with:** a deliverable that survives hostile questions.

## 14. Intelligence Lab — the trust seal
1. **[You]** Hit "Report card" on the project → the engine sweeps every Run: % with repro
   manifests, % of report claims Evidence-backed, leakage/red-team flags outstanding.
2. Output: a branded HTML report card with the **trust score** (e.g., 94/100) and an itemized
   ledger — the two deductions link straight to the un-reproduced Run and the unresolved subgroup
   flag, so "fix what's broken" is a click, not an audit.
3. The score + seal print on the deliverable's back page; the donor's procurement team can
   regenerate it themselves from the shared link.
**You end up with:** QA you can show the client — and a to-do list when it's imperfect.

## 15. Market Intel Lab — cited market truth (U10)
**Scenario:** Sambhav sizes India's solar cold-chain market for the agtech client.
1. **[Agent]** Market assessment: searches + scrapes → every captured page **snapshotted** (URL +
   text + timestamp) → TAM/SAM/SOM triangulated top-down AND bottom-up, method stated, confidence
   medium, freshest source stamped. An uncited figure is *rejected by the system*.
2. **[Agent]** Competitor scan: 14 players discovered → profiles (offerings, pricing, funding,
   news) → feature × competitor matrix, per-competitor SWOT, review-sentiment mining ("spoilage
   during power cuts" = #1 complaint across rivals).
3. **[Agent]** Workflow hunt: reconstructs how mango farmers currently sell (harvest → aggregator
   → mandi) → whitespace scoring finds "insurance-bundled cold storage at the aggregation point"
   unserved.
**You end up with:** a market chapter where every number has a receipt.

## 16. Impact & MLE Lab — the full grant-program lifecycle
**Scenario:** Sambhav runs MLE for the NGO women's-livelihoods program (3 districts, 1,200
households, 6 implementing partners, one donor).
1. **Design:** **[You]** feed the proposal + old logframe into Signal → **[AI]** Logframe Studio
   drafts ToC + 14 SMART indicators (numerator/denominator, disaggregation, targets, MoV) →
   **[Gate]** approve 12, edit 2. Each indicator is now a **computation recipe (U11)**. The MEL
   plan (collection calendar, methods, responsibilities) drafts itself and drives scheduling.
2. **Baseline:** Wave Manager scaffolds the baseline; 18 enumerators collect **offline** on
   phones in two languages (back-translation QA caught 3 bad items); GPS + timestamps captured;
   curbstoning analytics flag one enumerator (9 "interviews" from one courtyard) → review.
3. **Monitoring (quarterly):** **[Ext]** 6 partners submit output data via the **grantee
   portal**; validation → **[Gate]** reviewer approves → the **Living Logframe recomputes** →
   traffic-light IPTT on the donor dashboard; 2 late partners auto-chased.
4. **DQA:** `analyzer.dqa` scores each indicator on 5 dimensions; a spot-check plan samples 40
   records for field verification → one partner's "women trained" shows +18% reported-vs-verified
   variance → flagged with the mid-year redefinition annotated as a changepoint.
5. **Learning (U13):** the question *"does village-agent distribution reach the poorest
   quintile?"* accumulates evidence all year (waves, submissions, testimonies) → the annual
   pause-&-reflect opens **80% answered: no — 9 cited Evidence records**; `adaptive_recos` drafts
   three grounded course-corrections for management response.
6. **Midline:** panel re-contact (11% attrition, dashboard shows non-differential) → wave closes
   → all 14 indicators recompute vs baseline with significance; **DiD** on control districts:
   +23% income (parallel-trends sentinel passes); 40 testimonies transcribed/translated (originals
   linked), "reduced seasonal migration" emerges unplanned and triangulates convergent.
7. **VfM:** cost per outcome vs benchmark; 4E table. **Portfolio:** the donor sees this program
   rolled up beside 11 other grants (double-count guards).
8. **Report:** donor deck with click-to-verify IPTT, OECD-DAC findings, MSC stories with playable
   testimony. Analyst time on the midline: days, not weeks.

## 17. Strategy Lab — advisory that can prove itself
**Scenario:** Sambhav advises the cold-storage agtech + its prospective investor.
1. **Discovery:** value-chain analysis from 60 chain-actor interviews (offline-collected) → 31%
   post-harvest loss concentrated at aggregation points; **Neo4j ecosystem map** shows
   cooperatives as the gatekeeper channel.
2. **Canvas (U12):** **[AI]** drafts 3 business-model variants from the discovery evidence; the
   chosen canvas carries **23 assumptions**, each untested/testing/validated/invalidated and
   linked to Evidence. The riskiest: "farmers will pay ₹4/kg/day."
3. **Pricing:** Gabor-Granger WTP survey, 312 farmers, enumerator-collected → revenue-maximizing
   price **₹2.8** → assumption updates (invalidated at ₹4; validated at ₹2.8), canvas v2 logged
   in the pivot log.
4. **Financials:** unit economics recompute at ₹2.8 → contribution positive at 70% utilization;
   tornado chart says the model lives or dies on utilization; Monte Carlo puts P(break-even yr 2)
   at 0.64; branded .xlsx exports for the client's CFO.
5. **Pilot:** 2 test vs 2 control sites, 90 days, MDE-powered → utilization lands at 76% →
   assumption **validated**, financials refresh.
6. **IMM:** ToC via Logframe Studio; IRIS+ PI7885 (post-harvest loss) picked from the catalog;
   IMP 5-dimensions assessed; SDG 2.3 mapped; projections carry enforced "projected" labels.
7. **Invest:** the investor's deal screen scores the venture; the **diligence pack**
   auto-assembles — 14/23 assumptions validated (each click-to-verify), DiD'd pilot results,
   sensitivity analysis. Funded, eyes open.
### 17.1 The six advisory playbooks — one mini-guide each
**Landscape study** (point-of-care diagnostics, Uttar Pradesh): **[Agent]** Market Intel sizing
(snapshotted) + competitor scan → **[You]** field 25 KIIs with clinicians (Qual) → ecosystem graph
maps regulators/distributors/payers → gap analysis vs current care pathways → landscape report
with every figure cited. *2 weeks, not 8.*

**Concept & VP testing** (child-nutrition product): **[You]** define 3 concepts → `concept_test`
fields them monadic (n=150 each, mothers of under-5s, enumerator-assisted) → appeal/relevance/
uptake-intent/price-reaction scored with CIs → concept B wins on intent but fails affordability →
qual probes explain why → the consortium gets a go/kill matrix, Evidence-locked.

**GTM & channel pilot** (dairy agent network): **[You]** design the pilot (12 collection agents,
2 districts) → agents' daily activity ingests via routine forms → `channel_performance`: adoption
curves, retention, per-agent unit economics → agent archetype "dairy lead + input reseller"
outperforms 2.4× → expansion decision made on channel math, not anecdote.

**Behaviour-change campaign** (digital payments, 10k rural merchants): KAP baseline (n=800) →
campaign runs → monitoring dashboard tracks the adoption funnel (aware → tried → weekly-active)
per district → midline KAP shows knowledge +34pts but practice +6pts → `adaptive_recos` suggests
agent-assisted first-transaction push → endline validates. The whole arc is one project, three
waves, one funnel.

**Community needs assessment** (CSR, industrial township): household survey (n=600, offline) +
30 stakeholder interviews + secondary data (Signal) → `needs_priority` matrix (needs × severity ×
current coverage) → water quality and adolescent skilling rank 1–2 → 5–10-year roadmap deliverable
with per-initiative indicators wired for later M&E (U11-ready from day one).

**Program design → pilot → scale** (women's digital upskilling): Logframe Studio designs the
program ToC → 200-participant pilot as a wave study (pre/post skills + income) → DiD vs matched
comparison → `scale_readiness` diagnostic (ops, capital, replicability) → scale memo with
validated/open assumptions — the same U12 discipline applied to a program instead of a business.

## 18. Knowledge & Content Studio — the firm as publisher
**Scenario:** Sambhav's monthly "Sector Scan" + blog + donor publications.
1. **[Agent]** Sector Watch scans 40 configured sources (RSS + scrape + OpenAlex) all month →
   triages 300+ items to 63 with "why it matters" notes, all source-snapshotted.
2. **[You]** Curation queue: keep 17 articles + 5 publications, tweak two notes.
3. **[Agent]** **Ghostwriter** assembles the newsletter in Sambhav's learned voice (editor's note
   drafted from the month's picks) → **[Gate]** one-pass review → send to 2,400 consented
   subscribers → open/click analytics inform next month's triage.
4. Blog post: Ghostwriter proposes "What GST 2.0 means for rural MSMEs" from watch signals + Org
   Brain → researches → drafts with citations → **[You]** give inline feedback, it revises
   (tracked) → Claim Auditor catches one uncited stat → **TTS narration** attached → export
   HTML/Markdown to their CMS. The SHG-map-style post embeds a live district **choropleth** with
   a ProvenanceBadge.
5. Publication: the "8 lessons from 5 years of climate adaptation" report — archive ingested,
   lessons harvested with citations (U13 + Qual synthesis), donor co-branding, every claim
   glass-box.
**You end up with:** a week of content ops in an afternoon, with zero hallucinated figures.

## 19. Trials Lab — a policy RCT, end to end (with its validated twin)
**Scenario:** a state government asks Sambhav to test a subsidy policy: does a 40% e-rickshaw
battery-swap subsidy increase driver incomes? 80 wards; treatment = subsidy, control = none.
1. **[You]** Design the trial: unit = ward (cluster), stratify by district + baseline income;
   power calc (ICC from baseline data) → 40+40 wards detects a 12% income MDE. Primary/secondary
   outcomes + analysis plan **freeze into the pre-registration (U6)**.
2. **[Agent]** **Policy Twin dry-run (U16)** — persona-agents built from ward demographics
   simulate the policy: predicted take-up 46%, predicted effect +9% (below MDE!), flags "swap
   stations too sparse in 12 wards" as a take-up killer. The simulation carries its **retrodiction
   scorecard** (the simulator correctly retrodicted 7/9 published subsidy RCTs' directions).
   **[You]** redesign: add station-density stratification, extend the trial 3 months. The twin
   never becomes evidence — it just saved a doomed design.
3. **[You]** Randomize: seeded, blocked assignment → **balance dashboard** (SMD dot plot, all
   |SMD| < 0.1); assignment list is Evidence-locked (auditable, reproducible).
4. **[Ext]** Baseline + follow-up waves collect via enumerator/offline machinery; compliance
   tracked (assigned vs actually-subsidized); GPS spillover check flags 3 control wards adjacent
   to treatment swap stations.
5. Live **Trial Canvas**: arm swimlanes with enrollment counts, compliance funnels, attrition
   (differential test p=0.41, fine), auto-generated **CONSORT flow diagram**.
6. **[You]** Analyze at endline: ITT +11.2% income (ANCOVA-adjusted, CI [4.8, 17.6]); LATE for
   compliers +19%; heterogeneity: effect concentrated where station density > 1/km² (🔍
   exploratory-labeled); randomization inference confirms. **Forest plot** per outcome, prereg
   badges throughout.
7. Post-trial: predicted-vs-actual updates the twin's calibration (it under-predicted by 2pts —
   logged); the donor report ships with the CONSORT diagram, forest plots, and glass-box QRs.
**You end up with:** causal evidence a government can act on — and a simulator that gets
measurably better with every real trial.

---

## Cross-cutting functionality guides

### A. Study Navigator (U15) — the whole study, agent-driven
1. **[You]** New engagement → paste the brief → Navigator drafts the full plan: playbook
   (MR study), instruments, n=500 + 12 IDIs, timeline (6 weeks), LLM budget (~$25). **[Gate]**
   approve (autonomy: copilot).
2. **[Agent]** Executes as a durable graph: kicks off Ideation → questionnaire → twin dry-run →
   raises the publish gate → monitors fielding (Field Director reports to it) → schedules
   transcription as clips land → drafts tabs when the wave closes.
3. Daily standup digest: "Field 62% · women-45+ lagging (proposal pending) · 8/12 transcripts
   coded · IPTT draft refreshed." **[You]** pause, redirect, or take over anytime.

### B. Org Brain + Archive Import (U14) — 18 years, remembered
1. **[You]** (onboarding) Point the Archive Import Agent at the firm's project folders (120
   projects of reports, instruments, transcripts).
2. **[Agent]** Extracts → classifies (sector, geography, method) → embeds → links into the
   knowledge graph → learns the **brand-voice profile** from published work.
3. Forever after: any new engagement opens with an auto-brief — "3 precedent dairy-GTM projects;
   the 2019 agent-network instrument is reusable; your measured adoption benchmarks: 12–18%."
   Ask it anything: "what did we learn about women's SHG credit uptake?" → cited answer from
   your own history.

### C. Pipeline Canvas — compose Labs like Lego
**[You]** Drag: `connector.file → transform.mean_impute → model.ml.random_forest →
critic.red_team → report block` → run → each node a tracked Run, dataset flowing step to step,
Evidence throughout. Save as a reusable pipeline.

### D. Autonomy dial — you choose the gear
Per stage, per org: **manual** (AI assists only) · **copilot** (AI drafts, you approve —
default) · **autopilot** (AI executes, gates only at declared checkpoints; unlockable only after
the agent passes its eval harness). The Jharkhand evaluation runs copilot; the monthly newsletter
runs autopilot with one review gate.

### E. Client verification — what YOUR client experiences (U1)
A donor's auditor scans a QR on page 14 of the evaluation report → a public verification page:
the indicator's value, its computation recipe, the dataset version + hash, the wave, the repro
manifest — and for the quote beside it, the audio at 00:41:23. No login, no trust-me.

### F. Gates & approvals inbox — HITL as a first-class surface
Every pending decision (codebook approvals, Field Director proposals, grantee reviews, claim-audit
overrides, Navigator plans) lands in one inbox with context, diff, and one-click
approve/edit/reject; approvals are recorded with who/when/why. Comments + @mentions thread on any
gate or report block.

### G. Cost & observability — nothing invisible
LLM Activity shows every call (Lab, operation, tokens, latency, cost); `agent_runs` shows every
agent's plan, tool calls, and outcome; per-study budget caps warn before, not after. The twin
dry-run that cost $1.80 shows exactly where the $1.80 went.

### H. Extensibility — add a capability with zero UI code (Data Lab + registry)
Sambhav needs a winsorization transform the platform lacks. **[You]** run the
`laboratree-scaffold` skill → implement `transform.winsorize` (30 lines: ComponentSpec with
JSON-Schema params + `run(ctx)`) → restart. It now appears in `/api/components`, renders its own
form in every Lab picker, is callable on the Pipeline Canvas, **and is a tool every agent can
use** — no frontend work, no agent-prompt work. This is the plug-in economics the whole platform
runs on (existing `connector.file`, `transform.mean_impute`, `transform.drop_duplicates` were
built the same way).

### I. Team, roles & org setup
**[You]** (owner) register → your org exists → invite: two analysts (`analyst` — run Labs, no
member management), a field manager (`admin` — can resolve gates, manage panel), the client's PM
(`viewer` — dashboards and deliverables only, later the scoped client-portal role). Org
isolation is absolute and test-enforced: Meridian can never see Sambhav's rows, caches, or
embeddings. Every session is JWT + org-scoped (`X-Org-Id`).

### J. Sharing & export — evidence leaves the building safely
Paper share: **[You]** share a Paper Card with a collaborator → HMAC public read-only link,
revocable. Experiment evidence bundle: one click exports the full JSON bundle (runs, evidence,
manifests) — what the opened `evidence-bundle-4dba594e.json` in your Downloads is. Deliverables
share live dashboards + verification pages the same way; every public surface is tokened,
rate-limited, and revocable.

### K. Privacy flows — GDPR in practice
A panelist emails "delete my data." **[You]** Panel → respondent → **Export** (their full record:
attributes, consents, invitations, incentives — as JSON) → send it to them if requested →
**Delete** → identity rows purge; their survey answers remain as pseudonymous records that can
never be re-linked. ConsentRecords stay append-only for the audit trail of consent itself.

### Powers index — where each unique power's worked example lives
| Power | See section |
|---|---|
| U1 Glass-box deliverables | 13 (steps 4–5), E |
| U2 Field Director + changepoints | 5 (step 5) |
| U3 Twin dry-run + calibration | 4; 12 (step 5) |
| U4 Triangulation matrix | 12 (step 4); 11a (step 2) |
| U5 Claim Auditor | 13 (step 3); 18 (step 4) |
| U6 Pre-registration + honesty labels | 5 (step 2); 12 (step 2) |
| U7 Interview Copilot + saturation radar | 7 (step 6) |
| U8 Respondent memory | 6 (step 5) |
| U9 Living evidence re-runs | 13 (step 6) |
| U10 Evidence-cited market intel | 15 (all steps) |
| U11 Living Logframe | 16 (steps 1, 3, 6) |
| U12 Assumption Ledger | 17 (steps 2–5); 17.1 (program design) |
| U13 Self-answering learning agenda | 16 (step 5) |
| U14 Org Brain + archive import | B; 18 (step 4) |
| U15 Study Navigator | A |
| U16 Validated Policy Twin | 19 (steps 2, 7) |
