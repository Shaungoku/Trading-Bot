"""
Core strategy engine — invoked on each completed 1-minute candle.

Responsibilities:
    1. Run the gate stack (except for SL/TP checks on open positions).
    2. Call the scorer for a fresh 15-vote snapshot.
    3. Decide Long / Short / Flat from total score vs mode threshold.
    4. Manage an existing position (SL, TP, reversal, weakened-signal exit,
       force-close at 15:25 IST).
    5. Open new positions via PaperBroker.
    6. Persist every indicator snapshot, update session state.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional

import pytz

from config import IST_TZ, ModeConfig
from data.candle_builder import Candle, CandleBuilder
from data.market_data import get_vix
from execution.paper_broker import PaperBroker
from indicators.scorer import collect_votes
from indicators.structure import PrevOHLC, adx_value
from storage.database import Database
from strategy.gates import GateResult, check_gates, should_force_close, vix_requires_safe_mode
from strategy.risk import calculate_position

log = logging.getLogger(__name__)
IST = pytz.timezone(IST_TZ)


@dataclass
class SessionState:
    """Mutable per-session bookkeeping."""

    trades_today: int = 0
    wins: int = 0
    losses: int = 0
    daily_pnl: float = 0.0
    last_trade_time: Optional[datetime] = None
    consecutive_losses: int = 0
    last_loss_time: Optional[datetime] = None
    prev_day: Optional[PrevOHLC] = None
    last_gate_result: Optional[GateResult] = None
    last_score: int = 0
    last_votes: dict = field(default_factory=dict)
    last_signal: str = "FLAT"
    last_adx: Optional[float] = None
    last_vix: float = 15.0
    effective_mode: Optional[ModeConfig] = None


# Callback to notify the terminal renderer after each candle
RenderCallback = Callable[[Candle, SessionState, PaperBroker, Optional[float]], None]


class StrategyEngine:
    """Top-level engine orchestrating every 1-minute candle close."""

    def __init__(
        self,
        *,
        db: Database,
        broker: PaperBroker,
        candle_builder: CandleBuilder,
        mode: ModeConfig,
        render_cb: Optional[RenderCallback] = None,
    ) -> None:
        self.db = db
        self.broker = broker
        self.cb = candle_builder
        self.base_mode = mode
        self.render_cb = render_cb
        self.state = SessionState(effective_mode=mode)

    # ── public hooks ───────────────────────────────────────────────
    def on_candle_close(self, candle: Candle) -> None:
        """Driven by CandleBuilder. Never raises — wraps everything in try/except."""
        try:
            self._handle(candle)
        except Exception as exc:  # noqa: BLE001
            log.exception("engine.on_candle_close failed: %s", exc)

    # ── core logic ─────────────────────────────────────────────────
    def _handle(self, candle: Candle) -> None:
        self._persist_candle(candle)

        candles = self.cb.candles()
        vwap = self.cb.latest_vwap()

        # Indicators
        result = collect_votes(candles, vwap, self.state.prev_day)
        votes = result["votes"]
        total = int(result["total_score"])
        adx = adx_value(candles)
        vix = get_vix()

        self.state.last_votes = votes
        self.state.last_score = total
        self.state.last_adx = adx
        self.state.last_vix = vix

        # VIX safe-mode auto-switch
        mode = self.base_mode
        if vix_requires_safe_mode(vix):
            from config import SAFE
            if self.state.effective_mode is None or self.state.effective_mode.name != "SAFE":
                log.warning("VIX %.1f > 20 — auto-switching to SAFE mode", vix)
            mode = SAFE
        self.state.effective_mode = mode

        signal = self._signal_from_score(total, mode.score_threshold)
        self.state.last_signal = signal

        # Persist indicator snapshot
        self._persist_indicator_log(candle, votes, total, signal, adx, vix)

        # Manage open position (SL/TP/force-close/reversal) regardless of gates
        now_ts = candle.timestamp
        if self.broker.position is not None:
            handled = self._manage_open_position(candle, signal, total, mode)
            if handled:
                self._render(candle, vwap)
                return

        # Force-close window catches any lingering position too
        if should_force_close(now_ts):
            if self.broker.position is not None:
                self._close("FORCE_CLOSE", candle)
            self._render(candle, vwap)
            return

        # Gate check for new entry
        gate = check_gates(
            current_time=now_ts,
            adx_value=adx,
            vix_value=vix,
            daily_pnl=self.state.daily_pnl,
            trades_today=self.state.trades_today,
            last_trade_time=self.state.last_trade_time,
            consecutive_losses=self.state.consecutive_losses,
            last_loss_time=self.state.last_loss_time,
            mode=mode,
        )
        self.state.last_gate_result = gate

        if signal != "FLAT" and gate.allowed and self.broker.position is None:
            self._open(signal, candle, total, votes, mode)

        self._render(candle, vwap)

    # ── helpers ────────────────────────────────────────────────────
    def _signal_from_score(self, total: int, threshold: int) -> str:
        if total >= threshold:
            return "LONG"
        if total <= -threshold:
            return "SHORT"
        return "FLAT"

    def _manage_open_position(
        self, candle: Candle, signal: str, total: int, mode: ModeConfig
    ) -> bool:
        """Return True if we closed or reversed the position in this candle."""
        pos = self.broker.position
        assert pos is not None
        px = candle.close

        if pos.hit_stop(px):
            self._close("STOP_LOSS", candle)
            return True
        if pos.hit_target(px):
            self._close("TAKE_PROFIT", candle)
            return True

        # Reversal: if new signal is opposite direction
        opposite = (pos.direction == "LONG" and signal == "SHORT") or (
            pos.direction == "SHORT" and signal == "LONG"
        )
        if opposite:
            self._close("SIGNAL_REVERSAL", candle)
            # Open in new direction if gates allow
            gate = check_gates(
                current_time=candle.timestamp,
                adx_value=self.state.last_adx,
                vix_value=self.state.last_vix,
                daily_pnl=self.state.daily_pnl,
                trades_today=self.state.trades_today,
                last_trade_time=self.state.last_trade_time,
                consecutive_losses=self.state.consecutive_losses,
                last_loss_time=self.state.last_loss_time,
                mode=mode,
            )
            if gate.allowed:
                self._open(signal, candle, total, self.state.last_votes, mode)
            return True

        # Weakened signal exit: FLAT and score < 50% of threshold
        if signal == "FLAT":
            half = mode.score_threshold / 2.0
            signed_for_dir = total if pos.direction == "LONG" else -total
            if signed_for_dir < half:
                self._close("SIGNAL_WEAKENED", candle)
                return True

        return False

    def _open(
        self,
        signal: str,
        candle: Candle,
        total: int,
        votes: dict,
        mode: ModeConfig,
    ) -> None:
        params = calculate_position(candle.close, self.broker.capital, mode)
        if signal == "LONG":
            sl, tp = params.sl_price_long, params.tp_price_long
        else:
            sl, tp = params.sl_price_short, params.tp_price_short
        self.broker.open_position(
            direction=signal,
            candle_close=candle.close,
            units=params.units,
            sl=sl,
            tp=tp,
            timestamp=candle.timestamp,
            score_at_entry=total,
            indicator_votes=votes,
        )

    def _close(self, reason: str, candle: Candle) -> None:
        pnl, _exec = self.broker.close_position(
            candle_close=candle.close, reason=reason, timestamp=candle.timestamp
        )
        self.state.trades_today += 1
        self.state.daily_pnl += pnl
        self.state.last_trade_time = candle.timestamp
        if pnl > 0:
            self.state.wins += 1
            self.state.consecutive_losses = 0
        elif pnl < 0:
            self.state.losses += 1
            self.state.consecutive_losses += 1
            self.state.last_loss_time = candle.timestamp
        # pnl == 0 counted as neutral (no change to wins/losses)

    def _render(self, candle: Candle, vwap: Optional[float]) -> None:
        if self.render_cb is None:
            return
        try:
            self.render_cb(candle, self.state, self.broker, vwap)
        except Exception as exc:  # noqa: BLE001
            log.exception("render callback failed: %s", exc)

    def _persist_candle(self, candle: Candle) -> None:
        try:
            self.db.insert_candle(
                timestamp=candle.timestamp.isoformat(),
                o=candle.open,
                h=candle.high,
                l=candle.low,
                c=candle.close,
                v=candle.volume,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("insert_candle failed: %s", exc)

    def _persist_indicator_log(
        self,
        candle: Candle,
        votes: dict,
        total: int,
        signal: str,
        adx: Optional[float],
        vix: float,
    ) -> None:
        try:
            self.db.log_indicators(
                timestamp=candle.timestamp.isoformat(),
                votes=votes,
                total_score=total,
                signal=signal,
                adx_value=adx,
                vix_value=vix,
            )
        except Exception as exc:  # noqa: BLE001
            log.error("log_indicators failed: %s", exc)

    def force_close_if_open(self) -> None:
        """Invoked from main on shutdown / EOD."""
        if self.broker.position is None:
            return
        candles = self.cb.candles()
        if not candles:
            return
        last = candles[-1]
        self._close("EOD", last)
