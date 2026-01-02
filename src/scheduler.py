from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from threading import Event
from typing import Callable, Iterable, List, Optional

from src.advisor import SeatAdvisor, SeatRecommendation
from src.config import AppConfig
from src.date_sweep import DateSweepConfig, iter_available_dates
from src.notifier import Notifier
from src.screenings import ScreeningDescriptor
from src.seat_map import SeatMap
from src.seat_selection import SeatBlockSuggestion
from src.seatmap_fetcher import normalize_order_url
from src.seatmap_renderer import SeatMapRenderer

logger = logging.getLogger(__name__)


@dataclass
class SchedulerConfig:
    poll_interval_seconds: int = 300
    max_retries: int = 3
    backoff_factor: float = 2.0
    horizon_days: int = 3
    party_size: int = 2
    top_n: int = 3
    include_wheelchair: bool = False
    min_score: Optional[float] = 0.8
    avoid_aisle: bool = True
    aisle_boundary: int = 3

    @classmethod
    def from_app_config(cls, config: AppConfig) -> "SchedulerConfig":
        return cls(
            min_score=config.min_score,
            avoid_aisle=config.avoid_aisle,
            aisle_boundary=config.aisle_distance,
        )


class MonitorScheduler:
    """Runs SeatAdvisor periodically with retry/backoff and notification dispatch."""

    _LATEST_DATE_FILENAME = "latest_screening_date.txt"

    def __init__(
        self,
        app_config: AppConfig,
        *,
        advisor: Optional[SeatAdvisor] = None,
        notifier: Optional[Notifier] = None,
        scheduler_config: Optional[SchedulerConfig] = None,
        date_iterator: Callable[[DateSweepConfig], Iterable[date]] = iter_available_dates,
        renderer: Optional[SeatMapRenderer] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
        stop_event: Optional[Event] = None,
        latest_date_path: Optional[Path] = None,
    ):
        self.app_config = app_config
        self.advisor = advisor or SeatAdvisor()
        self.notifier = notifier or Notifier(app_config)
        self.scheduler_config = scheduler_config or SchedulerConfig.from_app_config(app_config)
        self.date_iterator = date_iterator
        self.renderer = renderer or SeatMapRenderer()
        self.sleep_fn = sleep_fn
        self._stop_event = stop_event or Event()
        self._latest_date_path = latest_date_path or self._default_latest_date_path()

    def _plan_dates(self) -> List[date]:
        sweep_config = DateSweepConfig(
            start_date=self.app_config.movie_date(),
            days=self.scheduler_config.horizon_days,
            allowed_weekdays=self.app_config.allowed_weekday_indices(),
        )
        return list(self.date_iterator(sweep_config))

    def run_once(self) -> int:
        dates = self._plan_dates()
        if not dates:
            logger.info("No eligible dates to check (filters excluded all days).")
            return 0

        recommendations = self.advisor.recommend(
            self.app_config,
            party_size=self.scheduler_config.party_size,
            top_n=self.scheduler_config.top_n,
            include_wheelchair=self.scheduler_config.include_wheelchair,
            dates=dates,
        )

        dispatched = 0
        for recommendation in recommendations:
            if (
                recommendation.presentation_date
                and recommendation.presentation_date != recommendation.screening_date
            ):
                logger.warning(
                    "Skipping screening %s: order page shows %s instead of %s",
                    recommendation.screening.order_url,
                    recommendation.presentation_date.isoformat(),
                    recommendation.screening_date.isoformat(),
                )
                continue
            filtered = self._filter_suggestions(recommendation)
            for suggestion in filtered:
                self._notify(recommendation, suggestion)
                dispatched += 1
        self._notify_if_no_new_screening_day()

        if dispatched == 0:
            logger.info("No seat suggestions available for configured dates.")
        return dispatched

    def poll_with_retry(self) -> int:
        attempt = 0
        last_error: Optional[Exception] = None
        while attempt <= self.scheduler_config.max_retries:
            try:
                return self.run_once()
            except Exception as exc:
                last_error = exc
                attempt += 1
                if attempt > self.scheduler_config.max_retries:
                    break
                wait = self.scheduler_config.poll_interval_seconds * (
                    self.scheduler_config.backoff_factor ** (attempt - 1)
                )
                logger.warning(
                    "Monitor attempt %s/%s failed (%s). Retrying in %.1fs.",
                    attempt,
                    self.scheduler_config.max_retries,
                    exc,
                    wait,
                )
                self.sleep_fn(wait)
        if last_error:
            logger.error("Monitor aborted after retries: %s", last_error)
            raise last_error
        return 0

    def run_forever(self) -> None:
        logger.info(
            "Starting scheduler loop (interval=%ss).", self.scheduler_config.poll_interval_seconds
        )
        while not self._stop_event.is_set():
            try:
                self.poll_with_retry()
            except Exception as exc:
                logger.exception("Polling failed: %s", exc)
            if self._stop_event.wait(self.scheduler_config.poll_interval_seconds):
                break

    def stop(self) -> None:
        self._stop_event.set()

    def _notify(self, recommendation: SeatRecommendation, suggestion: SeatBlockSuggestion) -> None:
        screenshot_path: Optional[str] = None
        if self.renderer:
            try:
                screenshot_path = self.renderer.render(recommendation.seat_map, suggestion)
            except Exception as exc:
                logger.warning("Seat map rendering failed: %s", exc)

        message = self._format_message(
            recommendation.screening,
            recommendation.screening_date,
            suggestion,
            has_attachment=bool(screenshot_path),
        )
        logger.info(
            "Sending alert for %s on %s: Row %s Seats %s",
            recommendation.screening.label,
            recommendation.screening_date,
            suggestion.row_number,
            ", ".join(map(str, suggestion.seat_numbers)),
        )
        self.notifier.send_alert_sync(message, screenshot_path=screenshot_path)

    def _format_message(
        self,
        screening: ScreeningDescriptor,
        screening_date: date,
        suggestion: SeatBlockSuggestion,
        *,
        has_attachment: bool = False,
    ) -> str:
        seats = ", ".join(str(num) for num in suggestion.seat_numbers)
        attachment_line = "\nSeat map preview attached." if has_attachment else ""
        return (
            "🎬 Seat Alert\n\n"
            f"Movie: {self.app_config.movie_name_slug}\n"
            f"Date: {screening_date} at {screening.label}\n"
            f"Row: {suggestion.row_number} — Seats: {seats}\n"
            f"Score: {suggestion.score:.2f}\n"
            f"Booking Link: {normalize_order_url(screening.order_url)}"
            f"{attachment_line}"
        )

    def _notify_if_no_new_screening_day(self) -> None:
        if not hasattr(self.advisor, "last_screening_dates"):
            return
        if not self.advisor.last_screening_dates:
            logger.info("No screening dates discovered; skipping latest-date tracking.")
            return

        latest_seen = max(self.advisor.last_screening_dates)
        previous = self._load_latest_screening_date()
        if previous is None or latest_seen > previous:
            self._store_latest_screening_date(latest_seen)
            logger.info(
                "Stored latest screening date (%s) in %s",
                latest_seen.isoformat(),
                self._latest_date_path,
            )
            return

        message = (
            "📅 No new screening day yet.\n\n"
            f"Latest available screening date remains {previous.isoformat()}."
        )
        self.notifier.send_alert_sync(message)

    def _load_latest_screening_date(self) -> Optional[date]:
        try:
            if not self._latest_date_path.exists():
                return None
            content = self._latest_date_path.read_text(encoding="utf-8").strip()
            if not content:
                return None
            return date.fromisoformat(content)
        except Exception as exc:
            logger.debug("Failed to read latest screening date: %s", exc)
            return None

    def _store_latest_screening_date(self, latest: date) -> None:
        try:
            self._latest_date_path.parent.mkdir(parents=True, exist_ok=True)
            self._latest_date_path.write_text(latest.isoformat(), encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to store latest screening date: %s", exc)

    def _default_latest_date_path(self) -> Path:
        base_dir = Path.home() / ".local" / "share" / "cinema-monitor"
        return base_dir / self._LATEST_DATE_FILENAME

    def _filter_suggestions(self, recommendation: SeatRecommendation) -> List[SeatBlockSuggestion]:
        filtered: List[SeatBlockSuggestion] = []
        min_score = self.scheduler_config.min_score
        for suggestion in recommendation.suggestions:
            if min_score is not None and suggestion.score < min_score:
                logger.debug(
                    "Skipping suggestion below min_score %.2f for %s",
                    min_score,
                    recommendation.screening.label,
                )
                continue
            if (
                self.scheduler_config.avoid_aisle
                and self.scheduler_config.aisle_boundary > 0
                and self._is_near_aisle(recommendation.seat_map, suggestion)
            ):
                logger.debug(
                    "Skipping suggestion near aisle (boundary=%s) for %s",
                    self.scheduler_config.aisle_boundary,
                    recommendation.screening.label,
                )
                continue
            filtered.append(suggestion)
        return filtered

    def _is_near_aisle(self, seat_map: SeatMap, suggestion: SeatBlockSuggestion) -> bool:
        boundary = max(self.scheduler_config.aisle_boundary, 0)
        if boundary == 0:
            return False

        row = seat_map.rows.get(suggestion.row_number)
        if not row or not row.seats:
            return False

        row_min = min(seat.grid_x for seat in row.seats)
        row_max = max(seat.grid_x for seat in row.seats)
        seat_lookup = {seat.seat_number: seat for seat in row.seats}

        for idx, seat_number in enumerate(suggestion.seat_numbers):
            seat = seat_lookup.get(seat_number)
            if seat:
                grid_x = seat.grid_x
            elif idx < len(suggestion.grid_positions):
                grid_x = suggestion.grid_positions[idx]
            else:
                continue

            if (grid_x - row_min) < boundary or (row_max - grid_x) < boundary:
                return True

        return False
