"""Persona Lab API — build persistent persona cohorts and re-survey them across waves.

Cohorts persist stable-trait personas; running a survey against a cohort conditions each persona on
its prior waves (memory) and appends the new answers — so wave 2 stays consistent with wave 1.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..core.deps import Principal, PrincipalDep, SessionDep, require_role
from ..core.llm.context import use_llm_context
from ..fieldwork.models import Survey
from ..labs.synth import llm as synth_llm
from ..labs.synth.graph_mirror import mirror_cohort_graph
from ..labs.synth.personas import build_personas
from ..labs.synth.social import build_social_graph, neighbour_opinion, social_context
from ..labs.synth.traits import assign_traits, bio_sketch
from ..labs.synth.twin import aggregate_dry_run, simulate_persona_wave
from ..personas.models import Persona, PersonaCohort
from ..projects.models import Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["personas"])


class CohortIn(BaseModel):
    name: str = "Cohort"
    n: int = 25
    margins: dict[str, dict[str, float]] = {}


class CohortOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    n: int
    waves: int
    margins: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class PersonaOut(BaseModel):
    id: uuid.UUID
    handle: str
    attributes: dict[str, Any]
    traits: dict[str, float]
    bio: str
    memory_waves: int


class RunWaveIn(BaseModel):
    survey_id: uuid.UUID


async def _require_project(session: SessionDep, principal: Principal, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


async def _require_cohort(session: SessionDep, principal: Principal, cohort_id: uuid.UUID) -> PersonaCohort:
    cohort = await session.get(PersonaCohort, cohort_id)
    if cohort is None or cohort.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="cohort not found")
    return cohort


@router.post("/projects/{project_id}/persona-cohorts", response_model=CohortOut, status_code=201)
async def create_cohort(
    project_id: uuid.UUID,
    body: CohortIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> PersonaCohort:
    """Build + persist a cohort of stable-trait personas from target margins."""
    await _require_project(session, principal, project_id)
    skeletons = build_personas(body.n, body.margins)
    for skeleton in skeletons:  # give each a stable handle before wiring the social graph
        skeleton["handle"] = str(skeleton.get("id", ""))
    edges = build_social_graph(skeletons)
    cohort = PersonaCohort(org_id=principal.org_id, project_id=project_id,
                           name=body.name, margins=body.margins, graph=edges,
                           n=len(skeletons), waves=0)
    session.add(cohort)
    await session.flush()  # assign cohort.id
    for skeleton in skeletons:
        traits = assign_traits(skeleton)
        session.add(Persona(
            org_id=principal.org_id, cohort_id=cohort.id, handle=skeleton["handle"],
            attributes=skeleton.get("attributes") or {}, traits=traits,
            bio=bio_sketch(skeleton, traits), memory=[],
        ))
    await session.commit()
    await session.refresh(cohort)
    await mirror_cohort_graph(cohort.id, principal.org_id, skeletons, edges)  # best-effort
    log.info("cohort %s created: %d personas, %d edges", cohort.id, cohort.n, len(edges))
    return cohort


@router.get("/projects/{project_id}/persona-cohorts", response_model=list[CohortOut])
async def list_cohorts(
    project_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[PersonaCohort]:
    await _require_project(session, principal, project_id)
    rows = (
        await session.execute(
            select(PersonaCohort).where(
                PersonaCohort.org_id == principal.org_id,
                PersonaCohort.project_id == project_id,
            ).order_by(PersonaCohort.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


async def _cohort_personas(session: SessionDep, cohort_id: uuid.UUID) -> list[Persona]:
    return list(
        (
            await session.execute(
                select(Persona).where(Persona.cohort_id == cohort_id).order_by(Persona.handle)
            )
        ).scalars().all()
    )


@router.get("/persona-cohorts/{cohort_id}", response_model=list[PersonaOut])
async def cohort_personas(
    cohort_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[PersonaOut]:
    await _require_cohort(session, principal, cohort_id)
    personas = await _cohort_personas(session, cohort_id)
    return [
        PersonaOut(id=p.id, handle=p.handle, attributes=p.attributes, traits=p.traits,
                   bio=p.bio, memory_waves=len(p.memory or []))
        for p in personas
    ]


@router.get("/persona-cohorts/{cohort_id}/graph")
async def cohort_graph(
    cohort_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """The cohort's social network (nodes + homophily edges) for visualization."""
    cohort = await _require_cohort(session, principal, cohort_id)
    personas = await _cohort_personas(session, cohort_id)
    return {
        "nodes": [{"handle": p.handle, "attributes": p.attributes} for p in personas],
        "edges": cohort.graph or [],
    }


@router.post("/persona-cohorts/{cohort_id}/run")
async def run_wave(
    cohort_id: uuid.UUID,
    body: RunWaveIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Survey the cohort: each persona answers in-character + consistent with prior waves."""
    cohort = await _require_cohort(session, principal, cohort_id)
    survey = await session.get(Survey, body.survey_id)
    if survey is None or survey.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="survey not found")
    structure = survey.structure or {}
    personas = await _cohort_personas(session, cohort_id)
    if not personas:
        raise HTTPException(status_code=409, detail="cohort has no personas")

    wave = cohort.waves + 1
    # each persona's neighbours' LAST-wave answers become social context (diffusion, no intra-wave loop)
    last_answers = {
        p.handle: (p.memory[-1]["answers"] if p.memory else {}) for p in personas
    }
    edges = cohort.graph or []
    persona_dicts = [
        {"handle": p.handle, "bio": p.bio, "attributes": p.attributes, "memory": p.memory or [],
         "social_context": social_context(neighbour_opinion(p.handle, edges, last_answers))}
        for p in personas
    ]

    def _run() -> list[dict[str, Any]]:
        return [
            simulate_persona_wave(structure, pd, synth_llm.default_complete,
                                  social_context=pd["social_context"])
            for pd in persona_dicts
        ]

    with use_llm_context("synth", "persona_wave", project_id=cohort.project_id, org_id=principal.org_id):
        results = await asyncio.to_thread(_run)

    now = datetime.now(UTC).isoformat()
    for persona, result in zip(personas, results, strict=True):
        episode = {"wave": wave, "survey_id": str(survey.id),
                   "answers": result.get("answers") or {}, "ts": now}
        persona.memory = [*(persona.memory or []), episode]  # reassign so JSONB change is tracked
    cohort.waves = wave
    await session.commit()

    report = aggregate_dry_run(structure, results)
    report["wave"] = wave
    log.info("cohort %s wave %d run on survey %s", cohort.id, wave, survey.id)
    return report
