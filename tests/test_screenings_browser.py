from datetime import date

from src.config import AppConfig
from src.screenings_browser import BrowserScreeningDiscovery, _extract_date_from_url


def test_extract_date_from_url_fragment():
    url = (
        "https://www.cinemacity.cz/films/avatar/123?lang=en_GB"
        "#/buy-tickets-by-film?in-cinema=prague&at=2026-01-08&for-movie=123"
    )
    assert _extract_date_from_url(url) == date(2026, 1, 8)


def test_extract_date_from_url_missing():
    url = "https://www.cinemacity.cz/films/avatar/123?lang=en_GB"
    assert _extract_date_from_url(url) is None


class _FakeAnchor:
    def __init__(self, url: str, attrs: str, label: str, cinema: str | None = None):
        self._url = url
        self._attrs = attrs
        self._label = label
        self._cinema = cinema

    def get_attribute(self, name: str) -> str | None:
        if name == "data-url":
            return self._url
        if name == "data-attrs":
            return self._attrs
        return None

    def inner_text(self) -> str:
        return self._label

    def evaluate(self, _script: str):
        return {"meta": {"data-attrs": self._attrs}, "cinema": self._cinema}


class _FakePage:
    def __init__(self, initial_url: str, post_render_url: str, anchors: list[_FakeAnchor]):
        self.url = initial_url
        self._post_render_url = post_render_url
        self._anchors = anchors
        self._waited = False

    def query_selector_all(self, _selector: str):
        if not self._waited:
            return []
        return self._anchors

    def wait_for_selector(self, _selector: str, timeout: int = 3000):
        self._waited = True
        self.url = self._post_render_url

    def wait_for_timeout(self, _ms: int):
        self._waited = True
        self.url = self._post_render_url


def test_browser_discovery_catches_post_render_spa_date_redirect():
    page = _FakePage(
        initial_url="https://www.cinemacity.cz/films/duna-cast-treti/8105s2r?lang=en_GB#/buy-tickets-by-film?at=2026-12-20",
        post_render_url="https://www.cinemacity.cz/films/duna-cast-treti/8105s2r?lang=en_GB#/buy-tickets-by-film?at=2026-12-15",
        anchors=[
            _FakeAnchor(
                "https://tickets.example.com/order/1",
                "70-mm,original-lang-en",
                "19:00",
                "Cinema City Flora | /cinemas/flora/1052",
            )
        ],
    )
    discovery = BrowserScreeningDiscovery()
    config = AppConfig(date="2026-12-20")
    result = discovery._discover_from_page(page, config, target_date=date(2026, 12, 20))  # type: ignore[arg-type]
    assert result == []


def test_browser_discovery_filters_cinema_and_preserves_metadata():
    page = _FakePage(
        initial_url="https://www.cinemacity.cz/films/duna-cast-treti/8105s2r?lang=en_GB#/buy-tickets-by-film?at=2026-12-15",
        post_render_url="https://www.cinemacity.cz/films/duna-cast-treti/8105s2r?lang=en_GB#/buy-tickets-by-film?at=2026-12-15",
        anchors=[
            _FakeAnchor(
                "https://tickets.example.com/order/flora",
                "70-mm,original-lang-en,subbed",
                "20:15",
                "Cinema City Flora | 1052",
            ),
            _FakeAnchor(
                "https://tickets.example.com/order/chodov",
                "imax,original-lang-en,subbed",
                "20:30",
                "Cinema City Chodov | 1055",
            ),
        ],
    )
    discovery = BrowserScreeningDiscovery()
    config = AppConfig(date="2026-12-15")
    result = discovery._discover_from_page(page, config, target_date=date(2026, 12, 15))  # type: ignore[arg-type]
    assert [s.order_url for s in result] == ["https://tickets.example.com/order/flora"]
    assert result[0].metadata["data-attrs"] == "70-mm,original-lang-en,subbed"
    assert "1052" in result[0].metadata["cinema"]
