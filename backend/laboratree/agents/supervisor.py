"""Supervisor agent — the durable LangGraph orchestration over every flow.

One supervisor drives the whole pipeline: it walks the compiled stage list, dispatching each
stage to its **Lab agent** (the registered phase executor, tagged with its owning Lab), spawning
the **DeepAgent** for stages nothing covers, and pausing at **human gates** with LangGraph
``interrupt`` — the run checkpoints (Postgres when available) and resumes days later exactly
where it stopped. Graph state stays JSON-serializable; heavy objects (dataframes, ORM rows) are
rehydrated per super-step from ids in the ``carry`` dict plus the deterministic ``_ensure_*``
helpers the executors already use.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from ..core.config import settings
from ..core.db.postgres import sessionmaker
from ..projects.models import GateStatus, GateTask, Run, RunStatus
from . import flow as flow_engine
from .deep import run_deep_agent
from .flow import FlowContext, PhaseResult

log = logging.getLogger(__name__)

# JSON-safe scraps of FlowContext.state carried across checkpoints (rehydration seeds)
CARRY_KEYS = ("survey_id", "cohort_id", "share_path", "run_ids", "research_frame")


class SupervisorState(TypedDict, total=False):
    flow_key: str
    stage_ids: list[str]
    objectives: dict[str, str]        # stage_id -> objective (for deep-agent stages)
    cursor: int
    report: list[dict[str, Any]]
    carry: dict[str, Any]
    org_id: str
    project_id: str
    flow_run_id: str
    pending_gate: dict[str, Any] | None


async def _flow_context(state: SupervisorState, session: Any) -> FlowContext:
    flow_run = await session.get(Run, uuid.UUID(state["flow_run_id"]))
    ctx = FlowContext(session=session, org_id=uuid.UUID(state["org_id"]),
                      project_id=uuid.UUID(state["project_id"]), flow_run=flow_run)
    ctx.state.update(state.get("carry") or {})
    return ctx


def _carry_from(ctx: FlowContext) -> dict[str, Any]:
    return {k: ctx.state[k] for k in CARRY_KEYS if k in ctx.state}


async def run_until_gate(state: SupervisorState) -> dict[str, Any]:
    """Execute stages from the cursor until a gate opens or the flow ends (one super-step)."""
    flow_key = state["flow_key"]
    report = list(state.get("report") or [])
    cursor = int(state.get("cursor") or 0)
    stage_ids = state["stage_ids"]
    pending_gate: dict[str, Any] | None = None

    async with sessionmaker()() as session:
        ctx = await _flow_context(state, session)
        while cursor < len(stage_ids):
            stage_id = stage_ids[cursor]
            entry = flow_engine.get_executor(flow_key, stage_id)
            try:
                if entry is not None:
                    executor, lab = entry
                    result = await executor(ctx)
                    result.lab = result.lab or lab
                else:
                    objective = (state.get("objectives") or {}).get(
                        stage_id, f"Fulfil the research phase '{stage_id}' for this project "
                                  f"using the available tools; ground every claim.")
                    result = await run_deep_agent(ctx, stage_id, objective)
                    result.lab = result.lab or "deep-agent"
            except Exception as exc:  # a phase failure is recorded, never fatal to the flow
                log.exception("supervised flow %s phase %s failed", flow_key, stage_id)
                await session.rollback()
                result = PhaseResult(stage_id=stage_id, status="failed", error=str(exc)[:300])
            report.append(result.as_dict())
            log.info("supervisor %s phase %-14s -> %s", flow_key, stage_id, result.status)
            cursor += 1
            if result.status == "gated":
                pending_gate = {"stage_id": stage_id,
                                "gate_id": result.artifacts.get("gate_id"),
                                "summary": result.summary}
                break
        await session.commit()
        carry = _carry_from(ctx)

    return {"report": report, "cursor": cursor, "carry": carry, "pending_gate": pending_gate}


async def gate(state: SupervisorState) -> dict[str, Any]:
    """Pause for the human: interrupt checkpoints the run; resume delivers the decision."""
    decision = interrupt(state.get("pending_gate") or {})
    gate_info = state.get("pending_gate") or {}
    approved = bool(decision.get("approved", False))
    async with sessionmaker()() as session:
        if gate_info.get("gate_id"):
            gate_task = await session.get(GateTask, uuid.UUID(str(gate_info["gate_id"])))
            if gate_task is not None:
                gate_task.status = GateStatus.APPROVED if approved else GateStatus.REJECTED
                gate_task.response = {"approved": approved,
                                      "note": str(decision.get("note", ""))[:500]}
                await session.commit()
    report = list(state.get("report") or [])
    report.append({"id": f"gate:{gate_info.get('stage_id')}", "lab": "human",
                   "status": "approved" if approved else "rejected",
                   "summary": str(decision.get("note", "")) or "human decision recorded",
                   "run_id": None, "evidence": 0, "artifacts": gate_info, "error": None})
    return {"report": report, "pending_gate": None}


def _after_run(state: SupervisorState) -> str:
    if state.get("pending_gate"):
        return "gate"
    return END


def _after_gate(state: SupervisorState) -> str:
    if int(state.get("cursor") or 0) < len(state.get("stage_ids") or []):
        return "run"
    return END


def build_supervisor(checkpointer: Any | None = None):
    g = StateGraph(SupervisorState)
    g.add_node("run", run_until_gate)
    g.add_node("gate", gate)
    g.add_edge(START, "run")
    g.add_conditional_edges("run", _after_run, {"gate": "gate", END: END})
    g.add_conditional_edges("gate", _after_gate, {"run": "run", END: END})
    return g.compile(checkpointer=checkpointer or MemorySaver())


# ----------------------------- durable singleton -----------------------------

_checkpointer: Any | None = None
_graph: Any | None = None


def _postgres_dsn() -> str:
    return (f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")


async def get_supervisor():
    """Compiled graph with the best available checkpointer (Postgres → Memory fallback)."""
    global _checkpointer, _graph
    if _graph is not None:
        return _graph
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        pool = AsyncConnectionPool(
            _postgres_dsn(), open=False, max_size=4,
            kwargs={"autocommit": True, "row_factory": dict_row},
        )
        await pool.open()
        saver = AsyncPostgresSaver(pool)
        await saver.setup()
        _checkpointer = saver
        log.info("supervisor checkpointer: Postgres (durable)")
    except Exception as exc:  # dev/test hosts without the driver or DB stay functional
        log.warning("supervisor falling back to in-memory checkpoints: %s", exc)
        _checkpointer = MemorySaver()
    _graph = build_supervisor(_checkpointer)
    return _graph


def reset_supervisor() -> None:
    """Test hook — drop the cached graph/checkpointer."""
    global _checkpointer, _graph
    _checkpointer = None
    _graph = None


# ----------------------------- API-facing helpers -----------------------------

def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def _payload(result: dict[str, Any], thread_id: str) -> dict[str, Any]:
    interrupted = "__interrupt__" in result
    report = result.get("report") or []
    return {
        "thread_id": thread_id,
        "flow_run_id": result.get("flow_run_id"),
        "status": "paused" if interrupted else "completed",
        "pending_gate": result.get("pending_gate"),
        "stages": report,
        "labs": sorted({r.get("lab") for r in report if r.get("lab")}),
        "evidence_total": sum(int(r.get("evidence") or 0) for r in report),
        "gates_opened": sum(1 for r in report if r.get("status") == "gated"),
    }


async def supervise(
    session: Any, *, org_id: uuid.UUID, project_id: uuid.UUID,
    flow_key: str, stage_ids: list[str], objectives: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Start a supervised run; returns at the first gate or on completion."""
    flow_run = Run(org_id=org_id, project_id=project_id, kind="flow",
                   lab="supervisor", component_id=f"flow.{flow_key}",
                   status=RunStatus.RUNNING, params={"stages": stage_ids, "supervised": True})
    session.add(flow_run)
    await session.commit()

    thread_id = str(uuid.uuid4())
    graph = await get_supervisor()
    result = await graph.ainvoke(
        SupervisorState(flow_key=flow_key, stage_ids=stage_ids,
                        objectives=objectives or {}, cursor=0, report=[], carry={},
                        org_id=str(org_id), project_id=str(project_id),
                        flow_run_id=str(flow_run.id), pending_gate=None),
        config=_config(thread_id),
    )
    payload = _payload(result, thread_id)
    if payload["status"] == "completed":
        await _finish_flow_run(flow_run.id, payload)
    return payload


