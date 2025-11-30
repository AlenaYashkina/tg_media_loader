"""Telethon wrapper for authorization and session handling."""
from __future__ import annotations

import logging

from telethon import TelegramClient

from .config import AppConfig

LOGGER = logging.getLogger(__name__)


class TelethonClientManager:
    def __init__(self, config: AppConfig):
        self._config = config
        self._client = TelegramClient(
            config.session_name,
            config.api_id,
            config.api_hash,
        )

    async def __aenter__(self) -> TelegramClient:
        await self._client.connect()
        if not await self._client.is_user_authorized():
            await self._client.disconnect()
            raise RuntimeError(
                "Telegram session is not authorized. "
                "Please prepare a working session file with Telethon before running the downloader."
            )
        LOGGER.debug("Telethon client authorized and ready")
        return self._client

    async def __aexit__(self, *exc_info) -> None:
        await self._client.disconnect()
