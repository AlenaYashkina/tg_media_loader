"""Dataclasses used throughout the application."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class MediaMetadata:
    chat_id: int
    chat_username: Optional[str]
    chat_title: Optional[str]
    chat_type: str
    message_id: int
    grouped_id: Optional[int]
    topic_id: Optional[int]
    topic_title: Optional[str]
    date_iso: str
    sender_id: Optional[int]
    sender_username: Optional[str]
    sender_display_name: Optional[str]
    text_raw: Optional[str]
    reply_to_message_id: Optional[int]
    media_type: str
    file_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    has_spoiler: bool
    is_forwarded: bool
    forward_from_id: Optional[int]
    forward_from_username: Optional[str]
    extra: Dict[str, Any]

    def to_json(self) -> str:
        return asdict(self)
