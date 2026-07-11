"""Qual Studio analysis API — codebooks (HITL-gated), coding, sentiment, quotes, synthesis.

The gate rule: nothing codes against a codebook a human hasn't approved (409 otherwise). Quotes
are LLM-proposed, verbatim-verified, then Evidence-locked through a real component Run.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..agents.run_executor import execute_component
from ..coding.models import Codebook, CodebookStatus
from ..core.deps import Principal, PrincipalDep, SessionDep, require_role
from ..core.llm.context import use_llm_context
from ..labs.qual import llm as qual_llm
from ..labs.qual.codebook import propose_codebook
from ..labs.qual.coding import apply_codebook, segment_sentiment
from ..labs.qual.codings import (
    add_human_assignment,
    get_coding,
    remove_assignment,
    save_coding,
    save_sentiment,
)
from ..labs.qual.quotes import propose_quotes, verbatim_filter
from ..labs.qual.synthesis import theme_matrix
from ..labs.qual.transcripts import get_transcript
from ..media.models import MediaAsset, MediaStatus
from ..projects.models import Project
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["qual"])


class CodebookOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    codes: list[dict[str, Any]]
    status: str
    source_asset_ids: list[str]
    approved_at: datetime | None

    model_config = {"from_attributes": True}


class ProposeIn(BaseModel):
    asset_ids: list[uuid.UUID]
    name: str = "Codebook"


class CodebookEditIn(BaseModel):
    codes: list[dict[str, str]]
    name: str | None = None


class CodeAssetIn(BaseModel):
    codebook_id: uuid.UUID


class OverrideIn(BaseModel):
    segment: int
    code: str
    action: str = "add"  # add | remove


async def _require_project(session: SessionDep, principal: Principal, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="project not found")
    return project


async def _require_asset(session: SessionDep, principal: Principal, asset_id: uuid.UUID) -> MediaAsset:
    asset = await session.get(MediaAsset, asset_id)
    if asset is None or asset.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="media asset not found")
    return asset


async def _require_codebook(session: SessionDep, principal: Principal, codebook_id: uuid.UUID) -> Codebook:
    codebook = await session.get(Codebook, codebook_id)
    if codebook is None or codebook.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="codebook not found")
    return codebook


async def _transcript_or_409(asset: MediaAsset, org_id: uuid.UUID) -> dict[str, Any]:
    if asset.status != MediaStatus.TRANSCRIBED:
        raise HTTPException(status_code=409, detail="asset is not transcribed yet")
    transcript = await get_transcript(asset.id, org_id)
    if not transcript or not transcript.get("segments"):
        raise HTTPException(status_code=409, detail="no transcript available for this asset")
    return transcript


# ----------------------------- codebooks (HITL) -----------------------------

@router.post("/projects/{project_id}/qual/codebooks", response_model=CodebookOut, status_code=201)
async def propose(
    project_id: uuid.UUID,
    body: ProposeIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Codebook:
    await _require_project(session, principal, project_id)
    texts: list[str] = []
    source_ids: list[str] = []
    for asset_id in body.asset_ids:
        asset = await _require_asset(session, principal, asset_id)
        transcript = await _transcript_or_409(asset, principal.org_id)
        texts.append(transcript.get("text", ""))
        source_ids.append(str(asset_id))
    if not texts:
        raise HTTPException(status_code=422, detail="at least one transcribed asset is required")

    with use_llm_context("qual", "codebook", project_id=project_id, org_id=principal.org_id):
        codes = propose_codebook(texts, qual_llm.default_complete)
    if not codes:
        raise HTTPException(status_code=502, detail="codebook proposal returned no usable codes")

    codebook = Codebook(
        org_id=principal.org_id,
        project_id=project_id,
        name=body.name,
        codes=codes,
        status=CodebookStatus.PROPOSED,
        source_asset_ids=source_ids,
    )
    session.add(codebook)
    await session.commit()
    await session.refresh(codebook)
    return codebook


@router.get("/projects/{project_id}/qual/codebooks", response_model=list[CodebookOut])
async def list_codebooks(
    project_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> list[Codebook]:
    await _require_project(session, principal, project_id)
    rows = (
        await session.execute(
            select(Codebook)
            .where(Codebook.org_id == principal.org_id, Codebook.project_id == project_id)
            .order_by(Codebook.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.patch("/qual/codebooks/{codebook_id}", response_model=CodebookOut)
async def edit_codebook(
    codebook_id: uuid.UUID,
    body: CodebookEditIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Codebook:
    codebook = await _require_codebook(session, principal, codebook_id)
    if codebook.status == CodebookStatus.APPROVED:
        raise HTTPException(status_code=409, detail="approved codebooks are immutable")
    cleaned = [
        {"name": str(c.get("name", "")).strip(), "definition": str(c.get("definition", "")).strip()}
        for c in body.codes
        if str(c.get("name", "")).strip()
    ]
    if not cleaned:
        raise HTTPException(status_code=422, detail="a codebook needs at least one code")
    codebook.codes = cleaned
    if body.name:
        codebook.name = body.name
    await session.commit()
    await session.refresh(codebook)
    return codebook


@router.post("/qual/codebooks/{codebook_id}/approve", response_model=CodebookOut)
async def approve_codebook(
    codebook_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Codebook:
    """The human gate: only approved codebooks can code anything."""
    codebook = await _require_codebook(session, principal, codebook_id)
    codebook.status = CodebookStatus.APPROVED
    codebook.approved_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(codebook)
    log.info("codebook %s approved by %s", codebook.id, principal.user.id)
    return codebook


# ----------------------------- coding + sentiment -----------------------------

@router.post("/media/{asset_id}/code")
async def code_asset(
    asset_id: uuid.UUID,
    body: CodeAssetIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    asset = await _require_asset(session, principal, asset_id)
    codebook = await _require_codebook(session, principal, body.codebook_id)
    if codebook.status != CodebookStatus.APPROVED:
        raise HTTPException(status_code=409, detail="codebook must be approved before coding")
    transcript = await _transcript_or_409(asset, principal.org_id)

    with use_llm_context("qual", "coding", project_id=asset.project_id, org_id=principal.org_id):
        assignments = apply_codebook(
            transcript["segments"], codebook.codes, qual_llm.default_complete
        )
    await save_coding(asset.id, principal.org_id, codebook.id, assignments)
    return {"assignments": assignments, "codebook_id": str(codebook.id)}


@router.post("/media/{asset_id}/sentiment")
async def sentiment_asset(
    asset_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    asset = await _require_asset(session, principal, asset_id)
    transcript = await _transcript_or_409(asset, principal.org_id)
    with use_llm_context("qual", "sentiment", project_id=asset.project_id, org_id=principal.org_id):
        rated = segment_sentiment(transcript["segments"], qual_llm.default_complete)
    await save_sentiment(asset.id, principal.org_id, rated)
    return {"sentiment": rated}


@router.get("/media/{asset_id}/coding")
async def read_coding(
    asset_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    await _require_asset(session, principal, asset_id)
    return {"coding": await get_coding(asset_id, principal.org_id)}


@router.patch("/media/{asset_id}/coding")
async def override_coding(
    asset_id: uuid.UUID,
    body: OverrideIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, str]:
    await _require_asset(session, principal, asset_id)
    if body.action == "add":
        ok = await add_human_assignment(asset_id, principal.org_id, body.segment, body.code)
    elif body.action == "remove":
        ok = await remove_assignment(asset_id, principal.org_id, body.segment, body.code)
    else:
        raise HTTPException(status_code=422, detail="action must be 'add' or 'remove'")
    if not ok:
        raise HTTPException(status_code=404, detail="coding not found for this asset")
    return {"status": body.action}


# ----------------------------- quotes (Evidence-locked) -----------------------------

@router.post("/media/{asset_id}/quotes")
async def extract_quotes(
    asset_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    asset = await _require_asset(session, principal, asset_id)
    transcript = await _transcript_or_409(asset, principal.org_id)

    with use_llm_context("qual", "quotes", project_id=asset.project_id, org_id=principal.org_id):
        candidates = propose_quotes(transcript.get("text", ""), qual_llm.default_complete)
    verified = verbatim_filter(candidates, transcript["segments"])
    dropped = len(candidates) - len(verified)

    result = await execute_component(
        session,
        org_id=principal.org_id,
        project_id=asset.project_id,
        component_id="analyzer.quote_extraction",
        params={"asset_id": str(asset.id), "quotes": verified},
        lab="qual",
    )
    await session.commit()
    return {
        "quotes": verified,
        "dropped_non_verbatim": dropped,
        "run_id": str(result.run.id),
        "evidence_count": len(verified) + 1,
    }


# ----------------------------- synthesis -----------------------------

@router.get("/projects/{project_id}/qual/synthesis")
async def synthesis(
    project_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> dict[str, Any]:
    """Theme × source matrix across all coded assets in the project (deterministic)."""
    await _require_project(session, principal, project_id)
    assets = (
        await session.execute(
            select(MediaAsset).where(
                MediaAsset.org_id == principal.org_id, MediaAsset.project_id == project_id
            )
        )
    ).scalars().all()
    codings_by_asset: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        coding = await get_coding(asset.id, principal.org_id)
        if coding and coding.get("assignments"):
            codings_by_asset[str(asset.id)] = coding["assignments"]
    matrix = theme_matrix(codings_by_asset)
    matrix["asset_names"] = {str(a.id): a.filename for a in assets}
    return matrix
