from datetime import date
from pathlib import Path

import httpx

from src.advisor import SeatAdvisor
from src.config import AppConfig
from src.screenings import ScreeningDiscovery
from src.seat_map import SeatMapParser
from src.seatmap_fetcher import SeatMapFetcher

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_advisor_returns_recommendations_for_party_size_two():
    movie_html = load_fixture("movie_page.html")
    seatmap_html = load_fixture("seatmap_page.html")

    def handler(request: httpx.Request) -> httpx.Response:
        if "films" in request.url.path:
            return httpx.Response(200, text=movie_html)
        elif "order" in request.url.path:
            return httpx.Response(200, text=seatmap_html)
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    advisor = SeatAdvisor(
        discovery=ScreeningDiscovery(transport=transport),
        fetcher=SeatMapFetcher(transport=transport, enable_browser_fallback=False),
        parser=SeatMapParser(),
    )

    config = AppConfig(date="2026-01-05")
    results = advisor.recommend(config, party_size=2, top_n=1, dates=[date(2025, 1, 6)])

    assert results
    # ensure each screening produced a suggestion block of size 2
    for recommendation in results:
        assert recommendation.screening_date == date(2025, 1, 6)
        assert (
            recommendation.suggestions[0].seat_numbers
            and len(recommendation.suggestions[0].seat_numbers) == 2
        )
        assert recommendation.seat_map.seats
