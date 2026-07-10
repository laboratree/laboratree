"""Anomaly-detection family — real per-algorithm mechanics on the actual data.

The 2-D map + per-row score/threshold are the shared base; the chosen detector is fitted for
real and its own mechanism is recorded so the lesson animates the student's real points:
  * isolation_forest -> every point's average isolation-path length + the path-length histogram
  * lof              -> each point's k-neighbourhood + its local-density ratio (LOF) on real rows
  * one_class_svm    -> the real learned boundary (a decision-function grid) around normal

Like clustering there is no answer column — the model learns what "usual" looks like.
"""

from __future__ import annotations

from . import register_tracer
from .common import resolve_params, split_holdout, table_rows
from .schema import ModelTrace

MAX_POINTS = 140
MECH_POINTS = 60


def _axes(X, feats):
    variances = [(f, float(X[f].std())) for f in feats]
    variances.sort(key=lambda t: -t[1])
    fx, fy = (variances[0][0], variances[1][0]) if len(variances) > 1 else (feats[0], feats[0])
    show = [f for f, _ in variances[:6]]
    return fx, fy, show, feats.index(fx), feats.index(fy)


IFOREST_SPEC = [
    {"key": "contamination", "label": "Contamination", "type": "float", "default": 0.08,
     "min": 0.01, "max": 0.4, "step": 0.01,
     "help": "Expected fraction of rows that are anomalies — sets how many get flagged."},
    {"key": "n_estimators", "label": "Trees in forest", "type": "int", "default": 100,
     "min": 20, "max": 400, "step": 20, "help": "How many random isolation trees to average over."},
]
LOF_SPEC = [
    {"key": "contamination", "label": "Contamination", "type": "float", "default": 0.08,
     "min": 0.01, "max": 0.4, "step": 0.01, "help": "Expected fraction of anomalies."},
    {"key": "n_neighbors", "label": "Neighbours (k)", "type": "int", "default": 20, "min": 5,
     "max": 50, "step": 5, "help": "Size of the local neighbourhood LOF compares densities over."},
]
OCSVM_SPEC = [
    {"key": "nu", "label": "ν (outlier budget)", "type": "float", "default": 0.08, "min": 0.01,
     "max": 0.4, "step": 0.01,
     "help": "Upper bound on the fraction of training rows left outside the boundary."},
]


