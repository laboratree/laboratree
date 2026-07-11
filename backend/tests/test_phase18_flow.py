"""Flow orchestrator tests: every phase dispatched as a sub-agent, manual stages open real gates."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from laboratree.main import app


@pytest.fixture(autouse=True)
def _deterministic_brain(monkeypatch):
    """Pin the deterministic executor path: no real LLM keys (the dev .env may carry them)."""
    from laboratree.core.config import settings
    from laboratree.core.llm import get_llm

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    get_llm.cache_clear()
    yield
    get_llm.cache_clear()


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"flow-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "F"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    project_id = client.post("/api/projects", json={"name": "Flow"},
                             headers=headers).json()["id"]
    return headers, project_id


def test_flow_catalog_lists_the_three_use_case_flows():
    with TestClient(app) as client:
        flows = {f["key"]: f for f in client.get("/api/flows").json()["flows"]}
        # the three use-case flows + the legacy alias
        assert {"research", "policy-research", "market-research", "ngo-policy"} <= set(flows)

        # policy research: every stage has an executor (fully orchestrable)
        policy = flows["policy-research"]
        assert len(policy["stages"]) == 19
        assert set(policy["stages"]) <= set(policy["executors"])

        # market research: the market-intel phases are DeepAgent stages BY DESIGN
        market = flows["market-research"]
        deep_stages = set(market["stages"]) - set(market["executors"])
        assert {"market-sizing", "competitor-scan", "trend-scan", "pricing-analysis"} == deep_stages
        assert "segmentation" in market["executors"]

        # research: literature is the DeepAgent stage
        research = flows["research"]
        assert set(research["stages"]) - set(research["executors"]) == {"literature"}


def test_orchestrated_flow_runs_every_phase_and_gates_the_human_step():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        report = client.post(f"/api/projects/{project_id}/flows/ngo-policy/run",
                             json={}, headers=headers)
        assert report.status_code == 200, report.text
        body = report.json()

        by_id = {s["id"]: s for s in body["stages"]}
        assert len(by_id) == 19

        # every automatable phase succeeded
        succeeded = [s for s in body["stages"] if s["status"] == "succeeded"]
        assert len(succeeded) == 18, [
            (s["id"], s["status"], s["error"]) for s in body["stages"]
            if s["status"] not in ("succeeded", "gated")
        ]

        # the genuinely-human phase opened a REAL gate (visible in the gates inbox)
        assert by_id["intervention"]["status"] == "gated"
        assert body["gates_opened"] == 1
        gates = client.get("/api/gates", headers=headers).json()
        assert any("intervention" in g["title"].lower() for g in gates)

        # cross-phase state threaded: field used the questionnaire's survey; impact used the pilot
        assert by_id["field"]["artifacts"]["completes"] == 60
        assert by_id["questionnaire"]["artifacts"]["public_url"].startswith("/s/")
        assert by_id["impact"]["run_id"]
        assert by_id["personas"]["artifacts"]["wave"] == 1
        assert by_id["monitor"]["artifacts"]["share_path"].startswith("/r/")

        # evidence accumulated across the flow, and the whole flow is itself a tracked Run
        assert body["evidence_total"] >= 10
        assert body["flow_run_id"]
        assert body["status"] == "succeeded"

        # background/questions/hypotheses share one research-frame analysis (no duplicate runs)
        assert by_id["questions"]["run_id"] == by_id["background"]["run_id"]


def test_flow_handles_unknown_stage_and_bad_flow_key():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        # unknown flow key -> 422
        bad = client.post(f"/api/projects/{project_id}/flows/nope/run", json={}, headers=headers)
        assert bad.status_code == 422
        # a user-edited flow with a custom stage: noted as skipped, everything else still runs
        report = client.post(
            f"/api/projects/{project_id}/flows/ngo-policy/run",
            json={"stages": ["intake", "my-custom-stage", "eda"]}, headers=headers).json()
        by_id = {s["id"]: s for s in report["stages"]}
        assert by_id["intake"]["status"] == "succeeded"
        assert by_id["my-custom-stage"]["status"] == "skipped"
        assert by_id["eda"]["status"] == "succeeded"
