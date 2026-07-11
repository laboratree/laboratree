"""DeepAgent v2 — plan → todo list → ReAct sub-agents → critic → converge.

The orchestrator the Supervisor spawns for phases nothing else covers (and the engine Lab
agents delegate to). Broad objectives are decomposed by the meta-planner into a todo list;
each task runs as its own ReAct sub-agent (scoped tools, sub-budget) sequentially with the
plan's progress recorded live; a synthesis pass merges findings, the critic drops anything
the observations don't support, and the survivors are Evidence-locked via the
``agent.deep_findings`` component with the full tree archived in the phase bucket.
No LLM key → a real GateTask (honest hand-off), never fabrication.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ...core.jsonparse import loads_lenient
from ...core.storage import get_blob_store
from ...labs.agentic import llm as agentic_llm
from ..flow import FlowContext, PhaseResult, open_gate
from ..run_executor import execute_component
from ..tools import AgentTool, available_tools, toolbelt_prompt
from . import prompts
from .critic import audit_findings
from .planner import plan_objective
from .react import MAX_STEPS, OnStep, ReactResult, ToolRunner, react_loop

log = logging.getLogger(__name__)

SUB_AGENT_STEPS = 4
# tools whose args survive a JSON round-trip (bytes-taking tools stay out of ReAct loops)
JSON_SAFE_TOOLS = frozenset({
    "web_search", "research_search", "arxiv_search", "reddit_search",
    "open_access_pdf", "fetch_page", "crawl", "knowledge_search", "index_text",
    "component_spec", "dataset_overview", "query_dataset_sql", "query_cypher",
    "storage_catalog", "read_blob", "run_component", "sandbox_run",
})


class BoundToolRunner(ToolRunner):
    """ToolRunner that binds context-needing tools (run_component, retrieval, storage)."""

    async def _invoke(self, tool: AgentTool, args: dict[str, Any]) -> Any:
        from .. import tools as belt

        if tool.name == "run_component":
            result = await execute_component(
                self.ctx.session, org_id=self.ctx.org_id, project_id=self.ctx.project_id,
                component_id=str(args.get("component_id", "")),
                params=dict(args.get("params") or {}),
                inputs={"dataset": self.ctx.state["df"]} if "df" in self.ctx.state else {},
                lab="deep-agent",
            )
            self.ctx.state.setdefault("deep_run_ids", []).append(str(result.run.id))
            return {"run_id": str(result.run.id), "evidence": result.evidence_count,
                    "outputs": json.dumps(result.outputs, default=str)[:1200]}
        if tool.name in belt.CONTEXT_BOUND_TOOLS:
            return await belt.call_context_tool(self.ctx, tool.name, args)
        return await super()._invoke(tool, args)


def scoped_tools(names: list[str] | None = None) -> dict[str, AgentTool]:
    base = {n: t for n, t in available_tools().items() if n in JSON_SAFE_TOOLS}
    if names:
        chosen = {n: base[n] for n in names if n in base}
        if chosen:
            return chosen
    return base


async def run_deep_agent(
    ctx: FlowContext, stage_id: str, objective: str, *,
    max_steps: int = MAX_STEPS, on_step: OnStep | None = None,
    persona: str = "", tools: dict[str, AgentTool] | None = None,
) -> PhaseResult:
    """Fulfil one phase with planning + delegated sub-agents. Returns a normal PhaseResult.

    ``tools`` lets a Lab agent inject its scoped belt (grounding subset + lab actions);
    default is the full JSON-safe toolbelt.
    """
    if not agentic_llm.is_configured():
        return await open_gate(
            ctx, stage_id=stage_id,
            title=f"Deep agent needed for '{stage_id}'",
            description="This phase requires the agent layer — configure an LLM key "
                        "(Hermes/OpenRouter or Azure) or complete the phase manually. "
                        f"Objective: {objective}",
            payload={"objective": objective},
        )

    tools = tools or scoped_tools()
    runner = BoundToolRunner(ctx=ctx, tools=tools)
    plan = plan_objective(objective, tools)

    async def _emit(step: dict[str, Any]) -> None:
        if on_step is not None:
            try:
                await on_step(step)
            except Exception:
                log.debug("on_step failed (non-fatal)")

    task_results: list[ReactResult] = []
    notes: list[str] = []
    if plan.planned:
        await _emit({"kind": "plan",
                     "todos": [{"id": t.id, "objective": t.objective, "status": "pending"}
                               for t in plan.tasks]})

    for task in plan.tasks:
        await _emit({"kind": "todo", "id": task.id, "status": "running",
                     "objective": task.objective})
        task_tools = {n: tools[n] for n in task.tools if n in tools} or tools
        result = await react_loop(
            ctx, objective=task.objective, tools=task_tools,
            system=prompts.react_system(toolbelt_prompt(task_tools), persona=persona),
            max_steps=SUB_AGENT_STEPS if plan.planned else max_steps,
            runner=runner, on_step=on_step,
        )
        task_results.append(result)
        await _emit({"kind": "todo", "id": task.id,
                     "status": "done" if not result.hit_budget else "budget",
                     "summary": result.summary[:200]})

    summary, findings = _converge(objective, plan.planned, task_results)
    all_steps = [s for r in task_results for s in r.scratchpad]
    findings, dropped = audit_findings(findings, all_steps)
    notes.extend(dropped)
    if dropped:
        await _emit({"kind": "critic", "dropped": len(dropped), "notes": dropped[:5]})

    lock = await execute_component(
        ctx.session, org_id=ctx.org_id, project_id=ctx.project_id,
        component_id="agent.deep_findings",
        params={"findings": findings, "summary": summary,
                "model": ctx.state.get("model") or "reasoning"},
        inputs={}, lab="deep-agent",
    )
    trace_key = _archive(ctx, stage_id, objective, plan, task_results, summary,
                         findings, notes)

    return PhaseResult(
        stage_id=stage_id, status="succeeded",
        summary=f"🤖 deep agent: {summary}"[:300],
        run_id=str(lock.run.id), evidence=lock.evidence_count,
        artifacts={"agent": "deep", "planned": plan.planned, "tasks": len(plan.tasks),
                   "steps": sum(len(r.scratchpad) for r in task_results),
                   "llm_calls": sum(r.llm_calls for r in task_results),
                   "critic_dropped": len(notes), "trace_key": trace_key,
                   "findings": findings[:10],
                   "tool_runs": ctx.state.get("deep_run_ids", [])},
    )


def _converge(objective: str, planned: bool,
              results: list[ReactResult]) -> tuple[str, list[dict[str, Any]]]:
    if not planned or len(results) == 1:
        only = results[0] if results else ReactResult("no tasks ran", [], [])
        return only.summary, only.findings
    merged = [f for r in results for f in r.findings]
    try:
        raw = agentic_llm.default_complete(
            prompts.synthesis_system(),
            f"OBJECTIVE:\n{objective}\n\nTASK SUMMARIES:\n"
            + "\n".join(f"- {r.summary}" for r in results)
            + f"\n\nFINDINGS:\n{json.dumps(merged, default=str)[:6000]}",
            role="reasoning")
        parsed = loads_lenient(raw) or {}
        findings = [f for f in (parsed.get("findings") or []) if isinstance(f, dict)]
        if findings:
            return str(parsed.get("summary", ""))[:1000], findings
    except Exception as exc:
        log.info("synthesis failed (%s); using concatenated findings", exc)
    return " ".join(r.summary for r in results)[:1000], merged


def _archive(ctx, stage_id, objective, plan, results, summary, findings, notes) -> str:
    trace_key = f"{ctx.bucket(stage_id)}trace.json"
    try:
        get_blob_store().put(trace_key, json.dumps({
            "objective": objective, "planned": plan.planned,
            "plan": [{"id": t.id, "objective": t.objective, "tools": t.tools}
                     for t in plan.tasks],
            "tasks": [{"summary": r.summary, "steps": r.scratchpad} for r in results],
            "summary": summary, "findings": findings, "critic_notes": notes,
        }, default=str).encode())
    except Exception as exc:  # archiving must not fail the phase
        log.warning("deep agent %s: trace archive failed: %s", stage_id, exc)
        return ""
    return trace_key


__all__ = ["run_deep_agent", "scoped_tools", "BoundToolRunner", "JSON_SAFE_TOOLS",
           "SUB_AGENT_STEPS", "MAX_STEPS"]
