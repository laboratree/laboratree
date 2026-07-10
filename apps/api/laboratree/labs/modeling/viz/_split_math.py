"""Split-criterion math shared by the tree-family tracers and their lessons.

Each impurity function returns the number AND the per-class breakdown, so lesson narrations can
show the full worked example ("2 of 5 rows are 'yes' → p = 0.4 → gini = 1 − (0.4² + 0.6²) …")
with the live data's counts.
"""

from __future__ import annotations

import numpy as np


def sigmoid(z: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-z))


def class_breakdown(y: np.ndarray) -> list[dict]:
    """Per-class {code, count, p} — the raw material for gini/entropy worked examples."""
    vals, counts = np.unique(y, return_counts=True)
    total = counts.sum() or 1
    return [
        {"code": int(v), "count": int(c), "p": round(float(c / total), 4)}
        for v, c in zip(vals, counts, strict=True)
    ]


def gini(y: np.ndarray) -> float:
    """1 − Σ pᵢ² — the chance two random draws disagree (0 = pure)."""
    if len(y) == 0:
        return 0.0
    _, counts = np.unique(y, return_counts=True)
    p = counts / counts.sum()
    return float(1.0 - float((p * p).sum()))


def entropy(y: np.ndarray) -> float:
    """−Σ pᵢ·log₂(pᵢ) — the expected surprise of the group (0 = pure)."""
    if len(y) == 0:
        return 0.0
    _, counts = np.unique(y, return_counts=True)
    p = counts / counts.sum()
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def mse(y: np.ndarray) -> float:
    """Mean squared distance to the group mean — the regression 'mix-up score'."""
    if len(y) == 0:
        return 0.0
    return float(((y - y.mean()) ** 2).mean())


def quantile_thresholds(x: np.ndarray, m: int = 8) -> list[float]:
    """Up to ``m`` interior candidate cut-points at the feature's quantiles (mirrors XGBoost's
    approximate sketch). Deduped and strictly inside (min, max) so no split is empty."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return []
    lo, hi = float(x.min()), float(x.max())
    if hi <= lo:
        return []
    qs = np.quantile(x, np.linspace(0, 1, m + 2)[1:-1])
    out: list[float] = []
    for q in qs:
        t = float(q)
        if lo < t < hi and (not out or abs(t - out[-1]) > 1e-12):
            out.append(round(t, 6))
    return out
