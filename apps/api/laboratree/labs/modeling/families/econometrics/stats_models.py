"""More statistical models — quantile regression, VAR, negative binomial.

Broadens the econometrics offering beyond the conditional-mean regressions:
  * quantile regression -> models the median (or any percentile), robust to outliers
  * VAR                 -> several interrelated series predict each other (macro workhorse)
  * negative binomial   -> overdispersed counts where Poisson's mean=variance fails
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from ...evaluation.metrics import numeric_features


@register
class QuantileRegressionModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.quantile",
        name="Quantile Regression",
        summary="Models a chosen percentile of the outcome (e.g. the median or the 90th) instead "
        "of the mean — robust to outliers and reveals effects across the distribution.",
        params_schema={
            "type": "object",
            "required": ["target"],
            "properties": {
                "target": {"type": "string", "title": "Outcome column"},
                "features": {"type": "array", "items": {"type": "string"}, "title": "Features"},
                "quantile": {"type": "number", "default": 0.5, "title": "Quantile (0–1)"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "regression", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import numpy as np
        import statsmodels.api as sm

        df = ctx.inputs["dataset"].dropna()
        target = ctx.params["target"]
        feats = numeric_features(df, target, ctx.params.get("features"))
        if not feats:
            raise ValueError("no numeric features for quantile regression")
        q = float(ctx.params.get("quantile", 0.5))
        q = min(0.95, max(0.05, q))
        X = sm.add_constant(df[feats].astype(float))
        y = df[target].astype(float)
        res = sm.QuantReg(y, X).fit(q=q)
        pred = res.predict(X)
        # pinball (quantile) loss — the objective quantile regression minimises
        err = y - pred
        pinball = float(np.mean(np.maximum(q * err, (q - 1) * err)))
        metrics = {"quantile": round(q, 2), "pinball_loss": round(pinball, 4),
                   "pseudo_r2": round(float(res.prsquared), 4)}
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {"metrics": metrics, "task": "regression", "n_obs": int(len(df)),
                "coefficients": {str(k): round(float(v), 4) for k, v in res.params.items()}}


@register
class VARModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.var",
        name="Vector Autoregression (VAR)",
        summary="Several time series predict each other from their joint past — the macro "
        "econometrician's tool for dynamics, impulse responses and Granger causality.",
        params_schema={
            "type": "object",
            "required": ["value_columns"],
            "properties": {
                "value_columns": {"type": "array", "items": {"type": "string"},
                                  "title": "Series columns (2+)"},
                "time_column": {"type": "string", "title": "Time column (optional)"},
                "lags": {"type": "integer", "default": 1, "title": "Lag order"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import pandas as pd
        from statsmodels.tsa.api import VAR

        df: pd.DataFrame = ctx.inputs["dataset"]
        tcol = ctx.params.get("time_column")
        if tcol and tcol in df.columns:
            df = df.sort_values(tcol)
        cols = ctx.params.get("value_columns") or []
        cols = [c for c in cols if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        if len(cols) < 2:
            raise ValueError("VAR needs at least 2 numeric series.")
        data = df[cols].astype(float).dropna().reset_index(drop=True)
        lags = max(1, int(ctx.params.get("lags", 1)))
        res = VAR(data).fit(maxlags=lags)
        metrics = {"aic": round(float(res.aic), 3), "bic": round(float(res.bic), 3),
                   "lags": int(res.k_ar)}
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {"metrics": metrics, "task": "timeseries", "n_obs": int(len(data)),
                "series": cols}


@register
class NegativeBinomialModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.negative_binomial",
        name="Negative Binomial",
        summary="Count regression for OVERDISPERSED data (variance > mean) — where Poisson's "
        "equal-variance assumption understates the standard errors.",
        params_schema={
            "type": "object",
            "required": ["target"],
            "properties": {
                "target": {"type": "string", "title": "Count outcome column"},
                "features": {"type": "array", "items": {"type": "string"}, "title": "Features"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "counts", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import statsmodels.api as sm

        df = ctx.inputs["dataset"].dropna()
        target = ctx.params["target"]
        y = df[target].astype(float)
        if (y < 0).any():
            raise ValueError("Negative Binomial needs a non-negative count target.")
        feats = numeric_features(df, target, ctx.params.get("features"))
        if not feats:
            raise ValueError("no numeric features for negative binomial")
        X = sm.add_constant(df[feats].astype(float))
        res = sm.NegativeBinomial(y, X).fit(disp=0, maxiter=200)
        mean, var = float(y.mean()), float(y.var())
        metrics = {
            "pseudo_r2": round(float(res.prsquared), 4),
            "aic": round(float(res.aic), 3),
            "dispersion": round(var / mean, 3) if mean else 0.0,  # >1 ⇒ overdispersed
        }
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {"metrics": metrics, "task": "regression", "n_obs": int(len(df)),
                "coefficients": {str(k): round(float(v), 4) for k, v in res.params.items()},
                "overdispersed": bool(var > 1.2 * mean)}
