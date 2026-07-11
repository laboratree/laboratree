"""Phase 10 (Field Lab) tests: pure skip-logic/quality/quota units + survey API + public runtime.

Integration tests require a live migrated Postgres (see repo ops notes; POSTGRES_PORT=5433).
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from laboratree.labs.fieldwork.director import analyze_field
from laboratree.labs.fieldwork.quality import (
    flag_duplicate,
    flag_speeder,
    flag_straightliner,
)
from laboratree.labs.fieldwork.quotas import matching_quota
from laboratree.labs.fieldwork.runtime import (
    END,
    SCREENED_OUT,
    is_screened_out,
    missing_required,
    next_question_id,
    validate_answer,
    validate_structure,
    visible_path,
)
from laboratree.labs.synth.personas import MAX_PERSONAS, build_personas
from laboratree.labs.synth.twin import aggregate_dry_run
from laboratree.main import app

# ----------------------------- fixtures for pure logic -----------------------------

STRUCT = {
    "sections": [
        {
            "id": "s1",
            "title": "Screener",
            "questions": [
                {"id": "q1", "type": "single", "text": "Own a scooter?",
                 "required": True, "options": ["yes", "no"]},
                {"id": "q2", "type": "scale", "text": "Safety concern?",
                 "required": True, "scale": {"min": 1, "max": 5}},
                {"id": "q3", "type": "single", "text": "Would switch?",
                 "required": False, "options": ["yes", "no"]},
            ],
        }
    ],
    "logic": [
        {"if": {"qid": "q1", "op": "eq", "value": "no"},
         "then": {"action": "skip_to", "target": "q3"}},
        {"if": {"qid": "q2", "op": "lt", "value": 2},
         "then": {"action": "screen_out"}},
    ],
}


# ----------------------------- pure: structure validation -----------------------------

def test_valid_structure_has_no_errors():
    assert validate_structure(STRUCT) == []


def test_structure_validation_catches_problems():
    bad = {
        "sections": [{"id": "s", "questions": [
            {"id": "q1", "type": "single", "text": "x", "options": []},        # empty options
            {"id": "q1", "type": "mystery", "text": "y"},                      # dup id + bad type
            {"id": "q3", "type": "scale", "text": "z", "scale": {"min": 5, "max": 1}},  # min>=max
        ]}],
        "logic": [
            {"if": {"qid": "nope", "op": "eq", "value": 1}, "then": {"action": "skip_to", "target": "q1"}},
            {"if": {"qid": "q3", "op": "eq", "value": 1}, "then": {"action": "skip_to", "target": "q1"}},  # backward
        ],
    }
    errors = validate_structure(bad)
    joined = " | ".join(errors)
    assert "duplicate question id" in joined
    assert "unknown type" in joined
    assert "non-empty options" in joined
    assert "min < max" in joined
    assert "not a question" in joined
    assert "forward-only" in joined


# ----------------------------- pure: traversal -----------------------------

def test_skip_logic_jumps_forward():
    # answering q1="no" skips q2 -> straight to q3
    assert next_question_id(STRUCT, {"q1": "no"}, "q1") == "q3"
    # answering q1="yes" advances normally to q2
    assert next_question_id(STRUCT, {"q1": "yes"}, "q1") == "q2"


def test_screen_out_short_circuits():
    assert next_question_id(STRUCT, {"q1": "yes", "q2": 1}, "q2") == SCREENED_OUT
    assert is_screened_out(STRUCT, {"q1": "yes", "q2": 1}) is True
    assert is_screened_out(STRUCT, {"q1": "yes", "q2": 4}) is False


def test_visible_path_and_end():
    assert next_question_id(STRUCT, {}, None) == "q1"
    assert visible_path(STRUCT, {"q1": "no"}) == ["q1", "q3"]     # q2 skipped
    assert visible_path(STRUCT, {"q1": "yes", "q2": 4}) == ["q1", "q2", "q3"]
    assert next_question_id(STRUCT, {"q1": "yes", "q2": 4}, "q3") == END


def test_missing_required():
    # q3 is optional; on the yes path q1+q2 are required
    assert set(missing_required(STRUCT, {})) == {"q1", "q2"}
    assert missing_required(STRUCT, {"q1": "yes", "q2": 3}) == []
    # on the "no" path q2 is skipped, so only q1 is required
    assert missing_required(STRUCT, {"q1": "no"}) == []


def test_answer_validation():
    q_single = STRUCT["sections"][0]["questions"][0]
    q_scale = STRUCT["sections"][0]["questions"][1]
    assert validate_answer(q_single, "yes") is None
    assert validate_answer(q_single, "maybe") is not None
    assert validate_answer(q_scale, 3) is None
    assert validate_answer(q_scale, 9) is not None
    assert validate_answer(q_scale, "x") is not None


# ----------------------------- pure: quality + quotas -----------------------------

def test_quality_flags_pure():
    # 3 questions * 4s = 12s threshold
    assert flag_speeder(3.0, 3) is True
    assert flag_speeder(60.0, 3) is False
    assert flag_speeder(None, 3) is False

    straight = {"q1": "yes", "q2": 5, "q3": "yes"}  # q1/q3 single, q2 scale; but q2 differs
    # make all three identical-valued categorical -> straightliner
    struct3 = {"sections": [{"id": "s", "questions": [
        {"id": "a", "type": "single", "options": ["x", "y"]},
        {"id": "b", "type": "single", "options": ["x", "y"]},
        {"id": "c", "type": "single", "options": ["x", "y"]},
    ]}], "logic": []}
    assert flag_straightliner({"a": "x", "b": "x", "c": "x"}, struct3) is True
    assert flag_straightliner({"a": "x", "b": "y", "c": "x"}, struct3) is False
    assert flag_straightliner(straight, STRUCT) is False  # only 2 categorical, differing

    fp = {"ip_hash": "abc", "ua_hash": "z"}
    assert flag_duplicate(fp, [{"ip_hash": "abc"}]) is True
    assert flag_duplicate(fp, [{"ip_hash": "other"}]) is False
    assert flag_duplicate({"ip_hash": ""}, [{"ip_hash": ""}]) is False


def test_quota_matcher():
    quotas = [
        {"id": "1", "conditions": [{"qid": "q1", "value": "yes"}], "target": 5, "current": 0},
        {"id": "2", "conditions": [{"qid": "q1", "value": "no"}], "target": 5, "current": 0},
    ]
    assert matching_quota(quotas, {"q1": "yes"})["id"] == "1"
    assert matching_quota(quotas, {"q1": "no"})["id"] == "2"
    assert matching_quota(quotas, {"q1": "maybe"}) is None


# ----------------------------- pure: field director (U2) -----------------------------

def test_director_detects_dropoff_spike():
    monitor = {
        "completes": 20, "in_progress": 0, "screened_out": 0, "quota_full": 0, "flagged": 0,
        "quotas": [],
        "dropoff": [
            {"qid": "q1", "reached": 20, "answered": 20},
            {"qid": "q2", "reached": 20, "answered": 19},
            {"qid": "q3", "reached": 20, "answered": 8},   # 60% drop -> spike
        ],
    }
    findings = analyze_field(monitor)
    kinds = {f["kind"] for f in findings}
    assert "dropoff_spike" in kinds
    spike = next(f for f in findings if f["kind"] == "dropoff_spike")
    assert spike["detail"]["qid"] == "q3"
    assert spike["proposal"]


def test_director_flags_quota_lag_and_quality():
    monitor = {
        "completes": 40, "in_progress": 0, "screened_out": 0, "quota_full": 0, "flagged": 15,
        "quotas": [
            {"name": "men", "target": 100, "current": 80},   # leader, 80%
            {"name": "women", "target": 100, "current": 20},  # lagging, 20%
        ],
        "dropoff": [],
    }
    kinds = {f["kind"] for f in analyze_field(monitor)}
    assert "quota_lag" in kinds       # women cell lagging
    assert "quality" in kinds         # 15/55 > 20% flagged


def test_director_quiet_when_healthy():
    monitor = {
        "completes": 30, "in_progress": 5, "screened_out": 1, "quota_full": 0, "flagged": 1,
        "quotas": [
            {"name": "a", "target": 50, "current": 20},
            {"name": "b", "target": 50, "current": 18},
        ],
        "dropoff": [
            {"qid": "q1", "reached": 30, "answered": 30},
            {"qid": "q2", "reached": 30, "answered": 29},
        ],
    }
    assert analyze_field(monitor) == []


# ----------------------------- pure: synthetic twins (U3) -----------------------------

def test_build_personas_matches_margins_and_caps():
    personas = build_personas(10, {"gender": {"male": 0.5, "female": 0.5}})
    assert len(personas) == 10
    genders = [p["attributes"]["gender"] for p in personas]
    assert genders.count("male") == 5 and genders.count("female") == 5
    # hard cap
    assert len(build_personas(10_000, {})) == MAX_PERSONAS
    # largest-remainder rounding still totals n for uneven splits
    p3 = build_personas(3, {"grp": {"a": 0.34, "b": 0.33, "c": 0.33}})
    assert len(p3) == 3


def test_aggregate_dry_run_report():
    results = [
        {"answers": {"q1": "yes", "q2": 4}, "confusions": [], "dropped_at": None},
        {"answers": {"q1": "yes"}, "confusions": [{"qid": "q2", "note": "too vague"}], "dropped_at": "q2"},
        {"answers": {"q1": "no", "q2": 5}, "confusions": [{"qid": "q2", "note": "unclear scale"}],
         "dropped_at": None},
    ]
    report = aggregate_dry_run(STRUCT, results)
    assert report["n"] == 3
    assert report["completed"] == 2
    assert report["completion_rate"] == round(2 / 3, 3)
    assert report["predicted_dropoff"][0] == {"qid": "q2", "dropped": 1}
    assert report["confusing_items"][0]["qid"] == "q2"
    assert report["confusing_items"][0]["count"] == 2
    assert report["distributions"]["q1"]  # tallied yes/no
    assert "Synthetic" in report["caveat"]


# ----------------------------- integration helpers -----------------------------

def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"field-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "F"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    headers = _auth(token)
    cp = client.post("/api/projects", json={"name": "Field study"}, headers=headers)
    assert cp.status_code == 201, cp.text
    return headers, cp.json()["id"]


def _backdate_start(resume_key: str, minutes: int = 10) -> None:
    """Push started_at into the past so a millisecond-fast test completion isn't a speeder."""
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


