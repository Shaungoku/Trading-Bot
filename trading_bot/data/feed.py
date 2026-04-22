"""
WebSocket feed + REST historical seeder for Nifty 50 and India VIX.

Connects to IndStocks' WS price feed, subscribes to NSE_3045 (full mode)
and NSE_VIX (ltp mode), routes Nifty ticks into the CandleBuilder, and
sets latest VIX via market_data.set_vix(). Handles exponential backoff
reconnects and falls back to REST LTP polling after repeated failures.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional

import pytz
import requests
import websocket  # from websocket-client

from auth import get_headers, get_token
from config import (
    HISTORICAL_ENDPOINT,
    HISTORICAL_SEED_CANDLES,
    HTTP_RETRIES,
    HTTP_RETRY_DELAY,
    HTTP_TIMEOUT,
    INDSTOCKS_WS_URL,
    IST_TZ,
    NIFTY_SCRIP_CODE,
    QUOTE_LTP,
    REST_POLL_INTERVAL,
    VIX_SCRIP_CODE,
    WS_MAX_RETRIES,
    WS_RECONNECT_DELAYS,
)
from data.candle_builder import Candle, CandleBuilder
from data.market_data import set_vix

log = logging.getLogger(__name__)
IST = pytz.timezone(IST_TZ)


# ─────────────────────────────────────────────────────────────────────
# Tick parsing helpers (resilient to minor payload schema differences)
# ─────────────────────────────────────────────────────────────────────
def _as_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def _pick(d: dict, *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def _instrument_of(msg: dict) -> Optional[str]:
    for k in ("instrument", "scrip_code", "scripCode", "symbol", "tradingsymbol"):
        v = msg.get(k)
        if isinstance(v, str):
            return v
    return None


def _parse_timestamp(msg: dict) -> datetime:
    raw = _pick(msg, "timestamp", "ts", "time", "exchange_timestamp")
    if raw is None:
        return datetime.now(IST)
    # epoch seconds / millis
    if isinstance(raw, (int, float)):
        v = float(raw)
        if v > 1e12:  # millis
            v /= 1000.0
        return datetime.fromtimestamp(v, tz=IST)
    if isinstance(raw, str):
        try:
            if raw.isdigit():
                v = float(raw)
                if v > 1e12:
                    v /= 1000.0
                return datetime.fromtimestamp(v, tz=IST)
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = IST.localize(dt)
            return dt.astimezone(IST)
        except ValueError:
            pass
    return datetime.now(IST)


# ─────────────────────────────────────────────────────────────────────
# Historical seed
# ─────────────────────────────────────────────────────────────────────
def fetch_historical_candles(
    scrip_code: str = NIFTY_SCRIP_CODE, n: int = HISTORICAL_SEED_CANDLES
) -> List[Candle]:
    """Fetch the last N 1-minute OHLCV candles via IndStocks REST."""
    end = datetime.now(IST)
    start = end - timedelta(minutes=n + 5)
    params = {
        "instrument": scrip_code,
        "interval": "1minute",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
    }
    for attempt in range(HTTP_RETRIES):
        try:
            resp = requests.get(
                HISTORICAL_ENDPOINT,
                params=params,
                headers=get_headers(),
                timeout=HTTP_TIMEOUT,
            )
            if resp.status_code == 200:
                return _parse_historical_payload(resp.json(), n)
            log.warning("Historical REST HTTP %d: %s", resp.status_code, resp.text[:200])
        except requests.RequestException as exc:
            log.warning("Historical REST error (attempt %d): %s", attempt + 1, exc)
        time.sleep(HTTP_RETRY_DELAY)
    log.warning("Historical seed unavailable — starting cold")
    return []


def _parse_historical_payload(payload: Any, n: int) -> List[Candle]:
    """Best-effort parse of the historical candles payload into Candle objects."""
    rows: List[dict] = []
    if isinstance(payload, dict):
        for key in ("data", "candles", "result", "results"):
            if key in payload and isinstance(payload[key], list):
                rows = payload[key]
                break
    elif isinstance(payload, list):
        rows = payload

    out: List[Candle] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        ts = _parse_timestamp(r)
        o = _as_float(_pick(r, "open", "o"))
        h = _as_float(_pick(r, "high", "h"))
        l = _as_float(_pick(r, "low", "l"))
        c = _as_float(_pick(r, "close", "c"))
        v = _as_float(_pick(r, "volume", "v")) or 0.0
        if None in (o, h, l, c):
            continue
        bucket = ts.replace(second=0, microsecond=0)
        out.append(Candle(bucket, o, h, l, c, v))
    out.sort(key=lambda c: c.timestamp)
    return out[-n:]


# ─────────────────────────────────────────────────────────────────────
# WebSocket client
# ─────────────────────────────────────────────────────────────────────
class IndStocksFeed:
    """
    Persistent WebSocket feed. Routes Nifty ticks to a CandleBuilder and
    VIX ticks to market_data.set_vix(). Thread-safe start/stop lifecycle.
    """

    def __init__(self, candle_builder: CandleBuilder) -> None:
        self._cb = candle_builder
        self._ws: Optional[websocket.WebSocketApp] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._rest_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._rest_fallback_active = threading.Event()
        self._retries_in_row = 0
        self._connected = threading.Event()

    # ── lifecycle ───────────────────────────────────────────────────
    def start(self) -> None:
        self._stop.clear()
        self._ws_thread = threading.Thread(
            target=self._run_forever, name="ws-feed", daemon=True
        )
        self._ws_thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:  # noqa: BLE001
                pass

    # ── WebSocket driver ────────────────────────────────────────────
    def _run_forever(self) -> None:
        while not self._stop.is_set():
            token = get_token()
            header = [f"Authorization: Bearer {token}"] if token else []
            self._ws = websocket.WebSocketApp(
                INDSTOCKS_WS_URL,
                header=header,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            try:
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:  # noqa: BLE001
                log.exception("WebSocket run_forever crashed: %s", exc)

            if self._stop.is_set():
                return

            # Backoff before reconnect
            self._retries_in_row += 1
            delay_idx = min(self._retries_in_row - 1, len(WS_RECONNECT_DELAYS) - 1)
            delay = WS_RECONNECT_DELAYS[delay_idx]
            log.warning(
                "WebSocket disconnected — reconnecting in %ds (attempt %d)",
                delay,
                self._retries_in_row,
            )
            time.sleep(delay)

            if self._retries_in_row >= WS_MAX_RETRIES:
                log.critical(
                    "WebSocket failed %d times — activating REST polling fallback",
                    self._retries_in_row,
                )
                self._start_rest_fallback()

    # ── WS event handlers ───────────────────────────────────────────
    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        log.info("WebSocket connected — subscribing to %s + %s", NIFTY_SCRIP_CODE, VIX_SCRIP_CODE)
        self._connected.set()
        self._retries_in_row = 0
        self._stop_rest_fallback()

        try:
            ws.send(json.dumps({
                "action": "subscribe",
                "instrument": NIFTY_SCRIP_CODE,
                "mode": "full",
            }))
            ws.send(json.dumps({
                "action": "subscribe",
                "instrument": VIX_SCRIP_CODE,
                "mode": "ltp",
            }))
        except Exception as exc:  # noqa: BLE001
            log.exception("WebSocket subscribe failed: %s", exc)

    def _on_message(self, _ws: websocket.WebSocketApp, raw: str) -> None:
        try:
            self._handle_message(raw)
        except Exception as exc:  # noqa: BLE001
            log.exception("Tick handler error: %s", exc)

    def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            log.debug("Non-JSON frame: %s", raw[:120])
            return

        # Some APIs wrap payloads
        if isinstance(msg, dict) and "data" in msg and isinstance(msg["data"], dict):
            inner = msg["data"]
            inner.setdefault("instrument", _instrument_of(msg) or _instrument_of(inner))
            msg = inner

        if not isinstance(msg, dict):
            return

        instrument = _instrument_of(msg) or ""
        ltp = _as_float(_pick(msg, "ltp", "last_price", "lastPrice", "price", "c", "close"))
        if ltp is None:
            return

        if VIX_SCRIP_CODE in instrument or "VIX" in instrument.upper():
            set_vix(ltp)
            return

        if NIFTY_SCRIP_CODE in instrument or instrument == "" or "NIFTY" in instrument.upper():
            vol = _as_float(_pick(msg, "volume", "v", "vol", "last_traded_quantity")) or 0.0
            ts = _parse_timestamp(msg)
            self._cb.on_tick(ltp=ltp, volume=vol, ts=ts)

    def _on_error(self, _ws: websocket.WebSocketApp, error: BaseException) -> None:
        log.error("WebSocket error: %s", error)

    def _on_close(
        self,
        _ws: websocket.WebSocketApp,
        status_code: Optional[int],
        reason: Optional[str],
    ) -> None:
        self._connected.clear()
        log.info("WebSocket closed: code=%s reason=%s", status_code, reason)

    # ── REST polling fallback ───────────────────────────────────────
    def _start_rest_fallback(self) -> None:
        if self._rest_fallback_active.is_set():
            return
        self._rest_fallback_active.set()
        self._rest_thread = threading.Thread(
            target=self._poll_rest, name="rest-fallback", daemon=True
        )
        self._rest_thread.start()

    def _stop_rest_fallback(self) -> None:
        self._rest_fallback_active.clear()

    def _poll_rest(self) -> None:
        """Poll LTP every REST_POLL_INTERVAL seconds until WS reconnects."""
        while self._rest_fallback_active.is_set() and not self._stop.is_set():
            try:
                resp = requests.get(
                    QUOTE_LTP,
                    params={"scrip-codes": NIFTY_SCRIP_CODE},
                    headers=get_headers(),
                    timeout=HTTP_TIMEOUT,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    ltp = _as_float(_extract_ltp(data))
                    if ltp is not None:
                        self._cb.on_tick(ltp=ltp, volume=0.0)
            except requests.RequestException as exc:
                log.warning("REST fallback error: %s", exc)
            time.sleep(REST_POLL_INTERVAL)


def _extract_ltp(payload: Any) -> Optional[float]:
    """Traverse an IndStocks LTP response and pull out the numeric price."""
    if isinstance(payload, dict):
        for k in ("ltp", "last_price", "lastPrice", "price"):
            if k in payload:
                return _as_float(payload[k])
        if "data" in payload:
            return _extract_ltp(payload["data"])
        for v in payload.values():
            if isinstance(v, (dict, list)):
                got = _extract_ltp(v)
                if got is not None:
                    return got
    elif isinstance(payload, list) and payload:
        return _extract_ltp(payload[0])
    return None
