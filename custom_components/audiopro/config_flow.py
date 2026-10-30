"""Config flow: add a speaker by IP address, edit its radio stations in the options."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .api import AudioProApi, AudioProError
from .const import (
    CONF_STATIONS,
    DEFAULT_STATIONS,
    DOMAIN,
    stations_to_text,
    text_to_stations,
)


class AudioProConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            api = AudioProApi(host, async_get_clientsession(self.hass, verify_ssl=False))
            try:
                info = await api.get_device_info()
            except AudioProError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(info.get("uuid") or info.get("MAC") or host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                return self.async_create_entry(
                    title=info.get("DeviceName", host),
                    data={CONF_HOST: host},
                    options={CONF_STATIONS: DEFAULT_STATIONS},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return AudioProOptionsFlow()


class AudioProOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders = {"line": ""}
        if user_input is not None:
            try:
                stations = text_to_stations(user_input[CONF_STATIONS])
            except ValueError as err:
                errors[CONF_STATIONS] = "invalid_station"
                placeholders["line"] = str(err)
            else:
                return self.async_create_entry(data={CONF_STATIONS: stations})

        current = self.config_entry.options.get(CONF_STATIONS, DEFAULT_STATIONS)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_STATIONS, default=stations_to_text(current)
                    ): TextSelector(TextSelectorConfig(multiline=True)),
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )
