"""Flow orchestrator — walks a pipeline template phase by phase, each phase a sub-agent.

Every stage id maps to a registered *phase executor*: an async callable with a fixed contract
(``FlowContext`` in, ``PhaseResult`` out). The orchestrator dispatches them in order, threads
shared state (datasets, survey ids, run ids) between phases, opens a real HITL ``GateTask`` for
manual stages, and records everything under one parent Run — so an orchestrated flow is itself
provenance-tracked. A failing phase is recorded honestly and the flow continues; nothing is
silently skipped.

This is the Study Navigator (U15) skeleton: LLM-reasoning sub-agents can replace individual
executors later without changing the contract.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...projects.models import GateStatus, GateTask, Run, RunStatus

log = logging.getLogger(__name__)


@dataclass
class FlowContext:
    """What a phase executor gets to work with."""

    session: AsyncSession
    org_id: uuid.UUID
    project_id: uuid.UUID
    flow_run: Run                                  # the parent Run all gates hang off
    state: dict[str, Any] = field(default_factory=dict)   # cross-phase artifacts


@dataclass
class PhaseResult:
    stage_id: str
    status: str                                    # succeeded | failed | gated | skipped
    summary: str = ""
    run_id: str | None = None
    evidence: int = 0
    artifacts: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


PhaseExecutor = Callable[[FlowContext], Awaitable[PhaseResult]]

_EXECUTORS: dict[tuple[str, str], PhaseExecutor] = {}


def phase(flow_key: str, stage_id: str) -> Callable[[PhaseExecutor], PhaseExecutor]:
    """Register an executor for one stage of one flow."""

    def _wrap(fn: PhaseExecutor) -> PhaseExecutor:
        _EXECUTORS[(flow_key, stage_id)] = fn
        return fn

    return _wrap


def registered_stages(flow_key: str) -> list[str]:
    return [stage for key, stage in _EXECUTORS if key == flow_key]


async def open_gate(ctx: FlowContext, *, stage_id: str, title: str,
                    description: str, payload: dict[str, Any]) -> PhaseResult:
    """A manual phase = a real HITL gate the humans resolve in the gates inbox."""
    gate = GateTask(org_id=ctx.org_id, run_id=ctx.flow_run.id, title=title,
                    description=description, payload=payload, status=GateStatus.PENDING)
    ctx.session.add(gate)
    await ctx.session.flush()
    return PhaseResult(stage_id=stage_id, status="gated",
                       summary=f"waiting on human approval: {title}",
                       artifacts={"gate_id": str(gate.id)})


async def run_flow(
    session: AsyncSession, *, org_id: uuid.UUID, project_id: uuid.UUID,
    flow_key: str, stage_ids: list[str],
) -> dict[str, Any]:
    """Dispatch each stage to its executor in order. Returns the per-phase report."""
    flow_run = Run(org_id=org_id, project_id=project_id, kind="flow",
                   lab="orchestrator", component_id=f"flow.{flow_key}",
                   status=RunStatus.RUNNING, params={"stages": stage_ids})
    session.add(flow_run)
    await session.flush()

    ctx = FlowContext(session=session, org_id=org_id, project_id=project_id, flow_run=flow_run)
    results: list[PhaseResult] = []
    for stage_id in stage_ids:
        executor = _EXECUTORS.get((flow_key, stage_id))
        if executor is None:
            results.append(PhaseResult(stage_id=stage_id, status="skipped",
                                       summary="no executor registered — do this stage by hand"))
            continue
        started = time.monotonic()
        try:
            result = await executor(ctx)
        except Exception as exc:  # one phase failing must not kill the whole flow
            log.exception("flow %s phase %s failed", flow_key, stage_id)
            await session.rollback()
            result = PhaseResult(stage_id=stage_id, status="failed", error=str(exc)[:300])
        result.artifacts.setdefault("duration_ms", round((time.monotonic() - started) * 1000))
        results.append(result)
        log.info("flow %s phase %-14s -> %s (%s)", flow_key, stage_id, result.status,
                 result.summary or result.error or "")

    statuses = {r.status for r in results}
    flow_run.status = RunStatus.SUCCEEDED if "failed" not in statuses else RunStatus.FAILED
    flow_run.params = {**flow_run.params,
                       "report": [{"stage": r.stage_id, "status": r.status} for r in results]}
    await session.commit()
    return {
        "flow_key": flow_key,
        "flow_run_id": str(flow_run.id),
        "status": flow_run.status.value,
        "stages": [
            {"id": r.stage_id, "status": r.status, "summary": r.summary, "run_id": r.run_id,
             "evidence": r.evidence, "artifacts": r.artifacts, "error": r.error}
            for r in results
        ],
        "gates_opened": sum(1 for r in results if r.status == "gated"),
        "evidence_total": sum(r.evidence for r in results),
    }


__all__ = ["FlowContext", "PhaseResult", "phase", "registered_stages", "open_gate", "run_flow"]
