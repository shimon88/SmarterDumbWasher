from .const import (
    SAMPLE_SECONDS,
    STAGE_FILL,
    STAGE_HEAT,
    STAGE_RINSE,
    STAGE_SPIN,
    STAGE_WASH,
)

_SMOOTH_WINDOW = 3
_MIN_SEGMENT_SECONDS = 30.0
_LEVEL_JUMP = 0.25
_MIN_JUMP_WATTS = 15.0
_HIGH_FRACTION = 0.55
_LOW_FRACTION = 0.30
_BAND_RATIO = 0.1
_INF = float("inf")


def build_program(name, samples, idle_threshold, existing=None):
    trimmed = trim_idle(samples, idle_threshold)
    if len(trimmed) < 2 or trimmed[-1][0] <= 0:
        return None
    values, duration = grid_trace(trimmed)
    runs = 1
    stored = _stored_samples(existing)
    if stored is not None:
        values = align_average(stored, values)
        duration = (float(existing["duration"]) + duration) / 2
        runs = int(existing.get("runs", 1)) + 1
    return {
        "name": name,
        "samples": [round(value, 3) for value in values],
        "sample_seconds": round(duration / (len(values) - 1), 3),
        "duration": round(duration, 3),
        "stages": segment(values, duration),
        "runs": runs,
    }


def grid_trace(samples):
    values, duration = resample(samples, SAMPLE_SECONDS)
    return smooth(values, _SMOOTH_WINDOW), duration


def trim_idle(samples, idle_threshold):
    if not samples:
        return []
    end = len(samples)
    limit = float(idle_threshold)
    while end > 0 and samples[end - 1][1] < limit:
        end -= 1
    if end == 0:
        return []
    kept = list(samples[:end])
    if end < len(samples) and samples[end][0] > kept[-1][0]:
        kept.append((samples[end][0], kept[-1][1]))
    return kept


def resample(samples, grid):
    end = samples[-1][0]
    if end <= 0:
        return [samples[-1][1]], 0.0
    steps = max(1, int(round(end / grid)))
    values = [_hold(samples, index * end / steps) for index in range(steps + 1)]
    return values, end


def smooth(values, window):
    if window <= 1 or len(values) < 3:
        return list(values)
    half = window // 2
    smoothed = []
    for index in range(len(values)):
        lo = max(0, index - half)
        hi = min(len(values), index + half + 1)
        chunk = values[lo:hi]
        smoothed.append(sum(chunk) / len(chunk))
    return smoothed


def segment(values, duration):
    if not values or duration <= 0:
        return []
    if len(values) == 1:
        return [_stage(STAGE_WASH, 0.0, duration)]
    step = duration / (len(values) - 1)
    span = max(values) - min(values)
    threshold = max(_MIN_JUMP_WATTS, _LEVEL_JUMP * span)
    cuts = [0]
    for index in range(1, len(values)):
        if abs(values[index] - values[index - 1]) >= threshold:
            cuts.append(index)
    cuts.append(len(values))
    spans = [(cuts[index], cuts[index + 1]) for index in range(len(cuts) - 1)]
    spans = _merge_short(values, spans, step, _MIN_SEGMENT_SECONDS)
    spans = _merge_close(values, spans, threshold)
    if len(spans) <= 1:
        return [_stage(STAGE_WASH, 0.0, round(duration, 3))]
    return _label_stages(values, spans, step, duration)


def align_average(left, right):
    mixed = _dtw_average(left, right)
    target = max(1, round((len(left) + len(right)) / 2))
    return _resample_series(mixed, target)


def _stored_samples(existing):
    if not existing:
        return None
    samples = existing.get("samples")
    if not samples or existing.get("duration") in (None, 0):
        return None
    return samples


def _hold(samples, moment):
    chosen = samples[0][1]
    for stamp, watts in samples:
        if stamp > moment:
            break
        chosen = watts
    return chosen


def _mean(values, span):
    start, end = span
    chunk = values[start:end]
    return sum(chunk) / len(chunk)


def _merge_short(values, spans, step, min_seconds):
    spans = list(spans)
    while len(spans) > 1:
        short = None
        for index, (start, end) in enumerate(spans):
            if (end - start) * step < min_seconds:
                short = index
                break
        if short is None:
            break
        spans = _merge_index(values, spans, short)
    return spans


def _merge_close(values, spans, threshold):
    spans = list(spans)
    changed = True
    while changed and len(spans) > 1:
        changed = False
        for index in range(len(spans) - 1):
            gap = abs(_mean(values, spans[index]) - _mean(values, spans[index + 1]))
            if gap < threshold:
                merged = (spans[index][0], spans[index + 1][1])
                spans = spans[:index] + [merged] + spans[index + 2 :]
                changed = True
                break
    return spans


