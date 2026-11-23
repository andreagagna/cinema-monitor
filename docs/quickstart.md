# Quickstart Lab

Welcome to the Cinema Monitor lab. In less than 15 minutes you will:

1. Install the tooling.
2. Configure Telegram credentials (optional but recommended).
3. Run the monitor once and inspect the output.
4. Experiment with filters and next steps.

Bring a terminal and basic familiarity with Python tooling; everything else is
scripted.

## Prerequisites

- Python 3.10+ installed.
- [`uv`](https://github.com/astral-sh/uv) or `pip` + `python -m venv`.
- Telegram bot token and chat ID (optional—without them the monitor logs to the
  console only).
- Chromium Playwright browsers (we’ll install them below).

> **Need help?** Consult the Troubleshooting section of `README.md` or
> `docs/troubleshooting.md`.

## Step 1 – Clone & Install

Clone the repo and install dependencies with uv:

```bash
git clone <repository-url>
cd cinema-monitor
uv sync
uv run playwright install chromium
```

> **Verify:** Run the test suite quickly to ensure your environment works.
> ```bash
> uv run pytest -q
> ```
> Expect a green “passed” summary.

## Step 2 – Configure `.env`

Copy the sample env file and fill in your credentials and filters.

```bash
cp .env.example .env  # skip if you manage env vars another way
```

Edit `.env` with at least:

```ini
TELEGRAM_BOT_TOKEN=123456:ABCDEF
TELEGRAM_CHAT_ID=987654321
MOVIE_PRESET=dune-part-three
DATE=2027-01-01
```

The default preset tracks *Dune: Part Three* (`duna-cast-treti` / `8105s2r`) at
Prague Cinema City Flora IMAX (`imax,70-mm`) in original English audio from
January 1–7, 2027. Use `DATE=2026-12-15` to check the December presale instead.
Set `MOVIE_PRESET=avatar-fire-and-ash` or override `MOVIE_NAME_SLUG` + `MOVIE_ID`
to monitor another film, and adjust `DATE` for that film.

> **Mini-exercise:** limit sweeps to Friday evenings. Add:
> ```ini
> EARLIEST_SHOW_TIME=18:00
> ALLOWED_WEEKDAYS=fri
> ```
> You’ll see the effect in Step 3’s logs (no screenings outside Fridays).

## Step 3 – Run the Monitor

Launch the packaged CLI:

```bash
uv run cinema-monitor
```

You should see logs similar to:

```
INFO ... Starting Cinema Seat Advisor for avatar-ohen-a-popel (7148s2r)
INFO ... Sending alert for 19:30 on 2026-01-05: Row 10 Seats 11, 12
```

If Telegram credentials are set, check your chat for a message titled
“🎬 Seat Alert” with the recommended seats and booking link.

> **Checklist:**
> - Were screenings discovered for the configured date(s)?
> - Did SeatAdvisor skip any screenings due to errors? (Look for WARN lines.)
> - Did you receive a Telegram alert? If not, confirm the bot token/chat ID.

## Step 4 – Iterate

- **Adjust party size / ranking**
  ```bash
  export PARTY_SIZE=3
  export TOP_N=5
  uv run cinema-monitor
  ```
  (or edit `SchedulerConfig` in `src/main.py`). Observe how the seat blocks
  change.
- **Include wheelchair seats**: set `INCLUDE_WHEELCHAIR=true` in `.env` to allow
  wheelchair seats in the suggestions.
- **Explore the pipeline**: read `docs/overview.md` or follow the tutorials in
  `docs/tutorials/` to configure continuous monitoring or extend seat scoring.

> **Next steps**
> - Want automated polling? Head to `docs/tutorials/daily-monitor.md`.
> - Want to customise scoring? Try `docs/tutorials/seat-selector.md`.
> - Want to plug in Slack/email alerts? See `docs/how-to/custom-notifier.md`.
