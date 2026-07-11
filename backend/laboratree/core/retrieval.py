"""Hybrid retrieval — the platform's one search engine over the knowledge corpus.

Dense (pgvector cosine) and lexical (Postgres full-text, ``websearch_to_tsquery`` + GIN index)
legs run together and merge with Reciprocal Rank Fusion; an optional single batched LLM rerank
sharpens the final order when a model is configured. Scope is org-mandatory and narrows to a
project or a single paper. Every leg degrades independently (no embeddings → lexical only;
odd query → deterministic keyword fallback) — retrieval never raises.

``index_document`` is the growth loop: agents ingest crawled/researched text here so it becomes
retrievable, citable knowledge for every later question.
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..labs.paper.ingest import chunk_text
from ..papers.models import Paper, PaperChunk, PaperStatus
from .jsonparse import loads_lenient

log = logging.getLogger(__name__)

CompleteFn = Callable[[str, str], str]
EmbedFn = Callable[[list[str]], list[list[float]]]

RRF_K = 60
LEG_POOL = 4          # each leg contributes k * LEG_POOL candidates before fusion
RERANK_SYSTEM = (
    "Score each passage 0-10 for relevance to the query. Respond ONLY as JSON: "
    '{"scores": {"<id>": <0-10>, ...}}'
)
_TOKEN = re.compile(r"[a-z0-9]{3,}")


@dataclass
class RetrievedChunk:
    chunk_id: str
    paper_id: str
    ordinal: int
    text: str
    score: float
    dense_rank: int | None
    lexical_rank: int | None
    source: str                       # paper title or indexed source url


def _scope(org_id: uuid.UUID, project_id: uuid.UUID | None, paper_id: uuid.UUID | None):
    stmt = select(PaperChunk, Paper.title, Paper.filename).join(
        Paper, Paper.id == PaperChunk.paper_id
    ).where(PaperChunk.org_id == org_id)
    if paper_id is not None:
        stmt = stmt.where(PaperChunk.paper_id == paper_id)
    elif project_id is not None:
        stmt = stmt.where(Paper.project_id == project_id)
    return stmt


def _as_chunk(row, *, dense_rank=None, lexical_rank=None) -> RetrievedChunk:
    chunk, title, filename = row
    return RetrievedChunk(
        chunk_id=str(chunk.id), paper_id=str(chunk.paper_id), ordinal=chunk.ordinal,
        text=chunk.text, score=0.0, dense_rank=dense_rank, lexical_rank=lexical_rank,
        source=title or filename or "",
    )


async def hybrid_search(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    paper_id: uuid.UUID | None = None,
    query: str,
    k: int = 6,
    embed_fn: EmbedFn | None = None,
    complete_fn: CompleteFn | None = None,
) -> list[RetrievedChunk]:
    pool = k * LEG_POOL
    fused: dict[str, RetrievedChunk] = {}

    # ---- dense leg (best-effort) ----
    if embed_fn is not None:
        try:
            qv = embed_fn([query])[0]
            rows = (await session.execute(
                _scope(org_id, project_id, paper_id)
                .where(PaperChunk.embedding.isnot(None))
                .order_by(PaperChunk.embedding.cosine_distance(qv))
                .limit(pool)
            )).all()
            for rank, row in enumerate(rows, start=1):
                c = _as_chunk(row, dense_rank=rank)
                fused[c.chunk_id] = c
        except Exception as exc:
            log.info("dense retrieval leg failed (%s); continuing lexical-only", exc)

    # ---- lexical leg (native Postgres FTS; best-effort) ----
    try:
        tsv = func.to_tsvector("english", PaperChunk.text)
        tsq = func.websearch_to_tsquery("english", query)
        rows = (await session.execute(
            _scope(org_id, project_id, paper_id)
            .where(tsv.op("@@")(tsq))
            .order_by(func.ts_rank_cd(tsv, tsq).desc())
            .limit(pool)
        )).all()
        for rank, row in enumerate(rows, start=1):
            c = _as_chunk(row, lexical_rank=rank)
            if c.chunk_id in fused:
                fused[c.chunk_id].lexical_rank = rank
            else:
                fused[c.chunk_id] = c
    except Exception as exc:
        log.info("lexical retrieval leg failed (%s)", exc)

    # ---- deterministic keyword fallback when both legs came back empty ----
    if not fused:
        return await _keyword_fallback(session, org_id, project_id, paper_id, query, k)

    # ---- Reciprocal Rank Fusion ----
    for c in fused.values():
        c.score = sum(1.0 / (RRF_K + r) for r in (c.dense_rank, c.lexical_rank) if r is not None)
    ranked = sorted(fused.values(), key=lambda c: (-c.score, c.ordinal))

    # ---- optional single batched rerank ----
    if complete_fn is not None and len(ranked) > k:
        ranked = _rerank(query, ranked, k, complete_fn)
    return ranked[:k]


def _rerank(query: str, candidates: list[RetrievedChunk], k: int,
            complete_fn: CompleteFn) -> list[RetrievedChunk]:
    """One batched relevance pass; any failure keeps the RRF order (never degrades below it)."""
    listing = "\n\n".join(f"[{c.chunk_id}] {c.text[:500]}" for c in candidates[: k * 2])
    try:
        raw = complete_fn(RERANK_SYSTEM, f"QUERY: {query}\n\nPASSAGES:\n{listing}")
        scores = (loads_lenient(raw) or {}).get("scores") or {}
        if scores:
            return sorted(candidates,
                          key=lambda c: (-float(scores.get(c.chunk_id, -1)), -c.score))
    except Exception as exc:
        log.info("rerank failed (%s); keeping RRF order", exc)
    return candidates


async def _keyword_fallback(session, org_id, project_id, paper_id, query, k) -> list[RetrievedChunk]:
    rows = (await session.execute(
        _scope(org_id, project_id, paper_id).order_by(PaperChunk.ordinal)
    )).all()
    terms = set(_TOKEN.findall(query.lower()))
    scored = []
    for row in rows:
        c = _as_chunk(row)
        c.score = float(sum(c.text.lower().count(t) for t in terms))
        scored.append(c)
    scored.sort(key=lambda c: (-c.score, c.ordinal))
    top = [c for c in scored if c.score > 0][:k] or scored[:k]
    return top


async def index_document(
    session: AsyncSession,
    *,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    title: str,
    text: str,
    source_url: str = "",
    embed_fn: EmbedFn | None = None,
) -> uuid.UUID:
    """Add researched/crawled text to the retrievable corpus (deduped by source hash)."""
    canonical = (source_url or "").split("#")[0].split("?utm", 1)[0].strip().lower()
    digest = hashlib.sha256((canonical or text).encode()).hexdigest()[:32]
    marker = f"indexed:{digest}"

    existing = (await session.execute(
        select(Paper).where(Paper.org_id == org_id, Paper.project_id == project_id,
                            Paper.storage_key == marker)
    )).scalar_one_or_none()
    if existing is not None:
        return existing.id

    paper = Paper(org_id=org_id, project_id=project_id, title=title[:490],
                  filename=(canonical or title)[:290], storage_key=marker,
                  status=PaperStatus.PARSED)
    session.add(paper)
    await session.flush()

    pieces = chunk_text(text)
    embeddings: list[list[float] | None] = [None] * len(pieces)
    if embed_fn is not None and pieces:
        try:
            embeddings = list(embed_fn(pieces))
        except Exception as exc:
            log.warning("indexing embeddings failed (%s); lexical-only for %s", exc, paper.id)
            embeddings = [None] * len(pieces)
    for i, (piece, emb) in enumerate(zip(pieces, embeddings, strict=False)):
        session.add(PaperChunk(org_id=org_id, paper_id=paper.id, ordinal=i,
                               text=piece, embedding=emb))
    paper.n_chunks = len(pieces)
    await session.flush()
    log.info("indexed document %r (%d chunks) into project %s", title[:60], len(pieces), project_id)
    return paper.id


__all__ = ["RetrievedChunk", "hybrid_search", "index_document", "RRF_K"]
