"""Verification — the deterministic numeric spot-check after the critic.

A claim that quotes numbers NONE of which appear in any recorded observation is a fabrication
signal and is dropped (conservative on purpose: partial matches survive, so rounded phrasings
of real observations are not punished). Runs keyless — verification is a law, not a feature.
"""

from __future__ import annotations

import re
from typing import Any

_NUMBER = re.compile(r"-?\d+(?:[,.]\d+)*%?")
# small integers appear in prose ("2 studies", "one of 3") — only distinctive numbers count
_MIN_DISTINCTIVE = 10


def _numbers(text: str) -> set[str]:
    found = set()
    for raw in _NUMBER.findall(text):
        cleaned = raw.rstrip("%").replace(",", "")
        try:
            value = float(cleaned)
        except ValueError:
            continue
        if abs(value) >= _MIN_DISTINCTIVE or "." in cleaned:
            found.add(cleaned.rstrip("0").rstrip(".") if "." in cleaned else cleaned)
    return found


def verify_findings(
    findings: list[dict[str, Any]], scratchpad: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Returns (surviving findings, drop notes). Numberless claims always pass."""
    observed = _numbers(" ".join(
        str(s.get("observation", "")) for s in scratchpad if s.get("kind", "tool") == "tool"))
    survivors: list[dict[str, Any]] = []
    notes: list[str] = []
    for finding in findings:
        claimed = _numbers(str(finding.get("claim", "")))
        if claimed and observed.isdisjoint(claimed):
            notes.append("verification dropped finding whose numbers appear in no "
                         f"observation: {str(finding.get('claim', ''))[:120]}")
            continue
        survivors.append(finding)
    return survivors, notes


__all__ = ["verify_findings"]
