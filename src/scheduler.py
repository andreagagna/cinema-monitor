from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable, List, Optional

from src.advisor import SeatAdvisor, SeatRecommendation
from src.config import AppConfig
from src.date_sweep import DateSweepConfig, iter_available_dates
from src.notifier import Notifier
from src.screenings import ScreeningDescriptor
from src.seat_selection import SeatBlockSuggestion

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


class MonitorScheduler:
    """Runs SeatAdvisor periodically with retry/backoff and notification dispatch."""

    def __init__(
        self,
        app_config: AppConfig,
        *,
        advisor: Optional[SeatAdvisor] = None,
        notifier: Optional[Notifier] = None,
        scheduler_config: Optional[SchedulerConfig] = None,
        date_iterator: Callable[[DateSweepConfig], Iterable[date]] = iter_available_dates,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.app_config = app_config
        self.advisor = advisor or SeatAdvisor()
        self.notifier = notifier or Notifier(app_config)
        self.scheduler_config = scheduler_config or SchedulerConfig()
        self.date_iterator = date_iterator
        self.sleep_fn = sleep_fn

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
            for suggestion in recommendation.suggestions:
                self._notify(recommendation, suggestion)
                dispatched += 1

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
        while True:
            try:
                self.poll_with_retry()
            except Exception as exc:
                logger.exception("Polling failed: %s", exc)
            self.sleep_fn(self.scheduler_config.poll_interval_seconds)

    def _notify(self, recommendation: SeatRecommendation, suggestion: SeatBlockSuggestion) -> None:
        message = self._format_message(
            recommendation.screening, recommendation.screening_date, suggestion
        )
        logger.info(
            "Sending alert for %s on %s: Row %s Seats %s",
            recommendation.screening.label,
            recommendation.screening_date,
            suggestion.row_number,
            ", ".join(map(str, suggestion.seat_numbers)),
        )
        self.notifier.send_alert_sync(message)

    def _format_message(
        self, screening: ScreeningDescriptor, screening_date: date, suggestion: SeatBlockSuggestion
    ) -> str:
        seats = ", ".join(str(num) for num in suggestion.seat_numbers)
        return (
            "🎬 Seat Alert\n\n"
            f"Movie: {self.app_config.movie_name_slug}\n"
            f"Date: {screening_date} at {screening.label}\n"
            f"Row: {suggestion.row_number} — Seats: {seats}\n"
            f"Score: {suggestion.score:.2f}\n"
            f"Booking Link: {screening.order_url}"
        )
