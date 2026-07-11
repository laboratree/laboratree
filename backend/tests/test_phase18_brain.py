"""Agent brain tests: LLM reasoning is Evidence-locked; keyless flows fall back honestly."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from laboratree.main import app


@pytest.fixture(autouse=True)
def _fresh_llm_cache():
    """get_llm is lru-cached — never let a client built under patched settings leak out."""
    from laboratree.core.llm import get_llm

    get_llm.cache_clear()
    yield
    get_llm.cache_clear()

FAKE_ANSWER = (
    '{"findings": [{"claim": "Dropout concentrates where distance_km exceeds 5",'
    ' "basis": "SAMPLE ROWS distance_km vs dropout"},'
    ' {"claim": "Low income_band households show triple the dropout rate",'
    ' "basis": "income_band column"}],'
    ' "summary": "Distance and income are the primary dropout drivers in this data."}'
)


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"brain-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "B"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    project_id = client.post("/api/projects", json={"name": "Brain"},
                             headers=headers).json()["id"]
    return headers, project_id


def test_agentic_phases_reason_with_llm_and_lock_evidence(monkeypatch):
    from laboratree.core.config import settings
    from laboratree.labs.agentic import llm as agentic_llm

    prompts: list[str] = []

    def _fake(system: str, prompt: str, **kw) -> str:
        prompts.append(prompt)
        return FAKE_ANSWER

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")  # so is_configured() passes
    monkeypatch.setattr(agentic_llm, "default_complete", _fake)
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        report = client.post(f"/api/projects/{project_id}/flows/ngo-policy/run",
                             json={"stages": ["intake", "hypotheses"]}, headers=headers).json()
        by_id = {s["id"]: s for s in report["stages"]}

        # both phases used the agent brain, over REAL project context (dataset columns fed in)
        assert by_id["intake"]["artifacts"]["agent"] is True
        assert by_id["intake"]["summary"].startswith("🧠")
        assert any("distance_km" in p for p in prompts)   # actual schema reached the agent

        # the agent's findings are Evidence-locked (claims with the model named)
        evidence = client.get(f"/api/runs/{by_id['intake']['run_id']}/evidence",
                              headers=headers).json()
        claims = [e for e in evidence if e["kind"] == "claim"]
        assert len(claims) == 2
        assert "distance_km exceeds 5" in str(claims[0]["value"])

        # agent hypotheses were still TESTED against the data (never opinion-only)
        assert by_id["hypotheses"]["artifacts"]["agent"] is True
        assert by_id["hypotheses"]["artifacts"]["tested_run_id"]


def test_agentic_phases_fall_back_without_llm_key(monkeypatch):
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        report = client.post(f"/api/projects/{project_id}/flows/ngo-policy/run",
                             json={"stages": ["intake"]}, headers=headers).json()
        stage = report["stages"][0]
        # honest fallback: still succeeds, still Evidence-locked, and SAYS it was deterministic
        assert stage["status"] == "succeeded"
        assert "deterministic" in stage["summary"]
        assert stage["run_id"]
