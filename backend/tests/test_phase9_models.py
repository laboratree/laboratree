"""Model Lab expansion: random forest, gradient boosting, econometrics (logit/probit/arima)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from laboratree.core.registry import REGISTRY
from laboratree_sdk import RunContext


class _Sink:
    def record(self, *, label, value, kind="metric", **m):
        return "e"


def _run(component_id, params, df):
    ctx = RunContext(run_id="r", org_id="o", params=params, inputs={"dataset": df}, evidence=_Sink())
    return REGISTRY.create(component_id).run(ctx)


def _binary_df(n=80):
    rng = np.random.default_rng(0)
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    p = 1 / (1 + np.exp(-(1.6 * x1 - 1.1 * x2)))
    y = (rng.uniform(size=n) < p).astype(int)
    return pd.DataFrame({"x1": x1, "x2": x2, "y": y})


def test_random_forest_classifies_iris():
    from sklearn.datasets import load_iris

    out = _run("model.ml.random_forest", {"target": "target"}, load_iris(as_frame=True).frame)
    assert out["task"] == "classification" and out["metrics"]["accuracy"] > 0.6


def test_gradient_boosting_classifies_iris():
    from sklearn.datasets import load_iris

    out = _run("model.ml.gradient_boosting", {"target": "target"}, load_iris(as_frame=True).frame)
    assert out["metrics"]["accuracy"] > 0.6


def test_logit_binary():
    out = _run("model.econometrics.logit", {"target": "y"}, _binary_df())
    assert "accuracy" in out["metrics"] and "pseudo_r2" in out["metrics"]
    assert "const" in out["coefficients"]


def test_probit_binary():
    out = _run("model.econometrics.probit", {"target": "y"}, _binary_df())
    assert "pseudo_r2" in out["metrics"]


def test_arima_reports_aic():
    rng = np.random.default_rng(1)
    series = np.cumsum(rng.normal(size=48)) + 50
    out = _run("model.econometrics.arima", {"value_column": "sales", "order": [1, 1, 1]},
               pd.DataFrame({"sales": series}))
    assert "aic" in out["metrics"] and out["n_obs"] == 48


def _panel_df(n_firms=8, n_periods=12):
    """Firm-year panel where firm 'baggage' confounds pooled OLS but not FE."""
    rng = np.random.default_rng(7)
    rows = []
    for firm in range(n_firms):
        alpha = rng.normal(0, 3)  # time-constant firm effect, correlated with x
        for _t in range(n_periods):
            x = rng.normal(alpha * 0.8, 1)  # regressor correlates with the firm effect
            y = 2.0 * x + alpha + rng.normal(0, 0.5)
            rows.append({"firm": firm, "rnd_spend": x, "productivity": y})
    return pd.DataFrame(rows)


def test_pooled_ols_runs_on_panel():
    out = _run("model.econometrics.pooled_ols",
               {"target": "productivity", "entity_column": "firm"}, _panel_df())
    assert out["task"] == "regression" and out["entity_column"] == "firm"
    assert "rnd_spend" in out["coefficients"]


def test_fixed_effects_removes_entity_baggage():
    out = _run("model.econometrics.fixed_effects",
               {"target": "productivity", "entity_column": "firm"}, _panel_df())
    assert out["n_entities"] == 8
    # the within estimator should recover the true slope (2.0) despite the confounder
    assert abs(out["coefficients"]["rnd_spend"] - 2.0) < 0.3


def test_random_effects_runs_on_panel():
    out = _run("model.econometrics.random_effects",
               {"target": "productivity", "entity_column": "firm"}, _panel_df())
    assert out["n_entities"] == 8
    assert "rnd_spend" in out["coefficients"] and "Group Var" not in out["coefficients"]


# ---- volatility / causal / stats models --------------------------------------------------------


def _garch_series(n=300):
    rng = np.random.default_rng(3)
    r = np.zeros(n)
    h = np.ones(n)
    for t in range(1, n):
        h[t] = 0.1 + 0.1 * r[t - 1] ** 2 + 0.85 * h[t - 1]
        r[t] = np.sqrt(h[t]) * rng.normal()
    return pd.DataFrame({"ret": r.round(4)})


def test_garch_beats_arch_on_clustered_vol():
    g = _run("model.econometrics.garch", {"value_column": "ret", "p": 1, "q": 1}, _garch_series())
    a = _run("model.econometrics.arch", {"value_column": "ret", "p": 1}, _garch_series())
    assert g["metrics"]["aic"] < a["metrics"]["aic"]  # GARCH fits clustered vol better
    assert "omega" in g["coefficients"]


def test_rct_recovers_effect():
    rng = np.random.default_rng(0)
    n = 300
    t = rng.integers(0, 2, n)
    y = (2.0 * t + rng.normal(0, 1, n)).round(3)
    out = _run("model.causal.rct", {"outcome": "y", "treatment": "t"}, pd.DataFrame({"y": y, "t": t}))
    assert abs(out["metrics"]["ate"] - 2.0) < 0.4 and out["metrics"]["p_value"] < 0.01


def test_did_recovers_interaction():
    rng = np.random.default_rng(0)
    n = 400
    g, post = rng.integers(0, 2, n), rng.integers(0, 2, n)
    y = (1.0 * g + 0.5 * post + 1.5 * g * post + rng.normal(0, 1, n)).round(3)
    out = _run("model.causal.did", {"outcome": "y", "treated_group": "g", "post_period": "p"},
               pd.DataFrame({"y": y, "g": g, "p": post}))
    assert abs(out["metrics"]["did_effect"] - 1.5) < 0.5


def test_iv_beats_confounded_ols():
    rng = np.random.default_rng(0)
    n = 500
    z, u = rng.normal(size=n), rng.normal(size=n)
    x = 0.8 * z + u + rng.normal(0, 0.5, n)
    y = 1.5 * x + 2 * u + rng.normal(0, 0.5, n)  # u confounds → OLS biased up
    out = _run("model.causal.iv", {"outcome": "y", "endogenous": "x", "instrument": "z"},
               pd.DataFrame({"y": y, "x": x, "z": z}))
    assert abs(out["metrics"]["iv_effect"] - 1.5) < abs(out["metrics"]["naive_ols_effect"] - 1.5)
    assert out["metrics"]["first_stage_F"] > 10 and not out["weak_instrument"]


def test_quantile_and_negbinomial_and_var():
    rng = np.random.default_rng(0)
    n = 200
    df = pd.DataFrame({"x1": rng.normal(size=n)})
    df["y"] = (2 * df.x1 + 3 * rng.normal(size=n)).round(3)
    q = _run("model.econometrics.quantile", {"target": "y", "quantile": 0.9}, df)
    assert q["metrics"]["quantile"] == 0.9 and "pinball_loss" in q["metrics"]

    cnt = rng.poisson(np.exp(0.5 + 0.3 * rng.normal(size=n)) * rng.gamma(2, 0.5, n))
    nb = _run("model.econometrics.negative_binomial", {"target": "c"},
              pd.DataFrame({"c": cnt, "x": rng.normal(size=n)}))
    assert nb["metrics"]["dispersion"] > 1.0  # overdispersed

    a = np.cumsum(rng.normal(size=120))
    b = 0.5 * np.roll(a, 1) + rng.normal(size=120)
    v = _run("model.econometrics.var", {"value_columns": ["a", "b"], "lags": 2},
             pd.DataFrame({"a": a, "b": b}))
    assert v["metrics"]["lags"] == 2 and len(v["series"]) == 2


def test_wave2_timeseries_and_regression_variants():
    rng = np.random.default_rng(5)
    s = pd.DataFrame({"v": np.cumsum(rng.normal(size=100)).round(3)})
    assert "aic" in _run("model.econometrics.ar", {"value_column": "v", "order": 2}, s)["metrics"]
    assert "aic" in _run("model.econometrics.ma", {"value_column": "v", "order": 1}, s)["metrics"]
    assert "aic" in _run("model.econometrics.arma", {"value_column": "v", "p": 1, "q": 1}, s)["metrics"]
    a = np.cumsum(rng.normal(size=120))
    coint = pd.DataFrame({"a": a, "b": a + rng.normal(0, 0.5, 120)})
    assert _run("model.econometrics.vecm", {"value_columns": ["a", "b"]}, coint)["metrics"]["coint_rank"] == 1

    reg = pd.DataFrame({"x1": rng.normal(size=200)})
    reg["y"] = (2 * reg.x1 + rng.normal(0, 1, 200)).round(3)
    for cid in ["wls", "gls", "robust"]:
        out = _run(f"model.econometrics.{cid}", {"target": "y"}, reg)
        assert out["metrics"]["rmse"] > 0 and "const" in out["coefficients"]


def test_wave2_volatility_variants_and_choice_and_rdd():
    rng = np.random.default_rng(6)
    r = pd.DataFrame({"ret": rng.normal(0, 1, 300).round(3)})
    assert "aic" in _run("model.econometrics.egarch", {"value_column": "ret"}, r)["metrics"]
    assert "aic" in _run("model.econometrics.gjr_garch", {"value_column": "ret"}, r)["metrics"]

    n = 300
    x = rng.normal(size=(n, 2))
    cats = pd.cut(x[:, 0] + rng.normal(0, 1, n), 3, labels=["lo", "mid", "hi"])
    dfc = pd.DataFrame({"x1": x[:, 0].round(2), "x2": x[:, 1].round(2), "y": cats})
    assert _run("model.econometrics.multinomial_logit", {"target": "y"}, dfc)["metrics"]["n_classes"] == 3
    assert _run("model.econometrics.ordered_logit", {"target": "y"}, dfc)["metrics"]["n_classes"] == 3
    assert _run("model.econometrics.ordered_probit", {"target": "y"}, dfc)["metrics"]["n_classes"] == 3

    cnt = np.where(rng.uniform(size=n) < 0.4, 0, rng.poisson(3, n))
    zip_out = _run("model.econometrics.zip", {"target": "c"},
                   pd.DataFrame({"c": cnt, "x": rng.normal(size=n)}))
    assert zip_out["metrics"]["zero_share"] > 0.2

    run = np.linspace(-5, 5, 200)
    y = 3 * (run >= 0) + 0.5 * run + rng.normal(0, 1, 200)
    rdd = _run("model.causal.rdd", {"outcome": "y", "running": "r", "cutoff": 0},
               pd.DataFrame({"y": y, "r": run}))
    assert abs(rdd["metrics"]["rd_effect"] - 3.0) < 1.0 and rdd["metrics"]["p_value"] < 0.05
