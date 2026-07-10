"""Theory-grounded answers: replace the LLM's guess where behavioural theory can decide.

A question opts in by declaring a ``behavioral`` spec. Only those questions are overridden — every
other answer stays as the LLM produced it, so nothing is silently "corrected" by theory that theory
has no claim on.

Supported models:
- ``discrete_choice`` — multinomial logit over alternatives; each persona draws deterministically
  from the predicted shares, so a cohort's aggregate choice shares match the MNL prediction while
  any single persona stays reproducible across runs.
- ``prospect`` — prospect-theory value over outcomes; the persona prefers the higher-value option.
  Loss aversion is modulated by the persona's neuroticism (a documented heuristic: more neurotic
  respondents behave more loss-averse), around the Kahneman-Tversky median of lambda = 2.25.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any

from .behavioral import PT_LAMBDA, choice_shares, prospect_value

log = logging.getLogger(__name__)


@dataclass
class GroundedResult:
    """Answers after theory grounding, plus the ids of the questions theory decided."""

    answers: dict[str, Any]
    grounded: list[str] = field(default_factory=list)


def stable_unit(seed: str) -> float:
    """Deterministic float in [0, 1) from a seed — a persona's stable 'coin'."""
    return int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) / 0x100000000


def _loss_aversion(persona: dict[str, Any]) -> float:
    """Neuroticism scales loss aversion around the K-T median (2.25)."""
    neuroticism = float((persona.get("traits") or {}).get("neuroticism", 0.5))
    return PT_LAMBDA * (0.5 + neuroticism)


def _discrete_choice_answer(spec: dict[str, Any], persona: dict[str, Any], qid: str) -> Any:
    alternatives = spec.get("alternatives") or []
    weights = spec.get("weights") or {}
    if not alternatives:
        return None
    attrs = [{k: v for k, v in alt.items() if k != "option"} for alt in alternatives]
    shares = choice_shares(attrs, weights, scale=float(spec.get("scale", 1.0)))
    draw = stable_unit(f"{persona.get('handle', '')}|{qid}")
    cumulative = 0.0
    for alt, row in zip(alternatives, shares, strict=True):
        cumulative += row["share"]
        if draw <= cumulative:
            return alt.get("option")
    return alternatives[-1].get("option")


def _prospect_answer(spec: dict[str, Any], persona: dict[str, Any]) -> Any:
    options = spec.get("options") or []
    if not options:
        return None
    reference = float(spec.get("reference", 0.0))
    lam = _loss_aversion(persona)
    best = max(
        options,
        key=lambda o: prospect_value(float(o.get("outcome", 0.0)), reference=reference, lam=lam),
    )
    return best.get("option")


def ground_answers(
    structure: dict[str, Any], persona: dict[str, Any], answers: dict[str, Any]
) -> GroundedResult:
    """Override answers for questions that declare a behavioural model. Returns (answers, grounded)."""
    grounded: list[str] = []
    out = dict(answers)
    for section in structure.get("sections", []) or []:
        for question in section.get("questions", []) or []:
            spec = question.get("behavioral")
            if not isinstance(spec, dict):
                continue
            qid = str(question.get("id"))
            model = spec.get("model")
            if model == "discrete_choice":
                value = _discrete_choice_answer(spec, persona, qid)
            elif model == "prospect":
                value = _prospect_answer(spec, persona)
            else:
                log.info("unknown behavioural model %r on %s — leaving the LLM answer", model, qid)
                continue
            if value is not None:
                out[qid] = value
                grounded.append(qid)
    return GroundedResult(answers=out, grounded=grounded)


__all__ = ["GroundedResult", "stable_unit", "ground_answers"]
