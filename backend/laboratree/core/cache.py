"""Redis-backed result cache for expensive, deterministic-enough operations (evidence hunt, data
hunt) — so repeating a hypothesis doesn't re-pay for the searches + LLM calls.

Keys are hashed from the normalized inputs; values are JSON. **Fails open**: any Redis error (or
caching disabled) simply computes the result live. Only cache READ-ONLY work — never operations with
side effects (creating datasets/papers/runs).
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from .config import settings

log = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _enabled() -> bool:
    # cache_enabled is the switch; the legacy ideation flag still disables when explicitly off
    return settings.cache_enabled and settings.ideation_cache_enabled


# process-local TTL memos (for SYNC hot paths like search providers); registered so tests can
# wipe them between cases
_MEMO_STORES: list[dict[str, tuple[float, Any]]] = []


def memoize_ttl(ttl_s: float, maxsize: int = 256) -> Callable[[F], F]:
    """In-process TTL memo for synchronous, read-only functions (e.g. search providers).

    Fail-open: unhashable inputs or a disabled cache just call through. On overflow the store
    resets wholesale (simple + predictable beats LRU bookkeeping here).
    """

    def _decorate(fn: F) -> F:
        store: dict[str, tuple[float, Any]] = {}
        _MEMO_STORES.append(store)

        @functools.wraps(fn)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _enabled():
                return fn(*args, **kwargs)
            try:
                key = repr((args, sorted(kwargs.items())))
            except Exception:
                return fn(*args, **kwargs)
            now = time.monotonic()
            hit = store.get(key)
            if hit is not None and now - hit[0] < ttl_s:
                return hit[1]
            result = fn(*args, **kwargs)
            if len(store) >= maxsize:
                store.clear()
            store[key] = (now, result)
            return result

        return _wrapper  # type: ignore[return-value]

    return _decorate


def clear_all_memos() -> None:
    """Wipe every in-process memo (test hygiene between cases)."""
    for store in _MEMO_STORES:
        store.clear()


def cache_key(bucket: str, project_id: Any, *parts: Any) -> str:
    """Stable key from a bucket + project + the inputs that define the result."""
    raw = json.dumps(parts, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return f"cache:{bucket}:{project_id}:{digest}"


async def cache_get(key: str) -> Any | None:
    if not _enabled():
        return None
    try:
        from .db.redis import client

        raw = await client().get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        log.info("cache read failed (%s); computing live", exc)
        return None


async def cache_set(key: str, value: Any, ttl_s: int) -> None:
    if not _enabled():
        return
    try:
        from .db.redis import client

        await client().set(key, json.dumps(value, default=str), ex=ttl_s)
    except Exception as exc:
        log.info("cache write failed (%s); ignoring", exc)


async def cached_json(key: str, ttl_s: int, compute: Callable[[], Awaitable[Any]]) -> Any:
    """Return the cached value for `key`, else run `compute()`, cache it, and return it. Transparent —
    the caller gets the same shape whether hit or miss."""
    hit = await cache_get(key)
    if hit is not None:
        return hit
    result = await compute()
    await cache_set(key, result, ttl_s)
    return result


__all__ = ["cache_get", "cache_key", "cache_set", "cached_json",
           "memoize_ttl", "clear_all_memos"]
