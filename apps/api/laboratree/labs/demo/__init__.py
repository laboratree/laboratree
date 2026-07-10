"""Realistic demo data for end-to-end testing of the research pipeline.

The NGO education scenario (Bright Future Foundation): rural students where dropout rises with
distance to school, falls with household income, and is worse for girls far from school — real,
interpretable correlations so every downstream Lab (EDA, crosstab, model, report) has something
true to find. Deterministic given a seed so tests are stable.
"""

from __future__ import annotations

import logging
import random
from typing import Any

log = logging.getLogger(__name__)

VILLAGES = [f"Village-{i}" for i in range(1, 11)]
INCOME_BANDS = ("low", "mid", "high")


def education_records(n: int = 300, seed: int = 1729) -> list[dict[str, Any]]:
    """Generate ``n`` synthetic rural-student records with realistic dropout drivers."""
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for i in range(n):
        village = rng.choice(VILLAGES)
        gender = rng.choice(["m", "f"])
        distance_km = round(rng.uniform(0.5, 8.0), 1)
        income = rng.choices(INCOME_BANDS, weights=[0.5, 0.35, 0.15])[0]
        income_score = {"low": 0.0, "mid": 0.5, "high": 1.0}[income]

        # attendance falls with distance, rises with income; girls penalised more by distance
        gender_penalty = 0.06 if gender == "f" else 0.0
        attendance = (
            0.95 - 0.05 * distance_km - gender_penalty * distance_km
            + 0.10 * income_score + rng.gauss(0, 0.05)
        )
        attendance = max(0.2, min(1.0, attendance))
        exam_score = max(0, min(100, 40 + 45 * attendance + 8 * income_score + rng.gauss(0, 6)))

        # dropout probability rises as attendance/income fall and distance grows
        dropout_p = 0.55 - 0.5 * attendance - 0.15 * income_score + 0.03 * distance_km
        dropout = "yes" if rng.random() < max(0.02, min(0.9, dropout_p)) else "no"

        rows.append({
            "student_id": f"S{i + 1:04d}",
            "village": village,
            "gender": gender,
            "age": rng.randint(6, 16),
            "distance_km": distance_km,
            "income_band": income,
            "attendance_rate": round(attendance, 3),
            "exam_score": round(exam_score, 1),
            "dropout": dropout,
        })
    log.info("generated %d demo education records (seed=%d)", n, seed)
    return rows


def education_survey_structure() -> dict[str, Any]:
    """A KAP-style education survey matching the demo dataset's themes."""
    return {
        "sections": [{"id": "s1", "title": "Access & barriers", "questions": [
            {"id": "attends_regularly", "type": "single", "text": "Does the child attend regularly?",
             "required": True, "options": ["yes", "no"]},
            {"id": "main_barrier", "type": "single", "text": "Biggest barrier to attendance?",
             "required": True, "options": ["distance", "cost", "safety", "work", "none"]},
            {"id": "safety_concern", "type": "scale", "text": "Safety concern travelling to school (1-5)?",
             "required": True, "scale": {"min": 1, "max": 5}},
            {"id": "would_use_bicycle", "type": "single", "text": "Would a free bicycle help?",
             "required": False, "options": ["yes", "no"]},
        ]}],
        "logic": [
            {"if": {"qid": "attends_regularly", "op": "eq", "value": "yes"},
             "then": {"action": "skip_to", "target": "would_use_bicycle"}},
        ],
    }


__all__ = ["education_records", "education_survey_structure", "VILLAGES", "INCOME_BANDS"]
