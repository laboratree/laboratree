"""Persona Lab behavioral grounding tests: prospect theory, discrete choice, Bass diffusion.

Pure math with hand-checkable properties + a registry/runs integration check.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.labs.synth.behavioral import (
    bass_adoption,
    choice_shares,
    logit_shares,
    price_elasticity,
    prospect_choice,
    prospect_value,
)
from laboratree.main import app

# ----------------------------- prospect theory -----------------------------

def test_prospect_theory_loss_aversion():
    # a loss looms larger than an equivalent gain (lambda = 2.25)
    gain = prospect_value(100)
    loss = prospect_value(-100)
    assert gain > 0 and loss < 0
    assert abs(loss) > gain
    assert abs(loss) == round(2.25 * gain / 1, 10) or abs(abs(loss) / gain - 2.25) < 1e-9

    # reference point matters: 150 framed against a 200 expectation is a loss
    assert prospect_value(150, reference=200) < 0
    # a risk-averse chooser prefers the smaller sure gain shape around the reference
    choice = prospect_choice(50, -50, reference=0)
    assert choice["prefers"] == "a"


# ----------------------------- discrete choice (MNL) -----------------------------

def test_logit_shares_sum_to_one_and_equal_for_equal_utility():
    shares = logit_shares([1.0, 1.0, 1.0])
    assert abs(sum(shares) - 1.0) < 1e-5
    assert all(abs(s - 1 / 3) < 1e-5 for s in shares)
    # higher utility -> higher share
    ranked = logit_shares([0.0, 1.0, 2.0])
    assert ranked[2] > ranked[1] > ranked[0]


def test_choice_shares_and_price_elasticity():
    # two products; price coefficient negative -> cheaper product wins share
    alts = [{"price": 10.0, "quality": 1.0}, {"price": 20.0, "quality": 1.0}]
    weights = {"price": -0.1, "quality": 1.0}
    shares = choice_shares(alts, weights)
    assert abs(sum(s["share"] for s in shares) - 1.0) < 1e-5
    assert shares[0]["share"] > shares[1]["share"]  # cheaper product preferred

    # own-price elasticity is negative (raising a product's price lowers its share)
    e = price_elasticity(alts, weights, target_index=0)
    assert e < 0


# ----------------------------- Bass diffusion -----------------------------

def test_bass_diffusion_curve_properties():
    curve = bass_adoption(p=0.03, q=0.38, market=1000, periods=20)
    cumulative = [row["cumulative"] for row in curve]
    # monotonic non-decreasing, bounded by the market, penetration in [0, 1]
    assert all(b >= a for a, b in zip(cumulative, cumulative[1:], strict=False))
    assert cumulative[-1] <= 1000 + 1e-6
    assert all(0 <= row["penetration"] <= 1 + 1e-9 for row in curve)
    # with imitation q > p, the peak of NEW adopters is in the interior (not period 1)
    peak = max(curve, key=lambda r: r["new_adopters"])
    assert peak["period"] > 1
    # most of the market eventually adopts
    assert curve[-1]["penetration"] > 0.8


# ----------------------------- integration: registered components -----------------------------

def test_behavioral_components_registered_and_runnable():
    with TestClient(app) as client:
        comps = {c["id"] for c in client.get("/api/components").json()["components"]}
        assert "analyzer.discrete_choice" in comps
        assert "analyzer.bass_diffusion" in comps

        email = f"beh-{uuid.uuid4().hex[:10]}@example.com"
        r = client.post("/api/auth/register",
                        json={"email": email, "password": "supersecret1", "full_name": "B"})
        headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        project_id = client.post("/api/projects", json={"name": "Beh"},
                                 headers=headers).json()["id"]
        run = client.post(f"/api/projects/{project_id}/runs",
                          json={"component_id": "analyzer.bass_diffusion",
                                "params": {"market": 500, "periods": 8}, "dataset": []},
                          headers=headers)
        assert run.status_code == 201, run.text
        assert run.json()["run"]["status"] == "succeeded"
        assert run.json()["evidence_count"] >= 1
        assert len(run.json()["preview"]["curve"]) == 8
