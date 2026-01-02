from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

from src.config import AppConfig
from src.screenings import (
    ScreeningDescriptor,
    ScreeningDiscoveryError,
    _matches_language_and_format,
    filter_screenings_for_config,
    parse_show_time,
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
                page.goto(
                    movie_url, wait_until="domcontentloaded", timeout=self.navigation_timeout_ms
                )
                expected_date = target_date or config.movie_date()
                actual_date = _extract_date_from_url(page.url)
                if actual_date and actual_date != expected_date:
                    logger.warning(
                        "Screenings page redirected to %s (expected %s); skipping.",
                        actual_date,
                        expected_date,
                    )
                    browser.close()
                    return []

                selectors = page.query_selector_all("a.btn.btn-primary.btn-lg[data-url]")
                if not selectors:
                    page.wait_for_timeout(2000)
                    selectors = page.query_selector_all("a.btn.btn-primary.btn-lg[data-url]")

                descriptors: List[ScreeningDescriptor] = []
                for anchor in selectors:
                    order_url = anchor.get_attribute("data-url")
                    data_attrs = anchor.get_attribute("data-attrs")
                    label = (anchor.inner_text() or "").strip()
                    if not order_url or not label:
                        continue
                    if not _matches_language_and_format(data_attrs):
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
                return filter_screenings_for_config(descriptors, config, target_date)
        except Exception as exc:
            raise ScreeningDiscoveryError(f"Browser discovery failed: {exc}") from exc
