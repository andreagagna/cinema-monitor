from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import Iterable, List, Optional

from src.config import AppConfig
from src.screenings import ScreeningDescriptor, ScreeningDiscovery, ScreeningDiscoveryError
from src.screenings_browser import BrowserScreeningDiscovery
from src.seat_map import SeatMapParser
from src.seat_selection import SeatBlockSuggestion, SeatScoringConfig, SeatSelector
from src.seatmap_fetcher import SeatMapFetcher, SeatMapFetcherError

logger = logging.getLogger(__name__)


@dataclass
class SeatRecommendation:
    screening_date: date
    screening: ScreeningDescriptor
    suggestions: List[SeatBlockSuggestion]


class SeatAdvisor:
    """High-level orchestrator that goes from movie pages to seat suggestions."""

    def __init__(
        self,
        discovery: Optional[ScreeningDiscovery] = None,
        fetcher: Optional[SeatMapFetcher] = None,
        parser: Optional[SeatMapParser] = None,
        browser_discovery: Optional[BrowserScreeningDiscovery] = None,
    ):
        self.discovery = discovery or ScreeningDiscovery()
        self.fetcher = fetcher or SeatMapFetcher()
        self.parser = parser or SeatMapParser()
        self.browser_discovery = browser_discovery or BrowserScreeningDiscovery()

    def recommend(
        self,
        config: AppConfig,
        *,
        party_size: int = 1,
        top_n: int = 3,
        include_wheelchair: bool = False,
        dates: Optional[Iterable[date]] = None,
    ) -> List[SeatRecommendation]:
        if party_size < 1:
            raise ValueError("party_size must be >= 1")

        target_dates = list(dates) if dates else [config.movie_date()]
        results: List[SeatRecommendation] = []

        for screening_date in target_dates:
            movie_url = config.movie_url_for_date(screening_date)
            try:
                screenings = self.discovery.discover(movie_url, config, target_date=screening_date)
            except ScreeningDiscoveryError as exc:
                logger.warning("Failed to discover screenings for %s: %s", movie_url, exc)
                screenings = []

            if not screenings:
                try:
                    screenings = self.browser_discovery.discover(
                        movie_url, config, target_date=screening_date
                    )
                except ScreeningDiscoveryError as exc:
                    logger.warning("Browser discovery failed for %s: %s", movie_url, exc)
                    continue

            for screening in screenings:
                try:
                    svg_markup = self.fetcher.fetch_svg(screening.order_url)
                    seat_map = self.parser.parse(svg_markup)
                except (SeatMapFetcherError, ValueError) as exc:
                    logger.warning(
                        "Skipping screening %s due to seat map error: %s", screening.order_url, exc
                    )
                    if "captcha" in str(exc).lower():
                        logger.warning(
                            "Possible CAPTCHA encountered while fetching %s", screening.order_url
                        )
                    continue

                selector = SeatSelector(
                    seat_map, SeatScoringConfig(include_wheelchair=include_wheelchair)
                )
                suggestions = (
                    selector.best_blocks(size=party_size, top_n=top_n)
                    if party_size > 1
                    else selector.best_single_seats(top_n=top_n)
                )

                if not suggestions:
                    continue

                results.append(
                    SeatRecommendation(
                        screening_date=screening_date,
                        screening=screening,
                        suggestions=suggestions,
                    )
                )

        return results
