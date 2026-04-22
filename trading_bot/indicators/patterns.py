"""
Candlestick pattern recognition — counts as 2 votes in the scorer.

Evaluates the last three completed candles for bullish/bearish multi-bar
patterns (engulfing, morning/evening star, hammer/shooting star,
marubozu). Returns +2, -2, or 0.
"""
from __future__ import annotations

import logging
from typing import Iterable

from indicators._utils import safe

log = logging.getLogger(__name__)


def _metrics(c) -> dict:
    """Compute body / wick / range metrics for a single candle."""
    rng = max(c.high - c.low, 0.0)
    body = abs(c.close - c.open)
    upper = c.high - max(c.open, c.close)
    lower = min(c.open, c.close) - c.low
    return {
        "range": rng,
        "body": body,
        "upper": upper,
        "lower": lower,
        "bull": c.close > c.open,
        "bear": c.close < c.open,
        "doji": body < rng * 0.05 if rng > 0 else True,
    }


@safe()
def pattern_vote(candles: Iterable) -> int:
    """
    Detect bullish or bearish patterns on the last three candles.

    Returns +2 on any bullish pattern, -2 on any bearish pattern, 0
    otherwise. Doji / spinning top are explicitly neutral (log a debug
    warning so the session record still reflects their presence).
    """
    cs = list(candles)
    if len(cs) < 3:
        return 0
    c1, c2, c3 = cs[-3], cs[-2], cs[-1]
    m1, m2, m3 = _metrics(c1), _metrics(c2), _metrics(c3)

    # ── Bullish patterns ───────────────────────────────────────────
    # Bullish Engulfing
    if (
        m2["bear"] and m3["bull"]
        and c3.open < c2.close and c3.close > c2.open
    ):
        return 2

    # Morning Star
    if (
        m1["bear"] and m1["body"] > 0.6 * max(m1["range"], 1e-9)
        and m2["body"] < 0.3 * max(m2["range"], 1e-9)
        and m3["bull"] and m3["body"] > 0.6 * max(m3["range"], 1e-9)
        and c3.close > (c1.open + c1.close) / 2.0
    ):
        return 2

    # Hammer (in downtrend — last 3 closes declining)
    if (
        c1.close > c2.close > c3.close
        and m3["lower"] >= 2 * m3["body"]
        and m3["upper"] < max(m3["body"], 1e-9)
        and (m3["bull"] or m3["doji"])
    ):
        return 2

    # Bullish Marubozu
    if m3["bull"] and m3["body"] > 0.9 * max(m3["range"], 1e-9):
        return 2

    # ── Bearish patterns ───────────────────────────────────────────
    # Bearish Engulfing
    if (
        m2["bull"] and m3["bear"]
        and c3.open > c2.close and c3.close < c2.open
    ):
        return -2

    # Evening Star
    if (
        m1["bull"] and m1["body"] > 0.6 * max(m1["range"], 1e-9)
        and m2["body"] < 0.3 * max(m2["range"], 1e-9)
        and m3["bear"] and m3["body"] > 0.6 * max(m3["range"], 1e-9)
        and c3.close < (c1.open + c1.close) / 2.0
    ):
        return -2

    # Shooting Star (in uptrend — last 3 closes rising)
    if (
        c1.close < c2.close < c3.close
        and m3["upper"] >= 2 * m3["body"]
        and m3["lower"] < max(m3["body"], 1e-9)
        and (m3["bear"] or m3["doji"])
    ):
        return -2

    # Bearish Marubozu
    if m3["bear"] and m3["body"] > 0.9 * max(m3["range"], 1e-9):
        return -2

    # ── Neutral patterns ───────────────────────────────────────────
    if m3["doji"]:
        log.debug("Doji at %s — neutral", c3.timestamp)
    elif (
        m3["body"] < 0.3 * max(m3["range"], 1e-9)
        and m3["upper"] > 0.2 * m3["range"]
        and m3["lower"] > 0.2 * m3["range"]
    ):
        log.debug("Spinning top at %s — neutral", c3.timestamp)

    return 0
