# Laboratree — The Complete Frontend Guide

How every Lab and functionality looks, navigates, and behaves in the web app. Covers the design
system, the navigation map, per-Lab screen specs (all 16 Labs), cross-cutting surfaces, public/
external pages, and engineering conventions. Existing screens (Phases 1–9) are marked ✅; planned
screens carry their phase.

## 1. Design system (light forest)

- **Tokens** (`tailwind.config.ts` ✅): bg `#FBFDF9` · forest `#14342A` (headings, topbar, primary
  text on light) · leaf `#6DB33F` (CTAs, accents, active states) · sprout `#A8D08D` (borders,
  soft fills) · ink `#1E2A22` (body). Status: amber = running/pending, green = done/validated,
  red = failed/invalidated, gray = idle/untested.
- **Type**: serif display (Lora) for page/section headings and the wordmark; Inter for UI/body.
  Numbers in tables use tabular-nums.
- **Density**: generous whitespace, rounded-xl cards, soft shadows; data surfaces (tables,
  transcripts) tighten to compact rows.
- **Brand**: flask BrandMark + Labora/tree wordmark ✅; logo + "Grow · Innovate · Impact" on every
  export and public page footer.
- **Shared components** (`apps/web/components/`): `AppShell` (topbar: brand, project switcher,
  gates-inbox bell, org/user menu) ✅ · `FileDropzone` ✅ · `DynamicForm` (renders any component's
  JSON-Schema params — the zero-UI-code workhorse) ✅ · `VegaChart` ✅ · `ProvenanceBadge`
  (evidence popover: run, code hash, dataset version) ✅ · `ConfirmDialog` ✅ · React Flow canvases
  (`ExperimentCanvas` ✅, `PipelineLab` ✅) · `GateCard` (approve/edit/reject with context diff)
  ✅→extended · `StatusChip` · `EvidencePicker` (P15) · `AgentTimeline` (AR-1) · `AudioPlayer` +
  `TranscriptView` (P12) · `CanvasBoard` (P18) · `CurationQueue` (P19).

## 2. Navigation map

```
/login, /register ✅
/  (projects dashboard) ✅
/team ✅                          /settings (org, autonomy dial, sources)  P10+
/projects/[id] ✅ — the workspace. Lab tabs (role-gated, org-configurable):
   Ideation · Paper · Collection · Field(P10) · Panel(P11) · Qual(P12) · Signal ·
   Insight · Modeling(✅ via Paper/Experiment + datasets) · Trend · Decision ·
   Tabulate(P14) · Deliver(P15) · Market(P16) · Impact(P17) · Strategy(P18) · Content(P19) ·
   Trials(P20)
   + right-rail: Navigator panel (AR-4) · Gates inbox ✅→P15 · LLM/Agent activity ✅→AR-1
PUBLIC (no login, tokened, rate-limited):
   /s/[token]          survey runtime (P10)          /join/[token]   panel sign-up (P11)
   /verify/[token]     evidence-chain page (P15)     /dash/[token]   live dashboard (P15)
   /share/paper/[t] ✅  paper card share              /post/[slug]    public post page (P19)
EXTERNAL ROLES:  /portal (grantee submissions, P17b) · client-viewer sees Deliver+dashboards only
```

Tab overflow: beyond 8 tabs the workspace collapses to a grouped switcher (Research · Collect ·
Analyze · Deliver · Verticals) — same components, two-level nav.

## 3. Per-Lab screen guide

### Ideation ✅ (`IdeationLab.tsx`)
Left: hypothesis list (Elo-ranked cards, score chips). Right: detail pane with tabs — Evidence
brief (stance/confidence banner, [n]-cited findings, variables-to-test table), Brainstorm chat,
Data Hunt results (download-flagged rows, "push to Paper Lab" / "build dataset" buttons),
Auto-experiment (task/profile/plan/results/verdict accordion). Run states stream as status chips.

### Paper ✅ (`PapersLab.tsx`, `PaperCard.tsx`, `ExperimentCanvas.tsx`)
Paper list → detail with **Study | Experiment** tabs. Study: adaptive card (empirical: clickable
variable/model chips → popover with description + example; conceptual: segmented w/ analogy
callouts), SimplifyBlock per field, ChatPanel with citations. Experiment: React Flow walkthrough
(data→preprocess→model→result nodes), node click → detail/progress panel, run/fork controls,
compare-to-paper leaderboard, "Generate demo data" (caveat banner), animated model viz with
hyperparameter sliders.

