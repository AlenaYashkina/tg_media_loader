"""NDJSON writer for per-chat metadata."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import MediaMetadata


class MetadataWriter:
    def __init__(self, base_root: Path) -> None:
        self.base_root = base_root

    def write(self, chat_slug: str, metadata: MediaMetadata) -> None:
        metadata_path = self.base_root / chat_slug / "metadata.ndjson"
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("a", encoding="utf-8") as fh:
            json.dump(metadata.to_json(), fh, ensure_ascii=False)
            fh.write("\n")
