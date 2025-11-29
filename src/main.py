import logging
from src.advisor import SeatAdvisor
from src.config import AppConfig
from src.logging_setup import setup_logging
from src.notifier import Notifier
from src.scheduler import MonitorScheduler, SchedulerConfig

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    config = AppConfig.from_env()
    logger.info(
        "Starting Cinema Seat Advisor for %s (%s)",
        config.movie_name_slug,
        config.movie_id,
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
        scheduler_config=SchedulerConfig(),
    )

    try:
        scheduler.run_once()
    except KeyboardInterrupt:
        logger.info("Stopping monitor...")
    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)


if __name__ == "__main__":
    main()
