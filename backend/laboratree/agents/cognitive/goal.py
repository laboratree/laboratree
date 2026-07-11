"""Goal Interpreter — turn a raw ask into a structured Goal the meta-planner can reason about.

Cheap by law: generation-role model, deterministic template fallback, and skipped entirely for
narrow objectives (the whole cortex is bypassed — cost law F3).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ...core.jsonparse import loads_lenient
from ...labs.agentic import llm as agentic_llm

log = logging.getLogger(__name__)

# goal_kind keys the Experience DB — a coarse taxonomy is enough for recall
_KIND_KEYWORDS: dict[str, tuple[str, ...]] = {
    "modeling": ("model", "predict", "forecast", "regression", "classif", "cluster"),
    "analysis": ("analy", "crosstab", "correlat", "statistic", "distribution", "segment"),
    "literature": ("paper", "literature", "study", "studies", "research on", "evidence"),
    "collection": ("survey", "questionnaire", "interview", "collect"),
    "web": ("crawl", "scrape", "website", "job post", "listing"),
    "report": ("report", "summar", "brief", "deliverable", "present"),
}


@dataclass
class Goal:
    text: str
    intent: str
    deliverable: str = "findings"
    kind: str = "general"
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)


def classify_goal_kind(text: str) -> str:
    lowered = text.lower()
    for kind, keywords in _KIND_KEYWORDS.items():
        if any(k in lowered for k in keywords):
            return kind
    return "general"


def _fallback(text: str) -> Goal:
    return Goal(text=text, intent=text[:300], kind=classify_goal_kind(text))


def interpret_goal(message: str, context: str = "") -> Goal:
    """Structure the ask. Keyless or on failure → deterministic template, never a crash."""
    if not agentic_llm.is_configured():
        return _fallback(message)
    try:
        raw = agentic_llm.default_complete(
            "Interpret a research request. Respond ONLY as JSON: "
            '{"intent": "<one sentence>", "deliverable": "<what to hand back>", '
            '"constraints": ["..."], "success_criteria": ["..."]}. Be literal, no invention.',
            f"REQUEST:\n{message[:2000]}\n\nCONTEXT:\n{context[:800]}",
            role="generation")
    except agentic_llm.LLMNotConfigured:
        return _fallback(message)
    except Exception as exc:
        log.info("goal interpretation failed (%s); template fallback", exc)
        return _fallback(message)
    parsed = loads_lenient(raw) or {}
    if not parsed.get("intent"):
        return _fallback(message)
    return Goal(
        text=message,
        intent=str(parsed["intent"])[:300],
        deliverable=str(parsed.get("deliverable") or "findings")[:200],
        kind=classify_goal_kind(message),
        constraints=[str(c)[:200] for c in (parsed.get("constraints") or [])][:5],
        success_criteria=[str(c)[:200] for c in (parsed.get("success_criteria") or [])][:5],
    )


__all__ = ["Goal", "interpret_goal", "classify_goal_kind"]