def _iforest_mechanism(Xtr, fx, fy, ix, iy, p):
    """Real isolation forest: per-point average path length + the path-length histogram."""
    import numpy as np
    from sklearn.ensemble import IsolationForest

    iso = IsolationForest(contamination=p["contamination"], n_estimators=p["n_estimators"],
                          random_state=0).fit(Xtr)
    flag = iso.predict(Xtr)
    # score_samples is monotone with mean path length; expected path length c(n) normalises it.
    n = len(Xtr)
    c = 2 * (np.log(n - 1) + 0.5772156649) - 2 * (n - 1) / n if n > 2 else 1.0
    # anomaly score s = 2^(-E[h]/c); invert to recover E[h] (the average cuts to isolate)
    s = -iso.score_samples(Xtr)  # higher = more anomalous
    depth = np.clip(-np.log2(np.clip(s, 1e-6, None)) * c, 0.5, 3 * c)

    idxs = list(range(0, n, max(1, n // MECH_POINTS)))
    points = [{
        "x": round(float(Xtr.iloc[i][fx]), 3), "y": round(float(Xtr.iloc[i][fy]), 3),
        "depth": round(float(depth[i]), 2), "anomaly": bool(flag[i] < 0),
    } for i in idxs]
    # histogram of path lengths (short = suspicious)
    hist, edges = np.histogram(depth, bins=8)
    return {
        "kind": "isolation_forest", "points": points, "c_n": round(float(c), 2),
        "hist": [int(h) for h in hist],
        "edges": [round(float(e), 2) for e in edges],
    }, flag


def _lof_mechanism(Xtr, fx, fy, ix, iy, p):
    """Real LOF: the flagged point's k-neighbourhood + local-density ratios on real rows."""
    import numpy as np
    from sklearn.neighbors import LocalOutlierFactor

    k = min(p["n_neighbors"], max(2, len(Xtr) - 1))
    lof = LocalOutlierFactor(n_neighbors=k, contamination=p["contamination"])
    flag = lof.fit_predict(Xtr)
    scores = -lof.negative_outlier_factor_  # LOF ≈ 1 normal, ≫ 1 outlier

    Xa = Xtr[[fx, fy]].to_numpy(dtype=float)
    idxs = list(range(0, len(Xtr), max(1, len(Xtr) // MECH_POINTS)))
    points = [{
        "x": round(float(Xtr.iloc[i][fx]), 3), "y": round(float(Xtr.iloc[i][fy]), 3),
        "lof": round(float(scores[i]), 2), "anomaly": bool(flag[i] < 0),
    } for i in idxs]
    # highlight the top outlier + its k nearest (in the 2 map axes) for the neighbourhood ring
    top = int(np.argmax(scores))
    d = np.linalg.norm(Xa - Xa[top], axis=1)
    nbrs = np.argsort(d)[1 : k + 1]
    focus = {
        "x": round(float(Xa[top, 0]), 3), "y": round(float(Xa[top, 1]), 3),
        "lof": round(float(scores[top]), 2),
        "radius": round(float(d[nbrs].max()), 3),
        "neighbors": [{"x": round(float(Xa[j, 0]), 3), "y": round(float(Xa[j, 1]), 3)} for j in nbrs],
    }
    return {"kind": "lof", "k": k, "points": points, "focus": focus}, flag


def _ocsvm_mechanism(Xtr, fx, fy, ix, iy, p):
    """Real one-class SVM: the learned boundary as a decision-function grid over the 2 map axes."""
    import numpy as np
    from sklearn.svm import OneClassSVM

    Xa = Xtr[[fx, fy]].to_numpy(dtype=float)
    mu, sd = Xa.mean(0), Xa.std(0) + 1e-9
    Z = (Xa - mu) / sd
    oc = OneClassSVM(nu=p["nu"], gamma="scale").fit(Z)
    flag = oc.predict(Z)

    g = 22
    xs = np.linspace(Z[:, 0].min() - 0.5, Z[:, 0].max() + 0.5, g)
    ys = np.linspace(Z[:, 1].min() - 0.5, Z[:, 1].max() + 0.5, g)
    gx, gy = np.meshgrid(xs, ys)
    grid = np.c_[gx.ravel(), gy.ravel()]
    df = oc.decision_function(grid).reshape(g, g)

    def raw_x(z):
        return round(float(z * sd[0] + mu[0]), 3)

    def raw_y(z):
        return round(float(z * sd[1] + mu[1]), 3)

    idxs = list(range(0, len(Xtr), max(1, len(Xtr) // MECH_POINTS)))
    points = [{
        "x": round(float(Xa[i, 0]), 3), "y": round(float(Xa[i, 1]), 3),
        "anomaly": bool(flag[i] < 0),
    } for i in idxs]
    return {
        "kind": "one_class_svm", "nu": p["nu"],
        "grid": [[round(float(v), 3) for v in row] for row in df],
        "gx": [raw_x(v) for v in xs], "gy": [raw_y(v) for v in ys],
        "points": points,
    }, flag


_MECH = {
    "isolation_forest": (_iforest_mechanism, IFOREST_SPEC),
    "lof": (_lof_mechanism, LOF_SPEC),
    "one_class_svm": (_ocsvm_mechanism, OCSVM_SPEC),
}


@register_tracer("anomaly")
def trace_anomaly(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    import numpy as np
    from sklearn.ensemble import IsolationForest

    params = dict(params or {})
    model = str(params.pop("_model", "isolation_forest") or "isolation_forest")
    fn, spec = _MECH.get(model, _MECH["isolation_forest"])
    p, param_spec = resolve_params(spec, params)
    Xtr, Xte, _ytr, _yte = split_holdout(X, y)
    fx, fy, show, ix, iy = _axes(X, feats)

    mechanism, tr_flag = None, None
    try:
        mechanism, tr_flag = fn(Xtr, fx, fy, ix, iy, p)
    except Exception:  # any detector hiccup → fall back to the isolation-forest map
        mechanism, tr_flag = None, None

    # the shared base map + testing scores always come from an isolation forest (stable, fast)
    iso = IsolationForest(contamination=min(0.4, p.get("contamination", 0.08)),
                          random_state=0).fit(Xtr)
    if tr_flag is None:
        tr_flag = iso.predict(Xtr)

    step = max(1, len(Xtr) // MAX_POINTS)
    points = [
        {"x": round(float(Xtr.iloc[i][fx]), 3), "y": round(float(Xtr.iloc[i][fy]), 3),
         "label": "anomaly" if tr_flag[i] < 0 else "normal"}
        for i in range(0, len(Xtr), step)
    ]

    scores = iso.decision_function(Xte)
    flags = iso.predict(Xte)
    test_rows = [{
        "values": {f: round(float(Xte.iloc[j][f]), 3) for f in show},
        "x": round(float(Xte.iloc[j][fx]), 3), "y": round(float(Xte.iloc[j][fy]), 3),
        "score": round(float(scores[j]), 3),
        "predicted": "anomaly" if flags[j] < 0 else "normal", "actual": None,
        "correct": None, "error": None,
    } for j in range(len(Xte))]

    n_anom = int(np.sum(np.asarray(tr_flag) < 0))
    series = {"x": fx, "y": fy, "threshold": 0.0, "n_anomalies": n_anom, "n_train": int(len(Xtr))}
    if mechanism:
        series["mechanism"] = mechanism
    return ModelTrace(
        family="anomaly", target=target, task="anomaly", features=show, labels=labels,
        table=table_rows(X, y, show, target, task, labels),
        points=points, series=series,
        test_rows=test_rows, params=p, param_spec=param_spec,
        note="Anomaly detectors learn what 'usual' looks like and flag rows that don't fit. The "
        "mechanism chapter animates how THIS detector scored your real rows.",
    )
