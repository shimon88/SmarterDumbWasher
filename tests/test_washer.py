import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError

from custom_components.smarter_dumb_washer.const import (
    ATTR_ETA,
    CONF_DOOR_CLOSED_START,
    CONF_END_DELAY,
    CONF_IDLE_THRESHOLD,
    CONF_MIN_CYCLE,
    CONF_START_THRESHOLD,
    ATTR_LEARNING,
    ATTR_NEW_NAME,
    ATTR_PROGRAM_NAME,
    ATTR_PROGRAMS,
    DOMAIN,
    PROGRAM_UNKNOWN,
    SERVICE_DELETE_PROGRAM,
    SERVICE_LEARN_CANCEL,
    SERVICE_LEARN_START,
    SERVICE_RENAME_PROGRAM,
    STAGE_FILL,
    STAGE_HEAT,
    STAGE_SPIN,
    STAGE_UNKNOWN,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_RUNNING,
)
from custom_components.smarter_dumb_washer.matcher import match_trace
from custom_components.smarter_dumb_washer.profile import build_program

from .traces import COTTON, NOISY, NORMAL, PAUSE, QUICK, SHORT
from .washer import (
    call_washer,
    play,
    set_door,
    set_power,
    setup_washer,
    washer_attrs,
    washer_sensor,
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


def _relative(trace):
    points = [(stamp, watts) for stamp, watts, _door in trace if not (stamp == 0 and watts == 0)]
    origin = points[0][0]
    return [(stamp - origin, watts) for stamp, watts in points]


def test_matcher_picks_the_closer_program():
    cotton = build_program("Cotton", _relative(COTTON), 2)
    quick = build_program("Quick", _relative(QUICK), 2)
    programs = [cotton, quick]

    assert match_trace(_relative(COTTON)[:1], programs, 2) is None

    cotton_hit = match_trace(_relative(COTTON), programs, 2)
    assert cotton_hit["program"] == "Cotton"
    assert cotton_hit["stage"] == STAGE_SPIN
    assert cotton_hit["progress"] == 100
    assert cotton_hit["eta"] == 0

    quick_hit = match_trace(_relative(QUICK), programs, 2)
    assert quick_hit["program"] == "Quick"
    assert quick_hit["stage"] == STAGE_SPIN
    assert quick_hit["progress"] == 100


async def test_replay_reports_program_stage_and_progress(hass, washer_clock):
    entry = await setup_washer(hass)
    await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: "Cotton"})
    await play(hass, washer_clock, COTTON)

    assert washer_sensor(hass, entry, "program").state == "Cotton"
    assert washer_sensor(hass, entry, "stage").state == STAGE_SPIN
    assert washer_sensor(hass, entry, "progress").state == "100"
    assert washer_sensor(hass, entry, "progress").attributes[ATTR_ETA] == 0

    set_door(hass, False)
    await hass.async_block_till_done()
    assert washer_sensor(hass, entry, "program").state == PROGRAM_UNKNOWN
    assert washer_sensor(hass, entry, "stage").state == STAGE_UNKNOWN
    assert washer_sensor(hass, entry, "progress").state == "unknown"

    washer_clock.origin = washer_clock.when
    set_door(hass, True)
    await call_washer(hass, entry, SERVICE_LEARN_START, **{ATTR_PROGRAM_NAME: "Quick"})
    await play(hass, washer_clock, QUICK)
    assert washer_sensor(hass, entry, "program").state == "Quick"

    set_door(hass, False)
    await hass.async_block_till_done()
    washer_clock.origin = washer_clock.when
    set_door(hass, True)
    await play(hass, washer_clock, QUICK[:4])

    assert washer_state(hass, entry) == STATE_RUNNING
    assert washer_sensor(hass, entry, "program").state == "Quick"
    progress = int(washer_sensor(hass, entry, "progress").state)
    assert 0 < progress < 100
    assert washer_sensor(hass, entry, "stage").state == STAGE_SPIN
    assert washer_sensor(hass, entry, "progress").attributes[ATTR_ETA] > 0

    await play(hass, washer_clock, QUICK[4:])
    assert int(washer_sensor(hass, entry, "progress").state) >= progress
    assert washer_sensor(hass, entry, "progress").state == "100"
    assert washer_sensor(hass, entry, "stage").state == STAGE_SPIN
    assert washer_sensor(hass, entry, "program").state == "Quick"


async def test_options_flow_reloads_shorter_cycle_limits(hass, washer_clock):
    entry = await setup_washer(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    rejected = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_START_THRESHOLD: 10,
            CONF_IDLE_THRESHOLD: 10,
            CONF_END_DELAY: 30,
            CONF_MIN_CYCLE: 60,
            CONF_DOOR_CLOSED_START: True,
        },
    )
    assert rejected["type"] == FlowResultType.FORM
    assert rejected["errors"]["base"] == "idle_not_below_start"

    saved = await hass.config_entries.options.async_configure(
        rejected["flow_id"],
        {
            CONF_START_THRESHOLD: 10,
            CONF_IDLE_THRESHOLD: 2,
            CONF_END_DELAY: 30,
            CONF_MIN_CYCLE: 60,
            CONF_DOOR_CLOSED_START: True,
        },
    )
    assert saved["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_END_DELAY] == 30
    assert entry.options[CONF_MIN_CYCLE] == 60

    await play(
        hass,
        washer_clock,
        [
            (0, 0, True),
            (1, 80, True),
            (80, 1, True),
            (120, 1, True),
        ],
    )
    assert washer_state(hass, entry) == STATE_FINISHED
