"""Response-quality flags (pure) + a registered analyzer component.

Flags mark suspect responses; they never delete data (Evidence honesty). The API applies these
inline at completion; the ``analyzer.response_quality`` component exposes the same logic to the
catalog/pipeline for batch auditing.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from ..runtime import iter_questions

log = logging.getLogger(__name__)

# Flag names (also the keys the component emits counts for).
FLAG_SPEEDER = "speeder"
FLAG_STRAIGHTLINER = "straightliner"
FLAG_DUPLICATE = "duplicate"

DEFAULT_MIN_SECONDS_PER_QUESTION = 4.0
DEFAULT_STRAIGHTLINE_THRESHOLD = 0.9
MIN_ANSWERS_FOR_STRAIGHTLINE = 3


def flag_speeder(
    duration_seconds: float | None,
    question_count: int,
    min_seconds_per_question: float = DEFAULT_MIN_SECONDS_PER_QUESTION,
) -> bool:
    """True if the response was completed implausibly fast for its length."""
    if not duration_seconds or question_count <= 0:
        return False
    return duration_seconds < min_seconds_per_question * question_count


def flag_straightliner(
    answers: dict[str, Any],
    structure: dict[str, Any],
    threshold: float = DEFAULT_STRAIGHTLINE_THRESHOLD,
) -> bool:
    """True if a dominant fraction of scale/single answers are identical (no discrimination)."""
    categorical = {
        str(q.get("id"))
        for q in iter_questions(structure)
        if q.get("type") in ("scale", "single")
    }
    values = [
        answers[qid]
        for qid in categorical
        if qid in answers and answers[qid] not in (None, "", [])
    ]
    if len(values) < MIN_ANSWERS_FOR_STRAIGHTLINE:
        return False
    hashable = [v if not isinstance(v, list) else tuple(v) for v in values]
    _, top = Counter(hashable).most_common(1)[0]
    return top / len(hashable) >= threshold


def flag_duplicate(
    fingerprint: dict[str, Any] | None, prior_fingerprints: list[dict[str, Any]]
) -> bool:
    """True if this fingerprint's ip_hash already appears among prior responses."""
    if not fingerprint:
        return False
    ip_hash = fingerprint.get("ip_hash")
    if not ip_hash:
        return False
    return any((prior or {}).get("ip_hash") == ip_hash for prior in prior_fingerprints)


def quality_flags(
    *,
    answers: dict[str, Any],
    structure: dict[str, Any],
    duration_seconds: float | None,
    fingerprint: dict[str, Any] | None,
    prior_fingerprints: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Compute all quality flags for one response. Returns a list of flag names (possibly empty)."""
    flags: list[str] = []
    if flag_speeder(duration_seconds, len(iter_questions(structure))):
        flags.append(FLAG_SPEEDER)
    if flag_straightliner(answers, structure):
        flags.append(FLAG_STRAIGHTLINER)
    if flag_duplicate(fingerprint, prior_fingerprints or []):
        flags.append(FLAG_DUPLICATE)
    return flags


@register
class ResponseQuality(Component):
    """Batch-audit a set of survey responses for speeders, straightliners, and duplicates."""

    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="analyzer.response_quality",
        name="Response quality audit",
        summary="Flag suspect survey responses (speeders, straightliners, duplicates).",
        params_schema={
            "type": "object",
            "properties": {
                "structure": {"type": "object"},
                "responses": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Each: {answers, duration_seconds?, fingerprint?}",
                },
            },
            "required": ["structure", "responses"],
        },
        inputs=[],
        outputs=[Port(name="result", dtype="metrics")],
        tags=["fieldwork", "quality"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        structure = ctx.params.get("structure") or {}
        responses = ctx.params.get("responses") or []
        counts = {FLAG_SPEEDER: 0, FLAG_STRAIGHTLINER: 0, FLAG_DUPLICATE: 0}
        seen_fingerprints: list[dict[str, Any]] = []
        flagged = 0
        for response in responses:
            flags = quality_flags(
                answers=response.get("answers") or {},
                structure=structure,
                duration_seconds=response.get("duration_seconds"),
                fingerprint=response.get("fingerprint"),
                prior_fingerprints=seen_fingerprints,
            )
            if response.get("fingerprint"):
                seen_fingerprints.append(response["fingerprint"])
            if flags:
                flagged += 1
            for flag in flags:
                counts[flag] += 1

        total = len(responses)
        ctx.emit("responses_audited", total, kind="metric", component=self.spec.id)
        ctx.emit("responses_flagged", flagged, kind="metric", component=self.spec.id)
        for flag, count in counts.items():
            ctx.emit(f"flag_{flag}", count, kind="metric", component=self.spec.id)
        return {"audited": total, "flagged": flagged, "counts": counts}


__all__ = [
    "FLAG_SPEEDER",
    "FLAG_STRAIGHTLINER",
    "FLAG_DUPLICATE",
    "flag_speeder",
    "flag_straightliner",
    "flag_duplicate",
    "quality_flags",
    "ResponseQuality",
]
