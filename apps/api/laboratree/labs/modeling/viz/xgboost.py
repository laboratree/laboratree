"""XGBoost family — the EXACT math, reimplemented so every step can be shown.

Native XGBoost only reports the splits it kept; the lesson needs the AUDITIONS — every
candidate threshold's similarity scores and gain, the γ-pruning decisions, the per-round
gradient/hessian tables. So this tracer runs XGBoost's exact-greedy algorithm by hand on a
small slice of the real data (validated against native XGBoost in tests): per round it
computes g/h, grows a tree by maximising gain = sim(L)+sim(R)−sim(parent)−γ over quantile
candidate thresholds, sets leaf values −Σg/(Σh+λ), and updates F += η·tree(x).

Emits BOTH the rich ``boosting`` trace (for the deep lesson) and the legacy tree/rounds/test
shapes, so the classic ensemble animation keeps working unchanged.
"""

from __future__ import annotations

import numpy as np

from . import register_tracer
from ._split_math import quantile_thresholds, sigmoid
from .common import lbl, resolve_params, split_holdout, table_rows
from .schema import BoostingTrace, ModelTrace, NodeStats, SplitTrial, XGBNode, XGBRound

SPEC = [
    {"key": "eta", "label": "Learning rate (η)", "type": "float", "default": 0.3, "min": 0.05,
     "max": 1.0, "step": 0.05,
     "help": "How much of each tree's correction is applied. Small η + more trees = steadier."},
    {"key": "max_depth", "label": "Tree depth", "type": "int", "default": 3, "min": 1, "max": 3,
     "step": 1, "help": "Question-levels per tree. Shallow trees are weak learners on purpose."},
    {"key": "n_estimators", "label": "Boosting rounds", "type": "int", "default": 3, "min": 1,
     "max": 3, "step": 1, "help": "How many trees are stacked; each fixes what's still wrong."},
    {"key": "reg_lambda", "label": "λ (L2 regularisation)", "type": "float", "default": 1.0,
     "min": 0.0, "max": 10.0, "step": 0.5,
     "help": "Shrinks similarity scores and leaf values — bigger λ = more cautious trees."},
    {"key": "gamma", "label": "γ (min split gain)", "type": "float", "default": 0.0, "min": 0.0,
     "max": 5.0, "step": 0.25,
     "help": "A split must beat this gain or the branch is pruned away."},
    {"key": "min_child_weight", "label": "Min child weight", "type": "float", "default": 1.0,
     "min": 0.0, "max": 10.0, "step": 0.5,
     "help": "Each side of a split needs at least this much Σh (evidence) to be allowed."},
]

FIT_MAX_ROWS = 400
TRIAL_FEATURES = 3  # features auditioned at every node (top by root gain)
TRIAL_THRESHOLDS = 8  # quantile candidate cut-points per feature
RANK_FEATURES = 8  # features considered when picking the trial set
MIN_NODE_ROWS = 4
DEMO_ROWS = 7  # rows shown in each round's transformed table


def _stats(g: np.ndarray, h: np.ndarray, lam: float) -> NodeStats:
    sg, sh = float(g.sum()), float(h.sum())
    return NodeStats(
        n=len(g), sum_g=round(sg, 4), sum_h=round(sh, 4),
        similarity=round(sg * sg / (sh + lam), 4),
    )


def _leaf_value(g: np.ndarray, h: np.ndarray, lam: float) -> float:
    return round(float(-g.sum() / (h.sum() + lam)), 4)


def _trials(
    Xa: np.ndarray, g: np.ndarray, h: np.ndarray, idx: np.ndarray,
    trial_feats: list[tuple[int, str]], parent: NodeStats, cfg: dict,
) -> list[SplitTrial]:
    lam, gamma, mcw = cfg["reg_lambda"], cfg["gamma"], cfg["min_child_weight"]
    out: list[SplitTrial] = []
    for fi, fname in trial_feats:
        x = Xa[idx, fi]
        for t in quantile_thresholds(x, TRIAL_THRESHOLDS):
            mask = x <= t
            li, ri = idx[mask], idx[~mask]
            if len(li) == 0 or len(ri) == 0:
                continue
            left, right = _stats(g[li], h[li], lam), _stats(g[ri], h[ri], lam)
            gain = left.similarity + right.similarity - parent.similarity - gamma
            out.append(SplitTrial(
                feature=fname, threshold=round(float(t), 4), gain=round(float(gain), 4),
                left=left, right=right,
                eligible=left.sum_h >= mcw and right.sum_h >= mcw,
            ))
    return out


