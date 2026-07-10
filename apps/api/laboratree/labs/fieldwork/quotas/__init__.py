"""Quota matching (pure). A quota cell is a set of {qid, value} conditions ALL of which must

match a response's answers. The atomic increment (fill guard) lives in the API/DB layer; this
module only decides *which* cell a completed response belongs to.
"""

from __future__ import annotations

from typing import Any


def response_matches(conditions: list[dict[str, Any]], answers: dict[str, Any]) -> bool:
    """True if every {qid, value} condition matches the answers (multi answers match on membership)."""
    for cond in conditions or []:
        qid = str(cond.get("qid", ""))
        expected = cond.get("value")
        actual = answers.get(qid)
        if isinstance(actual, list):
            if expected not in actual:
                return False
        elif actual != expected:
            return False
    return True


def matching_quota(
    quotas: list[dict[str, Any]], answers: dict[str, Any]
) -> dict[str, Any] | None:
    """First quota whose conditions match, or ``None`` if the response fits no defined cell."""
    for quota in quotas or []:
        if response_matches(quota.get("conditions", []), answers):
            return quota
    return None


__all__ = ["response_matches", "matching_quota"]
