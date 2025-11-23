from pathlib import Path

import httpx
import pytest

from src.seatmap_fetcher import SeatMapFetcher, SeatMapFetcherError

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_fetcher_returns_svg_fragment():
    html = load_fixture("seatmap_page.html")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    fetcher = SeatMapFetcher(transport=httpx.MockTransport(handler))
    svg = fetcher.fetch_svg("https://tickets.example.com/order/111")
    assert "<svg" in svg
    assert 'id="svg-seatmap"' in svg


def test_fetcher_raises_when_svg_missing():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html></html>")

    fetcher = SeatMapFetcher(transport=httpx.MockTransport(handler))
    with pytest.raises(SeatMapFetcherError):
        fetcher.fetch_svg("https://tickets.example.com/order/000")
