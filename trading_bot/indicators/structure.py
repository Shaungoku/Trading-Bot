"""
Price structure & trend indicators: VWAP, Opening Range Breakout, Pivot
Points (classic + Camarilla), Parabolic SAR, and ATR-trend confirmation.

Some of these need extra context beyond the candle deque (session VWAP,
previous day's OHLC). These are passed in as parameters from the caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import numpy as np

from indicators._utils import atr, ohlcv, safe, sma


# ─────────────────────────────────────────────────────────────────────
# VWAP
# ─────────────────────────────────────────────────────────────────────
@safe()
def vwap_vote(candles: Iterable, vwap: Optional[float]) -> int:
    """
    Vote on price position relative to session VWAP.

    +1 if C > VWAP × 1.0005, -1 if C < VWAP × 0.9995, 0 if within ±0.05%.
    Returns 0 when VWAP is not yet available.
    """
    if vwap is None or vwap <= 0:
        return 0
    _, _, _, c, _ = ohlcv(candles)
    if len(c) == 0:
        return 0
    px = c[-1]
    if px > vwap * 1.0005:
        return 1
    if px < vwap * 0.9995:
        return -1
    return 0


# ─────────────────────────────────────────────────────────────────────
# Opening Range Breakout (09:15 → 09:30 IST)
# ─────────────────────────────────────────────────────────────────────
@safe()
def orb_vote(candles: Iterable) -> int:
    """
    Opening Range Breakout using 1-min bars 09:15–09:29 IST.

    Returns 0 if fewer than 15 ORB-window bars are available. Otherwise
    +1 on close > ORB high, -1 on close < ORB low, 0 inside the range.
    """
    cs = list(candles)
    if not cs:
        return 0
    orb_bars = [
        c for c in cs
        if c.timestamp.hour == 9 and 15 <= c.timestamp.minute <= 29
    ]
    if len(orb_bars) < 15:
        return 0
    orb_high = max(b.high for b in orb_bars)
    orb_low = min(b.low for b in orb_bars)
    # Only vote if we're past 09:30
    last = cs[-1]
    if last.timestamp.hour < 9 or (last.timestamp.hour == 9 and last.timestamp.minute < 30):
        return 0
    px = last.close
    if px > orb_high:
        return 1
    if px < orb_low:
        return -1
    return 0


# ─────────────────────────────────────────────────────────────────────
# Pivot points (classic + Camarilla)
# ─────────────────────────────────────────────────────────────────────
@dataclass
class PrevOHLC:
    """Previous trading day's OHLC used to compute pivot levels."""
    open: float
    high: float
    low: float
    close: float


def _pivot_levels(p: PrevOHLC) -> Tuple[float, List[float]]:
    """Return (classic pivot PP, sorted list of all classic+Camarilla levels)."""
    h, l, c = p.high, p.low, p.close
    rng = h - l
    pp = (h + l + c) / 3.0
    r1 = 2 * pp - l
    r2 = pp + rng
    r3 = h + 2 * (pp - l)
    s1 = 2 * pp - h
    s2 = pp - rng
    s3 = l - 2 * (h - pp)

    cam_r1 = c + rng * 1.1 / 12
    cam_r2 = c + rng * 1.1 / 6
    cam_r3 = c + rng * 1.1 / 4
    cam_r4 = c + rng * 1.1 / 2
    cam_s1 = c - rng * 1.1 / 12
    cam_s2 = c - rng * 1.1 / 6
    cam_s3 = c - rng * 1.1 / 4
    cam_s4 = c - rng * 1.1 / 2

    all_levels = sorted([
        r1, r2, r3, s1, s2, s3,
        cam_r1, cam_r2, cam_r3, cam_r4,
        cam_s1, cam_s2, cam_s3, cam_s4,
    ])
    return pp, all_levels


@safe()
def pivot_vote(candles: Iterable, prev_day: Optional[PrevOHLC]) -> int:
    """
    Combined classic + Camarilla pivot vote.

    +1 if price > PP and not within 0.1% of any level.
    -1 if price < PP and not within 0.1% of any level.
     0 if within 0.1% of any pivot level (danger zone) or prev_day unknown.
    """
    if prev_day is None:
        return 0
    _, _, _, c, _ = ohlcv(candles)
    if len(c) == 0:
        return 0
    pp, levels = _pivot_levels(prev_day)
    px = c[-1]
    # Proximity to any level
    for lvl in levels + [pp]:
        if lvl == 0:
            continue
        if abs(px - lvl) / lvl < 0.001:
            return 0
    if px > pp:
        return 1
    if px < pp:
        return -1
    return 0


