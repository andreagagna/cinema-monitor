from src.config import AppConfig
from src.monitor import CinemaMonitor


def test_monitor_initialization():
    config = AppConfig.from_env()
    monitor = CinemaMonitor(config)
    assert monitor.config.movie_name_slug == config.movie_name_slug
