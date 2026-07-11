"""Discrete-choice models — multinomial and ordered outcomes (micro-econometrics staples).

  * multinomial logit -> unordered categories (which brand / mode of transport)
  * ordered logit/probit -> ordered categories (credit ratings, Likert 1–5, low/med/high)
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from ...evaluation.metrics import numeric_features

_SCHEMA = {
    "type": "object",
    "required": ["target"],
    "properties": {
        "target": {"type": "string", "title": "Categorical outcome"},
        "features": {"type": "array", "items": {"type": "string"}, "title": "Features"},
    },
}


def _prep(ctx: RunContext):
    import statsmodels.api as sm

    df = ctx.inputs["dataset"].dropna()
    target = ctx.params["target"]
    feats = numeric_features(df, target, ctx.params.get("features"))
    if not feats:
        raise ValueError("no numeric features for the choice model")
    y = df[target].astype("category")
    X = sm.add_constant(df[feats].astype(float))
    return y, X, int(len(df))


@register
class MultinomialLogitModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.multinomial_logit",
        name="Multinomial Logit",
        summary="Predicts an UNORDERED categorical outcome (brand, transport mode) — one set of "
        "coefficients per alternative relative to a base.",
        params_schema=_SCHEMA, inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "classification", "choice", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import statsmodels.api as sm

        y, X, n = _prep(ctx)
        codes = y.cat.codes
        if len(y.cat.categories) < 3:
            raise ValueError("Multinomial logit expects 3+ categories (use logit for binary).")
        res = sm.MNLogit(codes, X).fit(disp=0, maxiter=200)
        acc = float((res.predict(X).values.argmax(axis=1) == codes.to_numpy()).mean())
        metrics = {"accuracy": round(acc, 4), "pseudo_r2": round(float(res.prsquared), 4),
                   "n_classes": int(len(y.cat.categories))}
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {"metrics": metrics, "task": "classification", "n_obs": n}


def _ordered(ctx: RunContext, cid: str, distr: str) -> dict[str, Any]:
    from statsmodels.miscmodels.ordinal_model import OrderedModel

    y, X, n = _prep(ctx)
    if len(y.cat.categories) < 3:
        raise ValueError("Ordered models expect 3+ ordered categories.")
    exog = X.drop(columns=["const"])  # OrderedModel fits its own thresholds
    res = OrderedModel(y.cat.codes, exog, distr=distr).fit(method="bfgs", disp=0, maxiter=200)
    pred = res.predict(exog).values.argmax(axis=1)
    acc = float((pred == y.cat.codes.to_numpy()).mean())
    metrics = {"accuracy": round(acc, 4), "pseudo_r2": round(float(res.prsquared), 4),
               "n_classes": int(len(y.cat.categories))}
    for k, v in metrics.items():
        ctx.emit(k, v, kind="metric", component=cid)
    return {"metrics": metrics, "task": "classification", "n_obs": n}


@register
class OrderedLogitModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.ordered_logit", name="Ordered Logit",
        summary="For ORDERED categories (low/med/high, ratings, Likert): one slope, a set of "
        "cut-points, logistic link.",
        params_schema=_SCHEMA, inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "classification", "choice", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        return _ordered(ctx, self.spec.id, "logit")


@register
class OrderedProbitModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL, id="model.econometrics.ordered_probit", name="Ordered Probit",
        summary="Ordered-category model with a normal (probit) link — the latent-score story "
        "crossing several thresholds.",
        params_schema=_SCHEMA, inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "classification", "choice", "regression-family:econometrics"])

    def run(self, ctx: RunContext) -> dict[str, Any]:
        return _ordered(ctx, self.spec.id, "probit")
