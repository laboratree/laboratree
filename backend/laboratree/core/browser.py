"""Browser engine — the SpiderWeb Lab's hands, availability-gated like OCR/sandbox.

``PlaywrightBrowser`` (optional dependency: ``uv add playwright`` + ``playwright install
chromium``) drives real pages: JS executes, clicks navigate, redirects resolve. Hosts without it
degrade to ``HttpBrowser`` (SSRF-guarded static fetch + link inventory) — honest static mode.

READ-ONLY WEB LAW (both engines): no form filling, no logins, no POSTs — navigation only; every
hop re-validates the SSRF guard; non-http(s) and private hosts are blocked at request level.
"""

from __future__ import annotations

import logging
from typing import Protocol

from .net import LinkInfo, extract_links, html_to_text, is_public_http_url, pdf_to_text, safe_fetch

log = logging.getLogger(__name__)

PAGE_TIMEOUT_MS = 20_000
MAX_LINKS = 60


class BrowserEngine(Protocol):
    async def open(self, url: str) -> bool: ...
    async def page_text(self) -> str: ...
    async def links(self) -> list[LinkInfo]: ...
    async def click(self, link_id: int) -> bool: ...
    async def back(self) -> bool: ...
    def current_url(self) -> str: ...
    async def close(self) -> None: ...


class HttpBrowser:
    """Static fallback: fetch + parse; click(id) follows the link's href."""

    def __init__(self) -> None:
        self._url = ""
        self._body: bytes = b""
        self._history: list[str] = []

    async def open(self, url: str) -> bool:
        import asyncio

        if not is_public_http_url(url):
            return False
        body = await asyncio.to_thread(safe_fetch, url)
        if body is None:
            return False
        if self._url:
            self._history.append(self._url)
        self._url, self._body = url, body
        return True

    async def page_text(self) -> str:
        # crawls constantly land on papers/reports — read PDFs as text, not bytes
        if self._body.lstrip()[:5].startswith(b"%PDF"):
            import asyncio

            return await asyncio.to_thread(pdf_to_text, self._body)
        return html_to_text(self._body)

    async def links(self) -> list[LinkInfo]:
        if self._body.lstrip()[:5].startswith(b"%PDF"):
            return []                                   # PDFs are leaves, no links to walk
        return extract_links(self._body, self._url)[:MAX_LINKS]

    async def click(self, link_id: int) -> bool:
        for link in await self.links():
            if link["id"] == link_id:
                return await self.open(link["href"])
        return False

    async def back(self) -> bool:
        if not self._history:
            return False
        return await self.open(self._history.pop())

    def current_url(self) -> str:
        return self._url

    async def close(self) -> None:
        self._url, self._body, self._history = "", b"", []


class PlaywrightBrowser:
    """Real headless chromium — JS pages, redirect chains, click-through navigation."""

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._page = None
        self._links: list[LinkInfo] = []

    async def _ensure(self) -> None:
        if self._page is not None:
            return
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        context = await self._browser.new_context(user_agent="Laboratree/0.1 (research agent)")
        # SSRF + read-only web law at the network layer: block private hosts and non-GETs
        await context.route("**/*", self._guard_route)
        self._page = await context.new_page()

    async def _guard_route(self, route) -> None:
        request = route.request
        if request.method != "GET" or not is_public_http_url(request.url):
            await route.abort()
            return
        await route.continue_()

    async def open(self, url: str) -> bool:
        if not is_public_http_url(url):
            return False
        await self._ensure()
        try:
            await self._page.goto(url, timeout=PAGE_TIMEOUT_MS, wait_until="domcontentloaded")
            return True
        except Exception as exc:
            log.info("browser open %s failed: %s", url, exc)
            return False

    async def page_text(self) -> str:
        if self.current_url().split("?")[0].lower().endswith(".pdf"):
            import asyncio

            body = await asyncio.to_thread(safe_fetch, self.current_url())
            return await asyncio.to_thread(pdf_to_text, body or b"")
        try:
            text = await self._page.inner_text("body", timeout=5_000)
            return " ".join(text.split())[:40_000]
        except Exception:
            return ""

    async def links(self) -> list[LinkInfo]:
        try:
            raw = await self._page.eval_on_selector_all(
                "a[href]", "els => els.map(e => ({text: e.innerText, href: e.href}))")
        except Exception:
            return []
        self._links = [
            LinkInfo(id=i, text=" ".join((r.get("text") or "").split())[:120],
                     href=str(r.get("href") or ""))
            for i, r in enumerate(raw[:MAX_LINKS])
            if str(r.get("href", "")).startswith(("http://", "https://"))
        ]
        return self._links

    async def click(self, link_id: int) -> bool:
        for link in self._links or await self.links():
            if link["id"] == link_id:
                return await self.open(link["href"])   # navigation-by-href: deterministic + guarded
        return False

    async def back(self) -> bool:
        try:
            await self._page.go_back(timeout=PAGE_TIMEOUT_MS)
            return True
        except Exception:
            return False

    def current_url(self) -> str:
        try:
            return self._page.url if self._page else ""
        except Exception:
            return ""

    async def close(self) -> None:
        for closer in (self._browser, self._pw):
            try:
                if closer is not None:
                    await closer.close() if closer is self._browser else await closer.stop()
            except Exception:
                pass
        self._pw = self._browser = self._page = None


def playwright_available() -> bool:
    try:
        import playwright.async_api  # noqa: F401

        return True
    except Exception:
        return False


def browser_available() -> bool:
    return True  # HttpBrowser always works; Playwright upgrades capability


def get_browser() -> BrowserEngine:
    if playwright_available():
        return PlaywrightBrowser()
    return HttpBrowser()


__all__ = ["BrowserEngine", "HttpBrowser", "PlaywrightBrowser", "get_browser",
           "browser_available", "playwright_available"]
