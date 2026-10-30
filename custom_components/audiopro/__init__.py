"""Audio Pro (LinkPlay) speakers, controlled by IP address without discovery."""
from __future__ import annotations

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AudioProApi, AudioProError
from .coordinator import AudioProConfigEntry, AudioProCoordinator

PLATFORMS = [
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: AudioProConfigEntry) -> bool:
    api = AudioProApi(entry.data[CONF_HOST], async_get_clientsession(hass, verify_ssl=False))
    try:
        device_info = await api.get_device_info()
    except AudioProError as err:
        raise ConfigEntryNotReady(str(err)) from err
    eq_list = await api.get_eq_list()

    coordinator = AudioProCoordinator(hass, entry, api, device_info, eq_list)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: AudioProConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: AudioProConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
