# Laboratree — WebSearch + Retrieval MCP

A standalone **MCP server** that turns web + scholarly search and retrieval into a small set of
intelligent verbs. Any MCP client (Claude Desktop, the Laboratree Research Director, LangGraph,
your own agent framework) can plug it in — the caller never learns which providers ran.

## Tools

| Tool | What it does |
|------|--------------|
| `deep_search` | Expand the query, fan out across web + scholarly + arXiv + community, then **merge, dedup, and rank**. Each result carries its providers + a confidence score. |
| `academic_search` | OpenAlex + Semantic Scholar + arXiv, papers first. |
| `web_search` | General web (Brave → SerpAPI fallback). |
| `find_dataset` | Search for downloadable datasets; flags direct-download URLs. |
| `fetch_and_read` | SSRF-guarded fetch of one page → readable text + link inventory (PDFs read as text). |
| `open_access_pdf` | Resolve a URL/DOI to an open-access PDF (OpenAlex → Unpaywall → arXiv/PMC). |
| `retrieve` | **DB-free hybrid retrieval** — BM25 + optional dense embeddings, fused with RRF — over documents you supply. |

Every response is version-stamped and carries `_meta` (server, version, query, providers used) —
the **Capability Contract**: stable schema · provenance on every item · confidence scores.

## Run it

```bash
# from the repo root (uv workspace)
uv run laboratree-search-mcp          # stdio transport
```

## Connect it (any MCP client)

```jsonc
{
  "mcpServers": {
    "laboratree-search": {
      "command": "uv",
      "args": ["run", "laboratree-search-mcp"]
    }
  }
}
```

## Configuration

Providers are keyless where possible (OpenAlex, Semantic Scholar, arXiv). Optional keys live in
the app's `.env` and raise limits / add providers:

- `BRAVE_SEARCH_API_KEY` / `SERPAPI_KEY` — web search
- `SEMANTIC_SCHOLAR_API_KEY` — higher scholarly limits
- an embedding backend (`LLM_PROVIDER` + key) — enables the dense retrieval leg

No datastore is required: `retrieve` ranks in-memory, so this server runs anywhere.
