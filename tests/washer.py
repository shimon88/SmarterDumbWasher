from datetime import UTC, datetime, timedelta

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.smarter_dumb_washer.const import (
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

POWER = "sensor.plug_power"
DOOR = "binary_sensor.washer_door"


class WasherClock:
    def __init__(self):
        self.when = datetime.now(UTC)
        self.origin = self.when

    def utcnow(self):
        return self.when


def entry_data(**overrides):
    data = {
        CONF_POWER_SENSOR: POWER,
        CONF_DOOR_SENSOR: DOOR,
        CONF_START_THRESHOLD: DEFAULT_START_THRESHOLD,
        CONF_IDLE_THRESHOLD: DEFAULT_IDLE_THRESHOLD,
        CONF_END_DELAY: DEFAULT_END_DELAY,
        CONF_MIN_CYCLE: DEFAULT_MIN_CYCLE,
        CONF_DOOR_CLOSED_START: DEFAULT_DOOR_CLOSED_START,
    }
    data.update(overrides)
    return data


def set_power(hass, watts):
    hass.states.async_set(
        POWER,
        str(watts),
        {"device_class": "power", "unit_of_measurement": "W"},
    )


def set_door(hass, closed):
    hass.states.async_set(
        DOOR,
        "off" if closed else "on",
        {"device_class": "door"},
    )


async def setup_washer(hass, power=0, door_closed=True, **overrides):
    set_power(hass, power)
    set_door(hass, door_closed)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=entry_data(**overrides),
        title="Washer",
        unique_id=POWER,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def play(hass, clock, samples):
    for offset, watts, door_closed in samples:
        clock.when = clock.origin + timedelta(seconds=offset)
        async_fire_time_changed(hass, clock.when)
        await hass.async_block_till_done()
        set_power(hass, watts)
        set_door(hass, door_closed)
        await hass.async_block_till_done()


def washer_state(hass, entry):
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}-state"
    )
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state
