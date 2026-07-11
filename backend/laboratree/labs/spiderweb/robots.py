"""robots.txt discipline — SpiderWeb honors Disallow for our user agent (cached per domain)."""

from __future__ import annotations

import logging
import urllib.robotparser
from urllib.parse import urlsplit

from ...core.cache import memoize_ttl
from ...core.net import safe_fetch

log = logging.getLogger(__name__)

USER_AGENT = "Laboratree"
ROBOTS_TTL_S = 3600.0


@memoize_ttl(ROBOTS_TTL_S)
def _parser_for(scheme_host: str) -> urllib.robotparser.RobotFileParser | None:
    parser = urllib.robotparser.RobotFileParser()
    body = safe_fetch(f"{scheme_host}/robots.txt", timeout=8.0, max_bytes=256 * 1024)
    if body is None:
        return None                          # unreachable robots -> default allow
    try:
        parser.parse(body.decode("utf-8", errors="replace").splitlines())
        return parser
    except Exception as exc:
        log.debug("robots parse failed for %s: %s", scheme_host, exc)
        return None


def allowed(url: str) -> bool:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return False
    parser = _parser_for(f"{parts.scheme}://{parts.netloc}")
    if parser is None:
        return True
    try:
        return parser.can_fetch(USER_AGENT, url)
    except Exception:
        return True


__all__ = ["allowed", "USER_AGENT"]
