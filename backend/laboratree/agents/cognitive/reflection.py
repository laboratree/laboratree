"""Reflection — after a run, distill what worked, what failed, and ≤3 reusable lessons.

The lessons feed the Experience DB so future meta-plans start smarter (strategy learning).
Deterministic fallback keeps keyless runs recording honest outcomes with no invented lessons.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ...core.jsonparse import loads_lenient
from ...labs.agentic import llm as agentic_llm
from .goal import Goal
from .memory import MAX_LESSONS

log = logging.getLogger(__name__)


@dataclass
class Reflection:
    worked: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)


def deterministic_reflection(task_notes: list[dict[str, Any]]) -> Reflection:
    """Honest no-LLM reflection: outcomes recorded, no invented lessons."""
    return Reflection(
        worked=[str(t.get("objective", ""))[:150] for t in task_notes if t.get("ok")],
        failed=[str(t.get("objective", ""))[:150] for t in task_notes if not t.get("ok")],
        lessons=[],
    )


def reflect(goal: Goal, task_notes: list[dict[str, Any]], *,
            critic_dropped: int = 0) -> Reflection:
    """task_notes: [{objective, agent_type, ok, summary}] — the run's honest self-assessment."""
    if not agentic_llm.is_configured():
        return deterministic_reflection(task_notes)
    listing = "\n".join(
        f'- [{t.get("agent_type", "?")}] {"OK" if t.get("ok") else "FAILED"}: '
        f'{str(t.get("objective", ""))[:150]} → {str(t.get("summary", ""))[:150]}'
        for t in task_notes)
    try:
        raw = agentic_llm.default_complete(
            "Reflect on an agent run. Respond ONLY as JSON: "
            '{"worked": ["..."], "failed": ["..."], "lessons": ["<reusable strategy lesson '
            'for similar future goals, imperative voice>"]}. Max 3 lessons, only ones a '
            "future planner could act on; empty lists are fine.",
            f"GOAL:\n{goal.intent or goal.text}\n\nTASKS:\n{listing}\n\n"
            f"CRITIC DROPPED: {critic_dropped} unsupported finding(s).",
            role="reasoning")
    except agentic_llm.LLMNotConfigured:
        return deterministic_reflection(task_notes)
    except Exception as exc:
        log.info("reflection failed (%s); deterministic fallback", exc)
        return deterministic_reflection(task_notes)
    parsed = loads_lenient(raw) or {}
    return Reflection(
        worked=[str(w)[:200] for w in (parsed.get("worked") or [])][:5],
        failed=[str(f)[:200] for f in (parsed.get("failed") or [])][:5],
        lessons=[str(le)[:300] for le in (parsed.get("lessons") or [])][:MAX_LESSONS],
    )


__all__ = ["Reflection", "reflect", "deterministic_reflection"]
