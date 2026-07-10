"""Persona Lab tests: stable traits + persistent cohorts with memory across survey waves.

The wave run uses a fake LLM (no network). Requires live Postgres.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.labs.synth.traits import OCEAN, assign_traits, bio_sketch
from laboratree.main import app

STRUCT = {
    "sections": [{"id": "s1", "title": "S", "questions": [
        {"id": "q1", "type": "single", "text": "Own a scooter?",
         "required": True, "options": ["yes", "no"]},
    ]}],
    "logic": [],
}


# ----------------------------- pure: traits -----------------------------

def test_traits_are_stable_and_bounded():
    persona = {"id": "p1", "attributes": {"gender": "f", "city": "berlin"}}
    t1 = assign_traits(persona)
    t2 = assign_traits(persona)
    assert t1 == t2                                   # deterministic
    assert set(t1) == set(OCEAN)
    assert all(0.0 <= v <= 1.0 for v in t1.values())
    # a different persona gets different traits
    assert assign_traits({"id": "p2", "attributes": {}}) != t1
    # bio reflects the attributes
    bio = bio_sketch(persona, t1)
    assert "berlin" in bio and "Personality" in bio


# ----------------------------- integration -----------------------------

def _fake(system: str, prompt: str, **kw) -> str:
    # a persona that has answered before should see its memory in the prompt
    return '{"answers": {"q1": "yes"}, "confusions": [], "dropped_at": null}'


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup(client: TestClient) -> tuple[dict[str, str], str, str]:
    email = f"persona-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "P"})
    headers = _auth(r.json()["access_token"])
    project_id = client.post("/api/projects", json={"name": "Persona"},
                             headers=headers).json()["id"]
    sid = client.post(f"/api/projects/{project_id}/surveys",
                      json={"title": "S", "structure": STRUCT}, headers=headers).json()["id"]
    return headers, project_id, sid


def test_cohort_persists_and_accumulates_memory_across_waves(monkeypatch):
    from laboratree.labs.synth import llm as synth_llm
    monkeypatch.setattr(synth_llm, "default_complete", _fake)

    with TestClient(app) as client:
        headers, project_id, sid = _setup(client)

        # build a persisted cohort with stable traits
        cohort = client.post(f"/api/projects/{project_id}/persona-cohorts",
                             json={"name": "Berliners", "n": 6,
                                   "margins": {"gender": {"m": 0.5, "f": 0.5}}},
                             headers=headers)
        assert cohort.status_code == 201, cohort.text
        cid = cohort.json()["id"]
        assert cohort.json()["n"] == 6 and cohort.json()["waves"] == 0

        personas = client.get(f"/api/persona-cohorts/{cid}", headers=headers).json()
        assert len(personas) == 6
        assert set(personas[0]["traits"]) == set(OCEAN)
        assert personas[0]["memory_waves"] == 0
        genders = [p["attributes"]["gender"] for p in personas]
        assert genders.count("m") == 3 and genders.count("f") == 3

        # wave 1
        w1 = client.post(f"/api/persona-cohorts/{cid}/run",
                         json={"survey_id": sid}, headers=headers)
        assert w1.status_code == 200, w1.text
        assert w1.json()["wave"] == 1
        assert w1.json()["completion_rate"] == 1.0

        # memory accumulated for every persona; cohort wave counter advanced
        after1 = client.get(f"/api/persona-cohorts/{cid}", headers=headers).json()
        assert all(p["memory_waves"] == 1 for p in after1)
        assert client.get(f"/api/projects/{project_id}/persona-cohorts",
                          headers=headers).json()[0]["waves"] == 1

        # wave 2 — the SAME personas answer again, memory grows to 2
        w2 = client.post(f"/api/persona-cohorts/{cid}/run",
                         json={"survey_id": sid}, headers=headers)
        assert w2.json()["wave"] == 2
        after2 = client.get(f"/api/persona-cohorts/{cid}", headers=headers).json()
        assert all(p["memory_waves"] == 2 for p in after2)


def test_persona_wave_prompt_includes_memory(monkeypatch):
    # verify the simulation actually feeds prior answers back into the prompt
    from laboratree.labs.synth import llm as synth_llm

    seen_prompts: list[str] = []

    def _capture(system: str, prompt: str, **kw) -> str:
        seen_prompts.append(prompt)
        return '{"answers": {"q1": "no"}, "confusions": [], "dropped_at": null}'

    monkeypatch.setattr(synth_llm, "default_complete", _capture)
    with TestClient(app) as client:
        headers, project_id, sid = _setup(client)
        cid = client.post(f"/api/projects/{project_id}/persona-cohorts",
                          json={"name": "C", "n": 2, "margins": {}}, headers=headers).json()["id"]
        client.post(f"/api/persona-cohorts/{cid}/run", json={"survey_id": sid}, headers=headers)
        client.post(f"/api/persona-cohorts/{cid}/run", json={"survey_id": sid}, headers=headers)
        # the second wave's prompts should reference the persona's past answers
        assert any("past answers" in p.lower() and "wave 1" in p for p in seen_prompts)


def test_cohort_org_isolation(monkeypatch):
    from laboratree.labs.synth import llm as synth_llm
    monkeypatch.setattr(synth_llm, "default_complete", _fake)
    with TestClient(app) as client:
        headers_a, project_a, _ = _setup(client)
        cid = client.post(f"/api/projects/{project_a}/persona-cohorts",
                          json={"name": "A", "n": 2, "margins": {}}, headers=headers_a).json()["id"]
        rb = client.post("/api/auth/register",
                         json={"email": f"b-{uuid.uuid4().hex[:8]}@example.com",
                               "password": "supersecret1", "full_name": "B"})
        headers_b = _auth(rb.json()["access_token"])
        assert client.get(f"/api/persona-cohorts/{cid}", headers=headers_b).status_code == 404
