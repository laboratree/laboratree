"""More time-series models — AR, MA, ARMA (the ARIMA building blocks) and VECM (cointegration).

AR/MA/ARMA are ARIMA with d=0 and specific orders; exposing them by name matches how they're
taught. VECM models several non-stationary series that share a long-run equilibrium.
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register


def _series(ctx: RunContext):
    import pandas as pd

    df: pd.DataFrame = ctx.inputs["dataset"]
    tcol = ctx.params.get("time_column")
    if tcol and tcol in df.columns:
        df = df.sort_values(tcol)
    return df[ctx.params["value_column"]].astype(float).dropna().reset_index(drop=True)


def _arima_like(ctx: RunContext, cid: str, order: tuple[int, int, int]) -> dict[str, Any]:
    import numpy as np
    from statsmodels.tsa.arima.model import ARIMA

    s = _series(ctx)
    res = ARIMA(s, order=order).fit()
    resid = res.resid.dropna()
    rmse = float(np.sqrt((resid**2).mean())) if len(resid) else 0.0
    metrics = {"aic": round(float(res.aic), 3), "bic": round(float(res.bic), 3),
               "rmse": round(rmse, 4)}
    for k, v in metrics.items():
        ctx.emit(k, v, kind="metric", component=cid)
    return {"metrics": metrics, "task": "timeseries", "order": list(order), "n_obs": int(len(s))}


_TS_SCHEMA = {
    "type": "object",
    "required": ["value_column"],
    "properties": {
        "value_column": {"type": "string", "title": "Value column"},
        "time_column": {"type": "string", "title": "Time column (optional)"},
        "order": {"type": "integer", "default": 1, "title": "Order"},
    },
}


@register
class ARModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.ar", name="AR (autoregressive)",
        summary="Today's value is a weighted sum of its own recent PAST values — the pure "
        "autoregressive piece of ARIMA.",
        params_schema=_TS_SCHEMA, inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        return _arima_like(ctx, self.spec.id, (max(1, int(ctx.params.get("order", 1))), 0, 0))


@register
class MAModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.ma", name="MA (moving average)",
        summary="Today's value is a weighted sum of recent forecast ERRORS — the pure "
        "moving-average piece of ARIMA.",
        params_schema=_TS_SCHEMA, inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        return _arima_like(ctx, self.spec.id, (0, 0, max(1, int(ctx.params.get("order", 1)))))


@register
class ARMAModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.arma", name="ARMA",
        summary="Combines autoregression (past values) and moving average (past errors) on a "
        "stationary series — ARIMA with no differencing.",
        params_schema={"type": "object", "required": ["value_column"], "properties": {
            "value_column": {"type": "string", "title": "Value column"},
            "time_column": {"type": "string", "title": "Time column (optional)"},
            "p": {"type": "integer", "default": 1, "title": "AR order (p)"},
            "q": {"type": "integer", "default": 1, "title": "MA order (q)"}}},
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        p, q = int(ctx.params.get("p", 1)), int(ctx.params.get("q", 1))
        return _arima_like(ctx, self.spec.id, (max(0, p), 0, max(0, q)))


@register
class VECMModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.vecm", name="VECM (cointegration)",
        summary="For non-stationary series that share a long-run equilibrium: models how they "
        "adjust back toward it when they drift apart (the error-correction term).",
        params_schema={"type": "object", "required": ["value_columns"], "properties": {
            "value_columns": {"type": "array", "items": {"type": "string"},
                              "title": "Series (2+)"},
            "time_column": {"type": "string", "title": "Time column (optional)"},
            "lags": {"type": "integer", "default": 1, "title": "Lag order"}}},
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import pandas as pd
        from statsmodels.tsa.vector_ar.vecm import VECM

        df: pd.DataFrame = ctx.inputs["dataset"]
        tcol = ctx.params.get("time_column")
        if tcol and tcol in df.columns:
            df = df.sort_values(tcol)
        cols = [c for c in (ctx.params.get("value_columns") or [])
                if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
        if len(cols) < 2:
            raise ValueError("VECM needs at least 2 numeric series.")
        data = df[cols].astype(float).dropna().reset_index(drop=True)
        lags = max(1, int(ctx.params.get("lags", 1)))
        res = VECM(data, k_ar_diff=lags, coint_rank=1).fit()
        aic = float(res.llf)
        metrics = {"log_likelihood": round(aic, 2), "lags": lags, "coint_rank": 1}
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {"metrics": metrics, "task": "timeseries", "n_obs": int(len(data)), "series": cols}
