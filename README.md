# Cinema Monitor

A Python-based tool to monitor a cinema website for specific movie availability and send notifications via Telegram.

## Description

Cinema Monitor watches the Cinema City booking site for any movie/city/format you
configure, evaluates the available seats, and pings you (via Telegram or a
custom notifier) when worthwhile seats appear or new dates drop. The default
configuration ships with the “Avatar: Fire and Ashes” IMAX showings as an
example, but every step in the pipeline is configurable.

## Features

- Monitors availability for a specific movie and format.
- Checks for new dates in the schedule.
- Sends notifications via Telegram.
- Renders seat-map previews that highlight the recommended seats and attaches
  them to Telegram alerts.
- Filters out low-scoring or aisle-edge seats via configurable thresholds so
  alerts only surface the best blocks.

## Quickstart

1. **Clone & install**
   ```bash
   git clone <repository-url>
   cd cinema-monitor
   uv sync
   uv run playwright install chromium
   ```
2. **Configure credentials** – copy `.env.example` to `.env`, set
   `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`, and tweak any movie/date settings.
3. **Run it once**
   ```bash
   uv run cinema-monitor
   ```
   You should see log lines such as
   `INFO SeatAdvisor ... Sending alert for 2026-01-05 ...` and (if Telegram is
   configured) receive a message describing the suggested seats.

See `docs/quickstart.md` for a more interactive walkthrough.

## Tech Stack

- Python 3.10+
- uv (dependency and tool launcher)
- Playwright (dynamic showtime discovery fallback)
- httpx + BeautifulSoup (HTML/SVG parsing)
- python-telegram-bot (default notifier)

## Setup & Usage

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd cinema-monitor
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    # OR
    pip install -r requirements.txt
    ```

3.  **Install Playwright browsers:**
    ```bash
    uv run playwright install chromium
    ```

### Configuration Overview

`AppConfig` (in `src/config.py`) pulls values from environment variables, so you
can control the monitor without editing code. Common options:

| Env var / field            | Description                                                                 | Default                    |
| -------------------------- | --------------------------------------------------------------------------- | -------------------------- |
| `MOVIE_NAME_SLUG`          | Slug portion of the film URL (e.g. `avatar-ohen-a-popel`).                  | `avatar-ohen-a-popel`      |
| `MOVIE_ID`                 | Cinema City internal film identifier.                                       | `7148s2r`                  |
| `CITY`                     | Cinema location (e.g. `prague`).                                            | `prague`                   |
| `DATE`                     | ISO date for the first sweep.                                               | `2026-01-05`               |
| `FILM_FORMAT`              | Booking filter such as `imax`, `4dx`, etc.                                  | `imax`                     |
| `EARLIEST_SHOW_TIME`       | Filter showings earlier than HH:MM.                                         | unset                      |
| `ALLOWED_WEEKDAYS`         | Comma-separated weekdays to include (`mon,fri`).                            | unset (all days)           |
| `TELEGRAM_BOT_TOKEN/CHAT`  | Notifier credentials (optional; falls back to logging if unset).            | unset                      |
| `MIN_SCORE`                | Minimum acceptable seat score.                                              | `0.8`                      |
| `AVOID_AISLE`              | Skip seats near the aisle edges.                                            | `True`                     |
| `AISLE_DISTANCE`           | How many seats per side count as “aisle”.                                   | `3`                        |

AppConfig now also owns the logging knobs: set `LOG_LEVEL=DEBUG` (or another
standard level) to increase verbosity and `LOG_FILE=/path/to/cinema.log` to
write a rotating log file alongside the console output. The default log file
path is `logs/cinema-monitor.log` in the current working directory. These two
variables do not contain secrets, so it is safe to commit/share them when
debugging, but keep private values (bot tokens, passwords, etc.) out of public
configs.

Seat filtering defaults to `MIN_SCORE=0.8` and treats the first/last three seats
in each row as aisle blocks. Lower the score threshold or set `AVOID_AISLE=false`
if you want more relaxed alerts, or increase `AISLE_DISTANCE` for stricter edge
avoidance.

See `docs/reference.md` for the full list, including scheduler options like
`party_size`, `top_n`, and logging destinations.

### Running the Monitor

Execute the monitor via the project script:
```bash
uv run cinema-monitor
```

The script will:
1.  Use `SeatAdvisor` + `MonitorScheduler` to sweep the configured date range.
2.  Fetch seat maps via HTTP, parse the SVG, and evaluate seat quality.
3.  Send Telegram alerts (if configured) for the best available seats.

## Key Components

- **SeatAdvisor (`src/advisor.py`)** – orchestrates discovery → seat-map fetch →
  parsing → seat selection and returns ranked suggestions.
- **MonitorScheduler (`src/scheduler.py`)** – sweeps date ranges, retries on
  failures, and dispatches alerts at intervals.
- **Notifier (`src/notifier.py`)** – default Telegram transport with fallback
  hooks for custom channels.
- **CLI (`cinema-monitor`)** – entry point defined in `pyproject.toml`, wired
  via `src/main.py`.

If you want to build on the library APIs, start with `docs/overview.md` and the
tutorials in `docs/tutorials/`.

## Further Documentation

The `docs/` folder contains didactic guides:

- `docs/index.md` – documentation landing page.
- `docs/overview.md` – architecture and data flow.
- `docs/quickstart.md` – guided first run.
- `docs/tutorials/` – end-to-end walkthroughs (daily monitoring, seat scoring).
- `docs/how-to/` – focused recipes (date sweeps, custom notifiers, etc.).
- `docs/reference.md` – config/API tables.
- `docs/troubleshooting.md` – FAQ and debugging tips.
- `docs/decisions.md` – rationale behind major choices.

## Development

We run formatting/linting/type checks in CI:

```bash
ruff check .
black --check .
mypy src
pytest
```

The GitHub Actions workflow `.github/workflows/ci.yml` mirrors these commands.

## Troubleshooting

- **Playwright install errors:** re-run `uv run playwright install chromium`.
  On CI or headless servers, ensure the required system libraries are present
  (see the Playwright docs linked from `docs/troubleshooting.md`).
- **Telegram alerts missing:** confirm `TELEGRAM_BOT_TOKEN` and
  `TELEGRAM_CHAT_ID` are set, and that the bot has messaged the chat before
  running. The scheduler logs “Fallback alert (reason: missing_config)” if
  credentials are missing.
- **No seats found:** loosen filters (`EARLIEST_SHOW_TIME`, `ALLOWED_WEEKDAYS`,
  `party_size`) or enable wheelchair inclusion. Logs note when all screenings
  are filtered out.
- **CAPTCHA or seat-map fetch failures:** watch for warnings mentioning
  CAPTCHA; rerun later or switch to the browser discovery path. See
  `docs/troubleshooting.md` for mitigation ideas.

## Working with AI / Contributors

- Read `agents.md` for coding standards, architecture expectations, and how AI
  assistants should operate when touching this repo.
- Document changes as you go (update README/docs + `docs/decisions.md` in the
  same PR).
- Keep the improvements log in `docs/improvements.md` in sync when you tackle or
  add new work items.
