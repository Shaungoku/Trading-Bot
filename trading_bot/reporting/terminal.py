"""
Live 1-minute terminal dashboard.

Renders a fixed-shape multi-line block coloured via colorama. Uses ANSI
cursor movement (no full-screen clears) so the block updates in place
while allowing logs to append below on shutdown.
"""
from __future__ import annotations

from typing import Dict, Optional

from colorama import Fore, Style, init as colorama_init

from config import STARTING_CAPITAL
from data.candle_builder import Candle
from execution.paper_broker import PaperBroker
from strategy.engine import SessionState

colorama_init(autoreset=True)

# Abbreviated indicator labels, in display order across three rows
_ROWS: list[list[tuple[str, str]]] = [
    [("RSI", "rsi"), ("W%R", "williams_r"), ("STOCH", "stochastic"),
     ("CCI", "cci"), ("MFI", "mfi")],
    [("VWAP", "vwap"), ("ORB", "orb"), ("PVOT", "pivot"),
     ("BB%B", "bb"), ("KELT", "keltner")],
    [("PSAR", "psar"), ("ATR", "atr_trend"), ("PATT", "pattern"),
     ("VOL", "volume")],
]


def _sign(v: int) -> str:
    if v > 0:
        return f"{Fore.GREEN}+{v}{Style.RESET_ALL}"
    if v < 0:
        return f"{Fore.RED}{v}{Style.RESET_ALL}"
    return f"{Fore.YELLOW} 0{Style.RESET_ALL}"


def _score_label(total: int, threshold: int) -> str:
    if total >= threshold:
        return f"{Fore.GREEN}{total}/15 BULLISH{Style.RESET_ALL}"
    if total <= -threshold:
        return f"{Fore.RED}{total}/15 BEARISH{Style.RESET_ALL}"
    return f"{Fore.YELLOW}{total}/15 NEUTRAL{Style.RESET_ALL}"


def _gate_icon(ok: bool) -> str:
    return f"{Fore.GREEN}\u2713{Style.RESET_ALL}" if ok else f"{Fore.RED}\u2717{Style.RESET_ALL}"


def render_dashboard(
    candle: Candle,
    state: SessionState,
    broker: PaperBroker,
    vwap: Optional[float],
) -> None:
    """Print the live terminal dashboard block for the given candle."""
    mode = state.effective_mode.name if state.effective_mode else "-"
    ts = candle.timestamp.strftime("%H:%M")

    sep = "\u2500" * 65
    print(sep)
    print(
        f" {Fore.CYAN}\U0001f550 {ts} IST{Style.RESET_ALL}  \u2502  "
        f"{Fore.CYAN}NIFTY 50: \u20b9{candle.close:,.2f}{Style.RESET_ALL}  \u2502  "
        f"Mode: {Fore.CYAN}{mode}{Style.RESET_ALL}"
    )
    print(sep)

    adx = state.last_adx
    adx_str = f"{adx:.1f}" if adx is not None else "--"
    adx_ok = adx is not None and adx >= 20
    vix_ok = state.last_vix <= 25

    score_txt = _score_label(
        state.last_score,
        state.effective_mode.score_threshold if state.effective_mode else 10,
    )
    print(
        f" SCORE   {score_txt}  \u2502  ADX: {adx_str} {_gate_icon(adx_ok)}  "
        f"\u2502  VIX: {state.last_vix:.1f} {_gate_icon(vix_ok)}"
    )
    print(sep)

    votes = state.last_votes or {}
    for row in _ROWS:
        parts = []
        for label, key in row:
            parts.append(f"{label}:{_sign(int(votes.get(key, 0)))}")
        print(" " + "  ".join(parts))
    print(sep)

    if broker.position is not None:
        p = broker.position
        pnl = p.unrealised_pnl(candle.close)
        arrow = "\u25b2" if pnl >= 0 else "\u25bc"
        pnl_colour = Fore.GREEN if pnl >= 0 else Fore.RED
        dir_colour = Fore.GREEN if p.direction == "LONG" else Fore.RED
        print(
            f" POSITION  {dir_colour}{p.direction}{Style.RESET_ALL} @ "
            f"\u20b9{p.entry_price:,.2f}  SL:\u20b9{p.sl_price:,.2f}  "
            f"TP:\u20b9{p.tp_price:,.2f}"
        )
        print(
            f"           Units: {p.units:.2f}  \u2502  "
            f"Unrealised P&L: {pnl_colour}{pnl:+,.2f}{Style.RESET_ALL}  {arrow}"
        )
    else:
        print(
            f" POSITION  {Fore.YELLOW}FLAT{Style.RESET_ALL}  \u2502  "
            "Waiting for signal threshold..."
        )

    gate = state.last_gate_result
    if gate is not None and not gate.allowed and broker.position is None:
        print(f" GATES     {Fore.RED}\u26d4 {gate.reason}{Style.RESET_ALL}")

    print(sep)
    cap = broker.capital
    pnl_today = cap - STARTING_CAPITAL
    pct = 100.0 * pnl_today / STARTING_CAPITAL if STARTING_CAPITAL else 0.0
    pnl_colour = Fore.GREEN if pnl_today >= 0 else Fore.RED
    total_trades = state.wins + state.losses
    wr = (state.wins / total_trades * 100.0) if total_trades else 0.0
    print(
        f" TODAY     Capital: \u20b9{cap:,.2f}  \u2502  "
        f"P&L: {pnl_colour}{pnl_today:+,.2f} ({pct:+.2f}%){Style.RESET_ALL}"
    )
    print(
        f"           Trades: {state.trades_today}  \u2502  Wins: {state.wins}  "
        f"\u2502  Losses: {state.losses}  \u2502  Win Rate: {wr:.0f}%"
    )
    print(sep)
