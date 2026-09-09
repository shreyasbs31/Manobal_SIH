"""Array aliases used throughout the generator.

Every stage of the causal chain operates on whole daily series rather than on
scalars per day. That is not only a speed decision: expressing "sleep responds to
the trailing week of duty hours" as an array operation keeps the lag explicit and
makes it impossible to accidentally read tomorrow's workload.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]
BoolArray = npt.NDArray[np.bool_]
IntArray = npt.NDArray[np.int64]


def zeros(n: int) -> FloatArray:
    return np.zeros(n, dtype=np.float64)


def clip(values: FloatArray, lower: float, upper: float) -> FloatArray:
    return np.clip(values, lower, upper).astype(np.float64, copy=False)
