"""Select entity to pick a radio station from the configured list."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AudioProError
from .coordinator import AudioProConfigEntry, AudioProCoordinator
from .entity import AudioProEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AudioProConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AudioProStationSelect(entry.runtime_data)])


class AudioProStationSelect(AudioProEntity, SelectEntity):
    _attr_translation_key = "station"
    _attr_icon = "mdi:radio"

    def __init__(self, coordinator: AudioProCoordinator) -> None:
        super().__init__(coordinator, "station")
        self._attr_options = [s["name"] for s in coordinator.stations]

    @property
    def current_option(self) -> str | None:
        station = self.current_station
        return station["name"] if station else None

    async def async_select_option(self, option: str) -> None:
        station = next((s for s in self.coordinator.stations if s["name"] == option), None)
        if station is None:
            raise HomeAssistantError(f"Unknown station: {option}")
        self.coordinator.last_url = station["url"]
        try:
            await self.coordinator.api.play_url(station["url"])
        except AudioProError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
