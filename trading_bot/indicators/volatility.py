"""
Volatility indicators: Bollinger %B and Keltner Channel position.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np

from indicators._utils import atr, ema, ohlcv, safe


@safe()
def bollinger_vote(candles: Iterable, period: int = 20, std_dev: float = 2.0) -> int:
    """
    Bollinger Bands %B.

    Middle = SMA(C, 20); Upper/Lower = Middle ± 2·StdDev(C, 20).
    %B = (C - Lower) / (Upper - Lower).
    Vote: +1 if 0.55 < %B < 0.95, -1 if 0.05 < %B < 0.45, 0 otherwise.
    """
    _, _, _, c, _ = ohlcv(candles)
    if len(c) < period:
        return 0
    window = c[-period:]
    mid = float(np.mean(window))
    sd = float(np.std(window, ddof=0))
    if sd == 0:
        return 0
    upper = mid + std_dev * sd
    lower = mid - std_dev * sd
    pb = (c[-1] - lower) / (upper - lower)
    if pb >= 0.95 or pb <= 0.05:
        return 0
    if 0.55 < pb < 0.95:
        return 1
    if 0.05 < pb < 0.45:
        return -1
    return 0


@safe()
def keltner_vote(
    candles: Iterable,
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0,
) -> int:
    """
    Keltner Channel Position.

    Middle = EMA(C, 20); Upper/Lower = Middle ± 2·ATR(10).
    Vote: +1 if Middle < C < Upper, -1 if Lower < C < Middle,
           0 if outside the channel (extreme).
    """
    _, h, l, c, _ = ohlcv(candles)
    if len(c) < max(ema_period, atr_period) + 1:
        return 0
    mid_arr = ema(c, ema_period)
    atr_arr = atr(h, l, c, atr_period)
    mid = mid_arr[-1]
    a = atr_arr[-1]
    if np.isnan(mid) or np.isnan(a) or a == 0:
        return 0
    upper = mid + multiplier * a
    lower = mid - multiplier * a
    px = c[-1]
    if px > upper or px < lower:
        return 0
    if mid < px < upper:
        return 1
    if lower < px < mid:
        return -1
    return 0
