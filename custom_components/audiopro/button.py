"""Buttons: speaker presets and reboot."""
from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AudioProConfigEntry, AudioProCoordinator
from .entity import AudioProEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AudioProConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[ButtonEntity] = [AudioProRebootButton(coordinator)]
    # Presets stored on the speaker itself (set via the Audio Pro app); often empty.
    for index, preset in enumerate(coordinator.data.settings.presets, start=1):
        number = int(preset.get("number", index))
        name = preset.get("name") or f"Preset {number}"
        entities.append(AudioProPresetButton(coordinator, number, name))
    async_add_entities(entities)


class AudioProPresetButton(AudioProEntity, ButtonEntity):
    def __init__(self, coordinator: AudioProCoordinator, number: int, name: str) -> None:
        super().__init__(coordinator, f"preset_{number}")
        self._number = number
        self._attr_name = f"Preset {number}: {name}"
        self._attr_icon = f"mdi:numeric-{number}-box" if number < 10 else "mdi:star"

    async def async_press(self) -> None:
        await self.async_run(self.coordinator.api.play_preset(self._number))


class AudioProRebootButton(AudioProEntity, ButtonEntity):
    _attr_translation_key = "reboot"
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AudioProCoordinator) -> None:
        super().__init__(coordinator, "reboot")

    async def async_press(self) -> None:
        await self.async_run(self.coordinator.api.reboot())
