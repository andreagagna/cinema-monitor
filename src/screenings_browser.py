from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, sync_playwright

from src.config import AppConfig
from src.screenings import (
    ScreeningDescriptor,
    ScreeningDiscoveryError,
    filter_screenings_for_config,
    matches_cinema_context,
    matches_language_and_format,
    parse_show_time,
)

logger = logging.getLogger(__name__)

_ANCHOR_SELECTOR = "a.btn.btn-primary.btn-lg[data-url]"


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


def _extract_anchor_metadata_and_cinema(anchor: Any) -> tuple[Dict[str, str], Optional[str]]:
    """Extract data-* attrs and nearest cinema label from a Playwright ElementHandle."""
    try:
        payload = anchor.evaluate(
            """el => {
                const meta = {};
                for (const attr of el.attributes || []) {
                    if (attr.name.startsWith('data-') && attr.name !== 'data-url') {
                        meta[attr.name] = attr.value;
                    }
                }
                const cinemaSel = [
                    "a[href*='/cinemas/']",
                    ".qb-cinema-name",
                    ".cinema-name",
                    "[data-cinema-id]",
                    "[data-cinema-name]",
                    "[data-automation-id*='cinema']",
                    "h2.qb-cinema-title",
                    "h3.qb-cinema-title",
                    ".qb-cinema-details h2",
                    ".qb-cinema-details h3",
                    ".qb-cinema h2",
                    ".qb-cinema h3",
                    ".qb-cinema h4"
                ].join(", ");
                let cur = el.parentElement;
                let cinema = null;
                while (cur && cur.tagName !== 'BODY' && cur.tagName !== 'HTML') {
                    const markers = cur.querySelectorAll(cinemaSel);
                    if (markers && markers.length > 0) {
                        const parts = [];
                        markers.forEach(m => {
                            const txt = (m.textContent || '').trim();
                            if (txt) parts.push(txt);
                            for (const k of ['href', 'data-cinema-id', 'data-cinema-name']) {
                                const v = m.getAttribute(k);
                                if (v) parts.push(v);
                            }
                        });
                        if (parts.length > 0) {
                            cinema = parts.join(' | ');
                            break;
                        }
                    }
                    cur = cur.parentElement;
                }
                return { meta, cinema };
            }"""
        )
        if isinstance(payload, dict):
            meta_raw = payload.get("meta")
            meta = (
                {str(k): str(v) for k, v in meta_raw.items()} if isinstance(meta_raw, dict) else {}
            )
            cinema_raw = payload.get("cinema")
            cinema = str(cinema_raw) if cinema_raw else None
            return meta, cinema
    except Exception:
        pass
    return {}, None


class BrowserScreeningDiscovery:
    """Uses Playwright to load the dynamic movie page and extract showtimes."""

    def __init__(
        self,
        *,
        headless: bool = True,
        navigation_timeout_ms: int = 15000,
        render_wait_ms: int = 3000,
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

        selectors = page.query_selector_all(_ANCHOR_SELECTOR)
        if not selectors:
            try:
                page.wait_for_selector(_ANCHOR_SELECTOR, timeout=self.render_wait_ms)
            except Exception:
                page.wait_for_timeout(min(self.render_wait_ms, 1500))
            selectors = page.query_selector_all(_ANCHOR_SELECTOR)

        actual_date = _extract_date_from_url(page.url)
        if actual_date and actual_date != expected_date:
            logger.warning(
                "Screenings page redirected to %s (expected %s); skipping.",
                actual_date,
                expected_date,
            )
            return []

        descriptors: List[ScreeningDescriptor] = []
        for anchor in selectors:
            order_url = anchor.get_attribute("data-url")
            data_attrs = anchor.get_attribute("data-attrs")
            label = (anchor.inner_text() or "").strip()
            if not order_url or not label:
                continue
            metadata, cinema_context = _extract_anchor_metadata_and_cinema(anchor)
            if data_attrs and "data-attrs" not in metadata:
                metadata["data-attrs"] = data_attrs
            if cinema_context:
                metadata["cinema"] = cinema_context
            if not matches_cinema_context(cinema_context, config):
                continue
            if not matches_language_and_format(data_attrs, config):
                continue
            show_time = parse_show_time(label)
            if show_time is None:
                continue
            descriptors.append(
                ScreeningDescriptor(
                    label=label,
                    show_time=show_time,
                    order_url=order_url,
                    metadata=metadata,
                )
            )

        return filter_screenings_for_config(descriptors, config, target_date)
