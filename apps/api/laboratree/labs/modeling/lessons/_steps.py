"""Shared step/chapter builders + pacing and payload-budget constants for every lesson.

Deep per-model scripts compose these with their own hand-written chapters, so the common
chapters (roadmap / the data / testing / hyperparameters / verdict) are written once and stay
consistent — and the verdict/hyperparameter content is generated from the curated facts
registry rather than re-written 35 times.
"""

from __future__ import annotations

from typing import Any

from ..explain import EXPLAINERS, explainer_for
from ..explain.facts import ExamQA, ModelFacts
from ..viz.schema import ModelTrace
from .schema import AnimDirective, Chapter, MathBlock, Step, Symbol, TableSnapshot

# ---- pacing (ms at 1x speed) — deliberately slow: this is a documentary, not a loader -------
DUR_BEAT = 5_000  # a single idea / sentence
DUR_SCENE = 9_000  # a step with a diagram or table to absorb
DUR_SHOW = 14_000  # a step the viewer should watch unfold (training, trials, morphs)

# ---- payload budget (enforced by tests) ------------------------------------------------------
TABLE_ROWS = 12  # max rows in any TableSnapshot
FIT_MAX_ROWS = 400  # rows a lesson tracer may fit on
TRIAL_FEATURES = 3  # features shown in a split-trials board
TRIAL_THRESHOLDS = 8  # candidate thresholds per feature per node
MAX_DEPTH = 3
MAX_ROUNDS = 3
MAX_LESSON_BYTES = 300_000  # serialized lesson must stay under this


def step(
    id: str,
    narration: str,
    *,
    duration_ms: int = DUR_SCENE,
    math: list[MathBlock] | None = None,
    table: TableSnapshot | None = None,
    anim: AnimDirective | None = None,
    widget: str | None = None,
    quiz: list[ExamQA] | None = None,
) -> Step:
    return Step(
        id=id, narration=narration, duration_ms=duration_ms,
        math=math or [], table=table, anim=anim, widget=widget, quiz=quiz or [],
    )


def chapter(id: str, title: str, steps: list[Step], kicker: str = "") -> Chapter:
    return Chapter(id=id, title=title, kicker=kicker, steps=steps)


def explainer_for_chain(keys: list[str]) -> dict[str, Any]:
    """Finest family explainer along a resolve chain (e.g. ridge -> the 'regularized' guide)."""
    for k in keys:
        if k in EXPLAINERS:
            return explainer_for(k)
    return explainer_for(keys[-1] if keys else "trees")


def math_block(m: dict) -> MathBlock:
    """Convert an EXPLAINERS math entry ({name, formula, plain, symbols, worked_example})."""
    return MathBlock(
        name=str(m.get("name", "")),
        formula=str(m.get("formula", "")),
        plain=str(m.get("plain", "")),
        symbols=[Symbol(sym=s["sym"], means=s["means"]) for s in m.get("symbols", [])],
        worked=str(m.get("worked_example", m.get("worked", ""))),
    )


def data_table(trace: ModelTrace, caption: str = "") -> TableSnapshot | None:
    rows = (trace.table or [])[:TABLE_ROWS]
    if not rows:
        return None
    cols = [*trace.features, trace.target]
    return TableSnapshot(columns=cols, rows=rows, target_col=trace.target, caption=caption)


# ---- the shared chapters ----------------------------------------------------------------------


def roadmap_chapter(title: str, chapters: list[Chapter], one_liner: str) -> Chapter:
    """Prepend-able overview; call AFTER the other chapters are assembled."""
    stops = " → ".join(c.title for c in chapters)
    return chapter(
        "roadmap",
        "What you'll learn",
        [
            step(
                "roadmap",
                f"{one_liner} — In this guided show we'll go end to end: {stops}. "
                "Everything you'll see is computed on YOUR real data, not a toy example. "
                "Use the transport bar to pause, step, change speed, or jump chapters.",
                duration_ms=DUR_SCENE,
                anim=AnimDirective(kind="roadmap"),
            )
        ],
        kicker=title,
    )


def data_chapter(trace: ModelTrace) -> Chapter:
    n = len(trace.table or [])
    k = len(trace.features)
    if trace.task == "clustering" or trace.task == "anomaly":
        what = (
            f"Here is the real data: {k} feature columns"
            f"{f' (showing {min(n, TABLE_ROWS)} of the rows)' if n else ''}. There is NO answer "
            "column — the model must find structure on its own."
        )
    else:
        what = (
            f"Here is the real data: {k} independent variables (the inputs) and one outcome "
            f"column, {trace.target}, highlighted in gold — that's what the model must learn to "
            f"predict. This is a {trace.task} problem"
            + (
                f" with classes {', '.join(trace.labels)}."
                if trace.labels
                else ": the outcome is a number."
            )
        )
    return chapter(
        "the-data",
        "The data",
        [
            step(
                "data-reveal",
                what,
                duration_ms=DUR_SCENE,
                table=data_table(trace),
                anim=AnimDirective(kind="data-table", substeps=min(n, TABLE_ROWS) or 1),
            )
        ],
        kicker="Real rows from your dataset",
    )