# ----------------------------- integration: CRUD + publish -----------------------------

def test_create_and_save_empty_draft_then_publish_requires_questions():
    # regression (browser smoke): a fresh draft may be empty; only PUBLISH requires >=1 question
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        empty = {"sections": [{"id": "s1", "title": "Section 1", "questions": []}], "logic": []}
        created = client.post(f"/api/projects/{project_id}/surveys",
                              json={"title": "Untitled survey", "structure": empty}, headers=headers)
        assert created.status_code == 201, created.text  # was 422 before the fix
        sid = created.json()["id"]

        # saving an in-progress (still empty) draft is allowed
        saved = client.patch(f"/api/surveys/{sid}", json={"structure": empty}, headers=headers)
        assert saved.status_code == 200, saved.text

        # publishing an empty instrument is refused
        pub_empty = client.post(f"/api/surveys/{sid}/publish", headers=headers)
        assert pub_empty.status_code == 422

        # add a question, then publish succeeds
        client.patch(f"/api/surveys/{sid}", json={"structure": STRUCT}, headers=headers)
        assert client.post(f"/api/surveys/{sid}/publish", headers=headers).status_code == 200


def test_create_rejects_invalid_structure_and_patch_is_draft_only():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        bad = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "x", "structure": {"sections": [{"id": "s", "questions": [
                              {"id": "q1", "type": "single", "options": []}]}]}},
                          headers=headers)
        assert bad.status_code == 422
        assert "errors" in bad.json()["detail"]

        ok = client.post(f"/api/projects/{project_id}/surveys",
                         json={"title": "Scooter", "structure": STRUCT}, headers=headers)
        assert ok.status_code == 201, ok.text
        sid = ok.json()["id"]
        assert ok.json()["status"] == "draft"

        pub = client.post(f"/api/surveys/{sid}/publish", headers=headers)
        assert pub.status_code == 200
        assert pub.json()["public_url"].startswith("/s/")

        # editing after publish is refused
        patched = client.patch(f"/api/surveys/{sid}", json={"title": "nope"}, headers=headers)
        assert patched.status_code == 409


