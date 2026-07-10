"""Deterministic persona answers — the no-LLM fallback for wave simulation.

House pattern: every agentic feature keeps a deterministic fallback. When no LLM provider is
configured, a wave still runs: each persona answers every question from a stable hash of
(handle, question id) shaded by its traits, so answers are reproducible, vary across the cohort,
and stay consistent for the same persona across waves. Results carry ``fallback: "deterministic"``
so nobody mistakes them for LLM reasoning.
"""

from __future__ import annotations

import logging
from typing import Any

from .grounding import stable_unit

log = logging.getLogger(__name__)


def _scale_answer(question: dict[str, Any], persona: dict[str, Any], draw: float) -> int:
    scale = question.get("scale") or {}
    lo, hi = int(scale.get("min", 1)), int(scale.get("max", 5))
    # neurotic personas skew toward the anxious end of scales
    neuroticism = float((persona.get("traits") or {}).get("neuroticism", 0.5))
    shaded = min(0.999, max(0.0, 0.7 * draw + 0.3 * neuroticism))
    return lo + int(shaded * (hi - lo + 1) - 1e-9)


def _answer(question: dict[str, Any], persona: dict[str, Any]) -> Any:
    qid = str(question.get("id"))
    draw = stable_unit(f"{persona.get('handle', '')}|{qid}")
    qtype = question.get("type")
    options = question.get("options") or []
    if qtype == "single" and options:
        return options[int(draw * len(options)) % len(options)]
    if qtype == "multi" and options:
        picked = [o for i, o in enumerate(options)
                  if stable_unit(f"{persona.get('handle', '')}|{qid}|{i}") < 0.4]
        return picked or [options[int(draw * len(options)) % len(options)]]
    if qtype == "scale":
        return _scale_answer(question, persona, draw)
    if qtype == "number":
        return round(draw * 100, 1)
    return f"({persona.get('handle', 'persona')} answered deterministically)"


def deterministic_wave_answers(
    structure: dict[str, Any], persona: dict[str, Any]
) -> dict[str, Any]:
    """Answer the whole instrument without an LLM. Same result shape as simulate_persona_wave."""
    answers: dict[str, Any] = {}
    for section in structure.get("sections", []) or []:
        for question in section.get("questions", []) or []:
            answers[str(question.get("id"))] = _answer(question, persona)
    return {
        "answers": answers,
        "confusions": [],
        "dropped_at": None,
        "persona_id": persona.get("id"),
        "fallback": "deterministic",
    }


__all__ = ["deterministic_wave_answers"]
