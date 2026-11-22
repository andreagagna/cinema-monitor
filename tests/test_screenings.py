from datetime import date, time
from pathlib import Path

import httpx

from src.config import AVATAR_FIRE_AND_ASH_PROFILE, DUNE_PART_THREE_PROFILE, AppConfig
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
        date="2026-01-05",  # Monday
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
    config = AppConfig(date="2025-01-06", earliest_show_time="18:00", allowed_weekdays="mon")
    # Config date differs; target_date should still be used for filtering.
    screenings = [
        ScreeningDescriptor(label="17:30", show_time=time(17, 30), order_url="early"),
        ScreeningDescriptor(label="18:30", show_time=time(18, 30), order_url="late"),
    ]
    filtered = filter_screenings_for_config(screenings, config, target_date=date(2026, 1, 5))
    assert [s.order_url for s in filtered] == ["late"]


def test_discovery_filters_non_english_or_non_imax():
    html = """
    <div class="qb-movie-info-column">
      <a class="btn btn-primary btn-lg"
         data-url="https://tickets.example.com/order/111"
         data-attrs="imax,original-lang-en,subbed">
        18:00
      </a>
      <a class="btn btn-primary btn-lg"
         data-url="https://tickets.example.com/order/222"
         data-attrs="imax,first-subbed-lang-cs,subbed">
        19:30
      </a>
      <a class="btn btn-primary btn-lg"
         data-url="https://tickets.example.com/order/333"
         data-attrs="vip,original-lang-en,subbed">
        20:00
      </a>
    </div>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    discovery = ScreeningDiscovery(transport=httpx.MockTransport(handler))
    config = AppConfig(date="2026-01-05")
    screenings = discovery.discover("https://example.com/movie", config)

    assert [s.order_url for s in screenings] == ["https://tickets.example.com/order/111"]


def test_dune_profile_defaults_and_env_overrides_ignore_dotenv():
    dune_cfg = AppConfig.from_env({}, load_dotenv_file=False)
    assert dune_cfg.movie_preset == DUNE_PART_THREE_PROFILE.name
    assert dune_cfg.movie_name_slug == "duna-cast-treti"
    assert dune_cfg.movie_id == "8105s2r"
    assert dune_cfg.cinema_filter == "flora"
    assert dune_cfg.format_tokens() == ("imax", "70-mm")
    # Multi-format omits `filtered=` so Quickbook returns both IMAX and 70-mm
    assert "filtered=" not in dune_cfg.movie_url()

    avatar_cfg = AppConfig.from_env(
        {"MOVIE_PRESET": "avatar-fire-and-ash", "DATE": "2026-01-12"},
        load_dotenv_file=False,
    )
    assert avatar_cfg.movie_id == AVATAR_FIRE_AND_ASH_PROFILE.movie_id
    assert avatar_cfg.movie_name_slug == "avatar-ohen-a-popel"
    assert avatar_cfg.date == "2026-01-12"
    assert "filtered=imax" in avatar_cfg.movie_url()


def test_discovery_accepts_70mm_and_rejects_dubbed_or_other_cinemas():
    html = """
    <div class="qb-cinema" data-cinema-id="1052">
      <h3 class="qb-cinema-title"><a href="/cinemas/flora/1052">Cinema City Flora</a></h3>
      <div class="qb-movie-info-column">
        <a class="btn btn-primary btn-lg"
           data-url="https://tickets.example.com/order/flora-70mm-en"
           data-attrs="70-mm,original-lang-en,first-subbed-lang-cs">
          17:30
        </a>
        <a class="btn btn-primary btn-lg"
           data-url="https://tickets.example.com/order/flora-imax-dubbed"
           data-attrs="imax,original-lang-en,dubbed,dubbed-lang-cs">
          14:00
        </a>
        <a class="btn btn-primary btn-lg"
           data-url="https://tickets.example.com/order/flora-imax-en"
           data-attrs="imax,original-lang-en,subbed">
          21:00
        </a>
      </div>
    </div>
    <div class="qb-cinema" data-cinema-id="1055">
      <h3 class="qb-cinema-title"><a href="/cinemas/chodov/1055">Cinema City Chodov</a></h3>
      <div class="qb-movie-info-column">
        <a class="btn btn-primary btn-lg"
           data-url="https://tickets.example.com/order/chodov-imax-en"
           data-attrs="imax,original-lang-en,subbed">
          20:00
        </a>
      </div>
    </div>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    discovery = ScreeningDiscovery(transport=httpx.MockTransport(handler))
    config = AppConfig(date="2026-12-15")
    screenings = discovery.discover("https://example.com/dune", config)

    assert [s.order_url for s in screenings] == [
        "https://tickets.example.com/order/flora-70mm-en",
        "https://tickets.example.com/order/flora-imax-en",
    ]
    assert "Flora" in screenings[0].metadata.get("cinema", "")


def test_discovery_handles_live_dune_attrs_without_explicit_original_lang():
    html = """
    <div class="row movie-row first-movie-row">
      <a href="https://www.cinemacity.cz/cinemas/flora#/buy-tickets-by-cinema?in-cinema=1052"
         class="qb-cinema-link"><h4 class="qb-cinema-name">Prague Flora, OC FLORA</h4></a>
      <div class="qb-movie-info-column">
        <a class="btn btn-primary btn-lg"
           data-url="https://tickets.cinemacity.cz/api/order/248958?lang=en"
           data-attrs="12-plus,2d,70-mm,action,adventure,drama,first-subbed-lang-cs,sci-fi,subbed">
          17:20
        </a>
        <a class="btn btn-primary btn-lg"
           data-url="https://tickets.cinemacity.cz/api/order/267895?lang=en"
           data-attrs="12-plus,2d,action,adventure,drama,first-subbed-lang-cs,sci-fi,subbed">
          18:00
        </a>
      </div>
    </div>
    <div class="row movie-row">
      <a href="https://www.cinemacity.cz/cinemas/chodov#/buy-tickets-by-cinema?in-cinema=1056"
         class="qb-cinema-link"><h4 class="qb-cinema-name">Prague Chodov</h4></a>
      <div class="qb-movie-info-column">
        <a class="btn btn-primary btn-lg"
           data-url="https://tickets.cinemacity.cz/api/order/267693?lang=en"
           data-attrs="12-plus,2d,4dx,action,adventure,drama,dubbed,dubbed-lang-cs,sci-fi">
          18:00
        </a>
      </div>
    </div>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html)

    discovery = ScreeningDiscovery(transport=httpx.MockTransport(handler))
    config = AppConfig()
    assert config.date == "2027-01-01"
    screenings = discovery.discover("https://example.com/dune", config)

    assert [s.order_url for s in screenings] == [
        "https://tickets.cinemacity.cz/api/order/248958?lang=en"
    ]
