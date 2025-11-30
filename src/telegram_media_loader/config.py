"""Configuration helpers for the Telegram media loader."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import yaml
from dotenv import load_dotenv


DEFAULT_MEDIA_TYPES = ("photo", "video", "document", "audio", "voice", "sticker", "gif", "other")
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_SQLITE = Path("data") / "state.sqlite"
DEFAULT_TZ = "UTC"


@dataclass
class AppConfig:
    api_id: int
    api_hash: str
    session_name: str
    phone_number: Optional[str]
    output_root: Path
    default_media_types: tuple[str, ...]
    log_level: str
    sqlite_path: Path
    tz: str


def load_env(env_path: Optional[Path] = None) -> dict:
    """Load sensitive values from a .env file or environment."""
    load_dotenv(env_path or Path(".env"), override=False)
    values = {
        "api_id": os.getenv("TG_API_ID"),
        "api_hash": os.getenv("TG_API_HASH"),
        "phone_number": os.getenv("TG_PHONE_NUMBER"),
        "session_name": os.getenv("TG_SESSION_NAME", "media_loader"),
    }
    return values


def load_config_file(config_path: Optional[Path]) -> dict:
    """Load YAML or JSON configuration from disk."""
    if not config_path:
        return {}
    config_path = config_path.expanduser()
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    if config_path.suffix in {".yaml", ".yml"}:
        loader = yaml.safe_load
    elif config_path.suffix == ".json":
        loader = json.load
    else:
        raise ValueError("Config must be YAML or JSON")
    with config_path.open("r", encoding="utf-8") as fh:
        data = loader(fh)
    return data or {}


def normalize_media_types(values: Optional[Iterable[str]]) -> tuple[str, ...]:
    if not values:
        return DEFAULT_MEDIA_TYPES
    normalized = []
    for item in values:
        for entry in (item.split(",") if isinstance(item, str) else [item]):
            stripped = entry.strip().lower()
            if not stripped:
                continue
            normalized.append(stripped)
    return tuple(dict.fromkeys(normalized)) or DEFAULT_MEDIA_TYPES


def build_app_config(
    *,
    config_path: Optional[Path],
    cli_output_root: Optional[Path],
    cli_log_level: Optional[str],
) -> AppConfig:
    env_values = load_env()
    config_values = load_config_file(config_path)

    api_id = env_values.get("api_id") or config_values.get("api_id") or config_values.get("TG_API_ID")
    api_hash = env_values.get("api_hash") or config_values.get("api_hash") or config_values.get("TG_API_HASH")
    if not api_id or not api_hash:
        raise ValueError("TG_API_ID and TG_API_HASH must be set in .env or config file.")
    try:
        api_id = int(api_id)
    except ValueError as exc:
        raise ValueError("TG_API_ID must be an integer.") from exc

    output_root = Path(
        cli_output_root
        or config_values.get("output_root")
        or os.getenv("OUTPUT_ROOT")
        or Path.cwd() / "downloads"
    ).expanduser()

    sqlite_path = Path(
        config_values.get("sqlite_path") or DEFAULT_SQLITE
    ).expanduser()

    session_name = (
        env_values.get("session_name")
        or config_values.get("session_name")
        or config_values.get("TG_SESSION_NAME")
        or "media_loader"
    )
    phone_number = env_values.get("phone_number") or config_values.get("phone_number") or config_values.get("TG_PHONE_NUMBER")

    default_media_types = normalize_media_types(config_values.get("default_media_types"))

    tz_value = config_values.get("tz") or DEFAULT_TZ

    log_level = cli_log_level or config_values.get("log_level") or DEFAULT_LOG_LEVEL
    log_level = log_level.upper()

    return AppConfig(
        api_id=api_id,
        api_hash=api_hash,
        session_name=session_name,
        phone_number=phone_number,
        output_root=output_root,
        default_media_types=default_media_types,
        log_level=log_level,
        sqlite_path=sqlite_path,
        tz=tz_value,
    )
