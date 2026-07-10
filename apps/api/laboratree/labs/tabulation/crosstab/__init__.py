"""Banner × stub crosstabs with column-proportion z-tests (letters notation) + chi-square.

The market-research table: rows = stub categories, columns = banner categories, cells = weighted
column %, with superscript letters marking which OTHER banner columns this cell is significantly
higher than (two-proportion z-test on effective bases, 95%). Chi-square is computed on the
weighted counts (a documented approximation; survey-corrected tests come later).
"""

from __future__ import annotations

import logging
import math
import string
from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from .. import as_records

log = logging.getLogger(__name__)

Z_95 = 1.96
MIN_BASE_FOR_TEST = 30  # columns below this base are never tested (standard MR practice)


def _weight(record: dict[str, Any], weight_column: str | None) -> float:
    if not weight_column:
        return 1.0
    value = record.get(weight_column)
    return float(value) if isinstance(value, (int, float)) and value > 0 else 1.0


def _effective_base(weights: list[float]) -> float:
    total = sum(weights)
    sum_sq = sum(w * w for w in weights)
    return (total * total / sum_sq) if sum_sq > 0 else 0.0


def _z_higher(p1: float, n1: float, p2: float, n2: float) -> bool:
    """True if proportion p1 (base n1) is significantly HIGHER than p2 (base n2) at 95%."""
    if n1 < MIN_BASE_FOR_TEST or n2 < MIN_BASE_FOR_TEST or p1 <= p2:
        return False
    pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
    variance = pooled * (1 - pooled) * (1 / n1 + 1 / n2)
    if variance <= 0:
        return False
    return (p1 - p2) / math.sqrt(variance) > Z_95


def crosstab(
    records: list[dict[str, Any]],
    banner: str,
    stub: str,
    weight_column: str | None = None,
) -> dict[str, Any]:
    """Weighted banner × stub table with letters + chi-square. Skips records missing either var."""
    usable = [
        r for r in records
        if r.get(banner) not in (None, "", []) and r.get(stub) not in (None, "", [])
    ]
    banner_cats = sorted({str(r[banner]) for r in usable})
    stub_cats = sorted({str(r[stub]) for r in usable})
    letters = {cat: string.ascii_uppercase[i % 26] for i, cat in enumerate(banner_cats)}

    col_weights: dict[str, list[float]] = {c: [] for c in banner_cats}
    counts: dict[str, dict[str, float]] = {s: {c: 0.0 for c in banner_cats} for s in stub_cats}
    for record in usable:
        weight = _weight(record, weight_column)
        banner_value = str(record[banner])
        col_weights[banner_value].append(weight)
        counts[str(record[stub])][banner_value] += weight

    col_totals = {c: sum(w) for c, w in col_weights.items()}
    col_effective = {c: _effective_base(w) for c, w in col_weights.items()}

    rows = []
    for stub_value in stub_cats:
        cells: dict[str, dict[str, Any]] = {}
        proportions = {
            c: (counts[stub_value][c] / col_totals[c]) if col_totals[c] > 0 else 0.0
            for c in banner_cats
        }
        for cat in banner_cats:
            higher_than = [
                letters[other]
                for other in banner_cats
                if other != cat
                and _z_higher(proportions[cat], col_effective[cat],
                              proportions[other], col_effective[other])
            ]
            cells[cat] = {
                "pct": round(100 * proportions[cat], 1),
                "n": round(counts[stub_value][cat], 1),
                "sig_higher_than": "".join(sorted(higher_than)),
            }
        rows.append({"stub_value": stub_value, "cells": cells})

    chi2, p_value, dof = _chi_square(counts, banner_cats, stub_cats)
    return {
        "banner": banner,
        "stub": stub,
        "weighted": bool(weight_column),
        "columns": [{"category": c, "letter": letters[c],
                     "base": round(col_totals[c], 1),
                     "effective_base": round(col_effective[c], 1)} for c in banner_cats],
        "rows": rows,
        "chi_square": chi2,
        "p_value": p_value,
        "dof": dof,
        "total_n": len(usable),
    }


def _chi_square(
    counts: dict[str, dict[str, float]], banner_cats: list[str], stub_cats: list[str]
) -> tuple[float | None, float | None, int]:
    try:
        from scipy.stats import chi2_contingency
    except ImportError:  # scipy is a core dep, but never hard-fail a table over a test statistic
        return None, None, 0
    table = [[counts[s][c] for c in banner_cats] for s in stub_cats]
    if len(table) < 2 or len(banner_cats) < 2 or any(sum(row) == 0 for row in table):
        return None, None, 0
    try:
        chi2, p, dof, _ = chi2_contingency(table)
        return round(float(chi2), 3), round(float(p), 5), int(dof)
    except ValueError as exc:
        log.info("chi-square skipped: %s", exc)
        return None, None, 0


@register
class Crosstab(Component):
    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="analyzer.crosstab",
        name="Crosstab (banner × stub)",
        summary="Weighted crosstab with column-proportion significance letters and chi-square.",
        params_schema={
            "type": "object",
            "properties": {
                "banner": {"type": "string"},
                "stub": {"type": "string"},
                "weight_column": {"type": "string"},
            },
            "required": ["banner", "stub"],
        },
        inputs=[Port(name="dataset", dtype="records")],
        outputs=[Port(name="result", dtype="table")],
        tags=["tabulation", "crosstab"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        records = as_records(ctx.inputs.get("dataset"))
        table = crosstab(
            records,
            banner=str(ctx.params["banner"]),
            stub=str(ctx.params["stub"]),
            weight_column=ctx.params.get("weight_column") or None,
        )
        ctx.emit("crosstab", {"banner": table["banner"], "stub": table["stub"],
                              "chi_square": table["chi_square"], "p_value": table["p_value"],
                              "total_n": table["total_n"]},
                 kind="table", component=self.spec.id)
        return table


__all__ = ["crosstab", "Crosstab"]
