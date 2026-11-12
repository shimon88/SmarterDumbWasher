import time

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers.event import async_call_later, async_track_state_change_event

from .const import (
    CONF_DOOR_CLOSED_START,
    CONF_DOOR_SENSOR,
    CONF_END_DELAY,
    CONF_IDLE_THRESHOLD,
    CONF_MIN_CYCLE,
    CONF_POWER_SENSOR,
    CONF_START_THRESHOLD,
)
from .cycle_detector import CycleDetector

_MISSING = (STATE_UNKNOWN, STATE_UNAVAILABLE)


class WasherCoordinator:
    def __init__(self, hass, entry):
        data = entry.data
        self.hass = hass
        self.entry = entry
        self.detector = CycleDetector(
            data[CONF_START_THRESHOLD],
            data[CONF_IDLE_THRESHOLD],
            data[CONF_END_DELAY],
            data[CONF_MIN_CYCLE],
            data[CONF_DOOR_CLOSED_START],
        )
        self._power_id = data[CONF_POWER_SENSOR]
        self._door_id = data[CONF_DOOR_SENSOR]
        self._listeners = set()
        self._unsub_state = None
        self._timer = None

    @property
    def state(self):
        return self.detector.state

    async def async_setup(self):
        self._apply()
        self._unsub_state = async_track_state_change_event(
            self.hass, [self._power_id, self._door_id], self._on_state
        )

    def async_shutdown(self):
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        self._cancel_timer()

    def async_add_listener(self, listener):
        self._listeners.add(listener)

        def _remove():
            self._listeners.discard(listener)

        return _remove

    def _on_state(self, _event):
        self._apply()

    def _on_timer(self, _now):
        self._timer = None
        self._apply()

    def _apply(self):
        now = time.monotonic()
        previous = self.detector.state
        self.detector.update(
            _power(self.hass.states.get(self._power_id)),
            _door_closed(self.hass.states.get(self._door_id)),
            now,
        )
        self._schedule(now)
        if self.detector.state == previous:
            return
        for listener in list(self._listeners):
            listener()

    def _schedule(self, now):
        self._cancel_timer()
        end_at = self.detector.end_check_at
        if end_at is None:
            return
        delay = end_at - now
        if delay <= 0:
            delay = 1.0
        self._timer = async_call_later(self.hass, delay, self._on_timer)

    def _cancel_timer(self):
        if self._timer is None:
            return
        self._timer()
        self._timer = None


def _power(state):
    if state is None or state.state in _MISSING:
        return None
    try:
        return float(state.state)
    except (TypeError, ValueError):
        return None


def _door_closed(state):
    if state is None or state.state in _MISSING:
        return None
    if state.state == STATE_OFF:
        return True
    if state.state == STATE_ON:
        return False
    return None
