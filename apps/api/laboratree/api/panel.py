"""Panel CRM API — respondents (the only PII surface), consent, and survey invitations.

GDPR floor: a respondent can be exported and deleted; their survey answers survive as pseudonymous
rows (linked only by the opaque invitation token, which maps to nothing once the panel row is gone).
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select

from ..core.deps import Principal, PrincipalDep, SessionDep, require_role
from ..core.notify import get_mailer
from ..fieldwork.models import Survey, SurveyStatus
from ..panel.models import ConsentRecord, Invitation, InvitationStatus, Respondent
from ..tenancy.models import Role

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["panel"])

INVITE_TOKEN_BYTES = 24
MAX_IMPORT_ROWS = 5000
DEFAULT_CONSENT_SCOPE = "surveys"


# ----------------------------- schemas -----------------------------

class RespondentOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    attributes: dict[str, Any]
    consented_at: datetime | None
    do_not_contact: bool
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RespondentIn(BaseModel):
    email: str
    full_name: str = ""
    attributes: dict[str, Any] = {}


class ConsentIn(BaseModel):
    scope: str = DEFAULT_CONSENT_SCOPE
    consent_text: str = ""
    channel: str = "manual"


class InviteBatchIn(BaseModel):
    respondent_ids: list[uuid.UUID] = []
    subject: str = "You're invited to a survey"
    message: str = "We'd value your input — the survey takes just a few minutes."


# ----------------------------- helpers -----------------------------

async def _require_respondent(
    session: SessionDep, principal: Principal, respondent_id: uuid.UUID
) -> Respondent:
    respondent = await session.get(Respondent, respondent_id)
    if respondent is None or respondent.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="respondent not found")
    return respondent


def _normalize_email(email: str) -> str:
    return email.strip().lower()


# ----------------------------- respondents -----------------------------

@router.get("/panel/respondents", response_model=list[RespondentOut])
async def list_respondents(
    session: SessionDep, principal: PrincipalDep, q: str | None = None
) -> list[Respondent]:
    query = select(Respondent).where(Respondent.org_id == principal.org_id)
    if q:
        like = f"%{q.lower()}%"
        query = query.where(
            func.lower(Respondent.email).like(like) | func.lower(Respondent.full_name).like(like)
        )
    rows = (await session.execute(query.order_by(Respondent.created_at.desc()))).scalars().all()
    return list(rows)


@router.post("/panel/respondents", response_model=RespondentOut, status_code=201)
async def create_respondent(
    body: RespondentIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Respondent:
    email = _normalize_email(body.email)
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="a valid email is required")
    existing = (
        await session.execute(
            select(Respondent).where(
                Respondent.org_id == principal.org_id, Respondent.email == email
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="respondent with this email already exists")
    respondent = Respondent(
        org_id=principal.org_id,
        email=email,
        full_name=body.full_name,
        attributes=body.attributes,
        source="manual",
    )
    session.add(respondent)
    await session.commit()
    await session.refresh(respondent)
    return respondent


@router.post("/panel/respondents/import")
async def import_respondents(
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
    file: Annotated[UploadFile, File(...)],
) -> dict[str, int]:
    """CSV import: an ``email`` column is required; every other column becomes an attribute.

    Dedupe: rows whose email already exists in the org (or repeats in the file) are skipped.
    """
    data = await file.read()
    try:
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
        rows = list(reader)[:MAX_IMPORT_ROWS]
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(status_code=422, detail=f"could not parse CSV: {exc}") from exc
    if rows and "email" not in {c.strip().lower() for c in (reader.fieldnames or [])}:
        raise HTTPException(status_code=422, detail="CSV needs an 'email' column")

    existing = set(
        (
            await session.execute(
                select(Respondent.email).where(Respondent.org_id == principal.org_id)
            )
        ).scalars().all()
    )
    imported = skipped = 0
    for row in rows:
        normalized = { (k or "").strip().lower(): (v or "").strip() for k, v in row.items() }
        email = _normalize_email(normalized.pop("email", ""))
        if not email or "@" not in email or email in existing:
            skipped += 1
            continue
        full_name = normalized.pop("full_name", normalized.pop("name", ""))
        session.add(
            Respondent(
                org_id=principal.org_id,
                email=email,
                full_name=full_name,
                attributes={k: v for k, v in normalized.items() if v},
                source="import",
            )
        )
        existing.add(email)
        imported += 1
    await session.commit()
    log.info("panel import: %d imported, %d skipped (org %s)", imported, skipped, principal.org_id)
    return {"imported": imported, "skipped": skipped}


@router.get("/panel/respondents/{respondent_id}/export")
async def export_respondent(
    respondent_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """GDPR access: the respondent's full panel record (PII + consents + invitations)."""
    respondent = await _require_respondent(session, principal, respondent_id)
    invitations = (
        await session.execute(
            select(Invitation).where(Invitation.respondent_id == respondent.id)
        )
    ).scalars().all()
    return {
        "respondent": RespondentOut.model_validate(respondent).model_dump(mode="json"),
        "consents": [
            {"scope": c.scope, "channel": c.channel, "recorded_at": c.created_at.isoformat()}
            for c in respondent.consents
        ],
        "invitations": [
            {"survey_id": str(i.survey_id), "status": i.status.value,
             "sent_at": i.sent_at.isoformat() if i.sent_at else None}
            for i in invitations
        ],
    }


