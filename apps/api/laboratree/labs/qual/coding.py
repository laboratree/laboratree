"""Thematic coding + sentiment over transcript segments (LLM, injectable, strictly validated).

Assignments referencing unknown codes or out-of-range segments are DROPPED, never guessed —
the codebook a human approved is the only vocabulary that can appear in results.
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.jsonparse import loads_lenient
from .codebook import CompleteFn

log = logging.getLogger(__name__)

SENTIMENTS = ("positive", "neutral", "negative")

_CODING_SYSTEM = (
    "You apply an approved qualitative codebook to numbered transcript segments. For every segment "
    "that clearly matches a code, output an assignment. Return ONLY a JSON array of "
    '{"segment": <index>, "code": "<exact code name>", "confidence": <0..1>, '
    '"support": "<short verbatim snippet>"}. Skip segments that match nothing.'
)

_SENTIMENT_SYSTEM = (
    "You rate the sentiment of numbered transcript segments from the SPEAKER's perspective. "
    'Return ONLY a JSON array of {"segment": <index>, "sentiment": "positive|neutral|negative"} '
    "covering every segment."
)


def _numbered(segments: list[dict[str, Any]]) -> str:
    return "\n".join(f"{i}. {s.get('text', '')}" for i, s in enumerate(segments))


def apply_codebook(
    segments: list[dict[str, Any]],
    codes: list[dict[str, str]],
    complete_fn: CompleteFn,
) -> list[dict[str, Any]]:
    """Code segments against an approved codebook → validated assignments (source='ai')."""
    if not segments or not codes:
        return []
    code_names = {c["name"] for c in codes}
    codebook_text = "\n".join(f"- {c['name']}: {c['definition']}" for c in codes)
    raw = complete_fn(
        _CODING_SYSTEM,
        f"Codebook:\n{codebook_text}\n\nSegments:\n{_numbered(segments)}\n\nCode them now.",
    )
    parsed = loads_lenient(raw)
    assignments: list[dict[str, Any]] = []
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict):
            continue
        segment = item.get("segment")
        code = str(item.get("code", "")).strip()
        if not isinstance(segment, int) or not (0 <= segment < len(segments)):
            continue
        if code not in code_names:  # never invent codes outside the approved vocabulary
            continue
        confidence = item.get("confidence")
        assignments.append({
            "segment": segment,
            "code": code,
            "confidence": round(float(confidence), 3) if isinstance(confidence, (int, float)) else None,
            "support": str(item.get("support", ""))[:300],
            "source": "ai",
        })
    log.info("thematic coding: %d assignments across %d segments", len(assignments), len(segments))
    return assignments


def segment_sentiment(
    segments: list[dict[str, Any]], complete_fn: CompleteFn
) -> list[dict[str, Any]]:
    """Per-segment sentiment → validated [{segment, sentiment}] (unknown labels dropped)."""
    if not segments:
        return []
    raw = complete_fn(_SENTIMENT_SYSTEM, f"Segments:\n{_numbered(segments)}")
    parsed = loads_lenient(raw)
    out: list[dict[str, Any]] = []
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict):
            continue
        segment = item.get("segment")
        sentiment = str(item.get("sentiment", "")).strip().lower()
        if isinstance(segment, int) and 0 <= segment < len(segments) and sentiment in SENTIMENTS:
            out.append({"segment": segment, "sentiment": sentiment})
    log.info("sentiment: %d/%d segments rated", len(out), len(segments))
    return out


__all__ = ["SENTIMENTS", "apply_codebook", "segment_sentiment"]
