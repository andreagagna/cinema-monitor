from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import time, date
from typing import Dict, List, Optional, cast

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.config import AppConfig


class ScreeningDiscoveryError(RuntimeError):
    """Raised when the screening list cannot be retrieved or parsed."""


@dataclass(frozen=True)
class ScreeningDescriptor:
    label: str
    show_time: time
    order_url: str
    metadata: Dict[str, str] = field(default_factory=dict)


class ScreeningDiscovery:
    """Fetch and parse screenings for a movie page."""

    def __init__(self, *, timeout: float = 10.0, transport: Optional[httpx.BaseTransport] = None):
        self._timeout = timeout
        self._transport = transport
        self._time_pattern = re.compile(r"(\d{1,2}:\d{2})")

    def discover(
        self, movie_url: str, config: AppConfig, target_date: Optional[date] = None
    ) -> List[ScreeningDescriptor]:
        html = self._fetch(movie_url)
        screenings = self._parse_screenings(html)
        return self._apply_filters(screenings, config, target_date)

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
                text_content: str = response.text
                return text_content
        except httpx.HTTPError as exc:
            raise ScreeningDiscoveryError(f"Failed to fetch screenings from {url}") from exc

    def _parse_screenings(self, html: str) -> List[ScreeningDescriptor]:
        soup = BeautifulSoup(html, "html.parser")
        descriptors: List[ScreeningDescriptor] = []
        columns = soup.select("div.qb-movie-info-column")

        for column in columns:
            if not isinstance(column, Tag):
                continue
            anchors = column.select("a.btn.btn-primary.btn-lg")
            for anchor in anchors:
                if not isinstance(anchor, Tag):
                    continue
                order_url_attr = anchor.get("data-url")
                if not isinstance(order_url_attr, str):
                    continue

                label_text = anchor.get_text(strip=True)
                label: str = str(label_text)
                show_time = self._extract_time(label)
                if show_time is None:
                    continue

                metadata: Dict[str, str] = {}
                for key, value in anchor.attrs.items():
                    if not key.startswith("data-") or key == "data-url":
                        continue
                    metadata[key] = str(value)

                descriptors.append(
                    ScreeningDescriptor(
                        label=label,
                        show_time=show_time,
                        order_url=order_url_attr,
                        metadata=metadata,
                    )
                )

        return descriptors

    def _apply_filters(
        self, screenings: List[ScreeningDescriptor], config: AppConfig, target_date: Optional[date]
    ) -> List[ScreeningDescriptor]:
        earliest = config.parsed_earliest_show_time()
        allowed_weekdays = config.allowed_weekday_indices()
        screening_date = target_date or config.movie_date()
        weekday = screening_date.weekday()

        filtered: List[ScreeningDescriptor] = []
        for descriptor in screenings:
            if earliest and descriptor.show_time < earliest:
                continue
            if allowed_weekdays and weekday not in allowed_weekdays:
                continue
            filtered.append(descriptor)
        return filtered

    def _extract_time(self, text: str) -> Optional[time]:
        match = self._time_pattern.search(text)
        if not match:
            return None
        hour_str = match.group(1)
        return time.fromisoformat(hour_str)
