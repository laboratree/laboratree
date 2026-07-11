"""The family-default lesson — every model plays a guided show from day one.

Wraps the model's existing staged animation (Train/Test stages in the frontend) in narrated
chapters built from the curated family explainer: how-it-learns beats, the math with worked
examples, testing, hyperparameters, and a verdict. Deep hand-written scripts (xgboost.py, …)
replace this per model as they roll out.
"""

from __future__ import annotations

from ..explain.facts import ModelFacts
from ..viz.schema import ModelTrace
from ._steps import (
    DUR_SCENE,
    DUR_SHOW,
    AnimDirective,
    Chapter,
    chapter,
    data_chapter,
    explainer_for_chain,
    hyperparams_chapter,
    math_block,
    quiz_chapter,
    roadmap_chapter,
    step,
    testing_chapter,
    verdict_chapter,
)


def build(trace: ModelTrace, facts: ModelFacts | None, keys: list[str]) -> list[Chapter]:
    guide = explainer_for_chain(keys)
    title = str(guide.get("title", "This model"))
    one_liner = str(guide.get("one_liner", ""))

    # how-it-learns: one narrated beat per explainer bullet, all over the live training animation
    how = [str(h) for h in guide.get("how_it_works", [])] or [
        "The model fits a pattern on the training rows."
    ]
    train_steps = [
        step(
            f"learn-{i + 1}",
            text,
            duration_ms=DUR_SHOW if i == 0 else DUR_SCENE,
            anim=AnimDirective(kind="legacy-train"),
        )
        for i, text in enumerate(how)
    ]
    training = chapter("training", "How it learns", train_steps, kicker="Watch it train, live")

    chapters: list[Chapter] = [data_chapter(trace), training]

    math_entries = [math_block(m) for m in guide.get("math", [])]
    if math_entries:
        chapters.append(
            chapter(
                "the-math",
                "The math, gently",
                [
                    step(
                        f"math-{i + 1}",
                        f"{m.name}: {m.plain}",
                        duration_ms=DUR_SHOW,
                        math=[m],
                        anim=AnimDirective(kind="legacy-train"),
                    )
                    for i, m in enumerate(math_entries)
                ],
                kicker="Every symbol explained, with your numbers",
            )
        )

    chapters.append(testing_chapter(trace))
    if trace.param_spec:
        chapters.append(hyperparams_chapter(trace, facts))
    chapters.append(verdict_chapter(facts, guide, title))
    quiz = quiz_chapter(facts, facts.display_name if facts else title)
    if quiz:
        chapters.append(quiz)

    return [roadmap_chapter(title, chapters, one_liner), *chapters]
