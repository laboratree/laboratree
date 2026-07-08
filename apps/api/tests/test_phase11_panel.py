"""Phase 11 (Panel CRM) tests: respondents, consent, invitations, GDPR erasure.

Requires a live migrated Postgres (POSTGRES_PORT=5433). Mail goes through the ConsoleMailer.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from laboratree.main import app

STRUCT = {
    "sections": [{"id": "s1", "title": "S", "questions": [
        {"id": "q1", "type": "single", "text": "Own a scooter?",
         "required": True, "options": ["yes", "no"]},
    ]}],
    "logic": [],
}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"panel-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "P"})
    assert r.status_code == 201, r.text
    headers = _auth(r.json()["access_token"])
    project_id = client.post("/api/projects", json={"name": "Panel study"},
                             headers=headers).json()["id"]
    return headers, project_id


def _live_survey(client: TestClient, headers: dict[str, str], project_id: str) -> tuple[str, str]:
    sid = client.post(f"/api/projects/{project_id}/surveys",
                      json={"title": "S", "structure": STRUCT}, headers=headers).json()["id"]
    token = client.post(f"/api/surveys/{sid}/publish", headers=headers).json()["token"]
    return sid, token


def _add_consented(client: TestClient, headers: dict[str, str], email: str) -> str:
    rid = client.post("/api/panel/respondents",
                      json={"email": email, "full_name": "R", "attributes": {"city": "berlin"}},
                      headers=headers).json()["id"]
    c = client.post(f"/api/panel/respondents/{rid}/consent",
                    json={"scope": "surveys", "consent_text": "I agree", "channel": "test"},
                    headers=headers)
    assert c.status_code == 200 and c.json()["consented_at"]
    return rid


def _backdate_start(resume_key: str, minutes: int = 10) -> None:
    from laboratree.core.db.postgres import sessionmaker
    from laboratree.fieldwork.models import SurveyResponse
    from sqlalchemy import update

    async def go() -> None:
        async with sessionmaker()() as s:
            await s.execute(
                update(SurveyResponse)
                .where(SurveyResponse.resume_key == resume_key)
                .values(started_at=datetime.now(UTC) - timedelta(minutes=minutes))
            )
            await s.commit()

    asyncio.run(go())


def test_respondent_crud_dedupe_and_consent():
    with TestClient(app) as client:
        headers, _ = _setup(client)
        rid = _add_consented(client, headers, "ada@example.com")

        # duplicate email -> 409
        dup = client.post("/api/panel/respondents",
                          json={"email": "ADA@example.com "}, headers=headers)
        assert dup.status_code == 409

        rows = client.get("/api/panel/respondents", headers=headers).json()
        assert len(rows) == 1 and rows[0]["id"] == rid
        # search
        assert client.get("/api/panel/respondents?q=ada", headers=headers).json()
        assert client.get("/api/panel/respondents?q=nobody", headers=headers).json() == []


def test_csv_import_dedupes_and_maps_attributes():
    with TestClient(app) as client:
        headers, _ = _setup(client)
        _add_consented(client, headers, "existing@example.com")
        csv_data = (
            "email,full_name,city\n"
            "existing@example.com,Dup,берлин\n"     # already in org -> skipped
            "new1@example.com,Nia,berlin\n"
            "new1@example.com,Nia again,berlin\n"   # repeats in file -> skipped
            "not-an-email,Bad,\n"                   # invalid -> skipped
            "new2@example.com,Omar,munich\n"
        )
        r = client.post("/api/panel/respondents/import",
                        files={"file": ("panel.csv", csv_data, "text/csv")}, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json() == {"imported": 2, "skipped": 3}
        rows = client.get("/api/panel/respondents", headers=headers).json()
        omar = next(x for x in rows if x["email"] == "new2@example.com")
        assert omar["attributes"]["city"] == "munich"


def test_invitation_flow_end_to_end():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid, survey_token = _live_survey(client, headers, project_id)

        rid = _add_consented(client, headers, "invitee@example.com")
        # a second respondent WITHOUT consent -> must be skipped
        client.post("/api/panel/respondents", json={"email": "noconsent@example.com"},
                    headers=headers)
        no_consent_id = client.get("/api/panel/respondents?q=noconsent",
                                   headers=headers).json()[0]["id"]

        batch = client.post(f"/api/surveys/{sid}/invitations",
                            json={"respondent_ids": [rid, no_consent_id]}, headers=headers)
        assert batch.status_code == 200, batch.text
        assert batch.json()["sent"] == 1 and batch.json()["skipped"] == 1

        # re-inviting the same respondent is skipped (already invited)
        again = client.post(f"/api/surveys/{sid}/invitations",
                            json={"respondent_ids": [rid]}, headers=headers)
        assert again.json()["sent"] == 0 and again.json()["skipped"] == 1

        stats = client.get(f"/api/surveys/{sid}/invitations", headers=headers).json()
        assert stats["sent"] == 1 and stats["total"] == 1

        # pull the invitation token via the GDPR export (has invitations but not the token) —
        # so read it from the DB layer instead
        from laboratree.core.db.postgres import sessionmaker
        from laboratree.panel.models import Invitation
        from sqlalchemy import select

        async def get_token() -> str:
            async with sessionmaker()() as s:
                inv = (
                    await s.execute(
                        select(Invitation).where(Invitation.survey_id == uuid.UUID(sid))
                    )
                ).scalars().first()
                assert inv is not None
                return inv.token

        inv_token = asyncio.run(get_token())

        # respondent starts via the invitation link -> invitation marked started
        rk = client.post(f"/public/surveys/{survey_token}/responses",
                         json={"invitation_token": inv_token}).json()["resume_key"]
        assert client.get(f"/api/surveys/{sid}/invitations", headers=headers).json()["started"] == 1

        # completes -> invitation marked completed; response stays pseudonymous
        client.patch(f"/public/surveys/{survey_token}/responses/{rk}",
                     json={"answers": {"q1": "yes"}})
        _backdate_start(rk)
        done = client.post(f"/public/surveys/{survey_token}/responses/{rk}/complete")
        assert done.json()["status"] == "accepted"
        assert client.get(f"/api/surveys/{sid}/invitations", headers=headers).json()["completed"] == 1

        rows = client.get(f"/api/surveys/{sid}/responses", headers=headers).json()
        assert rows and "email" not in rows[0]  # no PII on the response payload


def test_unknown_invitation_token_is_ignored():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        _, survey_token = _live_survey(client, headers, project_id)
        r = client.post(f"/public/surveys/{survey_token}/responses",
                        json={"invitation_token": "bogus"})
        assert r.status_code == 200  # open-link path still works


def test_gdpr_export_and_delete_keeps_pseudonymous_response():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid, survey_token = _live_survey(client, headers, project_id)
        rid = _add_consented(client, headers, "gdpr@example.com")
        client.post(f"/api/surveys/{sid}/invitations",
                    json={"respondent_ids": [rid]}, headers=headers)

        export = client.get(f"/api/panel/respondents/{rid}/export", headers=headers).json()
        assert export["respondent"]["email"] == "gdpr@example.com"
        assert export["consents"] and export["invitations"]

        # respond via invitation, then delete the identity
        from laboratree.core.db.postgres import sessionmaker
        from laboratree.panel.models import Invitation
        from sqlalchemy import select

        async def get_token() -> str:
            async with sessionmaker()() as s:
                inv = (
                    await s.execute(
                        select(Invitation).where(Invitation.survey_id == uuid.UUID(sid))
                    )
                ).scalars().first()
                assert inv is not None
                return inv.token

        inv_token = asyncio.run(get_token())
        rk = client.post(f"/public/surveys/{survey_token}/responses",
                         json={"invitation_token": inv_token}).json()["resume_key"]
        client.patch(f"/public/surveys/{survey_token}/responses/{rk}",
                     json={"answers": {"q1": "no"}})
        _backdate_start(rk)
        client.post(f"/public/surveys/{survey_token}/responses/{rk}/complete")

        assert client.delete(f"/api/panel/respondents/{rid}", headers=headers).status_code == 204
        assert client.get(f"/api/panel/respondents/{rid}/export", headers=headers).status_code == 404
        # the answer survives, pseudonymous
        rows = client.get(f"/api/surveys/{sid}/responses", headers=headers).json()
        assert len(rows) == 1 and rows[0]["answers"]["q1"] == "no"


def test_panel_org_isolation():
    with TestClient(app) as client:
        headers_a, _ = _setup(client)
        rid = _add_consented(client, headers_a, "iso@example.com")
        headers_b, _ = _setup(client)
        assert client.get("/api/panel/respondents", headers=headers_b).json() == []
        assert client.get(f"/api/panel/respondents/{rid}/export",
                          headers=headers_b).status_code == 404
