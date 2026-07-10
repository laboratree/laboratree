"""CNN family — the MLP base plus a REAL convolution + max-pool walkthrough.

The first demo row's (normalized) feature values are arranged into a grid; a small edge-detector
kernel slides across it computing every dot product; ReLU; then a 2×2 max-pool. Every number in
``series["conv"]`` is actually computed here, so the lesson's sliding-window animation shows the
true multiply-accumulate arithmetic — not a canned picture.
"""

from __future__ import annotations

from . import register_tracer
from .nn import trace_nn
from .schema import ModelTrace

GRID = 4  # grid side; up to 16 features shown as a 4×4 "image"
KERNEL = [[1.0, -1.0], [1.0, -1.0]]  # a vertical-edge detector — simple, honest, explainable


def _conv_demo(X, feats) -> dict:
    import numpy as np

    used = feats[: GRID * GRID]
    vals = np.asarray(X[used].iloc[0], dtype=float)
    lo, hi = float(vals.min()), float(vals.max())
    norm = (vals - lo) / (hi - lo) if hi > lo else np.zeros_like(vals)
    grid = np.zeros(GRID * GRID)
    grid[: len(norm)] = norm
    g = grid.reshape(GRID, GRID)

    k = np.asarray(KERNEL)
    out = GRID - 1  # valid convolution with a 2×2 kernel
    fmap = np.zeros((out, out))
    for i in range(out):
        for j in range(out):
            fmap[i, j] = float((g[i : i + 2, j : j + 2] * k).sum())
    relu = np.maximum(0.0, fmap)
    pout = out - 1  # 2×2 max-pool, stride 1
    pooled = np.zeros((pout, pout))
    for i in range(pout):
        for j in range(pout):
            pooled[i, j] = float(relu[i : i + 2, j : j + 2].max())

    r2 = lambda a: [[round(float(v), 2) for v in row] for row in a]  # noqa: E731
    return {
        "grid": r2(g), "kernel": r2(k), "fmap": r2(fmap), "relu": r2(relu),
        "pooled": r2(pooled), "feature_names": list(used),
    }


@register_tracer("cnn")
def trace_cnn(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    base = trace_nn(X, y, feats, target, task, labels, params=params)
    try:
        conv = _conv_demo(X, feats)
    except Exception:
        conv = None
    if conv:
        base.series = {**(base.series or {}), "conv": conv}
        base.note = (
            "A CNN slides one small detector (the kernel) across the whole input, computing a "
            "dot product at every position — the same pattern is found wherever it appears. "
            "Max-pooling then keeps the strongest evidence and shrinks the map. The dense head "
            "you see in the network diagram finishes the job."
        )
    return base