### Collection ✅ (`CollectionLab.tsx`)
Four tool cards: questionnaire designer (variables in → draft out, per-question edit), bias check
(flagged questions highlighted with suggested rewrite diff), sample size (form + result), synthetic
pilot (table of fake respondents). P10 adds: "Send to Field" CTA + **Twin dry-run** panel (cost
preview → progress → predicted drop-off chart + weak-item list). P14 adds Methodology Advisor card.

### Field (P10) — `FieldLab.tsx`
Three views. **Builder**: section/question tree (drag to reorder), per-question editor (type,
options, validation, translations tabs), logic editor (visual if/then rows), quota grid, publish
panel (bias-check status, prereg lock summary, URL + QR). **Live dashboard**: big-number header
(completes/target), quota bars, drop-off funnel (per-question bars), quality-flag rate, response
feed, **Director inbox** (proposal cards → approve/reject; approved instrument edits show a
changepoint marker on all charts). **Responses**: table w/ flag filters, per-response detail,
export-as-Dataset button.

### Panel (P11) — `PanelLab.tsx`
**Respondents** table (attribute columns, consent badge, fatigue score, segment filter bar) ·
**Import wizard** (dropzone → column mapping w/ auto-suggest → dedupe report → confirm) ·
**Invitation composer** (survey + segment pickers → preview email → throttle/schedule → batch
progress) · **Respondent timeline** drawer (consents, invites, completes, incentives, GDPR
export/delete buttons) · **Panel health** cards (churn, response rate, fatigue histogram).

### Qual (P12–13) — `QualStudio.tsx`
**Library**: asset grid (thumbnail, duration, status chip: uploaded→processing→transcribed;
progress bars streamed via SSE), Record button (MediaRecorder modal), upload dropzone.
**Transcript view**: media player docked top (audio waveform or video), transcript below —
click line ⇄ seek; inline edit (correction highlights); speaker labels editable; search-in-
transcript. **Coding workspace** (P13): transcript center, code sidebar (approved codebook,
color-coded), text spans highlight on hover, click-to-code, confidence dots on AI codes, filter
by code; codebook **gate banner** until approved. **Synthesis**: themes × sources matrix (cell
click → quote drawer w/ play buttons), saturation curve chart, cited narrative panel. **Copilot**
rail (P13): guide coverage checklist per interview, suggested probes, saturation radar dial.

### Signal ✅ (`SignalLab.tsx`)
Dropzone → file list with extraction status → consolidate button → result card (Data Dictionary
preview table, sheet list, download master workbook). Ambiguous-mapping gate renders inline.

### Insight ✅ (`InsightLab.tsx`)
Dataset picker → EDA profile (stat cards + distribution grid) · chart builder (type picker +
DynamicForm params → VegaChart with ProvenanceBadge). P19 adds `chart.choropleth` (region-key
mapping helper + bundled India/world TopoJSON).

### Modeling ✅ (datasets + Experiment surfaces)
Model runs launch from Experiment canvas, Pipeline, or auto-experiment; results render as metric
cards + animated `StagedModelAnimation` (tunable hyperparameters, loss curves, split scans) +
Red-Team verdict card (per-check pass/fail rows) + leakage warnings inline.

### Trend ✅ / Decision ✅ (`TrendLab.tsx`, `DecisionLab.tsx`)
Trend: series picker → decomposition charts (trend/seasonal/residual) + causal-impact panel
(actual vs counterfactual band). Decision: rule/EV forms (DynamicForm) → outcome cards with the
arithmetic shown.

### Tabulate (P14) — `TabulationLab.tsx`
**Weights wizard** (margin targets grid → run → effective-N/design-effect cards) · **Crosstab
builder** (banner picker: drag variables to columns; stub = all questions or a selection) →
crosstab viewer: letters-notation table (sig cells tinted), weighted/unweighted toggle,
prereg/exploratory badge, changepoint split toggle, export .xlsx · **Metrics** cards (NPS gauge,
T2B bars, CIs) · **Drivers** (tornado of importances) · **Segments** (profile cards per cluster)
· **Triangulation matrix** (P14): findings × {survey, qual, literature} grid, verdict chips
(convergent/divergent/unexplored), cell click → tri-modal evidence drawer.

