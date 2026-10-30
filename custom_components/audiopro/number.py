"""Number entities: balance and sleep timer."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AudioProApi
from .coordinator import AudioProConfigEntry, AudioProCoordinator, AudioProData
from .entity import AudioProEntity


@dataclass(frozen=True, kw_only=True)
class AudioProNumberDescription(NumberEntityDescription):
    value_fn: Callable[[AudioProData], float | None]
    set_fn: Callable[[AudioProApi, float], Awaitable[None]]
    is_setting: bool = True


def _sleep_minutes(data: AudioProData) -> float | None:
    secs = data.settings.sleep_timer
    return None if secs is None else round(secs / 60)


NUMBERS = (
    AudioProNumberDescription(
        key="balance",
        translation_key="balance",
        icon="mdi:speaker-multiple",
        native_min_value=-1,
        native_max_value=1,
        native_step=0.1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda d: d.settings.balance,
        set_fn=lambda api, v: api.set_balance(v),
    ),
    AudioProNumberDescription(
        key="sleep_timer",
        translation_key="sleep_timer",
        icon="mdi:timer-sand",
        native_min_value=0,
        native_max_value=240,
        native_step=5,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        value_fn=_sleep_minutes,
        set_fn=lambda api, v: api.set_sleep_timer(int(v * 60)),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: AudioProConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(AudioProNumber(entry.runtime_data, d) for d in NUMBERS)


class AudioProNumber(AudioProEntity, NumberEntity):
    entity_description: AudioProNumberDescription

    def __init__(self, coordinator: AudioProCoordinator, description: AudioProNumberDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        await self.async_run(
            self.entity_description.set_fn(self.coordinator.api, value),
            settings=self.entity_description.is_setting,
        )
