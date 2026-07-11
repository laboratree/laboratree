"""Pluggable persona engine (house pattern: OCREngine / Mailer / TranscriptionEngine).

The default ``LLMPersonaEngine`` builds trait-stable personas and simulates a survey wave, then
applies behavioural grounding so theory — not the LLM — decides questions that declare a model.
A TinyTroupe (or other agent-simulation) backend can be added later behind this same interface
without touching call sites; it is selected by ``settings.persona_engine``.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from ...core.config import settings
from . import llm as synth_llm
from .fallback import deterministic_wave_answers
from .grounding import ground_answers
from .personas import build_personas
from .traits import assign_traits, bio_sketch
from .twin import simulate_persona_wave

log = logging.getLogger(__name__)


class PersonaEngineUnavailable(RuntimeError):
    """Raised when the configured engine has no implementation — surfaced honestly, never faked."""


class PersonaEngine(Protocol):
    def build(self, n: int, margins: dict[str, dict[str, float]]) -> list[dict[str, Any]]: ...

    def simulate(
        self, structure: dict[str, Any], persona: dict[str, Any], *, social_context: str = ""
    ) -> dict[str, Any]: ...


class LLMPersonaEngine:
    """Trait-stable personas; LLM answers, overridden by behavioural theory where declared."""

    def build(self, n: int, margins: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
        skeletons = build_personas(n, margins)
        for skeleton in skeletons:
            skeleton["handle"] = str(skeleton.get("id", ""))
            skeleton["traits"] = assign_traits(skeleton)
            skeleton["bio"] = bio_sketch(skeleton, skeleton["traits"])
        return skeletons

    def simulate(
        self, structure: dict[str, Any], persona: dict[str, Any], *, social_context: str = ""
    ) -> dict[str, Any]:
        try:
            result = simulate_persona_wave(
                structure, persona, synth_llm.default_complete, social_context=social_context
            )
        except synth_llm.LLMNotConfigured as exc:
            # key absence only — real API errors still propagate
            log.warning("persona wave without LLM (%s) — deterministic fallback", exc)
            result = deterministic_wave_answers(structure, persona)
        grounded = ground_answers(structure, persona, result.get("answers") or {})
        result["answers"] = grounded.answers
        result["grounded"] = grounded.grounded
        return result


def get_persona_engine() -> PersonaEngine:
    provider = settings.persona_engine.lower()
    if provider == "llm":
        return LLMPersonaEngine()
    raise PersonaEngineUnavailable(
        f"persona engine {provider!r} is not implemented — set PERSONA_ENGINE=llm "
        "(a TinyTroupe backend can be plugged in behind this interface)"
    )


__all__ = ["PersonaEngine", "PersonaEngineUnavailable", "LLMPersonaEngine", "get_persona_engine"]
