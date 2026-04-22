"""Volume spike detector — 15th indicator (counts as 1 vote)."""
from __future__ import annotations

from typing import Iterable

import numpy as np

from indicators._utils import ohlcv, safe


@safe()
def volume_spike_vote(candles: Iterable, lookback: int = 20, mult: float = 1.5) -> int:
    """
    Detect volume spikes on the latest completed candle.

    Spike = current volume > `mult` × rolling mean of prior `lookback` bars.
    Vote: +1 if spike and close > open, -1 if spike and close < open, 0 else.
    """
    o, _, _, c, v = ohlcv(candles)
    n = len(v)
    if n < lookback + 1:
        return 0
    avg = float(np.mean(v[-lookback - 1 : -1]))
    if avg <= 0:
        return 0
    if v[-1] <= avg * mult:
        return 0
    if c[-1] > o[-1]:
        return 1
    if c[-1] < o[-1]:
        return -1
    return 0
