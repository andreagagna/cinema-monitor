from datetime import date, time

from src.advisor import SeatRecommendation
from src.config import AppConfig
from src.scheduler import MonitorScheduler, SchedulerConfig
from src.screenings import ScreeningDescriptor
from src.seat_map import Seat, SeatMap, SeatStatus
from src.seat_selection import SeatBlockSuggestion


def _build_row_seats(row_number: int, seat_count: int = 12, start_grid: int = 0):
    seats = []
    for idx in range(seat_count):
        seat_number = idx + 1
        grid_x = start_grid + idx
        seats.append(
            Seat(
                row_number=row_number,
                seat_number=seat_number,
                label=str(seat_number),
                status=SeatStatus.AVAILABLE,
                grid_x=grid_x,
                grid_row=row_number,
            )
        )
    return seats


class FakeAdvisor:
    def __init__(self, recommendations, screening_dates=None):
        self.recommendations = recommendations
        self.screening_dates = screening_dates or set()
        self.calls = []
        self.last_screening_dates = set()

    def recommend(self, app_config, **kwargs):
        self.calls.append(kwargs)
        self.last_screening_dates = set(self.screening_dates)
        return self.recommendations


class FakeNotifier:
    def __init__(self):
        self.messages = []
        self.attachments = []

    def send_alert_sync(self, message, screenshot_path=None):
        self.messages.append(message)
        self.attachments.append(screenshot_path)


class FakeRenderer:
    def __init__(self):
        self.calls = 0

    def render(self, seat_map, suggestion):
        self.calls += 1
        return f"/tmp/seatmap_{self.calls}.png"


def make_recommendation():
    screening = ScreeningDescriptor(
        label="19:30",
        show_time=time.fromisoformat("19:30"),
        order_url="https://tickets.example.com/222",
    )
    suggestion = SeatBlockSuggestion(
        row_number=5,
        seat_numbers=[6, 7],
        labels=["6", "7"],
        grid_positions=[5, 6],
        score=0.9,
    )
    seat_map = SeatMap.from_seats(_build_row_seats(5))
    return SeatRecommendation(
        screening_date=date(2026, 1, 5),
        screening=screening,
        seat_map=seat_map,
        suggestions=[suggestion],
    )


def test_run_once_dispatches_notifications(tmp_path):
    advisor = FakeAdvisor([make_recommendation()], screening_dates={date(2026, 1, 5)})
    notifier = FakeNotifier()
    renderer = FakeRenderer()
    scheduler = MonitorScheduler(
        AppConfig(date="2026-01-05"),
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig(horizon_days=1),
        renderer=renderer,
        latest_date_path=tmp_path / "latest_screening_date.txt",
    )

    dispatched = scheduler.run_once()
    assert dispatched == 1
    assert notifier.messages
    assert "Seat Alert" in notifier.messages[0]
    assert "Seat map preview attached." in notifier.messages[0]
    assert notifier.attachments[0].endswith(".png")


def test_poll_with_retry_retries_on_error(monkeypatch, tmp_path):
    advisor = FakeAdvisor([make_recommendation()], screening_dates={date(2026, 1, 5)})
    notifier = FakeNotifier()
    renderer = FakeRenderer()
    scheduler = MonitorScheduler(
        AppConfig(date="2026-01-05"),
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig(poll_interval_seconds=1, max_retries=2, horizon_days=1),
        renderer=renderer,
        sleep_fn=lambda _: None,
        latest_date_path=tmp_path / "latest_screening_date.txt",
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


def test_min_score_filters_suggestions(tmp_path):
    screening = ScreeningDescriptor(
        label="18:00",
        show_time=time.fromisoformat("18:00"),
        order_url="https://tickets.example.com/333",
    )
    seat_map = SeatMap.from_seats(_build_row_seats(3))
    strong = SeatBlockSuggestion(
        row_number=3,
        seat_numbers=[4],
        labels=["4"],
        grid_positions=[3],
        score=0.95,
    )
    weak = SeatBlockSuggestion(
        row_number=3,
        seat_numbers=[5],
        labels=["5"],
        grid_positions=[4],
        score=0.6,
    )
    recommendation = SeatRecommendation(
        screening_date=date(2025, 1, 6),
        screening=screening,
        seat_map=seat_map,
        suggestions=[strong, weak],
    )

    advisor = FakeAdvisor([recommendation], screening_dates={date(2025, 1, 6)})
    notifier = FakeNotifier()
    renderer = FakeRenderer()
    scheduler = MonitorScheduler(
        AppConfig(date="2026-01-05"),
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig(
            horizon_days=1,
            min_score=0.9,
            avoid_aisle=False,
        ),
        renderer=renderer,
        latest_date_path=tmp_path / "latest_screening_date.txt",
    )

    dispatched = scheduler.run_once()
    assert dispatched == 1
    assert len(notifier.messages) == 1
    assert renderer.calls == 1


def test_avoid_aisle_filters_edge_blocks(tmp_path):
    screening = ScreeningDescriptor(
        label="20:00",
        show_time=time.fromisoformat("20:00"),
        order_url="https://tickets.example.com/444",
    )
    seat_map = SeatMap.from_seats(_build_row_seats(7))
    edge = SeatBlockSuggestion(
        row_number=7,
        seat_numbers=[1],
        labels=["1"],
        grid_positions=[0],
        score=0.95,
    )
    center = SeatBlockSuggestion(
        row_number=7,
        seat_numbers=[6],
        labels=["6"],
        grid_positions=[5],
        score=0.9,
    )

    recommendation = SeatRecommendation(
        screening_date=date(2026, 1, 5),
        screening=screening,
        seat_map=seat_map,
        suggestions=[edge, center],
    )

    advisor = FakeAdvisor([recommendation], screening_dates={date(2026, 1, 5)})
    notifier = FakeNotifier()
    renderer = FakeRenderer()
    scheduler = MonitorScheduler(
        AppConfig(date="2026-01-05"),
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig(
            horizon_days=1,
            min_score=0.0,
            avoid_aisle=True,
            aisle_boundary=3,
        ),
        renderer=renderer,
        latest_date_path=tmp_path / "latest_screening_date.txt",
    )

    dispatched = scheduler.run_once()
    assert dispatched == 1
    assert len(notifier.messages) == 1
    assert "Seat Alert" in notifier.messages[0]
    # Ensure renderer ran exactly once for the surviving suggestion.
    assert renderer.calls == 1


def test_no_new_screening_day_sends_message(tmp_path):
    latest_date_path = tmp_path / "latest_screening_date.txt"
    advisor = FakeAdvisor([], screening_dates={date(2026, 1, 5)})
    notifier = FakeNotifier()

    scheduler = MonitorScheduler(
        AppConfig(date="2026-01-05"),
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig(horizon_days=1),
        latest_date_path=latest_date_path,
    )

    scheduler.run_once()
    assert not notifier.messages

    scheduler = MonitorScheduler(
        AppConfig(date="2026-01-05"),
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig(horizon_days=1),
        latest_date_path=latest_date_path,
    )

    scheduler.run_once()
    assert notifier.messages
    assert "No new screening day" in notifier.messages[0]
