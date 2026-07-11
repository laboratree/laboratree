"""Supervisor + DeepAgent tests: durable gates, lab grouping, gap-filling with tools."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from laboratree.main import app

DEEP_STEP_1 = json.dumps({
    "thought": "I should look for market size sources",
    "tool": "web_search", "args": {"query": "india edtech market size", "count": 3},
})
DEEP_FINISH = json.dumps({
    "finish": "The market is measured in the low billions USD.",
    "findings": [{"claim": "India edtech market estimated at $4-6B",
                  "basis": "web_search results (steps 1)"}],
})
# deep-agent v2 runs a critic audit after converging — script it as "all supported"
DEEP_CRITIC_OK = json.dumps({"verdicts": [{"index": 0, "supported": True}]})
# broad objectives engage the cognitive loop: goal interpretation + meta-plan up front,
# reflection at the end (narrow objectives skip all three — cost law)
DEEP_GOAL = json.dumps({"intent": "size the market", "deliverable": "sizing brief"})
DEEP_PLAN_ONE = json.dumps({"tasks": [{"objective": "size the market from credible sources",
                                       "agent_type": "research", "tools": ["web_search"]}]})
DEEP_REFLECT = json.dumps({"worked": ["triangulation"], "failed": [], "lessons": []})


@pytest.fixture(autouse=True)
def _fresh_supervisor():
    """Each test gets its own graph; keyless env pinned; LLM client cache cleared."""
    from laboratree.agents import supervisor
    from laboratree.core.llm import get_llm

    supervisor.reset_supervisor()
    get_llm.cache_clear()
    yield
    supervisor.reset_supervisor()
    get_llm.cache_clear()


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"sup-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "S"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    project_id = client.post("/api/projects", json={"name": "Sup"},
                             headers=headers).json()["id"]
    return headers, project_id


def test_supervised_flow_pauses_at_gate_and_resumes_to_completion(monkeypatch):
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")   # deterministic lab agents
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        run = client.post(f"/api/projects/{project_id}/flows/ngo-policy/supervise",
                          json={}, headers=headers)
        assert run.status_code == 200, run.text
        body = run.json()

        # paused exactly at the human gate, with everything before it done
        assert body["status"] == "paused"
        assert body["pending_gate"]["stage_id"] == "intervention"
        done = {s["id"]: s for s in body["stages"]}
        assert done["prioritize"]["status"] == "succeeded"
        assert "pilot" not in done                       # nothing after the gate ran yet

        # every phase is attributed to its Lab agent
        assert done["field"]["lab"] == "field"
        assert done["crosstab"]["lab"] == "tabulation"
        assert "signal" in body["labs"] and "decision" in body["labs"]

        # the gate is a REAL GateTask in the inbox
        gates = client.get("/api/gates", headers=headers).json()
        assert any("intervention" in g["title"].lower() and g["status"] == "pending"
                   for g in gates)

        # thread state is queryable while paused
        thread = client.get(f"/api/flows/threads/{body['thread_id']}", headers=headers).json()
        assert thread["status"] == "paused"

        # resume with approval -> the graph continues to the end
        final = client.post(f"/api/flows/threads/{body['thread_id']}/resume",
                            json={"approved": True, "note": "portfolio approved"},
                            headers=headers)
        assert final.status_code == 200, final.text
        fbody = final.json()
        assert fbody["status"] == "completed"
        by_id = {s["id"]: s for s in fbody["stages"]}
        assert by_id["impact"]["status"] == "succeeded"          # post-gate stages ran
        assert by_id["monitor"]["artifacts"]["share_path"].startswith("/r/")
        assert by_id["gate:intervention"]["status"] == "approved"
        # the GateTask row was resolved
        gates_after = client.get("/api/gates", headers=headers).json()
        assert any(g["status"] == "approved" for g in gates_after)
        # resuming a finished run is a clean conflict
        again = client.post(f"/api/flows/threads/{fbody['thread_id']}/resume",
                            json={"approved": True}, headers=headers)
        assert again.status_code == 409


def test_deep_agent_fills_uncovered_stage_with_tools(monkeypatch):
    from laboratree.core.config import settings
    from laboratree.core.search import SearchHit
    from laboratree.labs.agentic import llm as agentic_llm

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    scripted = iter([DEEP_STEP_1, DEEP_FINISH, DEEP_CRITIC_OK])
    prompts: list[str] = []

    def _fake(system: str, prompt: str, **kw) -> str:
        prompts.append(prompt)
        return next(scripted)

    monkeypatch.setattr(agentic_llm, "default_complete", _fake)

    import laboratree.core.search as search_mod
    monkeypatch.setattr(search_mod, "search_available", lambda: True)  # no web key in test env
    monkeypatch.setattr(search_mod, "web_search", lambda q, count=None: [
        SearchHit(title="EdTech in India 2026", url="https://example.org/r",
                  description="Market pegged at $5B", source="brave")])

    with TestClient(app) as client:
        headers, project_id = _setup(client)
        run = client.post(
            f"/api/projects/{project_id}/flows/ngo-policy/supervise",
            json={"stages": ["market-sizing"],
                  "objectives": {"market-sizing": "Size the Indian edtech market"}},
            headers=headers)
        assert run.status_code == 200, run.text
        body = run.json()
        assert body["status"] == "completed"
        stage = body["stages"][0]
        assert stage["lab"] == "deep-agent"
        assert stage["status"] == "succeeded"
        assert stage["artifacts"]["steps"] == 1                   # one tool call, then finish
        assert stage["artifacts"]["trace_key"].startswith("flows/")

        # the observation actually reached the second prompt (real ReAct loop)
        assert "EdTech in India 2026" in prompts[1]

        # findings are Evidence-locked (claims naming the deep agent's component)
        evidence = client.get(f"/api/runs/{stage['run_id']}/evidence", headers=headers).json()
        claims = [e for e in evidence if e["kind"] == "claim"]
        assert any("$4-6B" in str(e["value"]) for e in claims)


def test_market_research_flow_mixes_deep_agent_and_components(monkeypatch):
    from laboratree.core.config import settings
    from laboratree.core.search import SearchHit
    from laboratree.labs.agentic import llm as agentic_llm

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    scripted = iter([DEEP_GOAL, DEEP_PLAN_ONE, DEEP_STEP_1, DEEP_FINISH,
                     DEEP_CRITIC_OK, DEEP_REFLECT])
    monkeypatch.setattr(agentic_llm, "default_complete",
                        lambda s, p, **kw: next(scripted))
    import laboratree.core.search as search_mod
    monkeypatch.setattr(search_mod, "search_available", lambda: True)
    monkeypatch.setattr(search_mod, "web_search", lambda q, count=None: [
        SearchHit(title="Sizing report", url="https://example.org/m", description="$5B")])

    with TestClient(app) as client:
        headers, project_id = _setup(client)
        body = client.post(
            f"/api/projects/{project_id}/flows/market-research/supervise",
            json={"stages": ["market-sizing", "segmentation"]}, headers=headers).json()
        assert body["status"] == "completed"
        by_id = {s["id"]: s for s in body["stages"]}
        # the market-intel gap was filled by the deep agent, with the flow's DEFAULT objective
        assert by_id["market-sizing"]["lab"] == "deep-agent"
        assert by_id["market-sizing"]["status"] == "succeeded"
        # segmentation ran as a real Evidence-locked clustering component
        assert by_id["segmentation"]["lab"] == "modeling"
        assert by_id["segmentation"]["status"] == "succeeded"
        assert by_id["segmentation"]["evidence"] >= 1


def test_deep_agent_gates_honestly_without_llm(monkeypatch):
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        body = client.post(f"/api/projects/{project_id}/flows/ngo-policy/supervise",
                           json={"stages": ["mystery-phase"]}, headers=headers).json()
        # honest: paused on a gate explaining the agent layer is not configured
        assert body["status"] == "paused"
        assert body["pending_gate"]["stage_id"] == "mystery-phase"
        gates = client.get("/api/gates", headers=headers).json()
        assert any("deep agent needed" in g["title"].lower() for g in gates)
