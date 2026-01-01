from src.config import AppConfig
from src.notifier import Notifier


class DummyBot:
    def __init__(self, token, should_fail=False):
        self.token = token
        self.should_fail = should_fail
        self.sent_messages = []
        self.sent_photos = []

    async def send_message(self, chat_id, text):
        if self.should_fail:
            raise RuntimeError("network error")
        self.sent_messages.append((chat_id, text))

    async def send_photo(self, chat_id, photo):
        self.sent_photos.append((chat_id, photo.read()))


def test_notifier_falls_back_when_unconfigured():
    captured = []

    def fallback(message, screenshot, reason):
        captured.append((message, reason))

    config = AppConfig(telegram_bot_token=None, telegram_chat_id=None)
    notifier = Notifier(config, fallback_handler=fallback)

    notifier.send_alert_sync("Hello")
    assert captured
    assert captured[0][0] == "Hello"
    assert captured[0][1] == "missing_config"


def test_notifier_falls_back_on_send_failure():
    captured = []

    def fallback(message, screenshot, reason):
        captured.append(reason)

    config = AppConfig(telegram_bot_token="token", telegram_chat_id="chat")
    notifier = Notifier(
        config,
        fallback_handler=fallback,
        bot_factory=lambda token: DummyBot(token, should_fail=True),
    )

    notifier.send_alert_sync("Test")
    assert captured
    assert "network error" in captured[0]


def test_notifier_sends_screenshot_when_provided(tmp_path):
    config = AppConfig(telegram_bot_token="token", telegram_chat_id="chat")
    dummy_bot = DummyBot("token")
    notifier = Notifier(config, bot_factory=lambda token: dummy_bot)

    screenshot = tmp_path / "seatmap.png"
    screenshot.write_bytes(b"pngdata")

    notifier.send_alert_sync("Message", str(screenshot))

    assert dummy_bot.sent_messages
    assert dummy_bot.sent_messages[0] == ("chat", "Message")
    assert dummy_bot.sent_photos
