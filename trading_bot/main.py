"""
Nifty 50 paper trading bot — CLI entry point.

Startup sequence (see README):
    1. CLI parsing, mode resolution.
    2. Holiday / weekend guard.
    3. Token validation.
    4. DB init (+ optional --reset or --report).
    5. Historical seed, initial VIX, previous-day OHLC for pivots.
    6. WebSocket subscribe, main loop, graceful shutdown + EOD report.
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import pytz
import requests

from auth import get_headers, validate_token
from config import (
    FORCE_CLOSE_HOUR,
    FORCE_CLOSE_MINUTE,
    HISTORICAL_ENDPOINT,
    HTTP_TIMEOUT,
    IST_TZ,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    NIFTY_SCRIP_CODE,
    STARTING_CAPITAL,
    get_mode_config,
)
from data.candle_builder import CandleBuilder
from data.feed import IndStocksFeed, fetch_historical_candles
from data.market_data import (
    VixRestPoller,
    fetch_vix_rest,
    is_trading_day,
)
from execution.paper_broker import PaperBroker
from execution.position_manager import Position
from indicators.structure import PrevOHLC
from reporting.html_report import generate_report
from reporting.terminal import render_dashboard
from storage.database import Database
from strategy.engine import StrategyEngine

IST = pytz.timezone(IST_TZ)

# ─────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────
_LOG_PATH = Path(__file__).resolve().parent / "logs" / "bot.log"
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _setup_logging() -> None:
    handler = RotatingFileHandler(
        _LOG_PATH, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


log = logging.getLogger("main")


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Nifty 50 paper trading bot")
    ap.add_argument(
        "--mode",
        choices=["safe", "balanced", "aggressive"],
        default="balanced",
        help="Trading mode (default: balanced)",
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="Wipe today's DB records and reset paper capital to ₹10,000",
    )
    ap.add_argument(
        "--report",
        action="store_true",
        help="Generate today's HTML report from DB without trading, then exit",
    )
    return ap.parse_args()


# ─────────────────────────────────────────────────────────────────────
# Previous-day OHLC for pivot points
# ─────────────────────────────────────────────────────────────────────
def _fetch_prev_day_ohlc() -> Optional[PrevOHLC]:
    """Fetch previous trading day's OHLC via historical REST endpoint."""
    now = datetime.now(IST)
    start = (now - timedelta(days=5)).replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    try:
        resp = requests.get(
            HISTORICAL_ENDPOINT,
            params={
                "instrument": NIFTY_SCRIP_CODE,
                "interval": "day",
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
            headers=get_headers(),
            timeout=HTTP_TIMEOUT,
        )
        if resp.status_code != 200:
            log.warning("Prev-day OHLC HTTP %d", resp.status_code)
            return None
        payload = resp.json()
        rows = []
        if isinstance(payload, dict):
            for k in ("data", "candles", "result"):
                if k in payload and isinstance(payload[k], list):
                    rows = payload[k]; break
        elif isinstance(payload, list):
            rows = payload
        if not rows:
            return None
        # Take the last day entry as "previous day"
        r = rows[-2] if len(rows) >= 2 else rows[-1]
        def pick(d, *keys, default=None):
            for k in keys:
                if k in d: return d[k]
            return default
        return PrevOHLC(
            open=float(pick(r, "open", "o", default=0.0)),
            high=float(pick(r, "high", "h", default=0.0)),
            low=float(pick(r, "low", "l", default=0.0)),
            close=float(pick(r, "close", "c", default=0.0)),
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("Prev-day OHLC fetch failed: %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────
def main() -> None:
    _setup_logging()
    args = _parse_args()
    mode = get_mode_config(args.mode)

    # Report-only mode bypasses everything else
    if args.report:
        db = Database()
        trade_date = datetime.now(IST).strftime("%Y-%m-%d")
        path = generate_report(db, trade_date)
        print(f"Report generated: {path}")
        db.close()
        return

    # Holiday / weekend guard
    today = datetime.now(IST).date()
    if not is_trading_day(today):
        print(f"Today ({today.isoformat()}) is not a trading day. NSE is closed. Exiting.")
        sys.exit(0)

    # Token validation
    validate_token()

    # DB + optional reset + state restore
    db = Database()
    trade_date = today.isoformat()
    if args.reset:
        db.reset_today(trade_date, STARTING_CAPITAL)
        print(f"Today's session reset — capital restored to \u20b9{STARTING_CAPITAL:,.2f}")

    restored = db.restore_state(trade_date, STARTING_CAPITAL)

    broker = PaperBroker(db, starting_capital=restored.current_capital, mode_name=mode.name)

    # Rehydrate open position (if any) into broker
    op = restored.open_position
    if op is not None:
        broker.position = Position(
            direction=op["direction"],
            entry_price=op["entry_price"],
            units=op["units"],
            sl_price=op["sl_price"],
            tp_price=op["tp_price"],
            entry_time=datetime.fromisoformat(op["entry_time"]),
            score_at_entry=op["score_at_entry"],
            indicator_votes=op["indicator_votes"],
            trade_id=op["trade_id"],
        )

    print(
        f"\u2713 State restored: {restored.trades_today} trades today, "
        f"capital \u20b9{restored.current_capital:,.2f}, "
        f"position: {op['direction'] if op else 'FLAT'}"
    )

    # Historical seed
    cb = CandleBuilder()
    hist = fetch_historical_candles()
    if hist:
        cb.seed_history(hist)
        print(f"\u2713 Loaded {len(hist)} historical candles for indicator pre-warming")
    else:
        log.warning("Historical seed unavailable — indicators will warm from live ticks")

    # Initial VIX + poller
    fetch_vix_rest()
    vix_poller = VixRestPoller(interval_s=300.0)
    vix_poller.start()

    # Previous-day OHLC for pivots
    prev_day = _fetch_prev_day_ohlc()

    # Engine
    engine = StrategyEngine(
        db=db,
        broker=broker,
        candle_builder=cb,
        mode=mode,
        render_cb=render_dashboard,
    )
    engine.state.trades_today = restored.trades_today
    engine.state.daily_pnl = restored.daily_pnl
    engine.state.consecutive_losses = restored.consecutive_losses
    engine.state.prev_day = prev_day

    cb.set_callback(engine.on_candle_close)

    # Feed
    feed = IndStocksFeed(cb)

    # Banner
    _print_banner(mode.name)

    # Signal handlers
    shutdown_flag = {"stop": False}

    def _sig_handler(signum, _frame):  # noqa: ANN001
        log.info("Signal %s received — shutting down", signum)
        shutdown_flag["stop"] = True

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    feed.start()

    # Main loop: wait until market close or shutdown, then finalise
    close_anchor = datetime.now(IST).replace(
        hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0
    )
    try:
        while not shutdown_flag["stop"]:
            if datetime.now(IST) >= close_anchor:
                log.info("Market close reached (%s)", close_anchor.time())
                break
            time.sleep(1.0)
    finally:
        log.info("Shutting down…")
        cb.force_finalise()
        try:
            engine.force_close_if_open()
        except Exception as exc:  # noqa: BLE001
            log.exception("Force-close failed: %s", exc)
        feed.stop()
        vix_poller.stop()

        # EOD report
        try:
            path = generate_report(db, trade_date)
            print(f"\n\u2713 End-of-day HTML report: {path}")
        except Exception as exc:  # noqa: BLE001
            log.exception("Report generation failed: %s", exc)

        # Final summary
        net = broker.capital - STARTING_CAPITAL
        pct = 100.0 * net / STARTING_CAPITAL if STARTING_CAPITAL else 0.0
        print(
            f"Final capital: \u20b9{broker.capital:,.2f}  "
            f"Net P&L: {net:+,.2f} ({pct:+.2f}%)"
        )
        db.close()


def _print_banner(mode_name: str) -> None:
    now = datetime.now(IST)
    open_anchor = now.replace(
        hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
    )
    if now < open_anchor:
        delta = int((open_anchor - now).total_seconds() // 60)
        minutes_to_open = f"{delta} minutes"
    else:
        minutes_to_open = "open now"
    bar = "=" * 38
    print(bar)
    print(" \U0001f916 NIFTY 50 PAPER TRADING BOT")
    print(f" Mode: {mode_name} | Capital: \u20b9{STARTING_CAPITAL:,.0f}")
    print(f" Market opens in: {minutes_to_open}")
    print(" Indicators: 15 | Evaluation: 1-min")
    print(bar)


if __name__ == "__main__":
    main()
