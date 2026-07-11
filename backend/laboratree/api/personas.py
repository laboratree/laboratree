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
from ..labs.synth.conditioning import condition_traits
from ..labs.synth.engine import get_persona_engine
from ..labs.synth.graph_mirror import mirror_cohort_graph
from ..labs.synth.personas import build_personas
from ..labs.synth.social import build_social_graph, neighbour_opinion, social_context
from ..labs.synth.traits import assign_traits, bio_sketch
from ..labs.synth.twin import aggregate_dry_run
from ..personas.models import Persona, PersonaCohort
from ..projects.models import Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["personas"])


class CohortIn(BaseModel):
    name: str = "Cohort"
    n: int = 25
    margins: dict[str, dict[str, float]] = {}
    # objective conditioning: OFF by default; purpose="rct" FORCES neutral (bias guard)
    objective: str | None = None
    conditioning: str = "neutral"          # "neutral" | "objective"
    purpose: str = "survey"                # "survey" | "rct"


class CohortOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    n: int
    waves: int
    margins: dict[str, Any]
    # honesty labels: conditioning mode + the exact mean trait bias injected
    objective: str | None = None
    conditioning: str = "neutral"
    trait_delta: dict[str, Any] = {}
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
    if body.conditioning not in ("neutral", "objective"):
        raise HTTPException(status_code=422, detail="conditioning must be neutral|objective")
    if body.purpose == "rct" and body.conditioning == "objective":
        raise HTTPException(
            status_code=422,
            detail="objective-conditioned cohorts would bias causal estimates — use a "
                   "neutral cohort for RCT/impact work")
    if body.conditioning == "objective" and not (body.objective or "").strip():
        raise HTTPException(status_code=422, detail="objective conditioning needs an objective")
    skeletons = build_personas(body.n, body.margins)
    for skeleton in skeletons:  # give each a stable handle before wiring the social graph
        skeleton["handle"] = str(skeleton.get("id", ""))
    edges = build_social_graph(skeletons)
    cohort = PersonaCohort(org_id=principal.org_id, project_id=project_id,
                           name=body.name, margins=body.margins, graph=edges,
                           n=len(skeletons), waves=0,
                           objective=body.objective,
                           conditioning=body.conditioning, trait_delta={})
    session.add(cohort)
    await session.flush()  # assign cohort.id
    mean_delta: dict[str, float] = {}
    for skeleton in skeletons:
        traits = assign_traits(skeleton)
        attributes = dict(skeleton.get("attributes") or {})
        if body.conditioning == "objective":
            conditioned = condition_traits(
                {"traits": traits, "bio": bio_sketch(skeleton, traits)}, body.objective or "")
            traits = conditioned.traits
            attributes.update(conditioned.attitudes)
            for trait, shift in conditioned.delta.items():
                mean_delta[trait] = mean_delta.get(trait, 0.0) + shift / len(skeletons)
        session.add(Persona(
            org_id=principal.org_id, cohort_id=cohort.id, handle=skeleton["handle"],
            attributes=attributes, traits=traits,
            bio=bio_sketch(skeleton, traits), memory=[],
        ))
    if body.conditioning == "objective":
        cohort.trait_delta = {t: round(v, 4) for t, v in mean_delta.items()}
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


async def execute_wave(
    session: SessionDep, cohort: PersonaCohort, survey: Survey, *, org_id: uuid.UUID
) -> dict[str, Any]:
    """Run one survey wave over a cohort (shared by the API route and the demo seeder)."""
    structure = survey.structure or {}
    personas = await _cohort_personas(session, cohort.id)
    if not personas:
        raise HTTPException(status_code=409, detail="cohort has no personas")

    wave = cohort.waves + 1
    # each persona's neighbours' LAST-wave answers become social context (diffusion, no intra-wave loop)
    last_answers = {
        p.handle: (p.memory[-1]["answers"] if p.memory else {}) for p in personas
    }
    edges = cohort.graph or []
    persona_dicts = [
        {"handle": p.handle, "bio": p.bio, "attributes": p.attributes, "traits": p.traits,
         "memory": p.memory or [],
         "social_context": social_context(neighbour_opinion(p.handle, edges, last_answers))}
        for p in personas
    ]
    engine = get_persona_engine()

    def _run() -> list[dict[str, Any]]:
        return [
            engine.simulate(structure, pd, social_context=pd["social_context"])
            for pd in persona_dicts
        ]

    with use_llm_context("synth", "persona_wave", project_id=cohort.project_id, org_id=org_id):
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
    # how many answers behavioural theory decided (rather than the LLM guessing)
    report["grounded_questions"] = sorted({q for r in results for q in (r.get("grounded") or [])})
    log.info("cohort %s wave %d run on survey %s", cohort.id, wave, survey.id)
    return report


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
    return await execute_wave(session, cohort, survey, org_id=principal.org_id)
