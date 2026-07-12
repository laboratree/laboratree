"""WebSearch + Retrieval Intelligence — an MCP server.

Exposes intelligent verbs (``deep_search``, ``academic_search``, ``find_dataset``,
``fetch_and_read``, ``open_access_pdf``, ``retrieve``) over a strong, multi-provider search
belt. The caller never learns which providers ran: ``deep_search`` expands the query, fans out
to web + scholarly + arXiv + community sources, then merges, deduplicates and ranks — every
result carries its provenance and a confidence score. ``retrieve`` adds DB-free hybrid ranking
so any agent framework gets discovery AND retrieval from one server.

Capability Contract: stable typed results · provenance on every item · confidence scores ·
version-stamped responses. Transport: stdio (connect from any MCP client).
"""

from __future__ import annotations

import asyncio
from typing import Annotated, Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from mcp.server.fastmcp import FastMCP
from pydantic import Field

SERVER_VERSION = "0.1.0"
_TRACKING = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")
ACADEMIC_SOURCES = {"openalex", "semantic_scholar", "arxiv", "crossref", "pubmed"}

mcp = FastMCP("laboratree-search")


# ----------------------------- helpers -----------------------------

def _canonical(url: str) -> str:
    try:
        parts = urlsplit(url.strip())
    except Exception:
        return url.strip().lower()
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query)
                       if not any(k.lower().startswith(t) for t in _TRACKING)])
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(),
                       (parts.path or "/").rstrip("/") or "/", query, "")).lower()


def _hit_dict(hit: Any) -> dict[str, Any]:
    return {"title": getattr(hit, "title", ""), "url": getattr(hit, "url", ""),
            "snippet": getattr(hit, "description", "")[:500],
            "provider": getattr(hit, "source", "") or "web"}


def _meta(query: str, **extra: Any) -> dict[str, Any]:
    return {"server": "laboratree-search", "version": SERVER_VERSION, "query": query, **extra}


def _expand_query(query: str) -> list[str]:
    """Query expansion (synonyms / related terms). LLM when configured, else just the query."""
    try:
        from laboratree.labs.agentic import llm as agentic_llm

        if not agentic_llm.is_configured():
            return [query]
        raw = agentic_llm.default_complete(
            "Expand a search query for maximum recall. Return ONLY a JSON list of 2-4 alternative "
            "phrasings (synonyms, acronyms, related terminology) — no prose.",
            query, role="generation")
        from laboratree.core.jsonparse import loads_lenient

        extra = [str(q) for q in (loads_lenient(raw) or []) if isinstance(q, str)][:4]
        return [query, *(q for q in extra if q.lower() != query.lower())]
    except Exception:
        return [query]


def _merge_rank(groups: list[list[Any]], max_results: int) -> list[dict[str, Any]]:
    """Dedup by canonical URL and rank by provider agreement + scholarly + position."""
    merged: dict[str, dict[str, Any]] = {}
    for hits in groups:
        for pos, hit in enumerate(hits):
            d = _hit_dict(hit)
            if not d["url"]:
                continue
            key = _canonical(d["url"])
            entry = merged.get(key)
            if entry is None:
                merged[key] = {**d, "providers": {d["provider"]}, "_best_pos": pos}
            else:
                entry["providers"].add(d["provider"])
                entry["_best_pos"] = min(entry["_best_pos"], pos)
                if len(d["snippet"]) > len(entry["snippet"]):
                    entry["snippet"] = d["snippet"]
    ranked = []
    for entry in merged.values():
        providers = entry.pop("providers")
        agreement = len(providers)
        scholarly = any(p in ACADEMIC_SOURCES for p in providers)
        position = 1.0 / (1 + entry.pop("_best_pos"))
        score = agreement + (0.5 if scholarly else 0.0) + position
        entry["providers"] = sorted(providers)
        entry["confidence"] = round(min(1.0, score / 3.5), 3)
        entry["score"] = round(score, 3)
        ranked.append(entry)
    ranked.sort(key=lambda e: e["score"], reverse=True)
    return ranked[:max_results]


async def _to_thread(fn, *args):
    return await asyncio.to_thread(fn, *args)


# ----------------------------- tools -----------------------------

