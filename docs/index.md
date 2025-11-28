# Documentation Guide

Welcome! This guide helps you navigate Cinema Monitor’s documentation based on
your goals—whether you’re running the monitor for the first time, integrating it
into a bot, or extending the core modules.

## Start Here

1. **README.md** – quick project pitch and happiest-path instructions.
2. **Overview (`docs/overview.md`)** – architecture, data flow, and the rationale
   behind each module.
3. **Quickstart Lab (`docs/quickstart.md`)** – step-by-step setup with “try it
   now” prompts and verification checklists.

## Learn by Doing

- **Tutorials (`docs/tutorials/`)**
  - `daily-monitor.md` – configure `MonitorScheduler`, tune retries, see sample
    Telegram alerts.
  - `seat-selector.md` – inspect seat-map fixtures, customise scoring weights,
    and add tests for new heuristics.
- **How-To Guides (`docs/how-to/`)**
  - `date-sweep.md` – adjust horizons, weekday filters, and redirect handling.
  - `custom-notifier.md` – plug in Slack/email or bespoke transports.
  - Add more recipes as new workflows emerge (CAPTCHA mitigation, structured
    logging, etc.).

## Reference & Support

- **Reference (`docs/reference.md`)** – tables covering `AppConfig`,
  `SchedulerConfig`, CLI entry points, and public API objects.
- **Troubleshooting (`docs/troubleshooting.md`)** – FAQ with log examples,
  Playwright installation tips, Telegram debugging steps, and CAPTCHA guidance.
- **Decisions (`docs/decisions.md`)** – architecture choices and trade-offs
  (update this whenever a significant design decision changes).

## Contributing & Collaboration

- Read `agents.md` for coding conventions, architectural expectations, and how
  AI assistants should interact with this repo.
- When introducing new features or subsystems:
  1. Update the relevant doc(s) in the same change.
  2. Log noteworthy design decisions in `docs/decisions.md`.
  3. If documentation structure changes (new sections, tutorials), reflect that
     here so future contributors know where to plug their content.
