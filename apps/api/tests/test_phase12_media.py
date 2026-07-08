"""Phase 12 (Qual Studio I) tests: media upload → transcription pipeline → transcript store.

Requires live Postgres + Mongo (docker compose). The transcription engine is faked — no network.
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.core import transcribe as transcribe_core
from laboratree.core.media import extract_audio, media_kind
from laboratree.core.transcribe import Segment, TranscriptResult
from laboratree.main import app


class FakeEngine:
    """Deterministic engine: two segments, no network."""

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[str] = []

    def transcribe(self, audio: bytes, filename: str) -> TranscriptResult:
        self.calls.append(filename)
        if self.fail:
            raise RuntimeError("engine exploded")
        return TranscriptResult(
            segments=[
                Segment(start=0.0, end=3.5, text="Hello there."),
                Segment(start=3.5, end=7.0, text="Safety is my main concern."),
            ],
            text="Hello there. Safety is my main concern.",
            language="en",
        )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"media-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "M"})
    assert r.status_code == 201, r.text
    headers = _auth(r.json()["access_token"])
    project_id = client.post("/api/projects", json={"name": "Qual study"},
                             headers=headers).json()["id"]
    return headers, project_id


# ----------------------------- pure: core/media -----------------------------

def test_media_kind_classification():
    assert media_kind("interview.mp3") == "audio"
    assert media_kind("Interview.WAV") == "audio"
    assert media_kind("testimony.mp4") == "video"
    assert media_kind("notes.pdf") == "other"


def test_extract_audio_passthrough_and_video_gating(monkeypatch):
    # audio passes through unchanged
    data, name = extract_audio(b"fake-mp3-bytes", "talk.mp3")
    assert data == b"fake-mp3-bytes" and name == "talk.mp3"
    # video without ffmpeg -> clear actionable error
    import laboratree.core.media as media_mod
    monkeypatch.setattr(media_mod, "ffmpeg_available", lambda: False)
    try:
        media_mod.extract_audio(b"fake-mp4", "clip.mp4")
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "ffmpeg" in str(exc)


# ----------------------------- integration -----------------------------

def test_upload_transcribe_read_and_correct(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(transcribe_core, "get_engine", lambda: engine)
    with TestClient(app) as client:  # TestClient runs background tasks before returning
        headers, project_id = _setup(client)
        up = client.post(f"/api/projects/{project_id}/media",
                         files={"file": ("interview.mp3", b"fake-audio", "audio/mpeg")},
                         headers=headers)
        assert up.status_code == 201, up.text
        asset_id = up.json()["id"]
        assert engine.calls == ["interview.mp3"]

        # pipeline ran in background -> transcribed
        detail = client.get(f"/api/media/{asset_id}", headers=headers).json()
        assert detail["asset"]["status"] == "transcribed"
        assert detail["asset"]["language"] == "en"
        assert detail["asset"]["duration_seconds"] == 7.0
        assert len(detail["transcript"]["segments"]) == 2
        assert "Safety" in detail["transcript"]["text"]

        # list shows it
        rows = client.get(f"/api/projects/{project_id}/media", headers=headers).json()
        assert len(rows) == 1 and rows[0]["status"] == "transcribed"

        # human correction updates segment + full text
        fix = client.patch(f"/api/media/{asset_id}/transcript",
                           json={"index": 0, "text": "Hello there, interviewer."}, headers=headers)
        assert fix.status_code == 200
        detail2 = client.get(f"/api/media/{asset_id}", headers=headers).json()
        assert detail2["transcript"]["segments"][0]["text"] == "Hello there, interviewer."
        assert "interviewer" in detail2["transcript"]["text"]

        # out-of-range correction -> 404
        bad = client.patch(f"/api/media/{asset_id}/transcript",
                           json={"index": 99, "text": "x"}, headers=headers)
        assert bad.status_code == 404

        # file streams back
        blob = client.get(f"/api/media/{asset_id}/file", headers=headers)
        assert blob.status_code == 200 and blob.content == b"fake-audio"


def test_failed_engine_lands_in_failed_state_and_retry_works(monkeypatch):
    engine = FakeEngine(fail=True)
    monkeypatch.setattr(transcribe_core, "get_engine", lambda: engine)
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        up = client.post(f"/api/projects/{project_id}/media",
                         files={"file": ("talk.mp3", b"abc", "audio/mpeg")}, headers=headers)
        asset_id = up.json()["id"]
        detail = client.get(f"/api/media/{asset_id}", headers=headers).json()
        assert detail["asset"]["status"] == "failed"
        assert "exploded" in detail["asset"]["error"]
        assert detail["transcript"] is None

        # retry with a working engine succeeds
        engine.fail = False
        retry = client.post(f"/api/media/{asset_id}/retry", headers=headers)
        assert retry.status_code == 200
        detail2 = client.get(f"/api/media/{asset_id}", headers=headers).json()
        assert detail2["asset"]["status"] == "transcribed"


def test_unsupported_type_rejected_and_org_isolation(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(transcribe_core, "get_engine", lambda: engine)
    with TestClient(app) as client:
        headers_a, project_a = _setup(client)
        bad = client.post(f"/api/projects/{project_a}/media",
                          files={"file": ("doc.pdf", b"%PDF", "application/pdf")}, headers=headers_a)
        assert bad.status_code == 422

        up = client.post(f"/api/projects/{project_a}/media",
                         files={"file": ("a.mp3", b"x", "audio/mpeg")}, headers=headers_a)
        asset_id = up.json()["id"]

        headers_b, _ = _setup(client)
        assert client.get(f"/api/media/{asset_id}", headers=headers_b).status_code == 404
        assert client.get(f"/api/media/{asset_id}/file", headers=headers_b).status_code == 404