# ─────────────────────────────────────────────────────────────────────
# Parabolic SAR (full Wilder algorithm)
# ─────────────────────────────────────────────────────────────────────
@safe()
def psar_vote(
    candles: Iterable,
    af_start: float = 0.02,
    af_increment: float = 0.02,
    af_max: float = 0.2,
) -> int:
    """
    Parabolic SAR vote.

    Run the full PSAR algorithm over all available candles; at any bar
    we track the trend direction, extreme point (EP), and acceleration
    factor (AF). Vote from the final bar: +1 if SAR is below close,
    -1 if SAR is above close.
    """
    _, h, l, c, _ = ohlcv(candles)
    n = len(c)
    if n < 3:
        return 0

    # Initial trend: based on the direction from bar 0 to bar 1
    trend_up = c[1] >= c[0]
    sar = l[0] if trend_up else h[0]
    ep = h[1] if trend_up else l[1]
    af = af_start

    for i in range(2, n):
        prev_sar = sar
        sar = prev_sar + af * (ep - prev_sar)

        if trend_up:
            sar = min(sar, l[i - 1], l[i - 2])  # never above last two lows
            if l[i] < sar:
                # flip
                trend_up = False
                sar = ep  # new SAR = old EP
                ep = l[i]
                af = af_start
            else:
                if h[i] > ep:
                    ep = h[i]
                    af = min(af + af_increment, af_max)
        else:
            sar = max(sar, h[i - 1], h[i - 2])  # never below last two highs
            if h[i] > sar:
                trend_up = True
                sar = ep
                ep = h[i]
                af = af_start
            else:
                if l[i] < ep:
                    ep = l[i]
                    af = min(af + af_increment, af_max)

    px = c[-1]
    if sar < px:
        return 1
    if sar > px:
        return -1
    return 0


# ─────────────────────────────────────────────────────────────────────
# ATR trend confirmation
# ─────────────────────────────────────────────────────────────────────
@safe()
def atr_trend_vote(candles: Iterable, atr_period: int = 7, ma_period: int = 20) -> int:
    """
    ATR-based trend confirmation.

    ATR_7 expanding above SMA(ATR, 20) signals active trend.
    Vote: +1 if ATR_7 > SMA_20 AND close up vs prev close (up-trend with expansion);
          -1 if ATR_7 > SMA_20 AND close down vs prev close (down-trend);
           0 if ATR_7 <= SMA_20 (ranging, unreliable).
    """
    _, h, l, c, _ = ohlcv(candles)
    if len(c) < atr_period + ma_period + 1:
        return 0
    atr_arr = atr(h, l, c, atr_period)
    atr_ma = sma(atr_arr, ma_period)
    a_now = atr_arr[-1]
    ma_now = atr_ma[-1]
    if np.isnan(a_now) or np.isnan(ma_now):
        return 0
    if a_now <= ma_now:
        return 0
    if c[-1] > c[-2]:
        return 1
    if c[-1] < c[-2]:
        return -1
    return 0


# ─────────────────────────────────────────────────────────────────────
# ADX (used by gate, not a vote)
# ─────────────────────────────────────────────────────────────────────
def adx_value(candles: Iterable, period: int = 14) -> Optional[float]:
    """
    Average Directional Index over `period`. Returns None if too few bars.
    Uses Wilder smoothing per the classic formula.
    """
    _, h, l, c, _ = ohlcv(candles)
    n = len(c)
    if n < period * 2 + 1:
        return None

    plus_dm = np.zeros(n, dtype=np.float64)
    minus_dm = np.zeros(n, dtype=np.float64)
    tr = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        up = h[i] - h[i - 1]
        down = l[i - 1] - l[i]
        plus_dm[i] = up if up > down and up > 0 else 0.0
        minus_dm[i] = down if down > up and down > 0 else 0.0
        tr[i] = max(
            h[i] - l[i],
            abs(h[i] - c[i - 1]),
            abs(l[i] - c[i - 1]),
        )

    # Wilder accumulators
    sm_tr = np.full(n, np.nan, dtype=np.float64)
    sm_pdm = np.full(n, np.nan, dtype=np.float64)
    sm_mdm = np.full(n, np.nan, dtype=np.float64)

    sm_tr[period] = float(np.sum(tr[1 : period + 1]))
    sm_pdm[period] = float(np.sum(plus_dm[1 : period + 1]))
    sm_mdm[period] = float(np.sum(minus_dm[1 : period + 1]))

    for i in range(period + 1, n):
        sm_tr[i] = sm_tr[i - 1] - (sm_tr[i - 1] / period) + tr[i]
        sm_pdm[i] = sm_pdm[i - 1] - (sm_pdm[i - 1] / period) + plus_dm[i]
        sm_mdm[i] = sm_mdm[i - 1] - (sm_mdm[i - 1] / period) + minus_dm[i]

    plus_di = np.full(n, np.nan, dtype=np.float64)
    minus_di = np.full(n, np.nan, dtype=np.float64)
    dx = np.full(n, np.nan, dtype=np.float64)
    for i in range(period, n):
        if np.isnan(sm_tr[i]) or sm_tr[i] == 0:
            continue
        plus_di[i] = 100.0 * sm_pdm[i] / sm_tr[i]
        minus_di[i] = 100.0 * sm_mdm[i] / sm_tr[i]
        denom = plus_di[i] + minus_di[i]
        if denom == 0:
            dx[i] = 0.0
        else:
            dx[i] = 100.0 * abs(plus_di[i] - minus_di[i]) / denom

    # Final ADX = Wilder smoothing of DX over another `period`
    start = period * 2
    if start >= n or np.isnan(dx[period:start]).all():
        return None
    adx = np.full(n, np.nan, dtype=np.float64)
    valid = dx[period:start]
    if np.isnan(valid).any():
        return None
    adx[start - 1] = float(np.mean(valid))
    for i in range(start, n):
        if np.isnan(dx[i]):
            adx[i] = adx[i - 1]
        else:
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period

    last = adx[-1]
    return None if np.isnan(last) else float(last)
