"""Guided model lessons — one pluggable, curated "live show" script per model.

Sits on top of the viz tracers: ``build_lesson`` fits the model's trace on the REAL data
(one fetch, all playback data precomputed), then a per-model script turns it into narrated
chapters/steps with the live numbers interpolated. Models without a hand-written script get
the family-default lesson (``generic.py``) so every registered model plays from day one.

Plug IN a deep lesson: add ``<model>.py`` with ``@register_lesson("<model>")`` on a
``(trace, facts) -> list[Chapter]`` function — discovery is automatic. Plug OUT: delete it
(requests fall back to the generic lesson).
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable

from ..explain.facts import ModelFacts, facts_for
from ..viz import build_trace
from ..viz import families as viz_families
from ..viz.schema import ModelTrace
from . import generic
from .catalog import CATALOG
from .resolve import lesson_keys
from .schema import CatalogEntry, Chapter, Lesson

LessonScript = Callable[[ModelTrace, ModelFacts | None], list[Chapter]]

_LESSONS: dict[str, LessonScript] = {}
_DISCOVERED = False
_HELPER_MODULES = ("schema", "resolve", "catalog", "generic")


def register_lesson(key: str) -> Callable[[LessonScript], LessonScript]:
    def deco(fn: LessonScript) -> LessonScript:
        _LESSONS[key] = fn
        return fn

    return deco


def _discover() -> None:
    """Import every sibling module once so their @register_lesson decorators run."""
    global _DISCOVERED
    if _DISCOVERED:
        return
    for m in pkgutil.iter_modules(__path__):
        if not m.name.startswith("_") and m.name not in _HELPER_MODULES:
            importlib.import_module(f"{__name__}.{m.name}")
    _DISCOVERED = True


def build_lesson(data: bytes, target: str, model: str, params: dict | None = None) -> Lesson:
    """Sync (run via asyncio.to_thread): fit the trace on the real CSV bytes, then narrate it.

    ``model`` is free text (a paper's model name, a component id, or a lesson key) — it resolves
    through the same fallback chain the frontend uses, so anything plays.
    """
    _discover()
    keys = lesson_keys(model)
    tracer_family = next((k for k in keys if k in viz_families()), keys[-1])
    entry = next((e for e in CATALOG if e.key in keys), None)
    # a model's declared task overrides data-inference so e.g. Linear Regression on a binary
    # target stays regression (a linear probability model), not silently logistic.
    hint: dict = {"_model": keys[0]}
    if entry:
        t = entry.task.lower()
        if t == "classification":
            hint["_task"] = "classification"
        elif t.startswith("regression"):
            hint["_task"] = "regression"
    trace = build_trace(data, target, tracer_family, {**(params or {}), **hint})

    facts = facts_for(keys)
    script = next((_LESSONS[k] for k in keys if k in _LESSONS), None)
    chapters = script(trace, facts) if script else generic.build(trace, facts, keys)

    title = entry.display_name if entry else model.replace("_", " ").title()
    return Lesson(
        model=keys[0],
        family=trace.family,
        title=title,
        target=trace.target,
        task=trace.task,
        chapters=chapters,
        trace=trace,
        facts=facts,
        param_spec=trace.param_spec,
        params=trace.params,
        total_ms=sum(s.duration_ms for c in chapters for s in c.steps),
    )


def catalog_entries() -> list[CatalogEntry]:
    """The Learning Lab catalog with ``has_deep_lesson`` resolved against the live registry —
    a model counts as deep if ANY key on its resolve chain has a hand-written script."""
    _discover()
    return [
        e.model_copy(
            update={"has_deep_lesson": any(k in _LESSONS for k in lesson_keys(e.component_id))}
        )
        for e in CATALOG
    ]


__all__ = [
    "CatalogEntry",
    "Lesson",
    "build_lesson",
    "catalog_entries",
    "lesson_keys",
    "register_lesson",
]
