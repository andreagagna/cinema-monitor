import logging

from src.advisor import SeatAdvisor
from src.config import AppConfig
from src.logging_setup import setup_logging
from src.notifier import Notifier
from src.scheduler import MonitorScheduler, SchedulerConfig

logger = logging.getLogger(__name__)


def main() -> int:
    config = AppConfig.from_env()
    setup_logging(level=config.log_level, log_file=config.log_file)
    logger.info(
        "Starting Cinema Seat Advisor for %s [%s / %s] "
        "(city=%s, cinema=%s, format=%s, lang=%s, start=%s)",
        config.movie_title,
        config.movie_name_slug,
        config.movie_id,
        config.city,
        config.cinema_filter or "all",
        config.film_format or "any",
        config.audio_language or "any",
        config.date,
    )

    if not config.telegram_bot_token or not config.telegram_chat_id:
        logger.warning(
            "Telegram credentials not found. Alerts will be logged but not sent via Telegram."
        )

    advisor = SeatAdvisor()
    notifier = Notifier(config)
    scheduler = MonitorScheduler(
        config,
        advisor=advisor,
        notifier=notifier,
        scheduler_config=SchedulerConfig.from_app_config(config),
    )

    try:
        scheduler.run_once()
    except KeyboardInterrupt:
        logger.info("Stopping monitor...")
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
