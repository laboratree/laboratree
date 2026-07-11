"""Personality trait assignment (pure, deterministic).

Each persona gets stable OCEAN (Big Five) scores derived from a hash of its id + attributes, so the
same persona always has the same personality across survey waves. A short bio sketch turns the
numbers into promptable prose for the simulation engine.
"""

from __future__ import annotations

import hashlib
from typing import Any

OCEAN = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")


def _stable_unit(seed: str) -> float:
    """A stable float in [0, 1] from a string seed (deterministic across runs/machines)."""
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def assign_traits(persona: dict[str, Any]) -> dict[str, float]:
    """Deterministic OCEAN scores for a persona (stable given its id + attributes)."""
    base = str(persona.get("id", "")) + "|" + "|".join(
        f"{k}={v}" for k, v in sorted((persona.get("attributes") or {}).items())
    )
    return {trait: round(_stable_unit(f"{base}#{trait}"), 3) for trait in OCEAN}


def _band(score: float, low: str, mid: str, high: str) -> str:
    return low if score < 0.34 else (mid if score < 0.67 else high)


def bio_sketch(persona: dict[str, Any], traits: dict[str, float]) -> str:
    """A short natural-language personality description for prompting."""
    attrs = persona.get("attributes") or {}
    who = ", ".join(f"{k}: {v}" for k, v in attrs.items()) or "a general respondent"
    phrases = [
        _band(traits["openness"], "practical and conventional", "moderately curious",
              "curious and open to new ideas"),
        _band(traits["conscientiousness"], "spontaneous", "reasonably organized",
              "careful and detail-oriented"),
        _band(traits["extraversion"], "reserved", "socially balanced", "outgoing and talkative"),
        _band(traits["agreeableness"], "skeptical and blunt", "even-handed",
              "warm and cooperative"),
        _band(traits["neuroticism"], "calm and resilient", "generally steady",
              "sensitive and easily worried"),
    ]
    return f"{who}. Personality: {'; '.join(phrases)}."


__all__ = ["OCEAN", "assign_traits", "bio_sketch"]
