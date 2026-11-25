import logging

from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.exceptions import ServiceValidationError
from homeassistant.core import callback
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DOOR_CLOSED_START,
    CONF_DOOR_SENSOR,
    CONF_END_DELAY,
    CONF_IDLE_THRESHOLD,
    CONF_MIN_CYCLE,
    CONF_POWER_SENSOR,
    CONF_START_THRESHOLD,
    LEARN_EMPTY,
    LEARN_STORED,
    LEARN_TOO_SHORT,
    PROGRAM_UNKNOWN,
    SAMPLE_SECONDS,
    STAGE_UNKNOWN,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_RUNNING,
)
from .alerts import AlertManager
from .config_flow import configured_data
from .cycle_detector import CycleDetector
from .learning import LearnSession
from .matcher import LiveTrace, match_trace
from .profile import build_program
from .storage import ProgramStore

_LOGGER = logging.getLogger(__name__)
_MISSING = (STATE_UNKNOWN, STATE_UNAVAILABLE)


class WasherCoordinator:
    def __init__(self, hass, entry):
        data = configured_data(entry)
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
        self._idle_threshold = data[CONF_IDLE_THRESHOLD]
        self.alerts = AlertManager(hass, entry, data)
        self.store = ProgramStore(hass, entry.entry_id)
        self.learner = LearnSession()
        self._trace = LiveTrace()
        self.learn_result = None
        self.learn_result_program = None
        self.draft_name = ""
        self.selected_program = None
        self._match = None
        self._matched_at = None
        self._listeners = set()
        self._unsub_state = None
        self._timer = None
        self._match_timer = None

    @property
    def state(self):
        return self.detector.state

    @property
    def program_names(self):
        return sorted(self.store.programs)

    @property
    def learning_program(self):
        return self.learner.program_name

    @property
    def learn_status(self):
        return self.learner.status

    @property
    def learn_samples(self):
        return self.learner.samples

    @property
    def program(self):
        if self._match is None:
            return PROGRAM_UNKNOWN
        return self._match["program"]

    @property
    def stage(self):
        if self._match is None:
            return STAGE_UNKNOWN
        return self._match["stage"]

    @property
    def progress(self):
        if self._match is None:
            return None
        return self._match["progress"]

    @property
    def eta(self):
        if self._match is None:
            return None
        return self._match["eta"]

    async def async_setup(self):
        await self.store.async_load()
        self._apply()
        self._unsub_state = async_track_state_change_event(
            self.hass, [self._power_id, self._door_id], self._on_state
        )

    def async_shutdown(self):
        if self._unsub_state is not None:
            self._unsub_state()
            self._unsub_state = None
        self._cancel_timer()
        self._cancel_match_timer()
        self.alerts.stop()

    def async_add_listener(self, listener):
        self._listeners.add(listener)

        def _remove():
            self._listeners.discard(listener)

        return _remove

    def learn_start(self, name):
        self.learner.start(name)
        self._notify()

    def learn_cancel(self):
        self.learner.cancel()
        self._notify()

    def set_draft_name(self, name):
        self.draft_name = str(name).strip()
        self._notify()

    def select_program(self, name):
        if name not in self.store.programs:
            raise ServiceValidationError(f"Unknown program {name}")
        self.selected_program = name
        self._notify()

    def press_learn_start(self):
        if not self.draft_name:
            raise ServiceValidationError("Program name is empty")
        self.learn_start(self.draft_name)

    async def press_delete_program(self):
        name = self.selected_program
        if not name:
            raise ServiceValidationError("Select a learned program first")
        if not await self.async_delete_program(name):
            raise ServiceValidationError(f"Unknown program {name}")
        self.selected_program = None
        self._notify()

    async def press_rename_program(self):
        name = self.selected_program
        if not name:
            raise ServiceValidationError("Select a learned program first")
        if not self.draft_name:
            raise ServiceValidationError("Program name is empty")
        result = await self.async_rename_program(name, self.draft_name)
        if result == "missing":
            raise ServiceValidationError(f"Unknown program {name}")
        if result == "exists":
            raise ServiceValidationError(f"Program {self.draft_name} already exists")
        self.selected_program = self.draft_name
        self._notify()

    async def async_delete_program(self, name):
        deleted = await self.store.async_delete(name)
        if deleted:
            self._rematch()
            self._notify()
        return deleted

    async def async_rename_program(self, name, new_name):
        if name not in self.store.programs:
            return "missing"
        if new_name != name and new_name in self.store.programs:
            return "exists"
        if new_name != name:
            await self.store.async_rename(name, new_name)
            self._rematch()
            self._notify()
        return "ok"

    @callback
    def _on_state(self, _event):
        self._apply()

    @callback
    def _on_timer(self, _now):
        self._timer = None
        self._apply()

    def _apply(self):
        now = dt_util.utcnow().timestamp()
        previous = self.detector.state
        learning = (self.learner.status, self.learn_result, self.learn_result_program)
        power = _power(self.hass.states.get(self._power_id))
        self.detector.update(
            power,
            _door_closed(self.hass.states.get(self._door_id)),
            now,
        )
        prelude = self.detector.take_prelude()
        finished = self.learner.observe(
            previous, self.detector.state, power, now, prelude
        )
        match_before = self._match_key()
        self._follow_cycle(previous, power, now, prelude)
        self._schedule(now)
        if self.detector.state == STATE_FINISHED and previous != STATE_FINISHED:
            self.alerts.finished()
        elif previous == STATE_FINISHED and self.detector.state != STATE_FINISHED:
            self.alerts.stop()
        if finished is not None:
            kind, name, samples = finished
            if kind == LEARN_TOO_SHORT:
                self._remember_learn(LEARN_TOO_SHORT, name)
                _LOGGER.info(
                    "Ignored learn cycle for %s: shorter than the minimum cycle",
                    name,
                )
            else:
                self.entry.async_create_task(
                    self.hass, self._async_store_program(name, samples)
                )
        if (
            self.detector.state != previous
            or (self.learner.status, self.learn_result, self.learn_result_program)
            != learning
            or self._match_key() != match_before
        ):
            self._notify()

    async def _async_store_program(self, name, samples):
        program = build_program(
            name,
            samples,
            self._idle_threshold,
            self.store.programs.get(name),
        )
        if program is None:
            self._remember_learn(LEARN_EMPTY, name)
            _LOGGER.info("Learn cycle for %s had no usable power trace", name)
            self._notify()
            return
        await self.store.async_put(program)
        self._remember_learn(LEARN_STORED, name)
        _LOGGER.info("Stored program %s from %s runs", name, program["runs"])
        self._rematch()
        self._notify()

    def _remember_learn(self, result, name):
        self.learn_result = result
        self.learn_result_program = name

    def _follow_cycle(self, previous, power, now, prelude=()):
        state = self.detector.state
        if state == STATE_RUNNING and previous != STATE_RUNNING:
            if prelude:
                self._trace.start(prelude[0][0], prelude[0][1])
                for moment, watts in prelude[1:]:
                    self._trace.append(moment, watts)
                if prelude[-1][0] != now and power is not None:
                    self._trace.append(now, power)
            else:
                self._trace.start(now, power)
            self._match = None
            self._matched_at = None
            return
        if state == STATE_RUNNING or (
            previous == STATE_RUNNING and state == STATE_FINISHED
        ):
            changed = self._trace.append(now, power)
            same_instant = (
                self._matched_at is not None and abs(now - self._matched_at) < 0.001
            )
            self._maybe_match(
                now, force=state == STATE_FINISHED or (changed and same_instant)
            )
            return
        if state == STATE_IDLE and previous != STATE_IDLE:
            self._trace.clear()
            self._match = None
            self._matched_at = None

    def _maybe_match(self, now, force=False):
        due = self._matched_at is None or now - self._matched_at >= SAMPLE_SECONDS
        if not force and not due:
            return
        self._matched_at = now
        self._match = self._score()

    def _rematch(self):
        if self.detector.state == STATE_IDLE or not self._trace.samples:
            return
        self._match = self._score()

    def _score(self):
        return match_trace(
            self._trace.samples,
            self.store.programs.values(),
            self._idle_threshold,
        )

    def _match_key(self):
        if self._match is None:
            return None
        return (
            self._match["program"],
            self._match["stage"],
            self._match["progress"],
            self._match["eta"],
        )

    def _notify(self):
        for listener in list(self._listeners):
            listener()

    def _schedule(self, now):
        self._cancel_timer()
        self._schedule_match(now)
        end_at = self.detector.end_check_at
        if end_at is None:
            end_at = self.detector.confirm_check_at
        if end_at is None:
            return
        delay = end_at - now
        if delay <= 0:
            delay = 1.0
        self._timer = async_call_later(self.hass, delay, self._on_timer)

    def _schedule_match(self, now):
        self._cancel_match_timer()
        if self.detector.state != STATE_RUNNING:
            return
        delay = SAMPLE_SECONDS
        if self._matched_at is not None:
            delay = SAMPLE_SECONDS - (now - self._matched_at)
            if delay < 1.0:
                delay = SAMPLE_SECONDS
        self._match_timer = async_call_later(self.hass, delay, self._on_match_timer)

    @callback
    def _on_match_timer(self, _now):
        self._match_timer = None
        self._apply()

    def _cancel_timer(self):
        if self._timer is None:
            return
        self._timer()
        self._timer = None

    def _cancel_match_timer(self):
        if self._match_timer is None:
            return
        self._match_timer()
        self._match_timer = None


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
