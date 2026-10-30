"""Polling coordinator for an Audio Pro speaker."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AudioProApi, AudioProError
from .const import CONF_STATIONS, DEFAULT_STATIONS, DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


@dataclass
class AudioProData:
    status: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)


type AudioProConfigEntry = ConfigEntry[AudioProCoordinator]


class AudioProCoordinator(DataUpdateCoordinator[AudioProData]):
    """Polls getPlayerStatusEx and getMetaInfo."""

    config_entry: AudioProConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AudioProConfigEntry,
        api: AudioProApi,
        device_info: dict[str, Any],
        eq_list: list[str],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.api = api
        self.device_info = device_info
        self.eq_list = eq_list
        # Last URL we started, so the UI can show its station name.
        self.last_url: str | None = None

    @property
    def stations(self) -> list[dict[str, str]]:
        return self.config_entry.options.get(CONF_STATIONS, DEFAULT_STATIONS)

    def station_for_url(self, url: str | None) -> dict[str, str] | None:
        if not url:
            return None
        return next((s for s in self.stations if s["url"] == url), None)

    async def _async_update_data(self) -> AudioProData:
        try:
            status = await self.api.get_player_status()
        except AudioProError as err:
            raise UpdateFailed(str(err)) from err
        meta = await self.api.get_meta_info()
        return AudioProData(status=status, meta=meta)
