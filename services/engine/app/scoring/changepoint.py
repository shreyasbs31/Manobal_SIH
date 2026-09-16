from __future__ import annotations

import numpy as np


def pelt_rbf(series: list[float], *, min_size: int = 5) -> list[int]:
    values = np.asarray(series, dtype=np.float64)
    if values.size < min_size * 2:
        return []
    try:
        import ruptures as rpt
    except ImportError:
        return _pelt_fallback(values, min_size=min_size)
    algo = rpt.Pelt(model="rbf", min_size=min_size).fit(values)
    breaks = algo.predict(pen=1.2)
    return [int(index) for index in breaks[:-1]]


def onset_from_change_points(
    wsi: list[float],
    as_of_index: int,
    elevated: float = 0.35,
) -> int | None:
    if not wsi or wsi[as_of_index] <= elevated:
        return None
    window = wsi[max(0, as_of_index - 119) : as_of_index + 1]
    offset = max(0, as_of_index - 119)
    breaks = pelt_rbf(window)
    start = as_of_index
    while start > 0 and wsi[start - 1] > elevated:
        start -= 1
    if not breaks:
        return start
    in_episode = [offset + point for point in breaks if offset + point >= start]
    return min(in_episode) if in_episode else start


def _pelt_fallback(values: np.ndarray, min_size: int) -> list[int]:
    n = values.size
    cost = np.zeros(n + 1)
    prev = np.zeros(n + 1, dtype=np.int32)
    for end in range(min_size, n + 1):
        best = np.inf
        best_i = 0
        for start in range(0, end - min_size + 1):
            segment = values[start:end]
            local = float(np.var(segment) * (end - start))
            candidate = cost[start] + local + 1.2
            if candidate < best:
                best = candidate
                best_i = start
        cost[end] = best
        prev[end] = best_i
    breaks: list[int] = []
    idx = n
    while idx > 0:
        nxt = int(prev[idx])
        if nxt <= 0:
            break
        breaks.append(nxt)
        idx = nxt
    return list(reversed(breaks))
