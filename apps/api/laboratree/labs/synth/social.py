"""Persona social network (pure) — homophily graph + neighbour influence.

Personas who share attributes are more likely to be connected (homophily). During a survey wave a
persona sees what its neighbours answered *last* wave, so opinions diffuse through the network —
the "social influence / network effects" a graph of personas is meant to capture. Edges are the
source of truth in Postgres; Neo4j mirrors them best-effort for graph queries.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any

log = logging.getLogger(__name__)

DEFAULT_AVG_DEGREE = 4


def _similarity(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Fraction of shared attribute (key, value) pairs — a simple homophily score in [0, 1]."""
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    shared = sum(1 for k in keys if a.get(k) == b.get(k) and k in a and k in b)
    return shared / len(keys)


def build_social_graph(
    personas: list[dict[str, Any]], *, avg_degree: int = DEFAULT_AVG_DEGREE
) -> list[dict[str, Any]]:
    """Undirected homophily graph: each persona links to its most-similar peers (deterministic).

    Returns edges ``[{a, b, weight}]`` with ``a < b`` by handle (deduped). ``weight`` = similarity
    (falls back to a small constant when personas share no attributes, so the graph stays connected).
    """
    handles = [str(p.get("handle") or p.get("id")) for p in personas]
    by_handle = {h: p for h, p in zip(handles, personas, strict=True)}
    k = max(1, min(avg_degree, len(personas) - 1)) if len(personas) > 1 else 0
    edges: dict[tuple[str, str], float] = {}
    for h in handles:
        ranked = sorted(
            (o for o in handles if o != h),
            key=lambda o: (-_similarity(by_handle[h].get("attributes") or {},
                                        by_handle[o].get("attributes") or {}), o),
        )
        for other in ranked[:k]:
            key = (h, other) if h < other else (other, h)
            weight = _similarity(by_handle[h].get("attributes") or {},
                                 by_handle[other].get("attributes") or {})
            edges[key] = max(edges.get(key, 0.0), round(weight or 0.05, 3))
    return [{"a": a, "b": b, "weight": w} for (a, b), w in sorted(edges.items())]


def neighbours(handle: str, edges: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for e in edges:
        if e["a"] == handle:
            out.append(e["b"])
        elif e["b"] == handle:
            out.append(e["a"])
    return out


def neighbour_opinion(
    handle: str, edges: list[dict[str, Any]], last_answers: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """The modal answer among a persona's neighbours, per question (from their last wave)."""
    neigh = neighbours(handle, edges)
    tallies: dict[str, Counter[Any]] = {}
    for n in neigh:
        for qid, value in (last_answers.get(n) or {}).items():
            key = tuple(value) if isinstance(value, list) else value
            tallies.setdefault(qid, Counter())[key] += 1
    return {qid: counter.most_common(1)[0][0] for qid, counter in tallies.items() if counter}


def social_context(opinion: dict[str, Any]) -> str:
    """Render neighbour opinion as a prompt line (empty when there is nothing to say)."""
    if not opinion:
        return ""
    parts = ", ".join(f"{qid}={value}" for qid, value in opinion.items())
    return f"Most people in your social circle answered: {parts}. You may be influenced by them.\n\n"


__all__ = ["build_social_graph", "neighbours", "neighbour_opinion", "social_context"]
