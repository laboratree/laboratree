"""NGO policy-research flow — one sub-agent (phase executor) per pipeline stage.

Each executor is a self-contained unit with the FlowContext→PhaseResult contract; the
orchestrator threads shared artifacts (dataset, survey, cohort, run ids) through ctx.state.
Executors are order-tolerant: whatever they depend on they ensure exists (`_ensure_*`), so a
user-reordered flow still runs. LLM-reasoning agents can replace any of these later without
touching the orchestrator.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from ....fieldwork.models import Survey, SurveyStatus
from ....labs.demo import education_records, education_survey_structure, pilot_panel_records
from ....labs.synth.engine import get_persona_engine
from ....labs.synth.social import build_social_graph
from ....personas.models import Persona, PersonaCohort
from ...run_executor import execute_component
from .. import FlowContext, PhaseResult, open_gate, phase
from ..brain import agentic_phase

log = logging.getLogger(__name__)

FLOW_KEY = "ngo-policy"
N_PERSONAS = 12
N_COMPLETES = 60


# ----------------------------- shared ensure-helpers -----------------------------

async def _ensure_dataset(ctx: FlowContext) -> pd.DataFrame:
    if "df" not in ctx.state:
        from ....api.demo import _store_dataset  # noqa: PLC0415 — avoids an import cycle at module load

        df = pd.DataFrame(education_records())
        dataset = await _store_dataset(ctx.session, ctx.org_id, ctx.project_id,
                                       "Rural education (demo)", df)
        ctx.state["df"] = df
        ctx.state["dataset_id"] = str(dataset.id)
    return ctx.state["df"]


async def _ensure_survey(ctx: FlowContext) -> Survey:
    if "survey" not in ctx.state and ctx.state.get("survey_id"):
        # supervised runs rehydrate across checkpoints — reload rather than recreate
        existing = await ctx.session.get(Survey, uuid.UUID(str(ctx.state["survey_id"])))
        if existing is not None:
            ctx.state["survey"] = existing
    if "survey" not in ctx.state:
        from ....api.surveys import PUBLIC_TOKEN_BYTES, _structure_hash  # noqa: PLC0415

        structure = education_survey_structure()
        survey = Survey(
            org_id=ctx.org_id, project_id=ctx.project_id,
            title="Rural education access (demo)", structure=structure,
            status=SurveyStatus.LIVE,
            public_token=secrets.token_urlsafe(PUBLIC_TOKEN_BYTES),
            prereg={
                "frozen_at": datetime.now(UTC).isoformat(),
                "structure_hash": _structure_hash(structure),
                "hypotheses": "H1 financial hardship increases dropout; H2 school distance "
                              "reduces attendance; H3 attendance drives learning outcomes",
                "planned_analyses": ["crosstab dropout x gender", "logistic dropout model",
                                     "DiD on the bicycle pilot"],
            },
        )
        ctx.session.add(survey)
        await ctx.session.flush()
        ctx.state["survey"] = survey
    ctx.state["survey_id"] = str(ctx.state["survey"].id)
    return ctx.state["survey"]


async def _component_phase(
    ctx: FlowContext, stage_id: str, component_id: str, params: dict[str, Any],
    lab: str, summary: str, *, dataset: pd.DataFrame | None = None,
) -> PhaseResult:
    df = dataset if dataset is not None else await _ensure_dataset(ctx)
    result = await execute_component(
        ctx.session, org_id=ctx.org_id, project_id=ctx.project_id,
        component_id=component_id, params=params, inputs={"dataset": df}, lab=lab,
    )
    ctx.state.setdefault("run_ids", {})[component_id] = str(result.run.id)
    return PhaseResult(stage_id=stage_id, status="succeeded", summary=summary,
                       run_id=str(result.run.id), evidence=result.evidence_count,
                       artifacts={"component_id": component_id,
                                  "io": (result.run.repro_manifest or {}).get("io", {})})


# ----------------------------- understand -----------------------------

async def _intake_deterministic(ctx: FlowContext) -> PhaseResult:
    return await _component_phase(ctx, "intake", "demo.ngo_brief", {}, "demo",
                                  "brief parsed: mission, budget, timeline, target extracted")


@phase(FLOW_KEY, "intake", lab="signal")
async def intake(ctx: FlowContext) -> PhaseResult:
    await _ensure_dataset(ctx)  # so the agent has real material to reason over
    return await agentic_phase(
        ctx, "intake",
        "Extract the program's requirements from the context: mission, primary goal, budget, "
        "timeline, target population, and key risks the research must address.",
        _intake_deterministic)


@phase(FLOW_KEY, "stakeholders", lab="ideation")
async def stakeholders(ctx: FlowContext) -> PhaseResult:
    return await _component_phase(ctx, "stakeholders", "demo.stakeholder_map", {}, "demo",
                                  "stakeholder influence chain mapped")


async def _research_frame(ctx: FlowContext, stage_id: str, summary: str) -> PhaseResult:
    cached = ctx.state.get("research_frame")
    if cached:  # background/questions/hypotheses share one Evidence-locked analysis
        return PhaseResult(stage_id=stage_id, status="succeeded", summary=summary,
                           run_id=cached["run_id"], evidence=0,
                           artifacts={"shared_with": "research_frame"})
    result = await _component_phase(ctx, stage_id, "demo.research_frame", {}, "demo", summary)
    ctx.state["research_frame"] = {"run_id": result.run_id}
    return result


@phase(FLOW_KEY, "background", lab="ideation")
async def background(ctx: FlowContext) -> PhaseResult:
    return await _research_frame(ctx, "background", "dropout drivers framed from the data")


@phase(FLOW_KEY, "questions", lab="ideation")
async def questions(ctx: FlowContext) -> PhaseResult:
    return await _research_frame(ctx, "questions", "research questions defined")


async def _hypotheses_deterministic(ctx: FlowContext) -> PhaseResult:
    return await _research_frame(ctx, "hypotheses", "H1-H3 stated and tested against the data")


@phase(FLOW_KEY, "hypotheses", lab="ideation")
async def hypotheses(ctx: FlowContext) -> PhaseResult:
    await _ensure_dataset(ctx)
    result = await agentic_phase(
        ctx, "hypotheses",
        "Propose 3-5 falsifiable hypotheses about what drives school dropout in this data, each "
        "grounded in a specific pattern visible in the context (name the columns).",
        _hypotheses_deterministic)
    if result.artifacts.get("agent"):
        # theory the agent proposed still gets TESTED against the data (never opinion-only)
        tested = await _research_frame(ctx, "hypotheses",
                                       "agent hypotheses tested against the data")
        result.evidence += tested.evidence
        result.artifacts["tested_run_id"] = tested.run_id
    return result


# ----------------------------- design + personas + field -----------------------------

@phase(FLOW_KEY, "design", lab="collection")
async def design(ctx: FlowContext) -> PhaseResult:
    return await _component_phase(
        ctx, "design", "tool.sample_size",
        {"confidence": 0.95, "margin": 0.05, "population": 5000}, "collection",
        "Cochran sample size computed for the target population")


@phase(FLOW_KEY, "personas", lab="personas")
async def personas(ctx: FlowContext) -> PhaseResult:
    from ....api.personas import execute_wave  # noqa: PLC0415

    survey = await _ensure_survey(ctx)
    engine = get_persona_engine()
    skeletons = engine.build(N_PERSONAS, {"gender": {"m": 0.5, "f": 0.5}})
    cohort = PersonaCohort(org_id=ctx.org_id, project_id=ctx.project_id,
                           name="Rural households (demo)",
                           margins={"gender": {"m": 0.5, "f": 0.5}},
                           graph=build_social_graph(skeletons), n=len(skeletons), waves=0)
    ctx.session.add(cohort)
    await ctx.session.flush()
    for sk in skeletons:
        ctx.session.add(Persona(org_id=ctx.org_id, cohort_id=cohort.id, handle=sk["handle"],
                                attributes=sk.get("attributes") or {},
                                traits=sk.get("traits") or {},
                                bio=sk.get("bio") or "", memory=[]))
    await ctx.session.flush()
    wave = await execute_wave(ctx.session, cohort, survey, org_id=ctx.org_id)
    ctx.state["cohort_id"] = str(cohort.id)
    return PhaseResult(stage_id="personas", status="succeeded",
                       summary=f"{len(skeletons)} personas simulated wave 1 "
                               f"(completion {wave.get('completion_rate')})",
                       artifacts={"cohort_id": str(cohort.id), "wave": wave.get("wave")})


@phase(FLOW_KEY, "questionnaire", lab="field")
async def questionnaire(ctx: FlowContext) -> PhaseResult:
    survey = await _ensure_survey(ctx)
    return PhaseResult(stage_id="questionnaire", status="succeeded",
                       summary="KAP survey built, validated, and published (prereg frozen)",
                       artifacts={"survey_id": str(survey.id),
                                  "public_url": f"/s/{survey.public_token}"})


@phase(FLOW_KEY, "field", lab="field")
async def field(ctx: FlowContext) -> PhaseResult:
    from ....api.demo import _synthetic_completes  # noqa: PLC0415

    survey = await _ensure_survey(ctx)
    completes = _synthetic_completes(survey, ctx.org_id, n=N_COMPLETES)
    ctx.session.add_all(completes)
    await ctx.session.flush()
    return PhaseResult(stage_id="field", status="succeeded",
                       summary=f"{len(completes)} completes collected (synthetic, labeled; "
                               "3 speeder-flagged by the quality engine)",
                       artifacts={"survey_id": str(survey.id), "completes": len(completes)})


# ----------------------------- analyze -----------------------------

@phase(FLOW_KEY, "clean", lab="data")
async def clean(ctx: FlowContext) -> PhaseResult:
    return await _component_phase(ctx, "clean", "transform.mean_impute", {}, "data",
                                  "missing values imputed")


@phase(FLOW_KEY, "eda", lab="insight")
async def eda(ctx: FlowContext) -> PhaseResult:
    return await _component_phase(ctx, "eda", "analyzer.eda_profile", {}, "insight",
                                  "distributions, missingness, correlations profiled")


@phase(FLOW_KEY, "crosstab", lab="tabulation")
async def crosstab(ctx: FlowContext) -> PhaseResult:
    return await _component_phase(ctx, "crosstab", "analyzer.crosstab",
                                  {"banner": "gender", "stub": "dropout"}, "tabulation",
                                  "dropout x gender crosstab with significance letters")


@phase(FLOW_KEY, "model", lab="modeling")
async def model(ctx: FlowContext) -> PhaseResult:
    return await _component_phase(ctx, "model", "model.ml.logistic_regression",
                                  {"target": "dropout"}, "modeling",
                                  "dropout model fitted (distance/income/attendance)")


# ----------------------------- decide -----------------------------

@phase(FLOW_KEY, "prioritize", lab="decision")
async def prioritize(ctx: FlowContext) -> PhaseResult:
    options = [
        {"label": "Free bicycles (transport)", "value": 0.75, "probability": 0.85},
        {"label": "Scholarships (cost)", "value": 0.65, "probability": 0.70},
        {"label": "Libraries", "value": 0.40, "probability": 0.90},
    ]
    return await _component_phase(ctx, "prioritize", "decision.expected_value",
                                  {"options": options}, "decision",
                                  "interventions ranked by expected value")


@phase(FLOW_KEY, "intervention", lab="decision")
async def intervention(ctx: FlowContext) -> PhaseResult:
    # genuinely human: designing the portfolio is judgment — the flow opens a real gate
    return await open_gate(
        ctx, stage_id="intervention",
        title="Approve the intervention portfolio",
        description="The flow ranked bicycles > scholarships > libraries by expected value. "
                    "Design the portfolio (cost/reach/risk) and approve to proceed to the pilot.",
        payload={"ranking": ["Free bicycles", "Scholarships", "Libraries"],
                 "prioritize_run": (ctx.state.get("run_ids") or {}).get("decision.expected_value")},
    )


@phase(FLOW_KEY, "pilot", lab="field")
async def pilot(ctx: FlowContext) -> PhaseResult:
    from ....api.demo import _store_dataset  # noqa: PLC0415

    pilot_df = pd.DataFrame(pilot_panel_records())
    dataset = await _store_dataset(ctx.session, ctx.org_id, ctx.project_id,
                                   "Bicycle pilot panel (demo)", pilot_df)
    ctx.state["pilot_df"] = pilot_df
    return PhaseResult(stage_id="pilot", status="succeeded",
                       summary="bicycle pilot fielded: 200 students x 2 periods collected",
                       artifacts={"dataset_id": str(dataset.id)})


# ----------------------------- impact + deliver -----------------------------

@phase(FLOW_KEY, "impact", lab="impact")
async def impact(ctx: FlowContext) -> PhaseResult:
    if "pilot_df" not in ctx.state:
        await pilot(ctx)  # ensure the panel exists even in a reordered flow
    return await _component_phase(
        ctx, "impact", "model.causal.did",
        {"outcome": "attendance_rate", "treated_group": "treated", "post_period": "post"},
        "impact", "difference-in-differences estimated on the pilot panel",
        dataset=ctx.state["pilot_df"])


@phase(FLOW_KEY, "recommend", lab="deliverables")
async def recommend(ctx: FlowContext) -> PhaseResult:
    from ....api.demo import _build_report  # noqa: PLC0415

    report, share_path = await _build_report(
        ctx.session, ctx.org_id, ctx.project_id, ctx.state.get("run_ids") or {})
    ctx.state["share_path"] = share_path
    return PhaseResult(stage_id="recommend", status="succeeded",
                       summary="Evidence-bound recommendations report composed",
                       artifacts={"report_id": str(report.id)})


@phase(FLOW_KEY, "monitor", lab="deliverables")
async def monitor(ctx: FlowContext) -> PhaseResult:
    share_path = ctx.state.get("share_path")
    if not share_path:
        return PhaseResult(stage_id="monitor", status="skipped",
                           summary="no report to share — run the recommend phase first")
    return PhaseResult(stage_id="monitor", status="succeeded",
                       summary="public monitoring link live",
                       artifacts={"share_path": share_path})
