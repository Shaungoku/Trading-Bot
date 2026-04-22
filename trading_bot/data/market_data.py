"""
Supporting market data: India VIX tracking and NSE holiday calendar.

VIX is primarily pushed over the shared WebSocket; a REST poller serves
as a fallback. Holiday list is hard-coded for 2025 and 2026.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import date, datetime
from typing import List, Optional

import pytz
import requests

from auth import get_headers
from config import (
    HTTP_RETRIES,
    HTTP_RETRY_DELAY,
    HTTP_TIMEOUT,
    IST_TZ,
    QUOTE_LTP,
    VIX_SCRIP_CODE,
)

log = logging.getLogger(__name__)

IST = pytz.timezone(IST_TZ)

# ─────────────────────────────────────────────────────────────────────
# VIX state (thread-safe singleton)
# ─────────────────────────────────────────────────────────────────────
_vix_lock = threading.RLock()
_latest_vix: Optional[float] = None
_SAFE_DEFAULT_VIX: float = 15.0


def set_vix(value: float) -> None:
    """Update the latest VIX value (called from WS handler or REST poll)."""
    global _latest_vix
    if value is None:
        return
    try:
        v = float(value)
    except (TypeError, ValueError):
        return
    with _vix_lock:
        _latest_vix = v


def get_vix() -> float:
    """Latest VIX value or a safe default (15.0) with a warning if unset."""
    with _vix_lock:
        if _latest_vix is None:
            log.warning("VIX unavailable — returning safe default 15.0")
            return _SAFE_DEFAULT_VIX
        return _latest_vix


def fetch_vix_rest() -> Optional[float]:
    """One-shot REST fetch of India VIX LTP. Returns None on failure."""
    for attempt in range(HTTP_RETRIES):
        try:
            resp = requests.get(
                QUOTE_LTP,
                params={"scrip-codes": VIX_SCRIP_CODE},
                headers=get_headers(),
                timeout=HTTP_TIMEOUT,
            )
            if resp.status_code == 200:
                data = resp.json()
                val = _extract_ltp(data)
                if val is not None:
                    set_vix(val)
                    return val
            log.warning("VIX REST returned HTTP %d", resp.status_code)
        except requests.RequestException as exc:
            log.warning("VIX REST error (attempt %d): %s", attempt + 1, exc)
        time.sleep(HTTP_RETRY_DELAY)
    return None


def _extract_ltp(payload: object) -> Optional[float]:
    """Best-effort extraction of a numeric LTP from IndStocks JSON."""
    if isinstance(payload, dict):
        for k in ("ltp", "last_price", "lastPrice", "price"):
            if k in payload:
                try:
                    return float(payload[k])
                except (TypeError, ValueError):
                    pass
        if "data" in payload:
            return _extract_ltp(payload["data"])
        # Many IndStocks responses are keyed by scrip code
        for v in payload.values():
            if isinstance(v, (dict, list)):
                got = _extract_ltp(v)
                if got is not None:
                    return got
    elif isinstance(payload, list) and payload:
        return _extract_ltp(payload[0])
    return None


class VixRestPoller(threading.Thread):
    """Background poller that refreshes VIX every `interval_s` seconds."""

    def __init__(self, interval_s: float = 300.0) -> None:
        super().__init__(daemon=True, name="vix-rest-poller")
        self.interval_s = interval_s
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                fetch_vix_rest()
            except Exception as exc:  # noqa: BLE001
                log.exception("VixRestPoller error: %s", exc)
            self._stop.wait(self.interval_s)

    def stop(self) -> None:
        self._stop.set()


# ─────────────────────────────────────────────────────────────────────
# NSE holiday calendar
# ─────────────────────────────────────────────────────────────────────
# NSE declared trading holidays for 2025 and 2026.
# Sourced from the NSE "Trading Holidays" circular. Dates in ISO format.
NSE_HOLIDAYS_2025: List[str] = [
    "2025-02-26",  # Mahashivratri
    "2025-03-14",  # Holi
    "2025-03-31",  # Id-Ul-Fitr (Ramzan Id)
    "2025-04-10",  # Shri Mahavir Jayanti
    "2025-04-14",  # Dr. Baba Saheb Ambedkar Jayanti
    "2025-04-18",  # Good Friday
    "2025-05-01",  # Maharashtra Day
    "2025-08-15",  # Independence Day
    "2025-08-27",  # Shri Ganesh Chaturthi
    "2025-10-02",  # Mahatma Gandhi Jayanti / Dussehra
    "2025-10-21",  # Diwali Laxmi Pujan (Muhurat special session)
    "2025-10-22",  # Diwali-Balipratipada
    "2025-11-05",  # Prakash Gurpurb Sri Guru Nanak Dev
    "2025-12-25",  # Christmas
]

NSE_HOLIDAYS_2026: List[str] = [
    "2026-01-26",  # Republic Day
    "2026-03-03",  # Holi
    "2026-03-19",  # Id-Ul-Fitr
    "2026-03-31",  # Shri Mahavir Jayanti
    "2026-04-03",  # Good Friday
    "2026-04-14",  # Dr. Baba Saheb Ambedkar Jayanti
    "2026-05-01",  # Maharashtra Day
    "2026-05-27",  # Bakri Id
    "2026-06-26",  # Muharram
    "2026-08-14",  # Independence Day observance
    "2026-09-16",  # Shri Ganesh Chaturthi
    "2026-10-02",  # Mahatma Gandhi Jayanti
    "2026-10-20",  # Dussehra
    "2026-11-09",  # Diwali Laxmi Pujan (Muhurat special session)
    "2026-11-10",  # Diwali-Balipratipada
    "2026-11-24",  # Prakash Gurpurb Sri Guru Nanak Dev
    "2026-12-25",  # Christmas
]

_HOLIDAYS = set(NSE_HOLIDAYS_2025 + NSE_HOLIDAYS_2026)


def is_trading_day(d: Optional[date] = None) -> bool:
    """Return True if `d` (default: today IST) is an NSE trading day."""
    if d is None:
        d = datetime.now(IST).date()
    if d.weekday() >= 5:  # Sat=5, Sun=6
        return False
    return d.isoformat() not in _HOLIDAYS
