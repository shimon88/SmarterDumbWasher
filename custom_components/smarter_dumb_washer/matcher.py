from .const import (
    CONFIDENCE_MIN,
    SAMPLE_SECONDS,
    STAGE_UNKNOWN,
)
from .profile import grid_trace, trim_idle

_BAND_RATIO = 0.1
_MIN_POINTS = 3
_INF = float("inf")


class LiveTrace:
    def __init__(self):
        self._origin = None
        self.samples = []

    def start(self, now, power):
        self._origin = now
        self.samples = []
        if power is not None:
            self.samples.append((0.0, power))

    def append(self, now, power):
        if self._origin is None or power is None:
            return False
        moment = now - self._origin
        if self.samples and self.samples[-1][0] == moment:
            if self.samples[-1][1] == power:
                return False
            self.samples[-1] = (moment, power)
            return True
        self.samples.append((moment, power))
        return True

    def clear(self):
        self._origin = None
        self.samples = []


def match_trace(samples, programs, idle_threshold):
    samples = trim_idle(samples, idle_threshold)
    if len(samples) < 2 or samples[-1][0] < SAMPLE_SECONDS:
        return None
    query, live_duration = grid_trace(samples)
    if len(query) < _MIN_POINTS:
        return None
    best = None
    for program in programs:
        reference = program.get("samples") or []
        if len(reference) < 2:
            continue
        scored = _score(query, live_duration, program)
        if scored is None:
            continue
        if best is None or scored["confidence"] > best["confidence"]:
            best = scored
    if best is None or best["confidence"] < CONFIDENCE_MIN:
        return None
    return best


def _score(query, live_duration, program):
    reference = program["samples"]
    end_index, mae = _open_end(query, reference)
    if end_index is None:
        return None
    peak = max(reference)
    if peak <= 0:
        return None
    confidence = max(0.0, 1 - mae / peak)
    duration = float(program["duration"])
    if end_index >= len(reference) - 1 or duration <= 0:
        aligned = duration
    else:
        aligned = min(duration, end_index * float(program["sample_seconds"]))
    progress = 0 if duration <= 0 else min(100, int(round(100 * aligned / duration)))
    if aligned > 0 and live_duration > 0 and aligned < duration:
        eta = int(round((duration - aligned) * live_duration / aligned))
    elif aligned >= duration:
        eta = 0
    else:
        eta = int(round(duration))
    return {
        "program": program["name"],
        "confidence": round(confidence, 3),
        "stage": _stage_at(program.get("stages") or [], aligned),
        "progress": progress,
        "eta": eta,
    }


def _stage_at(stages, aligned):
    for stage in stages:
        if stage["start"] <= aligned < stage["end"]:
            return stage["name"]
    if stages and aligned >= stages[-1]["end"]:
        return stages[-1]["name"]
    return STAGE_UNKNOWN


def _open_end(query, reference):
    row_count = len(query)
    col_count = len(reference)
    band = max(1, int(round(_BAND_RATIO * max(row_count, col_count))))
    cost = [[_INF] * col_count for _ in range(row_count)]
    prev = [[None] * col_count for _ in range(row_count)]
    cost[0][0] = abs(query[0] - reference[0])
    for i in range(row_count):
        j_lo = max(0, i - band)
        j_hi = min(col_count - 1, i + band)
        for j in range(j_lo, j_hi + 1):
            if i == 0 and j == 0:
                continue
            choice = _best_prev(cost, i, j)
            if choice is None:
                continue
            pi, pj = choice
            cost[i][j] = cost[pi][pj] + abs(query[i] - reference[j])
            prev[i][j] = choice
    best_index = None
    best_cost = _INF
    for j in range(col_count):
        if cost[-1][j] <= best_cost:
            best_cost = cost[-1][j]
            best_index = j
    if best_index is None or best_cost == _INF:
        return None, None
    length = 0
    i = row_count - 1
    j = best_index
    guard = row_count * col_count
    while guard > 0:
        length += 1
        parent = prev[i][j]
        if parent is None:
            break
        i, j = parent
        guard -= 1
    if length == 0:
        return None, None
    return best_index, best_cost / length


def _best_prev(cost, i, j):
    best = _INF
    choice = None
    if i > 0 and cost[i - 1][j] < best:
        best = cost[i - 1][j]
        choice = (i - 1, j)
    if j > 0 and cost[i][j - 1] < best:
        best = cost[i][j - 1]
        choice = (i, j - 1)
    if i > 0 and j > 0 and cost[i - 1][j - 1] < best:
        choice = (i - 1, j - 1)
    return choice
