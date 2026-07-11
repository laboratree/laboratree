"""Time-series family — exponential smoothing (ETS / Holt-Winters) and seasonal ARIMA.

Row order = time; the numeric target column is the series. Holdout = the last 20% of the series,
scored with rmse/mae (plus AIC), all Evidence-emitted.
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from ...evaluation.metrics import as_metric_dict, regression_metrics, sample_predictions


def _series(ctx: RunContext, name: str):
    import pandas as pd

    df = ctx.inputs["dataset"].dropna()
    target = ctx.params["target"]
    if target not in df.columns:
        target = df.columns[-1]
    y = df[target]
    if not pd.api.types.is_numeric_dtype(y):
        raise ValueError(f"{name} needs a numeric series over time, but '{target}' is categorical.")
    v = y.astype(float).reset_index(drop=True)
    if len(v) < 30:
        raise ValueError(f"{name} needs at least 30 rows of history.")
    ntr = max(10, int(len(v) * 0.8))
    return v, ntr


def _finish(component: Component, ctx: RunContext, yte, pred, aic: float | None) -> dict[str, Any]:
    metrics = as_metric_dict(regression_metrics(yte, pred))
    if aic is not None:
        metrics["aic"] = round(float(aic), 2)
    for k, v in metrics.items():
        ctx.emit(k, v, kind="metric", component=component.spec.id)
    return {
        "metrics": metrics, "task": "regression", "n_test": int(len(yte)),
        "predictions": sample_predictions(yte, pred, "regression"),
    }


def _ts_schema(extra: dict) -> dict:
    return {
        "type": "object",
        "required": ["target"],
        "properties": {
            "target": {"type": "string", "title": "Numeric series column (rows = time)"},
            **extra,
        },
    }


@register
class ExponentialSmoothingModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.timeseries.ets",
        name="Exponential Smoothing (ETS / Holt-Winters)",
        summary="Forecasts by smoothly weighting recent history; optional trend and seasonality "
        "(Holt-Winters). The classic baseline for business series.",
        params_schema=_ts_schema({
            "trend": {"type": "string", "default": "add", "enum": ["add", "none"], "title": "Trend"},
            "seasonal": {"type": "string", "default": "none", "enum": ["add", "none"],
                         "title": "Seasonality"},
            "seasonal_periods": {"type": "integer", "default": 12, "title": "Season length"},
        }),
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["timeseries", "forecasting", "regression-family:timeseries"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from statsmodels.tsa.holtwinters import ExponentialSmoothing

        v, ntr = _series(ctx, self.spec.name)
        trend = None if ctx.params.get("trend", "add") == "none" else "add"
        seasonal = None if ctx.params.get("seasonal", "none") == "none" else "add"
        sp = int(ctx.params.get("seasonal_periods", 12)) if seasonal else None
        res = ExponentialSmoothing(
            v.iloc[:ntr], trend=trend, seasonal=seasonal, seasonal_periods=sp,
            initialization_method="estimated",
        ).fit()
        pred = res.forecast(len(v) - ntr)
        return _finish(self, ctx, v.iloc[ntr:], pred.to_numpy(), getattr(res, "aic", None))


@register
class SarimaModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.timeseries.sarima",
        name="SARIMA (statsmodels)",
        summary="ARIMA with a seasonal component — autoregression + differencing + moving average, "
        "repeating every season.",
        params_schema=_ts_schema({
            "p": {"type": "integer", "default": 1, "title": "AR order (p)"},
            "d": {"type": "integer", "default": 0, "title": "Differencing (d)"},
            "q": {"type": "integer", "default": 0, "title": "MA order (q)"},
            "P": {"type": "integer", "default": 0, "title": "Seasonal AR (P)"},
            "D": {"type": "integer", "default": 0, "title": "Seasonal diff (D)"},
            "Q": {"type": "integer", "default": 0, "title": "Seasonal MA (Q)"},
            "s": {"type": "integer", "default": 12, "title": "Season length (s)"},
        }),
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["timeseries", "forecasting", "econometrics", "regression-family:timeseries"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from statsmodels.tsa.arima.model import ARIMA

        v, ntr = _series(ctx, self.spec.name)

        def g(k: str, d: int) -> int:
            return int(ctx.params.get(k, d))

        seasonal = (g("P", 0), g("D", 0), g("Q", 0), g("s", 12))
        res = ARIMA(
            v.iloc[:ntr], order=(g("p", 1), g("d", 0), g("q", 0)),
            seasonal_order=seasonal if any(seasonal[:3]) else (0, 0, 0, 0),
        ).fit()
        pred = res.forecast(len(v) - ntr)
        return _finish(self, ctx, v.iloc[ntr:], pred.to_numpy(), getattr(res, "aic", None))
