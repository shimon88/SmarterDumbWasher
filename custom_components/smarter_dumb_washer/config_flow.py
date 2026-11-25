from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_ANNOUNCE_MESSAGE,
    CONF_DOOR_CLOSED_START,
    CONF_DOOR_SENSOR,
    CONF_END_DELAY,
    CONF_IDLE_THRESHOLD,
    CONF_MEDIA_PLAYERS,
    CONF_MIN_CYCLE,
    CONF_NOTIFY_SERVICES,
    CONF_POWER_SENSOR,
    CONF_QUIET_ENABLED,
    CONF_QUIET_END,
    CONF_QUIET_START,
    CONF_REPEAT_MINUTES,
    CONF_START_THRESHOLD,
    CONF_TTS_ENTITY,
    DEFAULT_ANNOUNCE_MESSAGE,
    DEFAULT_DOOR_CLOSED_START,
    DEFAULT_END_DELAY,
    DEFAULT_IDLE_THRESHOLD,
    DEFAULT_MIN_CYCLE,
    DEFAULT_QUIET_ENABLED,
    DEFAULT_QUIET_END,
    DEFAULT_QUIET_START,
    DEFAULT_REPEAT_MINUTES,
    DEFAULT_START_THRESHOLD,
    DOMAIN,
)

_WATTS = selector.NumberSelectorConfig(
    min=0,
    max=10000,
    step=1,
    mode=selector.NumberSelectorMode.BOX,
    unit_of_measurement="W",
)
_SECONDS = selector.NumberSelectorConfig(
    min=0,
    max=86400,
    step=1,
    mode=selector.NumberSelectorMode.BOX,
    unit_of_measurement="s",
)
_MINUTES = selector.NumberSelectorConfig(
    min=0,
    max=1440,
    step=1,
    mode=selector.NumberSelectorMode.BOX,
    unit_of_measurement="min",
)


def _required(key: str, default: Any, field: Any) -> tuple[vol.Required, Any]:
    marker = vol.Required(key) if default is None else vol.Required(key, default=default)
    return marker, field


def configured_data(entry: ConfigEntry) -> dict[str, Any]:
    data = dict(entry.data)
    data.update(entry.options)
    return data


def _threshold_fields(current: dict[str, Any]) -> list[tuple[vol.Required, Any]]:
    return [
        _required(
            CONF_START_THRESHOLD,
            current.get(CONF_START_THRESHOLD, DEFAULT_START_THRESHOLD),
            selector.NumberSelector(_WATTS),
        ),
        _required(
            CONF_IDLE_THRESHOLD,
            current.get(CONF_IDLE_THRESHOLD, DEFAULT_IDLE_THRESHOLD),
            selector.NumberSelector(_WATTS),
        ),
        _required(
            CONF_END_DELAY,
            current.get(CONF_END_DELAY, DEFAULT_END_DELAY),
            selector.NumberSelector(_SECONDS),
        ),
        _required(
            CONF_MIN_CYCLE,
            current.get(CONF_MIN_CYCLE, DEFAULT_MIN_CYCLE),
            selector.NumberSelector(_SECONDS),
        ),
        _required(
            CONF_DOOR_CLOSED_START,
            current.get(CONF_DOOR_CLOSED_START, DEFAULT_DOOR_CLOSED_START),
            selector.BooleanSelector(),
        ),
    ]


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    current = defaults or {}
    return vol.Schema(
        dict(
            [
                _required(
                    CONF_POWER_SENSOR,
                    current.get(CONF_POWER_SENSOR),
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(
                            domain="sensor", device_class="power"
                        )
                    ),
                ),
                _required(
                    CONF_DOOR_SENSOR,
                    current.get(CONF_DOOR_SENSOR),
                    selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="binary_sensor")
                    ),
                ),
                *_threshold_fields(current),
            ]
        )
    )


def _alert_fields(current: dict[str, Any]) -> list[tuple[Any, Any]]:
    return [
        (
            vol.Optional(
                CONF_TTS_ENTITY,
                description={"suggested_value": current.get(CONF_TTS_ENTITY)},
            ),
            selector.EntitySelector(selector.EntitySelectorConfig(domain="tts")),
        ),
        (
            vol.Optional(
                CONF_MEDIA_PLAYERS,
                description={"suggested_value": current.get(CONF_MEDIA_PLAYERS)},
            ),
            selector.EntitySelector(
                selector.EntitySelectorConfig(domain="media_player", multiple=True)
            ),
        ),
        (
            vol.Optional(
                CONF_NOTIFY_SERVICES,
                description={"suggested_value": current.get(CONF_NOTIFY_SERVICES)},
            ),
            selector.TextSelector(selector.TextSelectorConfig(multiple=True)),
        ),
        _required(
            CONF_ANNOUNCE_MESSAGE,
            current.get(CONF_ANNOUNCE_MESSAGE, DEFAULT_ANNOUNCE_MESSAGE),
            selector.TextSelector(),
        ),
        _required(
            CONF_REPEAT_MINUTES,
            current.get(CONF_REPEAT_MINUTES, DEFAULT_REPEAT_MINUTES),
            selector.NumberSelector(_MINUTES),
        ),
        _required(
            CONF_QUIET_ENABLED,
            current.get(CONF_QUIET_ENABLED, DEFAULT_QUIET_ENABLED),
            selector.BooleanSelector(),
        ),
        _required(
            CONF_QUIET_START,
            current.get(CONF_QUIET_START, DEFAULT_QUIET_START),
            selector.TimeSelector(),
        ),
        _required(
            CONF_QUIET_END,
            current.get(CONF_QUIET_END, DEFAULT_QUIET_END),
            selector.TimeSelector(),
        ),
    ]


