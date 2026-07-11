"""Agent toolbelt tests: catalog completeness, availability gating, facades, phase buckets."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from laboratree.agents.flow import FlowContext
from laboratree.agents.tools import TOOLBELT, AgentTool, available_tools, toolbelt_prompt

EXPECTED_TOOLS = {
    "web_search", "research_search", "arxiv_search", "reddit_search", "open_access_pdf",
    "extract_document", "ocr_pdf", "ocr_image", "profile_dataset", "detect_task",
    "run_component", "sandbox_run",
    # grounding + data-access additions (agentic platform v2)
    "fetch_page", "crawl", "component_spec", "knowledge_search", "index_text",
    "dataset_overview", "query_dataset_sql", "query_cypher", "storage_catalog", "read_blob",
}


def test_toolbelt_catalog_is_complete_and_typed():
    assert set(TOOLBELT) == EXPECTED_TOOLS
    for tool in TOOLBELT.values():
        assert isinstance(tool, AgentTool)
        assert tool.description and tool.params_hint.startswith("{")


def test_available_tools_gates_on_availability():
    always = {name: t for name, t in TOOLBELT.items()
              if name in ("open_access_pdf", "extract_document", "profile_dataset",
                          "detect_task", "run_component")}
    # ungated tools are always offered
    assert set(always) <= set(available_tools())
    # a probe that raises must exclude the tool, never break discovery
    broken = AgentTool("boom", "x", "{}", lambda: None, available=lambda: 1 / 0)
    assert "boom" not in available_tools({**TOOLBELT, "boom": broken})


def test_toolbelt_prompt_renders_names_and_hints():
    prompt = toolbelt_prompt(TOOLBELT)
    assert "- web_search:" in prompt and 'args={"query": str' in prompt
    assert "- run_component:" in prompt


def test_facades_call_through_to_the_real_capability(monkeypatch):
    import laboratree.core.search as search_mod

    calls: list[str] = []

    class Hit:
        def __init__(self):
            self.__dict__.update(title="T", url="u", snippet="s")

    monkeypatch.setattr(search_mod, "web_search",
                        lambda q, count=None: calls.append(q) or [Hit()])
    hits = TOOLBELT["web_search"].fn("dropout drivers", count=2)
    assert calls == ["dropout drivers"]
    assert hits[0]["title"] == "T"


def test_arxiv_search_parses_atom_and_fails_open(monkeypatch):
    import httpx
    from laboratree.core.search import arxiv_search

    atom = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><title>Dropout  Drivers</title><id>http://arxiv.org/abs/2401.0001</id>
        <summary>Distance   matters.</summary></entry>
    </feed>"""

    def _fake_get(url, **kw):
        assert "export.arxiv.org" in url
        return httpx.Response(200, text=atom, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", _fake_get)
    hits = arxiv_search("dropout", 5)
    assert hits[0].title == "Dropout Drivers" and hits[0].source == "arxiv"
    assert hits[0].description == "Distance matters."

    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(OSError("down")))
    # different query (providers are TTL-memoized) — provider down -> fail-open, never raises
    assert arxiv_search("attendance", 5) == []


def test_reddit_search_parses_listing_and_fails_open(monkeypatch):
    import httpx
    from laboratree.core.search import reddit_search

    listing = {"data": {"children": [{"data": {
        "title": "Why kids skip school", "permalink": "/r/education/comments/x1/",
        "subreddit": "education", "score": 42, "num_comments": 7, "selftext": "distance + cost",
    }}]}}

    def _fake_get(url, **kw):
        assert "reddit.com/search.json" in url
        return httpx.Response(200, json=listing, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", _fake_get)
    hits = reddit_search("school dropout", count=5)
    assert hits[0].url == "https://www.reddit.com/r/education/comments/x1/"
    assert "r/education · 42 points" in hits[0].description
    assert hits[0].source == "reddit"

    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(
        429, request=httpx.Request("GET", "x")))
    assert reddit_search("anything") == []             # rate-limited -> empty, never raises


def test_flow_context_bucket_is_per_flow_per_stage():
    run = MagicMock()
    run.id = uuid.UUID("00000000-0000-0000-0000-00000000abcd")
    ctx = FlowContext(session=MagicMock(), org_id=uuid.uuid4(), project_id=uuid.uuid4(),
                      flow_run=run)
    assert ctx.bucket("intake") == f"flows/{run.id}/intake/"
    assert ctx.bucket("impact") != ctx.bucket("intake")
