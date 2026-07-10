"""Phase 13 (Qual Studio II) tests: codebook HITL gate, coding, sentiment, quotes, synthesis.

Requires live Postgres + Mongo. All LLM calls are faked via labs.qual.llm monkeypatching.
"""

from __future__ import annotations

import json
import uuid

from fastapi.testclient import TestClient
from laboratree.core import transcribe as transcribe_core
from laboratree.core.transcribe import Segment, TranscriptResult
from laboratree.labs.qual.quotes import verbatim_filter
from laboratree.labs.qual.synthesis import theme_matrix
from laboratree.main import app

SEGMENTS_TEXT = ["I worry about traffic safety every day.", "The price seems fair to me."]


class FakeTranscribe:
    def transcribe(self, audio: bytes, filename: str) -> TranscriptResult:
        return TranscriptResult(
            segments=[
                Segment(start=0.0, end=4.0, text=SEGMENTS_TEXT[0]),
                Segment(start=4.0, end=8.0, text=SEGMENTS_TEXT[1]),
            ],
            text=" ".join(SEGMENTS_TEXT),
            language="en",
        )


def _fake_qual_llm(system: str, prompt: str, **kw) -> str:
    """Route by prompt content: codebook proposal, coding, sentiment, quotes."""
    if "building a thematic codebook" in system:
        return json.dumps([
            {"name": "safety-fear", "definition": "Concerns about physical/traffic safety."},
            {"name": "price-perception", "definition": "Views on cost and affordability."},
        ])
    if "apply an approved qualitative codebook" in system:
        return json.dumps([
            {"segment": 0, "code": "safety-fear", "confidence": 0.9, "support": "traffic safety"},
            {"segment": 1, "code": "price-perception", "confidence": 0.8, "support": "price seems fair"},
            {"segment": 1, "code": "invented-code", "confidence": 0.9, "support": "x"},  # dropped
            {"segment": 99, "code": "safety-fear", "confidence": 0.9, "support": "x"},   # dropped
        ])
    if "sentiment" in system.lower():
        return json.dumps([
            {"segment": 0, "sentiment": "negative"},
            {"segment": 1, "sentiment": "positive"},
            {"segment": 1, "sentiment": "elated"},  # unknown label -> dropped
        ])
    if "VERBATIM" in system:
        return json.dumps([
            {"text": "I worry about traffic safety every day.", "reason": "core fear"},
            {"text": "Scooters changed my life forever!", "reason": "FABRICATED"},  # not verbatim
        ])
    return "[]"


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_with_asset(client: TestClient, monkeypatch) -> tuple[dict[str, str], str, str]:
    monkeypatch.setattr(transcribe_core, "get_engine", lambda: FakeTranscribe())
    email = f"qual-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "Q"})
    headers = _auth(r.json()["access_token"])
    project_id = client.post("/api/projects", json={"name": "Qual II"},
                             headers=headers).json()["id"]
    asset_id = client.post(f"/api/projects/{project_id}/media",
                           files={"file": ("interview.mp3", b"fake", "audio/mpeg")},
                           headers=headers).json()["id"]
    return headers, project_id, asset_id


# ----------------------------- pure units -----------------------------

def test_verbatim_filter_drops_fabrications():
    segments = [{"start": 0.0, "end": 4.0, "text": SEGMENTS_TEXT[0]}]
    candidates = [
        {"text": "I worry about   traffic safety every day.", "reason": "ok (whitespace differs)"},
        {"text": "Something never said.", "reason": "fabricated"},
    ]
    kept = verbatim_filter(candidates, segments)
    assert len(kept) == 1
    assert kept[0]["start"] == 0.0 and kept[0]["end"] == 4.0


def test_theme_matrix_counts_and_saturation():
    matrix = theme_matrix({
        "a1": [{"segment": 0, "code": "safety"}, {"segment": 2, "code": "safety"}],
        "a2": [{"segment": 1, "code": "safety"}, {"segment": 3, "code": "price"}],
        "a3": [],
    })
    assert matrix["codes"][0] == "safety"  # most mentions first
    assert matrix["cells"]["safety"] == {"a1": 2, "a2": 1}
    sat = {row["code"]: row for row in matrix["saturation"]}
    assert sat["safety"]["sources"] == 2 and sat["safety"]["mentions"] == 3
    assert sat["price"]["sources"] == 1
    assert matrix["sources"] == ["a1", "a2", "a3"]


# ----------------------------- integration -----------------------------

