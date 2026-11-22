from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time
from typing import Dict, Iterable, List, Optional

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


TIME_PATTERN = re.compile(r"(\d{1,2}:\d{2})")

_CINEMA_SELECTOR = (
    "a[href*='/cinemas/'], .qb-cinema-name, .cinema-name, "
    "[data-cinema-id], [data-cinema-name], [data-automation-id*='cinema'], "
    "h2.qb-cinema-title, h3.qb-cinema-title, .qb-cinema-details h2, .qb-cinema-details h3, "
    ".qb-cinema h2, .qb-cinema h3, .qb-cinema h4"
)


def parse_show_time(text: str) -> Optional[time]:
    match = TIME_PATTERN.search(text)
    if not match:
        return None
    hour_str = match.group(1)
    return time.fromisoformat(hour_str)


def matches_language_and_format(
    data_attrs: Optional[str], config: Optional[AppConfig] = None
) -> bool:
    """Check Cinema City `data-attrs` against configured format, audio language, and dubbing rules."""
    cfg = config or AppConfig()
    formats = cfg.format_tokens()
    audio_lang = (cfg.audio_language or "").strip().lower()

    if not data_attrs:
        return not formats and not audio_lang

    lowered = data_attrs.lower()
    tokens = {tok.strip() for tok in lowered.split(",") if tok.strip()}

    if formats and not any(fmt in tokens or fmt in lowered for fmt in formats):
        return False

    if not cfg.allow_dubbed:
        if "dubbed" in tokens or any(tok.startswith("dubbed-lang") for tok in tokens):
            return False

    if audio_lang:
        lang_prefix = audio_lang.split("_")[0].split("-")[0]
        expected_tag = f"original-lang-{lang_prefix}"
        if expected_tag not in tokens and audio_lang not in tokens:
            return False

    return True


def _matches_language_and_format(
    data_attrs: Optional[str], config: Optional[AppConfig] = None
) -> bool:
    return matches_language_and_format(data_attrs, config)


def matches_cinema_context(cinema_context: Optional[str], config: AppConfig) -> bool:
    """Match extracted cinema context against CINEMA_FILTER when cinema wrappers exist in DOM."""
    cinema_tokens = config.cinema_filter_tokens()
    if not cinema_tokens or not cinema_context:
        return True
    lowered = cinema_context.lower()
    return any(tok in lowered for tok in cinema_tokens)


def _extract_cinema_context_for_column(column: Tag, page_has_cinema_markers: bool) -> Optional[str]:
    if not page_has_cinema_markers:
        return None

    for ancestor in column.parents:
        if not isinstance(ancestor, Tag) or ancestor.name in {"body", "html", "[document]"}:
            continue
        markers = ancestor.select(_CINEMA_SELECTOR)
        if markers:
            parts: List[str] = []
            for marker in markers:
                text = marker.get_text(" ", strip=True)
                if text:
                    parts.append(text)
                for attr_name in ("href", "data-cinema-id", "data-cinema-name"):
                    attr_val = marker.get(attr_name)
                    if isinstance(attr_val, str) and attr_val:
                        parts.append(attr_val)
            for attr_name in ("data-cinema-id", "data-cinema-name", "id"):
                anc_val = ancestor.get(attr_name)
                if isinstance(anc_val, str) and anc_val:
                    parts.append(anc_val)
            if parts:
                return " | ".join(parts)
    return None


def filter_screenings_for_config(
    screenings: Iterable[ScreeningDescriptor],
    config: AppConfig,
    target_date: Optional[date] = None,
) -> List[ScreeningDescriptor]:
    """Apply AppConfig limits (earliest show time, allowed weekdays) to screenings."""
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


class ScreeningDiscovery:
    """Fetch and parse screenings for a movie page."""

    def __init__(self, *, timeout: float = 10.0, transport: Optional[httpx.BaseTransport] = None):
        self._timeout = timeout
        self._transport = transport

    def discover(
        self, movie_url: str, config: AppConfig, target_date: Optional[date] = None
    ) -> List[ScreeningDescriptor]:
        html = self._fetch(movie_url)
        screenings = self._parse_screenings(html, config)
        return filter_screenings_for_config(screenings, config, target_date)

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

    def _parse_screenings(
        self, html: str, config: Optional[AppConfig] = None
    ) -> List[ScreeningDescriptor]:
        cfg = config or AppConfig()
        soup = BeautifulSoup(html, "html.parser")
        page_has_cinema_markers = bool(soup.select(_CINEMA_SELECTOR))
        descriptors: List[ScreeningDescriptor] = []
        columns = soup.select("div.qb-movie-info-column")

        for column in columns:
            if not isinstance(column, Tag):
                continue
            cinema_context = _extract_cinema_context_for_column(column, page_has_cinema_markers)
            if page_has_cinema_markers and cinema_context is not None:
                if not matches_cinema_context(cinema_context, cfg):
                    continue
            anchors = column.select("a.btn.btn-primary.btn-lg")
            for anchor in anchors:
                if not isinstance(anchor, Tag):
                    continue
                order_url_attr = anchor.get("data-url")
                if not isinstance(order_url_attr, str):
                    continue
                data_attrs = anchor.get("data-attrs")
                if not matches_language_and_format(
                    data_attrs if isinstance(data_attrs, str) else None,
                    cfg,
                ):
                    continue

                label = anchor.get_text(strip=True)
                show_time = parse_show_time(label)
                if show_time is None:
                    continue

                metadata: Dict[str, str] = {}
                for key, value in anchor.attrs.items():
                    if not key.startswith("data-") or key == "data-url":
                        continue
                    metadata[key] = str(value)
                if cinema_context:
                    metadata["cinema"] = cinema_context

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
        return filter_screenings_for_config(screenings, config, target_date)
