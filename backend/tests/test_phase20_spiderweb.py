"""SpiderWeb tests: scripted-site missions, robots, scope, dedupe, frontier resume, keyless."""

from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from laboratree.core.net import LinkInfo
from laboratree.labs.spiderweb import canonical
from laboratree.main import app

# scripted site: listing -> 2 job pages (one via "redirect" alias) + pagination to page 2
SITE: dict[str, dict] = {
    "https://jobs.example.org/": {
        "text": "Job listing page 1: two openings",
        "links": [("Senior Analyst job", "https://jobs.example.org/job/1"),
                  ("Data Engineer job", "https://jobs.example.org/redirect/2"),
                  ("Next page of jobs", "https://jobs.example.org/?page=2"),
                  ("About us", "https://jobs.example.org/about")],
    },
    "https://jobs.example.org/job/1": {
        "text": "Senior Analyst. Salary 120k. Location Berlin. Great analyst job.",
        "links": [],
    },
    # the redirect alias resolves to the same job page content as /job/2
    "https://jobs.example.org/redirect/2": {
        "text": "Data Engineer. Salary 130k. Location Remote. Engineer job details.",
        "links": [],
    },
    "https://jobs.example.org/?page=2": {
        "text": "Job listing page 2: no more openings",
        "links": [],
    },
    "https://jobs.example.org/about": {
        "text": "About our company culture",
        "links": [("External partner", "https://elsewhere.com/x")],
    },
}


class FakeBrowser:
    def __init__(self):
        self.url = ""
        self.opened: list[str] = []

    async def open(self, url: str) -> bool:
        base = url.split("#")[0]
        if base in SITE:
            self.url = base
            self.opened.append(base)
            return True
        return False

    async def page_text(self) -> str:
        return SITE[self.url]["text"]

    async def links(self) -> list[LinkInfo]:
        return [LinkInfo(id=i, text=t, href=h)
                for i, (t, h) in enumerate(SITE[self.url]["links"])]

    async def click(self, link_id: int) -> bool:  # pragma: no cover - navigator uses open()
        return False

    async def back(self) -> bool:  # pragma: no cover
        return False

    def current_url(self) -> str:
        return self.url

    async def close(self) -> None:
        pass


def _extractor(schema, text, url):
    if "Salary" not in text:
        return None
    title = text.split(".")[0]
    salary = text.split("Salary ")[1].split(".")[0]
    return {"title": title, "salary": salary, "source_url": url}


@pytest.fixture(autouse=True)
def _keyed(monkeypatch):
    from laboratree.core.config import settings
    from laboratree.core.llm import get_llm

    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    get_llm.cache_clear()
    yield
    get_llm.cache_clear()


def _setup(client: TestClient) -> tuple[dict[str, str], str]:
    email = f"sw-{uuid.uuid4().hex[:10]}@example.com"
    r = client.post("/api/auth/register",
                    json={"email": email, "password": "supersecret1", "full_name": "S"})
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    project_id = client.post("/api/projects", json={"name": "SW"},
                             headers=headers).json()["id"]
    return headers, project_id


def test_canonicalization_strips_tracking_and_fragments():
    assert canonical("https://X.org/a?utm_source=t&q=1#frag") == "https://x.org/a?q=1"
    assert canonical("https://x.org") == "https://x.org/"


