from .const import (
    LEARN_IDLE,
    LEARN_RECORDING,
    LEARN_TOO_SHORT,
    LEARN_WAITING,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_RUNNING,
)


class LearnSession:
    def __init__(self):
        self.program_name = None
        self._recording = False
        self._origin = None
        self._samples = []

    @property
    def status(self):
        if self.program_name is None:
            return LEARN_IDLE
        if self._recording:
            return LEARN_RECORDING
        return LEARN_WAITING

    @property
    def samples(self):
        return len(self._samples)

    def start(self, name):
        self.program_name = name
        self._stop_recording()

    def cancel(self):
        self.program_name = None
        self._stop_recording()

    def observe(self, previous, state, power, now, prelude=()):
        if self.program_name is None:
            return None
        if state == STATE_RUNNING and previous != STATE_RUNNING:
            self._recording = True
            self._origin = prelude[0][0] if prelude else now
            self._samples = []
            for moment, watts in prelude:
                self._append(moment - self._origin, watts)
        if self._recording and power is not None and (
            state == STATE_RUNNING or previous == STATE_RUNNING
        ):
            self._append(now - self._origin, power)
        if not self._recording or previous != STATE_RUNNING:
            return None
        if state == STATE_FINISHED:
            name = self.program_name
            samples = list(self._samples)
            self.cancel()
            return "finished", name, samples
        if state == STATE_IDLE:
            name = self.program_name
            self._stop_recording()
            return LEARN_TOO_SHORT, name, None
        return None

    def _append(self, moment, power):
        if self._samples and self._samples[-1][0] == moment:
            self._samples[-1] = (moment, power)
            return
        self._samples.append((moment, power))

    def _stop_recording(self):
        self._recording = False
        self._origin = None
        self._samples = []
