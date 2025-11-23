from datetime import date

from src.date_sweep import DateSweepConfig, iter_available_dates


def test_iter_available_dates_respects_length():
    config = DateSweepConfig(start_date=date(2025, 12, 17), days=3)
    dates = list(iter_available_dates(config))
    assert dates == [
        date(2025, 12, 17),
        date(2025, 12, 18),
        date(2025, 12, 19),
    ]


def test_iter_available_dates_filters_weekdays():
    config = DateSweepConfig(
        start_date=date(2025, 12, 17),  # Wednesday
        days=5,
        allowed_weekdays={2, 3, 4},  # Wed, Thu, Fri
    )
    dates = list(iter_available_dates(config))
    assert dates == [
        date(2025, 12, 17),
        date(2025, 12, 18),
        date(2025, 12, 19),
    ]
