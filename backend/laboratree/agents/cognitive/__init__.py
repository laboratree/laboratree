"""The self-improving cognitive architecture (Slice F).

Goal Interpreter → Meta Planner (recalls the Experience DB) → specialist sub-agents
(research/coding/analysis) sharing a Working Memory + the tool layer → Reflection → Critic →
Verification → Experience DB → future runs plan better. The executor of this loop is
``agents.deep.run_deep_agent`` — this package supplies the organs.

Honest scope: "self-improving" v1 = recorded experience + recall-informed planning + reflection
lessons (strategy learning), NOT model-weight updates.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.llm.context import current_llm_context
from ...projects.models import LLMCall
from .goal import Goal, classify_goal_kind, interpret_goal
from .memory import (
    WorkingMemory,
    digest_experiences,
    recall_experiences,
    record_experience,
)
from .meta_planner import MAX_REFINE_TASKS, default_agent_type, meta_plan
from .reflection import Reflection, reflect
from .specialists import SPECIALIST_TOOLS, specialist_persona, specialist_tools
from .verify import verify_findings

log = logging.getLogger(__name__)

_AGENT_RUN_OP_PREFIX = "agent-run:"


async def tokens_spent(session: AsyncSession) -> int:
    """Live token rollup for the current agent run (0 outside an agent-run LLM context)."""
    operation = current_llm_context().operation
    if not operation.startswith(_AGENT_RUN_OP_PREFIX):
        return 0
    try:
        return (await session.execute(
            select(func.coalesce(func.sum(LLMCall.total_tokens), 0))
            .where(LLMCall.operation == operation)
        )).scalar_one()
    except Exception as exc:  # observability must never fail a run
        log.debug("token rollup failed: %s", exc)
        await session.rollback()
        return 0


def current_agent_run_id() -> uuid.UUID | None:
    operation = current_llm_context().operation
    if not operation.startswith(_AGENT_RUN_OP_PREFIX):
        return None
    try:
        return uuid.UUID(operation.removeprefix(_AGENT_RUN_OP_PREFIX))
    except ValueError:
        return None


__all__ = [
    "Goal", "interpret_goal", "classify_goal_kind",
    "WorkingMemory", "record_experience", "recall_experiences", "digest_experiences",
    "meta_plan", "default_agent_type", "MAX_REFINE_TASKS",
    "Reflection", "reflect",
    "SPECIALIST_TOOLS", "specialist_tools", "specialist_persona",
    "verify_findings", "tokens_spent", "current_agent_run_id",
]
