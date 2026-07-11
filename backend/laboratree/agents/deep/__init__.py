"""DeepAgent — the executor of the cognitive architecture (Slice F).

Goal Interpreter → Meta Planner (recalls the Experience DB) → specialist sub-agents
(research/coding/analysis) sharing a Working Memory + the tool layer → converge → Critic →
Verification (numeric spot-check) → bounded refinement (max 1 revision round) → Reflection →
Experience DB, so the next similar goal plans better. Findings are Evidence-locked via the
``agent.deep_findings`` component with the full tree archived in the phase bucket.

Cost laws: narrow objectives skip the whole cortex (single ReAct pass, no goal/plan/reflect
calls); recall is a DB query digested to ≤500 chars; sub-agents share memory digests, never
raw scratchpads; a live token budget stops overruns honestly. No LLM key → a real GateTask.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ...core.config import settings
from ...core.jsonparse import loads_lenient
from ...core.storage import get_blob_store
from ...labs.agentic import llm as agentic_llm
from ...projects.models import ExperienceOutcome
from ..cognitive import (
    MAX_REFINE_TASKS,
    Goal,
    WorkingMemory,
    classify_goal_kind,
    digest_experiences,
    interpret_goal,
    meta_plan,
    recall_experiences,
    record_experience,
    reflect,
    specialist_persona,
    specialist_tools,
    tokens_spent,
    verify_findings,
)
from ..cognitive.reflection import Reflection, deterministic_reflection
from ..flow import FlowContext, PhaseResult, open_gate
from ..run_executor import execute_component
from ..tools import AgentTool, available_tools, toolbelt_prompt
from . import prompts
from .critic import audit_findings
from .planner import AgentPlan, PlannedTask, needs_planning
from .react import MAX_STEPS, OnStep, ReactResult, ToolRunner, react_loop

log = logging.getLogger(__name__)

SUB_AGENT_STEPS = 4
REFINE_STEPS = SUB_AGENT_STEPS // 2          # half budgets for the revision round (hard law)
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
    """Fulfil one phase through the cognitive loop. Returns a normal PhaseResult.

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
    # resolve the bucket NOW: a later rollback expires the anchor Run, and lazy-refreshing it
    # from sync code (_archive) would raise MissingGreenlet
    bucket_prefix = ctx.bucket(stage_id)

    async def _emit(step: dict[str, Any]) -> None:
        if on_step is not None:
            try:
                await on_step(step)
            except Exception:
                log.debug("on_step failed (non-fatal)")

    # --- goal + experience recall (the cortex; narrow asks bypass every LLM organ) ---
    broad = needs_planning(objective)
    goal = (interpret_goal(objective) if broad
            else Goal(text=objective, intent=objective[:300],
                      kind=classify_goal_kind(objective)))
    recalled = await _recall_safe(ctx, goal)
    experience_digest = digest_experiences(recalled)
    if recalled:
        await _emit({"kind": "recall", "count": len(recalled),
                     "lessons": experience_digest.splitlines()[1:4]})

    plan = meta_plan(goal, tools, experience_digest=experience_digest)
    memory = WorkingMemory()
    if plan.planned:
        await _emit({"kind": "plan",
                     "todos": [{"id": t.id, "objective": t.objective, "status": "pending",
                                "agent_type": t.agent_type} for t in plan.tasks]})

    task_results: list[ReactResult] = []
    task_notes: list[dict[str, Any]] = []
    base_note = experience_digest if (recalled and not plan.planned) else ""
    hit_token_budget = await _run_tasks(
        ctx, plan.tasks, tools=tools, runner=runner, persona=persona, memory=memory,
        base_note=base_note, results=task_results, notes=task_notes, emit=_emit,
        max_steps=SUB_AGENT_STEPS if plan.planned else max_steps, on_step=on_step)

    summary, findings = _converge(objective, plan.planned, task_results)
    pre_count = len(findings)
    findings, notes = _audit_and_verify(findings, task_results, _emit)
    await _emit_audit(notes, _emit)

    # --- bounded refinement: max ONE revision round (F5 — no loops-of-loops) ---
    reflection: Reflection | None = None
    refined = False
    failed_task = any(not n["ok"] for n in task_notes)
    needs_refinement = plan.planned and not hit_token_budget and (
        failed_task or (pre_count and len(notes) * 3 > pre_count))
    if needs_refinement:
        reflection = reflect(goal, task_notes, critic_dropped=len(notes))
        focus = "\n".join(
            [f"- task did not complete: {n['objective']}" for n in task_notes if not n["ok"]]
            + [f"- {note}" for note in notes[:3]])
        revision = meta_plan(goal, tools, focus=focus, max_tasks=MAX_REFINE_TASKS)
        if revision.planned:
            refined = True
            offset = len(plan.tasks)
            revision.tasks = [PlannedTask(id=offset + t.id, objective=t.objective,
                                          tools=t.tools, agent_type=t.agent_type)
                              for t in revision.tasks[:MAX_REFINE_TASKS]]
            await _emit({"kind": "refine", "reason": focus[:300],
                         "tasks": [{"id": t.id, "objective": t.objective,
                                    "agent_type": t.agent_type} for t in revision.tasks]})
            hit_token_budget = await _run_tasks(
                ctx, revision.tasks, tools=tools, runner=runner, persona=persona,
                memory=memory, base_note="", results=task_results, notes=task_notes,
                emit=_emit, max_steps=REFINE_STEPS, on_step=on_step)
            summary, findings = _converge(objective, True, task_results)
            findings, more_notes = _audit_and_verify(findings, task_results, _emit)
            notes.extend(more_notes)
            await _emit_audit(more_notes, _emit)
        else:
            notes.append("refinement skipped: revision planner unavailable")

    if reflection is None:
        # narrow runs and budget-exhausted runs never spend another call on reflection
        reflection = (reflect(goal, task_notes, critic_dropped=len(notes))
                      if plan.planned and not hit_token_budget
                      else deterministic_reflection(task_notes))
    await _record_safe(ctx, goal, plan, task_notes, findings, pre_count, reflection, refined)

    if hit_token_budget:
        summary = f"{summary} (stopped at the {settings.agent_token_budget}-token budget)"

    lock = await execute_component(
        ctx.session, org_id=ctx.org_id, project_id=ctx.project_id,
        component_id="agent.deep_findings",
        params={"findings": findings, "summary": summary,
                "model": ctx.state.get("model") or "reasoning"},
        inputs={}, lab="deep-agent",
    )
    trace_key = _archive(bucket_prefix, objective, plan, task_results, summary,
                         findings, notes, goal=goal, memory=memory, reflection=reflection,
                         recalled=len(recalled), refined=refined)

    return PhaseResult(
        stage_id=stage_id, status="succeeded",
        summary=f"🤖 deep agent: {summary}"[:300],
        run_id=str(lock.run.id), evidence=lock.evidence_count,
        artifacts={"agent": "deep", "planned": plan.planned, "tasks": len(task_results),
                   "steps": sum(len(r.scratchpad) for r in task_results),
                   "llm_calls": sum(r.llm_calls for r in task_results),
                   "critic_dropped": len(notes), "trace_key": trace_key,
                   "findings": findings[:10], "goal_kind": goal.kind,
                   "recalled": len(recalled), "refined": refined,
                   "tool_runs": ctx.state.get("deep_run_ids", [])},
    )


