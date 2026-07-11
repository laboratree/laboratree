"""Behavioural grounding tests: theory overrides the LLM where a question declares a model."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.labs.synth.behavioral import choice_shares
from laboratree.labs.synth.engine import (
    LLMPersonaEngine,
    PersonaEngineUnavailable,
    get_persona_engine,
)
from laboratree.labs.synth.grounding import ground_answers, stable_unit
from laboratree.main import app

# a choice question grounded by MNL, a risk question grounded by prospect theory, and a plain one
STRUCT = {
    "sections": [{"id": "s1", "title": "S", "questions": [
        {"id": "q_plain", "type": "single", "text": "Own a scooter?",
         "required": True, "options": ["yes", "no"]},
        {"id": "q_choice", "type": "single", "text": "Which plan?", "options": ["cheap", "premium"],
         "behavioral": {"model": "discrete_choice",
                        "alternatives": [{"option": "cheap", "price": 10.0, "quality": 1.0},
                                         {"option": "premium", "price": 30.0, "quality": 2.0}],
                        "weights": {"price": -0.2, "quality": 1.0}}},
        {"id": "q_risk", "type": "single", "text": "Sure gain or risky loss?",
         "options": ["sure", "gamble"],
         "behavioral": {"model": "prospect", "reference": 0,
                        "options": [{"option": "sure", "outcome": 20},
                                    {"option": "gamble", "outcome": -20}]}},
    ]}],
    "logic": [],
}


def _persona(handle: str, neuroticism: float = 0.5) -> dict:
    return {"handle": handle, "attributes": {}, "traits": {"neuroticism": neuroticism}}


# ----------------------------- pure: grounding -----------------------------

def test_grounding_overrides_llm_only_for_declared_questions():
    llm_answers = {"q_plain": "yes", "q_choice": "premium", "q_risk": "gamble"}
    result = ground_answers(STRUCT, _persona("p1"), llm_answers)
    # the plain question is untouched — theory has no claim on it
    assert result.answers["q_plain"] == "yes"
    assert "q_plain" not in result.grounded
    # both declared questions were decided by theory
    assert set(result.grounded) == {"q_choice", "q_risk"}
    # prospect theory: a loss-averse agent takes the sure +20 over a -20 gamble
    assert result.answers["q_risk"] == "sure"


def test_prospect_grounding_is_loss_averse_regardless_of_llm_guess():
    for guess in ("gamble", "sure"):
        out = ground_answers(STRUCT, _persona("p9"), {"q_risk": guess})
        assert out.answers["q_risk"] == "sure"


def test_discrete_choice_is_stable_per_persona_and_matches_mnl_shares():
    # same persona -> same choice every time (reproducible)
    first = ground_answers(STRUCT, _persona("p1"), {}).answers["q_choice"]
    assert ground_answers(STRUCT, _persona("p1"), {}).answers["q_choice"] == first

    # across a cohort, realized shares approximate the MNL prediction
    picks = [ground_answers(STRUCT, _persona(f"p{i}"), {}).answers["q_choice"] for i in range(400)]
    realized_cheap = picks.count("cheap") / len(picks)
    predicted = choice_shares(
        [{"price": 10.0, "quality": 1.0}, {"price": 30.0, "quality": 2.0}],
        {"price": -0.2, "quality": 1.0},
    )
    predicted_cheap = predicted[0]["share"]
    assert abs(realized_cheap - predicted_cheap) < 0.06  # hash-uniform draw ≈ predicted share
    assert 0 < realized_cheap < 1                        # both options actually chosen


def test_stable_unit_is_deterministic_and_in_range():
    assert stable_unit("x") == stable_unit("x")
    assert stable_unit("x") != stable_unit("y")
    assert all(0.0 <= stable_unit(f"s{i}") < 1.0 for i in range(50))


# ----------------------------- engine seam -----------------------------

def test_engine_selection_and_unknown_backend(monkeypatch):
    assert isinstance(get_persona_engine(), LLMPersonaEngine)
    from laboratree.core.config import settings
    monkeypatch.setattr(settings, "persona_engine", "tinytroupe")
    try:
        get_persona_engine()
        raise AssertionError("expected PersonaEngineUnavailable")
    except PersonaEngineUnavailable as exc:
        assert "tinytroupe" in str(exc)  # honest failure, never a silent fake


def test_wave_falls_back_deterministically_without_llm_key(monkeypatch):
    # no API key -> the wave still runs, reproducibly, and says so (never silently)
    from laboratree.core.config import settings
    from laboratree.labs.synth.fallback import deterministic_wave_answers

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    persona = _persona("p3")
    result = LLMPersonaEngine().simulate(STRUCT, persona)
    assert result["answers"]["q_plain"] in ("yes", "no")
    assert set(result["grounded"]) == {"q_choice", "q_risk"}   # theory still decides its questions
    # pure fallback is deterministic per persona
    assert deterministic_wave_answers(STRUCT, persona) == deterministic_wave_answers(STRUCT, persona)


# ----------------------------- integration -----------------------------

def test_wave_run_reports_grounded_questions(monkeypatch):
    from laboratree.labs.synth import llm as synth_llm

    # the LLM stubbornly answers "premium"/"gamble"; theory must overrule both
    monkeypatch.setattr(synth_llm, "default_complete", lambda s, p, **k: (
        '{"answers": {"q_plain": "yes", "q_choice": "premium", "q_risk": "gamble"}, '
        '"confusions": [], "dropped_at": null}'
    ))
    with TestClient(app) as client:
        email = f"gr-{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/auth/register",
                        json={"email": email, "password": "supersecret1", "full_name": "G"})
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        project_id = client.post("/api/projects", json={"name": "Gr"},
                                 headers=headers).json()["id"]
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "S", "structure": STRUCT}, headers=headers).json()["id"]
        cid = client.post(f"/api/projects/{project_id}/persona-cohorts",
                          json={"name": "C", "n": 10, "margins": {}}, headers=headers).json()["id"]

        report = client.post(f"/api/persona-cohorts/{cid}/run",
                             json={"survey_id": sid}, headers=headers)
        assert report.status_code == 200, report.text
        body = report.json()
        assert body["grounded_questions"] == ["q_choice", "q_risk"]
        # the risk answer is theory's "sure", not the LLM's "gamble"
        risk = body["distributions"]["q_risk"]
        assert risk[0]["value"] == "sure"
        # and the plain question kept the LLM's answer
        assert body["distributions"]["q_plain"][0]["value"] == "yes"
