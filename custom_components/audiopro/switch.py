"""Switch entities: mute, equalizer and status LED."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AudioProApi
from .coordinator import AudioProConfigEntry, AudioProCoordinator, AudioProData
from .entity import AudioProEntity


@dataclass(frozen=True, kw_only=True)
class AudioProSwitchDescription(SwitchEntityDescription):
    value_fn: Callable[[AudioProData], bool | None]
    set_fn: Callable[[AudioProApi, bool], Awaitable[None]]
    is_setting: bool = True


def _eq_on(data: AudioProData) -> bool | None:
    stat = data.settings.eq.get("EQStat")
    return None if stat is None else stat == "On"


SWITCHES = (
    AudioProSwitchDescription(
        key="mute",
        translation_key="mute",
        icon="mdi:volume-off",
        value_fn=lambda d: d.status.get("mute") == "1",
        set_fn=lambda api, on: api.set_mute(on),
        is_setting=False,
    ),
    AudioProSwitchDescription(
        key="equalizer",
        translation_key="equalizer",
        icon="mdi:equalizer",
        entity_category=EntityCategory.CONFIG,
        value_fn=_eq_on,
        set_fn=lambda api, on: api.set_eq_enabled(on),
    ),
    AudioProSwitchDescription(
        key="led",
        translation_key="led",
        icon="mdi:led-on",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda d: d.settings.led,
        set_fn=lambda api, on: api.set_led(on),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: AudioProConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(AudioProSwitch(entry.runtime_data, d) for d in SWITCHES)


class AudioProSwitch(AudioProEntity, SwitchEntity):
    entity_description: AudioProSwitchDescription

    def __init__(self, coordinator: AudioProCoordinator, description: AudioProSwitchDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, on: bool) -> None:
        await self.async_run(
            self.entity_description.set_fn(self.coordinator.api, on),
            settings=self.entity_description.is_setting,
        )
