"""Pipeline I/O visibility + storage tests: io manifest, bucket listing, guarded downloads."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from laboratree.main import app


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"st-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "S"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    project_id = client.post("/api/projects", json={"name": "ST"},
                             headers=headers).json()["id"]
    return headers, project_id


def test_every_component_run_records_io(monkeypatch):
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        run = client.post(
            f"/api/projects/{project_id}/runs",
            json={"component_id": "analyzer.eda_profile", "params": {},
                  "dataset": [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]},
            headers=headers).json()
        manifest = run["run"]["repro_manifest"]
        assert manifest["io"]["in"] == {"rows": 2, "cols": 2, "columns": ["a", "b"]}
        assert "keys" in manifest["io"]["out"]


def test_flow_storage_listing_and_guarded_download(monkeypatch):
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    with TestClient(app) as client:
        headers, project_id = _setup(client)
        # a supervised run with an uncovered stage -> keyless deep agent opens a gate;
        # use the plain flow instead: its flow run creates a bucket only when phases write.
        report = client.post(f"/api/projects/{project_id}/flows/ngo-policy/run",
                             json={"stages": ["intake", "eda"]}, headers=headers).json()
        flow_run_id = report["flow_run_id"]

        # write into the flow's bucket (as executors/deep agents do), then list it
        from laboratree.core.storage import get_blob_store
        key = f"flows/{flow_run_id}/eda/notes.json"
        get_blob_store().put(key, b'{"hello": 1}')
        listing = client.get(f"/api/flows/runs/{flow_run_id}/storage", headers=headers).json()
        assert listing["total_files"] >= 1
        assert "eda" in listing["stages"]

        # owner downloads fine; another org is refused
        ok = client.get(f"/api/blobs/download?key={key}", headers=headers)
        assert ok.status_code == 200 and ok.content == b'{"hello": 1}'
        other = client.post("/api/auth/register",
                            json={"email": f"x-{uuid.uuid4().hex[:8]}@example.com",
                                  "password": "supersecret1", "full_name": "X"}).json()
        stranger = {"Authorization": f"Bearer {other['access_token']}"}
        assert client.get(f"/api/blobs/download?key={key}", headers=stranger).status_code == 403
        assert client.get(f"/api/flows/runs/{flow_run_id}/storage",
                          headers=stranger).status_code == 404

        # per-phase io mirrored onto the flow report
        by_id = {s["id"]: s for s in report["stages"]}
        assert by_id["eda"]["artifacts"]["io"]["in"]["rows"] > 0
