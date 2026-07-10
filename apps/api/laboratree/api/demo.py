"""Demo-data seeder — populate a project with a realistic, interlinked research scenario.

One call activates EVERY stage of the NGO research flow with a real artifact: brief extraction,
stakeholder map, hypothesis tests (against the actual data), a Cochran sample-size run, a persona
wave, a PUBLISHED survey with synthetic completes (labeled), the analysis runs, a DiD on the pilot
panel, and an Evidence-bound report with a public share link.
"""

from __future__ import annotations

import io
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..agents.run_executor import execute_component
from ..core.deps import Principal, SessionDep, require_role
from ..core.repro import dataframe_hash
from ..core.storage import get_blob_store
from ..deliverables.models import Report
from ..fieldwork.models import ResponseStatus, Survey, SurveyResponse, SurveyStatus
from ..labs.deliverables import validate_blocks
from ..labs.demo import education_records, education_survey_structure, pilot_panel_records
from ..labs.demo.components import NGO_BRIEF
from ..labs.synth.engine import get_persona_engine
from ..labs.synth.grounding import stable_unit
from ..personas.models import Persona, PersonaCohort
from ..projects.models import Dataset, Evidence, Project
from ..tenancy.models import Role
from .personas import execute_wave
from .surveys import PUBLIC_TOKEN_BYTES, _structure_hash

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["demo"])

SCENARIOS = {"ngo_education"}


class SeedIn(BaseModel):
    scenario: str = "ngo_education"
    n_rows: int = 300
    n_personas: int = 20


async def _store_dataset(
    session: SessionDep, principal: Principal, project_id: uuid.UUID,
    name: str, df: pd.DataFrame,
) -> Dataset:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    key = f"demo/{project_id}/{uuid.uuid4()}.csv"
    get_blob_store().put(key, buf.getvalue())
    ds = Dataset(org_id=principal.org_id, project_id=project_id, name=name, storage_key=key,
                 content_hash=dataframe_hash(df), n_rows=int(len(df)), n_cols=int(df.shape[1]))
    session.add(ds)
    await session.flush()
    return ds


