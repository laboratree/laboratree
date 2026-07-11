"""Meta Planner — experience-informed decomposition into typed specialist tasks.

Upgrades ``deep.planner.plan_objective``: the prompt carries the recalled Experience digest
("last time crosstab-first beat model-first") and every task gains an agent_type
(research|coding|analysis) so the orchestrator dispatches the right specialist with the right
tool scope. Runs ONLY for broad goals (``needs_planning`` guard — cost law F3); keyless or on
failure → deterministic single-task plan typed from the goal kind.
"""

from __future__ import annotations

import logging

from ...core.jsonparse import loads_lenient
from ...labs.agentic import llm as agentic_llm
from ..deep.planner import MAX_TASKS, AgentPlan, PlannedTask, needs_planning
from ..tools import AgentTool, toolbelt_prompt
from .goal import Goal
from .specialists import SPECIALIST_TOOLS

log = logging.getLogger(__name__)

MAX_REFINE_TASKS = 2

_KIND_TO_AGENT = {"literature": "research", "web": "research", "collection": "research",
                  "modeling": "analysis", "analysis": "analysis", "report": "research"}


def default_agent_type(goal: Goal) -> str:
    if any(k in goal.text.lower() for k in ("sandbox", "write code", "script", "notebook")):
        return "coding"
    return _KIND_TO_AGENT.get(goal.kind, "research")


def _meta_plan_system(tool_catalog: str, experience_digest: str) -> str:
    experience = f"\n{experience_digest}\n" if experience_digest else ""
    return (
        "You are the meta-planner of a research platform. Decompose the goal into 2-5 small, "
        "delegable tasks for specialist sub-agents (research: external evidence; coding: "
        "components/sandbox; analysis: the project's own data via SQL/Cypher/components).\n"
        f"{experience}\n"
        f"AVAILABLE TOOLS:\n{tool_catalog}\n\n"
        'Respond ONLY as JSON: {"tasks": [{"objective": "<one focused sub-goal>", '
        '"agent_type": "research"|"coding"|"analysis", '
        '"tools": ["<tool names best suited>"]}]}. Order tasks so later ones build on earlier '
        "results; apply the past-experience lessons when they fit. Do not invent tools."
    )


def meta_plan(goal: Goal, tools: dict[str, AgentTool], *,
              experience_digest: str = "", focus: str = "",
              max_tasks: int = MAX_TASKS) -> AgentPlan:
    """Experience-informed plan. ``focus`` narrows a refinement round to the unmet parts."""
    fallback = AgentPlan(
        tasks=[PlannedTask(id=1, objective=goal.text[:500],
                           agent_type=default_agent_type(goal))],
        planned=False)
    if not agentic_llm.is_configured() or (not focus and not needs_planning(goal.text)):
        return fallback
    ask = f"GOAL:\n{goal.intent or goal.text}"
    if goal.success_criteria:
        ask += "\nSUCCESS CRITERIA:\n" + "\n".join(f"- {c}" for c in goal.success_criteria)
    if focus:
        ask += f"\n\nREVISION — plan ONLY for the unmet parts below (max {max_tasks} tasks):\n{focus}"
    try:
        raw = agentic_llm.default_complete(
            _meta_plan_system(toolbelt_prompt(tools), experience_digest), ask,
            role="reasoning")
    except agentic_llm.LLMNotConfigured:
        return fallback
    except Exception as exc:
        log.info("meta-plan failed (%s); single-task fallback", exc)
        return fallback
    parsed = loads_lenient(raw) or {}
    tasks = []
    for i, t in enumerate((parsed.get("tasks") or [])[:max_tasks], start=1):
        if isinstance(t, dict) and t.get("objective"):
            agent_type = str(t.get("agent_type", ""))
            tasks.append(PlannedTask(
                id=i, objective=str(t["objective"])[:500],
                tools=[n for n in (t.get("tools") or []) if n in tools],
                agent_type=agent_type if agent_type in SPECIALIST_TOOLS
                else default_agent_type(goal)))
    if not tasks:
        log.info("meta-planner returned no usable tasks — single-task fallback")
        return fallback
    return AgentPlan(tasks=tasks)


__all__ = ["meta_plan", "default_agent_type", "MAX_REFINE_TASKS"]
