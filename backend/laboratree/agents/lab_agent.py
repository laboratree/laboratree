"""Lab agents — every Lab is a conversational ReAct agent with its own tools and persona.

One registry (`LAB_AGENTS`) defines each Lab's persona, grounding-tool subset, and action tools
(thin wrappers over the Lab's existing pure functions). Execution rides the DeepAgent v2
orchestrator (plan → sub-agents → critic → Evidence lock) with steps persisted LIVE to an
``AgentRun`` row the UI polls. ``chat_turn`` is the conversational entry: it answers grounded
questions directly (hybrid retrieval), spawns an agent run for work, and — for the pipeline
agent — emits structured ``flow_ops`` the canvas applies. Keyless environments stay honest:
chat says the agent layer is unconfigured; deterministic pipeline commands still work.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.jsonparse import loads_lenient
from ..core.llm.context import use_llm_context
from ..labs.agentic import llm as agentic_llm
from ..projects.models import AgentRun, AgentRunStatus, AgentThread, Run, RunStatus
from .deep import JSON_SAFE_TOOLS, run_deep_agent, scoped_tools
from .flow import FlowContext
from .tools import AgentTool

log = logging.getLogger(__name__)

MAX_THREAD_MESSAGES = 10
MAX_MESSAGE_CHARS = 600
GROUNDING_DEFAULT = ("knowledge_search", "web_search", "research_search", "arxiv_search",
                     "reddit_search", "fetch_page", "crawl", "index_text", "storage_catalog",
                     "read_blob", "component_spec", "run_component", "dataset_overview",
                     "query_dataset_sql", "query_cypher")
# the Research Director wants the full discovery + retrieval belt, incl. open-access PDF pull
RESEARCH_GROUNDING = ("knowledge_search", "research_search", "web_search", "arxiv_search",
                      "reddit_search", "open_access_pdf", "fetch_page", "crawl", "index_text",
                      "storage_catalog", "read_blob", "component_spec", "dataset_overview")


@dataclass(frozen=True)
class LabAgentSpec:
    lab: str
    title: str
    persona: str
    grounding: tuple[str, ...] = GROUNDING_DEFAULT
    action_builders: tuple = ()          # callables returning {name: AgentTool}


def _llm_action(name: str, description: str, params_hint: str, fn, **inject) -> AgentTool:
    return AgentTool(name, description, params_hint,
                     partial(fn, complete_fn=agentic_llm.default_complete, **inject))


def _ideation_actions() -> dict[str, AgentTool]:
    from ..core.search import research_search
    from ..labs.ideation.coscientist import run_ideation
    from ..labs.ideation.evidence import gather_evidence

    return {
        "co_scientist": _llm_action(
            "co_scientist", "Generate + Elo-rank grounded hypotheses for a research goal.",
            '{"goal": str}', run_ideation),
        "evidence_hunt": AgentTool(
            "evidence_hunt", "Plan queries → search scholarship → cited evidence brief.",
            '{"hypothesis": str}',
            partial(gather_evidence, search_fn=research_search,
                    complete_fn=agentic_llm.default_complete)),
    }


def _collection_actions() -> dict[str, AgentTool]:
    from ..labs.collection.survey import design_questionnaire, detect_bias

    return {
        "design_questionnaire": _llm_action(
            "design_questionnaire", "Draft a sectioned questionnaire for a goal + audience.",
            '{"goal": str, "audience": str, "n": int}', design_questionnaire),
        "detect_bias": _llm_action(
            "detect_bias", "Flag leading/biased questions with suggested rewrites.",
            '{"questions": list}', detect_bias),
    }


def _field_actions() -> dict[str, AgentTool]:
    from ..labs.fieldwork.runtime import validate_structure

    return {
        "validate_survey": AgentTool(
            "validate_survey", "Validate a survey structure (sections/logic) — returns issues.",
            '{"structure": dict}',
            lambda structure: {"issues": validate_structure(structure) or ["valid"]}),
    }


def _qual_actions() -> dict[str, AgentTool]:
    from ..labs.qual.codebook import propose_codebook

    return {
        "propose_codebook": _llm_action(
            "propose_codebook", "Propose a thematic codebook from transcript text.",
            '{"texts": list}', propose_codebook),
    }


def _paper_actions() -> dict[str, AgentTool]:
    from ..labs.paper.card import generate_card

    return {
        "paper_card": _llm_action(
            "paper_card", "Generate a structured Paper Card from paper text.",
            '{"text": str}', generate_card),
    }


_ANALYTIC_PERSONA = ("You are the {title} of a provenance-locked research platform. Use "
                     "dataset_overview + component_spec BEFORE run_component so params use real "
                     "column names; every number you report must come from an observation.")


def _spec(lab: str, title: str, persona: str, *, grounding=GROUNDING_DEFAULT,
          builders=()) -> LabAgentSpec:
    return LabAgentSpec(lab=lab, title=title, persona=persona, grounding=tuple(grounding),
                        action_builders=tuple(builders))


LAB_AGENTS: dict[str, LabAgentSpec] = {s.lab: s for s in (
    _spec("ideation", "Research Director",
          "You are the Research Director of an autonomous Research OS. You DISCOVER, VERIFY, "
          "reason over, critique and SYNTHESIZE scholarly knowledge — you never merely extract. "
          "PLAYBOOK for a literature question: (1) call evidence_hunt(hypothesis=<the question>) "
          "FIRST — it plans queries, searches scholarship and returns a CITED brief with key "
          "findings; prefer it over raw research_search. (2) For the most important papers, pull "
          "the open-access PDF and READ it (open_access_pdf → fetch_page) to extract exact "
          "measures/claims from the text. (3) SYNTHESIZE from the abstracts and briefs you "
          "retrieved. Use focused 3-8 word search queries; for classics add 'seminal' or 'most "
          "cited'. CRITICAL: if a search returns papers with abstracts, you HAVE evidence — "
          "summarize what those papers measure; do NOT reply 'results are insufficient' when you "
          "have retrieved real papers. Every claim MUST cite an observation id — never fabricate "
          "a figure, source or result; when evidence is genuinely thin or conflicting, say so. "
          "Use co_scientist to turn a question into testable hypotheses.",
          grounding=RESEARCH_GROUNDING, builders=(_ideation_actions,)),
    _spec("papers", "Paper Lab agent",
          "You are the Paper Lab agent: understand, summarize, and interrogate research papers; "
          "always cite chunks you retrieved.", builders=(_paper_actions,)),
    _spec("signal", "Signal Lab agent",
          "You are the Signal Lab agent: make messy files analyzable and describe what the "
          "project's data actually contains."),
    _spec("collection", "Collection Lab agent",
          "You are the Collection Lab agent: design unbiased instruments and right-size "
          "samples.", builders=(_collection_actions,)),
    _spec("field", "Field Lab agent",
          "You are the Field Lab agent: guard fieldwork quality — instruments, quotas, "
          "fraud signals.", builders=(_field_actions,)),
    _spec("panel", "Panel agent",
          "You are the Panel agent: respondent recruitment, consent hygiene, panel health."),
    _spec("personas", "Persona Lab agent",
          "You are the Persona Lab agent: synthetic cohorts, their traits, memory and social "
          "dynamics; always label synthetic outputs."),
    _spec("qual", "Qual Studio agent",
          "You are the Qual Studio agent: transcripts, codebooks, verbatim quotes — never "
          "paraphrase a quote.", builders=(_qual_actions,)),
    _spec("insight", "Insight Lab agent", _ANALYTIC_PERSONA.format(title="Insight Lab agent")),
    _spec("modeling", "Modeling Lab agent", _ANALYTIC_PERSONA.format(title="Modeling Lab agent")),
    _spec("tabulation", "Tabulation agent", _ANALYTIC_PERSONA.format(title="Tabulation agent")),
    _spec("deliver", "Deliverables agent",
          "You are the Deliverables agent: every stat/table/quote in a report must bind real "
          "Evidence — refuse hand-typed numbers."),
    _spec("learning", "Learning Lab agent",
          "You are the Learning Lab agent: explain models and methods from zero, honestly."),
    _spec("pipeline", "Pipeline agent",
          "You are the Pipeline agent: help compose, modify and run research flows; prefer "
          "flow operations over prose when the user asks for changes."),
)}


def agent_tools_for(spec: LabAgentSpec) -> dict[str, AgentTool]:
    base = scoped_tools()  # availability-gated, JSON-safe
    tools = {n: base[n] for n in spec.grounding if n in base}
    for build in spec.action_builders:
        try:
            tools.update(build())
        except Exception as exc:  # a lab's optional deps must not kill its agent
            log.warning("lab %s action tools unavailable: %s", spec.lab, exc)
    return tools


# ----------------------------- agent-run execution -----------------------------

async def execute_agent_run(session: AsyncSession, agent_run_id: uuid.UUID) -> None:
    """Run one queued AgentRun to completion, persisting steps live (job body)."""
    agent_run = await session.get(AgentRun, agent_run_id)
    if agent_run is None or agent_run.status != AgentRunStatus.QUEUED:
        return
    spec = LAB_AGENTS.get(agent_run.lab)
    if spec is None:
        agent_run.status = AgentRunStatus.FAILED
        agent_run.summary = f"unknown lab: {agent_run.lab}"
        await session.commit()
        return

    anchor = Run(org_id=agent_run.org_id, project_id=agent_run.project_id, kind="agent",
                 lab=agent_run.lab, component_id=f"agent.{agent_run.lab}",
                 status=RunStatus.RUNNING, params={"task": agent_run.task})
    session.add(anchor)
    agent_run.status = AgentRunStatus.RUNNING
    await session.commit()

    ctx = FlowContext(session=session, org_id=agent_run.org_id,
                      project_id=agent_run.project_id, flow_run=anchor)

    async def _persist_step(step: dict[str, Any]) -> None:
        agent_run.steps = [*agent_run.steps, step]
        agent_run.llm_calls_used = agent_run.llm_calls_used + (1 if step.get("kind") == "tool" else 0)
        await session.commit()

    try:
        with use_llm_context(agent_run.lab, f"agent-run:{agent_run.id}",
                             project_id=agent_run.project_id, org_id=agent_run.org_id):
            result = await run_deep_agent(
                ctx, f"lab-{agent_run.lab}", agent_run.task,
                on_step=_persist_step, persona=spec.persona,
                tools=agent_tools_for(spec),
            )
    except Exception as exc:
        log.exception("agent run %s failed", agent_run.id)
        await session.rollback()
        agent_run.status = AgentRunStatus.FAILED
        agent_run.summary = str(exc)[:300]
        anchor.status = RunStatus.FAILED
        await session.commit()
        return

    agent_run.status = (AgentRunStatus.GATED if result.status == "gated"
                        else AgentRunStatus.SUCCEEDED)
    agent_run.summary = result.summary
    agent_run.findings = result.artifacts.get("findings", []) or []
    agent_run.trace_key = str(result.artifacts.get("trace_key", ""))
    agent_run.run_id = uuid.UUID(result.run_id) if result.run_id else None
    anchor.status = RunStatus.SUCCEEDED
    await session.commit()


# ----------------------------- conversational entry -----------------------------

_FLOW_OP_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\badd (?:an? )?agent stage (?:for |about )?(.+)", re.I), "add_agent"),
    (re.compile(r"\badd (?:a )?stage (?:for |about )?(.+)", re.I), "add_stage"),
    (re.compile(r"\bremove (?:the )?stage (.+)", re.I), "remove_stage"),
    (re.compile(r"\brun (?:the )?(?:whole )?flow\b", re.I), "supervise"),
]


def parse_flow_ops(message: str) -> list[dict[str, Any]]:
    """Deterministic pipeline commands — works keyless."""
    ops: list[dict[str, Any]] = []
    for pattern, op in _FLOW_OP_PATTERNS:
        m = pattern.search(message)
        if not m:
            continue
        if op == "add_agent":
            ops.append({"op": "add_stage", "kind": "agent", "label": m.group(1).strip()[:80],
                        "description": m.group(1).strip()})
        elif op == "add_stage":
            ops.append({"op": "add_stage", "kind": "manual", "label": m.group(1).strip()[:80],
                        "description": m.group(1).strip()})
        elif op == "remove_stage":
            ops.append({"op": "remove_stage", "label": m.group(1).strip()[:80]})
        elif op == "supervise":
            ops.append({"op": "supervise"})
    return ops


_ROUTER_SYSTEM = (
    "Route a user's chat message for a lab agent. Respond ONLY as JSON: "
    '{"mode": "answer"|"run", "reply": "<if answer: the grounded reply>"} — '
    'use "run" when the message asks for WORK (research, analysis, produce something); '
    '"answer" for questions your context already covers.'
)


@dataclass
class ChatReply:
    thread_id: str
    reply: str
    agent_run_id: str | None = None
    flow_ops: list[dict[str, Any]] = field(default_factory=list)


async def _thread(session, org_id, project_id, lab, thread_id) -> AgentThread:
    if thread_id:
        found = await session.get(AgentThread, uuid.UUID(str(thread_id)))
        if found is not None and found.org_id == org_id:
            return found
    thread = AgentThread(org_id=org_id, project_id=project_id, lab=lab, messages=[])
    session.add(thread)
    await session.flush()
    return thread


def _history_digest(messages: list[dict]) -> str:
    recent = messages[-MAX_THREAD_MESSAGES:]
    return "\n".join(f'{m.get("role", "?")}: {str(m.get("content", ""))[:MAX_MESSAGE_CHARS]}'
                     for m in recent)


async def chat_turn(
    session: AsyncSession, *, org_id: uuid.UUID, project_id: uuid.UUID,
    lab: str, thread_id: str | None, message: str,
) -> tuple[ChatReply, uuid.UUID | None]:
    """One conversational turn. Returns (reply, queued_agent_run_id_to_execute)."""
    spec = LAB_AGENTS[lab]
    thread = await _thread(session, org_id, project_id, lab, thread_id)
    now = datetime.now(UTC).isoformat()
    thread.messages = [*thread.messages, {"role": "user", "content": message[:2000], "ts": now}]

    # an active run on this thread → feedback queues after it (no concurrent mutation)
    active = next((m for m in reversed(thread.messages)
                   if m.get("agent_run_id") and m.get("active")), None)
    if active:
        run_row = await session.get(AgentRun, uuid.UUID(active["agent_run_id"]))
        if run_row is not None and run_row.status in (AgentRunStatus.QUEUED,
                                                      AgentRunStatus.RUNNING):
            reply = "The agent is still working on the previous task — your feedback is noted " \
                    "in the thread and will shape the next run."
            thread.messages = [*thread.messages, {"role": "agent", "content": reply, "ts": now}]
            await session.commit()
            return ChatReply(thread_id=str(thread.id), reply=reply), None
        active["active"] = False

    flow_ops = parse_flow_ops(message) if lab == "pipeline" else []
    if flow_ops:
        reply = f"Applying {len(flow_ops)} flow change(s) to the canvas."
        thread.messages = [*thread.messages,
                           {"role": "agent", "content": reply, "flow_ops": flow_ops, "ts": now}]
        await session.commit()
        return ChatReply(thread_id=str(thread.id), reply=reply, flow_ops=flow_ops), None

    if not agentic_llm.is_configured():
        reply = ("The agent layer isn't configured (no LLM key). Deterministic runs still work "
                 "— use ⚡ Run all phases, or add a key (Hermes/OpenRouter or Azure) to chat.")
        thread.messages = [*thread.messages, {"role": "agent", "content": reply, "ts": now}]
        await session.commit()
        return ChatReply(thread_id=str(thread.id), reply=reply), None

    history = _history_digest(thread.messages)
    grounding = await _ground(session, org_id, project_id, message)
    raw = agentic_llm.default_complete(
        _ROUTER_SYSTEM,
        f"LAB: {spec.title}\nHISTORY:\n{history}\n\nGROUNDING:\n{grounding}\n\n"
        f"MESSAGE:\n{message}",
        role="generation")
    routed = loads_lenient(raw) or {}

    if routed.get("mode") == "answer" and routed.get("reply"):
        reply = str(routed["reply"])[:2000]
        thread.messages = [*thread.messages, {"role": "agent", "content": reply, "ts": now}]
        await session.commit()
        return ChatReply(thread_id=str(thread.id), reply=reply), None

    # spawn an agent run; the task carries the conversation so feedback genuinely redirects it
    task = f"{message}\n\n(Conversation so far:\n{history})"
    agent_run = AgentRun(org_id=org_id, project_id=project_id, lab=lab, task=task,
                         status=AgentRunStatus.QUEUED)
    session.add(agent_run)
    await session.flush()
    reply = f"On it — the {spec.title} is working. Watch the live steps below."
    thread.messages = [*thread.messages,
                       {"role": "agent", "content": reply,
                        "agent_run_id": str(agent_run.id), "active": True, "ts": now}]
    await session.commit()
    return ChatReply(thread_id=str(thread.id), reply=reply,
                     agent_run_id=str(agent_run.id)), agent_run.id


async def _ground(session, org_id, project_id, query: str) -> str:
    try:
        from ..core.retrieval import hybrid_search

        hits = await hybrid_search(session, org_id=org_id, project_id=project_id,
                                   query=query, k=3)
        return "\n".join(f"[{h.source} #{h.ordinal}] {h.text[:300]}" for h in hits) or "(none)"
    except Exception:
        return "(retrieval unavailable)"


async def list_threads(session, org_id, project_id, lab) -> list[AgentThread]:
    return list((await session.execute(
        select(AgentThread).where(AgentThread.org_id == org_id,
                                  AgentThread.project_id == project_id,
                                  AgentThread.lab == lab)
        .order_by(AgentThread.updated_at.desc()).limit(10)
    )).scalars().all())


__all__ = ["LAB_AGENTS", "LabAgentSpec", "ChatReply", "chat_turn", "execute_agent_run",
           "agent_tools_for", "parse_flow_ops", "list_threads", "JSON_SAFE_TOOLS"]
