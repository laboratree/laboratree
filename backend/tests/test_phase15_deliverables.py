"""Phase 15 (Deliverables) tests: block validation (U1 Evidence enforcement), render, share.

Requires live Postgres. Uses a real component run to produce project Evidence to cite.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.labs.deliverables import render_html, validate_blocks
from laboratree.main import app

# ----------------------------- pure: validation -----------------------------

def test_validate_blocks_enforces_evidence():
    valid = {"ev-1", "ev-2"}
    blocks = [
        {"type": "heading", "text": "Findings"},
        {"type": "text", "text": "Some prose."},
        {"type": "stat", "evidence_id": "ev-1", "caption": "Intent"},   # ok
        {"type": "stat", "caption": "no id"},                            # missing id
        {"type": "quote", "evidence_id": "ev-nope"},                     # unknown id
        {"type": "mystery"},                                             # bad type
    ]
    errors = validate_blocks(blocks, valid)
    joined = " | ".join(errors)
    assert "must bind an evidence_id" in joined
    assert "is not in this project" in joined
    assert "unknown type" in joined
    # the valid blocks produce no error
    assert validate_blocks(blocks[:3], valid) == []


def test_render_html_shows_values_and_provenance():
    evidence_map = {
        "ev-1": {"label": "intent_pct", "kind": "metric", "value": 41.0, "run_id": "abcd1234ef"},
        "ev-2": {"label": "quote_1", "kind": "quote",
                 "value": {"text": "Safety is my main concern", "start": 12.0}, "run_id": "run2"},
    }
    blocks = [
        {"type": "heading", "text": "Key findings"},
        {"type": "stat", "evidence_id": "ev-1", "caption": "Intent to adopt"},
        {"type": "quote", "evidence_id": "ev-2"},
        {"type": "stat", "evidence_id": "missing"},  # unbacked -> visible warning
    ]
    out = render_html("GreenCommute Report", blocks, evidence_map)
    assert "GreenCommute Report" in out
    assert "41.0" in out
    assert "Safety is my main concern" in out
    assert "intent_pct" in out           # provenance label
    assert "abcd1234" in out             # run id (truncated)
    assert "unbacked" in out             # the missing-evidence block is flagged, not silent


# ----------------------------- integration -----------------------------

def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_with_evidence(client: TestClient) -> tuple[dict[str, str], str, str]:
    """Register, make a project, run a component to produce citable Evidence."""
    email = f"deliv-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "D"})
    headers = _auth(r.json()["access_token"])
    project_id = client.post("/api/projects", json={"name": "Deliv"}, headers=headers).json()["id"]
    # a metrics run emits Evidence into the project for the report to cite
    client.post(f"/api/projects/{project_id}/runs",
                json={"component_id": "analyzer.survey_metrics",
                      "params": {"column": "x", "metric": "mean"},
                      "dataset": [{"x": 3}, {"x": 4}, {"x": 5}]},
                headers=headers)
    ev = client.get(f"/api/projects/{project_id}/evidence", headers=headers).json()
    assert ev, "expected project evidence from the run"
    return headers, project_id, ev[0]["id"]


def test_report_crud_evidence_enforcement_and_render():
    with TestClient(app) as client:
        headers, project_id, evidence_id = _setup_with_evidence(client)

        rid = client.post(f"/api/projects/{project_id}/reports", headers=headers).json()["id"]

        # a hand-typed / unknown-evidence stat is rejected
        bad = client.patch(f"/api/reports/{rid}",
                           json={"blocks": [{"type": "stat", "evidence_id": str(uuid.uuid4())}]},
                           headers=headers)
        assert bad.status_code == 422
        assert "errors" in bad.json()["detail"]

        # binding real project Evidence is accepted
        good = client.patch(f"/api/reports/{rid}",
                            json={"title": "Client deck",
                                  "blocks": [
                                      {"type": "heading", "text": "Summary"},
                                      {"type": "stat", "evidence_id": evidence_id, "caption": "Mean"},
                                  ]},
                            headers=headers)
        assert good.status_code == 200, good.text
        assert good.json()["title"] == "Client deck"

        # render returns branded HTML containing the evidence-bound value
        html = client.get(f"/api/reports/{rid}/render", headers=headers)
        assert html.status_code == 200
        assert "Client deck" in html.text and "Laboratree" in html.text


def test_report_share_public_and_isolation():
    with TestClient(app) as client:
        headers, project_id, evidence_id = _setup_with_evidence(client)
        rid = client.post(f"/api/projects/{project_id}/reports", headers=headers).json()["id"]
        client.patch(f"/api/reports/{rid}",
                     json={"blocks": [{"type": "stat", "evidence_id": evidence_id}]}, headers=headers)

        token = client.post(f"/api/reports/{rid}/share", headers=headers).json()["token"]
        pub = client.get(f"/public/reports/{token}")
        assert pub.status_code == 200 and "Laboratree" in pub.text

        # revoke -> gone
        client.post(f"/api/reports/{rid}/unshare", headers=headers)
        assert client.get(f"/public/reports/{token}").status_code == 404
        assert client.get("/public/reports/bogus").status_code == 404

        # org isolation
        rb = client.post("/api/auth/register",
                         json={"email": f"b-{uuid.uuid4().hex[:8]}@example.com",
                               "password": "supersecret1", "full_name": "B"})
        headers_b = _auth(rb.json()["access_token"])
        assert client.get(f"/api/reports/{rid}", headers=headers_b).status_code == 404
