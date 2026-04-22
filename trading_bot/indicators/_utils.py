"""
Internal helpers shared by indicator modules.

Extracts OHLCV arrays from a deque of Candle dataclasses and provides a
`safe` decorator that catches errors and returns a neutral 0 vote.
"""
from __future__ import annotations

import functools
import logging
from typing import Callable, Iterable, List, Tuple, TypeVar

import numpy as np

log = logging.getLogger(__name__)

T = TypeVar("T")


def safe(default: int = 0) -> Callable[[Callable[..., int]], Callable[..., int]]:
    """Return a decorator that swallows exceptions and returns a default vote."""

    def outer(fn: Callable[..., int]) -> Callable[..., int]:
        @functools.wraps(fn)
        def inner(*args, **kwargs) -> int:
            try:
                v = fn(*args, **kwargs)
                if v not in (-2, -1, 0, 1, 2):
                    return default
                return v
            except Exception as exc:  # noqa: BLE001
                log.debug("Indicator %s failed: %s", fn.__name__, exc)
                return default

        return inner

    return outer


def ohlcv(candles: Iterable) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract (O, H, L, C, V) numpy arrays from a sequence of Candle objects."""
    cs = list(candles)
    n = len(cs)
    o = np.empty(n, dtype=np.float64)
    h = np.empty(n, dtype=np.float64)
    l = np.empty(n, dtype=np.float64)
    c = np.empty(n, dtype=np.float64)
    v = np.empty(n, dtype=np.float64)
    for i, cd in enumerate(cs):
        o[i], h[i], l[i], c[i], v[i] = cd.open, cd.high, cd.low, cd.close, cd.volume
    return o, h, l, c, v


def wilder_smooth(values: np.ndarray, period: int) -> np.ndarray:
    """
    Wilder's smoothing (used by RSI, ATR, ADX).

    First value = simple mean of the first `period` entries; subsequent
    values = (prev × (period-1) + current) / period.
    Returns an array the same length as `values`; entries before
    `period` indices are NaN.
    """
    n = len(values)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return out
    first = float(np.mean(values[:period]))
    out[period - 1] = first
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + values[i]) / period
    return out


def true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Classic TR = max(H-L, |H-prev_C|, |L-prev_C|). TR[0] = H[0]-L[0]."""
    n = len(c)
    tr = np.empty(n, dtype=np.float64)
    if n == 0:
        return tr
    tr[0] = h[0] - l[0]
    for i in range(1, n):
        tr[i] = max(
            h[i] - l[i],
            abs(h[i] - c[i - 1]),
            abs(l[i] - c[i - 1]),
        )
    return tr


def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, period: int) -> np.ndarray:
    """Wilder-smoothed ATR over `period`."""
    return wilder_smooth(true_range(h, l, c), period)


def sma(values: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average; leading entries NaN."""
    n = len(values)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return out
    csum = np.cumsum(values)
    out[period - 1] = csum[period - 1] / period
    for i in range(period, n):
        out[i] = (csum[i] - csum[i - period]) / period
    return out


def ema(values: np.ndarray, period: int) -> np.ndarray:
    """Exponential moving average with alpha=2/(period+1)."""
    n = len(values)
    out = np.full(n, np.nan, dtype=np.float64)
    if n < period:
        return out
    alpha = 2.0 / (period + 1.0)
    out[period - 1] = float(np.mean(values[:period]))
    for i in range(period, n):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]
    return out


def last_valid(arr: np.ndarray) -> float:
    """Return the most recent non-NaN value, or raise if all NaN."""
    mask = ~np.isnan(arr)
    if not mask.any():
        raise ValueError("no valid values")
    return float(arr[mask][-1])
