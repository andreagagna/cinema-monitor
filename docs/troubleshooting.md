# Troubleshooting & FAQ

If something feels off, scan this checklist before diving into the code. Most
issues have simple fixes (and we’ve sprinkled in log snippets to help).

## Playwright Installation Issues

**Symptoms**

- `playwright` command not found.
- Errors mentioning missing Chromium or system dependencies.

**Fixes**

1. Install browsers again:
   ```bash
   uv run playwright install chromium
   ```
2. On Linux servers, install Playwright’s required system packages (see
   [Playwright docs](https://playwright.dev/python/docs/browsers#install-system-dependencies)).
3. Verify with
   ```bash
   uv run python -c "from playwright.sync_api import sync_playwright"
   ```
   to ensure imports succeed.

## Telegram / Notifier Errors

**Symptoms**

- Logs show `Fallback alert (reason: missing_config)`.
- Bot responses fail with `telegram.error.Unauthorized`.

**Fixes**

1. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`. Ensure the bot has
   messaged the chat at least once.
2. Restart the script so `dotenv` reloads env vars.
3. To find a chat ID, DM `@RawDataBot` or follow
   [this guide](https://gist.github.com/nafiesl/4ad622f344cd1dc3bb1ecbe468ff9f8a#get-chat-id-for-a-channel).
   For groups, temporarily enable “Show chat history” and copy the numeric ID.
4. For local testing, pass a fallback handler to `Notifier` that logs alerts
   instead of sending them.

## CAPTCHA or Seat-Map Fetch Failures

**Symptoms**

- Logs warn: `Possible CAPTCHA encountered while fetching ...`.
- Seat maps fail with HTTP 403/503.

**Mitigations**

- Reduce polling frequency (`poll_interval_seconds`) to avoid hammering the site.
- Ensure Playwright fallback (`BrowserScreeningDiscovery`) is working—it can
  bypass some dynamic loading issues.
- If CAPTCHA persists, pause for 30–60 minutes or manually solve it in a browser
  before re-running.

## No Seats Found

**Checklist**

1. Confirm your date/weekday filters aren’t excluding everything
   (`ALLOWED_WEEKDAYS`, `EARLIEST_SHOW_TIME`).
2. Try a smaller `party_size` or enable wheelchair inclusion.
3. Inspect logs for “No eligible dates to check” (means the date iterator
   returned nothing).
4. Run `uv run pytest tests/test_seat_selection.py` to ensure scoring logic
   hasn’t regressed.

## Logging & Diagnostics

- Default logs go to stdout. To persist them, configure Python logging with a
  `FileHandler` (e.g., `logs/cinema-monitor.log`).
- Planned improvement: structured/JSON logging (see `docs/improvements.md`)
  capturing fields like `screening_date`, `seat_numbers`, `attempt`.
- When reporting issues, capture the full log snippet around the error plus the
  env vars you set (mask secrets!).

## Getting Help

- Re-read the relevant docs: Quickstart, tutorials, how-tos, and this FAQ.
- File an issue (or contact maintainers) with:
  - Console logs (truncated to the relevant section).
  - Env config summary (movie slug, city, filters, notifier type).
  - Steps to reproduce (commands run, expected vs actual result).
- Mention any local modifications to `AppConfig`, `SeatSelector`, or the
  scheduler.
