"""The typed tool belt agents consume — thin facades over existing capabilities.

Every entry wraps a function that already exists elsewhere (core/search, paper ingest, OCR,
auto-experiment planning, the sandbox, the Evidence-locked component executor). No logic lives
here: this module only gives agents one typed, discoverable catalog and a prompt rendering of it.
Availability-gated tools (OCR, sandbox, search) declare themselves so an agent never plans around
a capability the host lacks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

MAX_PROMPT_TOOLS = 20


@dataclass(frozen=True)
class AgentTool:
    name: str
    description: str
    params_hint: str                       # what to put in the ReAct "args" object
    fn: Callable[..., Any]
    available: Callable[[], bool] = lambda: True


def _web_search(query: str, count: int = 6) -> list[dict[str, Any]]:
    from ...core.search import web_search

    return [hit.__dict__ for hit in web_search(query, count=count)]


def _research_search(query: str, count: int = 6) -> list[dict[str, Any]]:
    from ...core.search import research_search

    return [hit.__dict__ for hit in research_search(query, count=count)]


def _arxiv_search(query: str, count: int = 6) -> list[dict[str, Any]]:
    from ...core.search import arxiv_search

    return [hit.__dict__ for hit in arxiv_search(query, count)]


def _reddit_search(query: str, count: int = 6) -> list[dict[str, Any]]:
    from ...core.search import reddit_search

    return [hit.__dict__ for hit in reddit_search(query, count=count)]


def _open_access_pdf(url: str) -> str | None:
    from ...core.search import open_access_pdf

    return open_access_pdf(url)


def _extract_document(filename: str, data: bytes) -> str:
    from ...labs.paper.ingest import extract_paper_text

    return extract_paper_text(filename, data)


def _ocr_pdf(pdf_bytes: bytes) -> list[str]:
    from ...ocr.service import ocr_pdf_pages

    return ocr_pdf_pages(pdf_bytes)


def _ocr_image(image_bytes: bytes) -> str:
    from ...ocr.service import ocr_image_bytes

    return ocr_image_bytes(image_bytes)


def _profile_dataset(df: Any, target: str) -> dict[str, Any]:
    from ...labs.ideation.auto_experiment import profile_dataset

    return profile_dataset(df, target)


def _detect_task(df: Any, target: str) -> str:
    from ...labs.ideation.auto_experiment import detect_task

    return detect_task(df, target)


def _search_ok() -> bool:
    from ...core.search import search_available

    return search_available()


def _research_ok() -> bool:
    from ...core.search import research_available

    return research_available()


def _ocr_ok() -> bool:
    from ...ocr.service import ocr_available

    return ocr_available()


def _sandbox_ok() -> bool:
    from ..sandbox import is_available

    return is_available()


def _sandbox_run(code: str, **kw: Any) -> Any:
    from ..sandbox import run_code

    return run_code(code, **kw)


TOOLBELT: dict[str, AgentTool] = {
    tool.name: tool
    for tool in (
        AgentTool("web_search", "Search the public web; returns ranked hits (title/url/snippet).",
                  '{"query": str, "count"?: int}', _web_search, _search_ok),
        AgentTool("research_search",
                  "Search scholarly databases (OpenAlex/Semantic Scholar) then the web; "
                  "returns papers first, DOI-deduped.",
                  '{"query": str, "count"?: int}', _research_search, _research_ok),
        AgentTool("arxiv_search", "Search arXiv preprints (keyless).",
                  '{"query": str, "count"?: int}', _arxiv_search),
        AgentTool("reddit_search",
                  "Search Reddit's public API — consumer/community sentiment and opinions.",
                  '{"query": str, "count"?: int}', _reddit_search),
        AgentTool("open_access_pdf", "Resolve a paper URL/DOI to a downloadable open-access PDF.",
                  '{"url": str}', _open_access_pdf),
        AgentTool("extract_document", "Extract text from a PDF/DOCX/image document (OCR fallback).",
                  '{"filename": str, "data": bytes}', _extract_document),
        AgentTool("ocr_pdf", "OCR a scanned PDF into per-page text.",
                  '{"pdf_bytes": bytes}', _ocr_pdf, _ocr_ok),
        AgentTool("ocr_image", "OCR one image into text.",
                  '{"image_bytes": bytes}', _ocr_image, _ocr_ok),
        AgentTool("profile_dataset", "Profile a dataframe: dtypes, missingness, cardinality.",
                  '{"df": dataset, "target": str}', _profile_dataset),
        AgentTool("detect_task", "Classify the modelling task for a dataframe + target.",
                  '{"df": dataset, "target": str}', _detect_task),
        AgentTool("run_component",
                  "Execute ANY registered component as an Evidence-locked run "
                  "(the universal analysis/model/transform tool).",
                  '{"component_id": str, "params": dict}', lambda: None),  # bound per-run
        AgentTool("sandbox_run", "Run Python in the no-network Docker sandbox.",
                  '{"code": str}', _sandbox_run, _sandbox_ok),
    )
}


def available_tools(catalog: dict[str, AgentTool] | None = None) -> dict[str, AgentTool]:
    """Only the tools this host can actually perform right now."""
    out: dict[str, AgentTool] = {}
    for name, tool in (catalog or TOOLBELT).items():
        try:
            if tool.available():
                out[name] = tool
        except Exception:  # availability probes must never break tool discovery
            continue
    return out


def toolbelt_prompt(tools: dict[str, AgentTool] | None = None) -> str:
    """Render the catalog for an agent's system prompt."""
    chosen = list((tools or available_tools()).values())[:MAX_PROMPT_TOOLS]
    return "\n".join(f"- {t.name}: {t.description} args={t.params_hint}" for t in chosen)


__all__ = ["AgentTool", "TOOLBELT", "available_tools", "toolbelt_prompt"]
