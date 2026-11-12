from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_DOOR_CLOSED_START,
    CONF_DOOR_SENSOR,
    CONF_END_DELAY,
    CONF_IDLE_THRESHOLD,
    CONF_MIN_CYCLE,
    CONF_POWER_SENSOR,
    CONF_START_THRESHOLD,
    DEFAULT_DOOR_CLOSED_START,
    DEFAULT_END_DELAY,
    DEFAULT_IDLE_THRESHOLD,
    DEFAULT_MIN_CYCLE,
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


def _required(key: str, default: Any, field: Any) -> tuple[vol.Required, Any]:
    marker = vol.Required(key) if default is None else vol.Required(key, default=default)
    return marker, field


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
        )
    )


class SmarterDumbWasherConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

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


def _validate(user_input: dict[str, Any]) -> dict[str, str]:
    if user_input[CONF_POWER_SENSOR] == user_input[CONF_DOOR_SENSOR]:
        return {"base": "same_entity"}
    if float(user_input[CONF_IDLE_THRESHOLD]) >= float(user_input[CONF_START_THRESHOLD]):
        return {"base": "idle_not_below_start"}
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


def _title(flow: ConfigFlow, power_entity_id: str) -> str:
    state = flow.hass.states.get(power_entity_id)
    if state is not None and state.name:
        return state.name
    return "Washer"
