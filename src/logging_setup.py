from __future__ import annotations

import logging
import logging.config
import os
from pathlib import Path
from typing import Optional


def setup_logging(
    level: Optional[str] = None, log_file: Optional[str] = None, httpx_level: str = "WARNING"
) -> None:
    """
    Configure application logging.

    Args:
        level: Base log level (defaults to LOG_LEVEL env or INFO).
        log_file: Optional path to a rotating log file (defaults to LOG_FILE env).
        httpx_level: Logging level for noisy third-party loggers.
    """

    log_level = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    file_path = log_file or os.getenv("LOG_FILE")

    handlers = ["console"]
    handler_configs = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": log_level,
        }
    }

    if file_path:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        handlers.append("file")
        handler_configs["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "level": log_level,
            "filename": file_path,
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
        }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                }
            },
            "handlers": handler_configs,
            "root": {
                "level": log_level,
                "handlers": handlers,
            },
        }
    )

    # Reduce noise from httpx/httpcore unless explicitly overridden.
    logging.getLogger("httpx").setLevel(httpx_level)
    logging.getLogger("httpcore").setLevel(httpx_level)
