"""Demo-data seeder — populate a project with a realistic, interlinked research scenario.

One call lays down the artifacts the pipeline stages consume: a versioned dataset, Evidence-producing
analysis runs (EDA, crosstab, survey metric), an education survey, and a persona cohort — so the
whole flow can be run end-to-end in a demo without hand-uploading anything.
"""

from __future__ import annotations

import io
import logging
import uuid
from typing import Annotated, Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..agents.run_executor import execute_component
from ..core.deps import Principal, SessionDep, require_role
from ..core.repro import dataframe_hash
from ..core.storage import get_blob_store
from ..fieldwork.models import Survey, SurveyStatus
from ..labs.demo import education_records, education_survey_structure
from ..labs.synth.engine import get_persona_engine
from ..personas.models import Persona, PersonaCohort
from ..projects.models import Dataset, Project
from ..tenancy.models import Role

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

    # Evidence-producing analysis runs — real runs, real Evidence in the ledger
    runs: list[dict[str, Any]] = []
    evidence_total = 0
    analyses = [
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
            evidence_total += result.evidence_count
        except Exception as exc:  # a demo seed should never hard-fail on one analysis
            log.warning("demo analysis %s failed: %s", component_id, exc)
            runs.append({"component_id": component_id, "error": str(exc)[:200]})

    # a matching education survey (draft, ready to publish or run against personas)
    survey = Survey(org_id=principal.org_id, project_id=project_id,
                    title="Rural education access (demo)",
                    structure=education_survey_structure(), status=SurveyStatus.DRAFT)
    session.add(survey)

    # a persona cohort for stress-testing the survey
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

    await session.commit()
    log.info("seeded demo '%s' into project %s: dataset=%s, %d evidence, cohort=%s",
             body.scenario, project_id, dataset.id, evidence_total, cohort.id)
    return {
        "scenario": body.scenario,
        "dataset_id": str(dataset.id),
        "n_rows": int(len(df)),
        "columns": list(df.columns),
        "rows": records,  # so the Pipeline canvas can run its component nodes on the demo data
        "runs": runs,
        "evidence_total": evidence_total,
        "survey_id": str(survey.id),
        "cohort_id": str(cohort.id),
        "personas": len(skeletons),
    }
