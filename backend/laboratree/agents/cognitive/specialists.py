"""Specialist sub-agents — research / coding / analysis, each with its own tool scope + persona.

The meta-planner assigns every task an agent_type; the orchestrator then hands the sub-agent
EXACTLY that scope (a research agent cannot run sandbox code; an analysis agent cannot crawl).
"""

from __future__ import annotations

from ..tools import AgentTool

SPECIALIST_TOOLS: dict[str, tuple[str, ...]] = {
    "research": ("knowledge_search", "web_search", "research_search", "arxiv_search",
                 "reddit_search", "open_access_pdf", "fetch_page", "crawl", "index_text",
                 "storage_catalog", "read_blob"),
    "coding": ("sandbox_run", "run_component", "component_spec", "dataset_overview",
               "query_dataset_sql", "storage_catalog", "read_blob"),
    "analysis": ("dataset_overview", "query_dataset_sql", "query_cypher", "run_component",
                 "component_spec", "knowledge_search", "storage_catalog", "read_blob"),
}

SPECIALIST_PERSONAS: dict[str, str] = {
    "research": ("You are the Research specialist of a provenance-locked research platform: "
                 "find, verify and cite external evidence — scholarly sources first."),
    "coding": ("You are the Coding specialist of a provenance-locked research platform: "
               "inspect specs and data BEFORE running components or sandbox code; report "
               "exactly what ran and what it produced."),
    "analysis": ("You are the Analysis specialist of a provenance-locked research platform: "
                 "query the project's data directly (SQL/Cypher/components) — every number you "
                 "report must come from an observation."),
}


def specialist_tools(agent_type: str,
                     tools: dict[str, AgentTool]) -> dict[str, AgentTool]:
    """Intersect the run's toolbelt with the specialist's scope; unknown type → full belt."""
    scope = SPECIALIST_TOOLS.get(agent_type)
    if not scope:
        return tools
    scoped = {n: tools[n] for n in scope if n in tools}
    return scoped or tools


def specialist_persona(agent_type: str, default: str = "") -> str:
    return SPECIALIST_PERSONAS.get(agent_type, default)


__all__ = ["SPECIALIST_TOOLS", "SPECIALIST_PERSONAS", "specialist_tools", "specialist_persona"]
