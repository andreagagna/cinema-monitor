from datetime import date

from src.date_sweep import DateSweepConfig, iter_available_dates


def test_iter_available_dates_respects_length():
    config = DateSweepConfig(start_date=date(2026, 1, 5), days=1)
    dates = list(iter_available_dates(config))
    assert dates == [date(2026, 1, 5)]


def test_iter_available_dates_filters_weekdays():
    config = DateSweepConfig(
        start_date=date(2026, 1, 5),  # Monday
        days=1,
        allowed_weekdays={1},  # Tuesday only
    )
    dates = list(iter_available_dates(config))
    assert dates == []
