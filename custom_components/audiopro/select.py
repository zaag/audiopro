"""Select entities: radio station, audio source and equalizer preset."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import MODE_TO_SOURCE, SOURCES
from .coordinator import AudioProConfigEntry, AudioProCoordinator
from .entity import AudioProEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AudioProConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = [
        AudioProStationSelect(coordinator),
        AudioProSourceSelect(coordinator),
    ]
    if coordinator.eq_list:
        entities.append(AudioProEqualizerSelect(coordinator))
    async_add_entities(entities)


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
        await self.async_run(self.coordinator.api.play_url(station["url"]))


class AudioProSourceSelect(AudioProEntity, SelectEntity):
    _attr_translation_key = "source"
    _attr_icon = "mdi:import"
    _attr_options = list(SOURCES.values())

    def __init__(self, coordinator: AudioProCoordinator) -> None:
        super().__init__(coordinator, "source")

    @property
    def current_option(self) -> str | None:
        key = MODE_TO_SOURCE.get(str(self.coordinator.data.status.get("mode")))
        return SOURCES.get(key) if key else None

    async def async_select_option(self, option: str) -> None:
        key = next((k for k, v in SOURCES.items() if v == option), None)
        if key is None:
            raise HomeAssistantError(f"Unknown source: {option}")
        await self.async_run(self.coordinator.api.switch_source(key))


class AudioProEqualizerSelect(AudioProEntity, SelectEntity):
    _attr_translation_key = "equalizer_preset"
    _attr_icon = "mdi:tune-vertical"

    def __init__(self, coordinator: AudioProCoordinator) -> None:
        super().__init__(coordinator, "equalizer_preset")
        self._attr_options = coordinator.eq_list

    @property
    def current_option(self) -> str | None:
        name = self.coordinator.data.settings.eq.get("Name")
        return name if name in self.options else None

    async def async_select_option(self, option: str) -> None:
        await self.async_run(self.coordinator.api.load_eq(option), settings=True)
