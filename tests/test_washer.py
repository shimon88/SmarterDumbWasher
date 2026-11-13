from custom_components.smarter_dumb_washer.const import (
    STATE_FINISHED,
    STATE_IDLE,
    STATE_RUNNING,
)

from .traces import COTTON, NOISY, NORMAL, PAUSE, QUICK, SHORT
from .washer import play, set_door, set_power, setup_washer, washer_state


async def test_short_cycle_is_ignored(hass, washer_clock):
    entry = await setup_washer(hass)

    await play(hass, washer_clock, SHORT)

    assert washer_state(hass, entry) == STATE_IDLE


async def test_normal_cycle_finishes_then_door_open_returns_idle(hass, washer_clock):
    entry = await setup_washer(hass)

    await play(hass, washer_clock, NORMAL)
    assert washer_state(hass, entry) == STATE_FINISHED

    set_door(hass, False)
    await hass.async_block_till_done()

    assert washer_state(hass, entry) == STATE_IDLE


async def test_pause_shorter_than_end_delay_stays_running(hass, washer_clock):
    entry = await setup_washer(hass)

    await play(hass, washer_clock, PAUSE[:4])
    assert washer_state(hass, entry) == STATE_RUNNING

    await play(hass, washer_clock, PAUSE[4:])
    assert washer_state(hass, entry) == STATE_FINISHED


async def test_noisy_power_stays_running_until_the_end(hass, washer_clock):
    entry = await setup_washer(hass)

    await play(hass, washer_clock, NOISY[:6])
    assert washer_state(hass, entry) == STATE_RUNNING

    await play(hass, washer_clock, NOISY[6:])
    assert washer_state(hass, entry) == STATE_FINISHED


async def test_cotton_and_quick_traces_finish(hass, washer_clock):
    cotton = await setup_washer(hass)
    await play(hass, washer_clock, COTTON)
    assert washer_state(hass, cotton) == STATE_FINISHED

    await hass.config_entries.async_remove(cotton.entry_id)
    await hass.async_block_till_done()

    washer_clock.origin = washer_clock.when
    quick = await setup_washer(hass)
    await play(hass, washer_clock, QUICK)
    assert washer_state(hass, quick) == STATE_FINISHED


async def test_open_door_blocks_start(hass, washer_clock):
    entry = await setup_washer(hass, power=0, door_closed=False)

    set_power(hass, 80)
    await hass.async_block_till_done()
    assert washer_state(hass, entry) == STATE_IDLE

    set_door(hass, True)
    await hass.async_block_till_done()
    assert washer_state(hass, entry) == STATE_RUNNING


async def test_unload_removes_state_sensor(hass, washer_clock):
    entry = await setup_washer(hass)
    assert washer_state(hass, entry) == STATE_IDLE

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert washer_state(hass, entry) == "unavailable"
