from __future__ import annotations

import logging
import time
import urllib.parse
from typing import Callable, Optional, cast

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag
from playwright.sync_api import Page, sync_playwright

logger = logging.getLogger(__name__)


class SeatMapFetcherError(RuntimeError):
    """Raised when the seat map cannot be retrieved."""


class SeatMapFetcher:
    """Download a booking page and extract the seat-map SVG."""

    def __init__(
        self,
        *,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
        browser_fetcher: Optional[Callable[[str], str]] = None,
        enable_browser_fallback: bool = True,
        headless: bool = True,
        navigation_timeout_ms: int = 2000,
        browser_args: Optional[list[str]] = None,
        chromium_sandbox: bool = False,
    ):
        self._timeout = timeout
        self._transport = transport
        self._browser_fetcher = browser_fetcher
        self._enable_browser_fallback = enable_browser_fallback
        self._headless = headless
        self._navigation_timeout_ms = navigation_timeout_ms
        self._browser_args = browser_args or ["--no-sandbox", "--disable-setuid-sandbox"]
        self._chromium_sandbox = chromium_sandbox

    def fetch_svg(self, order_url: str) -> str:
        normalized_url = self._normalize_order_url(order_url)
        browser_svg = self._maybe_fetch_with_browser(normalized_url)
        if browser_svg:
            return browser_svg

        # HTTP fallback exists primarily for tests where we inject static HTML.
        html = self._fetch(normalized_url)
        svg = self._extract_svg(html)
        if svg:
            logger.warning("Falling back to HTTP seat map fetch for %s", normalized_url)
            return svg

        raise SeatMapFetcherError(f"Failed to fetch seat map from {normalized_url}")

    def _fetch(self, url: str) -> str:
        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": "cinema-monitor/2.0"},
                transport=self._transport,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as exc:
            raise SeatMapFetcherError(f"Failed to fetch seat map from {url}") from exc

    def _extract_svg(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        svg = soup.find("svg", id="svg-seatmap")
        if not isinstance(svg, Tag):
            return None
        svg_text = svg.decode()
        return svg_text

    def _maybe_fetch_with_browser(self, order_url: str) -> Optional[str]:
        fetcher: Optional[Callable[[str], str]]
        if self._browser_fetcher is not None:
            fetcher = self._browser_fetcher
        elif self._enable_browser_fallback:
            fetcher = self._fetch_with_browser
        else:
            fetcher = None
        if fetcher is None:
            return None
        try:
            svg = fetcher(order_url)
            if svg:
                logger.info("Fetched seat map via browser for %s", order_url)
                return svg
            logger.warning("Browser seat map fetch returned empty for %s", order_url)
        except Exception as exc:
            logger.warning("Browser seat map fetch failed for %s: %s", order_url, exc)
        return None

    def _fetch_with_browser(self, order_url: str) -> str:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(
                        headless=self._headless,
                        args=self._browser_args,
                        chromium_sandbox=self._chromium_sandbox,
                    )
                    context = browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                        ),
                        viewport={"width": 1920, "height": 1080},
                    )
                    page = context.new_page()
                    logger.info(
                        "Loading seat map via Playwright (attempt %d/%d): %s",
                        attempt + 1,
                        max_retries,
                        order_url,
                    )
                    page.goto(
                        order_url,
                        wait_until="domcontentloaded",
                        timeout=self._navigation_timeout_ms,
                    )
                    svg_html = self._poll_for_svg(page, timeout_ms=5000)
                    browser.close()
                    if svg_html:
                        return svg_html
            except Exception as exc:
                logger.warning("Browser attempt %d failed: %s", attempt + 1, exc)
        raise SeatMapFetcherError(
            f"Failed to fetch seat map via browser after {max_retries} attempts"
        )

    def _poll_for_svg(self, page: Page, timeout_ms: int) -> Optional[str]:
        """Aggressively poll for the seat map SVG to beat the CAPTCHA."""
        start_time = time.time()
        last_svg = None

        while (time.time() - start_time) * 1000 < timeout_ms:
            try:
                svg_handle = page.query_selector("svg#svg-seatmap")
                if svg_handle:
                    content = svg_handle.query_selector("g[aria-description]")
                    if not content:
                        content = svg_handle.query_selector("use[aria-description]")

                    if content:
                        html = cast(str, svg_handle.evaluate("el => el.outerHTML"))
                        last_svg = html
                        if "Occupied" in html:
                            logger.info("Captured SVG with seat status data")
                            return html
            except Exception:
                pass
            time.sleep(0.1)

        # If we timed out but have a map, return it (better than nothing)
        if last_svg:
            logger.warning("Timed out waiting for seat status, returning last captured map")
            return last_svg
        return None

    def _normalize_order_url(self, url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path.replace("/api/order/", "/order/")
        normalized = parsed._replace(path=path)
        return urllib.parse.urlunsplit(normalized)