def _grow(
    node_id: str, depth: int, idx: np.ndarray, Xa: np.ndarray,
    g: np.ndarray, h: np.ndarray, trial_feats: list[tuple[int, str]], cfg: dict,
) -> XGBNode:
    """XGBoost's exact-greedy split search, recorded trial by trial."""
    lam = cfg["reg_lambda"]
    parent = _stats(g[idx], h[idx], lam)
    node = XGBNode(id=node_id, depth=depth, stats=parent)
    if depth >= cfg["max_depth"] or len(idx) < MIN_NODE_ROWS:
        node.leaf, node.value = True, _leaf_value(g[idx], h[idx], lam)
        return node

    node.trials = _trials(Xa, g, h, idx, trial_feats, parent, cfg)
    eligible = [t for t in node.trials if t.eligible]
    best = max(eligible, key=lambda t: t.gain, default=None)
    if best is None or best.gain <= 0:
        node.leaf, node.pruned = True, bool(node.trials)
        node.value = _leaf_value(g[idx], h[idx], lam)
        return node

    best.kept = True
    node.feature, node.threshold, node.gain = best.feature, best.threshold, best.gain
    fi = next(i for i, name in trial_feats if name == best.feature)
    mask = Xa[idx, fi] <= best.threshold
    node.left = _grow(node_id + "L", depth + 1, idx[mask], Xa, g, h, trial_feats, cfg)
    node.right = _grow(node_id + "R", depth + 1, idx[~mask], Xa, g, h, trial_feats, cfg)
    return node


def _predict(node: XGBNode, row: dict[str, float]) -> float:
    while not node.leaf:
        assert node.feature is not None and node.threshold is not None
        node = node.left if row[node.feature] <= node.threshold else node.right  # type: ignore[assignment]
        assert node is not None
    return float(node.value or 0.0)


def _path(node: XGBNode, row: dict[str, float]) -> list[dict]:
    steps = []
    while not node.leaf:
        assert node.feature is not None and node.threshold is not None
        go_left = row[node.feature] <= node.threshold
        steps.append({
            "feature": node.feature, "value": round(row[node.feature], 3),
            "threshold": round(node.threshold, 3), "go": "left" if go_left else "right",
        })
        node = node.left if go_left else node.right  # type: ignore[assignment]
        assert node is not None
    return steps


def _to_legacy(node: XGBNode) -> dict:
    """XGBNode → the legacy TreeNode shape the classic SVG diagram renders."""
    if node.leaf:
        return {"leaf": True, "samples": node.stats.n, "prediction": node.value}
    assert node.left is not None and node.right is not None
    return {
        "leaf": False, "feature": node.feature, "threshold": node.threshold,
        "gain": node.gain, "samples": node.stats.n,
        "left": _to_legacy(node.left), "right": _to_legacy(node.right),
    }


def _rank_trial_features(
    Xa: np.ndarray, g: np.ndarray, h: np.ndarray, feats: list[str], cfg: dict,
) -> list[tuple[int, str]]:
    """Top features by best single-split gain at the round-1 root — the audition shortlist."""
    root = _stats(g, h, cfg["reg_lambda"])
    idx = np.arange(len(g))
    scored: list[tuple[float, int, str]] = []
    for fi, fname in list(enumerate(feats))[:RANK_FEATURES]:
        trials = _trials(Xa, g, h, idx, [(fi, fname)], root, cfg)
        best = max((t.gain for t in trials), default=float("-inf"))
        scored.append((best, fi, fname))
    scored.sort(key=lambda s: -s[0])
    return [(fi, fname) for _, fi, fname in scored[:TRIAL_FEATURES]]


