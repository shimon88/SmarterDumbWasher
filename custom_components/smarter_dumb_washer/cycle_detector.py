from .const import STATE_FINISHED, STATE_IDLE, STATE_RUNNING


class CycleDetector:
    def __init__(
        self,
        start_threshold,
        idle_threshold,
        end_delay,
        min_cycle,
        door_closed_start,
    ):
        self._start_threshold = float(start_threshold)
        self._idle_threshold = float(idle_threshold)
        self._end_delay = float(end_delay)
        self._min_cycle = float(min_cycle)
        self._door_closed_start = bool(door_closed_start)
        self._state = STATE_IDLE
        self._run_started = None
        self._idle_since = None
        self._last_door_closed = None

    @property
    def state(self):
        return self._state

    @property
    def end_check_at(self):
        if self._state != STATE_RUNNING or self._idle_since is None:
            return None
        return self._idle_since + self._end_delay

    def update(self, power, door_closed, now):
        just_finished = False
        if self._state == STATE_RUNNING:
            self._update_running(power, now)
            just_finished = self._state == STATE_FINISHED
        elif (
            self._state == STATE_FINISHED
            and self._last_door_closed is True
            and door_closed is False
        ):
            self._clear_run()
            self._state = STATE_IDLE

        if just_finished and door_closed is False:
            self._last_door_closed = True
        else:
            self._last_door_closed = door_closed

        if self._state in (STATE_IDLE, STATE_FINISHED) and self._can_start(
            power, door_closed
        ):
            self._state = STATE_RUNNING
            self._run_started = now
            self._idle_since = None
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

    def _can_start(self, power, door_closed):
        if power is None or power < self._start_threshold:
            return False
        if not self._door_closed_start:
            return True
        return door_closed is True

    def _clear_run(self):
        self._run_started = None
        self._idle_since = None
