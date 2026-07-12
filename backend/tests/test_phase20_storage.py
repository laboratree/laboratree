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


def test_artifact_store_groups_by_lab_and_is_org_scoped(monkeypatch):
    import asyncio

    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "azure")
    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    with TestClient(app) as client:
        headers, project_id = _setup(client)

        from laboratree.agents.tools.context_tools import note_blob
        from laboratree.core.db.postgres import sessionmaker
        from laboratree.tenancy.models import Organization  # noqa: F401 (model import order)

        chat_run_id = uuid.uuid4()

        async def _seed():
            async with sessionmaker()() as session:
                from laboratree.projects.models import Run, RunStatus
                from sqlalchemy import text as sql_text
                org = (await session.execute(sql_text(
                    "SELECT org_id FROM projects WHERE id = :p"),
                    {"p": project_id})).scalar()
                await note_blob(session, org_id=org, project_id=uuid.UUID(project_id),
                                key=f"spiderweb/{uuid.uuid4()}/page1.txt", kind="page",
                                size=120, description="Job post: Senior Analyst @ X",
                                source="https://jobs.example.org/1")
                await note_blob(session, org_id=org, project_id=uuid.UUID(project_id),
                                key=f"flows/{uuid.uuid4()}/lab-insight/trace.json",
                                kind="trace", size=300, description="Insight agent trace",
                                source="")
                # a chatbot run: anchor Run(kind="agent") + its trace under flows/{run_id}/lab-field
                session.add(Run(id=chat_run_id, org_id=org, project_id=uuid.UUID(project_id),
                                kind="agent", lab="field", component_id="agent.field",
                                status=RunStatus.SUCCEEDED, params={"task": "why do students drop out?"}))
                await session.flush()
                await note_blob(session, org_id=org, project_id=uuid.UUID(project_id),
                                key=f"flows/{chat_run_id}/lab-field/trace.json", kind="trace",
                                size=200, description="Field agent chat trace", source="")
                await session.commit()
        asyncio.run(_seed())

        store = client.get(f"/api/projects/{project_id}/artifact-store",
                           headers=headers).json()
        groups = store["groups"]
        labs = {g["lab"] for g in groups}
        assert {"spiderweb", "insight"} <= labs
        # artifacts are grouped under their producing task, not a flat list
        assert all(g["count"] == len(g["artifacts"]) for g in groups)
        assert all(a["description"] for g in groups for a in g["artifacts"]
                   if a["origin"] == "blob")
        # the SpiderWeb blob groups as a 'mission', the flow trace as a 'flow' (not a mission)
        kinds = {g["lab"]: g["task_kind"] for g in groups}
        assert kinds["spiderweb"] == "mission" and kinds["insight"] == "flow"
        # a chatbot run is a 'chat' task labelled by its question — NOT a standalone mission
        chat = next(g for g in groups if g["task_id"] == str(chat_run_id))
        assert chat["task_kind"] == "chat" and chat["lab"] == "field"
        assert chat["label"] == "why do students drop out?"

        # lab filter narrows
        only = client.get(f"/api/projects/{project_id}/artifact-store?lab=spiderweb",
                          headers=headers).json()
        assert only["groups"] and all(g["lab"] == "spiderweb" for g in only["groups"])

        # another org: project 404 (no cross-org browsing)
        other = client.post("/api/auth/register",
                            json={"email": f"y-{uuid.uuid4().hex[:8]}@example.com",
                                  "password": "supersecret1", "full_name": "Y"}).json()
        stranger = {"Authorization": f"Bearer {other['access_token']}"}
        assert client.get(f"/api/projects/{project_id}/artifact-store",
                          headers=stranger).status_code == 404
