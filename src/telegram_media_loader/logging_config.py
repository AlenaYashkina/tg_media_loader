"""Central logging configuration for the application."""
from __future__ import annotations

import logging
from pathlib import Path


LOG_FILE_NAME = "app.log"
LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(log_level: str, base_log_dir: Path) -> None:
    """Set up console and file logging."""
    base_log_dir.mkdir(parents=True, exist_ok=True)
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    file_handler = logging.FileHandler(base_log_dir / LOG_FILE_NAME, encoding="utf-8")
    file_handler.setLevel(log_level_value)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(log_level_value)
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)
