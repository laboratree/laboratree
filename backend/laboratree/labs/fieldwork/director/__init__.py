"""Field Director v1 (U2) — detection only (pure, deterministic).

Watches a live survey's monitor snapshot and surfaces **findings + proposed actions** for a human
to approve. No LLM here: every finding is a computable signal from the monitor payload (drop-off,
quota imbalance, quality-flag rate, screen-out rate). LLM-worded proposals can layer on later; the
detection and the structured proposal are deterministic and testable.
"""

from __future__ import annotations

import logging
from statistics import median
from typing import Any

log = logging.getLogger(__name__)

# Thresholds (named, not magic).
DROPOFF_MIN_REACHED = 5          # ignore questions too few respondents have reached
DROPOFF_ABS_THRESHOLD = 0.15     # >15% of those who reached it leave without answering
DROPOFF_REL_MULTIPLE = 2.0       # ...or 2x the median drop across questions
FLAG_RATE_MIN_N = 10
FLAG_RATE_THRESHOLD = 0.20       # >20% of finished responses flagged
SCREENOUT_MIN_STARTS = 10
SCREENOUT_THRESHOLD = 0.50       # >50% of starts screened out -> screener too strict
QUOTA_LEADER_FILL = 0.70         # a cell is "ahead" once 70% full
QUOTA_LAG_RATIO = 0.5            # a lagging cell is < half the leader's fill fraction

SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"


def _finding(kind: str, severity: str, message: str, proposal: str, **detail: Any) -> dict[str, Any]:
    return {"kind": kind, "severity": severity, "message": message, "proposal": proposal,
            "detail": detail}


def _dropoff_findings(dropoff: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rates: dict[str, float] = {}
    for row in dropoff:
        reached = int(row.get("reached", 0) or 0)
        if reached < DROPOFF_MIN_REACHED:
            continue
        answered = int(row.get("answered", 0) or 0)
        rates[str(row.get("qid"))] = 1.0 - (answered / reached)
    if not rates:
        return []
    med = median(rates.values())
    findings = []
    for qid, rate in rates.items():
        if rate >= DROPOFF_ABS_THRESHOLD and rate >= DROPOFF_REL_MULTIPLE * max(med, 1e-9):
            findings.append(
                _finding(
                    "dropoff_spike",
                    SEVERITY_HIGH if rate >= 0.3 else SEVERITY_MEDIUM,
                    f"Question {qid} is losing {round(rate * 100)}% of respondents who reach it.",
                    f"Review the wording of {qid} — it may be confusing, sensitive, or too long.",
                    qid=qid,
                    drop_rate=round(rate, 3),
                )
            )
    return findings


def _quota_findings(quotas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fills = []
    for q in quotas:
        target = int(q.get("target", 0) or 0)
        if target <= 0:
            continue
        fills.append((q.get("name", "?"), int(q.get("current", 0) or 0) / target))
    if len(fills) < 2:
        return []
    leader_name, leader_fill = max(fills, key=lambda kv: kv[1])
    if leader_fill < QUOTA_LEADER_FILL:
        return []  # too early to call anything a laggard
    findings = []
    for name, fill in fills:
        if fill < QUOTA_LAG_RATIO * leader_fill:
            findings.append(
                _finding(
                    "quota_lag",
                    SEVERITY_MEDIUM,
                    f"Quota '{name}' is lagging ({round(fill * 100)}% full) while "
                    f"'{leader_name}' is {round(leader_fill * 100)}% full.",
                    f"Send a targeted reminder or boost recruitment for the '{name}' cell.",
                    quota=name,
                    fill=round(fill, 3),
                )
            )
    return findings


def _quality_findings(monitor: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    completes = int(monitor.get("completes", 0) or 0)
    flagged = int(monitor.get("flagged", 0) or 0)
    finished = completes + flagged
    if finished >= FLAG_RATE_MIN_N and flagged / finished > FLAG_RATE_THRESHOLD:
        findings.append(
            _finding(
                "quality",
                SEVERITY_HIGH,
                f"{round(flagged / finished * 100)}% of finished responses are quality-flagged.",
                "Inspect flagged responses; consider adding an attention check or tightening "
                "fraud controls.",
                flag_rate=round(flagged / finished, 3),
            )
        )

    screened = int(monitor.get("screened_out", 0) or 0)
    starts = finished + int(monitor.get("in_progress", 0) or 0) + screened + int(
        monitor.get("quota_full", 0) or 0
    )
    if starts >= SCREENOUT_MIN_STARTS and screened / starts > SCREENOUT_THRESHOLD:
        findings.append(
            _finding(
                "screenout",
                SEVERITY_MEDIUM,
                f"{round(screened / starts * 100)}% of starts are screened out.",
                "Your screener may be too strict — widen eligibility or check the screening logic.",
                screenout_rate=round(screened / starts, 3),
            )
        )
    return findings


def analyze_field(monitor: dict[str, Any]) -> list[dict[str, Any]]:
    """Return an ordered list of findings (high severity first) from a monitor snapshot."""
    findings = [
        *_dropoff_findings(monitor.get("dropoff", []) or []),
        *_quota_findings(monitor.get("quotas", []) or []),
        *_quality_findings(monitor),
    ]
    findings.sort(key=lambda f: 0 if f["severity"] == SEVERITY_HIGH else 1)
    log.info("field director produced %d finding(s)", len(findings))
    return findings


__all__ = ["analyze_field"]
