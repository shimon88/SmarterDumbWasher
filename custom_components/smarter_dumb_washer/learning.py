from .const import STATE_FINISHED, STATE_IDLE, STATE_RUNNING


class LearnSession:
    def __init__(self):
        self.program_name = None
        self._recording = False
        self._origin = None
        self._samples = []

    def start(self, name):
        self.program_name = name
        self._stop_recording()

    def cancel(self):
        self.program_name = None
        self._stop_recording()

    def observe(self, previous, state, power, now):
        if self.program_name is None:
            return None
        if state == STATE_RUNNING and previous != STATE_RUNNING:
            self._recording = True
            self._origin = now
            self._samples = []
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
            return name, samples
        if state == STATE_IDLE:
            self._stop_recording()
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
