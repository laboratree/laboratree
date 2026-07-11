"""Registered demo components — the early NGO research phases as real, Evidence-locked runs.

These make the intake/stakeholder/hypothesis stages of the demo pipeline *actually execute*:
- ``demo.ngo_brief``: requirement extraction from the program brief (mission, budget, timeline).
- ``demo.stakeholder_map``: the stakeholder influence chain as a graph artifact.
- ``demo.research_frame``: research questions + hypotheses H1–H3 **tested against the dataset**
  (dropout×income, distance×attendance, attendance×scores) — real statistics, not pre-authored
  verdicts.

All are tagged ``demo`` so they are honestly identifiable in the registry.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

NGO_BRIEF = {
    "client": "Bright Future Foundation",
    "mission": "Improve education outcomes for rural students in India",
    "budget_inr_crore": 5,
    "timeline_years": 2,
    "target_villages": 10,
    "geography": "West Bengal",
    "primary_goal": "Reduce dropout",
}

STAKEHOLDER_CHAIN = [
    "Students", "Parents", "Teachers", "Schools", "Village Leaders", "Government", "NGOs",
]

RESEARCH_QUESTIONS = [
    "Why are students absent?",
    "What causes dropout?",
    "Which intervention has the highest impact?",
]


@register
class NgoBrief(Component):
    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="demo.ngo_brief",
        name="NGO brief extraction (demo)",
        summary="Requirement extraction from the demo program brief: mission, budget, timeline, "
        "target — each an Evidence record.",
        params_schema={"type": "object", "properties": {}},
        inputs=[],
        outputs=[Port(name="brief", dtype="metrics")],
        tags=["demo", "intake"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        for label in ("mission", "budget_inr_crore", "timeline_years",
                      "target_villages", "primary_goal"):
            ctx.emit(label, NGO_BRIEF[label], kind="fact", component=self.spec.id)
        return {"brief": NGO_BRIEF}


@register
class StakeholderMap(Component):
    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="demo.stakeholder_map",
        name="Stakeholder mapping (demo)",
        summary="The education program's stakeholder influence chain as a graph artifact.",
        params_schema={"type": "object", "properties": {}},
        inputs=[],
        outputs=[Port(name="graph", dtype="metrics")],
        tags=["demo", "stakeholders"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        edges = [{"from": a, "to": b, "relation": "influences"}
                 for a, b in zip(STAKEHOLDER_CHAIN, STAKEHOLDER_CHAIN[1:], strict=False)]
        ctx.emit("stakeholder_count", len(STAKEHOLDER_CHAIN), kind="metric", component=self.spec.id)
        ctx.emit("stakeholder_chain", " -> ".join(STAKEHOLDER_CHAIN), kind="fact",
                 component=self.spec.id)
        return {"graph": {"nodes": STAKEHOLDER_CHAIN, "edges": edges}}


def _records(dataset: Any) -> list[dict[str, Any]]:
    if hasattr(dataset, "to_dict"):
        return list(dataset.to_dict("records"))
    return list(dataset or [])


@register
class ResearchFrame(Component):
    spec = ComponentSpec(
        kind=ComponentKind.ANALYZER,
        id="demo.research_frame",
        name="Research questions + hypothesis tests (demo)",
        summary="Frames the research questions and tests H1–H3 against the actual dataset: "
        "H1 low income raises dropout; H2 distance lowers attendance; H3 attendance drives scores.",
        params_schema={"type": "object", "properties": {}},
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="hypotheses", dtype="metrics")],
        tags=["demo", "hypotheses"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        rows = _records(ctx.inputs["dataset"])

        def dropout_rate(rs: list[dict[str, Any]]) -> float:
            return mean(1.0 if r.get("dropout") == "yes" else 0.0 for r in rs) if rs else 0.0

        low = [r for r in rows if r.get("income_band") == "low"]
        high = [r for r in rows if r.get("income_band") == "high"]
        near = [r for r in rows if float(r.get("distance_km", 0)) <= 2]
        far = [r for r in rows if float(r.get("distance_km", 0)) >= 5]
        hi_att = [r for r in rows if float(r.get("attendance_rate", 0)) >= 0.8]
        lo_att = [r for r in rows if float(r.get("attendance_rate", 0)) < 0.6]

        hypotheses = [
            {"id": "H1", "text": "Financial hardship increases dropout",
             "stat": {"dropout_low_income": round(dropout_rate(low), 3),
                      "dropout_high_income": round(dropout_rate(high), 3)},
             "supported": dropout_rate(low) > dropout_rate(high)},
            {"id": "H2", "text": "School distance reduces attendance",
             "stat": {"attendance_near": round(mean(r["attendance_rate"] for r in near), 3) if near else None,
                      "attendance_far": round(mean(r["attendance_rate"] for r in far), 3) if far else None},
             "supported": bool(near and far)
             and mean(r["attendance_rate"] for r in near) > mean(r["attendance_rate"] for r in far)},
            {"id": "H3", "text": "Attendance drives learning outcomes",
             "stat": {"score_high_attendance": round(mean(r["exam_score"] for r in hi_att), 1) if hi_att else None,
                      "score_low_attendance": round(mean(r["exam_score"] for r in lo_att), 1) if lo_att else None},
             "supported": bool(hi_att and lo_att)
             and mean(r["exam_score"] for r in hi_att) > mean(r["exam_score"] for r in lo_att)},
        ]
        for h in hypotheses:
            ctx.emit(f"{h['id']}_supported", h["supported"], kind="finding", component=self.spec.id)
        ctx.emit("research_questions", "; ".join(RESEARCH_QUESTIONS), kind="fact",
                 component=self.spec.id)
        return {"hypotheses": hypotheses, "research_questions": RESEARCH_QUESTIONS,
                "n_obs": len(rows)}