@router.delete("/panel/respondents/{respondent_id}", status_code=204)
async def delete_respondent(
    respondent_id: uuid.UUID,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> None:
    """GDPR erasure: removes the identity (and its consents/invitations via cascade).

    Survey responses are NOT touched — they carry only the opaque invitation token, which now
    maps to nothing.
    """
    respondent = await _require_respondent(session, principal, respondent_id)
    await session.delete(respondent)
    await session.commit()
    log.info("respondent %s deleted (GDPR erasure), org %s", respondent_id, principal.org_id)


# ----------------------------- consent -----------------------------

@router.post("/panel/respondents/{respondent_id}/consent", response_model=RespondentOut)
async def record_consent(
    respondent_id: uuid.UUID,
    body: ConsentIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> Respondent:
    respondent = await _require_respondent(session, principal, respondent_id)
    session.add(
        ConsentRecord(
            org_id=principal.org_id,
            respondent_id=respondent.id,
            scope=body.scope,
            text_hash=hashlib.sha256(body.consent_text.encode()).hexdigest() if body.consent_text else "",
            channel=body.channel,
        )
    )
    respondent.consented_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(respondent)
    return respondent


# ----------------------------- invitations -----------------------------

@router.post("/surveys/{survey_id}/invitations")
async def invite_batch(
    survey_id: uuid.UUID,
    body: InviteBatchIn,
    session: SessionDep,
    principal: Annotated[Principal, Depends(require_role(Role.ANALYST))],
) -> dict[str, Any]:
    """Invite consented respondents to a LIVE survey (unique token each; consent is enforced)."""
    survey = await session.get(Survey, survey_id)
    if survey is None or survey.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="survey not found")
    if survey.status != SurveyStatus.LIVE or not survey.public_token:
        raise HTTPException(status_code=409, detail="survey must be live to send invitations")
    if not body.respondent_ids:
        raise HTTPException(status_code=422, detail="respondent_ids is empty")

    respondents = (
        await session.execute(
            select(Respondent).where(
                Respondent.org_id == principal.org_id, Respondent.id.in_(body.respondent_ids)
            )
        )
    ).scalars().all()

    already = set(
        (
            await session.execute(
                select(Invitation.respondent_id).where(Invitation.survey_id == survey.id)
            )
        ).scalars().all()
    )

    mailer = get_mailer()
    sent = skipped = failed = 0
    for r in respondents:
        if r.do_not_contact or r.consented_at is None or r.id in already:
            skipped += 1
            continue
        token = secrets.token_urlsafe(INVITE_TOKEN_BYTES)
        link = f"/s/{survey.public_token}?inv={token}"
        html = (
            f"<p>Hi {r.full_name or 'there'},</p><p>{body.message}</p>"
            f'<p><a href="{link}">Take the survey</a></p>'
        )
        result = mailer.send(r.email, body.subject, html)
        session.add(
            Invitation(
                org_id=principal.org_id,
                survey_id=survey.id,
                respondent_id=r.id,
                token=token,
                status=InvitationStatus.SENT,
                sent_at=datetime.now(UTC),
                delivery_ok=result.ok,
            )
        )
        if result.ok:
            sent += 1
        else:
            failed += 1
    await session.commit()
    log.info("invitations for survey %s: %d sent, %d skipped, %d failed",
             survey.id, sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}


@router.get("/surveys/{survey_id}/invitations")
async def invitation_stats(
    survey_id: uuid.UUID, session: SessionDep, principal: PrincipalDep
) -> dict[str, int]:
    survey = await session.get(Survey, survey_id)
    if survey is None or survey.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="survey not found")
    rows = (
        await session.execute(
            select(Invitation.status, func.count())
            .where(Invitation.survey_id == survey.id)
            .group_by(Invitation.status)
        )
    ).all()
    counts = {status.value: 0 for status in InvitationStatus}
    for status, count in rows:
        counts[status.value] = int(count)
    counts["total"] = sum(counts.values())
    return counts
