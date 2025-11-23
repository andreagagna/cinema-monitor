# Cinema Monitor

A Python-based tool to monitor a cinema website for specific movie availability and send notifications via Telegram.

## Description

This project monitors the Cinema City website for the movie "Avatar: Fire and Ashes" (IMAX 3D) and alerts when tickets become available or new dates are added.

## Features

- Monitors availability for a specific movie and format.
- Checks for new dates in the schedule.
- Sends notifications via Telegram.

## Tech Stack

- Python
- uv (Dependency Management)
- Playwright (Web Scraping)
- Python Telegram Bot

## Setup & Usage

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd cinema-monitor
    ```

2.  **Install dependencies:**
    ```bash
    uv sync
    # OR
    pip install -r requirements.txt
    ```

3.  **Install Playwright browsers:**
    ```bash
    uv run playwright install chromium
    ```

### Configuration

1.  Create a `.env` file in the root directory:
    ```bash
    cp .env.example .env  # If example exists, otherwise create new
    ```

2.  Add your Telegram credentials to `.env`:
    ```ini
    TELEGRAM_BOT_TOKEN=your_bot_token
    TELEGRAM_CHAT_ID=your_chat_id
    ```

    To find the chat ID in Telegram, see this: [Get Chat ID For a Channel](https://gist.github.com/nafiesl/4ad622f344cd1dc3bb1ecbe468ff9f8a#get-chat-id-for-a-channel).

3.  (Optional) Modify `src/config.py` to change the target movie, date, or cinema location.

### Running the Monitor

Execute the monitor via the project script:
```bash
uv run cinema-monitor
```

The script will:
1.  Use `SeatAdvisor` + `MonitorScheduler` to sweep the configured date range.
2.  Fetch seat maps via HTTP, parse the SVG, and evaluate seat quality.
3.  Send Telegram alerts (if configured) for the best available seats.

## Further Documentation

High-level architecture notes, design decisions, and contributor guidance now live in `docs/`:

- `docs/architecture.md` – module map and data flow.
- `docs/decisions.md` – rationale behind major choices.

Please keep these documents up to date when extending the project.

## Development

We run formatting/linting/type checks in CI:

```bash
ruff check .
black --check .
mypy src
pytest
```

The GitHub Actions workflow `.github/workflows/ci.yml` mirrors these commands.
