import pytest
from homeassistant.exceptions import ServiceValidationError

from custom_components.smarter_dumb_washer.const import (
    ATTR_LEARNING,
    ATTR_NEW_NAME,
    ATTR_PROGRAM_NAME,
    ATTR_PROGRAMS,
    DOMAIN,
    SERVICE_DELETE_PROGRAM,
    SERVICE_LEARN_CANCEL,
    SERVICE_LEARN_START,
    SERVICE_RENAME_PROGRAM,
    STAGE_FILL,
    STAGE_HEAT,
    STAGE_SPIN,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_RUNNING,
)
from custom_components.smarter_dumb_washer.profile import build_program

from .traces import COTTON, NOISY, NORMAL, PAUSE, QUICK, SHORT
from .washer import (
    call_washer,
    play,
    set_door,
    set_power,
    setup_washer,
    washer_attrs,
    washer_state,
)


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
    assert hass.services.has_service(DOMAIN, SERVICE_LEARN_START)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert washer_state(hass, entry) == "unavailable"
    assert not hass.services.has_service(DOMAIN, SERVICE_LEARN_START)


def test_profile_segments_fill_heat_and_spin():
    samples = [(0, 30), (60, 500), (400, 40), (700, 600), (800, 600)]

    program = build_program("Cotton", samples, 2)

    names = [stage["name"] for stage in program["stages"]]
    assert names[0] == STAGE_FILL
    assert STAGE_HEAT in names
    assert names[-1] == STAGE_SPIN
    assert program["runs"] == 1
    assert program["duration"] == 800

    merged = build_program("Cotton", samples, 2, program)
    assert merged["runs"] == 2
    assert merged["stages"][-1]["name"] == STAGE_SPIN


async def test_learn_cycle_stores_program(hass, washer_clock):
    entry = await setup_washer(hass)
    await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: "Cotton"})
    assert washer_attrs(hass, entry)[ATTR_LEARNING] == "Cotton"

    await play(hass, washer_clock, COTTON)

    assert washer_state(hass, entry) == STATE_FINISHED
    attrs = washer_attrs(hass, entry)
    assert attrs[ATTR_PROGRAMS] == ["Cotton"]
    assert attrs[ATTR_LEARNING] is None
    program = entry.runtime_data.store.programs["Cotton"]
    names = [stage["name"] for stage in program["stages"]]
    assert names[0] == STAGE_FILL
    assert STAGE_HEAT in names
    assert names[-1] == STAGE_SPIN
    assert program["runs"] == 1


async def test_repeat_learn_merges_program(hass, washer_clock):
    entry = await setup_washer(hass)
    await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: "Cotton"})
    await play(hass, washer_clock, COTTON)

    washer_clock.origin = washer_clock.when
    await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: "Cotton"})
    await play(hass, washer_clock, COTTON)

    program = entry.runtime_data.store.programs["Cotton"]
    assert program["runs"] == 2
    assert program["stages"][-1]["name"] == STAGE_SPIN


async def test_cancel_and_short_cycle_do_not_store(hass, washer_clock):
    entry = await setup_washer(hass)
    await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: "Cotton"})
    await play(hass, washer_clock, COTTON[:4])
    await call_washer(hass, entry, SERVICE_LEARN_CANCEL)
    await play(hass, washer_clock, COTTON[4:])

    assert washer_attrs(hass, entry)[ATTR_PROGRAMS] == []
    assert entry.runtime_data.learning_program is None

    washer_clock.origin = washer_clock.when
    await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: "Quick"})
    await play(hass, washer_clock, SHORT)

    assert washer_state(hass, entry) == STATE_IDLE
    assert washer_attrs(hass, entry)[ATTR_LEARNING] == "Quick"
    assert washer_attrs(hass, entry)[ATTR_PROGRAMS] == []


async def test_rename_delete_and_reload_program(hass, washer_clock):
    entry = await setup_washer(hass)
    await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: "Cotton"})
    await play(hass, washer_clock, COTTON)

    await call_washer(
        hass,
        entry,
        SERVICE_RENAME_PROGRAM,
        **{ATTR_PROGRAM_NAME: "Cotton", ATTR_NEW_NAME: "Towels"},
    )
    assert washer_attrs(hass, entry)[ATTR_PROGRAMS] == ["Towels"]

    with pytest.raises(ServiceValidationError):
        await call_washer(
            hass, entry, SERVICE_DELETE_PROGRAM, **{ATTR_PROGRAM_NAME: "Missing"}
        )
    with pytest.raises(ServiceValidationError):
        await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: " "})

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert washer_attrs(hass, entry)[ATTR_PROGRAMS] == ["Towels"]
    await call_washer(
        hass, entry, SERVICE_DELETE_PROGRAM, **{ATTR_PROGRAM_NAME: "Towels"}
    )
    assert washer_attrs(hass, entry)[ATTR_PROGRAMS] == []
