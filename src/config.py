import os
import urllib.parse
from dataclasses import dataclass
from datetime import date as DateType
from datetime import datetime, time
from typing import Optional, Set

from dotenv import load_dotenv

load_dotenv()


def _get_float_env(name: str, default: Optional[float]) -> Optional[float]:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {name}: {raw}") from exc


def _get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean for {name}: {raw}")


def _get_int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw}") from exc


@dataclass(frozen=True)
class AppConfig:
    """Container for monitor configuration."""

    base_url: str = "https://www.cinemacity.cz"
    user_email: Optional[str] = None
    user_password: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    log_level: Optional[str] = None
    log_file: Optional[str] = None
    min_score: Optional[float] = 0.8
    avoid_aisle: bool = True
    aisle_distance: int = 3
    movie_name_slug: str = "avatar-ohen-a-popel"
    movie_id: str = "7148s2r"
    city: str = "prague"
    date: str = "2026-01-05"
    film_format: str = "imax"
    view_mode: str = "list"
    lang: str = "en_GB"
    earliest_show_time: Optional[str] = None
    allowed_weekdays: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create a config instance by reading environment variables."""
        return cls(
            base_url=os.getenv("CINEMA_BASE_URL", cls.base_url),
            user_email=os.getenv("USER_EMAIL"),
            user_password=os.getenv("USER_PASSWORD"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            log_level=os.getenv("LOG_LEVEL"),
            log_file=os.getenv("LOG_FILE"),
            min_score=_get_float_env("MIN_SCORE", cls.min_score),
            avoid_aisle=_get_bool_env("AVOID_AISLE", cls.avoid_aisle),
            aisle_distance=_get_int_env("AISLE_DISTANCE", cls.aisle_distance),
            movie_name_slug=os.getenv("MOVIE_NAME_SLUG", cls.movie_name_slug),
            movie_id=os.getenv("MOVIE_ID", cls.movie_id),
            city=os.getenv("CITY", cls.city),
            date=os.getenv("DATE", cls.date),
            film_format=os.getenv("FILM_FORMAT", cls.film_format),
            view_mode=os.getenv("VIEW_MODE", cls.view_mode),
            # lang=os.getenv("LANG", cls.lang),
            earliest_show_time=os.getenv("EARLIEST_SHOW_TIME"),
            allowed_weekdays=os.getenv("ALLOWED_WEEKDAYS"),
        )

    def movie_url(self) -> str:
        """Construct the ticket URL for the configured movie."""
        return self.movie_url_for_date(self.movie_date())

    def movie_url_for_date(self, target_date: DateType) -> str:
        path = f"/films/{self.movie_name_slug}/{self.movie_id}"
        query_params = {"lang": self.lang}
        fragment_path = "/buy-tickets-by-film"
        fragment_params = {
            "in-cinema": self.city,
            "at": target_date.strftime("%Y-%m-%d"),
            "for-movie": self.movie_id,
            "filtered": self.film_format,
            "view-mode": self.view_mode,
        }

        query_string = urllib.parse.urlencode(query_params)
        fragment_string = urllib.parse.urlencode(fragment_params)
        return f"{self.base_url}{path}?{query_string}#{fragment_path}?{fragment_string}"

    def movie_date(self) -> DateType:
        return datetime.strptime(self.date, "%Y-%m-%d").date()

    def parsed_earliest_show_time(self) -> Optional[time]:
        if not self.earliest_show_time:
            return None
        return datetime.strptime(self.earliest_show_time, "%H:%M").time()

    def allowed_weekday_indices(self) -> Optional[Set[int]]:
        if not self.allowed_weekdays:
            return None
        mapping = {
            "mon": 0,
            "monday": 0,
            "tue": 1,
            "tuesday": 1,
            "wed": 2,
            "wednesday": 2,
            "thu": 3,
            "thursday": 3,
            "fri": 4,
            "friday": 4,
            "sat": 5,
            "saturday": 5,
            "sun": 6,
            "sunday": 6,
        }
        indices: Set[int] = set()
        for part in self.allowed_weekdays.split(","):
            key = part.strip().lower()
            if key in mapping:
                indices.add(mapping[key])
        return indices or None
