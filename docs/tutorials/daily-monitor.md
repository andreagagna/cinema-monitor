# Tutorial: Schedule Daily Seat Checks

Remember that one time you missed IMAX seats because you refreshed the site only
twice? Let’s not do that again. In this tutorial we’ll wire up
`MonitorScheduler` so it keeps watch for you—complete with retries, Telegram
alerts, and a sprinkling of fun.

## Goal

- Sweep a multi-day horizon automatically.
- Retry politely when Cinema City throws a tantrum (CAPTCHA/HTTP errors).
- Celebrate with a Telegram ping when good seats pop up.

## What You'll Build

- A small runner script (`monitor_daily.py`) that configures `MonitorScheduler`.
- Log output that proves retries/backoff are working.
- Optional: a dry-run fallback notifier that cracks a joke instead of pinging
  Telegram (for dev mode).

## Step 0 – Warm-up

Make sure you’ve already completed the [Quickstart Lab](../quickstart.md): repo
cloned, dependencies installed, `.env` configured.

## Step 1 – Create a Daily Runner

Create `monitor_daily.py` in the repo root:

```python
from src.advisor import SeatAdvisor
from src.config import AppConfig
from src.notifier import Notifier
from src.scheduler import MonitorScheduler, SchedulerConfig


def main() -> None:
    config = AppConfig.from_env()
    scheduler = MonitorScheduler(
        config,
        advisor=SeatAdvisor(),
        notifier=Notifier(config),
        scheduler_config=SchedulerConfig(
            poll_interval_seconds=1800,  # every 30 minutes
            horizon_days=5,
            max_retries=2,
            backoff_factor=2.5,
            party_size=2,
            top_n=3,
        ),
    )
    scheduler.run_once()


if __name__ == "__main__":
    main()
```

> **Checkpoint:** Before running, jot down which dates will be checked (hint:
> start date comes from `AppConfig.date`, horizon adds 5 days, and weekday
> filters apply).

## Step 2 – Run & Observe

Kick off the script:

```bash
uv run python monitor_daily.py
```

Watch the logs:

```
INFO MonitorScheduler ... Checking dates: ['2026-01-05', '2025-01-06', ...]
INFO MonitorScheduler ... Sending alert for 2025-01-06 at 19:30 ...
```

If a request fails, you should see:

```
WARNING MonitorScheduler ... attempt 1/2 failed (CAPTCHA?). Retrying in 30.0s.
```

> **Checkpoint:** Do the actual wait times match
> `poll_interval_seconds * backoff_factor^(attempt-1)`? Math time!

## Step 3 – Add Telegram & Jest

Ensure your `.env` contains Telegram credentials. To confirm alerts:

```bash
uv run python monitor_daily.py
```

You should receive multiple alerts (one per suggestion) in chat. For local
testing without spamming friends, add a fallback notifier:

```python
def chuckle(message: str, screenshot: str | None, reason: str | None) -> None:
    print(f"[fallback] {message[:60]}... (reason: {reason or 'demo'})")

notifier = Notifier(config, fallback_handler=chuckle)
```

Now the scheduler will log a humorous fallback instead of sending real messages.

## Step 4 – Go Continuous (Optional)

Replace `scheduler.run_once()` with `scheduler.run_forever()` to create a true
daemon. Consider using `systemd`, `pm2`, or a simple tmux session to keep it
alive.

> **Safety tip:** Add structured logging (see `docs/improvements.md`) so you can
> tail log files, ship metrics, or feed alerts into monitoring systems later.

## Exercises

1. **Party of five:** Modify `SchedulerConfig.party_size` to 5 and observe how
   alerts change. Bonus: output the seat labels in your fallback handler using
   emoji (“Row 8 ⇒ 🪑🪑🪑🪑🪑”).
2. **Respect weekends only:** Update `ALLOWED_WEEKDAYS=Sat,Sun` and rerun. Confirm
   that `_plan_dates` skips weekdays.
3. **Structured logs:** Experiment with `structlog` or a JSON formatter in
   `monitor_daily.py`. Capture fields like `screening_date`, `attempt`, and
   `party_size` so you can filter logs later.
4. **Health probes:** Write a tiny HTTP endpoint (FastAPI/Flask) that reports the
   timestamp of the last successful alert. Handy when deploying to servers.
