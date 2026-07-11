"""Tabulation Lab — survey weighting, crosstabs with significance, and survey metrics.

Pure, deterministic statistics (no LLM): raking/post-stratification (``weights``), banner × stub
crosstabs with column-proportion z-tests (``crosstab``), and NPS/top-2-box/mean-CI metrics
(``metrics``). Every number is emitted as Evidence by the registered components.
"""

from __future__ import annotations

from typing import Any


def as_records(dataset: Any) -> list[dict[str, Any]]:
    """Coerce a component's dataset input (DataFrame or list of dicts) to records."""
    if dataset is None:
        return []
    if hasattr(dataset, "to_dict"):  # pandas DataFrame (the runs executor hands us one)
        return list(dataset.to_dict("records"))
    return list(dataset)


__all__ = ["as_records"]
