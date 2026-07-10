"""Linear family — logistic / linear regression, SVM-style weighted scoring, probit.

Training view: one learned weight per feature. Testing view: per-row feature x weight
contributions summed into a score (sigmoid -> probability for classification).
"""

from __future__ import annotations

import logging

from . import register_tracer
from .common import lbl, resolve_params, split_holdout, table_rows
from .schema import ModelTrace

log = logging.getLogger(__name__)

SPEC_CLF = [
    {"key": "C", "label": "Inverse regularization (C)", "type": "float", "default": 1.0,
     "min": 0.01, "max": 10.0, "step": 0.01,
     "help": "Smaller C = stronger regularization (weights pulled toward 0, simpler boundary)."},
    {"key": "max_iter", "label": "Max iterations", "type": "int", "default": 500, "min": 100,
     "max": 2000, "step": 100, "help": "How long the optimizer may run to fit the weights."},
]
SPEC_REG = [
    {"key": "alpha", "label": "Ridge penalty (α)", "type": "float", "default": 0.0, "min": 0.0,
     "max": 10.0, "step": 0.1,
     "help": "0 = plain least squares; larger α shrinks the weights to curb overfitting."},
]


def _sgd_loss_curve(Xtr, ytr, feats, epochs=40):
    """Illustrative gradient-descent trace for the 'loss descends' animation: an equivalent
    logistic model trained step-by-step (SGD, log-loss) on standardized features. Records the
    per-epoch training loss AND weight-table snapshots at a few checkpoints — the 'state between
    stages': watch the weights start random, grow, and settle as the error falls."""
    import numpy as np

    try:
        from sklearn.linear_model import SGDClassifier
        from sklearn.metrics import log_loss
        from sklearn.preprocessing import StandardScaler

        classes = np.unique(ytr)
        if len(classes) < 2:
            return None
        Xs = StandardScaler().fit_transform(Xtr)
        clf = SGDClassifier(loss="log_loss", learning_rate="constant", eta0=0.05, random_state=0)
        curve = []
        marks = {1, max(2, epochs // 4), max(3, epochs // 2), epochs}
        stages = []
        top6: list[int] = []
        for e in range(1, epochs + 1):
            clf.partial_fit(Xs, ytr, classes=classes)
            loss = float(log_loss(ytr, clf.predict_proba(Xs), labels=classes))
            curve.append(round(loss, 4))
            if e in marks:
                w = clf.coef_[0]
                if not top6:  # fix the displayed features at the final ordering's best guess
                    top6 = list(np.argsort(-np.abs(w))[:6])
                stages.append({
                    "epoch": e,
                    "loss": round(loss, 4),
                    "weights": [
                        {"feature": feats[i], "weight": round(float(w[i]), 3)} for i in top6
                    ],
                })
        return {"loss_curve": curve, "weight_stages": stages}
    except Exception as exc:  # the curve is a bonus visual — never let it break the trace
        log.debug("SGD loss-curve visual skipped (non-fatal): %s", exc)
        return None


def _regression_fit(Xtr, ytr, feats, target, n_points=44):
    """The classic least-squares picture on the REAL data: the single most-correlated feature vs
    the target, the best-fit simple-regression line, and every point's residual (actual → the
    predicted point ON the line). Also the 'just predict the mean' baseline, so the animation can
    show the squared error shrinking from the flat line down to the fitted one (that ratio is R²)."""
    import numpy as np

    y = np.asarray(ytr, dtype=float)
    if len(y) < 3 or float(np.std(y)) == 0:
        return None
    # pick the feature most linearly related to the target
    best_f, best_r = None, -1.0
    for f in feats:
        x = np.asarray(Xtr[f], dtype=float)
        if np.std(x) == 0:
            continue
        r = abs(float(np.corrcoef(x, y)[0, 1]))
        if np.isfinite(r) and r > best_r:
            best_f, best_r = f, r
    if best_f is None:
        return None

    x = np.asarray(Xtr[best_f], dtype=float)
    b = float(np.cov(x, y, bias=True)[0, 1] / np.var(x))  # slope
    a = float(y.mean() - b * x.mean())  # intercept
    mean_y = float(y.mean())
    pred = a + b * x
    sse_line = float(np.sum((y - pred) ** 2))
    sse_mean = float(np.sum((y - mean_y) ** 2))
    r2 = 1.0 - sse_line / sse_mean if sse_mean > 0 else 0.0

    step = max(1, len(x) // n_points)
    idx = list(range(0, len(x), step))
    points = [{"x": round(float(x[i]), 3), "y": round(float(y[i]), 3),
               "yhat": round(float(pred[i]), 3)} for i in idx]
    return {
        "regression_fit": {
            "feature": best_f, "target": target,
            "slope": round(b, 4), "intercept": round(a, 4),
            "mean_y": round(mean_y, 3),
            "sse_line": round(sse_line, 1), "sse_mean": round(sse_mean, 1),
            "r2": round(float(r2), 3), "points": points,
        }
    }


@register_tracer("linear")
def trace_linear(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    import numpy as np

    Xtr, Xte, ytr, yte = split_holdout(X, y)
    series = None
    if task == "classification":
        from sklearn.linear_model import LogisticRegression

        p, param_spec = resolve_params(SPEC_CLF, params)
        model = LogisticRegression(C=p["C"], max_iter=p["max_iter"]).fit(Xtr, ytr)
        coef = model.coef_[0]
        intercept = float(model.intercept_[0])
        series = _sgd_loss_curve(Xtr, ytr, feats)  # regression skips this (no descent curve)
    else:
        from sklearn.linear_model import LinearRegression, Ridge

        p, param_spec = resolve_params(SPEC_REG, params)
        model = (
            Ridge(alpha=p["alpha"]) if p["alpha"] > 0 else LinearRegression()
        ).fit(Xtr, ytr)
        coef = model.coef_
        intercept = float(model.intercept_)
        series = _regression_fit(Xtr, ytr, feats, target)  # scatter + best-fit line + residuals
    order = np.argsort(-np.abs(coef))[:6]
    top = [feats[i] for i in order]
    coef_list = [{"feature": feats[i], "weight": round(float(coef[i]), 4)} for i in order]

    def contribs_for(row):
        return [
            {"feature": f, "value": round(float(row[f]), 3),
             "weight": round(float(coef[feats.index(f)]), 4),
             "product": round(float(row[f] * coef[feats.index(f)]), 3)}
            for f in top
        ]

    test_rows = []
    for j in range(len(Xte)):
        row = Xte.iloc[j]
        cs = contribs_for(row)
        s = float(intercept + sum(c["product"] for c in cs))
        if task == "classification":
            prob = 1.0 / (1.0 + np.exp(-s))
            pi = 1 if prob > 0.5 else 0
            pred = labels[pi] if labels else str(pi)
            score = round(float(prob), 3)
            err = None
        else:
            pred = round(s, 3)
            score = None
            err = round(s - float(yte.iloc[j]), 3)
        actual = lbl(yte.iloc[j], task, labels)
        test_rows.append({
            "values": {f: round(float(row[f]), 3) for f in feats[:24]},
            "contributions": cs, "sum": round(s, 3), "score": score,
            "predicted": pred, "actual": actual,
            "correct": (pred == actual) if task == "classification" else None, "error": err,
        })
    return ModelTrace(
        family="linear", target=target, task=task, features=top, labels=labels,
        table=table_rows(X, y, top, target, task, labels),
        intercept=round(intercept, 4), coef=coef_list, series=series, test_rows=test_rows,
        params=p, param_spec=param_spec,
        note="Each feature is multiplied by a learned weight (bigger weight = more influence). The "
        + ("products are added up, then the sigmoid squeezes the total into a probability, then a class."
           if task == "classification" else "products are added up to give the predicted number."),
    )
