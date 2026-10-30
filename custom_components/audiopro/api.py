"""Minimal client for the LinkPlay HTTP API used by Audio Pro W-series speakers."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import aiohttp
from yarl import URL


class AudioProError(Exception):
    """Raised when the speaker cannot be reached or rejects a command."""


def decode_hex(value: str | None) -> str:
    """Decode the hex-encoded Title/Artist/Album fields of getPlayerStatusEx."""
    if not value:
        return ""
    try:
        return bytes.fromhex(value).decode("utf-8", "replace")
    except ValueError:
        return value


def clean(value: str | None) -> str:
    """Return '' for the speaker's placeholder values."""
    if not value or value.lower() in ("unknow", "un_known", "unknown"):
        return ""
    return value


class AudioProApi:
    """Talks to https://<host>/httpapi.asp?command=..."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        self.host = host
        self._session = session

    async def request(self, command: str) -> Any:
        """Send a command; return parsed JSON or the plain-text reply."""
        # Encode everything except the ':' separators, so stream URLs with '?' or '&'
        # stay inside the command parameter.
        url = URL(
            f"https://{self.host}/httpapi.asp?command={quote(command, safe=':/,')}",
            encoded=True,
        )
        try:
            async with self._session.get(
                url, ssl=False, timeout=aiohttp.ClientTimeout(total=8)
            ) as resp:
                resp.raise_for_status()
                text = await resp.text(errors="replace")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AudioProError(f"{self.host}: {err}") from err
        text = text.strip()
        if text in ("unknown command", "Failed", '{"status":"Failed"}'):
            raise AudioProError(f"{command}: {text}")
        try:
            return json.loads(text)
        except ValueError:
            return text

    async def get_device_info(self) -> dict[str, Any]:
        return await self.request("getStatusEx")

    async def get_player_status(self) -> dict[str, Any]:
        return await self.request("getPlayerStatusEx")

    async def get_meta_info(self) -> dict[str, Any]:
        try:
            data = await self.request("getMetaInfo")
        except AudioProError:
            return {}
        return data.get("metaData", {}) if isinstance(data, dict) else {}

    async def get_eq_list(self) -> list[str]:
        try:
            data = await self.request("EQGetList")
        except AudioProError:
            return []
        return data if isinstance(data, list) else []

    async def play_url(self, url: str) -> None:
        if url.lower().split("?")[0].endswith((".m3u", ".pls")):
            await self.request(f"setPlayerCmd:m3u:play:{url}")
        else:
            await self.request(f"setPlayerCmd:play:{url}")

    async def player_cmd(self, cmd: str) -> None:
        await self.request(f"setPlayerCmd:{cmd}")

    async def set_volume(self, volume: int) -> None:
        await self.player_cmd(f"vol:{max(0, min(100, volume))}")

    async def set_mute(self, mute: bool) -> None:
        await self.player_cmd(f"mute:{int(mute)}")

    async def switch_source(self, source: str) -> None:
        await self.player_cmd(f"switchmode:{source}")

    async def load_eq(self, name: str) -> None:
        await self.request(f"EQLoad:{name}")
