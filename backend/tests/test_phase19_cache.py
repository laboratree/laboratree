"""Caching tests: sync TTL memos (search providers) + cached catalog endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from laboratree.core.cache import clear_all_memos, memoize_ttl
from laboratree.core.config import settings
from laboratree.main import app


def test_memoize_ttl_dedupes_within_ttl_and_expires(monkeypatch):
    calls = {"n": 0}

    @memoize_ttl(60)
    def compute(q: str) -> list[str]:
        calls["n"] += 1
        return [q, str(calls["n"])]

    assert compute("a") == compute("a") == ["a", "1"]
    assert calls["n"] == 1                              # second call served from the memo
    assert compute("b") == ["b", "2"]                   # different args -> new computation

    import laboratree.core.cache as cache_mod
    base = cache_mod.time.monotonic()
    monkeypatch.setattr(cache_mod.time, "monotonic", lambda: base + 61)
    assert compute("a") == ["a", "3"]                   # TTL elapsed -> recomputed


def test_memoize_respects_disable_and_clear(monkeypatch):
    calls = {"n": 0}

    @memoize_ttl(60)
    def compute() -> int:
        calls["n"] += 1
        return calls["n"]

    monkeypatch.setattr(settings, "cache_enabled", False)
    assert compute() == 1 and compute() == 2            # disabled -> always live

    monkeypatch.setattr(settings, "cache_enabled", True)
    assert compute() == 3 and compute() == 3            # enabled -> memoized
    clear_all_memos()
    assert compute() == 4                               # cleared -> recomputed


def test_search_provider_is_memoized(monkeypatch):
    import laboratree.core.search as S

    calls = {"n": 0}

    def _fake_brave(query: str, count: int):
        calls["n"] += 1
        return [S.SearchHit(title="T", url="https://x", description="", source="brave")]

    monkeypatch.setattr(settings, "web_search_provider", "brave")
    monkeypatch.setattr(settings, "brave_search_api_key", "k")
    monkeypatch.setattr(S, "_brave", _fake_brave)
    monkeypatch.setitem(S._PROVIDERS, "brave", _fake_brave)

    first = S.web_search("same query", count=3)
    second = S.web_search("same query", count=3)
    assert first == second and calls["n"] == 1          # one provider hit for repeated queries
    S.web_search("different query", count=3)
    assert calls["n"] == 2


def test_catalog_endpoints_stay_correct_with_caching():
    with TestClient(app) as client:
        a = client.get("/api/components").json()
        b = client.get("/api/components").json()
        assert a["count"] == b["count"] > 0             # cached or not, same correct shape
        flows_a = client.get("/api/flows").json()["flows"]
        flows_b = client.get("/api/flows").json()["flows"]
        assert flows_a == flows_b
        assert {f["key"] for f in flows_a} >= {"research", "policy-research", "market-research"}
