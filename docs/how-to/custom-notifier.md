# How-To: Plug In a Custom Notifier

Need Slack alerts for your team or an email sentry for your home lab? Here’s how
to swap out the default Telegram notifier (or wrap it) without touching the
core pipeline.

## When to Use

- Telegram isn’t your preferred channel.
- You want multi-channel notifications (e.g., Telegram + Slack + logging).
- You’re building a hosted service and need rich notifications with screenshots.

## Prerequisites

- Completed Quickstart (repo setup + `.env` basics).
- Comfortable editing Python files (`src/main.py` or your own runner).
- Credentials or API keys for the service you’re targeting.

## Step 1 – Implement the Notifier

Create `src/my_notifier.py`:

```python
from typing import Optional

class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_alert(self, message: str, screenshot_path: Optional[str] = None) -> None:
        payload = {"text": message}
        # Use httpx or requests to POST to Slack. Screenshot? Upload via files API.
        ...

    def send_alert_sync(self, message: str, screenshot_path: Optional[str] = None) -> None:
        import asyncio

        asyncio.run(self.send_alert(message, screenshot_path))
```

> **Tip:** Mirror the method signatures from `src/notifier.Notifier` so you can
> drop it in without surprises.

## Step 2 – Inject the Notifier

Edit `src/main.py` (or your custom runner):

```python
from src.my_notifier import SlackNotifier

def main():
    config = AppConfig.from_env()
    notifier = SlackNotifier(webhook_url=config.slack_webhook_url)
    scheduler = MonitorScheduler(config, notifier=notifier, advisor=SeatAdvisor())
    scheduler.run_once()
```

Expose `SLACK_WEBHOOK_URL` via `.env` and parse it in `AppConfig` (or in your
custom notifier).

## Step 3 – Keep a Fallback

Even fancy APIs fail. Add a fallback handler:

```python
def log_fallback(message: str, screenshot: str | None, reason: str | None) -> None:
    logger.warning("Fallback alert (%s): %s", reason or "unknown", message)

notifier = SlackNotifier(..., fallback_handler=log_fallback)
```

Alternatively, wrap the Slack notifier so it tries Telegram first, then falls
back to Slack or logging.

## Step 4 – Test the Integration

1. Run `uv run python monitor_daily.py` (or `uv run cinema-monitor`) with
   feature-flagged test data.
2. Confirm messages arrive in your new channel.
3. Simulate a failure (disconnect network or invalidate the API key) and ensure
   the fallback logs fire.

> **Automation idea:** Write a lightweight integration test that spins up a mock
> HTTP server and asserts the payload format.

## Bonus Ideas

- **Multi-channel fan-out:** Build a notifier that forwards to several transports
  in sequence.
- **Screenshot sharing:** For services that support images, open the screenshot
  file and attach it (already supported in the Telegram notifier).
- **Structured context:** Include seat metadata (row, labels, booking link) as
  fields so channels like Slack can show richer cards.

Once you’ve proven your notifier, document it in `docs/reference.md` so teammates
know it exists. Spark joy, not alert fatigue. 🚀
