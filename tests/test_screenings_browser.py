from datetime import date

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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


class _FakePage:
    def __init__(self, initial_url: str, post_render_url: str, html: str | None):
        self.url = initial_url
        self._post_render_url = post_render_url
        self._html = html
        self._waited = False

    def wait_for_selector(self, selector: str, *, state: str, timeout: int):
        if self._html is None:
            raise PlaywrightTimeoutError("No screenings loaded")
        self._waited = True
        self.url = self._post_render_url

    def content(self) -> str:
        assert self._waited and self._html is not None
        return self._html


def test_browser_discovery_catches_post_render_spa_date_redirect():
    config = AppConfig(date="2026-12-20")
    page = _FakePage(
        initial_url=config.movie_url(),
        post_render_url=config.movie_url_for_date(date(2026, 12, 15)),
        html="""
        <section class="movie-row" data-cinema-id="1052">
          <div class="qb-movie-info-column">
            <a class="btn btn-primary btn-lg" data-url="/order/flora"
               data-attrs="70-mm,original-lang-en">19:00</a>
          </div>
        </section>
        """,
    )
    discovery = BrowserScreeningDiscovery()
    assert discovery._discover_from_page(page, config) == []  # type: ignore[arg-type]


def test_browser_discovery_returns_empty_when_no_showtimes_render():
    config = AppConfig()
    page = _FakePage(config.movie_url(), config.movie_url(), html=None)
    discovery = BrowserScreeningDiscovery()
    assert discovery._discover_from_page(page, config) == []  # type: ignore[arg-type]


def test_browser_discovery_uses_own_cinema_row_and_preserves_metadata():
    config = AppConfig(date="2026-12-15")
    page = _FakePage(
        initial_url=config.movie_url(),
        post_render_url=config.movie_url(),
        html="""
        <main>
          <section class="movie-row">
            <a href="/cinemas/flora#/buy-tickets-by-cinema?in-cinema=1052">Cinema City Flora</a>
            <div class="qb-movie-info-column">
              <a class="btn btn-primary btn-lg" data-url="/order/flora"
                 data-attrs="70-mm,subbed,first-subbed-lang-cs">20:15</a>
            </div>
          </section>
          <section class="movie-row">
            <div class="qb-movie-info-column">
              <a class="btn btn-primary btn-lg" data-url="/order/unknown"
                 data-attrs="imax,original-lang-en">20:30</a>
            </div>
          </section>
        </main>
        """,
    )
    discovery = BrowserScreeningDiscovery()
    result = discovery._discover_from_page(page, config)  # type: ignore[arg-type]
    assert [s.order_url for s in result] == ["/order/flora"]
    assert result[0].metadata["data-attrs"] == "70-mm,subbed,first-subbed-lang-cs"
    assert "1052" in result[0].metadata["cinema"]