### Deliver (P15) — `DeliverablesStudio.tsx`
Notion-style **block editor**: slash-menu inserts (heading, text, chart, crosstab, quote,
stat callout, methodology appendix); numeric/quote blocks open the **EvidencePicker** (searchable
list of the project's Evidence with previews) — free-typed numbers rejected with a helper
message. **Audit panel**: Claim Auditor findings as inline annotations (red = blocked, amber =
annotated; override requires a reason). **Export bar**: .pptx / .pdf buttons (per-slide QR
preview), template picker (report/memo/publication). **Share manager**: live-dashboard tokens
(create/revoke, open count), verification-page links. **Re-run** button (U9): per-figure diff
view (old→new values, as-of stamps).

### Intelligence ✅ (report card)
Project-level "Report card" button → branded HTML view: trust-score dial, itemized deductions
(each links to the offending Run/claim), evidence-coverage stats.

### Market (P16) — `MarketIntelLab.tsx`
**Assessment**: TAM/SAM/SOM cards (method + confidence + freshness stamps; every figure's
citation chip opens the snapshot) · **Competitors**: table (offerings/pricing/positioning
columns) + feature-matrix heat grid + per-competitor SWOT cards + review-sentiment themes ·
**Workflow map**: flow diagram of the market's current process, whitespace list ranked with
JTBD scores · source-snapshot drawer everywhere.

### Impact (P17) — `ImpactLab.tsx`
Widest Lab; left nav within the tab: **Logframe** (tree: goal→outcomes→outputs→indicators;
indicator drawer = recipe, targets, disaggregations, MoV; approval state) · **MEL plan**
(calendar grid: indicator × period × method × responsible) · **Waves** (timeline: baseline/
midline/endline chips, attrition dashboard, re-contact list) · **Field ops** (enumerator table,
cluster map w/ GPS pins, curbstoning flags, sync-status per device) · **Monitoring** (portal
review queue: submission cards → validate/approve; traffic-light IPTT; late-partner chase log) ·
**DQA** (five-dimension score grid per indicator, spot-check planner, reported-vs-verified
variance chart) · **Learning** (question boards: evidence-for/against stacks with stance chips,
answer-so-far meter, AAR composer) · **Portfolio** (donor view: grant cards, aggregated
indicators, double-count warnings) · **VfM** (4E table, cost-per-outcome vs benchmark).

### Strategy (P18) — `StrategyLab.tsx`
**Canvas board**: 9-box Business Model Canvas; each box lists assumption chips
(gray untested / amber testing / green validated / red invalidated); chip click → evidence links
+ status history; canvas version switcher (pivot log). **Value chain**: margin-flow diagram
(actors as nodes, margins on edges). **Ecosystem**: force graph (Neo4j-backed, filter by
relation). **Pricing**: Van Westendorp intersection chart / Gabor-Granger demand + revenue
curves. **Financial workbench**: driver inputs (each with evidence link or "unvalidated" flag),
unit-economics cards, tornado chart, Monte Carlo fan, .xlsx export. **Pilots**: pilot cards
(assumptions under test, MDE, status) → results auto-flip assumption chips. **IMM**: IRIS+
picker (searchable catalog), 5-dimensions grid, SDG chips, projection cards ("projected"
watermark). **Invest**: deal-screen scorecard, DD-pack builder (section checklist → assemble),
scale-readiness diagnostic radar. **Playbook launcher**: six template cards that pre-wire the
above + other Labs into a guided checklist with progress.

### Trials (P20) — `TrialsLab.tsx`
**Design view**: arm builder (add/name arms, allocation ratios), stratification picker, power
calculator panel (ICC slider → MDE curve), SAP editor with prereg-freeze banner. **Twin panel**:
run-simulation card (cost preview), prediction cards (take-up, effect, risks) each watermarked
`SIMULATED`, retrodiction-scorecard drawer (per-domain hit-rates; locked-state if below
baseline). **Trial Canvas** (the headline surface): horizontal arm swimlanes — each lane shows
enrollment count, compliance funnel (assigned→reached→treated→retained), quality flags; center
spine = timeline with wave markers and interim-look gates. **Balance view**: SMD dot plot
(covariates on y, dots per arm-pair, threshold band). **CONSORT diagram**: auto-laid-out flow
(vertical boxes with counts + exclusion reasons), export as SVG/PNG. **Results**: per-outcome
forest plot (effect + CI, prereg badge, subgroup rows), twin prediction-vs-actual overlay,
randomization-inference toggle. All figures ProvenanceBadged and insertable into Deliverables.

### Content (P19) — `ContentStudio.tsx`
**Watch queue**: item cards (source, date, why-it-matters, tags, snapshot link) → keep/kill
keyboard triage; source-health sidebar. **Newsletter composer**: issue outline (sections by
theme), drag kept items in, Ghostwriter "draft issue" button → editable rich text, test-send,
schedule; analytics view (opens/clicks per issue). **Post editor**: block editor (same core as
Deliverables) + chart/map embeds, Ghostwriter side panel (topic → research → draft → inline
feedback loop, tracked revisions), Claim Auditor annotations, TTS preview player, export
HTML/Markdown. **Publications**: template picker, co-branding slots (logo uploads), lessons-
harvest wizard (pick archive scope → review cited lessons → assemble).

## 4. Cross-cutting surfaces

- **Gates inbox** (bell in topbar; full page at `/projects/[id]?gates`): one queue for ALL
  pending decisions (codebooks, Director proposals, grantee reviews, claim overrides, Navigator
  plans, mapping confirmations). Card = context summary + diff + approve/edit/reject; keyboard
  j/k + a/e/r. Comments + @mentions thread per card (P15).
- **Navigator panel** (AR-4; right rail): current plan as a checklist with live statuses, daily
  standup digest feed, pause/redirect controls, cost-used vs budget meter.
- **Org Brain search** (AR-3; topbar ⌘K): ask anything → cited answer from the firm's history;
  "precedent projects" cards on every new-engagement screen.
- **Agent activity** (AR-1; extends LLM Activity tab ✅): agent-run list → timeline drawer
  (plan → tool calls as Run links → outcome), budget bars, kill switch.
- **Autonomy dial** (`/settings`): per-stage manual/copilot/autopilot toggles; autopilot options
  disabled until AR-5 eval badge is green.
- **Notification center** (P15): in-app list + email digest preferences.
- **Trust surfaces**: ProvenanceBadge on every figure ✅; trust-score dial; public verification
  page (P15): evidence chain rendered as a vertical stepper (value → recipe/run → code hash →
  dataset version → manifest), quote pages embed the media player at the timestamp.

## 5. Public & external surfaces (each: tokened, rate-limited, branded footer)

- **Survey runtime `/s/[token]`** (P10): mobile-first, no AppShell; one question-group per
  screen; progress bar; big touch targets (48px+); autosave toast + resume banner; offline queue
  indicator (P17 PWA); media-record question = tap-to-record with preview/retake; quota-full and
  screen-out end screens are polite and branded; WCAG 2.1 AA (labels, contrast, keyboard).
- **Panel sign-up `/join/[token]`** (P11): short form + explicit consent checkboxes (scope text
  shown), double-opt-in email.
- **Grantee portal `/portal`** (P17b): partner login → "my program" only: submission forms
  (generated, with validation errors inline), submission history + review status, feedback
  thread.
- **Live dashboard `/dash/[token]`** (P15): headline metric cards + field-progress bars,
  auto-refresh, "last updated" stamp; revocation returns a friendly gone-page.
- **Verification `/verify/[token]`** (P15) and **post pages `/post/[slug]`** (P19): server-
  rendered, fast, no login; posts include interactive charts (vega embeds), audio player, and
  citation hover-cards.
- **Enumerator mode** (P17): installable PWA shell of the survey runtime + assignment list,
  offline banner, queued-submission counter, sync button with per-record results.

## 6. Engineering conventions (`apps/web`)

- **Stack ✅**: Next.js App Router + TypeScript + Tailwind; `lib/api.ts` typed client (token +
  `X-Org-Id`); `lib/auth.tsx` context + route guard; lazy-loaded Lab tabs (`next/dynamic`) —
  keep: every new Lab tab is a dynamically imported component.
- **State**: server data via the typed client + SWR-style hooks (add `useApi` wrapper with
  focus revalidation as surfaces multiply); client state stays local to each Lab component;
  no global store.
- **Streaming**: SSE for job/agent progress (`EventSource` hook `useJobProgress(jobId)`); no
  websockets needed this horizon.
- **Forms**: component params ALWAYS render via `DynamicForm` from the ComponentSpec JSON-Schema
  — never hand-build a component form (that's the zero-UI-code contract).
- **Charts**: vega-embed only (`VegaChart`), specs come from the API; canvases: @xyflow/react;
  maps: vega + bundled TopoJSON (no map-tile dependency).
- **Public pages**: separate route group with no AppShell import, minimal JS budget (the survey
  page targets < 150KB gz), server components where possible.
- **Offline (P17)**: service worker scoped to `/s/*` + enumerator shell; IndexedDB queue
  (survey answers append-only records + idempotency keys); background sync where available,
  manual sync button always.
- **i18n**: respondent-facing strings come from the survey definition (translations are data,
  not UI locale files); app UI stays English this horizon (BRD non-goal).
- **A11y**: public surfaces WCAG 2.1 AA (NFR-07); all interactive elements keyboard-reachable;
  charts get text summaries.
- **Testing**: `npx tsc --noEmit` gate (never `npm run build` beside a dev server ✅ house
  rule); Playwright smoke flows per public surface (submit survey offline→sync, scan
  verify page) from Phase 10 on.
