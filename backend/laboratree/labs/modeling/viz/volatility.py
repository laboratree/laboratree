"""Volatility tracer — real ARCH/GARCH on the student's series.

Treats the target (or the highest-variance numeric column) as a return series and fits the real
model, emitting the conditional-volatility path and squared returns so the lesson animates the
actual volatility clustering: calm and turbulent stretches, and the variance forecast that
rides on them.
"""

from __future__ import annotations

from . import register_tracer
from .common import resolve_params, table_rows
from .schema import ModelTrace

MAX_T = 160

SPEC = [
    {"key": "p", "label": "ARCH order (p)", "type": "int", "default": 1, "min": 1, "max": 3,
     "step": 1, "help": "How many recent squared shocks feed today's variance."},
    {"key": "q", "label": "GARCH order (q)", "type": "int", "default": 1, "min": 0, "max": 3,
     "step": 1, "help": "How many recent variances feed today's (0 = pure ARCH)."},
]


@register_tracer("volatility")
def trace_volatility(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    import numpy as np

    params = dict(params or {})
    model = str(params.pop("_model", "garch") or "garch")
    p, param_spec = resolve_params(SPEC, params)

    # pick the series: the target if numeric, else the highest-variance feature
    ser = None
    if target in X.columns:
        ser = X[target]
    if ser is None or ser.std() == 0:
        ser = X[max(feats, key=lambda f: float(X[f].std()))]
    s = np.asarray(ser, dtype=float)
    s = s[np.isfinite(s)][:MAX_T]
    # de-mean to a shock series scaled to ~% units for a stable fit
    r = (s - s.mean())
    if r.std() > 0:
        r = r / r.std() * 3.0

    mech = None
    q = p["q"] if model == "garch" else 0
    try:
        from arch import arch_model

        vol = "GARCH" if model == "garch" and q > 0 else "ARCH"
        res = arch_model(r, vol=vol, p=max(1, p["p"]), q=max(0, q), rescale=False).fit(disp="off")
        cond = np.asarray(res.conditional_volatility, dtype=float)
        omega = float(res.params.get("omega", 0.0))
        alpha = float(res.params.get("alpha[1]", res.params.get("alpha", 0.0)))
        beta = float(res.params.get("beta[1]", 0.0)) if vol == "GARCH" else 0.0
        mech = {
            "kind": model,
            "returns": [round(float(v), 3) for v in r],
            "vol": [round(float(v), 3) for v in cond],
            "sq_returns": [round(float(v * v), 3) for v in r],
            "omega": round(omega, 4), "alpha": round(alpha, 4), "beta": round(beta, 4),
            "persistence": round(alpha + beta, 4),
            "aic": round(float(res.aic), 2),
        }
    except Exception:
        mech = None

    series = {"x": "t", "y": "return"}
    if mech:
        series["mechanism"] = mech
    note = (
        "Financial returns are unpredictable in level but their VARIANCE clusters — calm begets "
        "calm, turbulence begets turbulence. "
        + ("GARCH" if model == "garch" else "ARCH")
        + " models that conditional variance directly, so you can forecast risk."
    )
    return ModelTrace(
        family="volatility", target=target, task="volatility",
        features=feats[:6], labels=None,
        table=table_rows(X, y, feats[:6], target, task, None),
        series=series, test_rows=[], params=p, param_spec=param_spec, note=note,
    )
