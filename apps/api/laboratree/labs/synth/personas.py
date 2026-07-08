"""Persona frame construction (pure, deterministic).

Given target margins per attribute (e.g. ``{"gender": {"male": 0.5, "female": 0.5}}``), build N
persona skeletons whose attribute counts match the margins as closely as integer rounding allows.
Attributes are allocated independently per dimension (a light stand-in for full IPF — adequate for a
pre-fielding dry-run; joint-distribution IPF is a later upgrade).
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

MAX_PERSONAS = 100  # hard cap: twins cost LLM calls; a dry-run needs a sample, not a census


def _allocate(n: int, proportions: dict[str, float]) -> list[str]:
    """Split n items across categories by proportion, using largest-remainder rounding."""
    if not proportions:
        return []
    total = sum(proportions.values()) or 1.0
    exact = {k: n * v / total for k, v in proportions.items()}
    counts = {k: int(v) for k, v in exact.items()}
    remainder = n - sum(counts.values())
    # hand out the leftover to the largest fractional parts, deterministically
    order = sorted(exact, key=lambda k: (exact[k] - counts[k], k), reverse=True)
    for i in range(remainder):
        counts[order[i % len(order)]] += 1
    values: list[str] = []
    for category, count in counts.items():
        values.extend([category] * count)
    return values


def build_personas(n: int, margins: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    """Build ``min(n, MAX_PERSONAS)`` personas matching the per-attribute target margins."""
    n = max(1, min(int(n), MAX_PERSONAS))
    per_dimension = {dim: _allocate(n, props) for dim, props in (margins or {}).items()}
    personas: list[dict[str, Any]] = []
    for i in range(n):
        attributes = {dim: values[i] for dim, values in per_dimension.items() if i < len(values)}
        personas.append({"id": f"p{i + 1}", "attributes": attributes})
    log.info("built %d personas across %d attribute dimensions", len(personas), len(margins or {}))
    return personas


def describe(persona: dict[str, Any]) -> str:
    """A short natural-language description of a persona for prompting."""
    attrs = persona.get("attributes") or {}
    if not attrs:
        return "a general member of the target population"
    return ", ".join(f"{k}: {v}" for k, v in attrs.items())


__all__ = ["MAX_PERSONAS", "build_personas", "describe"]
