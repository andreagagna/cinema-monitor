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

## README.md

- **File(s):** README.md  
  **Issue:** No Quickstart flow for newcomers; only general setup steps.  
  **Suggested change:** Add a three-step Quickstart (“clone → configure `.env` → run `uv run cinema-monitor`”) with expected output so users can validate success quickly.  
  **Priority:** Medium  
  **Type:** Documentation  
  **Status:** ✅ Quickstart section added with commands and expected output (README.md).

- **File(s):** README.md, src/config.py  
  **Issue:** Configuration knobs (movie IDs, date sweep, weekdays, scoring, Telegram) are spread between `.env` and `AppConfig` but undocumented.  
  **Suggested change:** Document key environment variables & `AppConfig` fields in a dedicated “Configuration” section that mirrors the names/defaults in `src/config.py`.  
  **Priority:** Medium  
  **Type:** Documentation  
  **Status:** ✅ Configuration table summarising key env vars now in README; full list will live in `docs/reference.md`.

- **File(s):** README.md  
  **Issue:** No troubleshooting/FAQ guidance (Playwright install, Telegram auth, CAPTCHA, env vars).  
  **Suggested change:** Add a short Troubleshooting/FAQ section covering the most common failure modes and linking to deeper docs where appropriate.  
  **Priority:** Medium  
  **Type:** Documentation  
  **Status:** ✅ Troubleshooting section added with Playwright, Telegram, filter, and CAPTCHA tips plus link to docs.

- **File(s):** README.md  
  **Issue:** The description focuses on “Avatar: Fire and Ashes” which makes the tool feel hardcoded.  
  **Suggested change:** Reframe that movie/format as a sample configuration and highlight that the pipeline works for any Cinema City movie/city combo.  
  **Priority:** Low  
  **Type:** Documentation  
  **Status:** ✅ Intro now states Avatar config is an example and emphasises broader configurability.

- **File(s):** README.md, docs/architecture.md  
  **Issue:** No overview of entry points (CLI script, `SeatAdvisor`, `MonitorScheduler`) or how they relate to deeper docs.  
  **Suggested change:** Add a short “Key Components” subsection linking to `docs/architecture.md` and briefly describing advisor, scheduler, and notifier roles.  
  **Priority:** Low  
  **Type:** Documentation  
  **Status:** ✅ README now has “Key Components” linking to docs and describing main modules.

## docs/

- **File(s):** docs/architecture.md  
  **Issue:** Architecture table omits notifier/CLI layers, making the flow feel incomplete.  
  **Suggested change:** Extend the module table/diagram to include `Notifier`, `MonitorScheduler`, and `main.py`, noting how alerts propagate.  
  **Priority:** Medium  
  **Type:** Documentation  
  **Status:** ✅ Table now includes notifier + CLI entries with notes about alert flow.

- **File(s):** docs/architecture.md, docs/decisions.md  
  **Issue:** No navigation aids; contributors must guess which doc to open.  
  **Suggested change:** Add a short docs landing blurb or ToC that cross-links architecture, decisions, and any new guides so readers know where to start.  
  **Priority:** Low  
  **Type:** Documentation  
  **Status:** ✅ `docs/index.md` now links to architecture/decisions; README points to docs landing; architecture intro references the decisions log.

- **File(s):** docs/decisions.md  
  **Issue:** Decisions stop at early parsing-era choices; scheduler/notifier/retry policies are undocumented.  
  **Suggested change:** Add decisions covering alerting transports, retry/backoff strategy, and the move away from screenshot detection.  
  **Priority:** Medium  
  **Type:** Documentation  
  **Status:** ✅ Added entries for structured logging (ADR-7), pluggable notifier strategy (ADR-8), and docs navigation (ADR-9).

- **File(s):** docs/ (new files)  
  **Issue:** Docs directory only covers architecture/decisions; lacks overview, how-tos, or tutorials for different audiences.  
  **Suggested change:** Introduce additional guides (e.g., `overview.md`, “How to run the monitor continuously”, “Extending SeatSelector”) following a consistent template.  
  **Priority:** Medium  
  **Type:** Documentation
  **Status:** ✅ Skeleton guides (overview, quickstart, tutorials, how-tos, reference, troubleshooting, index) added; populate content next.

## Other Markdown

- **File(s):** project.md, project-description.md  
  **Issue:** Legacy documents repeat README/docs content and risk going stale.  
  **Suggested change:** Merge any unique insights into `docs/` (architecture/overview) then delete these files to reduce duplication.  
  **Priority:** Low  
  **Type:** Documentation  
  **Status:** ✅ Architecture narrative merged into `docs/overview.md`; legacy files removed.

- **File(s):** TODO.md  
  **Issue:** Task list is historical—nearly every item marked DONE—so it no longer guides contributors.  
  **Suggested change:** Migrate any remaining actionable tasks into GitHub issues or this improvements log, then remove/archivethe file.  
  **Priority:** Low  
  **Type:** Documentation  
  **Status:** ✅ All items confirmed complete; file removed.

- **File(s):** agents.md  
  **Issue:** Important AI-collaboration rules aren’t referenced elsewhere, so contributors may miss them.  
  **Suggested change:** Link to this file from README/docs or move it under `docs/agents.md` and mention it in a “Contributing / Working with AI agents” section.  
  **Priority:** Medium  
  **Type:** Documentation  
  **Status:** ✅ README now links to `agents.md` in “Working with AI / Contributors”, and docs/index references it for contributors.

- **File(s):** AI_DOCS_REVIEW_PLAN.md  
  **Issue:** Process document is useful during this review but will become noise afterward.  
  **Suggested change:** Once the staged review finishes, either archive it in `docs/process/` with context or remove it to keep the repo tidy.  
  **Priority:** Low  
  **Type:** Documentation  
  **Status:** ✅ File removed after completing the staged review.

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
  **Priority:** Low  
  **Type:** Refactor

## Style & Consistency

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