def _merge_index(values, spans, index):
    if index <= 0:
        target = 1
    elif index >= len(spans) - 1:
        target = index - 1
    else:
        mean = _mean(values, spans[index])
        left = abs(mean - _mean(values, spans[index - 1]))
        right = abs(mean - _mean(values, spans[index + 1]))
        target = index - 1 if left <= right else index + 1
    lo = min(index, target)
    hi = max(index, target)
    merged = (spans[lo][0], spans[hi][1])
    return spans[:lo] + [merged] + spans[hi + 1 :]


def _label_stages(values, spans, step, duration):
    means = [_mean(values, span) for span in spans]
    peak = max(means)
    high_at = _HIGH_FRACTION * peak
    low_at = _LOW_FRACTION * peak
    levels = [_level(mean, high_at, low_at) for mean in means]
    spin_index = _spin_index(levels, spans, step, duration)
    names = []
    seen_main = False
    for index, level in enumerate(levels):
        if index == spin_index:
            names.append(STAGE_SPIN)
            continue
        if level == "high":
            names.append(STAGE_HEAT)
            seen_main = True
            continue
        if not seen_main and not names and level == "low":
            names.append(STAGE_FILL)
            continue
        if not seen_main:
            names.append(STAGE_WASH)
            seen_main = True
            continue
        names.append(STAGE_RINSE)
    return _collapse_stages(names, spans, step, len(values), duration)


def _level(mean, high_at, low_at):
    if mean >= high_at:
        return "high"
    if mean <= low_at:
        return "low"
    return "mid"


def _spin_index(levels, spans, step, duration):
    last_high = None
    for index, level in enumerate(levels):
        if level == "high":
            last_high = index
    if last_high is None:
        return None
    start = spans[last_high][0] * step
    if last_high == len(spans) - 1 or start >= duration * 0.5:
        return last_high
    return None


def _collapse_stages(names, spans, step, count, duration):
    stages = []
    for name, (start, end) in zip(names, spans):
        end_at = _bound(end, step, count, duration)
        if stages and stages[-1]["name"] == name:
            stages[-1]["end"] = end_at
            continue
        stages.append(_stage(name, _bound(start, step, count, duration), end_at))
    if stages:
        stages[0]["start"] = 0.0
        stages[-1]["end"] = round(duration, 3)
    return stages


def _bound(index, step, count, duration):
    if index >= count - 1:
        return round(duration, 3)
    return round(index * step, 3)


def _stage(name, start, end):
    return {"name": name, "start": start, "end": end}


def _dtw_average(left, right):
    if not left:
        return list(right)
    if not right:
        return list(left)
    path = _dtw_path(left, right)
    if path is None:
        return _linear_average(left, right)
    return [(left[i] + right[j]) / 2 for i, j in path]


def _dtw_path(left, right):
    row_count = len(left)
    col_count = len(right)
    band = max(
        abs(row_count - col_count),
        int(round(_BAND_RATIO * max(row_count, col_count))),
        1,
    )
    cost = [[_INF] * col_count for _ in range(row_count)]
    prev = [[None] * col_count for _ in range(row_count)]
    cost[0][0] = abs(left[0] - right[0])
    for i in range(row_count):
        j_lo, j_hi = _window(i, row_count, col_count, band)
        for j in range(j_lo, j_hi + 1):
            if i == 0 and j == 0:
                continue
            choice = _best_prev(cost, i, j)
            if choice is None:
                continue
            pi, pj = choice
            cost[i][j] = cost[pi][pj] + abs(left[i] - right[j])
            prev[i][j] = choice
    if cost[-1][-1] == _INF:
        return None
    path = []
    i = row_count - 1
    j = col_count - 1
    guard = row_count * col_count
    while guard > 0:
        path.append((i, j))
        parent = prev[i][j]
        if parent is None:
            break
        i, j = parent
        guard -= 1
    if not path or path[-1] != (0, 0):
        return None
    path.reverse()
    return path


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


def _window(i, row_count, col_count, band):
    if row_count <= 1:
        return 0, col_count - 1
    center = i * (col_count - 1) / (row_count - 1)
    lo = max(0, int(center - band))
    hi = min(col_count - 1, int(center + band + 0.999999))
    return lo, hi


def _linear_average(left, right):
    count = max(len(left), len(right))
    left_fit = _resample_series(left, count)
    right_fit = _resample_series(right, count)
    return [(a + b) / 2 for a, b in zip(left_fit, right_fit)]


def _resample_series(values, count):
    if count <= 1:
        return [sum(values) / len(values)]
    if len(values) == count:
        return list(values)
    if len(values) == 1:
        return [values[0]] * count
    last = len(values) - 1
    span = count - 1
    fitted = []
    for index in range(count):
        pos = last * index / span
        lo = int(pos)
        hi = min(lo + 1, last)
        frac = pos - lo
        fitted.append(values[lo] * (1 - frac) + values[hi] * frac)
    return fitted
