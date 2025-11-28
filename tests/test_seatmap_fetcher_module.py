from pathlib import Path

import httpx
import pytest

from src.seatmap_fetcher import SeatMapFetcher, SeatMapFetcherError

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def build_api_handler():
    presentation = load_fixture("presentation_api.json")
    seatplan = load_fixture("seatplan_api.json")
    seat_status = load_fixture("seat_status_api.json")

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "presentations" in url:
            return httpx.Response(200, text=presentation)
        if "seatplanV2" in url:
            return httpx.Response(200, text=seatplan)
        if "seats-statusV2" in url:
            return httpx.Response(200, text=seat_status)
        return httpx.Response(404, text="not found")

    return handler


def test_fetcher_builds_svg_from_api():
    fetcher = SeatMapFetcher(transport=httpx.MockTransport(build_api_handler()))
    svg = fetcher.fetch_svg("https://tickets.example.com/order/123")
    assert '<svg id="svg-seatmap">' in svg
    assert "row: 1 seat: 21" in svg
    assert 's="1,10,1"' in svg


def test_fetcher_falls_back_to_browser_fetcher():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="error")

    called = {"count": 0}

    def fake_browser_fetcher(url: str) -> str:
        called["count"] += 1
        return '<svg id="svg-seatmap"></svg>'

    fetcher = SeatMapFetcher(
        transport=httpx.MockTransport(handler),
        browser_fetcher=fake_browser_fetcher,
    )
    svg = fetcher.fetch_svg("https://tickets.example.com/order/999")
    assert called["count"] == 1
    assert svg.startswith("<svg")


def test_fetcher_handles_api_order_urls():
    fetcher = SeatMapFetcher(transport=httpx.MockTransport(build_api_handler()))
    svg = fetcher.fetch_svg("https://tickets.example.com/api/order/123")
    assert "svg-seatmap" in svg