def test_codebook_gate_coding_sentiment_and_synthesis(monkeypatch):
    from laboratree.labs.qual import llm as qual_llm
    monkeypatch.setattr(qual_llm, "default_complete", _fake_qual_llm)

    with TestClient(app) as client:
        headers, project_id, asset_id = _setup_with_asset(client, monkeypatch)

        # propose a codebook from the transcribed asset
        cb = client.post(f"/api/projects/{project_id}/qual/codebooks",
                         json={"asset_ids": [asset_id], "name": "Round 1"}, headers=headers)
        assert cb.status_code == 201, cb.text
        codebook = cb.json()
        assert codebook["status"] == "proposed"
        assert {c["name"] for c in codebook["codes"]} == {"safety-fear", "price-perception"}

        # coding against an UNAPPROVED codebook is refused (the HITL gate)
        blocked = client.post(f"/api/media/{asset_id}/code",
                              json={"codebook_id": codebook["id"]}, headers=headers)
        assert blocked.status_code == 409

        # approve -> coding runs; invented codes and bad segments are dropped
        client.post(f"/api/qual/codebooks/{codebook['id']}/approve", headers=headers)
        coded = client.post(f"/api/media/{asset_id}/code",
                            json={"codebook_id": codebook["id"]}, headers=headers)
        assert coded.status_code == 200, coded.text
        assignments = coded.json()["assignments"]
        assert len(assignments) == 2
        assert all(a["code"] in ("safety-fear", "price-perception") for a in assignments)

        # approved codebooks are immutable
        frozen = client.patch(f"/api/qual/codebooks/{codebook['id']}",
                              json={"codes": [{"name": "x", "definition": "y"}]}, headers=headers)
        assert frozen.status_code == 409

        # sentiment (unknown label dropped)
        sent = client.post(f"/api/media/{asset_id}/sentiment", headers=headers).json()["sentiment"]
        assert len(sent) == 2 and sent[0]["sentiment"] == "negative"

        # human override: add + read + remove
        client.patch(f"/api/media/{asset_id}/coding",
                     json={"segment": 1, "code": "safety-fear", "action": "add"}, headers=headers)
        coding = client.get(f"/api/media/{asset_id}/coding", headers=headers).json()["coding"]
        human = [a for a in coding["assignments"] if a["source"] == "human"]
        assert len(human) == 1
        client.patch(f"/api/media/{asset_id}/coding",
                     json={"segment": 1, "code": "safety-fear", "action": "remove"}, headers=headers)
        coding2 = client.get(f"/api/media/{asset_id}/coding", headers=headers).json()["coding"]
        assert not [a for a in coding2["assignments"] if a["source"] == "human"]

        # synthesis matrix over the project
        matrix = client.get(f"/api/projects/{project_id}/qual/synthesis", headers=headers).json()
        assert "safety-fear" in matrix["codes"]
        assert matrix["asset_names"][asset_id] == "interview.mp3"


def test_quotes_are_verbatim_verified_and_evidence_locked(monkeypatch):
    from laboratree.labs.qual import llm as qual_llm
    monkeypatch.setattr(qual_llm, "default_complete", _fake_qual_llm)

    with TestClient(app) as client:
        headers, project_id, asset_id = _setup_with_asset(client, monkeypatch)
        res = client.post(f"/api/media/{asset_id}/quotes", headers=headers)
        assert res.status_code == 200, res.text
        payload = res.json()
        assert len(payload["quotes"]) == 1                      # fabricated quote dropped
        assert payload["dropped_non_verbatim"] == 1
        assert payload["quotes"][0]["start"] == 0.0

        # the lock ran as a REAL run with Evidence attached
        ev = client.get(f"/api/runs/{payload['run_id']}/evidence", headers=headers)
        assert ev.status_code == 200, ev.text
        evidence = ev.json()
        assert any(e.get("kind") == "quote" for e in evidence)
        quote_row = next(e for e in evidence if e.get("kind") == "quote")
        assert "traffic safety" in str(quote_row.get("value"))


def test_qual_org_isolation(monkeypatch):
    from laboratree.labs.qual import llm as qual_llm
    monkeypatch.setattr(qual_llm, "default_complete", _fake_qual_llm)
    with TestClient(app) as client:
        headers_a, project_a, asset_a = _setup_with_asset(client, monkeypatch)
        cb = client.post(f"/api/projects/{project_a}/qual/codebooks",
                         json={"asset_ids": [asset_a]}, headers=headers_a).json()

        email = f"qual-b-{uuid.uuid4().hex[:8]}@example.com"
        rb = client.post("/api/auth/register",
                         json={"email": email, "password": "supersecret1", "full_name": "B"})
        headers_b = _auth(rb.json()["access_token"])
        assert client.post(f"/api/qual/codebooks/{cb['id']}/approve",
                           headers=headers_b).status_code == 404
        assert client.get(f"/api/media/{asset_a}/coding", headers=headers_b).status_code == 404
