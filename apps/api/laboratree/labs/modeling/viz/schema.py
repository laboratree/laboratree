"""Shared response shapes for the staged model-visualization traces."""

from __future__ import annotations

from pydantic import BaseModel


class NodeStats(BaseModel):
    """One node's gradient bookkeeping — the inputs to the similarity score."""

    n: int  # rows that reached this node
    sum_g: float  # Σ gradients
    sum_h: float  # Σ hessians
    similarity: float  # (Σg)² / (Σh + λ)


class SplitTrial(BaseModel):
    """One audition: a candidate feature+threshold and the gain it would deliver."""

    feature: str
    threshold: float
    gain: float  # sim(L) + sim(R) − sim(parent) − γ
    left: NodeStats
    right: NodeStats
    eligible: bool = True  # False when a side's Σh < min_child_weight
    kept: bool = False  # the winning trial


class XGBNode(BaseModel):
    """A node in the exact-math boosted tree, with every trial it auditioned."""

    id: str  # "r", "rL", "rLR" …
    depth: int
    stats: NodeStats
    trials: list[SplitTrial] = []
    feature: str | None = None  # the chosen split (internal nodes)
    threshold: float | None = None
    gain: float | None = None
    pruned: bool = False  # had trials but best gain ≤ 0 → γ-pruned into a leaf
    leaf: bool = False
    value: float | None = None  # leaf output −Σg/(Σh+λ)
    left: XGBNode | None = None
    right: XGBNode | None = None


class XGBRound(BaseModel):
    """One boosting round: the (transformed) table it trains on + the tree it grew."""

    index: int
    # demo rows as this round sees them: {features…, actual, pred, g, h, residual}
    table: list[dict]
    root: XGBNode


class BoostingTrace(BaseModel):
    """The exact XGBoost math, round by round — powers the deep xgboost lesson."""

    objective: str  # "binary:logistic" | "reg:squarederror"
    base_score: float  # starting margin (0 → p=0.5) or the mean (regression)
    eta: float
    reg_lambda: float
    gamma: float
    min_child_weight: float
    trial_features: list[str]  # the features auditioned at every node
    rounds: list[XGBRound]
    positive_label: str | None = None  # multiclass runs binarize to this class vs rest


class ModelTrace(BaseModel):
    family: str  # "trees" | "linear" | "nn" | "knn" | "timeseries" | ...
    target: str
    task: str  # "classification" | "regression"
    features: list[str]  # the (top) feature columns shown
    labels: list[str] | None = None  # class label names (classification)
    table: list[dict] | None = None  # sample data rows (features + target) for the "the data" stage
    # trees
    tree: dict | None = None  # recursive node: {feature, threshold, gain, samples, leaf, prediction, left, right}
    baseline: float | None = None
    rounds: list[dict] | None = None  # legacy boosting rounds (kept for compatibility)
    # root-split threshold scan — how the tree auditioned cut-points for its FIRST question:
    # {parent_impurity, features: [{feature, candidates: [{t, impurity, gain, n_left, n_right}],
    #  best_t, best_gain}], chosen_feature}
    scan: dict | None = None
    # linear
    intercept: float | None = None
    coef: list[dict] | None = None
    samples: list[dict] | None = None
    # nn
    layers: list[int] | None = None
    forward: dict | None = None
    # knn — 2D scatter of (a sample of) the training rows: [{x, y, label}]
    points: list[dict] | None = None
    # timeseries / any family-specific extras: e.g. {x, y} axis names, history/fitted arrays, coefs
    series: dict | None = None
    # per-row testing walkthrough (all families): each row + how the prediction is formed
    test_rows: list[dict] | None = None
    # exact-math boosting (xgboost tracer): every similarity score, trial, and residual table
    boosting: BoostingTrace | None = None
    # tunable hyperparameters: the knobs the UI renders (with the live value) + the values used to fit.
    # Defaults come from the paper; the user can tweak and the trace re-fits with the new settings.
    param_spec: list[dict] | None = None
    params: dict | None = None
    note: str = ""


class FeatureSelectionTrace(BaseModel):
    target: str
    task: str
    features: list[str]  # the search space (top features)
    importances: list[dict]  # [{feature, importance}] one-feature fitness
    generations: list[dict]  # [{habitats:[{selected:[...], fitness}], best_fitness}]
    selected: list[str]
    best_fitness: float
    note: str
