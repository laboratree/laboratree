"""DeepAgent — the gap-filler the Supervisor spawns for phases nothing else can run.

A ReAct loop over the typed toolbelt: the LLM (reasoning role — Hermes when configured) sees the
tool catalog + objective + a running scratchpad, picks one tool per step as JSON, observes the
result, and finishes with cited findings. Provenance rules hold throughout: component calls go
through the Evidence-locked run executor, the finish step locks findings via the
``agent.deep_findings`` component, and the full step trace is stored in the phase's artifact
bucket. No LLM key → a real GateTask (honest hand-off), never fabrication.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from ...core.jsonparse import loads_lenient
from ...core.storage import get_blob_store
from ...labs.agentic import llm as agentic_llm
from ..flow import FlowContext, PhaseResult, open_gate
from ..run_executor import execute_component
from ..tools import available_tools, toolbelt_prompt
from . import prompts

log = logging.getLogger(__name__)

MAX_STEPS = 8
MAX_OBSERVATION_CHARS = 1500
# tools whose args survive a JSON round-trip (bytes-taking tools stay out of the ReAct loop)
JSON_SAFE_TOOLS = frozenset({
    "web_search", "research_search", "arxiv_search", "reddit_search",
    "open_access_pdf", "run_component", "sandbox_run",
})


def _observation(value: Any) -> str:
    try:
        text = json.dumps(value, default=str)
    except Exception:
        text = str(value)
    return text[:MAX_OBSERVATION_CHARS]


async def _call_tool(ctx: FlowContext, name: str, args: dict[str, Any]) -> Any:
    if name == "run_component":
        result = await execute_component(
            ctx.session, org_id=ctx.org_id, project_id=ctx.project_id,
            component_id=str(args.get("component_id", "")),
            params=dict(args.get("params") or {}),
            inputs={"dataset": ctx.state["df"]} if "df" in ctx.state else {},
            lab="deep-agent",
        )
        ctx.state.setdefault("deep_run_ids", []).append(str(result.run.id))
        return {"run_id": str(result.run.id), "evidence": result.evidence_count,
                "outputs": _observation(result.outputs)}

    tool = available_tools().get(name)
    if tool is None:
        return {"error": f"unknown or unavailable tool: {name}"}
    return await asyncio.to_thread(tool.fn, **args)


async def run_deep_agent(
    ctx: FlowContext, stage_id: str, objective: str, *, max_steps: int = MAX_STEPS
) -> PhaseResult:
    """Fulfil one phase with tools + reasoning. Returns a normal PhaseResult."""
    if not agentic_llm.is_configured():
        return await open_gate(
            ctx, stage_id=stage_id,
            title=f"Deep agent needed for '{stage_id}'",
            description="This phase has no built-in executor and requires the agent layer — "
                        "configure an LLM key (Hermes/OpenRouter or Azure) or complete the "
                        f"phase manually. Objective: {objective}",
            payload={"objective": objective},
        )

    tools = {n: t for n, t in available_tools().items() if n in JSON_SAFE_TOOLS}
    system = prompts.react_system(toolbelt_prompt(tools))
    scratchpad: list[dict[str, Any]] = []
    summary, findings = "", []

    for step in range(1, max_steps + 1):
        raw = agentic_llm.default_complete(
            system, prompts.react_turn(objective, scratchpad), role="reasoning")
        decision = loads_lenient(raw) or {}
        if "finish" in decision:
            summary = str(decision.get("finish", ""))[:1000]
            findings = [f for f in (decision.get("findings") or []) if isinstance(f, dict)]
            break
        tool_name = str(decision.get("tool", ""))
        args = dict(decision.get("args") or {})
        try:
            observation = await _call_tool(ctx, tool_name, args)
        except Exception as exc:  # a failing tool is an observation, not a crash
            log.warning("deep agent %s step %d tool %s failed: %s", stage_id, step, tool_name, exc)
            observation = {"error": str(exc)[:300]}
        scratchpad.append({"step": step, "thought": str(decision.get("thought", ""))[:400],
                           "tool": tool_name, "args": _observation(args),
                           "observation": _observation(observation)})
    else:
        summary = f"stopped at the {max_steps}-step budget without finishing"

    # Evidence-lock the conclusions + archive the full trace in the phase bucket
    lock = await execute_component(
        ctx.session, org_id=ctx.org_id, project_id=ctx.project_id,
        component_id="agent.deep_findings",
        params={"findings": findings, "summary": summary,
                "model": ctx.state.get("model") or "reasoning"},
        inputs={}, lab="deep-agent",
    )
    trace_key = f"{ctx.bucket(stage_id)}trace.json"
    try:
        get_blob_store().put(trace_key, json.dumps(
            {"objective": objective, "steps": scratchpad, "summary": summary,
             "findings": findings}, default=str).encode())
    except Exception as exc:  # archiving must not fail the phase
        log.warning("deep agent %s: trace archive failed: %s", stage_id, exc)
        trace_key = ""

    return PhaseResult(
        stage_id=stage_id, status="succeeded",
        summary=f"🤖 deep agent: {summary}"[:300],
        run_id=str(lock.run.id), evidence=lock.evidence_count,
        artifacts={"agent": "deep", "steps": len(scratchpad), "trace_key": trace_key,
                   "tool_runs": ctx.state.get("deep_run_ids", [])},
    )


__all__ = ["run_deep_agent", "MAX_STEPS", "JSON_SAFE_TOOLS"]
