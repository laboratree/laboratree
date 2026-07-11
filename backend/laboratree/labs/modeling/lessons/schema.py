"""Response shapes for guided model lessons — a cinematic, chapter/step "live show".

A ``Lesson`` wraps ONE embedded ``ModelTrace`` (the heavy numeric arrays fitted on the real
data). Chapters/steps are lightweight: final narration strings (live numbers already
interpolated server-side), KaTeX math blocks, table snapshots, and an ``AnimDirective`` that
POINTS into the trace — so payloads stay bounded no matter how granular the show is.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..explain.facts import ExamQA, ModelFacts
from ..viz.schema import ModelTrace


class Symbol(BaseModel):
    sym: str
    means: str


class MathBlock(BaseModel):
    name: str
    formula: str  # KaTeX-renderable source (frontend Tex.tsx)
    plain: str  # the formula in simple words
    symbols: list[Symbol] = []
    worked: str = ""  # worked example with the LIVE dataset's numbers, final string


class TableSnapshot(BaseModel):
    columns: list[str]
    rows: list[dict]
    target_col: str | None = None  # gold-highlighted outcome column
    highlight_cols: list[str] = []
    caption: str = ""


class AnimDirective(BaseModel):
    kind: str  # frontend StageRouter key: "data-table" | "legacy-train" | "split-trials" | …
    ref: dict = {}  # pointer into lesson.trace, e.g. {"round": 0, "node": "0.L", "row": 3}
    substeps: int = 1  # micro-scrub granularity inside this step (e.g. 24 split candidates)


class Step(BaseModel):
    id: str
    narration: str  # the caption read while this step plays
    duration_ms: int = 6000  # at 1x speed
    math: list[MathBlock] = []
    table: TableSnapshot | None = None
    anim: AnimDirective | None = None
    widget: str | None = None  # concept-widget key: "gini-balls" | "surprise-curve" | …
    quiz: list[ExamQA] = []  # self-check flip-cards (the "quiz" stage)


class Chapter(BaseModel):
    id: str
    title: str
    kicker: str = ""  # one-line subtitle under the chapter title
    steps: list[Step]


class Lesson(BaseModel):
    model: str  # resolved model key, e.g. "xgboost"
    family: str  # viz family that fitted the embedded trace (drives stage components)
    title: str
    target: str
    task: str
    chapters: list[Chapter]
    trace: ModelTrace  # ONE embedded trace; AnimDirectives point into it
    facts: ModelFacts | None = None
    param_spec: list[dict] | None = None  # mirrored from the trace for the ParamPanel
    params: dict | None = None
    total_ms: int = 0


class CatalogEntry(BaseModel):
    key: str  # lesson key, e.g. "xgboost"
    component_id: str  # registered component, e.g. "model.ml.xgboost"
    display_name: str
    group: str  # "Machine learning" | "Deep learning" | …
    family: str  # viz family it animates as today
    one_liner: str
    task: str  # "classification/regression" | "clustering" | "forecasting" | …
    has_deep_lesson: bool = False  # a hand-written script exists (vs the guided generic intro)
