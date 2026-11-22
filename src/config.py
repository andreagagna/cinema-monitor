from __future__ import annotations

import os
import urllib.parse
from dataclasses import dataclass
from datetime import date as DateType
from datetime import datetime, time
from typing import Dict, Mapping, Optional, Set, Tuple

from dotenv import load_dotenv


@dataclass(frozen=True)
class MovieProfile:
    """Reusable preset describing a target movie and screening filter defaults."""

    name: str
    movie_title: str
    movie_name_slug: str
    movie_id: str
    city: str = "prague"
    cinema_filter: Optional[str] = None
    date: str = "2026-12-15"
    film_format: str = "imax"
    audio_language: Optional[str] = "en"
    allow_dubbed: bool = False
    horizon_days: int = 7


DUNE_PART_THREE_PROFILE = MovieProfile(
    name="dune-part-three",
    movie_title="Dune: Part Three",
    movie_name_slug="duna-cast-treti",
    movie_id="8105s2r",
    city="prague",
    cinema_filter="flora",
    date="2026-12-15",
    film_format="imax,70-mm",
    audio_language="en",
    allow_dubbed=False,
    horizon_days=7,
)

AVATAR_FIRE_AND_ASH_PROFILE = MovieProfile(
    name="avatar-fire-and-ash",
    movie_title="Avatar: Fire and Ash",
    movie_name_slug="avatar-ohen-a-popel",
    movie_id="7148s2r",
    city="prague",
    cinema_filter=None,
    date="2026-01-08",
    film_format="imax",
    audio_language="en",
    allow_dubbed=False,
    horizon_days=3,
)

DEFAULT_MOVIE_PRESET = DUNE_PART_THREE_PROFILE.name

MOVIE_PROFILES: Dict[str, MovieProfile] = {
    DUNE_PART_THREE_PROFILE.name: DUNE_PART_THREE_PROFILE,
    AVATAR_FIRE_AND_ASH_PROFILE.name: AVATAR_FIRE_AND_ASH_PROFILE,
}

_PRESET_ALIASES: Dict[str, str] = {
    "dune": DUNE_PART_THREE_PROFILE.name,
    "dune-3": DUNE_PART_THREE_PROFILE.name,
    "duna-cast-treti": DUNE_PART_THREE_PROFILE.name,
    "avatar": AVATAR_FIRE_AND_ASH_PROFILE.name,
    "avatar-ohen-a-popel": AVATAR_FIRE_AND_ASH_PROFILE.name,
}


def get_movie_profile(preset_name: str) -> MovieProfile:
    """Resolve a named MovieProfile (or alias), raising ValueError if unknown."""
    key = preset_name.strip().lower()
    canonical = _PRESET_ALIASES.get(key, key)
    profile = MOVIE_PROFILES.get(canonical)
    if profile is None:
        valid = ", ".join(sorted(MOVIE_PROFILES.keys()))
        raise ValueError(f"Unknown MOVIE_PRESET '{preset_name}'. Available presets: {valid}")
    return profile


def _get_env(environ: Mapping[str, str], name: str) -> Optional[str]:
    return environ.get(name)


