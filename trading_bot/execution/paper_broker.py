"""
Simulated order execution with slippage + SQLite persistence.

The broker owns a single open Position (or None) and a running capital
figure. Every open/close writes to the trades table and capital_log.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from config import SLIPPAGE
from execution.position_manager import Position
from storage.database import Database

log = logging.getLogger(__name__)


class PaperBroker:
    """Paper-trading broker: slippage model + position + capital tracking."""

    def __init__(self, db: Database, starting_capital: float, mode_name: str) -> None:
        self.db = db
        self.capital: float = float(starting_capital)
        self.mode_name = mode_name
        self.position: Optional[Position] = None

    # ── state sync (post-restore) ──────────────────────────────────
    def restore(self, capital: float, open_position: Optional[Position]) -> None:
        self.capital = float(capital)
        self.position = open_position

    # ── open / close ───────────────────────────────────────────────
    def open_position(
        self,
        *,
        direction: str,
        candle_close: float,
        units: float,
        sl: float,
        tp: float,
        timestamp: datetime,
        score_at_entry: int,
        indicator_votes: Dict[str, int],
    ) -> Position:
        """
        Simulate a market order at candle close with one-side slippage.

        Returns the new Position and persists a trades row + capital_log entry.
        """
        if self.position is not None:
            raise RuntimeError("Cannot open a new position while one is already open")

        if direction == "LONG":
            exec_price = candle_close * (1.0 + SLIPPAGE)
        else:
            exec_price = candle_close * (1.0 - SLIPPAGE)

        # SL/TP are pre-computed relative to candle_close by strategy/risk.py,
        # so we re-anchor them to the executed price (proportional shift).
        shift = exec_price / candle_close
        sl_exec = sl * shift
        tp_exec = tp * shift

        trade_date = timestamp.strftime("%Y-%m-%d")
        entry_iso = timestamp.isoformat()
        trade_id = self.db.insert_open_trade(
            trade_date=trade_date,
            entry_time=entry_iso,
            direction=direction,
            entry_price=exec_price,
            units=units,
            sl_price=sl_exec,
            tp_price=tp_exec,
            mode=self.mode_name,
            score_at_entry=score_at_entry,
            indicator_votes=indicator_votes,
        )
        self.position = Position(
            direction=direction,
            entry_price=exec_price,
            units=units,
            sl_price=sl_exec,
            tp_price=tp_exec,
            entry_time=timestamp,
            score_at_entry=score_at_entry,
            indicator_votes=dict(indicator_votes),
            trade_id=trade_id,
        )

        self.db.log_capital(
            timestamp=entry_iso,
            event="POSITION_OPENED",
            capital_before=self.capital,
            capital_after=self.capital,
            notes=f"{direction} {units:.4f} @ {exec_price:.2f}",
        )
        log.info(
            "Opened %s %.4f @ %.2f | SL %.2f TP %.2f",
            direction, units, exec_price, sl_exec, tp_exec,
        )
        return self.position

    def close_position(
        self,
        *,
        candle_close: float,
        reason: str,
        timestamp: datetime,
    ) -> Tuple[float, float]:
        """
        Close the currently open position at candle close with slippage.

        Returns (realised_pnl, executed_price). Persists trade close + capital_log.
        """
        if self.position is None:
            raise RuntimeError("No open position to close")

        pos = self.position
        if pos.direction == "LONG":
            exec_price = candle_close * (1.0 - SLIPPAGE)
            pnl = (exec_price - pos.entry_price) * pos.units
        else:
            exec_price = candle_close * (1.0 + SLIPPAGE)
            pnl = (pos.entry_price - exec_price) * pos.units

        capital_before = self.capital
        self.capital = capital_before + pnl
        exit_iso = timestamp.isoformat()

        if pos.trade_id is not None:
            self.db.close_trade(
                pos.trade_id,
                exit_time=exit_iso,
                exit_price=exec_price,
                realised_pnl=pnl,
                exit_reason=reason,
            )
        self.db.log_capital(
            timestamp=exit_iso,
            event="POSITION_CLOSED",
            capital_before=capital_before,
            capital_after=self.capital,
            notes=f"{pos.direction} {reason} pnl={pnl:+.2f}",
        )
        log.info(
            "Closed %s @ %.2f (reason=%s) pnl=%+.2f capital=%.2f",
            pos.direction, exec_price, reason, pnl, self.capital,
        )
        self.position = None
        return pnl, exec_price

    # ── marks ──────────────────────────────────────────────────────
    def unrealised_pnl(self, current_price: float) -> float:
        if self.position is None:
            return 0.0
        return self.position.unrealised_pnl(current_price)
