from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterator, Optional, Set


@dataclass(frozen=True)
class DateSweepConfig:
    """Configuration for generating candidate dates."""

    start_date: date
    days: int = 7
    include_weekends: bool = True
    allowed_weekdays: Optional[Set[int]] = None


def iter_available_dates(config: DateSweepConfig) -> Iterator[date]:
    """Yield dates starting at `start_date` while respecting weekday filters."""
    current = config.start_date

    for _ in range(max(config.days, 0)):
        weekday = current.weekday()

        if not config.include_weekends and weekday >= 5 and not config.allowed_weekdays:
            current += timedelta(days=1)
            continue

        if config.allowed_weekdays and weekday not in config.allowed_weekdays:
            current += timedelta(days=1)
            continue

        yield current
        current += timedelta(days=1)
