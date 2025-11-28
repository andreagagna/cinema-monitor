# Design Decisions

This file summarises the main architectural choices behind the current implementation. Each entry explains **why** we chose the approach and **how** it shapes future work.

## 1. Switch from screenshots to SVG parsing
- **Why**: Screenshot-based detection was brittle (sensitive to colours, rendering artefacts, and Captcha). The booking page delivers the entire seat map as an SVG; parsing it is deterministic and significantly faster.
- **How**: We introduced `SeatMapFetcher` (HTTP only) and `SeatMapParser` (BeautifulSoup) to isolate network concerns from DOM parsing. The parser builds `Seat`, `SeatRow`, and `SeatMap` objects that upstream code can query without touching HTML.

## 2. Config-driven showtime filtering
- **Why**: Users often care about constraints like “after 18:00 on weekdays”. Encoding these once in `AppConfig` avoids duplicating logic across CLI/Scheduler/Bot layers.
- **How**: `AppConfig` parses `EARLIEST_SHOW_TIME` and `ALLOWED_WEEKDAYS` environment variables. `ScreeningDiscovery` applies those filters immediately after parsing the movie page.

## 3. Modular pipeline
- **Why**: The app needs to evolve (date sweeping, new scoring strategies, different alert transports). Keeping each concern as a focused module lowers coupling and keeps tests fast.
- **How**: Separate modules handle discovery, fetching, parsing, domain modelling, and seat selection. Tests use mock transports/fixtures to validate each layer in isolation.

## 4. Scoring strategy for seat selection
- **Why**: “Best seat” is subjective, so we expose configurable row/column weights and let users include/exclude wheelchair seats. Contiguous block searches must rely on the discrete grid indices from the SVG.
- **How**: `SeatSelector` scores seats relative to the hall centre (based on min/max grid indices) and uses sliding windows to find contiguous segments. Future work can plug in different scoring configs without touching parsing or HTTP.

## 5. Scheduler + SeatAdvisor orchestration
- **Why**: We need a single entry point that can sweep dates, retry HTTP fetches, and feed notifications without duplicating orchestration logic across bots/CLIs. This also gives us a central place to handle CAPTCHA detection and backoff.
- **How**: `SeatAdvisor` encapsulates discovery → fetch → parse → selection, while `MonitorScheduler` wraps it with retry/backoff, date sweeping (`DateSweepConfig`), and Telegram notifications. `main.py` simply instantiates these components, keeping CLI code minimal.

## 6. Documentation & Didactic Tone
- **Why**: Multiple contributors (possibly AI agents) will touch the project. Documentation should quietly teach newcomers how components interact and why they exist.
- **How**: The `/docs` folder hosts `architecture.md` (flow + module map) and this decisions log, complementing `README.md`. Any new subsystem should update these docs in the same PR to keep them trustworthy.

## 7. Structured Logging & Diagnostics
- **Why**: Operators need persistent, machine-readable logs to diagnose CAPTCHA spikes, notifier failures, or scheduling gaps. Plain stdout logs are hard to aggregate.
- **How**: Adopt Python’s logging with a JSON/structured formatter and rotating file handler (e.g., `logs/cinema-monitor.log`). Each entry should capture `timestamp`, `event`, `screening_date`, `order_url`, `party_size`, `attempt`, and error context. Until implemented, the docs and improvements log track the plan so future PRs can wire it in consistently.

## 8. Pluggable Notifier Strategy
- **Why**: Different deployments require different alert transports (Telegram for individuals, Slack/email for teams). Hardcoding Telegram would limit adoption.
- **How**: `Notifier` exposes async/sync send methods and accepts a fallback handler. `MonitorScheduler` depends on the interface rather than the Telegram implementation, enabling drop-in replacements. New notifiers must follow the same signature and provide fallbacks so failure modes remain predictable.

## 9. Documentation Landing & Navigation
- **Why**: As docs expanded (overview, quickstart, tutorials, how-tos, reference), contributors needed a map to avoid duplicating content or missing guides.
- **How**: `docs/index.md` serves as the landing page, describing when to use each doc. README links into the structure, and every new doc must be referenced there or in the index to keep navigation coherent.
