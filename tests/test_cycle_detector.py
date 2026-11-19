from custom_components.smarter_dumb_washer.const import (
    STATE_FINISHED,
    STATE_IDLE,
    STATE_MACHINE_ON,
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


def confirm(machine, power=50, door=True, at=0):
    assert machine.update(power, door, at) == STATE_MACHINE_ON
    assert machine.update(power, door, at + 20) == STATE_RUNNING


def test_power_and_closed_door_start_a_cycle():
    confirm(detector())


def test_open_door_blocks_start_when_required():
    machine = detector()

    assert machine.update(50, False, 0) == STATE_MACHINE_ON
    assert machine.update(50, False, 30) == STATE_MACHINE_ON


def test_open_door_can_start_when_not_required():
    confirm(detector(door_closed_start=False), door=False)


def test_power_between_thresholds_does_not_start():
    machine = detector()

    assert machine.update(5, True, 0) == STATE_MACHINE_ON
    assert machine.update(5, True, 30) == STATE_MACHINE_ON


def test_power_on_spike_stays_on():
    machine = detector()

    assert machine.update(1, True, 0) == STATE_IDLE
    assert machine.update(34, True, 10) == STATE_MACHINE_ON
    assert machine.update(53, True, 12) == STATE_MACHINE_ON
    assert machine.update(8, True, 14) == STATE_MACHINE_ON
    assert machine.update(8, True, 40) == STATE_MACHINE_ON

    for second in range(20):
        watts = 80 if second % 2 == 0 else 12
        machine.update(watts, True, 40 + second)
    assert machine.update(80, True, 61) == STATE_RUNNING


def test_missing_power_does_not_start():
    machine = detector()

    assert machine.update(None, True, 0) == STATE_IDLE


def test_short_run_returns_to_idle():
    machine = detector()
    confirm(machine)
    assert machine.update(1, True, 30) == STATE_RUNNING

    assert machine.update(1, True, 210) == STATE_IDLE


def test_long_run_finishes_and_door_open_returns_to_idle():
    machine = detector()
    confirm(machine)
    assert machine.update(1, True, 700) == STATE_RUNNING
    assert machine.end_check_at == 880

    assert machine.update(1, True, 880) == STATE_FINISHED
    assert machine.update(0, False, 881) == STATE_IDLE


def test_power_dip_shorter_than_end_delay_stays_running():
    machine = detector()
    confirm(machine)
    assert machine.update(1, True, 40) == STATE_RUNNING
    assert machine.end_check_at == 220

    assert machine.update(50, True, 50) == STATE_RUNNING
    assert machine.end_check_at is None


def test_door_open_during_run_does_not_stop_it():
    machine = detector()
    confirm(machine)

    assert machine.update(50, False, 30) == STATE_RUNNING


def test_missing_power_does_not_end_a_run():
    machine = detector(min_cycle=0, end_delay=10)
    confirm(machine)
    assert machine.update(1, True, 21) == STATE_RUNNING

    assert machine.update(None, True, 40) == STATE_RUNNING
    assert machine.end_check_at == 31
    assert machine.update(1, True, 31) == STATE_FINISHED


def test_second_cycle_can_start_from_finished():
    machine = detector(min_cycle=0, end_delay=10)
    confirm(machine)
    assert machine.update(1, True, 21) == STATE_RUNNING
    assert machine.update(1, True, 31) == STATE_FINISHED

    assert machine.update(50, True, 32) == STATE_FINISHED
    assert machine.update(50, True, 52) == STATE_RUNNING


def test_finish_with_door_already_open_clears_on_next_sample():
    machine = detector(min_cycle=0, end_delay=10, door_closed_start=False)
    confirm(machine, door=False)
    assert machine.update(1, False, 21) == STATE_RUNNING
    assert machine.update(1, False, 31) == STATE_FINISHED

    assert machine.update(1, False, 32) == STATE_IDLE
