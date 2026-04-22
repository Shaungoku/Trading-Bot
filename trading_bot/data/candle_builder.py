"""
Tick → 1-minute OHLCV candle aggregator with running VWAP state.

Feeds completed candles to a registered callback. Rolls a deque of the
last N candles for indicator consumption. VWAP is computed from the
start of the trading session (09:15 IST) using typical-price × volume.
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Deque, Iterable, List, Optional

import pytz

from config import CANDLE_HISTORY_SIZE, IST_TZ

log = logging.getLogger(__name__)

IST = pytz.timezone(IST_TZ)


@dataclass
class Candle:
    """A completed 1-minute OHLCV bar."""

    timestamp: datetime  # minute bucket (IST, second=0)
    open: float
    high: float
    low: float
    close: float
    volume: float


CandleCallback = Callable[[Candle], None]


class CandleBuilder:
    """Accumulates raw ticks into 1-minute OHLCV candles + running VWAP."""

    def __init__(self, on_candle_close: Optional[CandleCallback] = None) -> None:
        self._lock = threading.RLock()
        self._on_close: Optional[CandleCallback] = on_candle_close
        self._candles: Deque[Candle] = deque(maxlen=CANDLE_HISTORY_SIZE)

        # In-progress candle state
        self._cur_bucket: Optional[datetime] = None
        self._cur_o: float = 0.0
        self._cur_h: float = 0.0
        self._cur_l: float = 0.0
        self._cur_c: float = 0.0
        self._cur_v: float = 0.0

        # VWAP running state (session-wide, reset at 09:15 each day)
        self._vwap_session_date: Optional[str] = None
        self._cum_tp_vol: float = 0.0
        self._cum_vol: float = 0.0

    # ── public API ──────────────────────────────────────────────────
    def set_callback(self, cb: CandleCallback) -> None:
        self._on_close = cb

    def seed_history(self, candles: Iterable[Candle]) -> None:
        """Pre-warm the deque with historical candles (oldest first)."""
        with self._lock:
            for c in candles:
                self._candles.append(c)
        log.info("CandleBuilder seeded with %d historical candles", len(self._candles))

    def candles(self) -> List[Candle]:
        """Return a snapshot list of completed candles (oldest first)."""
        with self._lock:
            return list(self._candles)

    def latest_vwap(self) -> Optional[float]:
        """Session VWAP, or None if no volume has accumulated yet."""
        with self._lock:
            if self._cum_vol <= 0:
                return None
            return self._cum_tp_vol / self._cum_vol

    def on_tick(self, ltp: float, volume: float, ts: Optional[datetime] = None) -> None:
        """
        Update candle + VWAP state from a single tick.

        `ts` is expected in IST; if None, now(IST) is used. LTP-only ticks
        pass volume=0 — they still update price fields.
        """
        if ts is None:
            ts = datetime.now(IST)
        elif ts.tzinfo is None:
            ts = IST.localize(ts)
        else:
            ts = ts.astimezone(IST)

        bucket = ts.replace(second=0, microsecond=0)

        with self._lock:
            self._reset_vwap_if_new_session(ts)

            # Start first candle
            if self._cur_bucket is None:
                self._open_new_candle(bucket, ltp, volume)
                return

            # New minute — finalise previous, start fresh
            if bucket > self._cur_bucket:
                self._finalise_current()
                self._open_new_candle(bucket, ltp, volume)
                return

            # Same minute — update H/L/C and accumulate V
            if ltp > self._cur_h:
                self._cur_h = ltp
            if ltp < self._cur_l:
                self._cur_l = ltp
            self._cur_c = ltp
            self._cur_v += max(volume, 0.0)

            # VWAP running update (use ltp as typical price proxy for ticks)
            if volume > 0:
                self._cum_tp_vol += ltp * volume
                self._cum_vol += volume

    # ── internals ───────────────────────────────────────────────────
    def _open_new_candle(self, bucket: datetime, ltp: float, volume: float) -> None:
        self._cur_bucket = bucket
        self._cur_o = ltp
        self._cur_h = ltp
        self._cur_l = ltp
        self._cur_c = ltp
        self._cur_v = max(volume, 0.0)
        if volume > 0:
            self._cum_tp_vol += ltp * volume
            self._cum_vol += volume

    def _finalise_current(self) -> None:
        """Seal the current candle, push to deque, invoke callback."""
        if self._cur_bucket is None:
            return
        candle = Candle(
            timestamp=self._cur_bucket,
            open=self._cur_o,
            high=self._cur_h,
            low=self._cur_l,
            close=self._cur_c,
            volume=self._cur_v,
        )
        self._candles.append(candle)

        # VWAP: additionally fold the candle's typical price × volume
        # (we have already folded ticks; for seeded or LTP-only sessions
        # use this as the fallback VWAP driver).
        if self._cur_v > 0 and self._cum_vol == 0:
            tp = (candle.high + candle.low + candle.close) / 3.0
            self._cum_tp_vol += tp * candle.volume
            self._cum_vol += candle.volume

        self._cur_bucket = None

        cb = self._on_close
        if cb is not None:
            try:
                cb(candle)
            except Exception as exc:  # noqa: BLE001
                log.exception("on_candle_close callback error: %s", exc)

    def _reset_vwap_if_new_session(self, ts: datetime) -> None:
        """Reset cumulative VWAP state at 09:15 IST each trading day."""
        day_key = ts.strftime("%Y-%m-%d")
        # Session anchor: 09:15 IST on this day
        anchor = IST.localize(datetime(ts.year, ts.month, ts.day, 9, 15, 0))
        if self._vwap_session_date != day_key and ts >= anchor:
            self._vwap_session_date = day_key
            self._cum_tp_vol = 0.0
            self._cum_vol = 0.0
            log.info("VWAP reset for session %s", day_key)

    def force_finalise(self) -> None:
        """Emit the current in-progress candle (e.g. on shutdown)."""
        with self._lock:
            self._finalise_current()
