# Architecture & Flow

This project is evolving from a screenshot-based scraper into a reusable library that works directly with Cinema City’s HTML/SVG data. The goal is to keep each concern isolated so that future contributors (human or AI) can swap parts without touching the rest.

## High-Level Flow

```
AppConfig  ─┐
            ├─> ScreeningDiscovery ──> [ScreeningDescriptor...]
Date sweep ─┘
                   │
                   ▼
           SeatMapFetcher (per screening)
                   │
                   ▼
            SeatMapParser → SeatMap (Seat, SeatRow)
                   │
                   ▼
             SeatSelector / scoring
                   │
                   ▼
        SeatAdvisor (public API) ──> Suggestions, alerts, schedulers, bots
```

## Modules & Responsibilities

| Module | Responsibility | Notes |
| --- | --- | --- |
| `src/config.py` (`AppConfig`) | Centralises configuration: movie identifiers, date, filtering preferences (earliest show, allowed weekdays), Telegram settings, etc. Provides helpers to parse dates/times. | Keeps “magic” values in one place and allows future CLI/env overrides. |
| `src/screenings.py` (`ScreeningDiscovery`) | Downloads the movie page, extracts every `<a.btn.btn-primary.btn-lg>` showtime, and emits `ScreeningDescriptor` objects. Applies `AppConfig` filters (time-of-day, weekday). | Uses `httpx` + BeautifulSoup, making it easy to mock in tests. |
| `src/date_sweep.py` | Provides `DateSweepConfig` + `iter_available_dates`, which iterate day-by-day while respecting weekday filters. Higher layers can plug this into the advisor to scan multiple dates. | Redirect detection (when the site jumps to the next available date) can be layered on top by comparing requested vs returned dates. |
| `src/seatmap_fetcher.py` | Performs plain HTTP GET on the `data-url` booking link and extracts `<svg id="svg-seatmap">`. | No browser automation, so it’s fast and testable. |
| `src/seat_map.py` | Parses the SVG into domain objects (`Seat`, `SeatRow`, `SeatMap`). Each seat records logical row/seat numbers, grid coordinates (`s="…,x,row"`), availability (`SeatStatus`), and optional metadata. | The `SeatMapParser` only knows about SVG DOM; it doesn’t talk to HTTP or scoring logic. |
| `src/seat_selection.py` | Consumes `SeatMap` and produces recommendations. Implements configurable scoring (row/column weights), filters wheelchair seats when requested, and finds contiguous blocks via sliding windows over grid indices. | No HTML/SVG knowledge—pure data transformations. |
| `src/advisor.py` (`SeatAdvisor`) | Public API tying dates → discovery → seat-map fetch → parsing → seat selection. Returns serialisable `SeatRecommendation` objects for downstream bots/CLI. | Falls back to `BrowserScreeningDiscovery` (Playwright) when static HTML doesn’t expose showtimes. |
| `src/screenings_browser.py` | Playwright helper that loads the movie page, waits for dynamically injected showtime buttons, and extracts their `data-url`. | Keeps browser automation isolated so most tests stay fast; headless mode/timeouts are configurable. |
| `src/scheduler.py` (`MonitorScheduler`) | Scheduler loop that plugs `SeatAdvisor` + `Notifier`, iterates dates (via `date_sweep`), applies retry/backoff, and formats notifications. | Provides `run_once`, `poll_with_retry`, and `run_forever` for CLI/bots; sleeps and retries are injectable for tests. |
| `src/seatmap_fetcher.py`, `tests/fixtures/*.html/.svg` | Provide deterministic inputs for the parser and selector tests. | Ensures regressions are caught when Cinema City changes markup. |

## Key Design Choices

1. **HTML/SVG over screenshots** – fetching the booking page directly exposes machine-readable seat data. We avoid fragile visual heuristics, and parsing is deterministic.
2. **Composable steps** – each stage (discovery → fetch → parse → select) is a small Python module with typed inputs/outputs. This lets us unit-test almost everything without hitting the real site.
3. **Domain-first modelling** – the `SeatMap` aggregate offers convenient row/group queries. Higher layers need only this model, never raw HTML.
4. **Config-driven filtering** – time/day limits live in `AppConfig`, so automatic monitors (scheduler, Telegram bot) can share one source of truth without scattering logic.
5. **Test fixtures for every layer** – we store representative snippets in `tests/fixtures/` so future contributors can reproduce and extend scenarios offline.

## How to Extend

* **Date sweeping**: use `DateSweepConfig` + `iter_available_dates()` when you need a different horizon/weekday policy. If the site redirects to a different date, compare the requested vs returned date in `SeatAdvisor` to avoid duplicates.
* **Seat suggestions**: downstream services (CLI, Telegram bot) should depend on `SeatAdvisor` or `MonitorScheduler.run_once()`, which already delivers JSON-friendly `SeatRecommendation` objects. Pass a custom `BrowserScreeningDiscovery` if you need to tweak Playwright behaviour (non-headless, different timeouts/locale).
* **Scheduler tuning**: adjust `SchedulerConfig` (interval, retries, party size, `top_n`) to fit your deployment profile. Inject custom sleep functions or transports in tests to keep them deterministic.

For deeper design rationale, see `docs/decisions.md`.
