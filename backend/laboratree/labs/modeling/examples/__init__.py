"""Per-model example datasets — every model gets a data subset that actually fits it.

A Linear Regression lesson needs a numeric outcome; a CNN needs image-like grids; ARIMA needs a
time series; a clustering lesson needs blobs. So each model resolves to a data PROFILE, and each
profile has a small, realistic, deterministic generator. The Learning Lab defaults to the model's
own example, so no model is ever shown on the wrong kind of data.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..lessons.resolve import lesson_keys


@dataclass(frozen=True)
class Example:
    name: str  # human label for the dropdown, e.g. "House prices (regression)"
    target: str  # the outcome column
    task: str  # "classification" | "regression" | "clustering" | ...
    csv: bytes  # the dataset as CSV bytes


# ---- profile generators (all deterministic) --------------------------------------------------


def _csv(df) -> bytes:
    return df.to_csv(index=False).encode()


def _heart(n=260):
    """Binary classification — heart-disease screening."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(1)
    age = rng.integers(35, 75, n)
    chol = rng.normal(220, 40, n).round()
    bp = rng.normal(130, 18, n).round()
    max_hr = rng.normal(150, 22, n).round()
    exercise = rng.integers(0, 5, n)
    score = 0.05 * (age - 55) + 0.01 * (chol - 220) + 0.02 * (bp - 130) - 0.02 * (max_hr - 150) - 0.3 * exercise
    y = np.where(1 / (1 + np.exp(-score)) + rng.normal(0, 0.15, n) > 0.5, "disease", "healthy")
    df = pd.DataFrame({"age": age, "cholesterol": chol, "blood_pressure": bp,
                       "max_heart_rate": max_hr, "weekly_exercise": exercise, "heart_disease": y})
    return Example("Heart-disease screening (classification)", "heart_disease", "classification", _csv(df))


def _house(n=260):
    """Regression — house prices."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(2)
    beds = rng.integers(1, 6, n)
    area = (beds * 380 + rng.normal(0, 200, n)).round().clip(300)
    age = rng.integers(0, 60, n)
    dist = rng.uniform(0.5, 25, n).round(1)
    garage = rng.integers(0, 3, n)
    price = (60 + 0.12 * area + 14 * beds - 0.6 * age - 1.8 * dist + 9 * garage
             + rng.normal(0, 25, n)).round(1)
    df = pd.DataFrame({"bedrooms": beds, "area_sqft": area, "age_years": age,
                       "distance_to_city_km": dist, "garage_spaces": garage, "price_k": price})
    return Example("House prices (regression)", "price_k", "regression", _csv(df))


def _wine(n=270):
    """Multiclass — three grape varieties from chemistry."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(3)
    rows, ys = [], []
    for c, (al, ph, col) in enumerate([(13.7, 3.0, 5.5), (12.3, 3.3, 3.2), (13.0, 3.6, 8.0)]):
        m = n // 3
        rows.append(np.column_stack([
            rng.normal(al, 0.4, m), rng.normal(ph, 0.15, m), rng.normal(col, 0.8, m),
            rng.normal(2.3 + c, 0.5, m)]))
        ys += [f"variety_{chr(65 + c)}"] * m
    X = np.vstack(rows)
    df = pd.DataFrame(X.round(2), columns=["alcohol", "ph", "color_intensity", "flavanoids"])
    df["variety"] = ys
    return Example("Wine varieties (3-class)", "variety", "classification", _csv(df))


def _ratings(n=280):
    """Ordinal — product star ratings 1..5 from drivers."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(4)
    price = rng.normal(50, 15, n).round(1)
    quality = rng.integers(1, 10, n)
    delivery_days = rng.integers(1, 10, n)
    latent = 0.25 * quality - 0.03 * price - 0.2 * delivery_days + rng.normal(0, 1, n)
    stars = pd.cut(latent, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    df = pd.DataFrame({"price": price, "quality_score": quality,
                       "delivery_days": delivery_days, "stars": stars})
    return Example("Product ratings (ordinal 1–5)", "stars", "classification", _csv(df))


def _counts(n=280):
    """Counts — clinic visits per year (overdispersed, some structural zeros)."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(5)
    age = rng.integers(18, 80, n)
    chronic = rng.integers(0, 4, n)
    insured = rng.integers(0, 2, n)
    lam = np.exp(-0.5 + 0.02 * (age - 40) + 0.5 * chronic)
    visits = rng.poisson(lam * rng.gamma(2, 0.5, n))
    visits = np.where((insured == 0) & (rng.uniform(size=n) < 0.4), 0, visits)  # never-users
    df = pd.DataFrame({"age": age, "chronic_conditions": chronic, "insured": insured,
                       "doctor_visits": visits})
    return Example("Clinic visits (counts)", "doctor_visits", "regression (counts)", _csv(df))


