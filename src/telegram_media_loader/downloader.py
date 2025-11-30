"""Core downloader logic that walks messages and saves media with topic folders."""
from __future__ import annotations

import asyncio
import logging
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Iterable, Optional, Tuple

from telethon import errors, functions
from telethon.tl.functions.messages import GetForumTopicsByIDRequest, GetForumTopicsRequest
from telethon.tl.types import (
    Channel,
    Chat,
    DocumentAttributeAnimated,
    DocumentAttributeAudio,
    DocumentAttributeSticker,
    DocumentAttributeVideo,
    ForumTopic,
    Message,
    User,
)

from .config import AppConfig
from .db import DownloadDB
from .fs_layout import chat_slug as build_chat_slug, media_directory, topic_slug as build_topic_slug
from .metadata import MetadataWriter
from .models import MediaMetadata

LOGGER = logging.getLogger(__name__)


def _parse_chat_url(chat_url: str) -> str | int:
    value = chat_url.strip()
    if not value:
        raise ValueError("chat_url is required")
    if value in {"me", "self"}:
        return value
    match = re.match(r"https?://t\.me/c/(\d+)", value)
    if match:
        return int(f"-100{match.group(1)}")
    match = re.search(r"#(-?\d+)", value)
    if match:
        return int(match.group(1))
    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        return int(value)
    return value


class ProgressReporter:
    def message_processed(self) -> None:
        ...

    def media_downloaded(self) -> None:
        ...


