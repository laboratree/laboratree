"""Persona conditioning tests: clamped objective bias, neutrality invariance, RCT guard."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.labs.synth.conditioning import MAX_TRAIT_DELTA, condition_traits
from laboratree.labs.synth.traits import OCEAN
from laboratree.main import app


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"pc-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "supersecret1", "full_name": "P"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    project_id = client.post("/api/projects", json={"name": "PC"}, headers=headers).json()["id"]
    return headers, project_id


def test_condition_traits_clamps_and_records_delta(monkeypatch):
    from laboratree.core.config import settings
    from laboratree.labs.agentic import llm as agentic_llm

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    # the LLM proposes an EXTREME shift — the engine must clamp it
    monkeypatch.setattr(
        agentic_llm,
        "default_complete",
        lambda s, p, **kw: (
            '{"deltas": {"neuroticism": 0.9, "openness": -0.8}, "attitudes": {"safety_concern": "high"}}'
        ),
    )
    base = {"traits": dict.fromkeys(OCEAN, 0.5), "bio": "test persona"}
    result = condition_traits(base, "school safety survey")
    assert result.delta["neuroticism"] == MAX_TRAIT_DELTA  # clamped, not 0.9
    assert result.delta["openness"] == -MAX_TRAIT_DELTA
    assert result.traits["neuroticism"] == 0.5 + MAX_TRAIT_DELTA
    assert result.attitudes == {"safety_concern": "high"}
    assert all(abs(d) <= MAX_TRAIT_DELTA for d in result.delta.values())


def test_keyword_fallback_conditions_keyless(monkeypatch):
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    base = {"traits": dict.fromkeys(OCEAN, 0.5)}
    result = condition_traits(base, "education outcomes for rural students")
    assert result.delta["openness"] > 0  # education keyword nudged
    assert all(abs(d) <= MAX_TRAIT_DELTA for d in result.delta.values())


def test_cohort_conditioning_labels_and_neutral_invariance(monkeypatch):
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")  # deterministic fallback path
    with TestClient(app) as client:
        headers, project_id = _setup(client)

        # NEUTRAL cohorts are invariant to the objective (same margins -> same traits)
        neutral = client.post(
            f"/api/projects/{project_id}/persona-cohorts", json={"name": "N", "n": 4, "margins": {}}, headers=headers
        ).json()
        assert neutral["conditioning"] == "neutral" and neutral["trait_delta"] == {}

        conditioned = client.post(
            f"/api/projects/{project_id}/persona-cohorts",
            json={
                "name": "C",
                "n": 4,
                "margins": {},
                "conditioning": "objective",
                "objective": "education dropout drivers survey",
            },
            headers=headers,
        ).json()
        assert conditioned["conditioning"] == "objective"
        assert conditioned["trait_delta"].get("openness", 0) > 0  # recorded mean bias
        assert all(abs(v) <= MAX_TRAIT_DELTA for v in conditioned["trait_delta"].values())

        n_traits = client.get(f"/api/persona-cohorts/{neutral['id']}", headers=headers).json()[0]["traits"]
        c_traits = client.get(f"/api/persona-cohorts/{conditioned['id']}", headers=headers).json()[0]["traits"]
        assert c_traits != n_traits  # conditioning really shifted


def test_rct_purpose_refuses_objective_conditioning():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        refused = client.post(
            f"/api/projects/{project_id}/persona-cohorts",
            json={
                "name": "R",
                "n": 4,
                "margins": {},
                "purpose": "rct",
                "conditioning": "objective",
                "objective": "does the subsidy work?",
            },
            headers=headers,
        )
        assert refused.status_code == 422
        assert "bias causal estimates" in refused.json()["detail"]
        # neutral RCT cohorts are fine
        ok = client.post(
            f"/api/projects/{project_id}/persona-cohorts",
            json={"name": "R2", "n": 4, "margins": {}, "purpose": "rct"},
            headers=headers,
        )
        assert ok.status_code == 201
        # conditioning without an objective is rejected too
        missing = client.post(
            f"/api/projects/{project_id}/persona-cohorts",
            json={"name": "R3", "n": 4, "margins": {}, "conditioning": "objective"},
            headers=headers,
        )
        assert missing.status_code == 422
