"""Trees family — decision tree / random forest / XGBoost-style boosting.

Training view: the real fitted tree (splits + information gain). Testing view: the highlighted
root-to-leaf path for each held-out row.
"""

from __future__ import annotations

from . import register_tracer
from .common import lbl, resolve_params, split_holdout, table_rows
from .schema import ModelTrace

SPEC = [
    {"key": "max_depth", "label": "Tree depth", "type": "int", "default": 3, "min": 1, "max": 6,
     "step": 1, "help": "How many question-levels deep the single decision tree may grow."},
    {"key": "n_estimators", "label": "Boosting trees", "type": "int", "default": 3, "min": 1,
     "max": 6, "step": 1, "help": "How many trees the boosting ensemble (XGBoost-style) stacks."},
    {"key": "learning_rate", "label": "Learning rate", "type": "float", "default": 1.0, "min": 0.1,
     "max": 1.0, "step": 0.1, "help": "How much each new boosting tree is allowed to correct the last."},
]


def tree_to_dict(t, node_id, feats, task, labels):
    left, right = int(t.children_left[node_id]), int(t.children_right[node_id])
    n = int(t.n_node_samples[node_id])
    if left == right:  # leaf
        val = t.value[node_id][0]
        if task == "classification":
            cls = int(val.argmax())
            return {
                "leaf": True, "samples": n,
                "prediction": labels[cls] if labels else str(cls),
                "confidence": round(float(val.max() / (val.sum() or 1)), 2),
            }
        return {"leaf": True, "samples": n, "prediction": round(float(val[0]), 3)}
    imp = float(t.impurity[node_id])
    nl, nr = int(t.n_node_samples[left]), int(t.n_node_samples[right])
    gain = imp - (nl * float(t.impurity[left]) + nr * float(t.impurity[right])) / (n or 1)
    return {
        "leaf": False,
        "feature": feats[int(t.feature[node_id])],
        "threshold": round(float(t.threshold[node_id]), 3),
        "gain": round(float(gain), 4),
        "samples": n,
        "left": tree_to_dict(t, left, feats, task, labels),
        "right": tree_to_dict(t, right, feats, task, labels),
    }


def tree_path(t, feats, row):
    node, steps = 0, []
    while int(t.children_left[node]) != int(t.children_right[node]):
        f = feats[int(t.feature[node])]
        thr = float(t.threshold[node])
        val = float(row[f])
        go_left = val <= thr
        steps.append(
            {"feature": f, "value": round(val, 3), "threshold": round(thr, 3),
             "go": "left" if go_left else "right"}
        )
        node = int(t.children_left[node]) if go_left else int(t.children_right[node])
    return steps


def _impurity(vals, task):
    """The 'mix-up score' a split tries to reduce: gini (classification) or MSE (regression)."""
    import numpy as np

    if len(vals) == 0:
        return 0.0
    if task == "classification":
        _, counts = np.unique(vals, return_counts=True)
        p = counts / counts.sum()
        return float(1.0 - float((p * p).sum()))
    return float(((vals - vals.mean()) ** 2).mean())


def _split_scan(Xtr, ytr, feats, task, chosen_feature, n_thresholds=24):
    """Root-split threshold scan — the raw material for the 'how a split is chosen' animation.

    For the feature the fitted tree actually asked about first (plus the 2 next-best features by
    single-split gain), sweep ~24 evenly-spaced candidate thresholds and score each: the weighted
    child impurity, the gain vs the parent, and the left/right row counts. Cheap by construction
    (<=32 features x 24 cuts on the training rows)."""
    import numpy as np

    if chosen_feature is None:
        return None
    yv = np.asarray(ytr, dtype=float)
    n = len(yv)
    if n < 4:
        return None
    parent = _impurity(yv, task)
    sweep = list(feats[:32])
    if chosen_feature not in sweep:
        sweep = [chosen_feature, *sweep[:31]]
    scanned = []
    for f in sweep:
        x = np.asarray(Xtr[f], dtype=float)
        lo, hi = float(x.min()), float(x.max())
        if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
            continue
        cands = []
        for t_ in np.linspace(lo, hi, n_thresholds + 2)[1:-1]:  # interior cut-points only
            mask = x <= t_
            nl = int(mask.sum())
            nr = n - nl
            imp = parent if nl == 0 or nr == 0 else (
                nl * _impurity(yv[mask], task) + nr * _impurity(yv[~mask], task)
            ) / n
            cands.append({
                "t": round(float(t_), 4),
                "impurity": round(float(imp), 5),
                "gain": round(float(parent - imp), 5),
                "n_left": nl,
                "n_right": nr,
            })
        if not cands:
            continue
        best = max(cands, key=lambda c: c["gain"])
        scanned.append({
            "feature": f, "candidates": cands,
            "best_t": best["t"], "best_gain": best["gain"],
        })
    chosen = [s for s in scanned if s["feature"] == chosen_feature]
    if not chosen:
        return None
    runners_up = sorted(
        (s for s in scanned if s["feature"] != chosen_feature),
        key=lambda s: -s["best_gain"],
    )[:2]
    return {
        "parent_impurity": round(parent, 5),
        "features": chosen + runners_up,  # chosen first, then the best runners-up
        "chosen_feature": chosen_feature,
    }


