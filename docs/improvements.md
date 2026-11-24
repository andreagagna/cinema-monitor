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

## Seat Map Fetching & Selection

- **File(s):** src/seatmap_fetcher.py  
  **Issue:** Playwright occasionally hits CAPTCHA, but we capture the SVG before that happens.  
  **Suggested change:** Optional hardening: experiment with stealth/cookie reuse and expose headless/sandbox knobs in config.  
  **Priority:** Low  
  **Type:** Stability

- **File(s):** docs/seatmap_fetcher_report.md  
  **Issue:** Seat availability only exists in the live SVG; this is already documented in the seatmap report/debug notes.  
  **Status:** ✅ Documentation reflects the browser-first, fail-open behaviour.

- **File(s):** src/seat_selection.py  
  **Status:** ✅ Targeted unit tests added for single seats, contiguous blocks, wheelchair filtering, min-score, and aisle avoidance.

- **File(s):** src/config.py, src/screenings.py, src/screenings_browser.py\
  **Status:** ✅ Reusable `MovieProfile` presets (`dune-part-three`, `avatar-fire-and-ash`), multi-format (`imax,70-mm`), Flora venue (`1052`), and English original-audio filtering implemented and verified against live Cinema City pages.

- **File(s):** src/seatmap_renderer.py, docs/seatmap_renderer.md  
  **Status:** ✅ Seat map renderer now ships with colour legend + PNG previews for alerts.

- **File(s):** src/scheduler.py, docs/reference.md  
  **Status:** ✅ Recommendation filters (min score + aisle avoidance) wired with env docs.


## Legacy Modules & Cleanup

- **File(s):** src/date_sweep.py  
  **Issue:** `include_weekends` and `seen_redirects` are unused, which is misleading.  
  **Suggested change:** Implement the intended filtering/redirect detection or remove the dead fields to simplify the API.  
  **Priority:** Medium  
  **Type:** Refactor


## Code Quality & Docs

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
  **Status:** ✅ `include_weekends` now actively filters weekends when no custom weekday set is provided.

- **File(s):** legacy/monitor.py, legacy/seat_counter.py\
  **Status:** ✅ Legacy screenshot-based scripts isolated under `legacy/`.

- **File(s):** src/advisor.py  
  **Issue:** Discovery/fetch failures are only logged; scheduler cannot distinguish CAPTCHA/HTTP issues from “no seats found”.  
  **Suggested change:** Return structured error info or raise typed exceptions so callers can react (e.g., escalate CAPTCHA vs silently continue).  
- **File(s):** src/scheduler.py  
  **Status:** ✅ `MonitorScheduler.run_forever` uses `threading.Event` (`stop_event.wait`) for clean interruption, and `latest_screening_date_<movie_id>.txt` is scoped per film.

- **File(s):** src/seat_selection.py, src/scheduler.py, src/notifier.py (and other public modules)  
  **Issue:** Many public classes/methods lack docstrings, making the API harder to understand.  
  **Suggested change:** Adopt a consistent docstring style (short summary + `Args`/`Returns`) and apply it across public entry points.  
  **Priority:** Medium  
  **Type:** Style
