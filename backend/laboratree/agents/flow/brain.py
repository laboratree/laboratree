"""The flow's reasoning brain — dispatch a phase to the LLM agent over REAL project context.

``agentic_phase`` runs ``agent.reason`` (an Evidence-locked component run) against context
assembled from the project's actual artifacts: dataset schemas + sample rows and whatever earlier
phases put in state. No LLM key → typed fallback to the phase's deterministic executor, and the
result says which brain produced it — agent output and canned output are never conflated.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from sqlalchemy import select

from ...labs.agentic import llm as agentic_llm
from ...projects.models import Dataset
from ..run_executor import execute_component
from . import FlowContext, PhaseResult

log = logging.getLogger(__name__)

MAX_CONTEXT_DATASETS = 5
SAMPLE_ROWS = 5


async def project_context(ctx: FlowContext) -> str:
    """Assemble the real material the agent reasons over (never fabricated)."""
    parts: list[str] = []
    datasets = (await ctx.session.execute(
        select(Dataset).where(Dataset.project_id == ctx.project_id)
        .order_by(Dataset.created_at.desc()).limit(MAX_CONTEXT_DATASETS)
    )).scalars().all()
    for ds in datasets:
        parts.append(f"DATASET {ds.name!r}: {ds.n_rows} rows x {ds.n_cols} cols")
    df = ctx.state.get("df")
    if df is not None:
        parts.append(f"COLUMNS: {list(df.columns)}")
        parts.append(f"SAMPLE ROWS: {df.head(SAMPLE_ROWS).to_dict('records')}")
    if brief := ctx.state.get("brief"):
        parts.append(f"PROJECT BRIEF: {brief}")
    return "\n".join(parts) or "No project data uploaded yet."


async def agentic_phase(
    ctx: FlowContext, stage_id: str, objective: str,
    fallback: Callable[[FlowContext], Awaitable[PhaseResult]],
) -> PhaseResult:
    """LLM agent when configured; the deterministic executor otherwise — labeled either way."""
    if not agentic_llm.is_configured():
        log.warning("phase %s: no LLM configured — using the deterministic executor", stage_id)
        fallback_result = await fallback(ctx)
        fallback_result.summary = f"{fallback_result.summary} (deterministic — no LLM configured)"
        return fallback_result

    context = await project_context(ctx)
    result = await execute_component(
        ctx.session, org_id=ctx.org_id, project_id=ctx.project_id,
        component_id="agent.reason",
        params={"objective": objective, "context": context},
        inputs={}, lab="orchestrator",
    )

    ctx.state.setdefault("run_ids", {})[f"agent.reason:{stage_id}"] = str(result.run.id)
    output = result.outputs if isinstance(result.outputs, dict) else {}
    summary = output.get("summary") or "agent reasoned over the project context"
    return PhaseResult(stage_id=stage_id, status="succeeded",
                       summary=f"🧠 {summary}"[:300],
                       run_id=str(result.run.id), evidence=result.evidence_count,
                       artifacts={"agent": True, "model": output.get("model"),
                                  "n_findings": output.get("n_findings")})
