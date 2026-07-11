"""Econometrics family — the linear mechanics PLUS the inference layer.

Reuses the linear tracer for the staged animation (weights, sigmoid, per-row walkthrough),
then fits the matching statsmodels model (OLS / Logit / Probit / Poisson, chosen by the
resolved ``_model`` hint) and attaches ``series["inference"]``: per-coefficient standard
errors, t/z statistics, p-values, confidence intervals, and e^β readings — the material an
economics exam actually tests.
"""

from __future__ import annotations

from . import register_tracer
from .linear import trace_linear
from .schema import ModelTrace

FIT_MAX_ROWS = 400


def _exp_reading(kind: str) -> str | None:
    if kind == "logit":
        return "odds ratio"
    if kind == "poisson":
        return "rate ratio"
    return None


def _fit_inference(X, y, feats, task, kind: str):
    """statsmodels fit → typed-ish inference rows. Returns None when the data can't support
    the requested GLM (the lesson then simply skips the inference chapter)."""
    import numpy as np
    import statsmodels.api as sm

    Xs = sm.add_constant(X[feats].iloc[:FIT_MAX_ROWS].astype(float), has_constant="add")
    ys = np.asarray(y.iloc[:FIT_MAX_ROWS], dtype=float)

    if task == "classification":
        classes = np.unique(ys)
        if len(classes) > 2:  # binarize most-common vs rest, like the boosting tracer
            pos = int(np.bincount(ys.astype(int)).argmax())
            ys = (ys == pos).astype(float)
        model = sm.Probit(ys, Xs) if kind == "probit" else sm.Logit(ys, Xs)
        kind = "probit" if kind == "probit" else "logit"
        res = model.fit(disp=0, maxiter=200)
        fit_stat = {"name": "pseudo R²", "value": round(float(res.prsquared), 3)}
    elif kind == "poisson":
        if (ys < 0).any():
            return None  # a rate model needs non-negative outcomes
        res = sm.GLM(ys, Xs, family=sm.families.Poisson()).fit()
        fit_stat = {"name": "deviance", "value": round(float(res.deviance), 2)}
    else:
        kind = "ols"
        res = sm.OLS(ys, Xs).fit()
        fit_stat = {"name": "R²", "value": round(float(res.rsquared), 3)}

    ci = res.conf_int()
    rows = []
    for name in res.params.index:
        b = float(res.params[name])
        row = {
            "feature": "intercept" if name == "const" else str(name),
            "coef": round(b, 4),
            "se": round(float(res.bse[name]), 4),
            "stat": round(float(res.tvalues[name]), 3),  # t (OLS) or z (GLM)
            "p": round(float(res.pvalues[name]), 4),
            "ci_lo": round(float(ci.loc[name][0]), 4),
            "ci_hi": round(float(ci.loc[name][1]), 4),
        }
        if _exp_reading(kind) and name != "const":
            row["exp_coef"] = round(float(2.718281828**b), 3)
        rows.append(row)
    return {
        "kind": kind,
        "stat_name": "t" if kind == "ols" else "z",
        "exp_reading": _exp_reading(kind),
        "n": int(res.nobs),
        "fit": fit_stat,
        "rows": rows,
    }


@register_tracer("econometrics")
def trace_econometrics(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    params = dict(params or {})
    kind = str(params.pop("_model", "") or "")
    base = trace_linear(X, y, feats, target, task, labels, params=params)
    try:
        inference = _fit_inference(X, y, base.features[:12], task, kind)
    except Exception:  # singular matrix, separation… — the mechanics lesson still plays
        inference = None
    if inference:
        base.series = {**(base.series or {}), "inference": inference}
        base.note += (
            " Because this is an econometric fit, every coefficient also carries a standard "
            "error, a test statistic, a p-value, and a confidence interval — see the "
            "inference chapter."
        )
    return base
