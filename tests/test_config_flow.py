from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.smarter_dumb_washer.config_flow import _validate
from custom_components.smarter_dumb_washer.const import (
    CONF_DOOR_CLOSED_START,
    CONF_DOOR_SENSOR,
    CONF_END_DELAY,
    CONF_IDLE_THRESHOLD,
    CONF_MIN_CYCLE,
    CONF_POWER_SENSOR,
    CONF_START_THRESHOLD,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .washer import DOOR, POWER, entry_data, set_door, set_power


async def submit(hass, **overrides):
    set_power(hass, 0)
    set_door(hass, True)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    data = entry_data(**overrides)
    return await hass.config_entries.flow.async_configure(result["flow_id"], data)


async def test_config_flow_creates_entry(hass):
    result = await submit(hass)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_POWER_SENSOR] == POWER
    assert result["data"][CONF_DOOR_SENSOR] == DOOR
    assert result["data"][CONF_START_THRESHOLD] == 10
    assert result["data"][CONF_IDLE_THRESHOLD] == 2
    assert result["data"][CONF_END_DELAY] == 180
    assert result["data"][CONF_MIN_CYCLE] == 600
    assert result["data"][CONF_DOOR_CLOSED_START] is True


def test_same_entity_is_rejected():
    data = entry_data()
    data[CONF_DOOR_SENSOR] = data[CONF_POWER_SENSOR]

    assert _validate(data) == {"base": "same_entity"}


async def test_idle_threshold_must_be_below_start(hass):
    result = await submit(
        hass,
        **{CONF_START_THRESHOLD: 10, CONF_IDLE_THRESHOLD: 10},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "idle_not_below_start"


async def test_duplicate_power_sensor_is_rejected(hass):
    MockConfigEntry(
        domain=DOMAIN, data=entry_data(), title="Washer", unique_id=POWER
    ).add_to_hass(hass)

    result = await submit(hass)

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
