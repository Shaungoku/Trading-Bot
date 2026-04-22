"""
Scorer: runs all 15 indicators and aggregates votes.

Returned score is a signed integer in approximately [-16, +16] (pattern
contributes up to ±2, the other 13 contribute ±1 each, volume adds ±1).
Callers compare |total_score| against the mode's threshold to decide.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from indicators.momentum import (
    cci_vote,
    mfi_vote,
    rsi_vote,
    stochastic_vote,
    williams_r_vote,
)
from indicators.patterns import pattern_vote
from indicators.structure import (
    PrevOHLC,
    atr_trend_vote,
    orb_vote,
    pivot_vote,
    psar_vote,
    vwap_vote,
)
from indicators.volatility import bollinger_vote, keltner_vote
from indicators.volume import volume_spike_vote


INDICATOR_KEYS = [
    "rsi",
    "williams_r",
    "stochastic",
    "cci",
    "mfi",
    "vwap",
    "orb",
    "pivot",
    "bb",
    "keltner",
    "psar",
    "atr_trend",
    "pattern",
    "volume",
]


def collect_votes(
    candles: Iterable,
    vwap: Optional[float],
    prev_day: Optional[PrevOHLC] = None,
) -> Dict[str, Any]:
    """
    Run all 15 indicator checks and return a structured result.

    Keys:
        votes          - dict of {indicator_name: int vote}
        total_score    - sum of votes (signed, ~[-16, +16])
        bullish_count  - count of positive votes
        bearish_count  - count of negative votes
        neutral_count  - count of 0 votes
    """
    votes: Dict[str, int] = {
        "rsi": rsi_vote(candles),
        "williams_r": williams_r_vote(candles),
        "stochastic": stochastic_vote(candles),
        "cci": cci_vote(candles),
        "mfi": mfi_vote(candles),
        "vwap": vwap_vote(candles, vwap),
        "orb": orb_vote(candles),
        "pivot": pivot_vote(candles, prev_day),
        "bb": bollinger_vote(candles),
        "keltner": keltner_vote(candles),
        "psar": psar_vote(candles),
        "atr_trend": atr_trend_vote(candles),
        "pattern": pattern_vote(candles),  # ±2
        "volume": volume_spike_vote(candles),
    }
    total = int(sum(votes.values()))
    bullish = sum(1 for v in votes.values() if v > 0)
    bearish = sum(1 for v in votes.values() if v < 0)
    neutral = sum(1 for v in votes.values() if v == 0)
    return {
        "votes": votes,
        "total_score": total,
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
    }