@register_tracer("xgboost")
def trace_xgboost(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    cfg, param_spec = resolve_params(SPEC, params)
    eta, lam, n_rounds = cfg["eta"], cfg["reg_lambda"], cfg["n_estimators"]
    Xtr, Xte, ytr, yte = split_holdout(X, y)
    Xtr, ytr = Xtr.iloc[:FIT_MAX_ROWS], ytr.iloc[:FIT_MAX_ROWS]

    # binary objective; multiclass runs binarize to the most common class vs rest (and say so)
    positive_label: str | None = None
    if task == "classification":
        yt = np.asarray(ytr, dtype=float)
        classes = np.unique(yt)
        if len(classes) > 2:
            pos = int(np.bincount(yt.astype(int)).argmax())
            positive_label = labels[pos] if labels else str(pos)
            labels_bin = [f"not {positive_label}", positive_label]
            ytr_b = (yt == pos).astype(float)
            yte_b = (np.asarray(yte, dtype=float) == pos).astype(float)
        else:
            labels_bin = labels or ["0", "1"]
            ytr_b, yte_b = yt, np.asarray(yte, dtype=float)
        base = 0.0  # margin 0 → p = 0.5: "start by guessing 50/50"
        objective = "binary:logistic"
    else:
        labels_bin = None
        ytr_b, yte_b = np.asarray(ytr, dtype=float), np.asarray(yte, dtype=float)
        base = float(ytr_b.mean())
        objective = "reg:squarederror"

    Xa = Xtr[feats].to_numpy(dtype=float)
    n = len(ytr_b)
    F = np.full(n, base)

    def grads(Fv: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if task == "classification":
            p = sigmoid(Fv)
            return p - ytr_b, p * (1 - p), p  # g, h, current prediction
        return Fv - ytr_b, np.ones_like(Fv), Fv

    g0, h0, _ = grads(F)
    trial_feats = _rank_trial_features(Xa, g0, h0, feats, cfg)
    show3 = [fname for _, fname in trial_feats]

    rounds_rich: list[XGBRound] = []
    rounds_legacy: list[dict] = []
    trees: list[XGBNode] = []
    for r in range(n_rounds):
        g, h, cur = grads(F)
        rich_table, legacy_table = [], []
        for i in range(min(DEMO_ROWS, n)):
            fvals = {f: round(float(Xtr.iloc[i][f]), 2) for f in show3}
            actual = lbl(ytr_b[i], task, labels_bin)
            common = {"actual": actual, "current": round(float(cur[i]), 3),
                      "residual": round(float(ytr_b[i] - cur[i]), 3)}
            legacy_table.append({**fvals, **common})
            rich_table.append({**fvals, **common,
                               "g": round(float(g[i]), 3), "h": round(float(h[i]), 3)})
        root = _grow("r", 0, np.arange(n), Xa, g, h, trial_feats, cfg)
        trees.append(root)
        rounds_rich.append(XGBRound(index=r, table=rich_table, root=root))
        rounds_legacy.append({"tree": _to_legacy(root), "table": legacy_table})
        F = F + eta * np.array(
            [_predict(root, dict(zip(feats, Xa[i], strict=True))) for i in range(n)]
        )

    # per-row testing walkthrough: every round's path + leaf value, then the assembled score
    show = feats[:24]
    test_rows = []
    for j in range(len(Xte)):
        row = Xte.iloc[j]
        rowd = {f: float(row[f]) for f in feats}
        contribs = [
            {"path": _path(t, rowd), "value": round(eta * _predict(t, rowd), 3)} for t in trees
        ]
        score = base + sum(c["value"] for c in contribs)
        truth = float(yte_b[j])
        actual = lbl(truth, task, labels_bin)
        tr = {
            "values": {f: round(float(row[f]), 3) for f in show},
            "path": contribs[0]["path"],
            "actual": actual,
            "rounds": contribs,
            "boost_score": round(float(score), 3),
        }
        if task == "classification":
            prob = float(sigmoid(score))
            pred = (labels_bin or ["0", "1"])[1 if prob > 0.5 else 0]
            tr.update({"predicted": pred, "correct": pred == actual,
                       "boost_prob": round(prob, 3), "boost_pred": pred, "error": None})
        else:
            tr.update({"predicted": round(float(score), 3), "correct": None,
                       "boost_pred": round(float(score), 3),
                       "error": round(float(score - truth), 3)})
        test_rows.append(tr)

    boosting = BoostingTrace(
        objective=objective, base_score=round(base, 4), eta=eta, reg_lambda=lam,
        gamma=cfg["gamma"], min_child_weight=cfg["min_child_weight"],
        trial_features=show3, rounds=rounds_rich, positive_label=positive_label,
    )
    binarized = f" (multiclass shown as '{positive_label}' vs rest)" if positive_label else ""
    return ModelTrace(
        family="xgboost", target=target, task=task, features=show, labels=labels_bin,
        table=table_rows(X, y, feats[:8], target, task, labels),
        tree=_to_legacy(trees[0]),
        baseline=round(base, 3),
        rounds=rounds_legacy,
        boosting=boosting,
        test_rows=test_rows, params=cfg, param_spec=param_spec,
        note="This is XGBoost's real arithmetic on your data"
        + binarized
        + ": each round computes every row's gradient g and hessian h, auditions candidate "
        "splits by similarity score (Σg)²/(Σh+λ), keeps the split with the highest gain, sets "
        "leaf values −Σg/(Σh+λ), and nudges every prediction by η times its leaf.",
    )
