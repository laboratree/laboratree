"""Public survey runtime API — respondents answer with NO account (token = authorization).

Every route is rate-limited by client IP (fails open) and reads/writes only the single survey the
token resolves to — no authenticated data is reachable here. Completion runs server-side skip-logic,
an **atomic** quota check, and quality flags; suspect responses are flagged and STORED, never
deleted.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.db.postgres import get_session
from ..core.ratelimit import check_rate_limit
from ..fieldwork.models import ResponseStatus, Survey, SurveyResponse, SurveyStatus
from ..labs.fieldwork.quality import quality_flags
from ..labs.fieldwork.quotas import matching_quota
from ..labs.fieldwork.runtime import is_screened_out, missing_required

log = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["public-survey"])

RESUME_KEY_BYTES = 18


def public_rate_limited(bucket: str, *, limit: int, window_s: int = 60):
    """IP-keyed rate limit for unauthenticated routes (fails open like the authed limiter)."""

    async def _dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        allowed, retry = await check_rate_limit(f"rl:pub:{bucket}:{ip}", limit, window_s)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"too many requests — retry in {retry}s",
                headers={"Retry-After": str(retry)},
            )

    return Depends(_dep)


def _fingerprint(request: Request) -> dict[str, str]:
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    return {
        "ip_hash": hashlib.sha256(ip.encode()).hexdigest()[:32] if ip else "",
        "ua_hash": hashlib.sha256(ua.encode()).hexdigest()[:32] if ua else "",
    }


async def _live_survey(session: AsyncSession, token: str) -> Survey:
    """Resolve a token to a survey; 404 (with a friendly reason) for closed/unknown tokens."""
    survey = (
        await session.execute(select(Survey).where(Survey.public_token == token))
    ).scalar_one_or_none()
    if survey is None:
        raise HTTPException(status_code=404, detail="this survey link is not valid")
    if survey.status == SurveyStatus.CLOSED:
        raise HTTPException(status_code=404, detail="this survey has closed")
    return survey


# ----------------------------- schemas -----------------------------

class StartIn(BaseModel):
    resume_key: str | None = None
    invitation_token: str | None = None  # opaque panel link (never PII)


class AnswersIn(BaseModel):
    answers: dict[str, Any] = {}


# ----------------------------- routes -----------------------------

@router.get("/surveys/{token}", dependencies=[public_rate_limited("survey_get", limit=120)])
async def get_public_survey(
    token: str, session: Annotated[AsyncSession, Depends(get_session)]
) -> dict[str, Any]:
    survey = await _live_survey(session, token)
    if survey.status != SurveyStatus.LIVE:
        # paused: acknowledged but not accepting answers
        return {"title": survey.title, "structure": {}, "survey_status": survey.status.value}
    return {
        "title": survey.title,
        "structure": survey.structure or {},
        "survey_status": survey.status.value,
    }


@router.post("/surveys/{token}/responses", dependencies=[public_rate_limited("survey_start", limit=60)])
async def start_response(
    token: str,
    body: StartIn,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    survey = await _live_survey(session, token)
    if survey.status != SurveyStatus.LIVE:
        raise HTTPException(status_code=409, detail="this survey is not currently open")

    # Idempotent resume: a client-supplied key that already exists returns the same response.
    if body.resume_key:
        existing = (
            await session.execute(
                select(SurveyResponse).where(
                    SurveyResponse.resume_key == body.resume_key,
                    SurveyResponse.survey_id == survey.id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return {"resume_key": existing.resume_key}

    invitation_token = await _claim_invitation(session, survey, body.invitation_token)

    resume_key = body.resume_key or secrets.token_urlsafe(RESUME_KEY_BYTES)
    response = SurveyResponse(
        org_id=survey.org_id,
        survey_id=survey.id,
        instrument_version=survey.version,
        resume_key=resume_key,
        status=ResponseStatus.IN_PROGRESS,
        answers={},
        fingerprint=_fingerprint(request),
        invitation_token=invitation_token,
        started_at=datetime.now(UTC),
    )
    session.add(response)
    await session.commit()
    return {"resume_key": resume_key}


async def _claim_invitation(
    session: AsyncSession, survey: Survey, token: str | None
) -> str | None:
    """Validate an invitation token for this survey and mark it started. Invalid → ignored."""
    if not token:
        return None
    from ..panel.models import Invitation, InvitationStatus

    invitation = (
        await session.execute(
            select(Invitation).where(
                Invitation.token == token, Invitation.survey_id == survey.id
            )
        )
    ).scalar_one_or_none()
    if invitation is None:
        log.info("ignoring unknown invitation token for survey %s", survey.id)
        return None
    if invitation.status == InvitationStatus.SENT:
        invitation.status = InvitationStatus.STARTED
    return token


async def _load_response(
    session: AsyncSession, survey: Survey, resume_key: str
) -> SurveyResponse:
    response = (
        await session.execute(
            select(SurveyResponse).where(
                SurveyResponse.resume_key == resume_key,
                SurveyResponse.survey_id == survey.id,
            )
        )
    ).scalar_one_or_none()
    if response is None:
        raise HTTPException(status_code=404, detail="response not found")
    return response


@router.patch(
    "/surveys/{token}/responses/{resume_key}",
    dependencies=[public_rate_limited("survey_save", limit=300)],
)
async def save_answers(
    token: str,
    resume_key: str,
    body: AnswersIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    survey = await _live_survey(session, token)
    response = await _load_response(session, survey, resume_key)
    if response.status != ResponseStatus.IN_PROGRESS:
        raise HTTPException(status_code=409, detail="this response is already submitted")
    merged = dict(response.answers or {})
    merged.update(body.answers or {})  # last-write-wins per question
    response.answers = merged
    await session.commit()
    return {"status": "saved"}


@router.post(
    "/surveys/{token}/responses/{resume_key}/complete",
    dependencies=[public_rate_limited("survey_complete", limit=60)],
)
async def complete_response(
    token: str,
    resume_key: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    survey = await _live_survey(session, token)
    if survey.status != SurveyStatus.LIVE:
        raise HTTPException(status_code=409, detail="this survey is not currently open")
    response = await _load_response(session, survey, resume_key)
    if response.status != ResponseStatus.IN_PROGRESS:
        return {"status": "accepted"}  # idempotent: already finalized

    structure = survey.structure or {}
    answers = response.answers or {}

    missing = missing_required(structure, answers)
    if missing:
        raise HTTPException(status_code=422, detail={"missing": missing})

    now = datetime.now(UTC)
    if response.started_at is not None:
        response.duration_seconds = (now - response.started_at).total_seconds()
    response.completed_at = now

    if is_screened_out(structure, answers):
        response.status = ResponseStatus.SCREENED_OUT
        await session.commit()
        return {"status": "screened_out"}

    # Atomic quota fill: the single-statement guarded UPDATE lets exactly one racer take the last slot.
    await session.refresh(survey, attribute_names=["quotas"])
    quota_dicts = [
        {"id": str(q.id), "conditions": q.conditions, "target": q.target, "current": q.current}
        for q in survey.quotas
    ]
    matched = matching_quota(quota_dicts, answers)
    if matched is not None:
        result = await session.execute(
            text(
                "UPDATE survey_quotas SET current = current + 1 "
                "WHERE id = :qid AND current < target RETURNING id"
            ),
            {"qid": uuid.UUID(matched["id"])},
        )
        if result.first() is None:
            response.status = ResponseStatus.QUOTA_FULL
            await session.commit()
            return {"status": "quota_full"}

    prior = (
        await session.execute(
            select(SurveyResponse.fingerprint).where(
                SurveyResponse.survey_id == survey.id,
                SurveyResponse.id != response.id,
                SurveyResponse.status.in_(
                    [ResponseStatus.COMPLETE, ResponseStatus.FLAGGED]
                ),
            )
        )
    ).scalars().all()
    flags = quality_flags(
        answers=answers,
        structure=structure,
        duration_seconds=response.duration_seconds,
        fingerprint=response.fingerprint,
        prior_fingerprints=list(prior),
    )
    response.flags = flags
    response.status = ResponseStatus.FLAGGED if flags else ResponseStatus.COMPLETE
    await _complete_invitation(session, response.invitation_token)
    await session.commit()
    log.info("response %s completed (status=%s, flags=%s)", response.id, response.status.value, flags)
    return {"status": "accepted"}


async def _complete_invitation(session: AsyncSession, token: str | None) -> None:
    """Mark the linked panel invitation completed (no-op for open-link responses)."""
    if not token:
        return
    from ..panel.models import Invitation, InvitationStatus

    invitation = (
        await session.execute(select(Invitation).where(Invitation.token == token))
    ).scalar_one_or_none()
    if invitation is not None:
        invitation.status = InvitationStatus.COMPLETED


__all__ = ["router"]
