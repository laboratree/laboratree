"""Cognitive architecture (Slice F): goal, recall-informed planning, specialists, working
memory, reflection→experience, numeric verification, bounded refinement, run hygiene."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from laboratree.main import app
from sqlalchemy import text as sql_text

GOAL_OK = json.dumps({"intent": "study the market", "deliverable": "brief"})
REFLECT_OK = json.dumps({"worked": ["search"], "failed": [],
                         "lessons": ["triangulate sources before concluding"]})
CRITIC_ALL_OK = json.dumps({"verdicts": [{"index": 0, "supported": True}]})
BROAD_OBJECTIVE = ("research the education market thoroughly: gather credible evidence and "
                   "then compare providers and pricing end to end")


@pytest.fixture(autouse=True)
def _keyed_llm(monkeypatch):
    from laboratree.core.config import settings
    from laboratree.core.llm import get_llm

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    get_llm.cache_clear()
    yield
    get_llm.cache_clear()


def _script(monkeypatch, responses: list[str], prompts_out: list[str] | None = None):
    from laboratree.labs.agentic import llm as agentic_llm

    it = iter(responses)

    def _fake(system: str, prompt: str, **kw) -> str:
        if prompts_out is not None:
            prompts_out.append(f"{system}\n---\n{prompt}")
        return next(it)

    monkeypatch.setattr(agentic_llm, "default_complete", _fake)


async def _seed_context(session):
    """org + project + anchor Run → a FlowContext run_deep_agent can use directly."""
    from laboratree.agents.flow import FlowContext
    from laboratree.projects.models import Run, RunStatus

    org, proj = uuid.uuid4(), uuid.uuid4()
    await session.execute(sql_text(
        "INSERT INTO organizations (id, name, slug, created_at, updated_at) "
        "VALUES (:i, 't', 't-' || :sfx, now(), now())"), {"i": org, "sfx": str(org)[:8]})
    await session.execute(sql_text(
        "INSERT INTO projects (id, org_id, name, description, created_at, updated_at) "
        "VALUES (:i, :o, 'p', '', now(), now())"), {"i": proj, "o": org})
    anchor = Run(org_id=org, project_id=proj, kind="agent", lab="deep-agent",
                 component_id="agent.test", status=RunStatus.RUNNING, params={})
    session.add(anchor)
    await session.flush()
    return FlowContext(session=session, org_id=org, project_id=proj, flow_run=anchor)


# ----------------------------- organs (unit) -----------------------------

def test_goal_interpretation_falls_back_deterministically_keyless(monkeypatch):
    from laboratree.agents.cognitive import classify_goal_kind, interpret_goal
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "openai_api_key", "")           # keyless
    goal = interpret_goal("build a model to predict student dropout")
    assert goal.intent.startswith("build a model")
    assert goal.kind == "modeling"
    assert classify_goal_kind("crawl the ministry website for job posts") == "web"
    assert classify_goal_kind("say hello") == "general"


def test_verification_drops_metric_mismatch_deterministically():
    from laboratree.agents.cognitive import verify_findings

    scratchpad = [{"kind": "tool", "step": 1,
                   "observation": "attendance rose 12.5% after the subsidy (n=2400)"}]
    findings = [
        {"claim": "attendance rose 12.5% after the subsidy"},     # matches an observation
        {"claim": "attendance rose 47.3% after the subsidy"},     # fabricated metric
        {"claim": "the subsidy improved attendance"},             # numberless -> passes
    ]
    survivors, notes = verify_findings(findings, scratchpad)
    assert [f["claim"] for f in survivors] == [findings[0]["claim"], findings[2]["claim"]]
    assert len(notes) == 1 and "47.3" in notes[0]


def test_specialists_get_exactly_their_tool_scopes():
    from laboratree.agents.cognitive import SPECIALIST_TOOLS, specialist_tools
    from laboratree.agents.tools import AgentTool

    every = {n: AgentTool(n, "d", "{}", lambda: None)
             for scope in SPECIALIST_TOOLS.values() for n in scope}
    every["web_search"] = AgentTool("web_search", "d", "{}", lambda: None)
    coding = specialist_tools("coding", every)
    assert "sandbox_run" in coding and "query_dataset_sql" in coding
    assert "web_search" not in coding and "crawl" not in coding
    research = specialist_tools("research", every)
    assert "web_search" in research and "sandbox_run" not in research
    assert specialist_tools("unknown", every) == every            # unknown type -> full belt


def test_meta_plan_cites_experience_and_types_tasks(monkeypatch):
    from laboratree.agents.cognitive import Goal, meta_plan
    from laboratree.agents.tools import AgentTool

    prompts: list[str] = []
    _script(monkeypatch, [json.dumps({"tasks": [
        {"objective": "crosstab the panel first", "agent_type": "analysis", "tools": []},
        {"objective": "then search for benchmarks", "agent_type": "research", "tools": []},
    ]})], prompts)
    tools = {"web_search": AgentTool("web_search", "d", "{}", lambda: None)}
    digest = "PAST EXPERIENCE (from earlier runs):\n- worked: [analysis] crosstab-first beat model-first"
    plan = meta_plan(Goal(text=BROAD_OBJECTIVE, intent="compare providers", kind="analysis"),
                     tools, experience_digest=digest)
    assert plan.planned and [t.agent_type for t in plan.tasks] == ["analysis", "research"]
    assert "crosstab-first beat model-first" in prompts[0]        # recall reached the planner

    # narrow goal without a focus never spends a planning call (cost law)
    narrow = meta_plan(Goal(text="say hello", intent="say hello"), tools)
    assert not narrow.planned and narrow.tasks[0].agent_type == "research"


def test_working_memory_is_bounded_lru():
    from laboratree.agents.cognitive import WorkingMemory
    from laboratree.agents.cognitive.memory import MAX_DIGEST_CHARS, MAX_MEMORY_KEYS

    memory = WorkingMemory()
    for i in range(MAX_MEMORY_KEYS + 5):
        memory.note(f"k{i}", "v" * 500)
    assert len(memory.snapshot()) == MAX_MEMORY_KEYS
    assert memory.recall("k0") is None and memory.recall("k24") is not None
    assert len(memory.digest()) <= MAX_DIGEST_CHARS


# ----------------------------- the loop (integration) -----------------------------

@pytest.mark.asyncio
async def test_working_memory_crosses_subagents_but_raw_scratchpad_does_not(monkeypatch):
    from laboratree.agents.deep import run_deep_agent
    from laboratree.core.db.postgres import sessionmaker
    from laboratree.core.search import SearchHit

    prompts: list[str] = []
    _script(monkeypatch, [
        GOAL_OK,
        json.dumps({"tasks": [
            {"objective": "gather sources", "agent_type": "research", "tools": ["web_search"]},
            {"objective": "assess pricing", "agent_type": "research", "tools": ["web_search"]},
        ]}),
        json.dumps({"thought": "search", "tool": "web_search", "args": {"query": "s"}}),
        json.dumps({"finish": "SUMMARY-ONE: three credible sources found", "findings": []}),
        json.dumps({"finish": "pricing is tiered", "findings": []}),
        # no synthesis/critic: both tasks returned zero findings
        REFLECT_OK,
    ], prompts)
    import laboratree.core.search as search_mod
    monkeypatch.setattr(search_mod, "search_available", lambda: True)
    monkeypatch.setattr(search_mod, "web_search", lambda q, count=None: [
        SearchHit(title="RAW-OBS-MARKER source", url="https://s.org", description="d")])

    async with sessionmaker()() as session:
        ctx = await _seed_context(session)
        result = await run_deep_agent(ctx, "test-stage", BROAD_OBJECTIVE)
        assert result.status == "succeeded"

    task2_prompts = [p for p in prompts if "assess pricing" in p]
    assert task2_prompts, "second sub-agent never prompted"
    # the first task's summary crossed via working memory…
    assert any("SUMMARY-ONE" in p for p in task2_prompts)
    # …but its raw observation did not (token law: digests only)
    assert all("RAW-OBS-MARKER" not in p for p in task2_prompts)


@pytest.mark.asyncio
async def test_experience_roundtrip_recall_and_org_isolation(monkeypatch):
    from laboratree.agents.cognitive import Goal, digest_experiences, recall_experiences, record_experience
    from laboratree.core.db.postgres import sessionmaker
    from laboratree.projects.models import ExperienceOutcome

    async with sessionmaker()() as session:
        ctx = await _seed_context(session)
        goal = Goal(text="compare bicycle subsidy programs for rural attendance",
                    intent="compare programs", kind="analysis")
        await record_experience(
            session, org_id=ctx.org_id, project_id=ctx.project_id, goal=goal,
            plan=[{"objective": "crosstab first", "agent_type": "analysis"}],
            outcome=ExperienceOutcome.SUCCEEDED, score=1.0,
            lessons=["crosstab-first beat model-first"])
        await record_experience(
            session, org_id=ctx.org_id, project_id=ctx.project_id,
            goal=Goal(text="bicycle subsidy web scrape", intent="scrape", kind="web"),
            plan=[], outcome=ExperienceOutcome.FAILED, score=0.0,
            lessons=["site blocks static crawls"])
        await session.commit()

        recalled = await recall_experiences(
            session, org_id=ctx.org_id,
            goal=Goal(text="bicycle subsidy attendance analysis", kind="analysis",
                      intent=""))
        assert recalled, "seeded experience not recalled"
        digest = digest_experiences(recalled)
        assert "crosstab-first beat model-first" in digest
        assert "avoid:" in digest                                  # ≤1 failure, labeled

        # another org sees nothing (isolation law)
        foreign = await recall_experiences(
            session, org_id=uuid.uuid4(),
            goal=Goal(text="bicycle subsidy attendance analysis", kind="analysis",
                      intent=""))
        assert foreign == []


@pytest.mark.asyncio
async def test_refinement_runs_exactly_once_when_critic_guts_findings(monkeypatch):
    from laboratree.agents.deep import run_deep_agent
    from laboratree.core.db.postgres import sessionmaker

    _script(monkeypatch, [
        GOAL_OK,
        json.dumps({"tasks": [{"objective": "estimate market size",
                               "agent_type": "research", "tools": []}]}),
        json.dumps({"finish": "sized it",
                    "findings": [{"claim": "market is huge", "basis": "none"},
                                 {"claim": "growth is wild", "basis": "none"}]}),
        json.dumps({"verdicts": [{"index": 0, "supported": False, "reason": "no obs"},
                                 {"index": 1, "supported": False, "reason": "no obs"}]}),
        REFLECT_OK,                                               # refinement reflection
        json.dumps({"tasks": [{"objective": "re-verify with cited sources",
                               "agent_type": "research", "tools": []}]}),  # revision plan
        json.dumps({"finish": "verified from sources",
                    "findings": [{"claim": "credible sources exist", "basis": "1"}]}),
        json.dumps({"summary": "verified", "findings":
                    [{"claim": "credible sources exist", "basis": "task obs"}]}),  # synthesis
        CRITIC_ALL_OK,
        # no second reflection: the refinement round's reflection is reused
    ])
    steps: list[dict] = []

    async def _on_step(step: dict) -> None:
        steps.append(step)

    async with sessionmaker()() as session:
        ctx = await _seed_context(session)
        result = await run_deep_agent(ctx, "refine-stage", BROAD_OBJECTIVE,
                                      on_step=_on_step)

    refines = [s for s in steps if s.get("kind") == "refine"]
    assert len(refines) == 1                                      # max one revision (hard law)
    assert result.artifacts["refined"] is True
    assert any("credible sources exist" in str(f) for f in result.artifacts["findings"])
    assert not any("market is huge" in str(f) for f in result.artifacts["findings"])


@pytest.mark.asyncio
async def test_token_budget_stops_run_honestly(monkeypatch):
    from laboratree.agents.deep import run_deep_agent
    from laboratree.core.config import settings
    from laboratree.core.db.postgres import sessionmaker
    from laboratree.core.llm.context import use_llm_context

    monkeypatch.setattr(settings, "agent_token_budget", 10)
    _script(monkeypatch, [
        GOAL_OK,
        json.dumps({"tasks": [{"objective": "task one", "agent_type": "research",
                               "tools": []},
                              {"objective": "task two", "agent_type": "research",
                               "tools": []}]}),
        # nothing else: the budget check must stop before any sub-agent runs
    ])
    steps: list[dict] = []

    async def _on_step(step: dict) -> None:
        steps.append(step)

    run_op = f"agent-run:{uuid.uuid4()}"
    async with sessionmaker()() as session:
        from laboratree.projects.models import LLMCall

        ctx = await _seed_context(session)
        session.add(LLMCall(operation=run_op, total_tokens=50))
        await session.commit()
        with use_llm_context("test", run_op, org_id=ctx.org_id):
            result = await run_deep_agent(ctx, "budget-stage", BROAD_OBJECTIVE,
                                          on_step=_on_step)
        assert any(s.get("kind") == "budget" for s in steps)
        assert "token budget" in result.summary
        assert result.artifacts["tasks"] == 0                     # nothing ran past the stop
        # the overrun was still recorded as an experience (failed — no findings)
        experience = (await session.execute(sql_text(
            "SELECT outcome FROM agent_experiences WHERE org_id = :o"),
            {"o": ctx.org_id})).scalar()
        assert experience == "failed"


def test_stale_running_agent_run_is_reaped_on_read(monkeypatch):
    with TestClient(app) as client:
        email = f"cg-{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/auth/register",
                        json={"email": email, "password": "supersecret1", "full_name": "C"})
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        project_id = client.post("/api/projects", json={"name": "CG"},
                                 headers=headers).json()["id"]
        # a RUNNING run whose host died an hour ago
        import asyncio

        from laboratree.core.db.postgres import sessionmaker

        run_id = uuid.uuid4()

        async def _seed():
            async with sessionmaker()() as session:
                org = (await session.execute(sql_text(
                    "SELECT org_id FROM projects WHERE id = :p"),
                    {"p": project_id})).scalar()
                await session.execute(sql_text(
                    "INSERT INTO agent_runs (id, org_id, project_id, lab, task, status, "
                    " steps, findings, summary, trace_key, llm_calls_used, frontier, "
                    " created_at, updated_at) "
                    "VALUES (:i, :o, :p, 'field', 't', 'running', '[]', '[]', '', '', 0, "
                    " '{}', now(), now() - interval '1 hour')"),
                    {"i": run_id, "o": org, "p": project_id})
                await session.commit()

        asyncio.run(_seed())
        body = client.get(f"/api/projects/{project_id}/agent-runs/{run_id}",
                          headers=headers).json()
        assert body["status"] == "failed"
        assert "stale" in body["summary"]