def test_full_public_flow_and_export():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "Scooter", "structure": STRUCT}, headers=headers).json()["id"]
        token = client.post(f"/api/surveys/{sid}/publish", headers=headers).json()["token"]

        # public GET
        pub = client.get(f"/public/surveys/{token}")
        assert pub.status_code == 200
        assert pub.json()["survey_status"] == "live"
        assert pub.json()["title"] == "Scooter"

        # start -> save -> complete (backdated so it isn't a speeder; varied answers, no straightline)
        rk = client.post(f"/public/surveys/{token}/responses", json={}).json()["resume_key"]
        client.patch(f"/public/surveys/{token}/responses/{rk}",
                     json={"answers": {"q1": "yes", "q2": 4, "q3": "no"}})
        _backdate_start(rk)
        done = client.post(f"/public/surveys/{token}/responses/{rk}/complete")
        assert done.status_code == 200
        assert done.json()["status"] == "accepted"

        mon = client.get(f"/api/surveys/{sid}/monitor", headers=headers)
        assert mon.status_code == 200
        assert mon.json()["completes"] == 1
        # dropoff has a row per question
        assert {d["qid"] for d in mon.json()["dropoff"]} == {"q1", "q2", "q3"}

        exp = client.post(f"/api/surveys/{sid}/export-dataset", headers=headers)
        assert exp.status_code == 200
        assert exp.json()["n_rows"] == 1
        assert exp.json()["n_cols"] >= 3


