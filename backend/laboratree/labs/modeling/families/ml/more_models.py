"""Library expansion — regularized linear models, more ensembles, Gaussian process.

All reuse the classics.py fit/eval loop (train/test split, metrics, Evidence emits, predictions).
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, RunContext, register

from .classics import _SEED, _fit_eval, _spec


def _numeric_target_only(ctx: RunContext, name: str) -> None:
    import pandas as pd

    y = ctx.inputs["dataset"].dropna()[ctx.params["target"]]
    if not pd.api.types.is_numeric_dtype(y):
        raise ValueError(
            f"{name} is a regression model and needs a numeric target — for categories try "
            "logistic regression or gradient boosting."
        )


@register
class RidgeModel(Component):
    spec = _spec(
        "model.ml.ridge", "Ridge Regression",
        "Linear regression with an L2 penalty that shrinks weights to curb overfitting.",
        {"alpha": {"type": "number", "default": 1.0, "title": "Penalty strength (alpha)"}},
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.linear_model import Ridge

        _numeric_target_only(ctx, self.spec.name)
        a = ctx.params.get("alpha", 1.0)
        return _fit_eval(self, ctx, lambda task: Ridge(alpha=a))


@register
class LassoModel(Component):
    spec = _spec(
        "model.ml.lasso", "Lasso Regression",
        "Linear regression with an L1 penalty that drives weak weights to exactly zero "
        "(built-in feature selection).",
        {"alpha": {"type": "number", "default": 0.1, "title": "Penalty strength (alpha)"}},
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.linear_model import Lasso

        _numeric_target_only(ctx, self.spec.name)
        a = ctx.params.get("alpha", 0.1)
        return _fit_eval(self, ctx, lambda task: Lasso(alpha=a))


@register
class ElasticNetModel(Component):
    spec = _spec(
        "model.ml.elastic_net", "Elastic Net",
        "Blend of ridge (L2) and lasso (L1) penalties — shrinks all weights and zeroes weak ones.",
        {
            "alpha": {"type": "number", "default": 0.1, "title": "Penalty strength (alpha)"},
            "l1_ratio": {"type": "number", "default": 0.5, "title": "L1 share (0=ridge, 1=lasso)"},
        },
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.linear_model import ElasticNet

        _numeric_target_only(ctx, self.spec.name)
        a = ctx.params.get("alpha", 0.1)
        r = ctx.params.get("l1_ratio", 0.5)
        return _fit_eval(self, ctx, lambda task: ElasticNet(alpha=a, l1_ratio=r))


@register
class ExtraTreesModel(Component):
    spec = _spec(
        "model.ml.extra_trees", "Extra Trees",
        "Like a random forest but with extra-random split thresholds — often faster, similar accuracy.",
        {
            "n_estimators": {"type": "integer", "default": 200, "title": "Trees"},
            "max_depth": {"type": "integer", "default": 0, "title": "Max depth (0 = unlimited)"},
        },
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.ensemble import ExtraTreesClassifier, ExtraTreesRegressor

        n = int(ctx.params.get("n_estimators", 200))
        d = int(ctx.params.get("max_depth", 0)) or None

        def make(task):
            M = ExtraTreesClassifier if task == "classification" else ExtraTreesRegressor
            return M(n_estimators=n, max_depth=d, random_state=_SEED)

        return _fit_eval(self, ctx, make)


@register
class AdaBoostModel(Component):
    spec = _spec(
        "model.ml.adaboost", "AdaBoost",
        "The original boosting: each new weak learner focuses on the rows the previous ones got wrong.",
        {
            "n_estimators": {"type": "integer", "default": 100, "title": "Boosting rounds"},
            "learning_rate": {"type": "number", "default": 1.0, "title": "Learning rate"},
        },
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.ensemble import AdaBoostClassifier, AdaBoostRegressor

        n = int(ctx.params.get("n_estimators", 100))
        lr = ctx.params.get("learning_rate", 1.0)

        def make(task):
            M = AdaBoostClassifier if task == "classification" else AdaBoostRegressor
            return M(n_estimators=n, learning_rate=lr, random_state=_SEED)

        return _fit_eval(self, ctx, make)


@register
class BaggingModel(Component):
    spec = _spec(
        "model.ml.bagging", "Bagging",
        "Trains many models on bootstrap resamples of the data and averages them (variance reduction).",
        {"n_estimators": {"type": "integer", "default": 50, "title": "Base models"}},
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.ensemble import BaggingClassifier, BaggingRegressor

        n = int(ctx.params.get("n_estimators", 50))

        def make(task):
            M = BaggingClassifier if task == "classification" else BaggingRegressor
            return M(n_estimators=n, random_state=_SEED)

        return _fit_eval(self, ctx, make)


@register
class GaussianProcessModel(Component):
    spec = _spec(
        "model.ml.gaussian_process", "Gaussian Process",
        "Bayesian kernel model with built-in uncertainty; O(n³), so rows are capped at 800.",
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from sklearn.gaussian_process import GaussianProcessClassifier, GaussianProcessRegressor
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        df = ctx.inputs["dataset"]
        if len(df) > 800:
            ctx.inputs["dataset"] = df.sample(n=800, random_state=_SEED)

        def make(task):
            M = GaussianProcessClassifier if task == "classification" else GaussianProcessRegressor
            return make_pipeline(StandardScaler(), M(random_state=_SEED))

        return _fit_eval(self, ctx, make)
