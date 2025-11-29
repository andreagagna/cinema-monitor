import asyncio
import logging
from typing import Callable, Optional

from telegram import Bot

from src.config import AppConfig

logger = logging.getLogger(__name__)


FallbackHandler = Callable[[str, Optional[str], Optional[str]], None]


class Notifier:
    def __init__(
        self,
        config: AppConfig,
        *,
        fallback_handler: Optional[FallbackHandler] = None,
        bot_factory: Callable[[str], Bot] = Bot,
        async_runner: Optional[Callable[[Callable[[], asyncio.Future]], None]] = None,
    ):
        self.config = config
        self.token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self._bot = None
        self._bot_factory = bot_factory
        self._fallback_handler = fallback_handler or self._default_fallback
        self._async_runner = async_runner or self._default_async_runner

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    async def send_alert(self, message: str, screenshot_path: Optional[str] = None) -> None:
        """Sends a Telegram alert with optional screenshot, falling back if needed."""
        if not self.is_configured():
            self._fallback_handler(message, screenshot_path, "missing_config")
            return

        bot = self._get_bot()
        if not bot:
            self._fallback_handler(message, screenshot_path, "bot_init_failed")
            return

        try:
            logger.info("Sending Telegram alert")
            await bot.send_message(chat_id=self.chat_id, text=message)

            if screenshot_path:
                with open(screenshot_path, "rb") as photo:
                    await bot.send_photo(chat_id=self.chat_id, photo=photo)

        except Exception as exc:
            logger.exception("Failed to send Telegram alert: %s", exc)
            self._fallback_handler(message, screenshot_path, str(exc))

    def send_alert_sync(self, message: str, screenshot_path: Optional[str] = None) -> None:
        """Wrapper for sync calls."""
        self._async_runner(lambda: self.send_alert(message, screenshot_path))

    def _default_async_runner(self, coro_factory: Callable[[], asyncio.Future]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            task = loop.create_task(coro_factory())

            async def _consume() -> None:
                try:
                    await task
                except Exception:
                    logger.exception("Async notifier task failed")

            loop.create_task(_consume())
        else:
            asyncio.run(coro_factory())

    def _get_bot(self):
        if not self.is_configured():
            return None
        if not self._bot:
            try:
                self._bot = self._bot_factory(self.token)
            except Exception as exc:
                logger.exception("Unable to initialise Telegram bot: %s", exc)
                return None
        return self._bot

    def _default_fallback(
        self, message: str, screenshot_path: Optional[str], reason: Optional[str]
    ) -> None:
        suffix = f" (reason: {reason})" if reason else ""
        logger.warning("Fallback alert%s: %s", suffix, message)