def test_screen_out_response():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "S", "structure": STRUCT}, headers=headers).json()["id"]
        token = client.post(f"/api/surveys/{sid}/publish", headers=headers).json()["token"]
        rk = client.post(f"/public/surveys/{token}/responses", json={}).json()["resume_key"]
        # q2=1 triggers screen_out; q1 answered so required check passes on the visible path
        client.patch(f"/public/surveys/{token}/responses/{rk}",
                     json={"answers": {"q1": "yes", "q2": 1}})
        _backdate_start(rk)
        done = client.post(f"/public/surveys/{token}/responses/{rk}/complete")
        assert done.json()["status"] == "screened_out"


def test_quota_atomicity_last_slot():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "Q", "structure": STRUCT}, headers=headers).json()["id"]
        # a single-slot quota for q1=yes
        client.put(f"/api/surveys/{sid}/quotas",
                   json=[{"name": "yes-cell", "conditions": [{"qid": "q1", "value": "yes"}], "target": 1}],
                   headers=headers)
        token = client.post(f"/api/surveys/{sid}/publish", headers=headers).json()["token"]

        def _complete_yes() -> str:
            rk = client.post(f"/public/surveys/{token}/responses", json={}).json()["resume_key"]
            client.patch(f"/public/surveys/{token}/responses/{rk}",
                         json={"answers": {"q1": "yes", "q2": 4, "q3": "no"}})
            _backdate_start(rk)
            return client.post(f"/public/surveys/{token}/responses/{rk}/complete").json()["status"]

        first = _complete_yes()
        second = _complete_yes()
        assert {first, second} == {"accepted", "quota_full"}  # exactly one took the slot

        mon = client.get(f"/api/surveys/{sid}/monitor", headers=headers).json()
        assert mon["quotas"][0]["current"] == 1
        assert mon["quota_full"] == 1


def test_speeder_is_flagged_not_deleted():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "Fast", "structure": STRUCT}, headers=headers).json()["id"]
        token = client.post(f"/api/surveys/{sid}/publish", headers=headers).json()["token"]
        rk = client.post(f"/public/surveys/{token}/responses", json={}).json()["resume_key"]
        client.patch(f"/public/surveys/{token}/responses/{rk}",
                     json={"answers": {"q1": "yes", "q2": 4, "q3": "no"}})
        # NO backdate -> completes in milliseconds -> speeder
        done = client.post(f"/public/surveys/{token}/responses/{rk}/complete")
        assert done.json()["status"] == "accepted"  # respondent still thanked
        mon = client.get(f"/api/surveys/{sid}/monitor", headers=headers).json()
        assert mon["flagged"] == 1
        assert mon["completes"] == 0  # flagged, not clean-complete — but STORED
        rows = client.get(f"/api/surveys/{sid}/responses?status=flagged", headers=headers).json()
        assert rows and "speeder" in rows[0]["flags"]