async def resume(thread_id: str, *, approved: bool, note: str = "") -> dict[str, Any]:
    """Deliver a human decision to a paused run and continue it."""
    graph = await get_supervisor()
    result = await graph.ainvoke(
        Command(resume={"approved": approved, "note": note}), config=_config(thread_id))
    payload = _payload(result, thread_id)
    flow_run_id = (await graph.aget_state(_config(thread_id))).values.get("flow_run_id")
    if payload["status"] == "completed" and flow_run_id:
        await _finish_flow_run(uuid.UUID(flow_run_id), payload)
    return payload


async def thread_state(thread_id: str) -> dict[str, Any] | None:
    graph = await get_supervisor()
    snapshot = await graph.aget_state(_config(thread_id))
    if not snapshot or not snapshot.values:
        return None
    values = dict(snapshot.values)
    paused = bool(snapshot.next)
    return {"thread_id": thread_id, "status": "paused" if paused else "completed",
            "pending_gate": values.get("pending_gate"),
            "stages": values.get("report") or [], "cursor": values.get("cursor")}


async def _finish_flow_run(flow_run_id: uuid.UUID, payload: dict[str, Any]) -> None:
    async with sessionmaker()() as session:
        flow_run = await session.get(Run, flow_run_id)
        if flow_run is None:
            return
        failed = any(s.get("status") == "failed" for s in payload["stages"])
        flow_run.status = RunStatus.FAILED if failed else RunStatus.SUCCEEDED
        flow_run.params = {**flow_run.params, "report": [
            {"stage": s.get("id"), "status": s.get("status"), "lab": s.get("lab")}
            for s in payload["stages"]]}
        await session.commit()


__all__ = ["SupervisorState", "build_supervisor", "get_supervisor", "reset_supervisor",
           "supervise", "resume", "thread_state"]
