# Improvements Log

This document tracks documentation/code revisions identified during the staged
review. Each item lists the affected files, the issue, suggested action, and an
estimate of urgency/type so future contributors can pick them up easily.

## Table of Contents
- [README.md](#readmemd)
- [docs/](#docs)
- [Other Markdown](#other-markdown)
- [Codebase (src/)](#codebase-src)
- [Style & Consistency](#style--consistency)
- [Documentation Strategy](#)

## Observability & Notifications

- **File(s):** src/notifier.py  
  **Issue:** Sending multiple Telegram alerts sequentially triggers `RuntimeError: Event loop is closed` because `send_alert_sync` always uses `asyncio.run`.  
  **Suggested change:** Keep a persistent loop (or use `asyncio.run` once) so repeated sends share the same event loop; consider exposing a purely synchronous transport for CLI usage.  
  **Priority:** High  
  **Type:** Bug Risk  
  **Status:** ✅ `Notifier` now uses a reusable async runner (no more per-send `asyncio.run`) so multiple alerts no longer crash when loops close.

- **File(s):** src/scheduler.py, logging configuration  
  **Issue:** Logs are extremely verbose (every HTTP request, every seat-map fetch, etc.) and there is no structured/rotating log file.  
  **Suggested change:** Introduce a central logging config (JSON/file + console) with levels per module; only surface high-level info in production runs.  
  **Priority:** Medium  
  **Type:** Observability  
  **Status:** ✅ Added `logging_setup.py`, root logging now configured via env (`LOG_LEVEL`, `LOG_FILE`) with httpx noise suppressed.

- **File(s):** src/scheduler.py  
  **Issue:** `run_forever` uses `time.sleep` in a `while True`, so cancelling the process requires killing it.  
  **Suggested change:** Add a stoppable loop (e.g., `threading.Event`, signal handlers) and ensure graceful shutdown.  
  **Priority:** Low  
  **Type:** Refactor  
  **Status:** ✅ `MonitorScheduler` now accepts/owns a stop event; `run_forever` respects it so callers can stop cleanly.


## Seat Map Fetching & Selection

- **File(s):** src/seatmap_fetcher.py  
  **Issue:** Playwright still occasionally hits CAPTCHA or sandbox issues; there is no retry/stealth strategy beyond simple polling.  
  **Suggested change:** Evaluate `playwright-stealth` or cookie reuse; expose settings (headless, sandbox, timeouts) via config so operators can tune without editing code.  
  **Priority:** High  
  **Type:** Stability

- **File(s):** src/seat_map.py, docs/seatmap_fetcher_report.md  
  **Issue:** Seat status still relies on parsing the live SVG; document the limitations clearly (API endpoints do not expose availability, fail-open).  
  **Suggested change:** Expand troubleshooting/docs so operators know they must inspect logs when CAPTCHA hits, and expose a warning when we return a map without “Occupied” markers.  
  **Priority:** Medium  
  **Type:** Documentation/Stability

- **File(s):** src/seat_selection.py  
  **Issue:** No docstrings/tests covering the new seat-map output; filtering/score logic is still opaque.  
  **Suggested change:** Add unit tests/docstrings explaining scoring weights and row preference, especially now that we rely on parsed SVG output.  
  **Priority:** Medium  
  **Type:** Style/Testing


## Legacy Modules & Cleanup

- **File(s):** src/date_sweep.py  
  **Issue:** `include_weekends` and `seen_redirects` are unused, which is misleading.  
  **Suggested change:** Implement the intended filtering/redirect detection or remove the dead fields to simplify the API.  
  **Priority:** Medium  
  **Type:** Refactor

- **File(s):** src/monitor.py, src/seat_counter.py  
  **Issue:** Old screenshot-based monitor still lives in the repo even though the CLI uses the new advisor; it confuses newcomers.  
  **Suggested change:** Move to `legacy/` or delete with a note in docs so only the modern pipeline remains.  
  **Priority:** Low  
  **Type:** Cleanup


## Code Quality & Docs

- **File(s):** src/notifier.py, src/scheduler.py, src/seatmap_fetcher.py, etc.  
  **Issue:** Public classes/functions still lack docstrings and type hints in places.  
  **Suggested change:** Adopt a lightweight docstring style for all public modules so future contributors can understand the API surface quickly.  
  **Priority:** Medium  
  **Type:** Style

- **File(s):** README.md, docs/reference.md, config docs  
  **Issue:** Configuration defaults/terminology can drift between docs and `AppConfig`.  
  **Suggested change:** Generate or table-ify the config reference directly from `AppConfig` (or keep a single source of truth) to avoid divergence.  
  **Priority:** Medium  
  **Type:** Documentation

- **File(s):** docs/ (general)  
  **Issue:** Markdown style is mostly consistent now, but there is still no explicit style guide.  
  **Suggested change:** Optional: document headings/callouts/code-block conventions so future docs stay uniform.  
  **Priority:** Low  
  **Type:** Documentation (Deferred)

## Codebase (src/)

- **File(s):** src/date_sweep.py  
  **Issue:** `include_weekends` flag and `seen_redirects` set (lines 9-23) are unused, so config suggests capabilities that don’t exist.  
  **Suggested change:** Implement weekend filtering/redirect tracking or delete the dead parameters to avoid confusion.  
  **Priority:** Medium  
  **Type:** Refactor

- **File(s):** src/screenings_browser.py  
  **Issue:** Playwright fallback returns all showtimes without reapplying `AppConfig` filters (earliest time, allowed weekdays).  
  **Suggested change:** Reuse `ScreeningDiscovery._apply_filters` or factor filter logic into a shared helper so browser discovery honors the same rules.  
  **Priority:** High  
  **Type:** Bug Risk  
  **Status:** ✅ Filtering extracted into `filter_screenings_for_config` and reused by both discovery paths; tests updated.

- **File(s):** src/monitor.py, src/seat_counter.py  
  **Issue:** Screenshot-based monitoring remains in the repo but isn’t wired into the CLI; it mixes prints/logging and confuses new contributors.  
  **Suggested change:** Either remove these legacy modules or move them to a clearly labeled `legacy/` folder with documentation about their status.  
  **Priority:** Low  
  **Type:** Cleanup

- **File(s):** src/notifier.py  
  **Issue:** `Notifier.send_alert_sync` always calls `asyncio.run`, which breaks if the consumer already has an event loop (e.g., running inside another async app).  
  **Suggested change:** Allow injecting a loop / executor-friendly runner, or provide a pure-sync implementation so library users can integrate safely.  
  **Priority:** Medium  
  **Type:** Refactor

- **File(s):** src/advisor.py  
  **Issue:** Discovery/fetch failures are only logged; scheduler cannot distinguish CAPTCHA/HTTP issues from “no seats found”.  
  **Suggested change:** Return structured error info or raise typed exceptions so callers can react (e.g., escalate CAPTCHA vs silently continue).  
- **File(s):** src/scheduler.py  
  **Issue:** `run_forever` uses `time.sleep` in an infinite loop, making it hard to interrupt gracefully (e.g., via SIGINT) without killing the process.  
  **Suggested change:** Use `threading.Event` or handle `KeyboardInterrupt`/signals to exit the loop cleanly.  
  **Priority:** Low  
  **Type:** Refactor

- **File(s):** src/seatmap_fetcher.py  
  **Issue:** Browser fallback is currently blocked by CAPTCHA ("reCAPTCHA validation failed"), rendering it ineffective as a backup.  
  **Suggested change:** Investigate `playwright-stealth` or similar techniques to bypass bot detection, or document that browser fallback is unreliable.  
  **Priority:** High  
  **Type:** Bug Risk

- **File(s):** src/seatmap_fetcher.py  
  **Issue:** Seat status API (`seats-statusV2`) is blocked (403) or returns useless data (all 0s). The fetcher now assumes all seats are available if the API fails.  
  **Suggested change:** This is a "fail-open" strategy that may lead to false positives. Consider implementing a more robust status check (e.g., parsing the "live" SVG from a real browser session if possible) or explicitly warning the user in the notification that availability is unverified.  
  **Priority:** High  
  **Type:** Feature


- **File(s):** src/seat_selection.py, src/scheduler.py, src/notifier.py (and other public modules)  
  **Issue:** Many public classes/methods lack docstrings, making the API harder to understand.  
  **Suggested change:** Adopt a consistent docstring style (short summary + `Args`/`Returns`) and apply it across public entry points.  
  **Priority:** Medium  
  **Type:** Style

- **File(s):** logging across src/, main CLI entry  
  **Issue:** Logging is basic stdout INFO; no structured output or file persistence, and legacy modules still use `print`.  
  **Suggested change:** Design a unified logging approach that writes to a rotating file and is easy to parse (evaluate `structlog` vs enriched `logging` + JSON formatter). Document the decision and wire it through `main.py`/scheduler.  
  **Priority:** Medium  
  **Type:** Style

- **File(s):** docs/ and README.md  
  **Issue:** Markdown style varies (heading levels, tone, link syntax), especially in older files.  
  **Suggested change:** Define a docs style guide (headings, callouts, code blocks) and retrofit existing docs to match for a uniform didactic tone.  
  **Priority:** Low  
  **Type:** Documentation  
  **Status:** Deferred – tone is now mostly consistent after recent rewrites, but formalising a style guide is optional future work; leave item for later if needed.

- **File(s):** README.md, docs/architecture.md, src/config.py  
  **Issue:** Configuration defaults/terminology can drift between code and docs.  
  **Suggested change:** Ensure docs pull terminology directly from `AppConfig` (maybe via tables or generated snippets) so users see the same names/values everywhere.  
  **Priority:** Medium  
  **Type:** Documentation

## Documentation Strategy

- **Structure:** Adopt a multi-layer doc set—`README.md` (high-level pitch + Quickstart), `docs/overview.md` (concepts/data flow), `docs/quickstart.md` (interactive Try-it-Now), `docs/tutorials/*.md` (end-to-end guides), `docs/how-to/*.md` (task-oriented recipes), `docs/reference.md` (config/API tables), `docs/troubleshooting.md` (FAQ/checklist), and `docs/process/decisions.md` (ADR log).  
- **Reuse:** Seed Overview/Reference with material from `docs/architecture.md` and `docs/decisions.md`; transition unique content from `project-description.md` into Overview/Tutorials before deleting the legacy file.  
- **Interactivity:** Quickstart/Tutorials should include “Run `uv run cinema-monitor --example` now” steps, verification prompts, and mini-exercises (e.g., adjust `AppConfig` to filter weekdays) so readers practice immediately.  
- **Navigation:** Add a docs landing page (README section or `docs/index.md`) that links to each category, highlights target audiences (user/operator/developer), and explains when to use which guide.  
- **Maintenance:** When code/config choices change, update the paired guide in the same PR and log noteworthy shifts in `docs/decisions.md` to keep historical context.
