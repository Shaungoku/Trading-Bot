"""
Central configuration for the Nifty 50 paper trading bot.

Defines per-mode trading parameters, universal session constants, and
IndStocks API endpoints. The active mode is selected by CLI argument in
main.py and resolved via get_mode_config().
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# ─────────────────────────────────────────────────────────────────────
# Mode parameters
# ─────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ModeConfig:
    """Per-mode risk and trade-pacing parameters."""

    name: str
    score_threshold: int          # absolute score needed to fire a signal (out of 15)
    sl_pct: float                 # stop loss distance from entry (fraction)
    tp_pct: float                 # take profit distance from entry (fraction)
    max_trades_per_day: int
    max_daily_loss: float         # ₹ absolute
    risk_per_trade_pct: float     # fraction of current capital risked per trade
    cooldown_minutes: int         # enforced gap between trades


SAFE = ModeConfig(
    name="SAFE",
    score_threshold=12,
    sl_pct=0.005,
    tp_pct=0.010,
    max_trades_per_day=3,
    max_daily_loss=500.0,
    risk_per_trade_pct=0.01,
    cooldown_minutes=10,
)

BALANCED = ModeConfig(
    name="BALANCED",
    score_threshold=10,
    sl_pct=0.010,
    tp_pct=0.020,
    max_trades_per_day=6,
    max_daily_loss=1500.0,
    risk_per_trade_pct=0.02,
    cooldown_minutes=5,
)

AGGRESSIVE = ModeConfig(
    name="AGGRESSIVE",
    score_threshold=8,
    sl_pct=0.015,
    tp_pct=0.030,
    max_trades_per_day=10,
    max_daily_loss=3000.0,
    risk_per_trade_pct=0.03,
    cooldown_minutes=3,
)

MODES: Dict[str, ModeConfig] = {
    "safe": SAFE,
    "balanced": BALANCED,
    "aggressive": AGGRESSIVE,
}


def get_mode_config(name: str) -> ModeConfig:
    """Resolve a CLI mode string to its ModeConfig."""
    key = name.strip().lower()
    if key not in MODES:
        raise ValueError(f"Unknown mode: {name!r}. Choose from {list(MODES)}.")
    return MODES[key]


# ─────────────────────────────────────────────────────────────────────
# Universal session constants
# ─────────────────────────────────────────────────────────────────────
STARTING_CAPITAL: float = 10_000.0
SLIPPAGE: float = 0.0005  # 0.05% per side

# Trading window (IST)
MARKET_OPEN_HOUR: int = 9
MARKET_OPEN_MINUTE: int = 15
ORB_END_HOUR: int = 9
ORB_END_MINUTE: int = 30       # no entries before 9:30
NO_NEW_ENTRIES_HOUR: int = 15
NO_NEW_ENTRIES_MINUTE: int = 15  # no new entries after 15:15
FORCE_CLOSE_HOUR: int = 15
FORCE_CLOSE_MINUTE: int = 25     # force close all at 15:25
MARKET_CLOSE_HOUR: int = 15
MARKET_CLOSE_MINUTE: int = 30

# Consecutive-loss circuit breaker
CONSECUTIVE_LOSS_LIMIT: int = 3
CONSECUTIVE_LOSS_PAUSE_MINUTES: int = 30

# Gate thresholds
ADX_MIN: float = 20.0
VIX_BLOCK_ABOVE: float = 25.0
VIX_SAFE_MODE_ABOVE: float = 20.0

# Instruments
NIFTY_SCRIP_CODE: str = "NSE_3045"
VIX_SCRIP_CODE: str = "NSE_VIX"

# ─────────────────────────────────────────────────────────────────────
# IndStocks endpoints
# ─────────────────────────────────────────────────────────────────────
INDSTOCKS_WS_URL: str = "wss://ws-prices.indstocks.com/api/v1/ws/prices"
INDSTOCKS_REST_BASE: str = "https://api.indstocks.com"

QUOTE_FULL: str = INDSTOCKS_REST_BASE + "/market/quotes/full"
QUOTE_LTP: str = INDSTOCKS_REST_BASE + "/market/quotes/ltp"
QUOTE_MKT: str = INDSTOCKS_REST_BASE + "/market/quotes/mkt"
HISTORICAL_ENDPOINT: str = INDSTOCKS_REST_BASE + "/market/historical"

# HTTP
HTTP_TIMEOUT: float = 10.0
HTTP_RETRIES: int = 3
HTTP_RETRY_DELAY: float = 2.0

# WebSocket reconnect
WS_RECONNECT_DELAYS = [2, 4, 8, 16, 32]  # seconds
WS_MAX_RETRIES: int = 5
REST_POLL_INTERVAL: float = 5.0  # fallback tick interval

# Candle window
CANDLE_HISTORY_SIZE: int = 200
HISTORICAL_SEED_CANDLES: int = 50

# ─────────────────────────────────────────────────────────────────────
# Timezone
# ─────────────────────────────────────────────────────────────────────
IST_TZ: str = "Asia/Kolkata"