async def _run_tasks(
    ctx: FlowContext, tasks: list[PlannedTask], *, tools: dict[str, AgentTool],
    runner: ToolRunner, persona: str, memory: WorkingMemory, base_note: str,
    results: list[ReactResult], notes: list[dict[str, Any]], emit, max_steps: int, on_step,
) -> bool:
    """Run planned tasks as specialist sub-agents. Returns True if the token budget tripped."""
    for task in tasks:
        spent = await tokens_spent(ctx.session)
        if spent > settings.agent_token_budget:
            await emit({"kind": "budget", "tokens": spent,
                        "note": "token budget exhausted — remaining tasks skipped"})
            notes.append({"objective": task.objective, "agent_type": task.agent_type,
                          "ok": False, "summary": "skipped: token budget exhausted"})
            return True
        await emit({"kind": "todo", "id": task.id, "status": "running",
                    "objective": task.objective, "agent_type": task.agent_type})
        sub_tools = ({n: tools[n] for n in task.tools if n in tools}
                     or specialist_tools(task.agent_type, tools))
        context_note = "\n\n".join(p for p in (base_note, memory.digest()) if p)
        result = await react_loop(
            ctx, objective=task.objective, tools=sub_tools,
            system=prompts.react_system(
                toolbelt_prompt(sub_tools),
                persona=persona or specialist_persona(task.agent_type)),
            max_steps=max_steps, runner=runner, on_step=on_step,
            context_note=context_note,
        )
        results.append(result)
        memory.note(f"task-{task.id}", result.summary or "(no summary)",
                    source=f"task-{task.id}")
        notes.append({"objective": task.objective, "agent_type": task.agent_type,
                      "ok": not result.hit_budget and bool(result.summary),
                      "summary": result.summary})
        await emit({"kind": "todo", "id": task.id,
                    "status": "done" if not result.hit_budget else "budget",
                    "summary": result.summary[:200]})
    return False


