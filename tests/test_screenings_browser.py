from datetime import date

from src.screenings_browser import _extract_date_from_url


def test_extract_date_from_url_fragment():
    url = (
        "https://www.cinemacity.cz/films/avatar/123?lang=en_GB"
        "#/buy-tickets-by-film?in-cinema=prague&at=2026-01-08&for-movie=123"
    )
    assert _extract_date_from_url(url) == date(2026, 1, 8)


def test_extract_date_from_url_missing():
    url = "https://www.cinemacity.cz/films/avatar/123?lang=en_GB"
    assert _extract_date_from_url(url) is None
