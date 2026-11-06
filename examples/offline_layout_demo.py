"""Build a small fictional Telegram-media folder example without connecting to Telegram.

Usage: python examples/offline_layout_demo.py
Writes to a temporary folder and verifies repeat-run idempotency.
"""
from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from telegram_media_loader.db import DownloadDB
from telegram_media_loader.fs_layout import media_directory

# No original Telegram IDs, messages, or downloaded images are used.
EXAMPLES = [
    (101, 9001, "2026-11-01T23:58:00Z"),
    (102, 9001, "2026-11-02T00:03:00Z"),
    (103, None, "2026-11-02T00:08:00Z"),
]


def create_example(root: Path) -> list[str]:
    output = root / "fictional-media"
    created: list[str] = []
    with DownloadDB(root / "demo.sqlite") as ledger:
        album_roots: dict[int, int] = {}
        for _ in range(2):
            for message_id, grouped_id, iso in EXAMPLES:
                if ledger.already_downloaded(0, message_id, 1):
                    continue
                date = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
                destination = media_directory(output, "fictional-channel", "__root", date.date())
                if grouped_id is not None:
                    destination = destination / str(album_roots.setdefault(grouped_id, message_id))
                destination.mkdir(parents=True, exist_ok=True)
                file = destination / f"{message_id}.txt"
                # Placeholder text files, not fabricated camera photos.
                file.write_text(f"FICTIONAL MEDIA PLACEHOLDER: {message_id}\n", encoding="utf-8")
                ledger.record_media(
                    chat_id=0, message_id=message_id, media_index=1,
                    media_type="document", file_path=str(file),
                    file_size=file.stat().st_size, mime_type="text/plain",
                    date_iso=iso, status="success",
                )
                created.append(str(file.relative_to(root)))
        assert len(created) == len(EXAMPLES), "Repeated pass produced duplicate files"
        assert ledger.already_downloaded(0, 101, 1)
    return created


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tg-media-portfolio-") as workspace:
        root = Path(workspace)
        files = create_example(root)
        print(json.dumps({"mode": "synthetic", "timezone": "UTC", "files": files}, indent=2))
        assert files == [
            "fictional-media/fictional-channel/__root/2026-11-01/101/101.txt",
            "fictional-media/fictional-channel/__root/2026-11-02/101/102.txt",
            "fictional-media/fictional-channel/__root/2026-11-02/103.txt",
        ]
        print("PASS: album grouping, UTC date boundary, no duplicate on rerun")


if __name__ == "__main__":
    main()