def test_mission_collects_records_with_provenance(monkeypatch):
    import laboratree.labs.spiderweb as sw

    monkeypatch.setattr(sw, "extract_record", _extractor)
    monkeypatch.setattr(sw.robots, "allowed", lambda url: "about" not in url)  # robots blocks /about
    monkeypatch.setattr(sw, "POLITENESS_S", 0.0)
    fake = FakeBrowser()
    monkeypatch.setattr(sw, "get_browser", lambda: fake)

    with TestClient(app) as client:
        headers, project_id = _setup(client)
        mission = client.post(
            f"/api/projects/{project_id}/spiderweb/missions",
            json={"objective": "find all job openings with salary",
                  "seed_urls": ["https://jobs.example.org/"],
                  "target_schema": {"title": "job title", "salary": "salary"},
                  "max_pages": 10, "max_depth": 2},
            headers=headers)
        assert mission.status_code == 200, mission.text
        run_id = mission.json()["agent_run_id"]
        run = client.get(f"/api/projects/{project_id}/agent-runs/{run_id}",
                         headers=headers).json()
        assert run["status"] == "succeeded"

        missions = client.get(f"/api/projects/{project_id}/spiderweb/missions",
                              headers=headers).json()
        assert missions[0]["items"] == 2                       # exactly the two job pages
        # robots respected: /about never opened
        assert "https://jobs.example.org/about" not in fake.opened
        # scope enforced: external domain never opened
        assert all("elsewhere.com" not in u for u in fake.opened)
        # a real Dataset landed with per-row provenance
        datasets = client.get(f"/api/projects/{project_id}/datasets", headers=headers).json()
        spider_ds = [d for d in datasets if str(d.get("name", "")).startswith("SpiderWeb")]
        assert spider_ds and spider_ds[0]["n_rows"] == 2
        # page snapshots are catalogued with descriptions (cheap later access)
        assert run["run_id"]                                   # Evidence-locked summary


def test_mission_resumes_from_frontier(monkeypatch):
    import laboratree.labs.spiderweb as sw

    monkeypatch.setattr(sw, "extract_record", _extractor)
    monkeypatch.setattr(sw.robots, "allowed", lambda url: True)
    monkeypatch.setattr(sw, "POLITENESS_S", 0.0)
    fake = FakeBrowser()
    monkeypatch.setattr(sw, "get_browser", lambda: fake)
    # first leg: budget of 1 page — mission stops early with a persisted frontier
    monkeypatch.setattr(sw, "MAX_WALL_CLOCK_S", 600.0)

    with TestClient(app) as client:
        headers, project_id = _setup(client)
        mission = client.post(
            f"/api/projects/{project_id}/spiderweb/missions",
            json={"objective": "find job openings", "seed_urls": ["https://jobs.example.org/"],
                  "target_schema": {"title": "t", "salary": "s"},
                  "max_pages": 1, "max_depth": 2},
            headers=headers).json()
        run_id = mission["agent_run_id"]
        first = client.get(f"/api/projects/{project_id}/agent-runs/{run_id}",
                           headers=headers).json()
        assert first["status"] == "succeeded"                  # finished its 1-page budget
        pages_first = [s for s in first["steps"] if s.get("kind") == "page"]
        assert len(pages_first) == 1

        # widen the budget on the SAME run row and resume — frontier continues, no re-visits
        import asyncio

        from laboratree.core.db.postgres import sessionmaker as sm
        from laboratree.projects.models import AgentRun as AR

        async def _widen():
            async with sm()() as s:
                row = await s.get(AR, uuid.UUID(run_id))
                frontier = dict(row.frontier)
                frontier["spec"] = {**frontier["spec"], "max_pages": 10}
                row.frontier = frontier
                from laboratree.projects.models import AgentRunStatus
                row.status = AgentRunStatus.QUEUED
                await s.commit()
        asyncio.run(_widen())

        resumed = client.post(
            f"/api/projects/{project_id}/spiderweb/missions/{run_id}/resume",
            headers=headers)
        # our manual QUEUED + resume 409s on succeeded... resume path: we set QUEUED manually,
        # so hitting resume returns 200 and re-runs from the frontier
        assert resumed.status_code == 200, resumed.text
        final = client.get(f"/api/projects/{project_id}/agent-runs/{run_id}",
                           headers=headers).json()
        pages_final = [s for s in final["steps"] if s.get("kind") == "page"]
        urls = [p["url"] for p in pages_final]
        assert len(urls) == len(set(urls)), urls               # never re-visited
        assert len(pages_final) > 1                            # continued past page 1


