from legacy.monitor import CinemaMonitor
from src.config import AppConfig


def test_monitor_initialization():
    config = AppConfig.from_env()
    monitor = CinemaMonitor(config)
    assert monitor.config.movie_name_slug == config.movie_name_slug
