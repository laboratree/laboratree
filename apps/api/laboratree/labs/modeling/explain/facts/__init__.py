"""Per-MODEL curated facts — pros/cons/limitations/when-to-use/alternatives/hyperparameters.

The family EXPLAINERS (``explain/__init__.py``) teach a whole family from zero; FACTS are the
model-specific verdict material: what THIS model is good/bad at and when to prefer a named
alternative. Every lesson's closing "verdict" chapter and hyperparameter chapter render from here.

Curated (not LLM-generated). Keys match ``lessons/resolve.py`` model keys (e.g. "xgboost",
"lstm", "dbscan"); ``facts_for`` walks the same fallback chain, so a model without its own entry
inherits its family's. Populated family-by-family as deep lessons roll out.
"""

from __future__ import annotations

from pydantic import BaseModel


class Alternative(BaseModel):
    model: str  # human name of the competing model, e.g. "Random forest"
    prefer_when: str  # one sentence: when the alternative is the better pick


class HyperparameterDoc(BaseModel):
    name: str  # param key as exposed in the component spec, e.g. "learning_rate"
    plain: str  # what it is, in simple words
    effect: str  # what turning it up/down does to the model
    typical_range: str = ""  # e.g. "0.01 – 0.3"


class ExamQA(BaseModel):
    q: str  # an exam/interview-style question
    a: str  # the model answer, in a few sentences


class ModelFacts(BaseModel):
    key: str  # lesson key, e.g. "xgboost"
    display_name: str
    family: str  # viz family the model animates as
    one_liner: str = ""
    pros: list[str] = []
    cons: list[str] = []
    limitations: list[str] = []
    use_when: list[str] = []
    alternatives: list[Alternative] = []
    hyperparameters: list[HyperparameterDoc] = []
    applications: list[str] = []  # "in the wild": business/economics case studies
    edge_cases: list[str] = []  # gotchas: missing values, imbalance, extrapolation…
    exam_questions: list[ExamQA] = []  # hand-written drill; the quiz also self-generates


# key -> facts; family modules (ml.py, dl.py, …) register into this as they are written.
FACTS: dict[str, ModelFacts] = {}


def register_facts(facts: ModelFacts) -> ModelFacts:
    FACTS[facts.key] = facts
    return facts


def facts_for(keys: list[str]) -> ModelFacts | None:
    """First facts entry along a resolve chain (model key first, then family keys)."""
    _load()
    for k in keys:
        if k in FACTS:
            return FACTS[k]
    return None


_LOADED = False


def _load() -> None:
    """Import the family modules once so their register_facts calls run (import at call time
    to avoid a circular import: the modules import from this package)."""
    global _LOADED
    if _LOADED:
        return
    from . import (  # noqa: F401
        anomaly,
        clustering,
        dl,
        econometrics,
        econometrics2,
        ml,
        timeseries,
    )
    from .drill import enrich

    enrich()  # applications / edge cases / exam Q&A onto every entry
    _LOADED = True
