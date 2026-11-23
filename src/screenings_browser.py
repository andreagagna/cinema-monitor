from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from src.config import AppConfig
from src.screenings import (
    SCREENING_SELECTOR,
    ScreeningDescriptor,
    ScreeningDiscoveryError,
    filter_screenings_for_config,
    parse_screenings,
)

logger = logging.getLogger(__name__)


def _extract_date_from_url(url: str) -> Optional[date]:
    fragment = urlsplit(url).fragment
    if "?" not in fragment:
        return None
    _, query = fragment.split("?", 1)
    params = parse_qs(query)
    value = params.get("at", [None])[0]
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


class BrowserScreeningDiscovery:
    """Uses Playwright to load the dynamic movie page and extract showtimes."""

    def __init__(
        self,
        *,
        headless: bool = True,
        navigation_timeout_ms: int = 15000,
        render_wait_ms: int = 10000,
    ):
        self.headless = headless
        self.navigation_timeout_ms = navigation_timeout_ms
        self.render_wait_ms = render_wait_ms

    def discover(
        self,
        movie_url: str,
        config: AppConfig,
        target_date: Optional[date] = None,
    ) -> List[ScreeningDescriptor]:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                try:
                    context = browser.new_context(locale=config.lang.replace("_", "-"))
                    page = context.new_page()
                    logger.info("Loading movie page via Playwright: %s", movie_url)
                    page.goto(
                        movie_url,
                        wait_until="domcontentloaded",
                        timeout=self.navigation_timeout_ms,
                    )
                    return self._discover_from_page(page, config, target_date)
                finally:
                    browser.close()
        except Exception as exc:
            raise ScreeningDiscoveryError(f"Browser discovery failed: {exc}") from exc

    def _discover_from_page(
        self,
        page: Page,
        config: AppConfig,
        target_date: Optional[date] = None,
    ) -> List[ScreeningDescriptor]:
        expected_date = target_date or config.movie_date()
        try:
            page.wait_for_selector(
                SCREENING_SELECTOR, state="attached", timeout=self.render_wait_ms
            )
        except PlaywrightTimeoutError:
            return []

        html = page.content()
        actual_date = _extract_date_from_url(page.url)
        if actual_date and actual_date != expected_date:
            logger.warning(
                "Screenings page redirected to %s (expected %s); skipping.",
                actual_date,
                expected_date,
            )
            return []

        screenings = parse_screenings(html, config)
        return filter_screenings_for_config(screenings, config, target_date)
