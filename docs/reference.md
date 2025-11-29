# Reference

## Configuration Tables

### AppConfig

| Env var / field | Default | Description |
| --- | --- | --- |
| `CINEMA_BASE_URL` | `https://www.cinemacity.cz` | Base domain for movie URLs. |
| `MOVIE_NAME_SLUG` | `avatar-ohen-a-popel` | Slug component of the film. |
| `MOVIE_ID` | `7148s2r` | Cinema City internal movie ID. |
| `CITY` | `prague` | Cinema location identifier. |
| `DATE` | `2025-12-17` | Baseline date (ISO). |
| `FILM_FORMAT` | `imax` | Filter for hall format (`4dx`, `vip`, etc.). |
| `VIEW_MODE` | `list` | Booking page view mode. |
| `EARLIEST_SHOW_TIME` | unset | HH:MM string to skip early shows. |
| `ALLOWED_WEEKDAYS` | unset | Comma-separated weekdays (`fri,sat`). |
| `TELEGRAM_BOT_TOKEN` | unset | Telegram bot token (optional). |
| `TELEGRAM_CHAT_ID` | unset | Target chat ID (optional). |
| `LOG_LEVEL` | `INFO` | Global logging level (`DEBUG`, `INFO`, etc.). |
| `LOG_FILE` | unset | Optional path to a rotating log file. |

### SchedulerConfig

| Field | Default | Description |
| --- | --- | --- |
| `poll_interval_seconds` | `300` | Delay between successive runs in `run_forever`. |
| `max_retries` | `3` | Retry attempts in `poll_with_retry`. |
| `backoff_factor` | `2.0` | Multiplier for exponential backoff. |
| `horizon_days` | `3` | Number of days beyond `DATE` to check. |
| `party_size` | `2` | Seats per suggestion. |
| `top_n` | `3` | How many suggestions to emit per screening. |
| `include_wheelchair` | `False` | Include wheelchair seats in scoring. |

## CLI / Entry Points

- **`uv run cinema-monitor`** – Entry point defined in `pyproject.toml`
  (`cinema-monitor = "src.main:main"`). Respects `.env` variables before
  instantiating `SeatAdvisor`, `Notifier`, and `MonitorScheduler`.
- **Custom scripts** – Import `AppConfig`, `SeatAdvisor`, `MonitorScheduler`,
  and `Notifier` to tailor schedulers (see tutorials).

## API Objects

- `ScreeningDescriptor` (`src/screenings.py`) – label, `show_time`, `order_url`,
  and metadata parsed from the movie page.
- `SeatBlockSuggestion` (`src/seat_selection.py`) – row number, seat numbers,
  labels, grid positions, and score for a contiguous block or single seat.
- `SeatRecommendation` (`src/advisor.py`) – wraps a `ScreeningDescriptor`,
  screening date, and list of `SeatBlockSuggestion`s.
- `SeatAdvisor.recommend(...) -> List[SeatRecommendation]` – accepts
  `AppConfig`, `party_size`, `top_n`, `include_wheelchair`, optional dates.

## Logging & Metrics

- Default logging uses Python’s `logging` module with INFO-level console output.
- Planned upgrade: structured logging (JSON) with rotating file handler. Fields
  to include: `timestamp`, `event`, `screening_date`, `order_url`, `party_size`,
  `attempt`, `error`. Track this in `docs/improvements.md`.
- Place log files in `logs/cinema-monitor.log` (or similar) and document how to
  configure them once implemented.

## File & Directory Layout

- `src/config.py` – configuration helpers.
- `src/screenings.py` / `screenings_browser.py` – discovery (HTTP + Playwright).
- `src/seatmap_fetcher.py` / `seat_map.py` – seat map fetching/parsing.
- `src/seat_selection.py` – scoring and selection logic.
- `src/advisor.py` – orchestrator.
- `src/scheduler.py` – scheduler loops.
- `src/notifier.py` – Telegram notifier (replaceable).

For practical workflows and code snippets, consult:

- Tutorials (`docs/tutorials/`) – daily monitoring, seat scoring customisation.
- How-To Guides (`docs/how-to/`) – date sweeps, custom notifiers, etc.
