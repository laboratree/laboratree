# Pipeline tab revamp — design

**Date:** 2026-07-10
**Status:** Approved direction: phase-grouped canvas, "calm editorial" visual style.
**Scope:** `apps/web` Pipeline tab + lab deep-links only. No backend changes. Other tabs untouched.

## Problem

The Pipeline tab renders every stage as a default React Flow box (emoji + label) on a flat
4-column grid. Phases aren't grouped, nodes carry almost no information, the config sidebar is
cramped, and "Lab" stages only *tell* the user to visit a Lab tab — there is no actual link
(`PipelineLab` cannot switch the workspace tab). The 16-phase lifecycle the templates describe is
invisible in the UI.

## Goals

1. **Clear phases** — stages grouped into named phase lanes with live progress.
2. **Rich nodes** — each node reads as a proper phase card: number, kind, status, owning Lab.
3. **Closer look** — selecting a node opens a detail drawer with the full story and controls.
4. **Real lab integration** — "Open in \<Lab\> →" switches the workspace tab.
5. **Fascinating but calm** — "calm editorial" style: white cards, hairline borders, color only
   where it carries status; animation only while something is actually happening.
6. **Zero new dependencies** — CSS keyframes + existing stack (`@xyflow/react`, Tailwind).

## Non-goals

- Persisting flows or completion state to the backend (today's Pipeline tab is client-state only;
  that stays true).
- Editing edges / free-form graph topology (flows remain a linear sequence).
- Redesigning other tabs or the workspace shell.

## 1. Data model — `apps/web/lib/pipelineTemplates.ts`

```ts
export type FlowPhase = {
  key: string;      // "understand"
  title: string;    // "Understand"
  blurb: string;    // "problem → evidence → hypotheses"
};

export type FlowTemplate = {
  key: string; name: string; tagline: string;
  phases: FlowPhase[];          // NEW — ordered
  stages: FlowStage[];
};

export type FlowStage = {
  // existing fields unchanged, plus:
  phase: string;                // NEW — FlowPhase.key
};
```

- All three templates get phases. NGO policy: **Understand** (1–5), **Design** (6–8),
  **Field** (9), **Analyze** (10a–10d), **Decide** (11–13), **Impact & Monitor** (14–16).
  Research-firm and policy-firm flows get analogous 5–6 phase groupings.
- Stages whose `phase` doesn't match a template phase (e.g. stages the user adds on a blank
  canvas) render in a trailing **"Custom"** lane that exists implicitly.
- **Phase numbering** is derived, not stored: a stage's display number is its 1-based position in
  `stages` (the NGO flow keeps its lettered sub-steps by keeping distinct stages). The hardcoded
  `"1 · "`-style prefixes in NGO template labels are removed — the number chip renders it instead.

### Shared lab-tab registry — new `apps/web/lib/labTabs.ts`

The workspace tab list currently lives inline in `app/projects/[id]/page.tsx` (`TABS`), and
`FlowStage.labTab` refers to those keys as untyped strings. Extract:

```ts
export const LAB_TABS = [ { key: "ideation", label: "Ideation Lab" }, … ] as const;
export type LabTabKey = (typeof LAB_TABS)[number]["key"];
export const labTabLabel = (key: string): string => …;
```

`page.tsx` consumes `LAB_TABS`; `FlowStage.labTab` becomes `LabTabKey`. This makes the deep-link
contract typed end-to-end and removes the duplication.

## 2. Component architecture — new `apps/web/components/pipeline/`

The 341-line `components/PipelineLab.tsx` is split by responsibility; the old file is deleted and
the import in `page.tsx` updated.

| File | Responsibility |
|---|---|
| `PipelineLab.tsx` | Container: state, `Api.listComponents` / `Api.runPipeline` / `demoApi.seed`, template loading, CSV parsing. Run logic unchanged except lab/manual stages are no longer marked `skipped` (§6). |
| `StageNode.tsx` | Custom React Flow node (`type: "stage"`): the phase card. |
| `LaneNode.tsx` | Custom React Flow node (`type: "lane"`): phase-lane background + header (title, blurb, progress). |
| `StageDrawer.tsx` | The "closer look" panel. |
| `layout.ts` | Pure function `(stages, phases) → { nodes, edges }`: positions stage nodes inside lane nodes, chains edges in stage order. |
| `types.ts` | `StageState`, `StepStatus`, kind/status label + style maps, `PipelineLabProps`. |

- `nodeTypes` is defined once at module scope (React Flow re-render requirement).
- `PipelineLab` accepts `onOpenLab?: (tab: LabTabKey) => void`; `page.tsx` passes
  `(t) => setTab(t)`.

