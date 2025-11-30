"""Command-line interface for the Telegram media loader."""
from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Sequence

from zoneinfo import ZoneInfo
from tqdm import tqdm

from .config import AppConfig, build_app_config
from .db import DownloadDB
from .downloader import MediaDownloader, ProgressReporter
from .logging_config import configure_logging
from .metadata import MetadataWriter
from .telethon_client import TelethonClientManager

LOGGER = logging.getLogger(__name__)


def parse_media_types(value: Optional[str], default: Sequence[str]) -> Iterable[str]:
    if not value:
        return default
    items = [item.strip().lower() for item in value.split(",")]
    return [item for item in items if item]


def parse_datetime_option(value: Optional[str], tz_name: str) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = timezone.utc
        parsed = parsed.replace(tzinfo=tz)
    return parsed


async def run_download(
    *,
    config: AppConfig,
    chat_url: str,
    media_types: Iterable[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    progress: Optional[ProgressReporter] = None,
) -> None:
    db = DownloadDB(config.sqlite_path)
    metadata_writer = MetadataWriter(config.output_root)
    async with TelethonClientManager(config) as client:
        downloader = MediaDownloader(
            client=client,
            config=config,
            db=db,
            metadata_writer=metadata_writer,
            progress=progress,
        )
        await downloader.download(
            chat_url=chat_url,
            media_types=media_types,
            date_from=date_from,
            date_to=date_to,
        )


class TqdmProgress(ProgressReporter):
    def __init__(self) -> None:
        self._messages = tqdm(desc="Messages", unit="msg")
        self._media = tqdm(desc="Downloaded", unit="media")

    def message_processed(self) -> None:
        self._messages.update(1)

    def media_downloaded(self) -> None:
        self._media.update(1)

    def close(self) -> None:
        self._messages.close()
        self._media.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="telegram_media_loader",
        description="Download media from Telegram chats with metadata tracking.",
    )
    parser.add_argument("--chat-url", required=True, help="Telegram chat or channel URL (https://t.me/...).")
    parser.add_argument("--output-root", required=True, help="Directory where media will be saved.")
    parser.add_argument("--date-from", help="Include messages from this date/time (ISO format).")
    parser.add_argument("--date-to", help="Include messages up to this date/time (ISO format).")
    parser.add_argument("--media-types", help="Comma-separated list of media types to download.")
    parser.add_argument("--config", type=Path, help="Optional YAML/JSON configuration file.")
    parser.add_argument("--log-level", help="Override log level (INFO|DEBUG|ERROR).")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    try:
        config = build_app_config(
            config_path=args.config,
            cli_output_root=Path(args.output_root),
            cli_log_level=args.log_level,
        )
    except Exception as exc:
        LOGGER.error("Failed to build configuration: %s", exc)
        raise

    configure_logging(config.log_level, Path("logs"))

    media_types = parse_media_types(args.media_types, config.default_media_types)
    date_from = parse_datetime_option(args.date_from, config.tz)
    date_to = parse_datetime_option(args.date_to, config.tz)

    progress = TqdmProgress()
    try:
        asyncio.run(
            run_download(
                config=config,
                chat_url=args.chat_url,
                media_types=media_types,
                date_from=date_from,
                date_to=date_to,
                progress=progress,
            )
        )
    except Exception as exc:
        LOGGER.exception("Download failed: %s", exc)
        raise
    finally:
        progress.close()
