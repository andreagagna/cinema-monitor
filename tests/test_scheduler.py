from datetime import date, time

from src.advisor import SeatRecommendation
from src.config import AppConfig
from src.scheduler import MonitorScheduler, SchedulerConfig
from src.screenings import ScreeningDescriptor
from src.seat_selection import SeatBlockSuggestion


class FakeAdvisor:
    def __init__(self, recommendations):
        self.recommendations = recommendations
        self.calls = []

    def recommend(self, app_config, **kwargs):
        self.calls.append(kwargs)
        return self.recommendations


class FakeNotifier:
    def __init__(self):
        self.messages = []

    def send_alert_sync(self, message, screenshot_path=None):
        self.messages.append(message)


def make_recommendation():
    screening = ScreeningDescriptor(
        label="19:30",
        show_time=time.fromisoformat("19:30"),
        order_url="https://tickets.example.com/222",
    )
    suggestion = SeatBlockSuggestion(
        row_number=5,
        seat_numbers=[11, 12],
        labels=["11", "12"],
        grid_positions=[11, 12],
        score=0.9,
    )
    return SeatRecommendation(
        screening_date=date(2025, 12, 17), screening=screening, suggestions=[suggestion]
    )


def test_run_once_dispatches_notifications():
    advisor = FakeAdvisor([make_recommendation()])
    notifier = FakeNotifier()
    scheduler = MonitorScheduler(
        AppConfig(date="2025-12-17"),
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig(horizon_days=1),
    )

    dispatched = scheduler.run_once()
    assert dispatched == 1
    assert notifier.messages
    assert "Seat Alert" in notifier.messages[0]


def test_poll_with_retry_retries_on_error(monkeypatch):
    advisor = FakeAdvisor([make_recommendation()])
    notifier = FakeNotifier()
    scheduler = MonitorScheduler(
        AppConfig(date="2025-12-17"),
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig(poll_interval_seconds=1, max_retries=2, horizon_days=1),
        sleep_fn=lambda _: None,
    )

    calls = {"count": 0}

    original_run_once = scheduler.run_once

    def failing_run_once():
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("transient")
        return original_run_once()

    monkeypatch.setattr(scheduler, "run_once", failing_run_once)

    result = scheduler.poll_with_retry()
    assert result >= 1
