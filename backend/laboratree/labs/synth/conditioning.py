"""Objective-conditioned persona traits — powerful for stress-tests, POISON for RCTs.

``condition_traits`` shifts a persona's OCEAN priors toward a survey objective (LLM-proposed,
deterministic keyword-map fallback) — but every shift is CLAMPED (|Δ| ≤ MAX_TRAIT_DELTA) and the
full per-trait delta is RETURNED so cohorts store exactly the bias that was injected. It is
never applied silently, and cohorts created for RCT/impact work must stay neutral (enforced at
the API): objective-conditioned respondents would bias causal estimates by construction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ...core.jsonparse import loads_lenient
from ..agentic import llm as agentic_llm
from .traits import OCEAN

log = logging.getLogger(__name__)

MAX_TRAIT_DELTA = 0.25

_SYSTEM = (
    "Given a survey objective and a persona, propose how the persona's Big-Five traits should "
    "shift to make it a REALISTIC respondent for this objective, plus up to 3 objective-"
    'relevant attitude attributes. Respond ONLY as JSON: {"deltas": {"openness": <-1..1>, ...}, '
    '"attitudes": {"<name>": "<value>"}}. Small, defensible shifts only.'
)

# deterministic fallback: objective keywords -> modest trait nudges
_KEYWORD_NUDGES: dict[str, dict[str, float]] = {
    "health": {"neuroticism": 0.15, "conscientiousness": 0.1},
    "education": {"openness": 0.15, "conscientiousness": 0.1},
    "finance": {"conscientiousness": 0.15, "neuroticism": 0.1},
    "safety": {"neuroticism": 0.2},
    "technology": {"openness": 0.2},
    "environment": {"openness": 0.15, "agreeableness": 0.1},
}


@dataclass
class ConditionedTraits:
    traits: dict[str, float]
    delta: dict[str, float]
    attitudes: dict[str, Any] = field(default_factory=dict)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _apply(base: dict[str, float], raw_deltas: dict[str, Any],
           attitudes: dict[str, Any]) -> ConditionedTraits:
    traits: dict[str, float] = {}
    delta: dict[str, float] = {}
    for trait in OCEAN:
        proposed = float(raw_deltas.get(trait, 0.0) or 0.0)
        clamped = max(-MAX_TRAIT_DELTA, min(MAX_TRAIT_DELTA, proposed))
        delta[trait] = round(clamped, 4)
        traits[trait] = round(_clamp(base.get(trait, 0.5) + clamped), 4)
    return ConditionedTraits(traits=traits, delta=delta,
                             attitudes={str(k)[:40]: v for k, v in list(attitudes.items())[:3]})


def _fallback_deltas(objective: str) -> dict[str, float]:
    deltas: dict[str, float] = {}
    lowered = objective.lower()
    for keyword, nudges in _KEYWORD_NUDGES.items():
        if keyword in lowered:
            for trait, shift in nudges.items():
                deltas[trait] = deltas.get(trait, 0.0) + shift
    return deltas


def condition_traits(persona: dict[str, Any], objective: str) -> ConditionedTraits:
    """Objective-shift a persona's traits. Clamped, fully recorded, keyless-safe."""
    base = dict(persona.get("traits") or {t: 0.5 for t in OCEAN})
    if not agentic_llm.is_configured():
        return _apply(base, _fallback_deltas(objective), {})
    try:
        raw = agentic_llm.default_complete(
            _SYSTEM,
            f"OBJECTIVE:\n{objective}\n\nPERSONA:\n{persona.get('bio', '')[:600]}",
            role="generation")
        parsed = loads_lenient(raw) or {}
        return _apply(base, parsed.get("deltas") or {}, parsed.get("attitudes") or {})
    except agentic_llm.LLMNotConfigured:
        return _apply(base, _fallback_deltas(objective), {})
    except Exception as exc:
        log.info("conditioning LLM failed (%s); keyword fallback", exc)
        return _apply(base, _fallback_deltas(objective), {})


__all__ = ["condition_traits", "ConditionedTraits", "MAX_TRAIT_DELTA"]