@mcp.tool()
async def deep_search(
    query: Annotated[str, Field(description="What to find — a natural-language research query")],
    max_results: Annotated[int, Field(ge=1, le=40, description="Max merged results")] = 12,
    sources: Annotated[list[str] | None, Field(
        description="Any of: web, academic, arxiv, reddit (default: web+academic+arxiv)")] = None,
    expand: Annotated[bool, Field(description="Expand the query for higher recall")] = True,
) -> dict[str, Any]:
    """Deep, multi-provider search: expand the query, fan out across web + scholarly + arXiv +
    community sources, then merge, deduplicate and rank. Every result carries its providers and
    a confidence score; you never need to know which engines ran."""
    from laboratree.core.search import (
        arxiv_search,
        reddit_search,
        research_search,
        web_search,
    )

    queries = _expand_query(query) if expand else [query]
    per = max(3, max_results // max(1, len(queries)))
    groups: list[list[Any]] = []
    chosen = set(sources or ["web", "academic", "arxiv"])
    for q in queries:
        if "web" in chosen:
            groups.append(await _to_thread(web_search, q, per))
        if "academic" in chosen:
            groups.append(await _to_thread(research_search, q, per))
        if "arxiv" in chosen:
            groups.append(await _to_thread(arxiv_search, q, per))
        if "reddit" in chosen:
            groups.append(await _to_thread(reddit_search, q, per))
    results = _merge_rank(groups, max_results)
    return {"results": results, "count": len(results),
            "_meta": _meta(query, expanded_queries=queries, sources=sorted(chosen))}


@mcp.tool()
async def academic_search(
    query: Annotated[str, Field(description="Scholarly query")],
    max_results: Annotated[int, Field(ge=1, le=40)] = 12,
) -> dict[str, Any]:
    """Scholarly search across OpenAlex, Semantic Scholar and arXiv (papers first), merged and
    ranked with provenance."""
    from laboratree.core.search import arxiv_search, research_search

    groups = [await _to_thread(research_search, query, max_results),
              await _to_thread(arxiv_search, query, max_results)]
    results = _merge_rank(groups, max_results)
    return {"results": results, "count": len(results),
            "_meta": _meta(query, sources=["openalex", "semantic_scholar", "arxiv"])}


@mcp.tool()
async def web_search(
    query: Annotated[str, Field(description="Web query")],
    max_results: Annotated[int, Field(ge=1, le=20)] = 8,
) -> dict[str, Any]:
    """General web search (Brave with SerpAPI fallback), results with provenance."""
    from laboratree.core.search import web_search as _web

    hits = await _to_thread(_web, query, max_results)
    return {"results": [_hit_dict(h) for h in hits], "count": len(hits), "_meta": _meta(query)}


@mcp.tool()
async def find_dataset(
    query: Annotated[str, Field(description="The kind of dataset you need")],
    max_results: Annotated[int, Field(ge=1, le=20)] = 10,
) -> dict[str, Any]:
    """Find downloadable datasets — searches scholarly + web and flags direct data URLs."""
    from laboratree.core.search import looks_like_data_url, research_search
    from laboratree.core.search import web_search as _web

    hits = (await _to_thread(research_search, f"{query} dataset", max_results)
            + await _to_thread(_web, f"{query} dataset download", max_results))
    out = []
    seen = set()
    for h in hits:
        d = _hit_dict(h)
        key = _canonical(d["url"])
        if not d["url"] or key in seen:
            continue
        seen.add(key)
        d["direct_download"] = looks_like_data_url(d["url"])
        out.append(d)
    out.sort(key=lambda e: (not e["direct_download"]))
    return {"results": out[:max_results], "count": len(out[:max_results]), "_meta": _meta(query)}


@mcp.tool()
async def fetch_and_read(
    url: Annotated[str, Field(description="Absolute http(s) URL — HTML or PDF")],
) -> dict[str, Any]:
    """Fetch ONE page (SSRF-guarded) and return readable text + its link inventory. PDFs are
    read as text, not bytes."""
    from laboratree.core.net import extract_links, html_to_text, pdf_to_text, safe_fetch

    body = await _to_thread(safe_fetch, url)
    if not body:
        return {"error": "fetch blocked or failed (SSRF guard / size cap / network)",
                "url": url, "_meta": _meta(url)}
    is_pdf = body.lstrip()[:5].startswith(b"%PDF")
    text = (await _to_thread(pdf_to_text, body)) if is_pdf else html_to_text(body)
    links = [] if is_pdf else extract_links(body, url)[:40]
    return {"url": url, "kind": "pdf" if is_pdf else "html", "text": text[:12000],
            "links": links, "truncated": len(text) > 12000, "_meta": _meta(url)}


@mcp.tool()
async def open_access_pdf(
    url_or_doi: Annotated[str, Field(description="A paper URL, landing page, or DOI")],
) -> dict[str, Any]:
    """Resolve a paper URL/DOI to a downloadable open-access PDF (OpenAlex → Unpaywall →
    arXiv/PMC)."""
    from laboratree.core.search import open_access_pdf as _oa

    pdf_url = await _to_thread(_oa, url_or_doi)
    return {"pdf_url": pdf_url, "found": bool(pdf_url), "_meta": _meta(url_or_doi)}


@mcp.tool()
async def retrieve(
    query: Annotated[str, Field(description="What to rank the documents against")],
    documents: Annotated[list[str], Field(description="Candidate passages/documents to rank")],
    k: Annotated[int, Field(ge=1, le=50, description="How many top passages to return")] = 6,
) -> dict[str, Any]:
    """DB-free hybrid retrieval: rank the supplied documents against the query with BM25 (plus a
    dense leg when an embedding backend is configured), fused with Reciprocal Rank Fusion. Bring
    documents from anywhere — search results, files, a corpus — and get the most relevant back."""
    from .retrieval import hybrid_retrieve

    embed_fn = None
    try:
        from laboratree.core.llm import get_llm

        client = get_llm()
        if client.configured():
            embed_fn = client.embed
    except Exception:
        embed_fn = None

    ranked = await asyncio.to_thread(hybrid_retrieve, query, documents, k=k, embed_fn=embed_fn)
    return {"results": [{"ordinal": r.ordinal, "text": r.text[:2000], "score": r.score,
                         "lexical_rank": r.lexical_rank, "dense_rank": r.dense_rank}
                        for r in ranked],
            "count": len(ranked), "dense_used": embed_fn is not None, "_meta": _meta(query)}


def main() -> None:
    """Entrypoint — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