def _timeseries(n=140):
    """A single monthly series with trend + seasonality."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(6)
    t = np.arange(n)
    sales = (120 + 0.8 * t + 18 * np.sin(2 * np.pi * t / 12) + rng.normal(0, 6, n)).round(1)
    df = pd.DataFrame({"month": t + 1, "monthly_sales": sales})
    return Example("Monthly sales (time series)", "monthly_sales", "forecasting", _csv(df))


def _returns(n=300):
    """A daily returns series with volatility clustering (for ARCH/GARCH)."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(7)
    r = np.zeros(n)
    h = np.ones(n)
    for i in range(1, n):
        h[i] = 0.15 + 0.12 * r[i - 1] ** 2 + 0.82 * h[i - 1]
        r[i] = np.sqrt(h[i]) * rng.normal()
    df = pd.DataFrame({"day": np.arange(1, n + 1), "daily_return_pct": (r * 1.5).round(3)})
    return Example("Daily stock returns (volatility)", "daily_return_pct", "volatility", _csv(df))


def _multiseries(n=160):
    """Two co-moving macro series (for VAR / VECM)."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(8)
    gdp = np.cumsum(rng.normal(0.3, 1, n)) + 100
    inflation = 0.6 * np.roll(gdp, 1) / 10 + rng.normal(2, 0.6, n)
    df = pd.DataFrame({"quarter": np.arange(1, n + 1), "gdp_index": gdp.round(2),
                       "inflation_pct": inflation.round(2)})
    return Example("GDP & inflation (multi-series)", "gdp_index", "forecasting", _csv(df))


def _panel(n_firms=12, n_years=10):
    """A firm-year panel with a time-constant firm effect (for FE/RE/pooled)."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(9)
    rows = []
    for f in range(n_firms):
        alpha = rng.normal(0, 4)
        for yr in range(n_years):
            rnd = rng.normal(alpha * 0.7 + 5, 1.5)
            prod = 2.0 * rnd + alpha + 0.5 * yr + rng.normal(0, 1, 1)[0]
            rows.append({"firm": f, "year": 2014 + yr, "rnd_spend": round(rnd, 2),
                         "productivity": round(prod, 2)})
    return Example("Firm productivity (panel)", "productivity", "regression (panel)",
                   _csv(pd.DataFrame(rows)))


def _clusters(n=180):
    """Customer segments — three blobs in spend/frequency (for clustering)."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(10)
    centers = [(20, 2), (60, 8), (110, 20)]
    rows, seg = [], []
    for i, (s, f) in enumerate(centers):
        m = n // 3
        rows.append(np.column_stack([rng.normal(s, 8, m), rng.normal(f, 2, m),
                                     rng.normal(30 + i * 10, 6, m)]))
        seg += [f"segment_{i + 1}"] * m
    X = np.vstack(rows)
    df = pd.DataFrame(X.round(1), columns=["monthly_spend", "visits_per_month", "avg_basket"])
    df["segment"] = seg  # a label exists but clustering ignores it
    return Example("Customer segments (clustering)", "segment", "clustering", _csv(df))


def _anomaly(n=200):
    """Transactions — mostly normal with a handful of fraud outliers."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(11)
    amount = np.abs(rng.normal(60, 20, n))
    hour = rng.integers(6, 23, n)
    dist = np.abs(rng.normal(5, 3, n))
    k = 10
    idx = rng.choice(n, k, replace=False)
    amount[idx] = rng.uniform(400, 900, k)
    hour[idx] = rng.integers(0, 5, k)
    dist[idx] = rng.uniform(40, 90, k)
    df = pd.DataFrame({"amount": amount.round(1), "hour": hour, "distance_km": dist.round(1),
                       "is_fraud": np.where(np.isin(np.arange(n), idx), "fraud", "normal")})
    return Example("Card transactions (anomaly)", "is_fraud", "anomaly detection", _csv(df))


