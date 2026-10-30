"""Diagnostic sensors."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AudioProConfigEntry, AudioProCoordinator
from .entity import AudioProEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: AudioProConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AudioProWifiSignal(entry.runtime_data)])


class AudioProWifiSignal(AudioProEntity, SensorEntity):
    _attr_translation_key = "wifi_signal"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: AudioProCoordinator) -> None:
        super().__init__(coordinator, "wifi_signal")

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.settings.rssi
