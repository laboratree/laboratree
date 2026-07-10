"""Phase 14 (Tabulation) tests: raking, crosstab significance letters, survey metrics.

Pure math with hand-computed goldens + one runs-API integration check.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.labs.tabulation.crosstab import crosstab
from laboratree.labs.tabulation.metrics import mean_ci, nps, top2box
from laboratree.labs.tabulation.weights import rake
from laboratree.main import app

# ----------------------------- raking -----------------------------

def test_rake_hits_target_margins():
    # 80 men / 20 women observed; target 50/50
    records = [{"gender": "m"}] * 80 + [{"gender": "f"}] * 20
    result = rake(records, {"gender": {"m": 0.5, "f": 0.5}})
    assert result["converged"] is True
    achieved = result["achieved"]["gender"]
    assert abs(achieved["m"] - 0.5) < 1e-3 and abs(achieved["f"] - 0.5) < 1e-3
    # men down-weighted (0.625), women up-weighted (2.5)
    assert abs(result["weights"][0] - 0.625) < 1e-2
    assert abs(result["weights"][-1] - 2.5) < 1e-2
    # Kish: eff N = (Σw)²/Σw² = 100² / (80*0.625² + 20*2.5²) = 10000/156.25 = 64
    assert abs(result["effective_n"] - 64.0) < 0.5
    assert abs(result["design_effect"] - 100 / 64.0) < 0.02


def test_rake_two_dimensions_and_no_margins():
    records = (
        [{"g": "m", "age": "young"}] * 40 + [{"g": "m", "age": "old"}] * 40
        + [{"g": "f", "age": "young"}] * 10 + [{"g": "f", "age": "old"}] * 10
    )
    result = rake(records, {"g": {"m": 0.5, "f": 0.5}, "age": {"young": 0.5, "old": 0.5}})
    assert result["converged"]
    assert abs(result["achieved"]["g"]["f"] - 0.5) < 1e-3
    assert abs(result["achieved"]["age"]["young"] - 0.5) < 1e-3
    # no margins -> unit weights
    flat = rake(records, {})
    assert flat["weights"] == [1.0] * len(records)
    assert flat["design_effect"] == 1.0


# ----------------------------- crosstab -----------------------------

def test_crosstab_percentages_and_significance_letters():
    # men: 80% yes (n=100); women: 20% yes (n=100) -> yes row: A > B
    records = (
        [{"gender": "m", "intent": "yes"}] * 80 + [{"gender": "m", "intent": "no"}] * 20
        + [{"gender": "f", "intent": "yes"}] * 20 + [{"gender": "f", "intent": "no"}] * 80
    )
    table = crosstab(records, banner="gender", stub="intent")
    cols = {c["category"]: c for c in table["columns"]}
    assert cols["f"]["letter"] == "A" and cols["m"]["letter"] == "B"  # sorted alphabetically
    assert cols["m"]["base"] == 100.0

    yes_row = next(r for r in table["rows"] if r["stub_value"] == "yes")
    assert yes_row["cells"]["m"]["pct"] == 80.0
    assert yes_row["cells"]["f"]["pct"] == 20.0
    assert yes_row["cells"]["m"]["sig_higher_than"] == "A"   # men higher than women
    assert yes_row["cells"]["f"]["sig_higher_than"] == ""
    no_row = next(r for r in table["rows"] if r["stub_value"] == "no")
    assert no_row["cells"]["f"]["sig_higher_than"] == "B"

    assert table["chi_square"] is not None and table["p_value"] < 0.001
    assert table["dof"] == 1
    assert table["total_n"] == 200


def test_crosstab_small_bases_never_tested_and_weighting():
    # bases of 10 are below MIN_BASE_FOR_TEST -> no letters even at 90% vs 10%
    records = (
        [{"g": "a", "v": "y"}] * 9 + [{"g": "a", "v": "n"}] * 1
        + [{"g": "b", "v": "y"}] * 1 + [{"g": "b", "v": "n"}] * 9
    )
    table = crosstab(records, banner="g", stub="v")
    y_row = next(r for r in table["rows"] if r["stub_value"] == "y")
    assert y_row["cells"]["a"]["sig_higher_than"] == ""

    # weighting changes percentages: double-weight the 'n' answers in column a
    weighted = [{**r, "_w": 2.0 if r["v"] == "n" else 1.0} for r in records]
    tw = crosstab(weighted, banner="g", stub="v", weight_column="_w")
    y_a = next(r for r in tw["rows"] if r["stub_value"] == "y")["cells"]["a"]["pct"]
    assert y_a == round(100 * 9 / (9 + 2), 1)  # 9 vs weighted base 11


# ----------------------------- metrics -----------------------------

def test_nps_top2box_and_mean_ci():
    # 5 promoters (10), 3 passives (8), 2 detractors (3) -> NPS = 50-20 = 30
    records = [{"s": 10}] * 5 + [{"s": 8}] * 3 + [{"s": 3}] * 2
    result = nps(records, "s")
    assert result["nps"] == 30.0
    assert result["promoters_pct"] == 50.0
    assert result["detractors_pct"] == 20.0

    # scale 1..5: top2box counts 4s and 5s
    likert = [{"q": 5}] * 2 + [{"q": 4}] * 3 + [{"q": 2}] * 5
    assert top2box(likert, "q", scale_max=5)["top2box_pct"] == 50.0

    # unweighted mean of [1..5] = 3.0, symmetric CI
    vals = [{"m": v} for v in (1, 2, 3, 4, 5)]
    m = mean_ci(vals, "m")
    assert m["mean"] == 3.0
    assert abs((m["ci_high"] - 3.0) - (3.0 - m["ci_low"])) < 1e-9
    assert m["effective_n"] == 5.0

    # non-numeric values are ignored
    assert nps([{"s": "x"}, {"s": None}], "s")["n"] == 0


# ----------------------------- integration: runs API -----------------------------

def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_crosstab_component_via_runs_api():
    with TestClient(app) as client:
        email = f"tab-{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/auth/register",
                        json={"email": email, "password": "supersecret1", "full_name": "T"})
        headers = _auth(r.json()["access_token"])
        project_id = client.post("/api/projects", json={"name": "Tab"},
                                 headers=headers).json()["id"]
        dataset = (
            [{"gender": "m", "intent": "yes"}] * 40 + [{"gender": "m", "intent": "no"}] * 10
            + [{"gender": "f", "intent": "yes"}] * 10 + [{"gender": "f", "intent": "no"}] * 40
        )
        run = client.post(f"/api/projects/{project_id}/runs",
                          json={"component_id": "analyzer.crosstab",
                                "params": {"banner": "gender", "stub": "intent"},
                                "dataset": dataset},
                          headers=headers)
        assert run.status_code == 201, run.text
        body = run.json()
        assert body["run"]["status"] == "succeeded"
        assert body["evidence_count"] >= 1
        assert body["preview"]["chi_square"] is not None
