"""Filesystem helpers for chat/topic/media layout."""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Optional


def slugify(value: str, fallback: str) -> str:
    if not value:
        return fallback
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        return fallback
    sanitized = re.sub(r"[<>:\"/\\|?*\x00-\x1F]+", "-", normalized)
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    sanitized = sanitized.strip(" -")
    return sanitized or fallback


def chat_slug(name: Optional[str], username: Optional[str], chat_id: Optional[int]) -> str:
    if username:
        return slugify(username, f"chat_{chat_id or 'unknown'}")
    if name:
        return slugify(name, f"chat_{chat_id or 'unknown'}")
    if chat_id:
        return f"chat_{chat_id}"
    return "chat_unknown"


def topic_slug(topic_title: Optional[str], topic_id: Optional[int]) -> str:
    if topic_title:
        return slugify(topic_title, "__topic")
    if topic_id:
        return f"topic_{topic_id}"
    return "__root"


def media_directory(output_root: Path, chat_slug_value: str, topic_slug_value: str, message_date: date) -> Path:
    return output_root / chat_slug_value / topic_slug_value / message_date.strftime("%Y-%m-%d")


def media_file_path(
    directory: Path,
    message_id: int,
    media_index: int,
    media_type: str,
    extension: str,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{message_id}_{media_index}_{media_type}{extension}"
    return directory / filename