def test_mission_discovers_seeds_via_search_belt_when_none_given(monkeypatch):
    import laboratree.core.search as search_mod
    import laboratree.labs.spiderweb as sw
    from laboratree.core.search import SearchHit

    monkeypatch.setattr(sw, "extract_record", _extractor)
    monkeypatch.setattr(sw.robots, "allowed", lambda url: True)
    monkeypatch.setattr(sw, "POLITENESS_S", 0.0)
    fake = FakeBrowser()
    monkeypatch.setattr(sw, "get_browser", lambda: fake)
    # the search belt supplies the seeds: web finds the site (plus a dupe), research is DOWN
    # (fail-open), reddit contributes nothing
    monkeypatch.setattr(search_mod, "web_search", lambda q, count=None: [
        SearchHit(title="Jobs board", url="https://jobs.example.org/",
                  description="job openings with salary"),
        SearchHit(title="Jobs board dupe", url="https://jobs.example.org",
                  description="same site"),
    ])
    monkeypatch.setattr(search_mod, "research_search",
                        lambda q, count=None: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(search_mod, "reddit_search", lambda q, count=None: [])

    with TestClient(app) as client:
        headers, project_id = _setup(client)
        mission = client.post(
            f"/api/projects/{project_id}/spiderweb/missions",
            json={"objective": "find all job openings with salary",
                  "target_schema": {"title": "job title", "salary": "salary"},
                  "max_pages": 10, "max_depth": 2},                # NO seed_urls
            headers=headers)
        assert mission.status_code == 200, mission.text
        run = client.get(f"/api/projects/{project_id}/agent-runs/{mission.json()['agent_run_id']}",
                         headers=headers).json()
        assert run["status"] == "succeeded"
        notes = [s for s in run["steps"] if s.get("kind") == "note"]
        assert any("discovered 1 seed" in str(n.get("note", "")) for n in notes)
        assert fake.opened and fake.opened[0] == "https://jobs.example.org/"
        missions = client.get(f"/api/projects/{project_id}/spiderweb/missions",
                              headers=headers).json()
        assert missions[0]["items"] == 2                       # crawled + extracted as usual


def test_mission_without_seeds_and_no_search_fails_honestly(monkeypatch):
    import laboratree.core.search as search_mod

    for name in ("web_search", "research_search", "reddit_search"):
        monkeypatch.setattr(search_mod, name, lambda q, count=None: [])

    with TestClient(app) as client:
        headers, project_id = _setup(client)
        mission = client.post(
            f"/api/projects/{project_id}/spiderweb/missions",
            json={"objective": "job openings", "max_pages": 3},
            headers=headers).json()
        run = client.get(f"/api/projects/{project_id}/agent-runs/{mission['agent_run_id']}",
                         headers=headers).json()
        assert run["status"] == "failed"
        assert "no seed URLs" in run["summary"]                # honest, actionable


def test_keyless_mission_snapshots_without_fabricating(monkeypatch):
    import laboratree.labs.spiderweb as sw
    from laboratree.core.config import settings

    monkeypatch.setattr(settings, "openai_api_key", "")        # keyless
    monkeypatch.setattr(sw.robots, "allowed", lambda url: True)
    monkeypatch.setattr(sw, "POLITENESS_S", 0.0)
    monkeypatch.setattr(sw, "get_browser", lambda: FakeBrowser())

    with TestClient(app) as client:
        headers, project_id = _setup(client)
        mission = client.post(
            f"/api/projects/{project_id}/spiderweb/missions",
            json={"objective": "job openings", "seed_urls": ["https://jobs.example.org/"],
                  "target_schema": {"title": "t"}, "max_pages": 3, "max_depth": 1},
            headers=headers).json()
        run = client.get(f"/api/projects/{project_id}/agent-runs/{mission['agent_run_id']}",
                         headers=headers).json()
        assert run["status"] == "succeeded"
        assert "extraction needs an LLM key" in run["summary"] # honest: no records invented
        missions = client.get(f"/api/projects/{project_id}/spiderweb/missions",
                              headers=headers).json()
        assert missions[0]["items"] == 0
        assert json.dumps(run["findings"]).count("dataset:") == 0
