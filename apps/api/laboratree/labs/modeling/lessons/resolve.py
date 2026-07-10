"""Resolve free model text ("XGBoost", "model.dl.rnn", "LSTM (bidirectional)") to lesson keys.

Returns an ordered fallback chain, finest first: ``["xgboost", "trees"]``, ``["lstm", "rnn",
"nn"]``. The lesson registry picks the first key with a hand-written script; the tracer picks
the first key that is a registered viz family. Mirrors (and refines) the frontend
``modelKind()`` in ``apps/web/components/ModelAnimation.tsx`` — most specific cues first.
"""

from __future__ import annotations

import re

# (pattern, chain) — first match wins, so keep specific cues above generic ones
# (e.g. "isolation forest" before "forest", "one-class svm" before "svm").
_RULES: list[tuple[str, list[str]]] = [
    # anomaly
    (r"isolation forest|iforest", ["isolation_forest", "anomaly"]),
    (r"\blof\b|local outlier", ["lof", "anomaly"]),
    (r"one.?class", ["one_class_svm", "anomaly"]),
    (r"anomal|outlier", ["anomaly"]),
    # clustering
    (r"k.?means", ["kmeans", "clustering"]),
    (r"dbscan", ["dbscan", "clustering"]),
    (r"gaussian mixture|\bgmm\b", ["gmm", "clustering"]),
    (r"hierarchical|agglomerative", ["hierarchical", "clustering"]),
    (r"spectral", ["spectral", "clustering"]),
    (r"cluster", ["clustering"]),
    # causal inference (before generic regression cues)
    (r"regression discontinuity|\brdd?\b|running variable|cutoff design", ["rdd", "causal", "linear"]),
    (r"diff.?in.?diff|difference.?in.?difference|\bdid\b|parallel trend", ["did", "causal", "linear"]),
    (r"instrumental|\biv\b|2sls|two.?stage least", ["iv", "causal", "linear"]),
    (r"\brct\b|a/?b test|randomi[sz]ed|treatment effect|experiment", ["rct", "causal", "linear"]),
    # volatility & multivariate time series (before generic time-series)
    (r"egarch|exponential garch", ["egarch", "volatility", "timeseries"]),
    (r"gjr|glosten|threshold garch|\btgarch\b|leverage effect", ["gjr_garch", "volatility", "timeseries"]),
    (r"garch", ["garch", "volatility", "timeseries"]),
    (r"\barch\b", ["arch", "volatility", "timeseries"]),
    (r"volatilit|conditional variance", ["garch", "volatility", "timeseries"]),
    (r"vecm|cointegrat|error.?correction", ["vecm", "timeseries"]),
    (r"\bvar\b|vector autoregress|impulse response", ["var", "timeseries"]),
    # time series
    (r"sarima", ["sarima", "arima", "timeseries"]),
    (r"arima|autoregressive integrated", ["arima", "timeseries"]),
    (r"\barma\b", ["arma", "timeseries"]),
    (r"\bar\(|\bar\b|autoregress", ["ar", "timeseries"]),
    (r"\bma\b|\bma\(|moving average", ["ma", "timeseries"]),
    (r"exponential smoothing|holt|\bets\b", ["ets", "timeseries"]),
    (r"time.?series|forecast|prophet", ["timeseries"]),
    # deep learning
    (r"transformer|attention|\bbert\b|\bgpt\b|\bvit\b", ["transformer"]),
    (r"lstm", ["lstm", "rnn", "nn"]),
    (r"\bgru\b", ["gru", "rnn", "nn"]),
    (r"\brnn\b|recurrent", ["rnn", "nn"]),
    (r"\bcnn\b|convolution", ["cnn", "nn"]),
    (r"\bmlp\b|neural|perceptron|deep|network|\bdnn\b|autoencoder", ["mlp", "nn"]),
    # trees & ensembles
    (r"xgboost|\bxgb\b", ["xgboost", "trees"]),
    (r"lightgbm|catboost|gradient.?boost|\bgbm\b|\bgbdt\b|hist.?gradient", ["gradient_boosting", "trees"]),
    (r"extra.?trees|extremely random", ["extra_trees", "random_forest", "trees"]),
    (r"random forest|\brf\b", ["random_forest", "trees"]),
    (r"adaboost|ada.?boost", ["adaboost", "trees"]),
    (r"bagging", ["bagging", "random_forest", "trees"]),
    (r"decision tree|decision.?stump|\bcart\b", ["decision_tree", "trees"]),
    (r"boost|tree|forest|ensemble", ["trees"]),
    # neighbors
    (r"k.?nearest|nearest neighbou?r|\bknn\b", ["knn"]),
    # linear-family & econometrics (probit before logit/logistic: "probit" contains no "logit"
    # but keep explicit ordering anyway; gaussian process before generic "regression")
    (r"gaussian process|\bgp\b|kriging", ["gaussian_process", "trees"]),
    (r"pooled", ["pooled_ols", "panel", "econometrics", "linear"]),
    (r"fixed.?effect|within estimator", ["fixed_effects", "panel", "econometrics", "linear"]),
    (r"random.?effect|mixed.?effect|multilevel|hierarchical model",
     ["random_effects", "panel", "econometrics", "linear"]),
    (r"panel", ["panel", "econometrics", "linear"]),
    (r"multinomial|\bmnl\b|conditional logit", ["multinomial_logit", "linear"]),
    (r"ordered logit|ordinal logit|proportional odds", ["ordered_logit", "linear"]),
    (r"ordered probit|ordinal probit", ["ordered_probit", "linear"]),
    (r"probit", ["probit", "econometrics", "linear"]),
    (r"logit", ["logit", "econometrics", "logistic_regression", "linear"]),
    (r"weighted least|\bwls\b", ["wls", "linear"]),
    (r"generalized least|\bgls\b|feasible gls|\bfgls\b", ["gls", "linear"]),
    (r"robust regression|\brobust\b|\brlm\b|huber|\bm.?estimat", ["robust", "linear"]),
    (r"zero.?inflated poisson|\bzip\b", ["zip", "econometrics", "linear"]),
    (r"zero.?inflated", ["zip", "econometrics", "linear"]),
    (r"quantile|median regression|pinball", ["quantile", "econometrics", "linear"]),
    (r"negative.?binomial|overdispers|\bnb\b", ["negative_binomial", "econometrics", "linear"]),
    (r"poisson", ["poisson", "econometrics", "linear"]),
    (r"\bols\b|ordinary least", ["ols", "econometrics", "linear_regression", "linear"]),
    (r"elastic.?net", ["elastic_net", "regularized", "linear"]),
    (r"ridge", ["ridge", "regularized", "linear"]),
    (r"lasso", ["lasso", "regularized", "linear"]),
    (r"support vector|\bsvm\b|\bsvc\b|\bsvr\b", ["svm", "linear"]),
    (r"naive bayes|\bbayes\b", ["naive_bayes", "linear"]),
    (r"logistic", ["logistic_regression", "linear"]),
    (r"linear regression|linear model|\blpm\b|regression|\bglm\b", ["linear_regression", "linear"]),
    (r"linear", ["linear"]),
]

_DEFAULT_CHAIN = ["trees"]  # same teaching default as viz.build_trace


def lesson_keys(model_text: str) -> list[str]:
    """Ordered lesson-key fallback chain for free model text (never empty)."""
    s = (model_text or "").lower().replace("_", " ").replace(".", " ")
    for pattern, chain in _RULES:
        if re.search(pattern, s):
            return list(chain)
    return list(_DEFAULT_CHAIN)
