from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from playwright.sync_api import sync_playwright

from src.config import AppConfig
from src.screenings import (
    ScreeningDescriptor,
    ScreeningDiscoveryError,
    parse_show_time,
)

logger = logging.getLogger(__name__)


class BrowserScreeningDiscovery:
    """Uses Playwright to load the dynamic movie page and extract showtimes."""

    def __init__(self, *, headless: bool = True, navigation_timeout_ms: int = 15000):
        self.headless = headless
        self.navigation_timeout_ms = navigation_timeout_ms

    def discover(
        self,
        movie_url: str,
        config: AppConfig,
        target_date: Optional[date] = None,
    ) -> List[ScreeningDescriptor]:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self.headless)
                context = browser.new_context(locale=config.lang)
                page = context.new_page()
                logger.info("Loading movie page via Playwright: %s", movie_url)
                page.goto(movie_url, wait_until="domcontentloaded", timeout=self.navigation_timeout_ms)

                selectors = page.query_selector_all("a.btn.btn-primary.btn-lg[data-url]")
                if not selectors:
                    page.wait_for_timeout(2000)
                    selectors = page.query_selector_all("a.btn.btn-primary.btn-lg[data-url]")

                descriptors: List[ScreeningDescriptor] = []
                for anchor in selectors:
                    order_url = anchor.get_attribute("data-url")
                    label = (anchor.inner_text() or "").strip()
                    if not order_url or not label:
                        continue
                    show_time = parse_show_time(label)
                    if show_time is None:
                        continue
                    descriptors.append(
                        ScreeningDescriptor(
                            label=label,
                            show_time=show_time,
                            order_url=order_url,
                            metadata={},
                        )
                    )
                browser.close()
                return descriptors
        except Exception as exc:
            raise ScreeningDiscoveryError(f"Browser discovery failed: {exc}") from exc
