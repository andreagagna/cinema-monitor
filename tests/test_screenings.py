from datetime import date, time
from pathlib import Path

import httpx

from src.config import AppConfig
from src.screenings import ScreeningDescriptor, ScreeningDiscovery, filter_screenings_for_config

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_discovery_returns_all_screenings_without_filters():
    html = load_fixture("movie_page.html")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    discovery = ScreeningDiscovery(transport=httpx.MockTransport(handler))
    config = AppConfig()

    screenings = discovery.discover("https://example.com/movie", config)
    assert len(screenings) == 3
    assert {s.order_url for s in screenings} == {
        "https://tickets.example.com/order/111",
        "https://tickets.example.com/order/222",
        "https://tickets.example.com/order/333",
    }


def test_discovery_applies_time_and_weekday_filters():
    html = load_fixture("movie_page.html")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    discovery = ScreeningDiscovery(transport=httpx.MockTransport(handler))
    config = AppConfig(
        date="2025-12-17",  # Wednesday
        earliest_show_time="18:00",
        allowed_weekdays="mon,tue,wed,thu,fri",
    )

    screenings = discovery.discover("https://example.com/movie", config)
    assert len(screenings) == 2
    assert [s.order_url for s in screenings] == [
        "https://tickets.example.com/order/222",
        "https://tickets.example.com/order/333",
    ]


def test_filter_screenings_for_config_honours_target_date():
    config = AppConfig(date="2025-12-17", earliest_show_time="18:00", allowed_weekdays="fri")
    # Config date is Wednesday, but target_date Friday should allow screening.
    screenings = [
        ScreeningDescriptor(label="17:30", show_time=time(17, 30), order_url="early"),
        ScreeningDescriptor(label="18:30", show_time=time(18, 30), order_url="late"),
    ]
    filtered = filter_screenings_for_config(screenings, config, target_date=date(2025, 12, 19))
    assert [s.order_url for s in filtered] == ["late"]
