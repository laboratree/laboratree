"""Context-bound agent tools — org/project-scoped by construction, guard mechanics enforced.

- text2sql runs over the project's DATASETS in an in-memory sqlite engine with a SELECT-only
  authorizer (never raw prod Postgres — isolation by construction, not by parsing);
- text2cypher runs in a READ transaction with an org-anchored template + write-keyword denylist;
- blob access goes through BlobNote (described catalog) so agents browse cheaply and load full
  content only deliberately.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from typing import Any

from sqlalchemy import select

from ...core.storage import get_blob_store
from ...projects.models import BlobNote
from ..flow import FlowContext

log = logging.getLogger(__name__)

SQL_ROW_CAP = 200
SQL_COL_CAP = 30
CYPHER_ROW_CAP = 100
EXCERPT_CHARS = 1200
_CYPHER_DENY = re.compile(
    r"\b(create|merge|delete|detach|set|remove|drop|load|call\s+db\.)\b", re.IGNORECASE)


async def tool_knowledge_search(ctx: FlowContext, query: str, k: int = 6) -> Any:
    from ...core.retrieval import hybrid_search

    hits = await hybrid_search(ctx.session, org_id=ctx.org_id, project_id=ctx.project_id,
                               query=str(query), k=min(int(k), 10))
    return [{"source": h.source, "ordinal": h.ordinal, "text": h.text[:600],
             "score": round(h.score, 4)} for h in hits]


async def tool_index_text(ctx: FlowContext, title: str, text: str, source_url: str = "") -> Any:
    from ...core.retrieval import index_document

    paper_id = await index_document(ctx.session, org_id=ctx.org_id, project_id=ctx.project_id,
                                    title=str(title), text=str(text),
                                    source_url=str(source_url))
    return {"indexed": True, "document_id": str(paper_id)}


async def tool_dataset_overview(ctx: FlowContext) -> Any:
    df = ctx.state.get("df")
    if df is None:
        return {"note": "no working dataset in this run's state"}
    return {"n_rows": int(len(df)), "columns": {c: str(t) for c, t in df.dtypes.items()}}


def _sqlite_authorizer(action: int, *args: Any) -> int:
    # allow only read-class operations: SELECT/READ/FUNCTION/RECURSIVE — everything else denied
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
               getattr(sqlite3, "SQLITE_RECURSIVE", 33)}
    return sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY


async def tool_query_dataset_sql(ctx: FlowContext, sql: str) -> Any:
    df = ctx.state.get("df")
    if df is None:
        return {"error": "no working dataset — nothing to query"}
    if ";" in sql.strip().rstrip(";"):
        return {"error": "single statement only"}

    import asyncio

    def _run() -> Any:
        conn = sqlite3.connect(":memory:")
        try:
            df.head(50_000).to_sql("data", conn, index=False)
            conn.set_authorizer(_sqlite_authorizer)
            cur = conn.execute(sql)
            cols = [d[0] for d in (cur.description or [])][:SQL_COL_CAP]
            rows = cur.fetchmany(SQL_ROW_CAP)
            header = " | ".join(cols)
            body = "\n".join(" | ".join(str(v)[:60] for v in row[:SQL_COL_CAP]) for row in rows)
            return {"columns": cols, "n_rows": len(rows), "table": f"{header}\n{body}"[:4000]}
        finally:
            conn.close()

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run), timeout=10)
    except sqlite3.Error as exc:
        return {"error": f"sql rejected: {exc}"}
    except TimeoutError:
        return {"error": "query timed out (10s)"}


async def tool_query_cypher(ctx: FlowContext, cypher: str) -> Any:
    if _CYPHER_DENY.search(cypher):
        return {"error": "read-only cypher: write clauses are rejected"}
    try:
        from ...core.db.neo4j import driver
    except Exception:
        return {"error": "graph store unavailable"}

    # the agent writes a MATCH pattern; we mount it in an org-anchored read transaction
    query = cypher.strip().rstrip(";")

    def _read(tx):
        return [dict(rec) for rec in tx.run(query, org=str(ctx.org_id))][:CYPHER_ROW_CAP]

    try:
        d = driver()
        if d is None:
            return {"error": "graph store unavailable"}
        with d.session() as session:
            rows = session.execute_read(_read)
        return {"n_rows": len(rows), "rows": rows}
    except Exception as exc:
        return {"error": f"cypher failed: {str(exc)[:200]}"}


async def tool_storage_catalog(ctx: FlowContext, prefix: str = "") -> Any:
    stmt = select(BlobNote).where(BlobNote.org_id == ctx.org_id,
                                  BlobNote.project_id == ctx.project_id)
    if prefix:
        stmt = stmt.where(BlobNote.key.startswith(prefix))
    rows = (await ctx.session.execute(stmt.order_by(BlobNote.created_at.desc()).limit(50))
            ).scalars().all()
    return [{"key": r.key, "kind": r.kind, "size": r.size, "description": r.description}
            for r in rows]


async def tool_read_blob(ctx: FlowContext, key: str, mode: str = "excerpt") -> Any:
    note = (await ctx.session.execute(
        select(BlobNote).where(BlobNote.org_id == ctx.org_id, BlobNote.key == key)
    )).scalar_one_or_none()
    if note is None:
        return {"error": "unknown blob key (only catalogued blobs are readable)"}
    try:
        body = get_blob_store().get(key)
    except Exception as exc:
        return {"error": f"blob read failed: {str(exc)[:120]}"}
    text = body.decode("utf-8", errors="replace")
    if mode != "full":
        return {"key": key, "description": note.description, "excerpt": text[:EXCERPT_CHARS],
                "total_chars": len(text)}
    return {"key": key, "description": note.description, "content": text[:20_000]}


async def note_blob(session: Any, *, org_id: Any, project_id: Any, key: str, kind: str,
                    size: int, description: str, source: str = "") -> None:
    """Catalog a stored blob (idempotent on key) — the cheap-browse backbone."""
    existing = (await session.execute(
        select(BlobNote).where(BlobNote.org_id == org_id, BlobNote.key == key)
    )).scalar_one_or_none()
    if existing is not None:
        existing.description = description[:500] or existing.description
        existing.size = size
        return
    session.add(BlobNote(org_id=org_id, project_id=project_id, key=key, kind=kind[:40],
                         size=size, description=description[:500], source=source[:300]))

