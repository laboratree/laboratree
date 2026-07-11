"""Meta-planning for deep agents: decompose an objective into delegable sub-agent tasks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ...core.jsonparse import loads_lenient
from ...labs.agentic import llm as agentic_llm
from ..tools import AgentTool, toolbelt_prompt
from . import prompts

log = logging.getLogger(__name__)

MAX_TASKS = 5
# below this many words an objective is "narrow" — planning would cost more than it buys
NARROW_OBJECTIVE_WORDS = 14
_BROAD_MARKERS = (" and ", ";", " then ", " compare", " all ", "comprehensive", "end to end")


@dataclass
class PlannedTask:
    id: int
    objective: str
    tools: list[str] = field(default_factory=list)     # names; empty = full scope


@dataclass
class AgentPlan:
    tasks: list[PlannedTask]
    planned: bool = True                               # False = single-pass fallback


def needs_planning(objective: str) -> bool:
    """Narrow asks skip the whole planning cortex (cost law)."""
    words = objective.split()
    if len(words) <= NARROW_OBJECTIVE_WORDS:
        return any(marker in objective.lower() for marker in _BROAD_MARKERS)
    return True


def plan_objective(objective: str, tools: dict[str, AgentTool]) -> AgentPlan:
    """LLM decomposition with a deterministic single-task fallback (keyless-safe)."""
    fallback = AgentPlan(tasks=[PlannedTask(id=1, objective=objective)], planned=False)
    if not agentic_llm.is_configured() or not needs_planning(objective):
        return fallback
    try:
        raw = agentic_llm.default_complete(
            prompts.plan_system(toolbelt_prompt(tools)), f"OBJECTIVE:\n{objective}",
            role="reasoning")
    except agentic_llm.LLMNotConfigured:
        return fallback
    parsed = loads_lenient(raw) or {}
    tasks = []
    for i, t in enumerate((parsed.get("tasks") or [])[:MAX_TASKS], start=1):
        if isinstance(t, dict) and t.get("objective"):
            names = [n for n in (t.get("tools") or []) if n in tools]
            tasks.append(PlannedTask(id=i, objective=str(t["objective"])[:500], tools=names))
    if not tasks:
        log.info("planner returned no usable tasks — single-pass fallback")
        return fallback
    return AgentPlan(tasks=tasks)


__all__ = ["AgentPlan", "PlannedTask", "plan_objective", "needs_planning", "MAX_TASKS"]
