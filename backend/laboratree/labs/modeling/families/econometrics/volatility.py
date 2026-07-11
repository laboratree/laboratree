"""Volatility models — ARCH & GARCH (the finance workhorses).

Financial returns are roughly unpredictable in LEVEL but their VARIANCE clusters: calm periods
and turbulent periods bunch together. ARCH/GARCH model that conditional variance directly, so
you can forecast risk (VaR), size positions, and price options. Built on the `arch` package.
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register


def _returns(ctx: RunContext) -> tuple[Any, str]:
    """The series to model — a return/value column, sorted by time if given, scaled to ~%."""
    import numpy as np
    import pandas as pd

    df: pd.DataFrame = ctx.inputs["dataset"]
    col = ctx.params["value_column"]
    tcol = ctx.params.get("time_column")
    if tcol and tcol in df.columns:
        df = df.sort_values(tcol)
    s = df[col].astype(float).dropna().reset_index(drop=True)
    # if the column looks like prices (all positive, trending), model log returns instead
    if ctx.params.get("as_returns") and (s > 0).all():
        s = (np.log(s).diff().dropna() * 100).reset_index(drop=True)
    return s, col


def _finish(ctx: RunContext, cid: str, res, n: int) -> dict[str, Any]:
    metrics = {
        "aic": round(float(res.aic), 3),
        "bic": round(float(res.bic), 3),
        "log_likelihood": round(float(res.loglikelihood), 3),
    }
    for k, v in metrics.items():
        ctx.emit(k, v, kind="metric", component=cid)
    params = {str(k): round(float(v), 5) for k, v in res.params.items()}
    return {"metrics": metrics, "task": "volatility", "n_obs": int(n),
            "coefficients": params, "predictions": []}


_SCHEMA = {
    "type": "object",
    "required": ["value_column"],
    "properties": {
        "value_column": {"type": "string", "title": "Return / value column"},
        "time_column": {"type": "string", "title": "Time column (optional, for sorting)"},
        "as_returns": {"type": "boolean", "default": False,
                       "title": "Column is a price → model its log returns"},
    },
}


@register
class ARCHModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.arch",
        name="ARCH",
        summary="Models volatility clustering: today's variance depends on recent squared shocks "
        "(Engle's Nobel-winning model).",
        params_schema={**_SCHEMA, "properties": {**_SCHEMA["properties"],
                       "p": {"type": "integer", "default": 1, "title": "ARCH order (p)"}}},
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "volatility", "finance",
              "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from arch import arch_model

        s, _ = _returns(ctx)
        p = int(ctx.params.get("p", 1))
        res = arch_model(s, vol="ARCH", p=max(1, p)).fit(disp="off")
        return _finish(ctx, self.spec.id, res, len(s))


@register
class GARCHModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.garch",
        name="GARCH",
        summary="The standard volatility model: today's variance depends on recent squared shocks "
        "AND recent variance — captures long, persistent turbulence with few parameters.",
        params_schema={**_SCHEMA, "properties": {**_SCHEMA["properties"],
                       "p": {"type": "integer", "default": 1, "title": "ARCH order (p)"},
                       "q": {"type": "integer", "default": 1, "title": "GARCH order (q)"}}},
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "volatility", "finance",
              "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from arch import arch_model

        s, _ = _returns(ctx)
        p, q = int(ctx.params.get("p", 1)), int(ctx.params.get("q", 1))
        res = arch_model(s, vol="GARCH", p=max(1, p), q=max(1, q)).fit(disp="off")
        return _finish(ctx, self.spec.id, res, len(s))


@register
class EGARCHModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.egarch",
        name="EGARCH",
        summary="Exponential GARCH — captures the LEVERAGE EFFECT: bad news raises volatility more "
        "than equally-sized good news, and needs no positivity constraints (models log-variance).",
        params_schema=_SCHEMA,
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "volatility", "finance",
              "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from arch import arch_model

        s, _ = _returns(ctx)
        res = arch_model(s, vol="EGARCH", p=1, o=1, q=1).fit(disp="off")
        return _finish(ctx, self.spec.id, res, len(s))


@register
class GJRGARCHModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.gjr_garch",
        name="GJR-GARCH",
        summary="GARCH plus an asymmetry term (Glosten–Jagannathan–Runkle): a negative shock adds "
        "EXTRA variance, matching the leverage effect in equity returns.",
        params_schema=_SCHEMA,
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "timeseries", "volatility", "finance",
              "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from arch import arch_model

        s, _ = _returns(ctx)
        res = arch_model(s, vol="GARCH", p=1, o=1, q=1).fit(disp="off")  # o=1 ⇒ GJR asymmetry
        return _finish(ctx, self.spec.id, res, len(s))