def _get_str_env(environ: Mapping[str, str], name: str, default: str) -> str:
    raw = _get_env(environ, name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


def _get_optional_filter_env(
    environ: Mapping[str, str], name: str, default: Optional[str]
) -> Optional[str]:
    """Read an optional string filter where explicit empty/'none'/'all' disables filtering."""
    raw = _get_env(environ, name)
    if raw is None:
        return default
    stripped = raw.strip()
    if stripped.lower() in {"", "none", "all", "*"}:
        return None
    return stripped


def _get_float_env(
    environ: Mapping[str, str], name: str, default: Optional[float]
) -> Optional[float]:
    raw = _get_env(environ, name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid float for {name}: {raw}") from exc


def _get_bool_env(environ: Mapping[str, str], name: str, default: bool) -> bool:
    raw = _get_env(environ, name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean for {name}: {raw}")


def _get_int_env(environ: Mapping[str, str], name: str, default: int) -> int:
    raw = _get_env(environ, name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer for {name}: {raw}") from exc


def _get_log_level_env(
    environ: Mapping[str, str], name: str, default: Optional[str]
) -> Optional[str]:
    raw = _get_env(environ, name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"", "0", "false", "off", "none"}:
        return None
    return raw.strip()


@dataclass(frozen=True)
class AppConfig:
    """Container for monitor configuration."""

    base_url: str = "https://www.cinemacity.cz"
    user_email: Optional[str] = None
    user_password: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    log_level: Optional[str] = None
    log_file: Optional[str] = "logs/cinema-monitor.log"
    min_score: Optional[float] = 0.8
    avoid_aisle: bool = True
    aisle_distance: int = 3
    movie_preset: str = DEFAULT_MOVIE_PRESET
    movie_title: str = DUNE_PART_THREE_PROFILE.movie_title
    movie_name_slug: str = DUNE_PART_THREE_PROFILE.movie_name_slug
    movie_id: str = DUNE_PART_THREE_PROFILE.movie_id
    city: str = DUNE_PART_THREE_PROFILE.city
    cinema_filter: Optional[str] = DUNE_PART_THREE_PROFILE.cinema_filter
    date: str = DUNE_PART_THREE_PROFILE.date
    film_format: str = DUNE_PART_THREE_PROFILE.film_format
    audio_language: Optional[str] = DUNE_PART_THREE_PROFILE.audio_language
    allow_dubbed: bool = DUNE_PART_THREE_PROFILE.allow_dubbed
    view_mode: str = "list"
    lang: str = "en_GB"
    earliest_show_time: Optional[str] = None
    allowed_weekdays: Optional[str] = None
    horizon_days: int = DUNE_PART_THREE_PROFILE.horizon_days
    party_size: int = 2
    top_n: int = 3
    include_wheelchair: bool = False
    poll_interval_seconds: int = 300

    @classmethod
    def from_profile(cls, preset_name: str, **overrides: object) -> "AppConfig":
        """Build an AppConfig seeded from a named MovieProfile plus optional field overrides."""
        profile = get_movie_profile(preset_name)
        base_kwargs: Dict[str, object] = {
            "movie_preset": profile.name,
            "movie_title": profile.movie_title,
            "movie_name_slug": profile.movie_name_slug,
            "movie_id": profile.movie_id,
            "city": profile.city,
            "cinema_filter": profile.cinema_filter,
            "date": profile.date,
            "film_format": profile.film_format,
            "audio_language": profile.audio_language,
            "allow_dubbed": profile.allow_dubbed,
            "horizon_days": profile.horizon_days,
        }
        base_kwargs.update(overrides)
        return cls(**base_kwargs)  # type: ignore[arg-type]

    @classmethod
    def from_env(
        cls,
        environ: Optional[Mapping[str, str]] = None,
        *,
        load_dotenv_file: bool = True,
    ) -> "AppConfig":
        """Create a config instance by reading environment variables."""
        if environ is None:
            if load_dotenv_file:
                load_dotenv()
            env_map: Mapping[str, str] = os.environ
        else:
            env_map = environ

        preset_raw = _get_str_env(env_map, "MOVIE_PRESET", cls.movie_preset)
        profile = get_movie_profile(preset_raw)

        movie_name_slug = _get_str_env(env_map, "MOVIE_NAME_SLUG", profile.movie_name_slug)
        default_title = (
            profile.movie_title
            if movie_name_slug == profile.movie_name_slug
            else movie_name_slug.replace("-", " ").title()
        )

        return cls(
            base_url=_get_str_env(env_map, "CINEMA_BASE_URL", cls.base_url),
            user_email=_get_env(env_map, "USER_EMAIL"),
            user_password=_get_env(env_map, "USER_PASSWORD"),
            telegram_bot_token=_get_env(env_map, "TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=_get_env(env_map, "TELEGRAM_CHAT_ID"),
            log_level=_get_log_level_env(env_map, "LOG_LEVEL", cls.log_level),
            log_file=_get_str_env(env_map, "LOG_FILE", cls.log_file or "logs/cinema-monitor.log"),
            min_score=_get_float_env(env_map, "MIN_SCORE", cls.min_score),
            avoid_aisle=_get_bool_env(env_map, "AVOID_AISLE", cls.avoid_aisle),
            aisle_distance=_get_int_env(env_map, "AISLE_DISTANCE", cls.aisle_distance),
            movie_preset=profile.name,
            movie_title=_get_str_env(env_map, "MOVIE_TITLE", default_title),
            movie_name_slug=movie_name_slug,
            movie_id=_get_str_env(env_map, "MOVIE_ID", profile.movie_id),
            city=_get_str_env(env_map, "CITY", profile.city),
            cinema_filter=_get_optional_filter_env(env_map, "CINEMA_FILTER", profile.cinema_filter),
            date=_get_str_env(env_map, "DATE", profile.date),
            film_format=_get_optional_filter_env(env_map, "FILM_FORMAT", profile.film_format) or "",
            audio_language=_get_optional_filter_env(
                env_map, "AUDIO_LANGUAGE", profile.audio_language
            ),
            allow_dubbed=_get_bool_env(env_map, "ALLOW_DUBBED", profile.allow_dubbed),
            view_mode=_get_str_env(env_map, "VIEW_MODE", cls.view_mode),
            lang=_get_str_env(env_map, "CINEMA_LANG", cls.lang),
            earliest_show_time=_get_optional_filter_env(
                env_map, "EARLIEST_SHOW_TIME", cls.earliest_show_time
            ),
            allowed_weekdays=_get_optional_filter_env(
                env_map, "ALLOWED_WEEKDAYS", cls.allowed_weekdays
            ),
            horizon_days=_get_int_env(env_map, "HORIZON_DAYS", profile.horizon_days),
            party_size=_get_int_env(env_map, "PARTY_SIZE", cls.party_size),
            top_n=_get_int_env(env_map, "TOP_N", cls.top_n),
            include_wheelchair=_get_bool_env(env_map, "INCLUDE_WHEELCHAIR", cls.include_wheelchair),
            poll_interval_seconds=_get_int_env(
                env_map, "POLL_INTERVAL_SECONDS", cls.poll_interval_seconds
            ),
        )

    def format_tokens(self) -> Tuple[str, ...]:
        """Return normalized format tokens (e.g. ('imax', '70-mm'))."""
        if not self.film_format:
            return ()
        tokens = [part.strip().lower() for part in self.film_format.split(",") if part.strip()]
        return tuple(tokens)

    def cinema_filter_tokens(self) -> Tuple[str, ...]:
        """Return normalized cinema filter tokens, expanding known Cinema City venue IDs."""
        if not self.cinema_filter:
            return ()
        tokens = [part.strip().lower() for part in self.cinema_filter.split(",") if part.strip()]
        if "flora" in tokens and "1052" not in tokens:
            tokens.append("1052")
        return tuple(tokens)

    def movie_url(self) -> str:
        """Construct the ticket URL for the configured movie."""
        return self.movie_url_for_date(self.movie_date())

    def movie_url_for_date(self, target_date: DateType) -> str:
        path = f"/films/{self.movie_name_slug}/{self.movie_id}"
        query_params = {"lang": self.lang}
        fragment_path = "/buy-tickets-by-film"
        fragment_params: Dict[str, str] = {
            "in-cinema": self.city,
            "at": target_date.strftime("%Y-%m-%d"),
            "for-movie": self.movie_id,
        }
        formats = self.format_tokens()
        if len(formats) == 1:
            fragment_params["filtered"] = formats[0]
        fragment_params["view-mode"] = self.view_mode

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
