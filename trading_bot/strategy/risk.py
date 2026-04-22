"""
Position sizing and SL/TP calculation helpers.

Units are fractional ("0.35 units of index") and rounded to 0.05 since
Nifty index trades indivisibly but the paper simulator supports fractions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from config import ModeConfig


@dataclass
class PositionParams:
    """Computed entry parameters before execution."""

    units: float
    sl_price_long: float
    tp_price_long: float
    sl_price_short: float
    tp_price_short: float
    risk_amount: float


def calculate_position(
    entry_price: float, current_capital: float, mode: ModeConfig
) -> PositionParams:
    """
    Compute units and SL/TP for both directions given current capital.

    risk_amount = capital × risk_per_trade_pct
    sl_distance = entry × sl_pct
    units = risk_amount / sl_distance, rounded down to 0.05.
    """
    risk_amount = current_capital * mode.risk_per_trade_pct
    sl_distance = entry_price * mode.sl_pct
    if sl_distance <= 0:
        raise ValueError("sl_distance must be > 0")
    raw_units = risk_amount / sl_distance
    units = math.floor(raw_units * 20.0) / 20.0
    if units < 0.05:
        units = 0.05  # minimum meaningful size

    sl_long = entry_price * (1.0 - mode.sl_pct)
    tp_long = entry_price * (1.0 + mode.tp_pct)
    sl_short = entry_price * (1.0 + mode.sl_pct)
    tp_short = entry_price * (1.0 - mode.tp_pct)

    return PositionParams(
        units=units,
        sl_price_long=sl_long,
        tp_price_long=tp_long,
        sl_price_short=sl_short,
        tp_price_short=tp_short,
        risk_amount=risk_amount,
    )