def _audit_and_verify(findings, task_results, emit) -> tuple[list[dict[str, Any]], list[str]]:
    all_steps = [s for r in task_results for s in r.scratchpad]
    findings, critic_notes = audit_findings(findings, all_steps)
    findings, verify_notes = verify_findings(findings, all_steps)
    return findings, critic_notes + verify_notes


async def _emit_audit(notes: list[str], emit) -> None:
    if notes:
        await emit({"kind": "critic", "dropped": len(notes), "notes": notes[:5]})


async def _recall_safe(ctx: FlowContext, goal: Goal):
    try:
        return await recall_experiences(ctx.session, org_id=ctx.org_id, goal=goal)
    except Exception as exc:  # recall is an optimization, never a blocker
        log.info("experience recall failed: %s", exc)
        return []


async def _record_safe(ctx, goal, plan: AgentPlan, task_notes, findings, pre_count,
                       reflection: Reflection, refined: bool) -> None:
    failed_task = any(not n["ok"] for n in task_notes)
    if findings and not failed_task:
        outcome = ExperienceOutcome.SUCCEEDED
    elif findings:
        outcome = ExperienceOutcome.PARTIAL
    else:
        outcome = ExperienceOutcome.FAILED
    try:
        await record_experience(
            ctx.session, org_id=ctx.org_id, project_id=ctx.project_id, goal=goal,
            plan=[{"objective": t.objective, "agent_type": t.agent_type} for t in plan.tasks],
            outcome=outcome, score=len(findings) / max(1, pre_count),
            lessons=reflection.lessons, refined=refined)
    except Exception as exc:  # strategy memory must never fail the run
        log.warning("experience recording failed: %s", exc)
        try:
            await ctx.session.rollback()
        except Exception:
            log.debug("rollback after experience-record failure also failed")


def _converge(objective: str, planned: bool,
              results: list[ReactResult]) -> tuple[str, list[dict[str, Any]]]:
    if not planned or len(results) <= 1:
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


def _archive(bucket_prefix: str, objective, plan, results, summary, findings, notes, *,
             goal: Goal, memory: WorkingMemory, reflection: Reflection,
             recalled: int, refined: bool) -> str:
    trace_key = f"{bucket_prefix}trace.json"
    try:
        get_blob_store().put(trace_key, json.dumps({
            "objective": objective,
            "goal": {"intent": goal.intent, "kind": goal.kind,
                     "deliverable": goal.deliverable,
                     "success_criteria": goal.success_criteria},
            "recalled_experiences": recalled, "refined": refined,
            "planned": plan.planned,
            "plan": [{"id": t.id, "objective": t.objective, "tools": t.tools,
                      "agent_type": t.agent_type} for t in plan.tasks],
            "tasks": [{"summary": r.summary, "steps": r.scratchpad} for r in results],
            "working_memory": memory.snapshot(),
            "reflection": {"worked": reflection.worked, "failed": reflection.failed,
                           "lessons": reflection.lessons},
            "summary": summary, "findings": findings, "critic_notes": notes,
        }, default=str).encode())
    except Exception as exc:  # archiving must not fail the phase
        log.warning("deep agent trace archive to %s failed: %s", trace_key, exc)
        return ""
    return trace_key


__all__ = ["run_deep_agent", "scoped_tools", "BoundToolRunner", "JSON_SAFE_TOOLS",
           "SUB_AGENT_STEPS", "REFINE_STEPS", "MAX_STEPS"]