def test_public_routes_reject_bad_token_and_org_isolation():
    with TestClient(app) as client:
        headers_a, project_a = _setup(client)
        sid = client.post(f"/api/projects/{project_a}/surveys",
                          json={"title": "A", "structure": STRUCT}, headers=headers_a).json()["id"]

        # unknown public token -> friendly 404
        assert client.get("/public/surveys/not-a-real-token").status_code == 404

        # org B cannot read org A's survey via the admin API
        headers_b, _ = _setup(client)
        assert client.get(f"/api/surveys/{sid}", headers=headers_b).status_code == 404


def test_twin_dry_run_api_offline(monkeypatch):
    # fake LLM: every twin answers q1=yes, q2=4, finds q2 confusing, doesn't drop off
    from laboratree.labs.synth import llm as synth_llm

    def _fake(system: str, prompt: str, **kw) -> str:
        return (
            '{"answers": {"q1": "yes", "q2": 4}, '
            '"confusions": [{"qid": "q2", "note": "scale unclear"}], "dropped_at": null}'
        )

    monkeypatch.setattr(synth_llm, "default_complete", _fake)
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "T", "structure": STRUCT}, headers=headers).json()["id"]
        r = client.post(f"/api/surveys/{sid}/twin-dry-run",
                        json={"n": 6, "margins": {"gender": {"male": 0.5, "female": 0.5}}},
                        headers=headers)
        assert r.status_code == 200, r.text
        report = r.json()
        assert report["personas_run"] == 6
        assert report["completion_rate"] == 1.0
        assert report["confusing_items"][0]["qid"] == "q2"
        assert "Synthetic" in report["caveat"]


def test_prereg_lock_freezes_at_publish():
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "P", "structure": STRUCT}, headers=headers).json()["id"]
        # set a pre-registration on the draft
        pr = client.put(f"/api/surveys/{sid}/prereg",
                        json={"hypotheses": "Safety beats price", "planned_analyses": ["crosstab by gender"]},
                        headers=headers)
        assert pr.status_code == 200
        assert pr.json()["prereg"]["frozen_at"] is None

        # publish freezes it (stamps frozen_at + structure hash)
        client.post(f"/api/surveys/{sid}/publish", headers=headers)
        got = client.get(f"/api/surveys/{sid}", headers=headers).json()
        assert got["prereg"]["frozen_at"] is not None
        assert got["prereg"]["structure_hash"]
        assert got["prereg"]["hypotheses"] == "Safety beats price"

        # editing the pre-registration after the freeze is refused
        locked = client.put(f"/api/surveys/{sid}/prereg",
                            json={"hypotheses": "changed", "planned_analyses": []}, headers=headers)
        assert locked.status_code == 409


def test_atomic_quota_update_guard_sql_level():
    """Direct check: the guarded single-statement UPDATE refuses to increment past target."""
    from laboratree.core.db.postgres import sessionmaker
    from sqlalchemy import text

    with TestClient(app) as client:
        headers, project_id = _setup(client)
        sid = client.post(f"/api/projects/{project_id}/surveys",
                          json={"title": "G", "structure": STRUCT}, headers=headers).json()["id"]
        client.put(f"/api/surveys/{sid}/quotas",
                   json=[{"name": "c", "conditions": [{"qid": "q1", "value": "yes"}], "target": 1}],
                   headers=headers)
        quota_id = client.get(f"/api/surveys/{sid}", headers=headers).json()["quotas"][0]["id"]

    async def go() -> None:
        async with sessionmaker()() as s:
            stmt = text("UPDATE survey_quotas SET current = current + 1 "
                        "WHERE id = :qid AND current < target RETURNING id")
            first = (await s.execute(stmt, {"qid": uuid.UUID(quota_id)})).first()
            second = (await s.execute(stmt, {"qid": uuid.UUID(quota_id)})).first()
            await s.commit()
            assert first is not None      # took the slot
            assert second is None         # blocked at target

    asyncio.run(go())
