from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterable, Iterator, Optional, Set


@dataclass(frozen=True)
class DateSweepConfig:
    start_date: date
    days: int = 7
    include_weekends: bool = True
    allowed_weekdays: Optional[Set[int]] = None


def iter_available_dates(config: DateSweepConfig) -> Iterator[date]:
    current = config.start_date
    seen_redirects: Set[date] = set()

    for _ in range(max(config.days, 0)):
        weekday = current.weekday()
        if config.allowed_weekdays and weekday not in config.allowed_weekdays:
            current += timedelta(days=1)
            continue
        yield current
        current += timedelta(days=1)
