# Nifty 50 Paper Trading Bot

An autonomous, production-grade intraday paper trading bot for the Nifty 50
index, driven by the IndStocks real-time WebSocket feed. Fifteen leading
technical indicators are evaluated every minute; a weighted voting system
makes Long / Short / Flat decisions; trades are simulated against ₹10,000
paper capital with realistic slippage and persisted to SQLite.

> **Disclaimer** — this is **paper trading only**. Nothing here is financial
> advice, a recommendation, or a guarantee of profit. You are responsible for
> your own trading decisions.

## Prerequisites

- Python 3.10 or newer
- An active IndStocks account with API access
- Network access to `api.indstocks.com` and `ws-prices.indstocks.com`

## Installation

```bash
git clone <this repo>
cd trading_bot
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Getting an IndStocks API access token

1. Log in to your IndStocks account at <https://indstocks.com>.
2. Navigate to **API settings** and generate a new access token.
3. Paste the token into `.env`:
   ```
   INDSTOCKS_ACCESS_TOKEN=your_token_here
   ```
4. Save the file. The bot will validate the token on startup with a single
   LTP request and fail fast if the token is expired or missing.

## Running the bot

```bash
# Default (balanced mode)
python main.py --mode balanced

# Conservative
python main.py --mode safe

# Aggressive
python main.py --mode aggressive

# Reset today's paper capital to ₹10,000 (wipes today's DB rows)
python main.py --reset

# Generate today's HTML report without trading
python main.py --report
```

The bot refuses to run on NSE holidays or weekends. If the WebSocket drops it
automatically reconnects with exponential backoff (2, 4, 8, 16, 32 s). After
five failed attempts it falls back to REST LTP polling until the feed recovers.

## The 15 indicators

All of these are **leading** indicators — they describe momentum, structure,
volatility, and price action _now_, not confirmed on lag. Every indicator
emits a single vote per 1-minute candle: +1, 0, or –1 (the pattern detector
emits ±2 on strong signals).

### Momentum (5)
| Name | Why leading |
| --- | --- |
| **RSI (7)** | Wilder-smoothed momentum oscillator; flags exhaustion and inflexion points before price confirms. |
| **Williams %R (14)** | Measures close relative to recent high/low; turns ahead of moving averages. |
| **Stochastic (5,3,3)** | Slow %K/%D cross signals acceleration changes within the last 5 bars. |
| **CCI (14)** | Deviation from typical price mean — breaks through ±100 as momentum ignites. |
| **MFI (7)** | RSI + volume; catches divergences between money flow and price early. |

### Volatility (2)
| **Bollinger %B (20, 2σ)** | Position inside the band widens before a breakout. |
| --- | --- |
| **Keltner (20 EMA, 10 ATR, ×2)** | ATR-anchored envelope; detects sustainable trends vs. mean-reversion. |

### Price structure / trend (5)
| **VWAP** | Intraday fair-value reference; reclaims and rejections lead trend changes. |
| --- | --- |
| **Opening Range Breakout** | First-15-minute range break captures the day's directional bias early. |
| **Pivot Points (Classic + Camarilla)** | Prior-day-derived levels where directional moves initiate. |
| **Parabolic SAR** | Flips direction the instant momentum turns. |
| **ATR Trend Confirmation** | ATR(7) vs. SMA(ATR, 20) detects expansion before trend acceleration. |

### Price action (2)
| **Candlestick patterns** | Three-bar formations (engulfing, stars, hammer, marubozu) fire before follow-through. |
| --- | --- |

### Volume (1)
| **Volume spike** | >1.5× rolling average with directional body confirms conviction. |
| --- | --- |

## Scoring system

1. Each candle, every indicator casts its vote.
2. Votes are summed into `total_score` (range ≈ −16 … +16).
3. If `|total_score| >= mode.threshold`, a directional signal is fired
   (long if positive, short if negative).
4. Before a trade is opened, a stack of **hard gates** must pass:
   trading time window, ADX ≥ 20, VIX ≤ 25, daily loss limit, max
   trades/day, per-trade cooldown, and the 3-consecutive-losses
   30-minute pause.
5. Mode thresholds:
   - **Safe:** ≥ 12/15 same-direction, 3 trades/day, 1% SL / 2% TP
   - **Balanced:** ≥ 10/15, 6 trades/day, 1% / 2%
   - **Aggressive:** ≥ 8/15, 10 trades/day, 1.5% / 3%

## Reading the terminal display

The dashboard prints every minute on candle close:

```
─────────────────────────────────────────────────────────────────
 🕐 10:32 IST  │  NIFTY 50: ₹24,187.45  │  Mode: BALANCED
─────────────────────────────────────────────────────────────────
 SCORE   11/15 BULLISH  │  ADX: 28.4 ✓  │  VIX: 14.2 ✓
─────────────────────────────────────────────────────────────────
 RSI:+1  W%R:+1  STOCH:+1  CCI:+1  MFI: 0
 VWAP:+1  ORB:+1  PVOT: 0  BB%B:+1  KELT:+1
 PSAR:+1  ATR:+1  PATT:+1  VOL:-1
─────────────────────────────────────────────────────────────────
 POSITION  LONG @ ₹24,150.00  SL:₹23,909.25  TP:₹24,632.25
           Units: 0.35  │  Unrealised P&L: +13.04  ▲
─────────────────────────────────────────────────────────────────
 TODAY     Capital: ₹10,082.00  │  P&L: +82.00 (+0.82%)
           Trades: 2  │  Wins: 1  │  Losses: 1  │  Win Rate: 50%
─────────────────────────────────────────────────────────────────
```

- **Green** — positive P&L, +1 votes, passed gates, LONG.
- **Red** — negative P&L, –1 votes, failed gates, SHORT.
- **Yellow** — neutral 0 votes, warnings.
- **Cyan** — time, price, labels.

When no position is open and gates are blocking, a `GATES ⛔` line is added
with the blocking reason.

## Reading the HTML report

The end-of-day report is saved to `reports/YYYY-MM-DD.html` and opens in any
browser — no server needed. Sections:

1. **Summary** — starting/ending capital, net P&L, trade counts, win rate,
   best/worst trade, max drawdown.
2. **Equity curve** — Chart.js line chart of capital over time, with a
   reference line at ₹10,000.
3. **Trade log** — every closed trade with P&L colour-coded.
4. **Indicator heatmap** — one row per minute, one column per indicator,
   coloured green/red/grey.
5. **Indicator accuracy** — for each indicator, how often its directional
   vote agreed with a profitable trade.
6. **Risk metrics** — average hold, average P&L, longest win/loss streaks,
   profit factor, recovery factor.

## Project layout

See the top-level `trading_bot/` folder; every subdirectory has a
single responsibility (data, indicators, strategy, execution, storage,
reporting).

## Risk disclaimer

This is an **educational paper-trading simulator**. It is not a broker, does
not place real orders, and makes no claim of accuracy, completeness, or
profitability. Past simulated performance is not indicative of future
results. Trading real capital involves substantial risk of loss. **Use at
your own risk.**
