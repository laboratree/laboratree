"""Plan primitives for deep agents — the meta-planner itself lives in ``agents.cognitive``."""

from __future__ import annotations

from dataclasses import dataclass, field

MAX_TASKS = 5
# below this many words an objective is "narrow" — planning would cost more than it buys
NARROW_OBJECTIVE_WORDS = 14
_BROAD_MARKERS = (" and ", ";", " then ", " compare", " all ", "comprehensive", "end to end")


@dataclass
class PlannedTask:
    id: int
    objective: str
    tools: list[str] = field(default_factory=list)     # names; empty = full scope
    agent_type: str = ""                               # research|coding|analysis; "" = generic


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


__all__ = ["AgentPlan", "PlannedTask", "needs_planning", "MAX_TASKS"]
