from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qs, urlsplit

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.config import DUNE_PART_THREE_PROFILE, AppConfig


class ScreeningDiscoveryError(RuntimeError):
    """Raised when the screening list cannot be retrieved or parsed."""


@dataclass(frozen=True)
class ScreeningDescriptor:
    label: str
    show_time: time
    order_url: str
    metadata: Dict[str, str] = field(default_factory=dict)


SCREENING_SELECTOR = ".qb-movie-info-column a.btn.btn-primary.btn-lg[data-url]"
TIME_PATTERN = re.compile(r"(\d{1,2}:\d{2})")

_CINEMA_SECTION_SELECTOR = ".movie-row, .qb-cinema, [data-cinema-id], [data-cinema-name]"
_CINEMA_MARKER_SELECTOR = (
    "a[href*='/cinemas/'], .qb-cinema-name, .cinema-name, .qb-cinema-title, "
    ".qb-cinema-details h2, .qb-cinema-details h3"
)
_CINEMA_PATH = re.compile(r"/cinemas/([^/]+)(?:/(\d+))?/?")
_DUNE_70MM_SUBTITLE_TAGS = {"70-mm", "subbed", "first-subbed-lang-cs"}


def parse_show_time(text: str) -> Optional[time]:
    match = TIME_PATTERN.search(text)
    if not match:
        return None
    return time.fromisoformat(match.group(1))


def matches_language_and_format(data_attrs: str, config: AppConfig) -> bool:
    """Match Cinema City `data-attrs` against format, audio language, and dubbing rules."""
    formats = config.format_tokens()
    tokens = {part.strip() for part in data_attrs.lower().split(",") if part.strip()}

    if formats and tokens.isdisjoint(formats):
        return False

    dubbed = "dubbed" in tokens or any(token.startswith("dubbed-lang-") for token in tokens)
    if dubbed and not config.allow_dubbed:
        return False

    audio_lang = (config.audio_language or "").strip().lower().replace("_", "-").split("-", 1)[0]
    if not audio_lang:
        return True

    original_audio = {token for token in tokens if token.startswith("original-lang-")}
    if original_audio:
        return f"original-lang-{audio_lang}" in original_audio
    if audio_lang in tokens:
        return True

    # These Dune advance listings identify the Czech-subtitled 70mm print of
    # the original English film without an explicit original-language tag.
    return (
        config.movie_id == DUNE_PART_THREE_PROFILE.movie_id
        and audio_lang == "en"
        and not dubbed
        and _DUNE_70MM_SUBTITLE_TAGS.issubset(tokens)
    )


def _extract_cinema_context(anchor: Tag) -> tuple[Optional[str], list[str]]:
    """Read the venue from the enclosing Quickbook row or explicitly identified cinema."""
    section = anchor.css.closest(_CINEMA_SECTION_SELECTOR)
    if section is None:
        return None, []

    cinema_id = section.get("data-cinema-id")
    cinema_ids = {cinema_id.strip()} if isinstance(cinema_id, str) and cinema_id.strip() else set()
    cinema_name = section.get("data-cinema-name")
    names = [cinema_name.strip()] if isinstance(cinema_name, str) and cinema_name.strip() else []
    for marker in section.select(_CINEMA_MARKER_SELECTOR):
        # A nested cinema row owns its own headings and links.
        parent = marker.parent
        if (
            not isinstance(parent, Tag)
            or parent.css.closest(_CINEMA_SECTION_SELECTOR) is not section
        ):
            continue
        label = marker.get_text(" ", strip=True)
        if label:
            names.append(label)
        href = marker.get("href")
        if not isinstance(href, str):
            continue
        try:
            url = urlsplit(href)
        except ValueError:
            continue
        cinema_path = _CINEMA_PATH.fullmatch(url.path)
        if cinema_path is None:
            continue
        slug, path_id = cinema_path.groups()
        names.append(slug)
        if path_id:
            cinema_ids.add(path_id)
        fragment_params = parse_qs(url.fragment.partition("?")[2])
        cinema_ids.update(
            value for value in fragment_params.get("in-cinema", []) if value.isdigit()
        )

    if len(cinema_ids) > 1:
        return None, []
    return next(iter(cinema_ids), None), list(dict.fromkeys(names))


def parse_screenings(html: str, config: AppConfig) -> List[ScreeningDescriptor]:
    """Parse either the initial HTML or Playwright's rendered Quickbook listings."""
    soup = BeautifulSoup(html, "html.parser")
    cinema_tokens = config.cinema_filter_tokens()
    cinema_name_patterns = [
        re.compile(rf"(?<!\w){re.escape(token)}(?!\w)", re.IGNORECASE)
        for token in cinema_tokens
        if not token.isdigit()
    ]
    descriptors: List[ScreeningDescriptor] = []
    for anchor in soup.select(SCREENING_SELECTOR):
        order_url = anchor.get("data-url")
        data_attrs = anchor.get("data-attrs")
        if not isinstance(order_url, str) or not order_url.strip():
            continue
        if not matches_language_and_format(
            data_attrs if isinstance(data_attrs, str) else "", config
        ):
            continue

        cinema_id, names = _extract_cinema_context(anchor)
        if (
            cinema_tokens
            and cinema_id not in cinema_tokens
            and not any(pattern.search(name) for pattern in cinema_name_patterns for name in names)
        ):
            continue

        label = anchor.get_text(" ", strip=True)
        show_time = parse_show_time(label)
        if show_time is None:
            continue
        metadata = {
            key: str(value)
            for key, value in anchor.attrs.items()
            if key.startswith("data-") and key != "data-url"
        }
        context = names + ([cinema_id] if cinema_id else [])
        if context:
            metadata["cinema"] = " | ".join(context)
        descriptors.append(ScreeningDescriptor(label, show_time, order_url.strip(), metadata))

    return descriptors


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
        screenings = parse_screenings(html, config)
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
