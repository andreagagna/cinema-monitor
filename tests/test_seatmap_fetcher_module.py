from datetime import date
from pathlib import Path

import httpx
import pytest

from src.seatmap_fetcher import SeatMapFetcher, SeatMapFetcherError

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_fetcher_returns_svg_via_http_fallback():
    html = load_fixture("seatmap_page.html")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL("https://tickets.example.com/order/111")
        return httpx.Response(200, text=html)

    fetcher = SeatMapFetcher(
        transport=httpx.MockTransport(handler),
        enable_browser_fallback=False,
    )
    svg = fetcher.fetch_svg("https://tickets.example.com/api/order/111")
    assert 'id="svg-seatmap"' in svg


def test_fetcher_raises_when_http_and_browser_fail():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="error")

    fetcher = SeatMapFetcher(
        transport=httpx.MockTransport(handler),
        enable_browser_fallback=False,
    )

    with pytest.raises(SeatMapFetcherError):
        fetcher.fetch_svg("https://tickets.example.com/order/000")


def test_fetcher_uses_injected_browser_fetcher():
    called = {"count": 0}

    def fake_browser_fetcher(url: str) -> str:
        called["count"] += 1
        return '<svg id="svg-seatmap"></svg>'

    fetcher = SeatMapFetcher(
        browser_fetcher=fake_browser_fetcher,
    )
    svg = fetcher.fetch_svg("https://tickets.example.com/order/999")
    assert called["count"] == 1
    assert svg.startswith("<svg")


def test_parse_presentation_date_handles_dec_to_jan_year_rollover():
    fetcher = SeatMapFetcher(enable_browser_fallback=False)
    fetcher._expected_date = date(2027, 1, 2)
    parsed = fetcher._parse_presentation_date_text("Sat Jan 2")
    assert parsed == date(2027, 1, 2)

    # Also resolves Dec date when expected date is in Dec 2026 even if run in Jan 2027
    parsed_dec = fetcher._parse_presentation_date_text(
        "Tue Dec 15", reference_date=date(2027, 1, 2)
    )
    assert parsed_dec == date(2026, 12, 15)
