# Overview

Cinema Monitor is a reusable Python toolkit for tracking Cinema City
screenings, analysing seat maps, and delivering actionable alerts. It evolved
from a screenshot-based experiment into a modular library that fetches and
parses the HTML/SVG data directly, making the results deterministic, testable,
and easy to extend.

## Purpose

- Monitor any Cinema City movie/city/format for new showtimes or high-quality
  seats.
- Evaluate seat quality (single or contiguous blocks) according to configurable
  heuristics.
- Push results to Telegram (default) or any custom notification channel.

## Core Concepts

- **Screening Discovery** – Crawls the movie page (static HTML first, Playwright
  fallback) and yields `ScreeningDescriptor`s (time, metadata, booking URL),
  applying the same `AppConfig` filters (earliest time, weekdays) regardless of
  the discovery path.
- **Seat Map Domain** – Parses `<svg id="svg-seatmap">` markup into structured
  objects:
  - `Seat` – row number, seat label, grid coordinates, status (available,
    occupied, wheelchair, unknown).
  - `SeatRow` / `SeatMap` – aggregates for row-wise queries and global bounds.
- **Seat Selection** – `SeatSelector` scores individual seats or contiguous
  blocks, balancing distance from the hall centre, row preferences, and
  wheelchair inclusion. Produces `SeatBlockSuggestion`s.
- **SeatAdvisor** – Public API tying discovery → fetch → parse → selection for
  one or more dates, returning `SeatRecommendation`s.
- **MonitorScheduler & Notifiers** – Wrap SeatAdvisor with retry/backoff,
  date sweeping, and alert transport(s).

## Architecture Snapshot

| Module | Responsibility |
| --- | --- |
| `src/config.AppConfig` | Builds movie URLs, parses env vars (`MOVIE_ID`, `CITY`, filters). |
| `src/screenings.ScreeningDiscovery` | Static HTML showtime extraction and filtering. |
| `src/screenings_browser.BrowserScreeningDiscovery` | Playwright-based fallback when HTML lacks data. |
| `src/seatmap_fetcher.SeatMapFetcher` | HTTP client (with Playwright fallback) that fetches booking pages and isolates the SVG seat map. |
| `src/seat_map.SeatMapParser` | Converts SVG DOM into `Seat`, `SeatRow`, `SeatMap`. |
| `src/seat_selection.SeatSelector` | Scores seats/blocks according to configurable weights. |
| `src/advisor.SeatAdvisor` | Orchestrates full pipeline and emits ranked recommendations. |
| `src/scheduler.MonitorScheduler` | Schedules sweeps, handles retries/backoff, formats alerts. |
| `src/notifier.Notifier` | Telegram transport + fallback handler; pluggable for custom channels. |

## Data Flow

1. **Configuration + Date Sweep** – `AppConfig.from_env()` reads `.env`, builds
   the first movie URL, and `DateSweepConfig` yields the dates to check.
2. **Discovery** – For each date, `ScreeningDiscovery` scrapes static HTML.
   If no buttons appear, `BrowserScreeningDiscovery` uses Playwright to extract
   dynamically injected showtimes.
3. **Fetch & Parse Seat Maps** – `SeatMapFetcher` downloads the booking page,
   extracts the SVG, and `SeatMapParser` creates the seat domain model.
4. **Selection & Recommendations** – `SeatSelector` finds best singles or
   contiguous blocks; `SeatAdvisor` packages them as `SeatRecommendation`s.
5. **Scheduling & Notifications** – `MonitorScheduler` iterates dates, retries
   failures, and invokes `Notifier` to send alerts (Telegram, logs, or custom
   channels).

## Testing Strategy

- Use frozen HTML and SVG fixtures that represent common hall layouts and edge
  cases (full house, missing metadata, wheelchair rows).
- Unit-test each layer independently: discovery parsing, SVG parsing invariants,
  scoring heuristics, scheduler retry/backoff, notifier fallbacks.
- Add regression tests when Cinema City markup changes to prevent silent
  breakage.

## Extensibility Notes

- **New cinemas or formats** – Adjust `AppConfig` values or expose CLI flags to
  accept alternative slugs/IDs. Hall geometry assumptions can be extended in
  `SeatSelector`.
- **Seat scoring strategies** – Plug new heuristics into `SeatSelector` or wrap
  it with custom scoring modules; tests should cover the desired behaviour.
- **Notification channels** – Implement a drop-in replacement for
  `Notifier.send_alert`/`send_alert_sync`, and inject it into `MonitorScheduler`.
- **Structured logging/metrics** – Future work will adopt file-backed structured
  logging (see `docs/improvements.md`) so deployments can ship metrics/alerts to
  monitoring stacks.
