"""
Hard gates that must pass before a new entry is allowed.

Gates are checked in order; the first failure blocks and returns a
human-readable reason for the terminal / log.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pytz

from config import (
    ADX_MIN,
    CONSECUTIVE_LOSS_LIMIT,
    CONSECUTIVE_LOSS_PAUSE_MINUTES,
    FORCE_CLOSE_HOUR,
    FORCE_CLOSE_MINUTE,
    IST_TZ,
    ModeConfig,
    NO_NEW_ENTRIES_HOUR,
    NO_NEW_ENTRIES_MINUTE,
    ORB_END_HOUR,
    ORB_END_MINUTE,
    VIX_BLOCK_ABOVE,
    VIX_SAFE_MODE_ABOVE,
)

IST = pytz.timezone(IST_TZ)


@dataclass
class GateResult:
    """Outcome of check_gates: allowed + reason string."""

    allowed: bool
    reason: str


def check_gates(
    *,
    current_time: datetime,
    adx_value: Optional[float],
    vix_value: float,
    daily_pnl: float,
    trades_today: int,
    last_trade_time: Optional[datetime],
    consecutive_losses: int,
    last_loss_time: Optional[datetime],
    mode: ModeConfig,
) -> GateResult:
    """
    Run all hard gates in order. Return the first failure, or allowed=True.

    Caller is responsible for converting current_time to IST; this
    function handles naive datetimes by localising to IST.
    """
    if current_time.tzinfo is None:
        current_time = IST.localize(current_time)
    else:
        current_time = current_time.astimezone(IST)

    # 1. Time gate — ORB window
    orb_end = current_time.replace(
        hour=ORB_END_HOUR, minute=ORB_END_MINUTE, second=0, microsecond=0
    )
    if current_time < orb_end:
        return GateResult(False, "ORB formation window")

    # No new entries after 15:15
    no_new = current_time.replace(
        hour=NO_NEW_ENTRIES_HOUR,
        minute=NO_NEW_ENTRIES_MINUTE,
        second=0,
        microsecond=0,
    )
    force = current_time.replace(
        hour=FORCE_CLOSE_HOUR, minute=FORCE_CLOSE_MINUTE, second=0, microsecond=0
    )
    if current_time >= force:
        return GateResult(False, "Force-close window")
    if current_time >= no_new:
        return GateResult(False, "Market closing soon")

    # 2. ADX gate
    if adx_value is None:
        return GateResult(False, "ADX unavailable (warming up)")
    if adx_value < ADX_MIN:
        return GateResult(False, f"Low ADX ({adx_value:.1f}) — choppy market")

    # 3. VIX gate
    if vix_value > VIX_BLOCK_ABOVE:
        return GateResult(False, f"Extreme VIX ({vix_value:.1f}) — suspended")
    # Note: VIX>20 auto-switch to Safe handled by caller (we only warn here).

    # 4. Daily loss limit
    if daily_pnl <= -abs(mode.max_daily_loss):
        return GateResult(False, "Daily loss limit hit")

    # 5. Max trades
    if trades_today >= mode.max_trades_per_day:
        return GateResult(False, "Max trades reached")

    # 6. Cooldown
    if last_trade_time is not None:
        lt = last_trade_time
        if lt.tzinfo is None:
            lt = IST.localize(lt)
        delta = current_time - lt.astimezone(IST)
        if delta < timedelta(minutes=mode.cooldown_minutes):
            remaining = mode.cooldown_minutes - int(delta.total_seconds() // 60)
            return GateResult(False, f"Cooldown active ({remaining} min remaining)")

    # 7. Consecutive losses
    if consecutive_losses >= CONSECUTIVE_LOSS_LIMIT and last_loss_time is not None:
        ll = last_loss_time
        if ll.tzinfo is None:
            ll = IST.localize(ll)
        since = current_time - ll.astimezone(IST)
        if since < timedelta(minutes=CONSECUTIVE_LOSS_PAUSE_MINUTES):
            remaining = CONSECUTIVE_LOSS_PAUSE_MINUTES - int(since.total_seconds() // 60)
            return GateResult(
                False, f"3 losses — {remaining}min pause"
            )

    return GateResult(True, "OK")


def should_force_close(current_time: datetime) -> bool:
    """True when clock is at/after the force-close anchor (15:25 IST)."""
    if current_time.tzinfo is None:
        current_time = IST.localize(current_time)
    else:
        current_time = current_time.astimezone(IST)
    anchor = current_time.replace(
        hour=FORCE_CLOSE_HOUR, minute=FORCE_CLOSE_MINUTE, second=0, microsecond=0
    )
    return current_time >= anchor


def vix_requires_safe_mode(vix: float) -> bool:
    """True when VIX > 20 and we should auto-switch to Safe."""
    return VIX_SAFE_MODE_ABOVE < vix <= VIX_BLOCK_ABOVE
