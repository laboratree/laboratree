"""Demo-data seeder tests: realistic education data (correlations hold) + end-to-end seed."""

from __future__ import annotations

import uuid
from statistics import mean

from fastapi.testclient import TestClient
from laboratree.labs.demo import (
    PILOT_EFFECT,
    TREATMENT_VILLAGES,
    education_records,
    education_survey_structure,
    pilot_panel_records,
)
from laboratree.main import app

# ----------------------------- pure: realistic data -----------------------------

def test_education_data_is_deterministic_and_has_real_correlations():
    a = education_records(n=300, seed=1729)
    assert education_records(n=300, seed=1729) == a          # deterministic
    assert len(a) == 300
    assert set(a[0]) >= {"village", "gender", "distance_km", "income_band",
                         "attendance_rate", "exam_score", "dropout"}

    # dropout should be MORE common among students far from school than those close
    far = [r for r in a if r["distance_km"] >= 5]
    near = [r for r in a if r["distance_km"] <= 2]
    far_dropout = mean(1 if r["dropout"] == "yes" else 0 for r in far)
    near_dropout = mean(1 if r["dropout"] == "yes" else 0 for r in near)
    assert far_dropout > near_dropout

    # attendance should rise with income (low < high on average)
    low = mean(r["attendance_rate"] for r in a if r["income_band"] == "low")
    high = mean(r["attendance_rate"] for r in a if r["income_band"] == "high")
    assert high > low

    # exam scores track attendance (a real, findable signal for the modelling stage)
    hi_att = mean(r["exam_score"] for r in a if r["attendance_rate"] >= 0.8)
    lo_att = mean(r["exam_score"] for r in a if r["attendance_rate"] < 0.6)
    assert hi_att > lo_att


def test_pilot_panel_did_recovers_planted_effect():
    rows = pilot_panel_records(n_per_period=200, seed=4104)
    assert pilot_panel_records(n_per_period=200, seed=4104) == rows   # deterministic
    assert len(rows) == 400                                            # 200 students x 2 periods
    assert all(r["treated"] == (1 if r["village"] in TREATMENT_VILLAGES else 0) for r in rows)

    # hand-computed difference-in-differences must recover the planted effect
    def cell_mean(treated: int, post: int) -> float:
        vals = [r["attendance_rate"] for r in rows if r["treated"] == treated and r["post"] == post]
        return mean(vals)

    did = (cell_mean(1, 1) - cell_mean(1, 0)) - (cell_mean(0, 1) - cell_mean(0, 0))
    assert abs(did - PILOT_EFFECT) < 0.02   # noise sigma 0.03, n=400 -> tight recovery


def test_survey_structure_is_valid():
    from laboratree.labs.fieldwork.runtime import validate_structure
    assert validate_structure(education_survey_structure()) == []


# ----------------------------- integration -----------------------------

def test_seed_creates_dataset_evidence_survey_and_cohort():
    with TestClient(app) as client:
        email = f"demo-{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/auth/register",
                        json={"email": email, "password": "supersecret1", "full_name": "D"})
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        project_id = client.post("/api/projects", json={"name": "Demo"},
                                 headers=headers).json()["id"]

        seed = client.post(f"/api/projects/{project_id}/demo/seed",
                           json={"scenario": "ngo_education", "n_rows": 120, "n_personas": 8},
                           headers=headers)
        assert seed.status_code == 200, seed.text
        body = seed.json()
        assert body["n_rows"] == 120
        assert "dropout" in body["columns"]
        # the analysis runs produced real Evidence in the ledger
        assert body["evidence_total"] >= 3
        assert all("run_id" in run for run in body["runs"])       # every analysis ran
        assert body["personas"] == 8

        # impact evaluation genuinely ran: DiD on the pilot panel with the planted effect
        did_run = next(r for r in body["runs"] if r["component_id"] == "model.causal.did")
        assert "run_id" in did_run and did_run["evidence"] >= 1
        assert body["pilot_dataset_id"]
        assert len(body["pilot_rows"]) == 400
        run_detail = client.get(f"/api/runs/{did_run['run_id']}/evidence", headers=headers).json()
        did_effect = next(e["value"] for e in run_detail if e["label"] == "did_effect")
        assert abs(float(did_effect) - PILOT_EFFECT) < 0.02

        # the dataset is real and downloadable via the evidence picker's project scope
        evidence = client.get(f"/api/projects/{project_id}/evidence", headers=headers).json()
        assert len(evidence) >= 3

        # the seeded survey exists as a draft
        surveys = client.get(f"/api/projects/{project_id}/surveys", headers=headers).json()
        assert any(s["title"].startswith("Rural education") for s in surveys)

        # the persona cohort exists
        cohorts = client.get(f"/api/projects/{project_id}/persona-cohorts", headers=headers).json()
        assert cohorts and cohorts[0]["n"] == 8

        # unknown scenario is rejected
        bad = client.post(f"/api/projects/{project_id}/demo/seed",
                          json={"scenario": "nope"}, headers=headers)
        assert bad.status_code == 422
