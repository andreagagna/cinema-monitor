from __future__ import annotations

from typing import Optional

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag


class SeatMapFetcherError(RuntimeError):
    """Raised when the seat map cannot be retrieved."""


class SeatMapFetcher:
    """Download a booking page and extract the seat-map SVG."""

    def __init__(self, *, timeout: float = 10.0, transport: Optional[httpx.BaseTransport] = None):
        self._timeout = timeout
        self._transport = transport

    def fetch_svg(self, order_url: str) -> str:
        html = self._fetch(order_url)
        svg = self._extract_svg(html)
        if not svg:
            raise SeatMapFetcherError(f"No seat map SVG present at {order_url}")
        return svg

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
                return response.text  # type: ignore[no-any-return]
        except httpx.HTTPError as exc:
            raise SeatMapFetcherError(f"Failed to fetch seat map from {url}") from exc

    def _extract_svg(self, html: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        svg = soup.find("svg", id="svg-seatmap")
        if not isinstance(svg, Tag):
            return None
        svg_text = svg.decode()
        return svg_text
