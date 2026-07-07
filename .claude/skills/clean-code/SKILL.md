---
name: clean-code
description: The clean-code and clean-architecture standards for Laboratree. Consult and apply whenever writing, modifying, or refactoring any code in this repo (Python backend in apps/api, TypeScript/React frontend in apps/web, plugin-SDK). Covers naming, single-responsibility, DRY/KISS, typed data models over raw dicts, layer separation (routes/services/prompts/schemas/models/utils), error handling, and the pre-completion review checklist.
---

# Clean code — Laboratree standards

Apply these on every code change. They are the project's non-negotiable defaults; deviate only with a
stated reason. When editing existing code, **match the surrounding style** first, then leave it a little
cleaner than you found it (principle: refactor continuously).

## The principles, mapped to this repo

1. **Meaningful names.** Descriptive, intention-revealing names for vars, functions, files, folders.
   Component ids stay stable + dotted (`transform.dropna`, `model.ml.xgboost`). No `data2`, `tmp`, `mgr`.
2. **Single responsibility.** One reason to change per function/class/module. A router handles HTTP; a
   service holds business logic; a Component's `run` does the work; a prompt module holds the prompt.
3. **Small, focused functions.** If a function needs a comment to explain a *section*, that section is a
   function. Extract; don't scroll.
4. **DRY.** Shared logic goes to `core/` (backend) or `apps/web/lib` / a shared component (frontend).
   Never copy a helper between Labs — Labs share only through `core/` and `plugin-sdk`.
5. **KISS / YAGNI.** Simplest thing that works. No speculative abstraction, no config knob nobody asked
   for. Reuse mature libraries (sklearn/statsmodels/PyTorch/…); agents orchestrate, they don't reimplement.
6. **Readable code.** Consistent formatting (ruff for Python, the web toolchain for TS). Self-explanatory
   over clever.
7. **No magic values.** Named constants or `settings`. **Never hardcode model ids, ports, URLs, prompts,
   thresholds** — read model ids/keys from `core/settings`; keep tunables at the top of the module or in config.
8. **Shallow control flow.** Guard clauses + early returns over nested `if/else`. Validate-and-return-early
   at the top of the function.
9. **Separation of concerns — the layers.** Keep these in their own modules; do not mix them:
   - **routes** → `apps/api/laboratree/api/<lab>.py` (FastAPI routers: parse request, call a service, shape response — no business logic).
   - **services / business logic** → the Lab package `labs/<lab>/…` (or `core/` if cross-cutting).
   - **models / data shapes** → `models.py` (SQLAlchemy) and Pydantic/dataclass DTOs.
   - **schemas** → JSON-Schema in `ComponentSpec.params_schema`; Pydantic request/response models for APIs.
   - **prompts** → keep LLM prompt text in a dedicated module/constant, not inline in orchestration logic.
   - **utils** → `core/` shared helpers. **config** → `core/settings`.
   Frontend mirror: API calls in `apps/web/lib/api.ts`, UI in `components/`, pages in `app/`.
10. **Proper error handling.** Handle expected failures explicitly with actionable messages (see the
    `readiness_reason` pattern). Raise typed HTTP errors from routers. The **only** allowed silent
    `try/except` is fire-and-forget observability/telemetry that must never break a request — and it stays
    narrow and commented (`# fail-open: logging must never break the request`).
11. **Minimal comments.** Explain *why*, not *what*. Delete narration. A comment that restates the code is noise.
12. **Consistent structure.** Put a new file where its siblings live. Model families → `labs/modeling/<family>/`
    (`ml | dl_pytorch | econometrics | timeseries | anomaly`). Don't scatter related files.
13. **No raw dict plumbing.** Pass **typed models** (Pydantic / `@dataclass` / TS `interface`), not big
    `dict[str, Any]`. Dicts are allowed **only at defined boundaries**: `Component.run -> dict`, LLM
    JSON I/O, and DB JSON columns — parse those into a typed model at the boundary and pass the model onward.
14. **Strong typing.** Full type hints on every Python signature; `strict` TS, real `interface`s.
    Avoid `Any` — if a boundary forces it, narrow to a typed model immediately after.
15. **Remove dead code.** Delete unused imports, vars, functions, and commented-out blocks in files you touch.
    (ruff catches unused imports — keep it clean.)
16. **Explicit dependencies.** No hidden global state. Components reach the world only through `RunContext`
    (`blobs`, `evidence`, `llm`, `workdir`, `logger`). Inject clients; get the LLM via `get_llm()`, DB via
    the session dependency — don't reach for module-level singletons.
17. **Refactor continuously.** Improve names/shape of code you're already editing, without changing behavior.
18. **Maintainable & scalable.** Async everywhere in the API; heavy/long work goes to Celery (`core/jobs`),
    not the request path. Optimize for the next reader.
19. **Cohesive modules.** One clear responsibility per file/folder. When a file grows or takes on a second
    concern, split it (e.g. a `viz/` family tracer per model family, not one mega-file).
20. **Review before done.** See the checklist below — run it before calling any task complete.

## Provenance rule (project-specific, non-negotiable)
Every reported number must go through `ctx.emit(...)` so it is Evidence-locked. Never return, display, or
report a metric that wasn't actually computed by a real run. Charts/reports refuse claims without Evidence.

## Pre-completion review checklist
Before considering a change complete, verify:

- [ ] Names are clear; functions are small and single-purpose; control flow is shallow (guard clauses).
- [ ] No duplicated logic (extracted to `core/` or a shared component/util).
- [ ] No magic values; model ids/keys/ports/thresholds come from `settings`/constants.
- [ ] Data crossing module boundaries is a **typed model**, not a raw dict; signatures are fully typed; no stray `Any`.
- [ ] Layers are separated (route ↔ service ↔ model ↔ schema ↔ prompt ↔ util); the file lives with its siblings.
- [ ] Errors are handled explicitly with useful messages; no silent excepts except commented fail-open telemetry.
- [ ] Dead code, unused imports, and commented-out blocks removed.
- [ ] Every reported number flows through `ctx.emit` (provenance).
- [ ] Tests updated/added; `cd apps/api && uv run pytest` green; `uv run ruff check` clean.
- [ ] Frontend: `cd apps/web && npx tsc --noEmit` clean. **Never** `npm run build` while `npm run dev` is live.

If any box fails, refactor before finishing — don't ship it and note it as a TODO.
