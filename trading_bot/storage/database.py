"""
SQLite persistence layer.

Provides a single Database class that wraps all read/write operations for
trades, candles, capital events, and indicator votes. All writes are
wrapped with a retry-once-on-error guard.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger(__name__)

_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent / "trading_bot.sqlite")
_SCHEMA_PATH = str(Path(__file__).resolve().parent / "schema.sql")


@dataclass
class RestoredState:
    """Snapshot of today's persisted session state, used for crash recovery."""

    trades_today: int
    daily_pnl: float
    current_capital: float
    open_position: Optional[Dict[str, Any]]
    consecutive_losses: int


class Database:
    """Thin, thread-safe SQLite wrapper for bot persistence."""

    def __init__(self, path: str = _DEFAULT_DB_PATH) -> None:
        self.path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ── schema ──────────────────────────────────────────────────────
    def _init_schema(self) -> None:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as fh:
            ddl = fh.read()
        with self._lock:
            self._conn.executescript(ddl)
            self._conn.commit()

    # ── retry-safe execute ──────────────────────────────────────────
    def _exec(self, sql: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a write with a single retry on sqlite3.Error."""
        last_err: Optional[Exception] = None
        for attempt in range(2):
            try:
                with self._lock:
                    cur = self._conn.execute(sql, params)
                    self._conn.commit()
                    return cur
            except sqlite3.Error as exc:
                last_err = exc
                log.error("DB write failed (attempt %d): %s", attempt + 1, exc)
                time.sleep(0.1)
        assert last_err is not None
        raise last_err

    def _query(self, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, params).fetchall())

    # ── trades ──────────────────────────────────────────────────────
    def insert_open_trade(
        self,
        *,
        trade_date: str,
        entry_time: str,
        direction: str,
        entry_price: float,
        units: float,
        sl_price: float,
        tp_price: float,
        mode: str,
        score_at_entry: int,
        indicator_votes: Dict[str, int],
    ) -> int:
        """Insert a trade row at entry (no exit fields yet). Returns new trade id."""
        cur = self._exec(
            """
            INSERT INTO trades (
                date, entry_time, direction, entry_price, units,
                sl_price, tp_price, mode, score_at_entry, indicator_votes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_date,
                entry_time,
                direction,
                entry_price,
                units,
                sl_price,
                tp_price,
                mode,
                score_at_entry,
                json.dumps(indicator_votes),
            ),
        )
        return int(cur.lastrowid)

    def close_trade(
        self,
        trade_id: int,
        *,
        exit_time: str,
        exit_price: float,
        realised_pnl: float,
        exit_reason: str,
    ) -> None:
        """Update a trade row with exit details."""
        self._exec(
            """
            UPDATE trades
               SET exit_time = ?, exit_price = ?, realised_pnl = ?, exit_reason = ?
             WHERE id = ?
            """,
            (exit_time, exit_price, realised_pnl, exit_reason, trade_id),
        )

    def fetch_trades_for(self, trade_date: str) -> List[sqlite3.Row]:
        """Return all trade rows for a given date (open + closed)."""
        return self._query(
            "SELECT * FROM trades WHERE date = ? ORDER BY id ASC", (trade_date,)
        )

    # ── candles ─────────────────────────────────────────────────────
    def insert_candle(
        self,
        *,
        timestamp: str,
        o: float,
        h: float,
        l: float,
        c: float,
        v: float,
    ) -> None:
        self._exec(
            "INSERT INTO candles (timestamp, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, o, h, l, c, v),
        )

    # ── capital log ─────────────────────────────────────────────────
    def log_capital(
        self,
        *,
        timestamp: str,
        event: str,
        capital_before: float,
        capital_after: float,
        notes: str = "",
    ) -> None:
        self._exec(
            "INSERT INTO capital_log (timestamp, event, capital_before, capital_after, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (timestamp, event, capital_before, capital_after, notes),
        )

    def fetch_capital_log_for(self, trade_date: str) -> List[sqlite3.Row]:
        return self._query(
            "SELECT * FROM capital_log WHERE substr(timestamp, 1, 10) = ? "
            "ORDER BY id ASC",
            (trade_date,),
        )

    # ── indicator log ───────────────────────────────────────────────
    def log_indicators(
        self,
        *,
        timestamp: str,
        votes: Dict[str, int],
        total_score: int,
        signal: str,
        adx_value: Optional[float],
        vix_value: Optional[float],
    ) -> None:
        self._exec(
            """
            INSERT INTO indicator_log (
                timestamp, rsi_vote, williams_r_vote, stochastic_vote, cci_vote,
                mfi_vote, vwap_vote, orb_vote, pivot_vote, bb_vote, keltner_vote,
                psar_vote, atr_trend_vote, pattern_vote, volume_vote,
                total_score, signal, adx_value, vix_value
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                int(votes.get("rsi", 0)),
                int(votes.get("williams_r", 0)),
                int(votes.get("stochastic", 0)),
                int(votes.get("cci", 0)),
                int(votes.get("mfi", 0)),
                int(votes.get("vwap", 0)),
                int(votes.get("orb", 0)),
                int(votes.get("pivot", 0)),
                int(votes.get("bb", 0)),
                int(votes.get("keltner", 0)),
                int(votes.get("psar", 0)),
                int(votes.get("atr_trend", 0)),
                int(votes.get("pattern", 0)),
                int(votes.get("volume", 0)),
                int(total_score),
                signal,
                adx_value,
                vix_value,
            ),
        )

    def fetch_indicator_log_for(self, trade_date: str) -> List[sqlite3.Row]:
        return self._query(
            "SELECT * FROM indicator_log WHERE substr(timestamp, 1, 10) = ? "
            "ORDER BY id ASC",
            (trade_date,),
        )

    # ── reset / restore ─────────────────────────────────────────────
    def reset_today(self, trade_date: str, starting_capital: float) -> None:
        """Wipe today's rows and seed a fresh capital entry."""
        with self._lock:
            self._conn.execute("DELETE FROM trades WHERE date = ?", (trade_date,))
            self._conn.execute(
                "DELETE FROM candles WHERE substr(timestamp, 1, 10) = ?", (trade_date,)
            )
            self._conn.execute(
                "DELETE FROM capital_log WHERE substr(timestamp, 1, 10) = ?",
                (trade_date,),
            )
            self._conn.execute(
                "DELETE FROM indicator_log WHERE substr(timestamp, 1, 10) = ?",
                (trade_date,),
            )
            self._conn.commit()
        self.log_capital(
            timestamp=f"{trade_date}T09:15:00",
            event="SESSION_RESET",
            capital_before=starting_capital,
            capital_after=starting_capital,
            notes="Reset via --reset",
        )

    def restore_state(
        self, trade_date: str, starting_capital: float
    ) -> RestoredState:
        """Rebuild today's session state from persisted rows for crash recovery."""
        trades = self.fetch_trades_for(trade_date)
        closed = [t for t in trades if t["exit_time"] is not None]
        open_rows = [t for t in trades if t["exit_time"] is None]

        daily_pnl = sum(float(t["realised_pnl"] or 0.0) for t in closed)
        trades_today = len(trades)

        # capital: last capital_after for today, else starting capital
        cap_rows = self.fetch_capital_log_for(trade_date)
        current_capital = (
            float(cap_rows[-1]["capital_after"]) if cap_rows else starting_capital
        )

        # open position dict
        open_position: Optional[Dict[str, Any]] = None
        if open_rows:
            row = open_rows[-1]
            open_position = {
                "trade_id": int(row["id"]),
                "direction": row["direction"],
                "entry_price": float(row["entry_price"]),
                "units": float(row["units"]),
                "sl_price": float(row["sl_price"]),
                "tp_price": float(row["tp_price"]),
                "entry_time": row["entry_time"],
                "score_at_entry": int(row["score_at_entry"]),
                "indicator_votes": json.loads(row["indicator_votes"]),
            }

        # consecutive losses at tail of closed trades
        consecutive_losses = 0
        for row in reversed(closed):
            if float(row["realised_pnl"] or 0.0) < 0:
                consecutive_losses += 1
            else:
                break

        return RestoredState(
            trades_today=trades_today,
            daily_pnl=daily_pnl,
            current_capital=current_capital,
            open_position=open_position,
            consecutive_losses=consecutive_losses,
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
