"""Raking (iterative proportional fitting) to target margins + design diagnostics.

``rake`` returns one weight per record such that the weighted category shares of each margin
column match the targets (within tolerance). Diagnostics follow Kish: effective N =
(Σw)² / Σw², design effect = n / effective N.
"""

from __future__ import annotations

import logging
from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from .. import as_records

log = logging.getLogger(__name__)

MAX_ITERATIONS = 100
TOLERANCE = 1e-4
WEIGHT_FLOOR = 0.01   # avoid zero/negative weights
WEIGHT_CAP = 10.0     # avoid a handful of respondents dominating


def _shares(records: list[dict[str, Any]], weights: list[float], column: str) -> dict[str, float]:
    total = sum(weights)
    by_cat: dict[str, float] = {}
    for record, weight in zip(records, weights, strict=True):
        category = str(record.get(column))
        by_cat[category] = by_cat.get(category, 0.0) + weight
    return {c: v / total for c, v in by_cat.items()} if total > 0 else {}


def rake(
    records: list[dict[str, Any]],
    margins: dict[str, dict[str, float]],
    *,
    max_iterations: int = MAX_ITERATIONS,
    tolerance: float = TOLERANCE,
) -> dict[str, Any]:
    """Return {weights, converged, iterations, effective_n, design_effect, achieved}.

    ``margins``: {column: {category: target_share}}; shares are normalised per column. Records
    whose category has no target keep their weight for that column (share denominator excludes
    them from adjustment).
    """
    n = len(records)
    if n == 0 or not margins:
        return {"weights": [1.0] * n, "converged": True, "iterations": 0,
                "effective_n": float(n), "design_effect": 1.0, "achieved": {}}

    normalized: dict[str, dict[str, float]] = {}
    for column, targets in margins.items():
        total = sum(v for v in targets.values() if isinstance(v, (int, float)) and v > 0)
        if total <= 0:
            continue
        normalized[column] = {str(k): float(v) / total for k, v in targets.items() if v > 0}

    weights = [1.0] * n
    converged = False
    iterations = 0
    while iterations < max_iterations:
        iterations += 1
        max_gap = 0.0
        for column, targets in normalized.items():
            shares = _shares(records, weights, column)
            for i, record in enumerate(records):
                category = str(record.get(column))
                target = targets.get(category)
                current = shares.get(category, 0.0)
                if target is not None and current > 0:
                    weights[i] = min(max(weights[i] * (target / current), WEIGHT_FLOOR), WEIGHT_CAP)
            shares_after = _shares(records, weights, column)
            for category, target in targets.items():
                max_gap = max(max_gap, abs(shares_after.get(category, 0.0) - target))
        if max_gap < tolerance:
            converged = True
            break

    total_w = sum(weights)
    sum_sq = sum(w * w for w in weights)
    effective_n = (total_w * total_w / sum_sq) if sum_sq > 0 else 0.0
    achieved = {column: _shares(records, weights, column) for column in normalized}
    log.info("raking: n=%d converged=%s iters=%d eff_n=%.1f", n, converged, iterations, effective_n)
    return {
        "weights": [round(w, 6) for w in weights],
        "converged": converged,
        "iterations": iterations,
        "effective_n": round(effective_n, 2),
        "design_effect": round(n / effective_n, 4) if effective_n > 0 else None,
        "achieved": achieved,
    }


@register
class RakeWeights(Component):
    spec = ComponentSpec(
        kind=ComponentKind.TRANSFORM,
        id="transform.rake_weights",
        name="Rake survey weights",
        summary="Post-stratify to target margins (IPF); adds a weight column + Kish diagnostics.",
        params_schema={
            "type": "object",
            "properties": {
                "margins": {"type": "object",
                            "description": "{column: {category: target_share}}"},
                "weight_column": {"type": "string", "default": "_weight"},
            },
            "required": ["margins"],
        },
        inputs=[Port(name="dataset", dtype="records")],
        outputs=[Port(name="dataset", dtype="records")],
        tags=["tabulation", "weights"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        records = as_records(ctx.inputs.get("dataset"))
        weight_column = str(ctx.params.get("weight_column") or "_weight")
        result = rake(records, ctx.params.get("margins") or {})
        for record, weight in zip(records, result["weights"], strict=True):
            record[weight_column] = weight
        ctx.emit("effective_n", result["effective_n"], kind="metric", component=self.spec.id)
        ctx.emit("design_effect", result["design_effect"], kind="metric", component=self.spec.id)
        ctx.emit("rake_converged", result["converged"], kind="metric", component=self.spec.id)
        return {"dataset": records, "diagnostics": {k: v for k, v in result.items() if k != "weights"}}


__all__ = ["rake", "RakeWeights"]
