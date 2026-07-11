"""Panel-data regressions — pooled OLS, fixed effects (within), random effects.

The classic econometrics ladder for repeated observations of the same entities (people,
firms, countries): POOLED ignores the panel structure; FIXED EFFECTS demeans within each
entity so every time-constant confounder drops out; RANDOM EFFECTS treats entity intercepts
as draws from a distribution (efficient when they're uncorrelated with X — the Hausman
question).
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

_SEED = 1729
_MAX_ENTITY_SHARE = 0.5  # a column whose cardinality exceeds half the rows isn't an entity id


def _params_schema() -> dict:
    return {
        "type": "object",
        "required": ["target"],
        "properties": {
            "target": {"type": "string", "title": "Numeric outcome column"},
            "entity_column": {
                "type": "string",
                "title": "Entity column (person/firm/country id)",
                "description": "Repeated-observation group id; auto-detected when omitted.",
            },
            "features": {"type": "array", "items": {"type": "string"}, "title": "Features"},
            "test_size": {"type": "number", "default": 0.25},
        },
    }


def pick_entity_column(df, target: str, wanted: str | None) -> str:
    """The user's entity column, or the lowest-cardinality plausible group id."""
    if wanted and wanted in df.columns:
        return wanted
    n = len(df)
    candidates = [
        (df[c].nunique(), c)
        for c in df.columns
        if c != target and 2 <= df[c].nunique() <= max(2, int(n * _MAX_ENTITY_SHARE))
    ]
    if not candidates:
        raise ValueError(
            "panel models need an entity column (a repeated group id) — none detected; "
            "set entity_column explicitly."
        )
    return min(candidates)[1]


def _prep(ctx: RunContext, name: str):
    import pandas as pd
    from sklearn.model_selection import train_test_split

    df = ctx.inputs["dataset"].dropna()
    target = ctx.params["target"]
    if not pd.api.types.is_numeric_dtype(df[target]):
        raise ValueError(f"{name} needs a numeric outcome, got categorical '{target}'.")
    entity = pick_entity_column(df, target, ctx.params.get("entity_column"))
    feats = [f for f in numeric_features(df, target, ctx.params.get("features")) if f != entity]
    if not feats:
        raise ValueError(f"no numeric features available for {name}")
    tr, te = train_test_split(
        df, test_size=ctx.params.get("test_size", 0.25), random_state=_SEED
    )
    return tr, te, feats, target, entity


def _finish(ctx: RunContext, component_id: str, res, yte, pred, extra: dict) -> dict[str, Any]:
    metrics = as_metric_dict(regression_metrics(yte, pred))
    for k, v in metrics.items():
        ctx.emit(k, v, kind="metric", component=component_id)
    return {
        "metrics": metrics, "task": "regression", "n_test": int(len(yte)),
        "coefficients": {str(k): round(float(v), 4) for k, v in res.params.items()},
        "p_values": {str(k): round(float(v), 4) for k, v in res.pvalues.items()},
        "predictions": sample_predictions(yte, pred, "regression"),
        **extra,
    }


@register
class PooledOLSModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.pooled_ols",
        name="Pooled OLS (panel)",
        summary="Stack all entity-period rows and run one OLS — the panel baseline that "
        "ignores who each row belongs to.",
        params_schema=_params_schema(),
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "panel", "regression", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import statsmodels.api as sm

        tr, te, feats, target, entity = _prep(ctx, self.spec.name)
        Xtr = sm.add_constant(tr[feats].astype(float))
        Xte = sm.add_constant(te[feats].astype(float), has_constant="add")
        res = sm.OLS(tr[target].astype(float), Xtr).fit()
        return _finish(ctx, self.spec.id, res, te[target].astype(float), res.predict(Xte),
                       {"entity_column": entity, "r2": round(float(res.rsquared), 4)})


@register
class FixedEffectsModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.fixed_effects",
        name="Fixed Effects (within estimator)",
        summary="Demean every variable within each entity so all time-constant confounders "
        "drop out — the workhorse of causal panel econometrics.",
        params_schema=_params_schema(),
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "panel", "regression", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import statsmodels.api as sm

        tr, te, feats, target, entity = _prep(ctx, self.spec.name)
        ytr = tr[target].astype(float)
        # the within transform: subtract each entity's own averages
        gmy = ytr.groupby(tr[entity]).transform("mean")
        gmx = tr[feats].astype(float).groupby(tr[entity]).transform("mean")
        res = sm.OLS(ytr - gmy, tr[feats].astype(float) - gmx).fit()
        # predict test rows with train entity means (global means for unseen entities)
        ent_y = ytr.groupby(tr[entity]).mean()
        base = te[entity].map(ent_y).fillna(float(ytr.mean()))
        ent_x = tr[feats].astype(float).groupby(tr[entity]).mean()
        xbase = te[entity].to_frame().join(ent_x, on=entity)[feats].fillna(
            tr[feats].astype(float).mean()
        )
        pred = base + ((te[feats].astype(float) - xbase) * res.params[feats]).sum(axis=1)
        return _finish(ctx, self.spec.id, res, te[target].astype(float), pred,
                       {"entity_column": entity,
                        "within_r2": round(float(res.rsquared), 4),
                        "n_entities": int(tr[entity].nunique())})


@register
class RandomEffectsModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.econometrics.random_effects",
        name="Random Effects (random intercepts)",
        summary="Entity intercepts drawn from a distribution — more efficient than FE when "
        "the entity effects are uncorrelated with the regressors (the Hausman question).",
        params_schema=_params_schema(),
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["econometrics", "panel", "regression", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import statsmodels.api as sm

        tr, te, feats, target, entity = _prep(ctx, self.spec.name)
        res = sm.MixedLM(
            tr[target].astype(float),
            sm.add_constant(tr[feats].astype(float)),
            groups=tr[entity],
        ).fit(reml=True)
        Xte = sm.add_constant(te[feats].astype(float), has_constant="add")
        pred = res.predict(Xte)  # population-level prediction (random intercept at its mean)
        out = _finish(ctx, self.spec.id, res, te[target].astype(float), pred,
                      {"entity_column": entity, "n_entities": int(tr[entity].nunique())})
        # report only the fixed part as the coefficient table (Group Var is a variance term)
        out["coefficients"].pop("Group Var", None)
        out["p_values"].pop("Group Var", None)
        return out
