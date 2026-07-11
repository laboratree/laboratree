"""Native XGBoost — the EXACT library most boosted-tree papers use (not a stand-in).

Exposes the paper-relevant hyperparameters (eta, depth, rounds, subsampling, regularization).
xgboost is imported lazily inside run() so registry discovery stays fast.
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from ...evaluation.metrics import (
    as_metric_dict,
    classification_metrics,
    numeric_features,
    regression_metrics,
    sample_predictions,
)

_SEED = 1729


def _is_classification(y) -> bool:
    if y.dtype == object or str(y.dtype).startswith(("category", "str")) or str(y.dtype) == "bool":
        return True
    return y.nunique() <= 10


@register
class XGBoostModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.ml.xgboost",
        name="XGBoost (native)",
        summary="The real XGBoost library — gradient-boosted trees with the paper's usual knobs "
        "(learning rate, depth, rounds, subsampling, regularization). Auto-detects "
        "classification vs regression.",
        params_schema={
            "type": "object",
            "required": ["target"],
            "properties": {
                "target": {"type": "string", "title": "Target column"},
                "features": {"type": "array", "items": {"type": "string"}, "title": "Features"},
                "test_size": {"type": "number", "default": 0.25},
                "learning_rate": {"type": "number", "default": 0.1, "title": "Learning rate (eta)"},
                "n_estimators": {"type": "integer", "default": 200, "title": "Boosting rounds"},
                "max_depth": {"type": "integer", "default": 6, "title": "Max tree depth"},
                "subsample": {"type": "number", "default": 1.0, "title": "Row subsample"},
                "colsample_bytree": {"type": "number", "default": 1.0, "title": "Column subsample"},
                "reg_lambda": {"type": "number", "default": 1.0, "title": "L2 regularization (lambda)"},
                "gamma": {"type": "number", "default": 0.0, "title": "Min split gain (gamma)"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["ml", "classification", "regression", "trees", "boosting", "xgboost",
              "regression-family:ml"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import pandas as pd
        from sklearn.model_selection import train_test_split
        from xgboost import XGBClassifier, XGBRegressor

        df: pd.DataFrame = ctx.inputs["dataset"].dropna()
        target = ctx.params["target"]
        feats = numeric_features(df, target, ctx.params.get("features"))
        if not feats:
            raise ValueError("no numeric features available for XGBoost")

        y = df[target]
        classify = _is_classification(y)
        if classify and not pd.api.types.is_numeric_dtype(y):
            y = y.astype("category").cat.codes  # xgboost needs 0..n-1 integer labels
        task = "classification" if classify else "regression"

        kw = dict(
            learning_rate=ctx.params.get("learning_rate", 0.1),
            n_estimators=int(ctx.params.get("n_estimators", 200)),
            max_depth=int(ctx.params.get("max_depth", 6)),
            subsample=ctx.params.get("subsample", 1.0),
            colsample_bytree=ctx.params.get("colsample_bytree", 1.0),
            reg_lambda=ctx.params.get("reg_lambda", 1.0),
            gamma=ctx.params.get("gamma", 0.0),
            random_state=_SEED,
        )
        stratify = y if (classify and y.nunique() > 1) else None
        Xtr, Xte, ytr, yte = train_test_split(
            df[feats], y, test_size=ctx.params.get("test_size", 0.25),
            random_state=_SEED, stratify=stratify,
        )
        if classify:
            model = XGBClassifier(**kw, eval_metric="logloss")
            model.fit(Xtr, ytr)
            pred = model.predict(Xte)
            proba = model.predict_proba(Xte)
            metrics = as_metric_dict(classification_metrics(yte, pred, proba))
        else:
            model = XGBRegressor(**kw)
            model.fit(Xtr, ytr)
            pred = model.predict(Xte)
            metrics = as_metric_dict(regression_metrics(yte, pred))

        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {
            "metrics": metrics,
            "task": task,
            "n_test": int(len(yte)),
            "predictions": sample_predictions(yte, pred, task),
        }
