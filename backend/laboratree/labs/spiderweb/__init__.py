"""SpiderWeb — the agentic web navigator: delegate a dig, get a Dataset back.

A mission = objective + seed URLs + a target schema. The navigator walks pages with the
browser engine (Playwright when installed, guarded static fetch otherwise), scores links
against the objective, extracts one record per matching page, and lands everything platform-
native: a versioned Dataset (source_url per row), page snapshots catalogued with descriptions
(BlobNote), Evidence-locked mission findings, and a frontier persisted after EVERY page so a
stopped mission RESUMES exactly where it was.

Laws: robots.txt honored; same-registrable-domain scope unless widened explicitly; politeness
delay per domain; URL canonicalization + content-hash dedupe; page/depth/wall-clock caps;
page text is DATA (fenced in the extractor) — never instructions.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...agents.tools.context_tools import note_blob
from ...core.browser import BrowserEngine, get_browser
from ...core.datasets import store_dataframe
from ...core.storage import get_blob_store
from ...labs.agentic import llm as agentic_llm
from ...projects.models import AgentRun, AgentRunStatus
from . import robots
from .extract import extract_record

log = logging.getLogger(__name__)

POLITENESS_S = 1.5
MAX_WALL_CLOCK_S = 600.0
LINKS_PER_PAGE = 6
_TRACKING_PARAMS = ("utm_", "fbclid", "gclid", "ref", "mc_cid", "mc_eid")


class MissionSpec(BaseModel):
    objective: str = Field(min_length=3, max_length=1000)
    seed_urls: list[str] = Field(min_length=1, max_length=10)
    target_schema: dict[str, str] = Field(default_factory=dict)   # {} = snapshot-only mode
    max_pages: int = Field(default=50, ge=1, le=200)
    max_depth: int = Field(default=3, ge=1, le=5)
    allow_domains: list[str] = Field(default_factory=list)


def canonical(url: str) -> str:
    parts = urlsplit(url.strip())
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query)
                       if not any(k.lower().startswith(t) for t in _TRACKING_PARAMS)])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/",
                       query, ""))


def _domain(url: str) -> str:
    host = urlsplit(url).netloc.split(":")[0].lower()
    return host.removeprefix("www.")


def _in_scope(url: str, spec: MissionSpec, seed_domains: set[str]) -> bool:
    return _domain(url) in seed_domains | {d.lower() for d in spec.allow_domains}


def _score_links(links: list[dict], objective: str) -> list[dict]:
    terms = {t for t in objective.lower().split() if len(t) > 3}
    return sorted(links, key=lambda li: -sum(
        t in f'{li.get("text", "")} {li.get("href", "")}'.lower() for t in terms))


async def run_mission(
    session: AsyncSession, agent_run_id: uuid.UUID, *,
    browser: BrowserEngine | None = None,
) -> None:
    """Execute (or RESUME) a mission; all progress persists on the AgentRun row."""
    agent_run = await session.get(AgentRun, agent_run_id)
    if agent_run is None or agent_run.status not in (AgentRunStatus.QUEUED,
                                                     AgentRunStatus.RUNNING):
        return
    # COPY-on-load: never mutate the ORM's own JSONB dict — SQLAlchemy compares old==new at
    # flush, and in-place mutation makes them the same object (the update silently no-ops).
    stored: dict[str, Any] = dict(agent_run.frontier or {})
    spec = MissionSpec(**stored["spec"])
    queue: list[list] = [list(x) for x in stored.get("queue") or
                         [[canonical(u), 0] for u in spec.seed_urls]]
    visited: list[str] = list(stored.get("visited") or [])
    records: list[dict] = [dict(r) for r in stored.get("records") or []]
    record_hashes: set[str] = set(stored.get("record_hashes") or [])
    frontier: dict[str, Any] = {"spec": stored["spec"]}
    seed_domains = {_domain(u) for u in spec.seed_urls}
    extract_enabled = bool(spec.target_schema) and agentic_llm.is_configured()

    agent_run.status = AgentRunStatus.RUNNING
    await session.commit()

    engine = browser or get_browser()
    started = time.monotonic()
    last_domain_hit: dict[str, float] = {}

    try:
        while queue and len(visited) < spec.max_pages:
            if time.monotonic() - started > MAX_WALL_CLOCK_S:
                agent_run.steps = [*agent_run.steps,
                                   {"kind": "note", "note": "wall-clock budget reached"}]
                break
            url, depth = queue.pop(0)
            if url in visited or not _in_scope(url, spec, seed_domains):
                continue
            if not await asyncio.to_thread(robots.allowed, url):
                agent_run.steps = [*agent_run.steps,
                                   {"kind": "page", "url": url, "skipped": "robots"}]
                visited.append(url)
                continue
            wait = POLITENESS_S - (time.monotonic() - last_domain_hit.get(_domain(url), 0.0))
            if wait > 0:
                await asyncio.sleep(wait)
            last_domain_hit[_domain(url)] = time.monotonic()

            opened = await engine.open(url)
            visited.append(url)
            if not opened:
                agent_run.steps = [*agent_run.steps,
                                   {"kind": "page", "url": url, "skipped": "unreachable"}]
                await _persist(session, agent_run, frontier, queue, visited, records,
                               record_hashes)
                continue

            text = await engine.page_text()
            record = None
            if extract_enabled and text:
                record = await asyncio.to_thread(extract_record, spec.target_schema, text, url)
                if record is not None:
                    digest = hashlib.sha256(json.dumps(
                        {k: record[k] for k in spec.target_schema}, sort_keys=True,
                        default=str).encode()).hexdigest()[:24]
                    if digest in record_hashes:
                        record = None
                    else:
                        record_hashes.add(digest)
                        records.append(record)

            await _snapshot(session, agent_run, url, text, record, spec)

            if depth < spec.max_depth:
                links = _score_links(list(await engine.links()), spec.objective)
                for link in links[:LINKS_PER_PAGE]:
                    href = canonical(link["href"])
                    if href not in visited and _in_scope(href, spec, seed_domains):
                        queue.append([href, depth + 1])

            agent_run.steps = [*agent_run.steps,
                               {"kind": "page", "url": url, "depth": depth,
                                "matched": record is not None, "items": len(records)}]
            await _persist(session, agent_run, frontier, queue, visited, records, record_hashes)
    finally:
        try:
            await engine.close()
        except Exception:
            pass

    await _finish(session, agent_run, spec, records, visited, extract_enabled)


async def _persist(session, agent_run, frontier, queue, visited, records, record_hashes):
    agent_run.frontier = {**frontier, "queue": [list(x) for x in queue],
                          "visited": list(visited), "records": [dict(r) for r in records],
                          "record_hashes": sorted(record_hashes)}
    await session.commit()


async def _snapshot(session, agent_run, url, text, record, spec) -> None:
    key = f"spiderweb/{agent_run.id}/{hashlib.sha256(url.encode()).hexdigest()[:16]}.txt"
    try:
        get_blob_store().put(key, text.encode())
        description = (
            f"Matched item: {json.dumps({k: record.get(k) for k in list(spec.target_schema)[:4]}, default=str)[:200]}"
            if record else f"Page snapshot: {url[:150]}"
        )
        await note_blob(session, org_id=agent_run.org_id, project_id=agent_run.project_id,
                        key=key, kind="page", size=len(text), description=description,
                        source=url)
    except Exception as exc:  # snapshots are best-effort
        log.debug("snapshot failed for %s: %s", url, exc)


async def _finish(session, agent_run, spec, records, visited, extract_enabled) -> None:
    from ...agents.run_executor import execute_component

    summary = (f"mission complete: {len(records)} item(s) from {len(visited)} page(s)"
               if extract_enabled else
               f"snapshot crawl complete: {len(visited)} page(s) archived"
               + ("" if agentic_llm.is_configured() or not spec.target_schema
                  else " (extraction needs an LLM key — records not parsed)"))

    dataset_id = None
    if records:
        df = pd.DataFrame(records)
        dataset = await store_dataframe(session, org_id=agent_run.org_id,
                                        project_id=agent_run.project_id,
                                        name=f"SpiderWeb: {spec.objective[:60]}", df=df,
                                        prefix="spiderweb")
        dataset_id = str(dataset.id)

    findings = [{"claim": f"Collected {len(records)} '{spec.objective[:60]}' items across "
                          f"{len(visited)} pages", "basis": "mission frontier", "confidence": 1.0}]
    try:
        lock = await execute_component(
            session, org_id=agent_run.org_id, project_id=agent_run.project_id,
            component_id="agent.deep_findings",
            params={"findings": findings, "summary": summary, "model": "spiderweb"},
            inputs={}, lab="spiderweb")
        agent_run.run_id = lock.run.id
    except Exception as exc:
        log.warning("mission evidence lock failed: %s", exc)

    agent_run.summary = summary
    agent_run.findings = [*findings,
                          *([{"claim": f"dataset:{dataset_id}"}] if dataset_id else [])]
    agent_run.status = AgentRunStatus.SUCCEEDED

    # missions feed the Experience DB too: future web goals start from what worked here
    try:
        from ...agents.cognitive import Goal, record_experience
        from ...projects.models import ExperienceOutcome

        await record_experience(
            session, org_id=agent_run.org_id, project_id=agent_run.project_id,
            goal=Goal(text=spec.objective, intent=spec.objective[:300], kind="web"),
            plan=[{"objective": spec.objective[:200], "agent_type": "research"}],
            outcome=(ExperienceOutcome.SUCCEEDED if records or not extract_enabled
                     else ExperienceOutcome.PARTIAL),
            score=min(1.0, len(records) / max(1, spec.max_pages)),
            lessons=[f"seeds {[str(u) for u in spec.seed_urls[:2]]} yielded "
                     f"{len(records)} records over {len(visited)} pages"])
    except Exception as exc:  # strategy memory must never fail the mission
        log.info("mission experience record failed: %s", exc)

    await session.commit()


__all__ = ["MissionSpec", "run_mission", "canonical"]
