"""Survey metrics: NPS, top-2-box, and weighted mean with a 95% CI."""

from __future__ import annotations

import logging
import math
from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from .. import as_records

log = logging.getLogger(__name__)

Z_95 = 1.96
NPS_PROMOTER_MIN = 9
NPS_DETRACTOR_MAX = 6


def _values_weights(
    records: list[dict[str, Any]], column: str, weight_column: str | None
) -> tuple[list[float], list[float]]:
    values: list[float] = []
    weights: list[float] = []
    for record in records:
        value = record.get(column)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        weight = record.get(weight_column) if weight_column else 1.0
        weight = float(weight) if isinstance(weight, (int, float)) and weight > 0 else 1.0
        values.append(float(value))
        weights.append(weight)
    return values, weights


def nps(records: list[dict[str, Any]], column: str, weight_column: str | None = None) -> dict[str, Any]:
    """Net Promoter Score on a 0–10 item: %promoters(9–10) − %detractors(0–6)."""
    values, weights = _values_weights(records, column, weight_column)
    total = sum(weights)
    if total == 0:
        return {"nps": None, "n": 0}
    promoters = sum(w for v, w in zip(values, weights, strict=True) if v >= NPS_PROMOTER_MIN) / total
    detractors = sum(w for v, w in zip(values, weights, strict=True) if v <= NPS_DETRACTOR_MAX) / total
    return {
        "nps": round(100 * (promoters - detractors), 1),
        "promoters_pct": round(100 * promoters, 1),
        "passives_pct": round(100 * (1 - promoters - detractors), 1),
        "detractors_pct": round(100 * detractors, 1),
        "n": len(values),
    }


def top2box(
    records: list[dict[str, Any]], column: str, scale_max: int, weight_column: str | None = None
) -> dict[str, Any]:
    """Share choosing the top two points of a bounded scale."""
    values, weights = _values_weights(records, column, weight_column)
    total = sum(weights)
    if total == 0:
        return {"top2box_pct": None, "n": 0}
    top = sum(w for v, w in zip(values, weights, strict=True) if v >= scale_max - 1) / total
    return {"top2box_pct": round(100 * top, 1), "scale_max": scale_max, "n": len(values)}


def mean_ci(
    records: list[dict[str, Any]], column: str, weight_column: str | None = None
) -> dict[str, Any]:
    """Weighted mean with a 95% CI on the effective base (Kish)."""
    values, weights = _values_weights(records, column, weight_column)
    total = sum(weights)
    if total == 0:
        return {"mean": None, "n": 0}
    mean = sum(v * w for v, w in zip(values, weights, strict=True)) / total
    variance = sum(w * (v - mean) ** 2 for v, w in zip(values, weights, strict=True)) / total
    sum_sq = sum(w * w for w in weights)
    effective_n = (total * total / sum_sq) if sum_sq > 0 else 0.0
    stderr = math.sqrt(variance / effective_n) if effective_n > 1 else 0.0
    return {
        "mean": round(mean, 3),
        "ci_low": round(mean - Z_95 * stderr, 3),
        "ci_high": round(mean + Z_95 * stderr, 3),
        "effective_n": round(effective_n, 1),
        "n": len(values),
    }


@register
class SurveyMetrics(Component):
    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="analyzer.survey_metrics",
        name="Survey metrics",
        summary="NPS, top-2-box, or weighted mean ± 95% CI for a numeric survey item.",
        params_schema={
            "type": "object",
            "properties": {
                "column": {"type": "string"},
                "metric": {"type": "string", "enum": ["nps", "top2box", "mean"], "default": "mean"},
                "scale_max": {"type": "integer", "default": 5},
                "weight_column": {"type": "string"},
            },
            "required": ["column"],
        },
        inputs=[Port(name="dataset", dtype="records")],
        outputs=[Port(name="result", dtype="metrics")],
        tags=["tabulation", "metrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        records = as_records(ctx.inputs.get("dataset"))
        column = str(ctx.params["column"])
        metric = str(ctx.params.get("metric") or "mean")
        weight_column = ctx.params.get("weight_column") or None
        if metric == "nps":
            result = nps(records, column, weight_column)
        elif metric == "top2box":
            result = top2box(records, column, int(ctx.params.get("scale_max") or 5), weight_column)
        else:
            result = mean_ci(records, column, weight_column)
        for key, value in result.items():
            if isinstance(value, (int, float)):
                ctx.emit(f"{metric}_{key}", value, kind="metric", component=self.spec.id)
        return {"metric": metric, "column": column, **result}


__all__ = ["nps", "top2box", "mean_ci", "SurveyMetrics"]
