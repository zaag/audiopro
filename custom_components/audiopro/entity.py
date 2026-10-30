"""Base entity for Audio Pro."""
from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import clean, decode_hex
from .const import DOMAIN, VENDOR_URL
from .coordinator import AudioProCoordinator


class AudioProEntity(CoordinatorEntity[AudioProCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AudioProCoordinator, key: str) -> None:
        super().__init__(coordinator)
        info = coordinator.device_info
        uid = coordinator.config_entry.unique_id
        self._attr_unique_id = f"{uid}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uid)},
            connections={(CONNECTION_NETWORK_MAC, info["MAC"].lower())} if info.get("MAC") else set(),
            name=info.get("DeviceName"),
            manufacturer="Audio Pro",
            model=info.get("project", "").replace("AudioPro_", "").replace("_", " ") or None,
            sw_version=info.get("firmware"),
            configuration_url=f"https://{coordinator.api.host}",
        )

    @property
    def stream_url(self) -> str | None:
        """URL of the stream started via play:<url>, or None for other sources."""
        status = self.coordinator.data.status
        if status.get("vendor") != VENDOR_URL:
            return None
        meta_title = clean(self.coordinator.data.meta.get("title"))
        return meta_title or decode_hex(status.get("Title")) or self.coordinator.last_url

    @property
    def current_station(self) -> dict[str, str] | None:
        url = self.stream_url
        return self.coordinator.station_for_url(url) or (
            self.coordinator.station_for_url(self.coordinator.last_url) if url else None
        )