def _image(n=200):
    """A tiny 8×8 'image' dataset — cats vs dogs as textured grids (for CNN)."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(12)
    rows, labels = [], []
    for i in range(n):
        cat = i % 2 == 0
        g = rng.normal(0.3, 0.1, (8, 8))
        if cat:  # cats: bright pointed 'ears' at the top corners
            g[0:2, 0:2] += 0.6
            g[0:2, 6:8] += 0.6
        else:  # dogs: a bright horizontal 'snout' band across the middle
            g[4:6, 2:6] += 0.6
        rows.append(g.clip(0, 1).round(2).flatten())
        labels.append("cat" if cat else "dog")
    cols = [f"px{r}_{c}" for r in range(8) for c in range(8)]
    df = pd.DataFrame(rows, columns=cols)
    df["animal"] = labels
    return Example("Cats vs dogs (8×8 tiny images)", "animal", "classification", _csv(df))


def _sequence(n=220):
    """A lagged sensor sequence (for RNN/LSTM)."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(13)
    base = np.sin(np.arange(n) / 6) + rng.normal(0, 0.2, n)
    cols = {f"t_minus_{k}": np.round(np.roll(base, k), 3) for k in range(8, 0, -1)}
    nxt = np.round(base, 3)
    df = pd.DataFrame(cols)
    df["next_value"] = nxt
    return Example("Sensor sequence (recurrent)", "next_value", "regression", _csv(df.iloc[8:]))


def _causal(n=400):
    """A generic experiment table — the causal tracers estimate their own designs, but the
    lesson still needs some rows to attach to."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(14)
    treat = rng.integers(0, 2, n)
    outcome = (10 + 2.0 * treat + rng.normal(0, 3, n)).round(2)
    df = pd.DataFrame({"treatment": treat, "post_period": rng.integers(0, 2, n),
                       "score": rng.normal(0, 1, n).round(2), "outcome": outcome})
    return Example("Treatment experiment (causal)", "outcome", "causal effect", _csv(df))


_PROFILES = {
    "tabular_binary": _heart, "tabular_regression": _house, "multiclass": _wine,
    "ordinal": _ratings, "counts": _counts, "timeseries": _timeseries, "returns": _returns,
    "multiseries": _multiseries, "panel": _panel, "clustering": _clusters, "anomaly": _anomaly,
    "image_grid": _image, "sequence": _sequence, "causal": _causal,
}

# per-key overrides where the family/task isn't enough to pick the right shape
_KEY_PROFILE = {
    "cnn": "image_grid", "rnn": "sequence",
    "ar": "timeseries", "ma": "timeseries", "arma": "timeseries", "arima": "timeseries",
    "sarima": "timeseries", "ets": "timeseries",
    "arch": "returns", "garch": "returns", "egarch": "returns", "gjr_garch": "returns",
    "var": "multiseries", "vecm": "multiseries",
    "pooled_ols": "panel", "fixed_effects": "panel", "random_effects": "panel",
    "rct": "causal", "did": "causal", "iv": "causal", "rdd": "causal",
    "poisson": "counts", "negative_binomial": "counts", "zip": "counts",
    "multinomial_logit": "multiclass", "ordered_logit": "ordinal", "ordered_probit": "ordinal",
}


def _profile_for(key: str, family: str, task: str) -> str:
    if key in _KEY_PROFILE:
        return _KEY_PROFILE[key]
    if family == "clustering":
        return "clustering"
    if family == "anomaly":
        return "anomaly"
    t = (task or "").lower()
    if t.startswith("regression"):
        return "tabular_regression"
    return "tabular_binary"  # classification + auto ("classification / regression") default


def example_for(model: str) -> Example:
    """The example dataset a model should default to (resolves free text → its data profile)."""
    from ..lessons.catalog import CATALOG

    keys = lesson_keys(model)
    entry = next((e for e in CATALOG if e.key in keys), None)
    key = entry.key if entry else keys[0]
    family = entry.family if entry else keys[-1]
    task = entry.task if entry else ""
    return _PROFILES[_profile_for(key, family, task)]()


__all__ = ["Example", "example_for"]
