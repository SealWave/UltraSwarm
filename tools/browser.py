"""
tools/browser.py
================
Browser utilities built on browser_use.

This module now uses browser_use directly under the project's uv environment.
It keeps DuckDuckGo search for discovery, and browser interaction is handled by
BrowserSession/Page/Element instead of local stub methods.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, List
from urllib.parse import quote_plus, urljoin
from pathlib import Path

import requests
from rich.console import Console

from tools.browser_actions import normalize_url

console = Console()
DEBUG_BROWSER = os.getenv("AGENT_BROWSER_DEBUG", "").lower() in {"1", "true", "yes"}
DDG_SEARCH_URL = "https://html.duckduckgo.com/html/?q={query}"


def _normalize_cdp_url(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith(("ws://", "wss://", "http://", "https://")):
        return cleaned
    if re.match(r"^[^/\s:]+:\d+(/.*)?$", cleaned):
        return f"http://{cleaned}"
    return cleaned


def _run_sync(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("browser helpers cannot run inside an active event loop")


class _DuckDuckGoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        classes = attr.get("class", "")
        if tag == "a" and "result__a" in classes:
            self._current = {"title": "", "url": attr.get("href", ""), "snippet": ""}
            self._capture = "title"
        elif self._current and "result__snippet" in classes:
            self._capture = "snippet"

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self._current:
            return
        if self._capture == "title" and self._current.get("title"):
            self.results.append(self._current)
            self._current = None
            self._capture = None
        elif self._capture == "snippet":
            self._capture = None

    def handle_data(self, data: str) -> None:
        if not self._current or not self._capture:
            return
        value = data.strip()
        if value:
            self._current[self._capture] = (self._current[self._capture] + " " + value).strip()


def _extract_title_and_text(html: str) -> tuple[str, str]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title_match.group(1))).strip() if title_match else ""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return title, text[:5000]


@dataclass
class _BrowserState:
    browser: Any
    llm: Any
    started: bool = False


class AgentBrowser:
    """Real browser_use-backed browser wrapper."""

    _state: _BrowserState | None = None

    @classmethod
    def _build_state(cls) -> _BrowserState:
        if cls._state is not None:
            return cls._state
        try:
            from browser_use import Browser, ChatBrowserUse
            from browser_use.browser.profile import BrowserProfile
        except Exception as exc:
            raise RuntimeError("browser-use is not installed in the active uv environment.") from exc

        cdp_url = _normalize_cdp_url(os.getenv("BROWSER_USE_CDP_URL"))
        if cdp_url:
            browser = Browser(cdp_url=cdp_url)
        elif os.getenv("BROWSER_USE_CLOUD", "").lower() in {"1", "true", "yes"}:
            browser = Browser(use_cloud=True)
        else:
            try:
                browser = Browser.from_system_chrome()
            except Exception:
                chrome_exe = Path(os.getenv("LOCALAPPDATA", "")) / "ms-playwright" / "chromium-1223" / "chrome-win64" / "chrome.exe"
                browser = Browser(
                    browser_profile=BrowserProfile(
                        headless=os.getenv("BROWSER_HEADLESS", "false").lower() in {"1", "true", "yes"},
                        is_local=True,
                        user_data_dir=tempfile.mkdtemp(prefix="browser-use-profile-"),
                        executable_path=str(chrome_exe) if chrome_exe.exists() else None,
                    )
                )
        llm = ChatBrowserUse(model=os.getenv("BROWSER_USE_MODEL") or None)
        cls._state = _BrowserState(browser=browser, llm=llm)
        return cls._state

    @classmethod
    async def _ensure_started(cls) -> None:
        state = cls._build_state()
        if not state.started:
            await state.browser.start()
            state.started = True

    @classmethod
    async def _current_page(cls):
        await cls._ensure_started()
        state = cls._build_state()
        return await state.browser.get_current_page()

    @classmethod
    async def _dismiss_common_popups(cls) -> None:
        state = cls._build_state()
        page = await state.browser.get_current_page()
        if page is None:
            return
        for hint in ("close", "dismiss", "accept cookies", "accept all", "no thanks", "not now", "skip", "sign in", "login"):
            try:
                element = await page.get_element_by_prompt(hint, llm=state.llm)
                if element:
                    await element.click()
                    await asyncio.sleep(0.2)
            except Exception:
                continue

    @classmethod
    async def _navigate(cls, url: str) -> dict:
        await cls._ensure_started()
        state = cls._build_state()
        await state.browser.navigate_to(url)
        await cls._dismiss_common_popups()
        text = await state.browser.get_state_as_text()
        current_url = await state.browser.get_current_page_url()
        title = await state.browser.get_current_page_title()
        return {"url": current_url, "title": title, "text": text, "status": "ok", "full_data": {"state_text": text}}

    @classmethod
    async def _snapshot(cls) -> dict:
        await cls._ensure_started()
        state = cls._build_state()
        await cls._dismiss_common_popups()
        text = await state.browser.get_state_as_text()
        current_url = await state.browser.get_current_page_url()
        title = await state.browser.get_current_page_title()
        return {"text": text, "url": current_url, "title": title, "status": "ok"}

    @classmethod
    async def _click(cls, prompt: str) -> bool:
        page = await cls._current_page()
        if page is None:
            return False
        state = cls._build_state()
        try:
            element = await page.get_element_by_prompt(prompt, llm=state.llm)
            if not element:
                return False
            await element.click()
            return True
        except Exception:
            return False

    @classmethod
    async def _type(cls, prompt: str, text: str) -> bool:
        page = await cls._current_page()
        if page is None:
            return False
        state = cls._build_state()
        try:
            element = await page.get_element_by_prompt(prompt, llm=state.llm)
            if not element:
                return False
            await element.fill(text, clear=True)
            return True
        except Exception:
            return False

    @classmethod
    async def _press(cls, key: str) -> bool:
        page = await cls._current_page()
        if page is None:
            return False
        try:
            await page.press(key)
            return True
        except Exception:
            return False

    @classmethod
    async def _scroll(cls, direction: str = "down", amount: int = 500) -> bool:
        page = await cls._current_page()
        if page is None:
            return False
        delta = amount if direction.lower() != "up" else -amount
        try:
            await page.evaluate(f"() => window.scrollBy(0, {delta})")
            return True
        except Exception:
            return False

    @classmethod
    async def _wait(cls, ms: int = 1000) -> bool:
        await asyncio.sleep(max(0, ms) / 1000)
        return True

    @classmethod
    def fetch_page(cls, url: str) -> dict:
        url = normalize_url(url)
        if not url:
            return {"url": "", "text": "", "title": "", "status": "error: unsafe or invalid URL"}
        try:
            return _run_sync(cls._navigate(url))
        except Exception as exc:
            return {"url": url, "text": "", "title": "", "status": f"error: {exc}"}

    @classmethod
    def snapshot(cls) -> dict:
        try:
            return _run_sync(cls._snapshot())
        except Exception as exc:
            return {"text": "", "url": "", "title": "", "status": f"error: {exc}"}

    @classmethod
    def click(cls, ref: str) -> bool:
        return bool(_run_sync(cls._click(ref)))

    @classmethod
    def type_text(cls, ref: str, text: str) -> bool:
        return bool(_run_sync(cls._type(ref, text)))

    @classmethod
    def wait(cls, ms: int = 1000) -> bool:
        return bool(_run_sync(cls._wait(ms)))

    @classmethod
    def scroll(cls, direction: str = "down", amount: int = 500) -> bool:
        return bool(_run_sync(cls._scroll(direction, amount)))

    @classmethod
    def press(cls, key: str = "Enter") -> bool:
        return bool(_run_sync(cls._press(key)))

    @classmethod
    def search(cls, query: str) -> list[dict]:
        return google_search(query)


def fetch_page(url: str, timeout: int = 15) -> dict:
    return AgentBrowser.fetch_page(url)


def google_search(query: str, num_results: int = 8) -> list[dict]:
    console.print(f"[dim]  -> DuckDuckGo searching:[/dim] {query}")
    url = DDG_SEARCH_URL.format(query=quote_plus(query))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        parser = _DuckDuckGoParser()
        parser.feed(response.text)
        results: list[dict[str, str]] = []
        for item in parser.results:
            href = item.get("url", "")
            if href.startswith("/l/?"):
                href = urljoin("https://duckduckgo.com", href)
            elif href.startswith("//"):
                href = f"https:{href}"
            if not href:
                continue
            results.append({"title": item.get("title", "").strip(), "url": href, "snippet": item.get("snippet", "").strip()})
            if len(results) >= num_results:
                break
        return results
    except Exception as exc:
        return [{"title": "DuckDuckGo search failed", "url": url, "snippet": str(exc)}]


def scrape_product_page(url: str) -> dict:
    data = AgentBrowser.fetch_page(url)
    text = data.get("text", "")
    title_match = re.search(r'heading.*?"(.*?)"', text, re.I)
    price_match = re.search(r"\$\d+\.?\d*", text)
    return {
        **data,
        "product_title": title_match.group(1) if title_match else data.get("title", ""),
        "price": price_match.group(0) if price_match else "N/A",
    }


def find_competitor_products(niche: str, competitor_url: str = None) -> list[dict]:
    query = f"best selling {niche} products 2025"
    if competitor_url:
        query += f" site:{competitor_url}"
    return google_search(query)


def get_seo_data(keyword: str, domain: str = None) -> dict:
    results = google_search(f"{keyword} site:reddit.com OR site:quora.com")
    serp = google_search(keyword)
    return {"keyword": keyword, "serp_results": serp, "community_discussions": results}


def find_and_fill_on_page(url: str, hint: str, text: str) -> dict:
    page = fetch_page(url)
    if page.get("status") != "ok":
        return {"success": False, "error": page.get("status", "page_error")}
    ok = AgentBrowser.type_text(hint or "search", text)
    return {"success": ok, "method": "browser_use", "ref": hint}


def use_skill_for_action(skill_name: str, page_url: str, **kwargs) -> dict:
    hint = kwargs.get("hint") or "search"
    action = kwargs.get("action", "fill")
    if action == "fill":
        return find_and_fill_on_page(page_url, hint, kwargs.get("text", ""))
    return {"success": False, "error": "unsupported skill action"}
