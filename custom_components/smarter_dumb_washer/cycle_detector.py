from .const import (
    ON_POWER,
    RUN_AVERAGE,
    RUN_WINDOW,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_MACHINE_ON,
    STATE_RUNNING,
)


class CycleDetector:
    def __init__(
        self,
        start_threshold,
        idle_threshold,
        end_delay,
        min_cycle,
        door_closed_start,
    ):
        self._confirm = max(float(start_threshold), RUN_AVERAGE)
        self._idle_threshold = float(idle_threshold)
        self._end_delay = float(end_delay)
        self._min_cycle = float(min_cycle)
        self._door_closed_start = bool(door_closed_start)
        self._state = STATE_IDLE
        self._run_started = None
        self._idle_since = None
        self._last_door_closed = None
        self._segments = []
        self._held = None
        self._mark = None
        self._arming = False
        self._candidate = False
        self._prelude = []

    @property
    def state(self):
        return self._state

    @property
    def end_check_at(self):
        if self._state != STATE_RUNNING or self._idle_since is None:
            return None
        return self._idle_since + self._end_delay

    @property
    def confirm_check_at(self):
        if self._state == STATE_RUNNING or not self._arming or self._held is None:
            return None
        if self._mark is None:
            return None
        span, energy = self._window()
        if span >= RUN_WINDOW - 1e-6:
            return None
        rest = RUN_WINDOW - span
        if (energy + rest * self._held) / RUN_WINDOW < self._confirm:
            return None
        return self._mark + rest

    def take_prelude(self):
        points = self._prelude
        self._prelude = []
        return points

    def update(self, power, door_closed, now):
        if self._state == STATE_RUNNING:
            self._update_running(power, now)
            if self._state == STATE_RUNNING:
                self._remember_door(False, door_closed)
                return self._state
            just_finished = True
        else:
            just_finished = False

        if (
            self._state == STATE_FINISHED
            and self._last_door_closed is True
            and door_closed is False
        ):
            self._clear_run()
            self._reset_window()
            self._state = STATE_IDLE

        self._remember_door(just_finished, door_closed)
        self._arm_window(power, door_closed, now)
        if self._confirmed():
            self._begin_run(now)
            self._update_running(power, now)
            return self._state
        if self._state != STATE_FINISHED:
            self._set_power_state(power)
        return self._state

    def _update_running(self, power, now):
        if power is None:
            return
        if power >= self._idle_threshold:
            self._idle_since = None
            return
        if self._idle_since is None:
            self._idle_since = now
            return
        if now + 0.1 < self._idle_since + self._end_delay:
            return
        active = self._idle_since - self._run_started
        self._clear_run()
        if active < self._min_cycle:
            self._state = STATE_IDLE
        else:
            self._state = STATE_FINISHED

    def _arm_window(self, power, door_closed, now):
        if power is None or not self._door_allows(door_closed):
            self._reset_window()
            return
        if (
            self._candidate
            and self._mark is not None
            and self._held is not None
            and now > self._mark
        ):
            self._segments.append((self._mark, now, self._held))
        self._held = power
        self._mark = now
        if not self._candidate:
            if power >= self._confirm:
                self._candidate = True
            self._arming = self._candidate
            return
        if self._failed_candidate():
            self._segments = []
            self._candidate = power >= self._confirm
        self._arming = self._candidate

    def _failed_candidate(self):
        span, energy = self._window()
        if span < RUN_WINDOW - 1e-6:
            return False
        if self._held is not None and self._held >= self._confirm:
            return False
        return energy / span < self._confirm

    def _confirmed(self):
        if not self._candidate:
            return False
        span, energy = self._window()
        if span < RUN_WINDOW - 1e-6:
            return False
        return energy / span >= self._confirm

    def _window(self):
        if not self._segments:
            return 0.0, 0.0
        cutoff = self._segments[-1][1] - RUN_WINDOW
        span = 0.0
        energy = 0.0
        for start, end, watts in self._segments:
            if end <= cutoff:
                continue
            duration = end - max(start, cutoff)
            span += duration
            energy += duration * watts
        return span, energy

    def _begin_run(self, now):
        self._state = STATE_RUNNING
        self._idle_since = None
        self._run_started = self._segments[0][0] if self._segments else now
        self._prelude = []
        for start, end, watts in self._segments:
            if not self._prelude or self._prelude[-1][0] != start:
                self._prelude.append((start, watts))
        end, watts = self._segments[-1][1], self._segments[-1][2]
        if self._prelude[-1][0] != end:
            self._prelude.append((end, watts))
        self._reset_window()

    def _set_power_state(self, power):
        if power is None:
            return
        if power >= ON_POWER:
            self._state = STATE_MACHINE_ON
            return
        self._state = STATE_IDLE
        self._reset_window()

    def _door_allows(self, door_closed):
        if not self._door_closed_start:
            return True
        return door_closed is True

    def _remember_door(self, just_finished, door_closed):
        if just_finished and door_closed is False:
            self._last_door_closed = True
        else:
            self._last_door_closed = door_closed

    def _clear_run(self):
        self._run_started = None
        self._idle_since = None

    def _reset_window(self):
        self._segments = []
        self._held = None
        self._mark = None
        self._arming = False
        self._candidate = False