class MediaDownloader:
    def __init__(
        self,
        *,
        client,
        config: AppConfig,
        db: DownloadDB,
        metadata_writer: MetadataWriter,
        progress: Optional[ProgressReporter] = None,
    ):
        self._client = client
        self._config = config
        self._db = db
        self._metadata_writer = metadata_writer
        self._progress = progress
        self._topic_cache: dict[int, str] = {}
        self._album_root_ids: dict[int, int] = {}
        self._entity = None

    async def download(
        self,
        chat_url: str,
        media_types: Iterable[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
    ) -> None:
        allowed_media = {value.lower() for value in media_types}
        entity = await self._client.get_entity(_parse_chat_url(chat_url))
        self._entity = entity
        chat_slug = build_chat_slug(
            getattr(entity, "title", None),
            getattr(entity, "username", None),
            getattr(entity, "id", None),
        )
        chat_type = self._determine_chat_type(entity, chat_url)
        chat_title = getattr(entity, "title", None) or ("Saved Messages" if chat_type == "saved" else None)
        topics = await self._forum_topics(entity)
        date_from_utc = date_from.astimezone(timezone.utc) if date_from else None
        date_to_utc = date_to.astimezone(timezone.utc) if date_to else None

        LOGGER.info("Downloading history for %s (%s)", chat_slug, chat_type)
        if topics:
            for topic in topics:
                topic_id = getattr(topic, "id", None)
                if topic_id:
                    title = getattr(topic, "title", None)
                    if title:
                        self._topic_cache[topic_id] = title

        iterator = self._iter_messages(entity, date_to)
        await self._process_iterator(iterator, chat_slug, chat_type, allowed_media, chat_title, date_from_utc, date_to_utc)

    async def _process_iterator(
        self,
        iterator: AsyncIterator[Message],
        chat_slug: str,
        chat_type: str,
        allowed_media: set[str],
        chat_title: Optional[str],
        date_from: Optional[datetime],
        date_to: Optional[datetime],
    ) -> None:
        async for message in iterator:
            if await self._handle_message(
                message=message,
                allowed_media=allowed_media,
                chat_slug=chat_slug,
                chat_type=chat_type,
                chat_username=getattr(message.sender, "username", None),
                chat_title=chat_title,
                date_from_utc=date_from,
                date_to_utc=date_to,
            ):
                return

    async def _iter_messages(self, entity, offset_date: Optional[datetime]) -> AsyncIterator[Message]:
        iterator = self._client.iter_messages(entity, offset_date=offset_date, reverse=False)
        while True:
            try:
                yield await iterator.__anext__()
            except StopAsyncIteration:
                break
            except errors.FloodWaitError as exc:
                LOGGER.warning("Flood wait %s seconds while iterating history", exc.seconds)
                await asyncio.sleep(exc.seconds)

    async def _handle_message(
        self,
        message: Message,
        allowed_media: set[str],
        chat_slug: str,
        chat_type: str,
        chat_username: Optional[str],
        chat_title: Optional[str],
        date_from_utc: Optional[datetime],
        date_to_utc: Optional[datetime],
        topic_override: Optional[Tuple[int, Optional[str]]] = None,
    ) -> bool:
        if not message or not message.media:
            return False
        if date_to_utc and message.date.astimezone(timezone.utc) > date_to_utc:
            return False

        media_type, mime_type = self._describe_media(message)
        if media_type not in allowed_media:
            return False

        metadata = await self._process_media(
            message=message,
            media_type=media_type,
            mime_type=mime_type,
            chat_slug=chat_slug,
            chat_type=chat_type,
            chat_id=getattr(self._entity, "id", None),
            chat_title=chat_title,
            chat_username=chat_username,
            topic_override=topic_override,
        )
        self._metadata_writer.write(chat_slug, metadata)
        self._progress and self._progress.media_downloaded()
        return False

    async def _process_media(
        self,
        message: Message,
        media_type: str,
        mime_type: Optional[str],
        chat_slug: str,
        chat_type: str,
        chat_id: Optional[int],
        chat_title: Optional[str],
        chat_username: Optional[str],
        topic_override: Optional[Tuple[int, Optional[str]]] = None,
    ) -> MediaMetadata:
        msg_date_utc = message.date.astimezone(timezone.utc)
        topic_id, topic_title = await self._resolve_topic_info(message, topic_override)
        if topic_id is not None and not topic_title:
            topic_title = f"topic-{topic_id}"
        topic_folder = build_topic_slug(topic_title, topic_id)
        directory = media_directory(
            self._config.output_root, chat_slug, topic_folder, message.date.astimezone(timezone.utc).date()
        )
        album_folder = self._album_folder(message.grouped_id, message)
        if album_folder:
            directory = directory / album_folder
        directory.mkdir(parents=True, exist_ok=True)

        extension = self._extension_from_message(message, media_type, mime_type)
        filename = f"{message.id}{extension}"
        destination = directory / filename
        file_path = destination
        file_size: Optional[int] = None
        download_success = False
        for attempt in range(2):
            try:
                saved = await message.download_media(file=str(destination))
                if saved:
                    file_path = Path(saved)
                    file_size = file_path.stat().st_size if file_path.exists() else None
                    download_success = True
                    break
            except errors.FloodWaitError as exc:
                LOGGER.warning("Flood wait %s seconds for message %s", exc.seconds, message.id)
                await asyncio.sleep(exc.seconds + 1)
            except Exception as exc:
                LOGGER.debug("Download attempt %s failed for %s: %s", attempt + 1, message.id, exc)

        status = "success" if download_success else "failed"
        self._db.record_media(
            chat_id=chat_id or 0,
            message_id=message.id,
            media_index=1,
            media_type=media_type,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=mime_type,
            date_iso=self._iso_date(msg_date_utc),
            status=status,
        )
        if topic_id is not None and topic_title:
            self._topic_cache[topic_id] = topic_title
        rel_path = file_path.relative_to(self._config.output_root) if file_path.exists() else file_path

        return MediaMetadata(
            chat_id=chat_id or 0,
            chat_username=chat_username,
            chat_title=chat_title,
            chat_type=chat_type,
            message_id=message.id,
            grouped_id=getattr(message, "grouped_id", None),
            topic_id=topic_id,
            topic_title=topic_title,
            date_iso=self._iso_date(msg_date_utc),
            sender_id=message.sender_id,
            sender_username=getattr(message.sender, "username", None),
            sender_display_name=self._display_name(message),
            text_raw=message.raw_text,
            reply_to_message_id=getattr(message, "reply_to_msg_id", None),
            media_type=media_type,
            file_path=str(rel_path),
            file_size=file_size,
            mime_type=mime_type,
            has_spoiler=bool(getattr(message.media, "spoiler", False)),
            is_forwarded=bool(message.fwd_from),
            forward_from_id=self._forward_from_id(message),
            forward_from_username=self._forward_from_username(message),
            extra={},
        )

    async def _resolve_topic_info(
        self,
        message: Message,
        topic_override: Optional[Tuple[int, Optional[str]]],
    ) -> Tuple[Optional[int], Optional[str]]:
        override_id, override_title = topic_override or (None, None)
        topic_id: Optional[int] = override_id
        topic_title: Optional[str] = override_title

        if topic_id is None:
            topic_id = getattr(message, "topic_id", None)

        if topic_id is None:
            topic_id = self._topic_id_from_reply(message)

        if topic_id is not None and not topic_title:
            topic_title = self._topic_cache.get(topic_id)
            if topic_title is None:
                topic_title = await self._topic_title(topic_id)

        return topic_id, topic_title

    def _topic_id_from_reply(self, message: Message) -> Optional[int]:
        """Derive a forum topic ID based on the reply header semantics."""
        reply_to = getattr(message, "reply_to", None)
        if not reply_to or not getattr(reply_to, "forum_topic", False):
            return None
        top_id = getattr(reply_to, "reply_to_top_id", None)
        if top_id is not None:
            return top_id
        return getattr(reply_to, "reply_to_msg_id", None)

    async def _topic_title(self, topic_id: Optional[int]) -> Optional[str]:
        if not topic_id or not self._entity:
            return None

        GetByID = getattr(functions.messages, "GetForumTopicsByIDRequest", None)
        arg_name = "peer"
        if GetByID is None:
            GetByID = getattr(functions.channels, "GetForumTopicsByIDRequest", None)
            arg_name = "channel"
        if GetByID is None:
            return None

        try:
            req = GetByID(**{arg_name: self._entity}, topics=[topic_id])
            response = await self._client(req)
            topics = getattr(response, "topics", []) or []
            if topics:
                title = getattr(topics[0], "title", None)
                if title:
                    self._topic_cache[topic_id] = title
                    return title
        except Exception:
            LOGGER.debug("Unable to resolve topic title for %s", topic_id, exc_info=True)
        return None

    async def _forum_topics(self, entity: Channel) -> list[ForumTopic]:
        if not isinstance(entity, Channel):
            return []
        GetTopics = getattr(functions.messages, "GetForumTopicsRequest", None)
        arg_name = "peer"
        if GetTopics is None:
            GetTopics = getattr(functions.channels, "GetForumTopicsRequest", None)
            arg_name = "channel"
        if GetTopics is None:
            return []

        topics: list[ForumTopic] = []
        limit = 100
        offset_date = 0
        offset_id = 0
        offset_topic = 0
        while True:
            try:
                req = GetTopics(
                    **{arg_name: entity},
                    q="",
                    offset_date=offset_date,
                    offset_id=offset_id,
                    offset_topic=offset_topic,
                    limit=limit,
                )
                response = await self._client(req)
            except errors.RPCError:
                break
            page = getattr(response, "topics", []) or []
            if not page:
                break
            topics.extend(page)
            last = page[-1]
            offset_date = getattr(last, "date", offset_date)
            offset_id = getattr(last, "id", offset_id)
            offset_topic = getattr(last, "id", offset_topic)
            if len(page) < limit:
                break

        for topic in topics:
            tid = getattr(topic, "id", None)
            title = getattr(topic, "title", None)
            if tid is not None and title:
                self._topic_cache[tid] = title
        return topics

    def _describe_media(self, message: Message) -> Tuple[str, Optional[str]]:
        if message.photo:
            return "photo", getattr(message.photo, "mime_type", None)
        if message.video:
            return "video", getattr(message.video, "mime_type", None)
        if message.document:
            doc = message.document
            mime_type = doc.mime_type
            attrs = doc.attributes or []
            if any(isinstance(attr, DocumentAttributeSticker) for attr in attrs):
                return "sticker", mime_type
            if any(isinstance(attr, DocumentAttributeAudio) and getattr(attr, "voice", False) for attr in attrs):
                return "voice", mime_type
            if any(isinstance(attr, DocumentAttributeAudio) for attr in attrs):
                return "audio", mime_type
            if any(isinstance(attr, DocumentAttributeAnimated) for attr in attrs):
                return "gif", mime_type
            if any(isinstance(attr, DocumentAttributeVideo) for attr in attrs):
                return "video", mime_type
            return "document", mime_type
        return "other", None

    def _album_folder(self, grouped_id: Optional[int], message: Message) -> Optional[str]:
        if not grouped_id:
            return None
        current = self._album_root_ids.get(grouped_id)
        if current is None:
            current = message.id
            self._album_root_ids[grouped_id] = current
        return str(current)

    def _extension_from_message(self, message: Message, media_type: str, mime_type: Optional[str]) -> str:
        if media_type == "photo":
            return ".jpg"
        if media_type == "video":
            return ".mp4"
        if media_type == "gif":
            return ".gif"
        if media_type == "sticker":
            return ".webp"
        if media_type == "voice":
            return ".ogg"
        if message.document and message.document.file_name:
            suffix = Path(message.document.file_name).suffix
            if suffix:
                return suffix
        if mime_type:
            guess = mimetypes.guess_extension(mime_type.split(";")[0])
            if guess:
                return guess
        return ".bin"

    def _display_name(self, message: Message) -> Optional[str]:
        sender = message.sender
        if not sender:
            return None
        names = [getattr(sender, "first_name", None), getattr(sender, "last_name", None)]
        joined = " ".join(filter(None, names)).strip()
        if joined:
            return joined
        return getattr(sender, "title", None) or getattr(sender, "username", None)

    def _forward_from_id(self, message: Message) -> Optional[int]:
        if not message.fwd_from:
            return None
        from_id = getattr(message.fwd_from, "from_id", None)
        if from_id:
            return getattr(from_id, "user_id", None) or getattr(from_id, "channel_id", None)
        return None

    def _forward_from_username(self, message: Message) -> Optional[str]:
        if not message.fwd_from:
            return None
        return getattr(message.fwd_from, "from_name", None)

    def _iso_date(self, dt: datetime) -> str:
        iso = dt.astimezone(timezone.utc).isoformat()
        if iso.endswith("+00:00"):
            iso = iso[:-6] + "Z"
        return iso

    def _determine_chat_type(self, entity, chat_url: str) -> str:
        if chat_url in {"me", "self"}:
            return "saved"
        if isinstance(entity, User):
            return "private"
        if isinstance(entity, Channel):
            if getattr(entity, "broadcast", False):
                return "channel"
            if getattr(entity, "megagroup", False):
                return "supergroup"
            return "channel"
        if isinstance(entity, Chat):
            return "group"
        return "private"
