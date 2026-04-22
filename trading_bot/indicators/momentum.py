"""
Momentum indicators: RSI(7), Williams %R(14), Stochastic(5,3,3), CCI(14), MFI(7).

All functions take a sequence of Candle dataclasses and return a discrete
vote: +1 bullish, -1 bearish, 0 neutral / insufficient data.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np

from indicators._utils import ohlcv, safe, wilder_smooth


@safe()
def rsi_vote(candles: Iterable, period: int = 7) -> int:
    """
    Wilder's RSI over `period` 1-min candles.

    RSI = 100 - 100 / (1 + avg_gain/avg_loss), with Wilder smoothing.
    Vote: +1 if RSI > 55, -1 if RSI < 45, 0 otherwise.
    Also returns 0 if RSI > 75 or < 25 (exhaustion zone).
    """
    _, _, _, c, _ = ohlcv(candles)
    if len(c) < period + 1:
        return 0
    diffs = np.diff(c)
    gains = np.where(diffs > 0, diffs, 0.0)
    losses = np.where(diffs < 0, -diffs, 0.0)

    avg_g = wilder_smooth(gains, period)
    avg_l = wilder_smooth(losses, period)

    g = avg_g[-1]
    l = avg_l[-1]
    if np.isnan(g) or np.isnan(l):
        return 0
    if l == 0:
        rsi = 100.0
    else:
        rs = g / l
        rsi = 100.0 - (100.0 / (1.0 + rs))

    if rsi > 75 or rsi < 25:
        return 0
    if rsi > 55:
        return 1
    if rsi < 45:
        return -1
    return 0


@safe()
def williams_r_vote(candles: Iterable, period: int = 14) -> int:
    """
    Williams %R = ((HH - Close) / (HH - LL)) × -100 over `period`.

    Vote: +1 if -40 < %R ≤ 0 (bullish), -1 if -100 ≤ %R < -60, 0 otherwise.
    """
    _, h, l, c, _ = ohlcv(candles)
    if len(c) < period:
        return 0
    hh = float(np.max(h[-period:]))
    ll = float(np.min(l[-period:]))
    if hh == ll:
        return 0
    wr = ((hh - c[-1]) / (hh - ll)) * -100.0
    if -40.0 < wr <= 0.0:
        return 1
    if -100.0 <= wr < -60.0:
        return -1
    return 0


@safe()
def stochastic_vote(
    candles: Iterable, k_period: int = 5, d_period: int = 3, smooth: int = 3
) -> int:
    """
    Stochastic Slow %K and %D.

    Raw %K = 100 × (C - LL(k)) / (HH(k) - LL(k))
    Slow %K = SMA(Raw %K, smooth); %D = SMA(Slow %K, d_period).
    Vote: +1 if Slow%K > %D and Slow%K < 80 (bullish cross).
          -1 if Slow%K < %D and Slow%K > 20 (bearish cross).
           0 otherwise.
    """
    _, h, l, c, _ = ohlcv(candles)
    n = len(c)
    need = k_period + smooth + d_period
    if n < need:
        return 0

    raw_k = np.full(n, np.nan, dtype=np.float64)
    for i in range(k_period - 1, n):
        hh = float(np.max(h[i - k_period + 1 : i + 1]))
        ll = float(np.min(l[i - k_period + 1 : i + 1]))
        raw_k[i] = 50.0 if hh == ll else 100.0 * (c[i] - ll) / (hh - ll)

    slow_k = _rolling_mean(raw_k, smooth)
    d = _rolling_mean(slow_k, d_period)

    sk = slow_k[-1]
    dd = d[-1]
    if np.isnan(sk) or np.isnan(dd):
        return 0
    if sk > dd and sk < 80.0:
        return 1
    if sk < dd and sk > 20.0:
        return -1
    return 0


@safe()
def cci_vote(candles: Iterable, period: int = 14) -> int:
    """
    CCI = (TP - SMA(TP)) / (0.015 × Mean Deviation).

    TP = (H+L+C)/3. Vote: +1 if CCI > 100, -1 if CCI < -100, 0 otherwise.
    """
    _, h, l, c, _ = ohlcv(candles)
    if len(c) < period:
        return 0
    tp = (h + l + c) / 3.0
    window = tp[-period:]
    sma_tp = float(np.mean(window))
    mean_dev = float(np.mean(np.abs(window - sma_tp)))
    if mean_dev == 0:
        return 0
    cci = (tp[-1] - sma_tp) / (0.015 * mean_dev)
    if cci > 100:
        return 1
    if cci < -100:
        return -1
    return 0


@safe()
def mfi_vote(candles: Iterable, period: int = 7) -> int:
    """
    Money Flow Index (price + volume).

    Raw MF = TP × V; positive MF on TP>prev_TP days, negative otherwise.
    MFI = 100 - 100/(1 + posMF/negMF) over `period`.
    Vote: +1 if 45 < MFI < 80, -1 if 20 < MFI < 55, 0 at extremes or mid-neutral.
    """
    _, h, l, c, v = ohlcv(candles)
    if len(c) < period + 1:
        return 0
    tp = (h + l + c) / 3.0
    raw_mf = tp * v
    pos_mf = 0.0
    neg_mf = 0.0
    for i in range(len(tp) - period, len(tp)):
        if i == 0:
            continue
        if tp[i] > tp[i - 1]:
            pos_mf += raw_mf[i]
        elif tp[i] < tp[i - 1]:
            neg_mf += raw_mf[i]
    if neg_mf == 0 and pos_mf == 0:
        return 0
    if neg_mf == 0:
        mfi = 100.0
    else:
        mfi = 100.0 - (100.0 / (1.0 + pos_mf / neg_mf))

    if mfi >= 80 or mfi <= 20:
        return 0
    if 45 < mfi < 80:
        return 1
    if 20 < mfi < 55:
        return -1
    return 0


def _rolling_mean(a: np.ndarray, w: int) -> np.ndarray:
    """NaN-tolerant rolling mean over window `w`."""
    n = len(a)
    out = np.full(n, np.nan, dtype=np.float64)
    if w <= 0 or n < w:
        return out
    for i in range(w - 1, n):
        window = a[i - w + 1 : i + 1]
        if np.isnan(window).any():
            continue
        out[i] = float(np.mean(window))
    return out
