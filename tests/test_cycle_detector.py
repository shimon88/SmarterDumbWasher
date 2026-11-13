from custom_components.smarter_dumb_washer.const import (
    STATE_FINISHED,
    STATE_IDLE,
    STATE_RUNNING,
)
from custom_components.smarter_dumb_washer.cycle_detector import CycleDetector


def detector(**overrides):
    params = {
        "start_threshold": 10,
        "idle_threshold": 2,
        "end_delay": 180,
        "min_cycle": 600,
        "door_closed_start": True,
    }
    params.update(overrides)
    return CycleDetector(**params)


def test_power_and_closed_door_start_a_cycle():
    machine = detector()

    assert machine.update(50, True, 0) == STATE_RUNNING


def test_open_door_blocks_start_when_required():
    machine = detector()

    assert machine.update(50, False, 0) == STATE_IDLE


def test_open_door_can_start_when_not_required():
    machine = detector(door_closed_start=False)

    assert machine.update(50, False, 0) == STATE_RUNNING


def test_power_between_thresholds_does_not_start():
    machine = detector()

    assert machine.update(5, True, 0) == STATE_IDLE


def test_missing_power_does_not_start():
    machine = detector()

    assert machine.update(None, True, 0) == STATE_IDLE


def test_short_run_returns_to_idle():
    machine = detector()
    assert machine.update(50, True, 0) == STATE_RUNNING
    assert machine.update(1, True, 10) == STATE_RUNNING

    assert machine.update(1, True, 190) == STATE_IDLE


def test_long_run_finishes_and_door_open_returns_to_idle():
    machine = detector()
    assert machine.update(50, True, 0) == STATE_RUNNING
    assert machine.update(1, True, 700) == STATE_RUNNING
    assert machine.end_check_at == 880

    assert machine.update(1, True, 880) == STATE_FINISHED
    assert machine.update(0, False, 881) == STATE_IDLE


def test_power_dip_shorter_than_end_delay_stays_running():
    machine = detector()
    assert machine.update(50, True, 0) == STATE_RUNNING
    assert machine.update(1, True, 20) == STATE_RUNNING
    assert machine.end_check_at == 200

    assert machine.update(50, True, 30) == STATE_RUNNING
    assert machine.end_check_at is None


def test_door_open_during_run_does_not_stop_it():
    machine = detector()
    assert machine.update(50, True, 0) == STATE_RUNNING

    assert machine.update(50, False, 10) == STATE_RUNNING


def test_missing_power_does_not_end_a_run():
    machine = detector(min_cycle=0, end_delay=10)
    assert machine.update(50, True, 0) == STATE_RUNNING
    assert machine.update(1, True, 1) == STATE_RUNNING

    assert machine.update(None, True, 20) == STATE_RUNNING
    assert machine.end_check_at == 11
    assert machine.update(1, True, 21) == STATE_FINISHED


def test_second_cycle_can_start_from_finished():
    machine = detector(min_cycle=0, end_delay=10)
    assert machine.update(50, True, 0) == STATE_RUNNING
    assert machine.update(1, True, 1) == STATE_RUNNING
    assert machine.update(1, True, 11) == STATE_FINISHED

    assert machine.update(50, True, 12) == STATE_RUNNING


def test_finish_with_door_already_open_clears_on_next_sample():
    machine = detector(min_cycle=0, end_delay=10, door_closed_start=False)
    assert machine.update(50, False, 0) == STATE_RUNNING
    assert machine.update(1, False, 1) == STATE_RUNNING
    assert machine.update(1, False, 11) == STATE_FINISHED

    assert machine.update(1, False, 12) == STATE_IDLE
