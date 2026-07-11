"""Seed discovery — a mission without seed URLs finds its own starting points.

The navigator asks the platform's whole search belt (web search, scholarly search, reddit)
for candidate pages, dedupes them, and ranks by objective-term overlap — the same scoring the
crawler applies to links. Availability-gated and fail-open per provider: whatever is
configured contributes; nothing configured → empty list (the mission then fails honestly,
telling the user to add seeds or a search key).
"""

from __future__ import annotations

import logging

from ...core import search as search_belt

log = logging.getLogger(__name__)

MAX_SEEDS = 5
_PROVIDERS: tuple[tuple[str, int], ...] = (
    ("web_search", 6), ("research_search", 4), ("reddit_search", 3))


def discover_seeds(objective: str, *, max_seeds: int = MAX_SEEDS) -> list[str]:
    hits = []
    for name, count in _PROVIDERS:
        try:
            hits.extend(getattr(search_belt, name)(objective, count))
        except Exception as exc:  # one dead provider must not kill discovery
            log.info("seed discovery provider %s failed: %s", name, exc)
    terms = {t for t in objective.lower().split() if len(t) > 3}

    def _score(hit) -> int:
        return sum(t in f"{hit.title} {hit.description} {hit.url}".lower() for t in terms)

    seeds: list[str] = []
    seen: set[str] = set()
    for hit in sorted(hits, key=_score, reverse=True):
        url = (hit.url or "").strip()
        key = url.split("#")[0].rstrip("/").lower()
        if not url.startswith(("http://", "https://")) or key in seen:
            continue
        seen.add(key)
        seeds.append(url)
        if len(seeds) >= max_seeds:
            break
    return seeds


__all__ = ["discover_seeds", "MAX_SEEDS"]
