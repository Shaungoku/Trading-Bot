"""
Open-position container + unrealised-P&L helper.

The PaperBroker holds at most one Position at a time (the bot is a
single-instrument bot). PositionManager is a thin dataclass wrapper with
helpers so callers don't scatter P&L math.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class Position:
    """Open paper-trade position."""

    direction: str  # "LONG" or "SHORT"
    entry_price: float
    units: float
    sl_price: float
    tp_price: float
    entry_time: datetime
    score_at_entry: int
    indicator_votes: Dict[str, int] = field(default_factory=dict)
    trade_id: Optional[int] = None

    def unrealised_pnl(self, current_price: float) -> float:
        """Mark-to-market P&L at `current_price`."""
        if self.direction == "LONG":
            return (current_price - self.entry_price) * self.units
        return (self.entry_price - current_price) * self.units

    def hit_stop(self, price: float) -> bool:
        if self.direction == "LONG":
            return price <= self.sl_price
        return price >= self.sl_price

    def hit_target(self, price: float) -> bool:
        if self.direction == "LONG":
            return price >= self.tp_price
        return price <= self.tp_price
