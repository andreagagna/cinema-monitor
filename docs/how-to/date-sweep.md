# How-To: Adjust Date Sweeps

Want to scan the next two weekends only? Need to limit checks to after-work
showtimes? This guide shows how to tighten or widen the scheduler’s horizon and
weekday filters without spelunking through code.

## When to Use

- You only care about specific days (e.g., Fridays and Saturdays).
- You want to sweep a longer horizon (say, 14 days) or just tomorrow.
- You need to avoid “sold out” mornings by enforcing an earliest showtime.

## Prerequisites

- Completed the [Quickstart Lab](../quickstart.md).
- Basic familiarity with `.env` and `src/config.AppConfig`.

## Step 1 – Set the Baseline Date

Edit `.env` (or export env vars) to set the starting date:

```ini
DATE=2025-12-17
```

This is the first date `AppConfig.movie_date()` returns.

## Step 2 – Filter Weekdays & Times

Add filters to `.env`:

```ini
ALLOWED_WEEKDAYS=fri,sat
EARLIEST_SHOW_TIME=18:30
```

Behind the scenes, `AppConfig.allowed_weekday_indices()` converts these into
their numeric weekdays (Friday=4, Saturday=5). `ScreeningDiscovery` uses them to
skip entire days whose weekday doesn’t match.

> **Tip:** Acceptable tokens include `mon`, `monday`, `sat`, `saturday`, etc.

## Step 3 – Tune the Horizon

Adjust `SchedulerConfig` (either in code or via env var if you expose it):

```python
from src.scheduler import SchedulerConfig

scheduler = MonitorScheduler(
    app_config,
    scheduler_config=SchedulerConfig(
        horizon_days=10,
        poll_interval_seconds=1800,
        # ...
    ),
)
```

Ten days from the baseline date (excluding filtered weekdays) will be checked.

## Step 4 – (Optional) Custom Date Iterator

Need advanced logic (e.g., skip holidays, double-check redirect behaviour)?
Inject a custom iterator:

```python
from datetime import timedelta

def weekends_only(config: DateSweepConfig):
    current = config.start_date
    for _ in range(config.days):
        if current.weekday() in {5, 6}:  # Saturday/Sunday
            yield current
        current += timedelta(days=1)

scheduler = MonitorScheduler(
    app_config,
    date_iterator=weekends_only,
)
```

Don’t forget to add tests for the iterator if it encodes new rules.

## Step 5 – Verify in Logs

Run the scheduler once:

```bash
uv run python monitor_daily.py
```

Look for lines such as:

```
INFO MonitorScheduler ... Checking dates: ['2025-12-19', '2025-12-20', '2025-12-26', '2025-12-27']
```

If weekdays you wanted are missing, recheck `ALLOWED_WEEKDAYS`. If extra days
appear, confirm your custom iterator respects the filters.

## Next Steps

- Document any custom iterator in `docs/reference.md`.
- Add regression tests if you modify `iter_available_dates`.
- Combine with scheduler tutorials to keep the monitor running continuously.