@router.post("/projects/{project_id}/demo/seed")
async def seed_demo(
    project_id: uuid.UUID,
    body: SeedIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    if body.scenario not in SCENARIOS:
        raise HTTPException(status_code=422, detail=f"unknown scenario: {body.scenario}")

    records = education_records(n=body.n_rows)
    df = pd.DataFrame(records)
    dataset = await _store_dataset(session, principal, project_id, "Rural education (demo)", df)

    # Evidence-producing analysis runs — real runs, real Evidence in the ledger.
    # Ordered to mirror the NGO flow: intake → stakeholders → hypotheses → design → analysis.
    runs: list[dict[str, Any]] = []
    run_ids: dict[str, str] = {}
    evidence_total = 0
    analyses = [
        ("demo.ngo_brief", {}, "demo"),
        ("demo.stakeholder_map", {}, "demo"),
        ("demo.research_frame", {}, "demo"),
        ("tool.sample_size", {"confidence": 0.95, "margin": 0.05, "population": 5000}, "collection"),
        ("analyzer.eda_profile", {}, "insight"),
        ("analyzer.crosstab", {"banner": "gender", "stub": "dropout"}, "tabulation"),
        ("analyzer.survey_metrics", {"column": "exam_score", "metric": "mean"}, "tabulation"),
    ]
    for component_id, params, lab in analyses:
        try:
            result = await execute_component(
                session, org_id=principal.org_id, project_id=project_id,
                component_id=component_id, params=params, inputs={"dataset": df}, lab=lab,
            )
            runs.append({"component_id": component_id, "run_id": str(result.run.id),
                         "evidence": result.evidence_count})
            run_ids[component_id] = str(result.run.id)
            evidence_total += result.evidence_count
        except Exception as exc:  # a demo seed should never hard-fail on one analysis
            log.warning("demo analysis %s failed: %s", component_id, exc)
            runs.append({"component_id": component_id, "error": str(exc)[:200]})

    # longitudinal pilot panel so impact evaluation (DiD) runs on real before/after data
    pilot_rows = pilot_panel_records()
    pilot_df = pd.DataFrame(pilot_rows)
    pilot_dataset = await _store_dataset(
        session, principal, project_id, "Bicycle pilot panel (demo)", pilot_df)
    try:
        did = await execute_component(
            session, org_id=principal.org_id, project_id=project_id,
            component_id="model.causal.did",
            params={"outcome": "attendance_rate", "treated_group": "treated",
                    "post_period": "post"},
            inputs={"dataset": pilot_df}, lab="impact",
        )
        runs.append({"component_id": "model.causal.did", "run_id": str(did.run.id),
                     "evidence": did.evidence_count})
        run_ids["model.causal.did"] = str(did.run.id)
        evidence_total += did.evidence_count
    except Exception as exc:
        log.warning("demo DiD failed: %s", exc)
        runs.append({"component_id": "model.causal.did", "error": str(exc)[:200]})

    # the education survey — PUBLISHED with the H1–H3 pre-registration frozen (U6)
    structure = education_survey_structure()
    survey = Survey(
        org_id=principal.org_id, project_id=project_id,
        title="Rural education access (demo)", structure=structure,
        status=SurveyStatus.LIVE,
        public_token=secrets.token_urlsafe(PUBLIC_TOKEN_BYTES),
        prereg={
            "frozen_at": datetime.now(UTC).isoformat(),
            "structure_hash": _structure_hash(structure),
            "hypotheses": "H1 financial hardship increases dropout; H2 school distance reduces "
                          "attendance; H3 attendance drives learning outcomes",
            "planned_analyses": ["crosstab dropout x gender", "logistic dropout model",
                                 "DiD on the bicycle pilot"],
        },
    )
    session.add(survey)
    await session.flush()
    completes = _synthetic_completes(survey, principal.org_id, n=60)
    session.add_all(completes)

    # a persona cohort — and its FIRST WAVE actually runs (deterministic fallback without a key)
    cohort = PersonaCohort(org_id=principal.org_id, project_id=project_id,
                           name="Rural households (demo)",
                           margins={"gender": {"m": 0.5, "f": 0.5}}, graph=[],
                           n=0, waves=0)
    session.add(cohort)
    await session.flush()
    skeletons = get_persona_engine().build(body.n_personas, {"gender": {"m": 0.5, "f": 0.5}})
    for sk in skeletons:
        session.add(Persona(org_id=principal.org_id, cohort_id=cohort.id, handle=sk["handle"],
                            attributes=sk.get("attributes") or {}, traits=sk.get("traits") or {},
                            bio=sk.get("bio") or "", memory=[]))
    cohort.n = len(skeletons)
    await session.flush()
    wave_report = await execute_wave(session, cohort, survey, org_id=principal.org_id)

    # the Evidence-bound report + public share link (U1: every number binds real Evidence)
    report, share_path = await _build_report(session, principal, project_id, run_ids)

    await session.commit()
    log.info("seeded demo '%s' into project %s: dataset=%s, %d evidence, survey LIVE, "
             "%d completes, wave 1 done, report shared",
             body.scenario, project_id, dataset.id, evidence_total, len(completes))
    return {
        "scenario": body.scenario,
        "dataset_id": str(dataset.id),
        "n_rows": int(len(df)),
        "columns": list(df.columns),
        "rows": records,  # so the Pipeline canvas can run its component nodes on the demo data
        "pilot_dataset_id": str(pilot_dataset.id),
        "pilot_rows": pilot_rows,  # before/after panel for the DiD pipeline node
        "runs": runs,
        "evidence_total": evidence_total,
        "survey_id": str(survey.id),
        "cohort_id": str(cohort.id),
        "personas": len(skeletons),
        # one real artifact per NGO flow stage — every phase is genuinely active
        "stages": {
            "intake": {"run_id": run_ids.get("demo.ngo_brief"), "brief": NGO_BRIEF},
            "stakeholders": {"run_id": run_ids.get("demo.stakeholder_map")},
            "background": {"run_id": run_ids.get("demo.research_frame")},
            "questions": {"run_id": run_ids.get("demo.research_frame")},
            "hypotheses": {"run_id": run_ids.get("demo.research_frame"),
                           "prereg_frozen": True},
            "design": {"run_id": run_ids.get("tool.sample_size")},
            "personas": {"cohort_id": str(cohort.id), "wave": wave_report.get("wave"),
                         "completion_rate": wave_report.get("completion_rate")},
            "questionnaire": {"survey_id": str(survey.id), "status": "live"},
            "field": {"public_url": f"/s/{survey.public_token}",
                      "completes": len(completes), "synthetic": True},
            "clean": {"note": "runs on the canvas"},
            "eda": {"run_id": run_ids.get("analyzer.eda_profile")},
            "crosstab": {"run_id": run_ids.get("analyzer.crosstab")},
            "model": {"note": "runs on the canvas"},
            "prioritize": {"note": "runs on the canvas"},
            "intervention": {"note": "human step"},
            "pilot": {"dataset_id": str(pilot_dataset.id)},
            "impact": {"run_id": run_ids.get("model.causal.did")},
            "recommend": {"report_id": str(report.id)},
            "monitor": {"share_path": share_path},
        },
    }


def _synthetic_completes(survey: Survey, org_id: uuid.UUID, *, n: int = 60) -> list[SurveyResponse]:
    """Realistic completed responses (labeled synthetic) honoring the survey's skip logic."""
    barriers = ["distance", "distance", "cost", "cost", "safety", "work", "none"]
    now = datetime.now(UTC)
    rows: list[SurveyResponse] = []
    for i in range(n):
        seed = f"resp{i}"
        attends = stable_unit(f"{seed}|attends") < 0.7
        answers: dict[str, Any] = {"attends_regularly": "yes" if attends else "no"}
        if not attends:  # skip logic jumps straight to the bicycle question for regulars
            answers["main_barrier"] = barriers[int(stable_unit(f"{seed}|barrier") * len(barriers))]
            answers["safety_concern"] = 1 + int(stable_unit(f"{seed}|safety") * 5)
        answers["would_use_bicycle"] = "yes" if stable_unit(f"{seed}|bike") < 0.8 else "no"
        speeder = i < 3  # a few flagged rows so the quality engine has something to show
        duration = 25.0 if speeder else 300.0 + stable_unit(f"{seed}|dur") * 600
        rows.append(SurveyResponse(
            org_id=org_id, survey_id=survey.id, instrument_version=1,
            resume_key=secrets.token_urlsafe(24), status=ResponseStatus.COMPLETE,
            answers=answers, fingerprint={}, flags=(["speeder"] if speeder else []),
            is_synthetic=True,
            started_at=now - timedelta(hours=2, seconds=duration),
            completed_at=now - timedelta(hours=2), duration_seconds=duration,
        ))
    return rows


async def _build_report(
    session: SessionDep, principal: Principal, project_id: uuid.UUID, run_ids: dict[str, str]
) -> tuple[Report, str | None]:
    """Compose the recommendations report from real Evidence and mint its public share link."""
    wanted_runs = [uuid.UUID(r) for r in
                   (run_ids.get("model.causal.did"), run_ids.get("demo.research_frame"))
                   if r]
    evidence = (await session.execute(
        select(Evidence).where(Evidence.run_id.in_(wanted_runs))
    )).scalars().all() if wanted_runs else []
    by_label = {e.label: e for e in evidence}

    blocks: list[dict[str, Any]] = [
        {"type": "heading", "text": "Recommendations — Bright Future Foundation"},
        {"type": "text",
         "text": "Distance, cost, and safety drive dropout. The bicycle pilot measurably raised "
                 "attendance in treatment villages; we recommend expanding bicycles, then "
                 "scholarships, then libraries."},
    ]
    for label, caption in (("did_effect", "Bicycle pilot effect on attendance (DiD)"),
                           ("H1_supported", "H1: financial hardship increases dropout"),
                           ("H2_supported", "H2: school distance reduces attendance")):
        if label in by_label:
            blocks.append({"type": "stat", "evidence_id": str(by_label[label].id),
                           "caption": caption})
    blocks.append({"type": "methodology",
                   "text": "n = 300 students + 60 field completes (synthetic, labeled); pilot "
                           "panel 200 x 2 periods; pre-registered H1–H3; DiD assumes parallel "
                           "trends."})

    all_ids = {str(e.id) for e in evidence}
    errors = validate_blocks(blocks, all_ids)
    if errors:  # never ship a demo report that violates the Evidence contract
        log.warning("demo report blocks rejected: %s", errors)
        blocks = [b for b in blocks if b.get("type") not in {"stat"}]

    report = Report(org_id=principal.org_id, project_id=project_id,
                    title="NGO education study — recommendations (demo)", blocks=blocks,
                    share_token=secrets.token_urlsafe(24))
    session.add(report)
    await session.flush()
    return report, f"/r/{report.share_token}"