def _options_schema(current: dict[str, Any]) -> vol.Schema:
    return vol.Schema(dict([*_threshold_fields(current), *_alert_fields(current)]))


class SmarterDumbWasherConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "WasherOptionsFlow":
        return WasherOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = _validate(user_input)
            if not errors:
                await self.async_set_unique_id(user_input[CONF_POWER_SENSOR])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_title(self, user_input[CONF_POWER_SENSOR]),
                    data=_entry_data(user_input),
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )


class WasherOptionsFlow(OptionsFlowWithReload):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        current = configured_data(self.config_entry)
        if user_input is not None:
            errors = _validate_thresholds(user_input) or _validate_alerts(user_input)
            if not errors:
                return self.async_create_entry(title="", data=_option_data(user_input))

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(user_input or current),
            errors=errors,
        )


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    if user_input[CONF_POWER_SENSOR] == user_input[CONF_DOOR_SENSOR]:
        return {"base": "same_entity"}
    return _validate_thresholds(user_input)


def _validate_thresholds(user_input: dict[str, Any]) -> dict[str, str]:
    if float(user_input[CONF_IDLE_THRESHOLD]) >= float(user_input[CONF_START_THRESHOLD]):
        return {"base": "idle_not_below_start"}
    return {}


def _validate_alerts(user_input: dict[str, Any]) -> dict[str, str]:
    tts = user_input.get(CONF_TTS_ENTITY)
    players = user_input.get(CONF_MEDIA_PLAYERS) or []
    if bool(tts) != bool(players):
        return {"base": "tts_incomplete"}
    for service in user_input.get(CONF_NOTIFY_SERVICES) or []:
        name = str(service).strip()
        if not name.startswith("notify.") or len(name) <= len("notify."):
            return {"base": "invalid_notify_service"}
    if user_input.get(CONF_QUIET_ENABLED, DEFAULT_QUIET_ENABLED) and user_input.get(
        CONF_QUIET_START, DEFAULT_QUIET_START
    ) == user_input.get(CONF_QUIET_END, DEFAULT_QUIET_END):
        return {"base": "quiet_hours_empty"}
    return {}


def _entry_data(user_input: dict[str, Any]) -> dict[str, Any]:
    return {
        CONF_POWER_SENSOR: user_input[CONF_POWER_SENSOR],
        CONF_DOOR_SENSOR: user_input[CONF_DOOR_SENSOR],
        CONF_START_THRESHOLD: float(user_input[CONF_START_THRESHOLD]),
        CONF_IDLE_THRESHOLD: float(user_input[CONF_IDLE_THRESHOLD]),
        CONF_END_DELAY: int(user_input[CONF_END_DELAY]),
        CONF_MIN_CYCLE: int(user_input[CONF_MIN_CYCLE]),
        CONF_DOOR_CLOSED_START: bool(user_input[CONF_DOOR_CLOSED_START]),
    }


def _option_data(user_input: dict[str, Any]) -> dict[str, Any]:
    data: dict[str, Any] = {
        CONF_START_THRESHOLD: float(user_input[CONF_START_THRESHOLD]),
        CONF_IDLE_THRESHOLD: float(user_input[CONF_IDLE_THRESHOLD]),
        CONF_END_DELAY: int(user_input[CONF_END_DELAY]),
        CONF_MIN_CYCLE: int(user_input[CONF_MIN_CYCLE]),
        CONF_DOOR_CLOSED_START: bool(user_input[CONF_DOOR_CLOSED_START]),
    }
    if user_input.get(CONF_TTS_ENTITY):
        data[CONF_TTS_ENTITY] = user_input[CONF_TTS_ENTITY]
    players = list(user_input.get(CONF_MEDIA_PLAYERS) or [])
    if players:
        data[CONF_MEDIA_PLAYERS] = players
    services = [
        str(service).strip()
        for service in user_input.get(CONF_NOTIFY_SERVICES) or []
        if str(service).strip()
    ]
    if services:
        data[CONF_NOTIFY_SERVICES] = services
    message = str(user_input.get(CONF_ANNOUNCE_MESSAGE) or "").strip()
    data[CONF_ANNOUNCE_MESSAGE] = message or DEFAULT_ANNOUNCE_MESSAGE
    data[CONF_REPEAT_MINUTES] = int(
        user_input.get(CONF_REPEAT_MINUTES, DEFAULT_REPEAT_MINUTES)
    )
    data[CONF_QUIET_ENABLED] = bool(
        user_input.get(CONF_QUIET_ENABLED, DEFAULT_QUIET_ENABLED)
    )
    data[CONF_QUIET_START] = str(user_input.get(CONF_QUIET_START, DEFAULT_QUIET_START))
    data[CONF_QUIET_END] = str(user_input.get(CONF_QUIET_END, DEFAULT_QUIET_END))
    return data


def _title(flow: ConfigFlow, power_entity_id: str) -> str:
    state = flow.hass.states.get(power_entity_id)
    if state is not None and state.name:
        return state.name
    return "Washer"