def _fit_boosting(Xtr, ytr, task, n_rounds, lr):
    """A tiny REAL gradient-boosting ensemble (depth-2 trees) so the animation can show the actual
    additive mechanics: baseline -> tree1 -> +tree2 -> … -> score. Binary/regression only (multiclass
    boosting has one tree per class per round — too much to animate)."""
    import numpy as np
    from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor

    if task == "classification":
        if len(np.unique(ytr)) != 2:
            return None, None
        gb = GradientBoostingClassifier(
            n_estimators=n_rounds, max_depth=2, learning_rate=lr, random_state=0
        ).fit(Xtr, ytr)
        p = float(np.clip(ytr.mean(), 1e-6, 1 - 1e-6))
        baseline = float(np.log(p / (1 - p)))  # starting log-odds before any tree
    else:
        gb = GradientBoostingRegressor(
            n_estimators=n_rounds, max_depth=2, learning_rate=lr, random_state=0
        ).fit(Xtr, ytr)
        baseline = float(ytr.mean())
    return gb, baseline


@register_tracer("trees")
def trace_trees(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    import numpy as np
    from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

    cfg, param_spec = resolve_params(SPEC, params)
    n_rounds, lr = cfg["n_estimators"], cfg["learning_rate"]
    Xtr, Xte, ytr, yte = split_holdout(X, y)
    Model = DecisionTreeClassifier if task == "classification" else DecisionTreeRegressor
    tree = Model(max_depth=cfg["max_depth"], random_state=0).fit(Xtr, ytr)
    t = tree.tree_
    show = feats[:24]  # the testing table shows every feature (scrolls horizontally)

    # how the ROOT split was chosen — sweep candidate thresholds on the winning feature + runners-up
    root_feature = (
        feats[int(t.feature[0])] if int(t.children_left[0]) != int(t.children_right[0]) else None
    )
    scan = _split_scan(Xtr, ytr, feats, task, root_feature)

    # the real boosting ensemble (for XGBoost-style papers)
    gb, baseline = _fit_boosting(Xtr, ytr, task, n_rounds, lr)
    rounds = None
    if gb is not None:
        # the "transformed table" BETWEEN stages: for a handful of training rows, what each round
        # receives as input — the current prediction and the leftover error the next tree must fix
        demo = Xtr.iloc[:7]
        ydemo = ytr.iloc[:7]
        F = np.full(len(demo), baseline)
        show3 = feats[:3]
        rounds = []
        for r in range(n_rounds):
            est = gb.estimators_[r][0]
            table = []
            for i in range(len(demo)):
                cur = 1.0 / (1.0 + np.exp(-F[i])) if task == "classification" else F[i]
                truth = float(ydemo.iloc[i])
                resid = truth - cur
                table.append({
                    **{f: round(float(demo.iloc[i][f]), 2) for f in show3},
                    "actual": lbl(ydemo.iloc[i], task, labels),
                    "current": round(float(cur), 3),
                    "residual": round(float(resid), 3),
                })
            rounds.append({
                "tree": tree_to_dict(est.tree_, 0, feats, "regression", None),
                "table": table,  # what THIS round sees before it trains
            })
            F = F + lr * est.predict(demo)

    preds = tree.predict(Xte)
    test_rows = []
    for j in range(len(Xte)):
        row = Xte.iloc[j]
        pred = lbl(preds[j], task, labels)
        actual = lbl(yte.iloc[j], task, labels)
        tr = {
            "values": {f: round(float(row[f]), 3) for f in show},
            "path": tree_path(t, feats, row),
            "predicted": pred, "actual": actual,
            "correct": (pred == actual) if task == "classification" else None,
            "error": None if task == "classification" else round(float(preds[j]) - float(yte.iloc[j]), 3),
        }
        if gb is not None:
            contribs = []
            for r in range(n_rounds):
                est = gb.estimators_[r][0]
                contribs.append({
                    "path": tree_path(est.tree_, feats, row),
                    "value": round(float(lr * est.predict(row.to_frame().T)[0]), 3),
                })
            s = baseline + sum(c["value"] for c in contribs)
            tr["rounds"] = contribs
            tr["boost_score"] = round(float(s), 3)
            if task == "classification":
                prob = 1.0 / (1.0 + np.exp(-s))
                pi = 1 if prob > 0.5 else 0
                tr["boost_prob"] = round(float(prob), 3)
                tr["boost_pred"] = labels[pi] if labels else str(pi)
            else:
                tr["boost_pred"] = round(float(s), 3)
        test_rows.append(tr)

    return ModelTrace(
        family="trees", target=target, task=task, features=show, labels=labels,
        table=table_rows(X, y, feats[:8], target, task, labels),
        tree=tree_to_dict(t, 0, feats, task, labels),
        scan=scan,
        baseline=None if baseline is None else round(baseline, 3),
        rounds=rounds, test_rows=test_rows, params=cfg, param_spec=param_spec,
        note="A decision tree asks yes/no questions about the features. Each split is picked to best "
        "separate the groups — 'gain' measures how much cleaner (more one-class) the two sides become. "
        "Boosting (XGBoost) stacks several small trees: each new tree is trained on the mistakes left "
        "by the ones before it, and their outputs ADD UP into the final score.",
    )
