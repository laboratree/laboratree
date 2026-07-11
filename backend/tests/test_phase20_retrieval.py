"""Hybrid retrieval tests: RRF fusion, lexical FTS, rerank, isolation, index_document loop."""

from __future__ import annotations

import json
import uuid

import pytest
from laboratree.core.db.postgres import sessionmaker
from laboratree.core.retrieval import hybrid_search, index_document
from laboratree.papers.models import Paper, PaperChunk, PaperStatus
from sqlalchemy import text as sql_text

DIM = 1536


def _vec(direction: int) -> list[float]:
    v = [0.0] * DIM
    v[direction] = 1.0
    return v


async def _seed_org_project(session) -> tuple[uuid.UUID, uuid.UUID]:
    org, proj = uuid.uuid4(), uuid.uuid4()
    await session.execute(sql_text(
        "INSERT INTO organizations (id, name, slug, created_at, updated_at) "
        "VALUES (:i, 't', 't-' || :sfx, now(), now())"), {"i": org, "sfx": str(org)[:8]})
    await session.execute(sql_text(
        "INSERT INTO projects (id, org_id, name, description, created_at, updated_at) "
        "VALUES (:i, :o, 'p', '', now(), now())"), {"i": proj, "o": org})
    return org, proj


async def _seed_paper(session, org, proj, title: str, chunks: list[tuple[str, list | None]]):
    paper = Paper(org_id=org, project_id=proj, title=title, filename=f"{title}.pdf",
                  status=PaperStatus.PARSED, n_chunks=len(chunks))
    session.add(paper)
    await session.flush()
    for i, (chunk_text_, emb) in enumerate(chunks):
        session.add(PaperChunk(org_id=org, paper_id=paper.id, ordinal=i,
                               text=chunk_text_, embedding=emb))
    await session.flush()
    return paper


@pytest.mark.asyncio
async def test_rrf_fusion_beats_single_leg_and_keeps_leg_ranks():
    async with sessionmaker()() as session:
        org, proj = await _seed_org_project(session)
        # A: lexical #1 (exact terms) + dense #2. B: dense #1 only. C: noise.
        await _seed_paper(session, org, proj, "study", [
            ("bicycle subsidies raise school attendance in rural india", _vec(1)),
            ("unrelated musings about weather patterns and crops", _vec(0)),
            ("noise chunk about macroeconomics", _vec(2)),
        ])
        await session.commit()

        # query vector points at direction 0 -> dense ranks: B(#1), then A/C by distance
        results = await hybrid_search(
            session, org_id=org, project_id=proj,
            query="bicycle subsidies school attendance",
            k=3, embed_fn=lambda texts: [_vec(0)])

        top = results[0]
        assert "bicycle subsidies" in top.text            # fused winner: lex#1 + dense presence
        assert top.lexical_rank == 1
        assert top.score > results[1].score
        # the dense-only chunk is present but ranked below the fused one
        dense_only = next(r for r in results if "weather" in r.text)
        assert dense_only.dense_rank == 1 and dense_only.lexical_rank is None


@pytest.mark.asyncio
async def test_lexical_leg_finds_exact_phrase_without_embeddings():
    async with sessionmaker()() as session:
        org, proj = await _seed_org_project(session)
        await _seed_paper(session, org, proj, "docs", [
            ("the zebra microfinance cooperative model spread quickly", None),
            ("completely unrelated content about oceans", None),
        ])
        await session.commit()
        results = await hybrid_search(session, org_id=org, project_id=proj,
                                      query="zebra microfinance", k=2)
        assert results and "zebra microfinance" in results[0].text
        assert results[0].lexical_rank == 1 and results[0].dense_rank is None


@pytest.mark.asyncio
async def test_org_and_project_isolation():
    async with sessionmaker()() as session:
        org_a, proj_a = await _seed_org_project(session)
        org_b, proj_b = await _seed_org_project(session)
        await _seed_paper(session, org_b, proj_b, "secret", [
            ("confidential zebra findings from org b", None)])
        await session.commit()
        # org A sees nothing of org B's corpus
        assert await hybrid_search(session, org_id=org_a, project_id=proj_a,
                                   query="zebra") == []


@pytest.mark.asyncio
async def test_rerank_reorders_with_scripted_scores():
    async with sessionmaker()() as session:
        org, proj = await _seed_org_project(session)
        await _seed_paper(session, org, proj, "s", [
            ("alpha passage about dropout", None),
            ("beta passage about dropout drivers in detail", None),
            ("gamma passage mentioning dropout once", None),
        ])
        await session.commit()

        def _score_high_for_beta(system: str, prompt: str) -> str:
            import re
            ids = re.findall(r"\[([0-9a-f-]{36})\]", prompt)
            scores = {i: 1 for i in ids}
            for line in prompt.splitlines():
                if "beta passage" in line:
                    scores[line.split("]")[0].lstrip("[")] = 10
            return json.dumps({"scores": scores})

        results = await hybrid_search(session, org_id=org, project_id=proj, query="dropout",
                                      k=1, complete_fn=_score_high_for_beta)
        assert "beta passage" in results[0].text


@pytest.mark.asyncio
async def test_index_document_roundtrip_and_dedupe():
    async with sessionmaker()() as session:
        org, proj = await _seed_org_project(session)
        pid1 = await index_document(session, org_id=org, project_id=proj,
                                    title="Market sizing notes",
                                    text="India edtech market estimated at five billion dollars "
                                         "growing twenty percent yearly.",
                                    source_url="https://example.org/report?utm_source=x")
        pid2 = await index_document(session, org_id=org, project_id=proj,
                                    title="Market sizing notes (dup)",
                                    text="different text, same canonical source",
                                    source_url="https://example.org/report")
        await session.commit()
        assert pid1 == pid2                                 # deduped by canonical source_url
        hits = await hybrid_search(session, org_id=org, project_id=proj,
                                   query="edtech market five billion", k=2)
        assert hits and "five billion" in hits[0].text
        assert hits[0].source                                # carries the source label
