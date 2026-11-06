"""Exercise the real download->filesystem->SQLite->NDJSON workflow with a fake Telegram client.

No network requests, credentials, real chats or Telegram session files.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from telegram_media_loader.config import AppConfig
from telegram_media_loader.db import DownloadDB
from telegram_media_loader.downloader import MediaDownloader
from telegram_media_loader.metadata import MetadataWriter


class FakeMessage:
    def __init__(self, message_id: int, at: str, album_id: int):
        self.id = message_id
        self.date = datetime.fromisoformat(at.replace("Z", "+00:00"))
        self.grouped_id = album_id
        self.photo = SimpleNamespace(mime_type="image/jpeg")
        self.media = SimpleNamespace(spoiler=False)
        self.video = None
        self.document = None
        self.sender = SimpleNamespace(username="fictional_sender", first_name="Example", last_name="User")
        self.sender_id = 0
        self.raw_text = "FICTIONAL TELEGRAM MESSAGE"
        self.reply_to_msg_id = None
        self.reply_to = None
        self.fwd_from = None
        self.file = SimpleNamespace(size=9)
        self.calls = 0

    async def download_media(self, file, progress_callback=None):
        self.calls += 1
        target = Path(file)
        target.write_bytes(b"FAKE-JPEG")
        if progress_callback:
            progress_callback(9, 9)
        return str(target)


class FakeTelegramClient:
    def __init__(self, messages):
        self.messages = messages

    async def get_entity(self, chat_ref):
        assert chat_ref == "fictional_test_chat"
        return SimpleNamespace(id=0, title="Fictional Test Channel", username="fictional_test_chat")

    def iter_messages(self, entity, *, offset_date=None, reverse=False):
        async def iterator():
            for message in self.messages:
                yield message
        return iterator()


def test_fake_telegram_media_downloader_roundtrip(tmp_path: Path):
    messages = [
        FakeMessage(101, "2026-11-01T23:58:00Z", 9001),
        FakeMessage(102, "2026-11-02T00:03:00Z", 9001),
    ]
    config = AppConfig(
        api_id=0, api_hash="fake", session_name="not-used", phone_number=None,
        output_root=tmp_path / "downloaded", default_media_types=("photo",),
        log_level="INFO", sqlite_path=tmp_path / "ledger.sqlite", tz="UTC",
    )
    with DownloadDB(config.sqlite_path) as db:
        client = FakeTelegramClient(messages)
        loader = MediaDownloader(client=client, config=config, db=db, metadata_writer=MetadataWriter(config.output_root))
        async def no_count(entity):
            return len(messages)
        async def no_topics(entity):
            return []
        loader._history_count = no_count
        loader._forum_topics = no_topics

        asyncio.run(loader.download("fictional_test_chat", ["photo"], None, None))
        asyncio.run(loader.download("fictional_test_chat", ["photo"], None, None))
        assert [message.calls for message in messages] == [1, 1], "Second pass downloaded duplicates"
        assert db.already_downloaded(0, 101, 1)
        assert db.already_downloaded(0, 102, 1)

    files = list(config.output_root.rglob("*.jpg"))
    assert len(files) == 2
    names = [f.relative_to(config.output_root).as_posix() for f in files]
    assert any("/2026-11-01/101/101.jpg" in f for f in names), names
    assert any("/2026-11-02/101/102.jpg" in f for f in names), names

    metadata_files = list(config.output_root.rglob("metadata.ndjson"))
    assert len(metadata_files) == 1
    rows = [json.loads(line) for line in metadata_files[0].read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert {row["message_id"] for row in rows} == {101, 102}
    assert {row["date_iso"] for row in rows} == {"2026-11-01T23:58:00Z", "2026-11-02T00:03:00Z"}
    assert all(row["file_path"].endswith(".jpg") for row in rows)