def testing_chapter(trace: ModelTrace) -> Chapter:
    n = len(trace.test_rows or [])
    return chapter(
        "testing",
        "Testing",
        [
            step(
                "holdout",
                f"The model never saw these {n} held-out rows during training — this is the honest "
                "exam. Watch each prediction form, then click any row to replay exactly how the "
                "model produced it.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="legacy-test", substeps=max(n, 1)),
            )
        ],
        kicker="Held-out rows the model never saw",
    )


def hyperparams_chapter(trace: ModelTrace, facts: ModelFacts | None) -> Chapter:
    doc = {h.name: h for h in (facts.hyperparameters if facts else [])}
    lines: list[str] = []
    for s in trace.param_spec or []:
        h = doc.get(str(s.get("key", "")))
        detail = f"{h.plain} {h.effect}" if h else str(s.get("help", "")).strip()
        if detail:
            lines.append(f"{s.get('label', s.get('key'))}: {detail}")
    narration = (
        "Every knob this model exposes, in plain words — open the hyperparameter panel and drag "
        "any of them: the whole lesson re-fits on the real data so you can SEE the effect. "
        + " · ".join(lines[:4])
    )
    return chapter(
        "hyperparameters",
        "Hyperparameters",
        [step("knobs", narration, duration_ms=DUR_SCENE, anim=AnimDirective(kind="hyperparams"))],
        kicker="The knobs, what they mean, and their effect",
    )


def quiz_chapter(facts: ModelFacts | None, model_name: str) -> Chapter | None:
    """Recap + self-check flip-cards. Hand-written exam questions come first; the rest are
    synthesised from the facts (alternatives, weaknesses, knobs, use-cases) so EVERY model
    gets a drill even before bespoke questions are written."""
    if facts is None:
        return None
    qa: list[ExamQA] = list(facts.exam_questions)
    for alt in facts.alternatives[:2]:
        qa.append(ExamQA(
            q=f"When would you prefer {alt.model} over {model_name}?",
            a=f"When {alt.prefer_when}.",
        ))
    weak = [*facts.cons, *facts.limitations]
    if weak:
        qa.append(ExamQA(
            q=f"Name the main weaknesses of {model_name}.",
            a=" · ".join(weak[:3]),
        ))
    for hp in facts.hyperparameters[:2]:
        qa.append(ExamQA(
            q=f"What does {hp.name} control, and what happens when you change it?",
            a=f"{hp.plain} {hp.effect}",
        ))
    if facts.use_when:
        qa.append(ExamQA(q=f"When is {model_name} the right choice?", a=" ".join(facts.use_when)))
    if not qa:
        return None
    recap = (
        f"The one-breath recap: {facts.one_liner} " if facts.one_liner else ""
    ) + (
        f"Strengths to remember: {facts.pros[0]}." if facts.pros else ""
    )
    return chapter(
        "self-check",
        "Recap & self-check",
        [
            step(
                "quiz",
                recap + " Now test yourself before the real exam — click each card to think "
                "first, then reveal the answer. Replay any chapter you hesitate on.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="quiz", substeps=len(qa)),
                quiz=qa,
            )
        ],
        kicker="Could you teach it to someone else?",
    )


def verdict_chapter(
    facts: ModelFacts | None, explainer: dict[str, Any], model_name: str
) -> Chapter:
    """Pros / cons / limitations / when-to-use-over-alternatives. Facts first, explainer fallback."""
    if facts:
        pros = facts.pros
        cons = facts.cons + facts.limitations
        use = " ".join(facts.use_when)
        alts = [f"prefer {a.model} when {a.prefer_when}" for a in facts.alternatives]
    else:
        pros = [str(explainer.get("when_to_use", ""))]
        cons = [str(w) for w in explainer.get("watch_out_for", [])]
        use = str(explainer.get("when_to_use", ""))
        alts = []
    parts = [f"Where {model_name} shines: {' '.join(p for p in pros if p)}"]
    if cons:
        parts.append(f"Watch out for: {' '.join(cons)}")
    if alts:
        parts.append("Choosing between models — " + "; ".join(alts) + ".")
    elif use:
        parts.append(f"Reach for it when: {use}")
    if facts and facts.applications:
        parts.append(f"In the wild: {facts.applications[0]}")
    return chapter(
        "verdict",
        "Verdict: when to use it",
        [
            step(
                "verdict",
                " ".join(parts),
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="verdict"),
            )
        ],
        kicker="Pros, cons, limitations, and the alternatives",
    )
