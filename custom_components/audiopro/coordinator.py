"""Polling coordinator for an Audio Pro speaker."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AudioProApi, AudioProError
from .const import (
    CONF_STATIONS,
    DEFAULT_STATIONS,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
    SETTINGS_EVERY_N_POLLS,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class AudioProSettings:
    """Speaker settings that change rarely; polled less often than playback."""

    eq: dict[str, Any] = field(default_factory=dict)
    balance: float | None = None
    led: bool | None = None
    sleep_timer: int | None = None
    rssi: int | None = None
    presets: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AudioProData:
    status: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    settings: AudioProSettings = field(default_factory=AudioProSettings)


type AudioProConfigEntry = ConfigEntry[AudioProCoordinator]


class AudioProCoordinator(DataUpdateCoordinator[AudioProData]):
    """Polls playback every few seconds and settings every SETTINGS_EVERY_N_POLLS."""

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
        self._polls = 0
        self._refresh_settings = True

    @property
    def stations(self) -> list[dict[str, str]]:
        return self.config_entry.options.get(CONF_STATIONS, DEFAULT_STATIONS)

    def station_for_url(self, url: str | None) -> dict[str, str] | None:
        if not url:
            return None
        return next((s for s in self.stations if s["url"] == url), None)

    async def async_refresh_settings(self) -> None:
        """Re-read settings right away, e.g. after changing one."""
        self._refresh_settings = True
        await self.async_request_refresh()

    async def _async_update_data(self) -> AudioProData:
        try:
            status = await self.api.get_player_status()
        except AudioProError as err:
            raise UpdateFailed(str(err)) from err
        meta = await self.api.get_meta_info()

        settings = self.data.settings if self.data else AudioProSettings()
        self._polls += 1
        if self._refresh_settings or self._polls % SETTINGS_EVERY_N_POLLS == 0:
            self._refresh_settings = False
            settings = await self._fetch_settings(settings)
        return AudioProData(status=status, meta=meta, settings=settings)

    async def _fetch_settings(self, old: AudioProSettings) -> AudioProSettings:
        results = await asyncio.gather(
            self.api.get_eq_state(),
            self.api.get_balance(),
            self.api.get_led(),
            self.api.get_sleep_timer(),
            self.api.get_device_info(),
            self.api.get_presets(),
            return_exceptions=True,
        )
        eq, balance, led, sleep_timer, info, presets = (
            None if isinstance(r, BaseException) else r for r in results
        )
        rssi = old.rssi
        if isinstance(info, dict):
            self.device_info = info
            try:
                rssi = int(info["RSSI"])
            except (KeyError, ValueError):
                pass
        return AudioProSettings(
            eq=eq if eq is not None else old.eq,
            balance=balance if balance is not None else old.balance,
            led=led if led is not None else old.led,
            sleep_timer=sleep_timer if sleep_timer is not None else old.sleep_timer,
            rssi=rssi,
            presets=presets if presets is not None else old.presets,
        )
