"""Media player entity for Audio Pro speakers."""
from __future__ import annotations

from typing import Any

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseError,
    BrowseMedia,
    MediaClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    async_process_play_media_url,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AudioProError, clean, decode_hex
from .const import MODE_TO_SOURCE, SOURCES
from .coordinator import AudioProConfigEntry, AudioProCoordinator
from .entity import AudioProEntity

STATIONS_ID = "audiopro://stations"

STATE_MAP = {
    "play": MediaPlayerState.PLAYING,
    "pause": MediaPlayerState.PAUSED,
    "load": MediaPlayerState.BUFFERING,
    "stop": MediaPlayerState.IDLE,
    "none": MediaPlayerState.IDLE,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: AudioProConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([AudioProMediaPlayer(entry.runtime_data)])


class AudioProMediaPlayer(AudioProEntity, MediaPlayerEntity):
    _attr_name = None
    _attr_media_content_type = MediaType.MUSIC
    _attr_source_list = list(SOURCES.values())
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.BROWSE_MEDIA
    )

    def __init__(self, coordinator: AudioProCoordinator) -> None:
        super().__init__(coordinator, "media_player")
        self._eq: str | None = None
        if coordinator.eq_list:
            self._attr_sound_mode_list = coordinator.eq_list
            self._attr_supported_features |= MediaPlayerEntityFeature.SELECT_SOUND_MODE

    @property
    def _status(self) -> dict[str, Any]:
        return self.coordinator.data.status

    @property
    def _meta(self) -> dict[str, Any]:
        return self.coordinator.data.meta

    @property
    def state(self) -> MediaPlayerState:
        return STATE_MAP.get(self._status.get("status", ""), MediaPlayerState.ON)

    @property
    def volume_level(self) -> float | None:
        vol = self._status.get("vol")
        return int(vol) / 100 if vol not in (None, "") else None

    @property
    def is_volume_muted(self) -> bool:
        return self._status.get("mute") == "1"

    @property
    def source(self) -> str | None:
        key = MODE_TO_SOURCE.get(str(self._status.get("mode")))
        return SOURCES.get(key) if key else None

    @property
    def sound_mode(self) -> str | None:
        if self._eq:
            return self._eq
        try:
            return self.coordinator.eq_list[int(self._status.get("eq", ""))]
        except (ValueError, IndexError):
            return None

    @property
    def media_title(self) -> str | None:
        if self.stream_url:
            station = self.current_station
            return station["name"] if station else "Internet radio"
        return clean(self._meta.get("title")) or clean(decode_hex(self._status.get("Title"))) or None

    @property
    def media_artist(self) -> str | None:
        if self.stream_url:
            return None
        return clean(self._meta.get("artist")) or clean(decode_hex(self._status.get("Artist"))) or None

    @property
    def media_album_name(self) -> str | None:
        if self.stream_url:
            return None
        return clean(self._meta.get("album")) or clean(decode_hex(self._status.get("Album"))) or None

    @property
    def media_image_url(self) -> str | None:
        art = clean(self._meta.get("albumArtURI"))
        return art if art.startswith("http") else None

    @property
    def media_content_id(self) -> str | None:
        return self.stream_url

    @property
    def media_duration(self) -> int | None:
        total = int(self._status.get("totlen") or 0)
        return total // 1000 or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        meta = self._meta
        return {
            k: v
            for k, v in {
                "bit_rate": clean(meta.get("bitRate")),
                "sample_rate": clean(meta.get("sampleRate")),
                "bit_depth": clean(meta.get("bitDepth")),
            }.items()
            if v
        }

    async def _run(self, coro) -> None:
        try:
            await coro
        except AudioProError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_media_play(self) -> None:
        if self._status.get("status") == "pause":
            await self._run(self.coordinator.api.player_cmd("resume"))
        elif self.coordinator.last_url and self.source == SOURCES["wifi"]:
            await self._run(self.coordinator.api.play_url(self.coordinator.last_url))
        else:
            await self._run(self.coordinator.api.player_cmd("resume"))

    async def async_media_pause(self) -> None:
        await self._run(self.coordinator.api.player_cmd("pause"))

    async def async_media_stop(self) -> None:
        await self._run(self.coordinator.api.player_cmd("stop"))

    async def async_media_next_track(self) -> None:
        await self._run(self.coordinator.api.player_cmd("next"))

    async def async_media_previous_track(self) -> None:
        await self._run(self.coordinator.api.player_cmd("prev"))

    async def async_set_volume_level(self, volume: float) -> None:
        await self._run(self.coordinator.api.set_volume(round(volume * 100)))

    async def async_mute_volume(self, mute: bool) -> None:
        await self._run(self.coordinator.api.set_mute(mute))

    async def async_select_source(self, source: str) -> None:
        key = next((k for k, v in SOURCES.items() if v == source), None)
        if key is None:
            raise HomeAssistantError(f"Unknown source: {source}")
        await self._run(self.coordinator.api.switch_source(key))

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        await self._run(self.coordinator.api.load_eq(sound_mode))
        self._eq = sound_mode
        self.async_write_ha_state()

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        if media_source.is_media_source_id(media_id):
            item = await media_source.async_resolve_media(self.hass, media_id, self.entity_id)
            media_id = item.url
        url = async_process_play_media_url(self.hass, media_id)
        self.coordinator.last_url = url
        await self._run(self.coordinator.api.play_url(url))

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia:
        if media_content_id and media_source.is_media_source_id(media_content_id):
            return await media_source.async_browse_media(
                self.hass, media_content_id, content_filter=_audio_only
            )
        if media_content_id == STATIONS_ID:
            return self._browse_stations()
        if media_content_id not in (None, ""):
            raise BrowseError(f"Unknown media: {media_content_id}")

        children = [self._browse_stations(with_children=False)]
        try:
            sources = await media_source.async_browse_media(
                self.hass, None, content_filter=_audio_only
            )
        except BrowseError:
            sources = None
        if sources is not None:
            if sources.domain is None and sources.children:
                children.extend(sources.children)
            else:
                children.append(sources)
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id="",
            media_content_type="",
            title=self.coordinator.device_info.get("DeviceName", "Audio Pro"),
            can_play=False,
            can_expand=True,
            children=children,
        )

    @callback
    def _browse_stations(self, with_children: bool = True) -> BrowseMedia:
        children = [
            BrowseMedia(
                media_class=MediaClass.CHANNEL,
                media_content_id=s["url"],
                media_content_type=MediaType.MUSIC,
                title=s["name"],
                can_play=True,
                can_expand=False,
            )
            for s in self.coordinator.stations
        ] if with_children else None
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=STATIONS_ID,
            media_content_type=MediaType.MUSIC,
            title="Radio stations",
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.CHANNEL,
        )


def _audio_only(item: BrowseMedia) -> bool:
    return item.media_content_type.startswith("audio/")
