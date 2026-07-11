"""Cross-transcript synthesis — deterministic theme×source matrix (+ optional cited narrative)."""

from __future__ import annotations

import logging
from typing import Any

from .codebook import CompleteFn

log = logging.getLogger(__name__)

_NARRATIVE_SYSTEM = (
    "You write a grounded qualitative synthesis from a theme-by-source matrix. State how "
    "widespread each theme is (n of N sources), lead with the strongest patterns, and note "
    "themes that appear in only one source as tentative. Plain language, one tight paragraph "
    "per major theme. Do not invent themes or counts not in the matrix."
)


def theme_matrix(
    codings_by_asset: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Aggregate per-asset code assignments → {codes, sources, cells, saturation} (pure).

    ``cells[code][asset_id]`` = number of coded segments; saturation = per code, how many sources
    it appears in.
    """
    sources = sorted(codings_by_asset.keys())
    cells: dict[str, dict[str, int]] = {}
    for asset_id, assignments in codings_by_asset.items():
        for assignment in assignments or []:
            code = str(assignment.get("code", ""))
            if not code:
                continue
            cells.setdefault(code, {})
            cells[code][asset_id] = cells[code].get(asset_id, 0) + 1

    codes = sorted(cells.keys(), key=lambda c: -sum(cells[c].values()))
    saturation = [
        {"code": code, "sources": len(cells[code]), "of": len(sources),
         "mentions": sum(cells[code].values())}
        for code in codes
    ]
    return {"codes": codes, "sources": sources, "cells": cells, "saturation": saturation}


def narrative(matrix: dict[str, Any], complete_fn: CompleteFn) -> str:
    """LLM narrative over the (already computed) matrix — grounded in its counts only."""
    lines = [
        f"- {row['code']}: in {row['sources']}/{row['of']} sources, {row['mentions']} mentions"
        for row in matrix.get("saturation", [])
    ]
    if not lines:
        return ""
    return complete_fn(_NARRATIVE_SYSTEM, "Theme matrix:\n" + "\n".join(lines)).strip()


__all__ = ["theme_matrix", "narrative"]
