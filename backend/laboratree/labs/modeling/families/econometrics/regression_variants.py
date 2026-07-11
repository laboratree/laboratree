"""Regression variants you meet constantly in applied work — WLS, GLS, robust (RLM), and the
zero-inflated Poisson for count data with excess zeros.
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from ...evaluation.metrics import (
    as_metric_dict,
    numeric_features,
    regression_metrics,
    sample_predictions,
)


def _reg_schema(extra: dict | None = None) -> dict:
    props = {
        "target": {"type": "string", "title": "Outcome column"},
        "features": {"type": "array", "items": {"type": "string"}, "title": "Features"},
    }
    props.update(extra or {})
    return {"type": "object", "required": ["target"], "properties": props}


def _xy(ctx: RunContext):
    import statsmodels.api as sm

    df = ctx.inputs["dataset"].dropna()
    target = ctx.params["target"]
    feats = numeric_features(df, target, ctx.params.get("features"))
    if not feats:
        raise ValueError("no numeric features")
    return sm.add_constant(df[feats].astype(float)), df[target].astype(float), int(len(df)), feats


def _finish(ctx: RunContext, cid: str, res, X, y, n: int, extra: dict) -> dict[str, Any]:
    pred = res.predict(X)
    metrics = as_metric_dict(regression_metrics(y, pred))
    for k, v in metrics.items():
        ctx.emit(k, v, kind="metric", component=cid)
    return {"metrics": metrics, "task": "regression", "n_obs": n,
            "coefficients": {str(k): round(float(v), 4) for k, v in res.params.items()},
            "predictions": sample_predictions(y, pred, "regression"), **extra}


@register
class WLSModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.wls", name="Weighted Least Squares (WLS)",
        summary="OLS that down-weights noisy observations — the right fit under known "
        "heteroskedasticity (variance that changes across rows).",
        params_schema=_reg_schema(), inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "regression", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import numpy as np
        import statsmodels.api as sm

        X, y, n, _ = _xy(ctx)
        # a practical feasible-WLS weight: inverse of the squared OLS residual magnitude
        ols = sm.OLS(y, X).fit()
        w = 1.0 / np.clip(np.abs(ols.resid) + ols.resid.std() * 0.1, 1e-6, None)
        res = sm.WLS(y, X, weights=w).fit()
        return _finish(ctx, self.spec.id, res, X, y, n, {"r2": round(float(res.rsquared), 4)})


@register
class GLSModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.gls", name="Generalized Least Squares (GLS)",
        summary="OLS generalised to correlated / unequal-variance errors — the umbrella that WLS "
        "and OLS are special cases of.",
        params_schema=_reg_schema(), inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "regression", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import statsmodels.api as sm

        X, y, n, _ = _xy(ctx)
        res = sm.GLS(y, X).fit()  # identity sigma ⇒ OLS; shown as the general framework
        return _finish(ctx, self.spec.id, res, X, y, n, {"r2": round(float(res.rsquared), 4)})


@register
class RobustRegressionModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.robust", name="Robust Regression (RLM)",
        summary="A regression line that shrugs off outliers by down-weighting them (Huber "
        "M-estimation) instead of letting a few extremes drag the fit.",
        params_schema=_reg_schema(), inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "regression", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import statsmodels.api as sm

        X, y, n, _ = _xy(ctx)
        res = sm.RLM(y, X, M=sm.robust.norms.HuberT()).fit()
        return _finish(ctx, self.spec.id, res, X, y, n, {})


@register
class ZeroInflatedPoissonModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.zip",
        name="Zero-Inflated Poisson (ZIP)",
        summary="Count model for data with MORE zeros than Poisson expects — mixes a 'structural "
        "zero' process with a Poisson count process.",
        params_schema=_reg_schema(), inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "counts", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import statsmodels.api as sm
        from statsmodels.discrete.count_model import ZeroInflatedPoisson

        df = ctx.inputs["dataset"].dropna()
        target = ctx.params["target"]
        y = df[target].astype(float)
        if (y < 0).any():
            raise ValueError("ZIP needs a non-negative count target.")
        feats = numeric_features(df, target, ctx.params.get("features"))
        if not feats:
            raise ValueError("no numeric features for ZIP")
        X = sm.add_constant(df[feats].astype(float))
        res = ZeroInflatedPoisson(y, X, exog_infl=sm.add_constant(df[feats[:1]].astype(float))).fit(
            disp=0, maxiter=200)
        zero_share = float((y == 0).mean())
        metrics = {"aic": round(float(res.aic), 3), "zero_share": round(zero_share, 3),
                   "log_likelihood": round(float(res.llf), 2)}
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {"metrics": metrics, "task": "regression", "n_obs": int(len(df))}
