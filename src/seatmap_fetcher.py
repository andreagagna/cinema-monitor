from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple, Union

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag
from playwright.sync_api import Frame, Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

import logging
import urllib.parse

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
    ):
        self._timeout = timeout
        self._transport = transport
        self._browser_fetcher = browser_fetcher
        self._enable_browser_fallback = enable_browser_fallback
        self._headless = headless
        self._navigation_timeout_ms = navigation_timeout_ms

    def fetch_svg(self, order_url: str) -> str:
        normalized_url = self._normalize_order_url(order_url)
        try:
            presentation_id = self._extract_presentation_id(normalized_url)
            metadata = self._fetch_presentation_metadata(presentation_id)
            seatplan = self._fetch_seatplan(metadata["venueId"], metadata["seatplanId"])
            seat_status = self._fetch_seat_status(presentation_id, metadata["venueTypeId"])
            svg_markup = self._build_svg_from_plan(seatplan, seat_status)
            if svg_markup:
                return svg_markup
            raise SeatMapFetcherError(f"No seat map SVG present at {normalized_url}")
        except SeatMapFetcherError as exc:
            browser_svg = self._maybe_fetch_with_browser(normalized_url)
            if browser_svg:
                return browser_svg
            raise exc

    def _fetch(self, url: str) -> str:
        response = self._http_get(url, error_message=f"Failed to fetch seat map from {url}")
        return response.text

    def _extract_svg(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        svg = soup.find("svg", id="svg-seatmap")
        if not isinstance(svg, Tag):
            return None
        svg_text = svg.decode()
        return svg_text

    def _presentation_base(self) -> str:
        return "https://tickets.cinemacity.cz/api"

    def _fetch_presentation_metadata(self, presentation_id: int) -> Dict[str, int]:
        url = f"{self._presentation_base()}/presentations/{presentation_id}?referralMiniSiteId=0"
        response = self._http_get(
            url, error_message=f"Failed to fetch presentation metadata from {url}"
        )
        data = response.json()
        presentation = data.get("presentation")
        if not presentation:
            raise SeatMapFetcherError("Presentation metadata missing from response")
        try:
            return {
                "venueId": int(presentation["venueId"]),
                "seatplanId": int(presentation["seatplanId"]),
                "venueTypeId": int(presentation["venueTypeId"]),
            }
        except (KeyError, ValueError, TypeError) as exc:
            raise SeatMapFetcherError("Presentation metadata missing required fields") from exc

    def _fetch_seatplan(self, venue_id: int, seatplan_id: int) -> Dict:
        url = f"{self._presentation_base()}/seats/seatplanV2?venueId={venue_id}&seatplanId={seatplan_id}"
        response = self._http_get(url, error_message=f"Failed to fetch seat plan from {url}")
        return response.json()

    def _fetch_seat_status(self, presentation_id: int, venue_type_id: int) -> Dict[str, int]:
        url = (
            f"{self._presentation_base()}/seats/seats-statusV2"
            f"?presentationId={presentation_id}&venueTypeId={venue_type_id}&isReserved=1"
        )
        response = self._http_get(url, error_message=f"Failed to fetch seat statuses from {url}")
        data = response.json()
        return data.get("seats", {})

    def _build_svg_from_plan(self, seatplan: Dict, seat_status: Dict[str, int]) -> str:
        sections = seatplan.get("S", {})
        if not sections:
            return ""
        parts = ['<svg id="svg-seatmap"><g class="svg-pan-zoom_viewport">']
        for section_id, section in sections.items():
            groups = section.get("G", {})
            for group in groups.values():
                for row_id, row in group.get("R", {}).items():
                    row_name = row.get("n") or str(row_id)
                    seats = row.get("S", {})
                    for seat_key, seat in seats.items():
                        seat_label = seat.get("n") or str(seat_key)
                        seat_uid = f"{section_id}_{seat_key}_{row_id}"
                        status_value = seat_status.get(seat_uid)
                        status_text = self._status_text(status_value, seat)
                        aria = f"row: {row_name} seat: {seat_label} - {status_text}"
                        parts.append(
                            f'<g s="{section_id},{seat_key},{row_id}" aria-description="{aria}">'
                            f"<text>{seat_label}</text>"
                            "</g>"
                        )
        parts.append("</g></svg>")
        return "".join(parts)

    def _status_text(self, status_value: Optional[int], seat: Dict) -> str:
        if status_value == 0 or status_value is None:
            return "Available"
        return "Occupied"

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
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=self._headless)
                context = browser.new_context()
                page = context.new_page()
                logger.info("Loading seat map via Playwright: %s", order_url)
                page.goto(
                    order_url,
                    wait_until="domcontentloaded",
                    timeout=self._navigation_timeout_ms,
                )
                self._dismiss_cookies(page)
                self._continue_as_guest(page)
                svg_html = self._extract_svg_from_page(page)
                browser.close()
                if not svg_html:
                    raise SeatMapFetcherError(f"No seat map SVG present at {order_url}")
                return svg_html
        except PlaywrightTimeoutError as exc:
            raise SeatMapFetcherError(f"Timed out waiting for seat map at {order_url}") from exc

    def _dismiss_cookies(self, page: Page) -> None:
        try:
            cookie_btn = (
                page.get_by_text("Reject All Cookies", exact=False)
                .or_(page.get_by_text("Odmítnout vše", exact=False))
                .first
            )
            if cookie_btn and cookie_btn.is_visible():
                cookie_btn.click()
        except Exception:
            pass

    def _continue_as_guest(self, page: Page) -> None:
        try:
            guest_btn = page.locator("button[data-automation-id='guest-button']").first
            guest_btn.wait_for(timeout=3000)
            if guest_btn.is_visible():
                guest_btn.click()
        except PlaywrightTimeoutError:
            pass

    def _extract_svg_from_page(self, page: Page) -> str:
        selectors = ["svg#svg-seatmap", ".seatmap svg#svg-seatmap"]
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                locator.wait_for(timeout=self._navigation_timeout_ms)
                self._wait_for_seat_content(page)
                svg_html = locator.evaluate("el => el.outerHTML")
                if svg_html:
                    return svg_html
            except PlaywrightTimeoutError:
                continue
        # Check all frames (seat map often lives inside an iframe)
        for frame in page.frames:
            svg_html = self._extract_svg_from_frame(frame)
            if svg_html:
                return svg_html
        raise PlaywrightTimeoutError("svg#svg-seatmap not found in page or frames")

    def _extract_svg_from_frame(self, frame: Frame) -> Optional[str]:
        try:
            locator = frame.locator("svg#svg-seatmap").first
            locator.wait_for(timeout=self._navigation_timeout_ms)
            self._wait_for_seat_content(frame)
            svg_html = locator.evaluate("el => el.outerHTML")
            if svg_html:
                return svg_html
        except PlaywrightTimeoutError:
            pass
        return None

    def _normalize_order_url(self, url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        path = parsed.path.replace("/api/order/", "/order/")
        normalized = parsed._replace(path=path)
        return urllib.parse.urlunsplit(normalized)

    def _wait_for_seat_content(self, context: Union[Page, Frame]) -> None:
        locator = context.locator("svg#svg-seatmap g[aria-description]").first
        locator.wait_for(timeout=self._navigation_timeout_ms)

    def _extract_presentation_id(self, url: str) -> int:
        parsed = urllib.parse.urlsplit(url)
        segments = [segment for segment in parsed.path.split("/") if segment]
        if not segments:
            raise SeatMapFetcherError(f"Unable to determine presentation id from {url}")
        try:
            return int(segments[-1])
        except ValueError as exc:
            raise SeatMapFetcherError(f"Invalid presentation id in {url}") from exc

    def _http_get(self, url: str, *, error_message: Optional[str] = None) -> httpx.Response:
        message = error_message or f"Failed to fetch {url}"
        try:
            with httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
                headers={"User-Agent": "cinema-monitor/2.0"},
                transport=self._transport,
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                return response
        except httpx.HTTPError as exc:
            raise SeatMapFetcherError(message) from exc
