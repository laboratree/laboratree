"""Persona Lab social graph tests: homophily edges, neighbour influence, graph endpoint."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.labs.synth.social import (
    build_social_graph,
    neighbour_opinion,
    neighbours,
    social_context,
)
from laboratree.main import app

STRUCT = {
    "sections": [{"id": "s1", "title": "S", "questions": [
        {"id": "q1", "type": "single", "text": "Own a scooter?",
         "required": True, "options": ["yes", "no"]},
    ]}],
    "logic": [],
}


# ----------------------------- pure: graph -----------------------------

def test_homophily_graph_prefers_similar_and_is_deterministic():
    personas = [
        {"handle": "p1", "attributes": {"city": "berlin", "gender": "f"}},
        {"handle": "p2", "attributes": {"city": "berlin", "gender": "f"}},  # like p1
        {"handle": "p3", "attributes": {"city": "munich", "gender": "m"}},
        {"handle": "p4", "attributes": {"city": "munich", "gender": "m"}},  # like p3
    ]
    edges = build_social_graph(personas, avg_degree=1)
    # deterministic
    assert build_social_graph(personas, avg_degree=1) == edges
    # edges are undirected + normalized (a < b)
    assert all(e["a"] < e["b"] for e in edges)
    # the two Berliners connect; the two Municher's connect (homophily)
    pairs = {(e["a"], e["b"]) for e in edges}
    assert ("p1", "p2") in pairs
    assert ("p3", "p4") in pairs
    # similar personas get a higher edge weight than dissimilar ones
    berlin = next(e for e in edges if {e["a"], e["b"]} == {"p1", "p2"})
    assert berlin["weight"] > 0.5


def test_neighbour_opinion_and_context():
    edges = [{"a": "p1", "b": "p2", "weight": 1.0}, {"a": "p1", "b": "p3", "weight": 1.0}]
    assert set(neighbours("p1", edges)) == {"p2", "p3"}
    last = {"p2": {"q1": "yes"}, "p3": {"q1": "yes"}, "p4": {"q1": "no"}}
    opinion = neighbour_opinion("p1", edges, last)
    assert opinion["q1"] == "yes"                          # both neighbours said yes
    assert "q1=yes" in social_context(opinion)
    assert social_context({}) == ""                        # nothing to say -> empty


# ----------------------------- integration -----------------------------

def _fake(system: str, prompt: str, **kw) -> str:
    return '{"answers": {"q1": "yes"}, "confusions": [], "dropped_at": null}'


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_cohort_builds_graph_and_wave_uses_social_context(monkeypatch):
    from laboratree.labs.synth import llm as synth_llm

    prompts: list[str] = []

    def _capture(system: str, prompt: str, **kw) -> str:
        prompts.append(prompt)
        return '{"answers": {"q1": "yes"}, "confusions": [], "dropped_at": null}'

    monkeypatch.setattr(synth_llm, "default_complete", _capture)
    with TestClient(app) as client:
        email = f"soc-{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/auth/register",
                        json={"email": email, "password": "supersecret1", "full_name": "S"})
        headers = _auth(r.json()["access_token"])
        project_id = client.post("/api/projects", json={"name": "Soc"},
                                 headers=headers).json()["id"]
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "S", "structure": STRUCT}, headers=headers).json()["id"]
        cid = client.post(f"/api/projects/{project_id}/persona-cohorts",
                          json={"name": "Net", "n": 8,
                                "margins": {"city": {"berlin": 0.5, "munich": 0.5}}},
                          headers=headers).json()["id"]

        # graph endpoint returns nodes + edges
        graph = client.get(f"/api/persona-cohorts/{cid}/graph", headers=headers).json()
        assert len(graph["nodes"]) == 8
        assert len(graph["edges"]) > 0
        assert all(e["a"] < e["b"] for e in graph["edges"])

        # wave 1 (no memory yet -> no social context), wave 2 (neighbours' wave-1 answers appear)
        client.post(f"/api/persona-cohorts/{cid}/run", json={"survey_id": sid}, headers=headers)
        client.post(f"/api/persona-cohorts/{cid}/run", json={"survey_id": sid}, headers=headers)
        assert any("social circle" in p.lower() and "q1=yes" in p for p in prompts)