### Layout algorithm (`layout.ts`)

- Lanes stack **vertically**, one per phase (in template order, then "Custom" if needed).
- Stage nodes flow **left → right** inside their lane, wrapping to a new row after **5 nodes**.
- Lane nodes are parents (`parentId` + `extent: "parent"` on stage nodes) sized from their
  children; stage cards are ~200px wide.
- Edges follow the global stage order (the array order), including across lanes; edges get
  `animated: true` **only while a run is in flight**.
- Canvas container height ~560px, `fitView`, pan/zoom enabled, attribution hidden (as today).

## 3. Node card (`StageNode`)

Calm editorial: white card, `border-line` hairline, 12px radius, soft shadow.

- **Header row:** `PHASE <n>` label (small caps, muted; `n` derives from the stage's position/label)
  and a **kind badge**: `⚙ RUN` (leaf-tinted `#EAF4E2`/forest-green), `🧪 LAB` (blue-tinted
  `#EDF4FB`/`#2563EB`), `👤 MANUAL` (gray tint, dashed card border).
- **Title** (semibold forest) + **description** clamped to 2 lines (muted).
- **Footer:** status on the left — `○ idle` (muted) / `● running` (amber) / `✓ done` (green) /
  `✕ failed` (red); on the right — lab stages show `<Lab name> ↗`, runnable stages show
  `🔒 <n> evidence` after a successful run.
- **States:** selected = leaf ring + shadow; running = amber border, `#FFFBEB` wash, soft pulse
  keyframe; succeeded = green check (card stays white — status color lives in the footer);
  failed = red border + red status.

## 4. Phase lane (`LaneNode`)

White rounded container, hairline border. Header: serif small-caps phase **title**, muted
**blurb**, right-aligned **progress** (`2/4 done`). A lane's count includes: runnable stages with
`status === "succeeded"` plus lab/manual stages the user marked complete.

## 5. Closer look drawer (`StageDrawer`)

Replaces the config sidebar: a ~380px white panel with a 3px leaf left border, slides in
(CSS transition) when a node is selected.

- **Header:** `CLOSER LOOK · PHASE <n>` label, serif stage title, kind badge, live status pill.
- **Phase navigation:** `←`/`→` footer links naming the previous/next stage — walk the lifecycle
  node by node without touching the canvas.
- **All kinds:** editable label + description (as today), remove-stage action.
- **Lab stages:** lab card naming the owning Lab + **"Open in \<Lab\> →"** button →
  `onOpenLab(stage.labTab)`. Plus **"Mark stage complete"** checkbox.
- **Manual stages:** same mark-complete checkbox; description doubles as notes.
- **Component stages:** component `<select>` (options grouped by `kind`), params JSON textarea
  with **inline** validation error (replaces today's global error banner for this case), and after
  a run: status + evidence count, `ProvenanceBadge`, scrollable result preview (as today).

## 6. Run experience & progress model

- **Header strip:** white card — serif flow name, `<n> phases · <k> runnable` counts, a leaf
  progress bar, `▶ Run <k> steps` button, and the existing template pills / 🌱 demo-seed /
  Clear / CSV dropzone, restyled but functionally identical.
- **Progress** = (succeeded runnable stages + marked-complete lab/manual stages) / total stages.
  Client-side only, resets on template load — same lifetime as the rest of the tab's state.
- **Behavior change:** running the flow no longer marks lab/manual stages `skipped`; a run only
  touches component stages. Lab/manual completion is owned by the user via mark-complete.
- **Motion:** edges animate and running cards pulse only during a run; when results land,
  statuses settle (no idle animation). A legend row of the three kind chips replaces the current
  explanatory sentence.
- **`markedDone: boolean`** lives on `StageState` (separate from run `status`, so runs can never
  clobber human progress).

## 7. Error handling

- Pipeline-run failure: unchanged — running stages flip to `failed`, message shown in the header
  strip area.
- Invalid params JSON: inline at the field in the drawer, not saved (as today), field highlighted.
- Component list fetch failure: unchanged (empty list); component `<select>` shows a hint when
  empty.

## 8. Verification

1. `npm run lint` and `npx tsc --noEmit` in `apps/web` — clean.
2. Playwright smoke (webapp-testing skill): open a project → Pipeline tab → load "NGO policy
   research" → lanes + cards render → click a node → drawer opens → click "Open in Field Lab →"
   → workspace switches to the Field Lab tab → back to Pipeline → 🌱 demo seed → ▶ Run → statuses
   and progress update.
3. Existing behavior spot-checks: template pills, Clear, CSV dropzone, params editing, run with
   no runnable stages shows the existing error.
