"""
End-of-day HTML report generator.

Reads the SQLite database for a given trading date and produces a
fully self-contained dark-themed HTML report saved to reports/YYYY-MM-DD.html.
Only external resource is Chart.js via CDN.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import STARTING_CAPITAL
from storage.database import Database

log = logging.getLogger(__name__)

_REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"

INDICATOR_COLS = [
    ("rsi_vote", "RSI"),
    ("williams_r_vote", "W%R"),
    ("stochastic_vote", "STOCH"),
    ("cci_vote", "CCI"),
    ("mfi_vote", "MFI"),
    ("vwap_vote", "VWAP"),
    ("orb_vote", "ORB"),
    ("pivot_vote", "PVOT"),
    ("bb_vote", "BB%B"),
    ("keltner_vote", "KELT"),
    ("psar_vote", "PSAR"),
    ("atr_trend_vote", "ATR"),
    ("pattern_vote", "PATT"),
    ("volume_vote", "VOL"),
]


def generate_report(db: Database, trade_date: str) -> Path:
    """Write an HTML report for `trade_date` and return the output path."""
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _REPORTS_DIR / f"{trade_date}.html"

    trades = [dict(r) for r in db.fetch_trades_for(trade_date)]
    caps = [dict(r) for r in db.fetch_capital_log_for(trade_date)]
    ind_rows = [dict(r) for r in db.fetch_indicator_log_for(trade_date)]

    summary = _compute_summary(trades, caps)
    risk = _compute_risk_metrics(trades)
    accuracy = _compute_indicator_accuracy(trades, ind_rows)

    equity_points = [
        {"t": r["timestamp"], "y": float(r["capital_after"])} for r in caps
    ]

    html = _render_html(
        trade_date=trade_date,
        summary=summary,
        risk=risk,
        equity_points=equity_points,
        trades=trades,
        ind_rows=ind_rows,
        accuracy=accuracy,
    )
    out_path.write_text(html, encoding="utf-8")
    log.info("HTML report written to %s", out_path)
    return out_path


# ─────────────────────────────────────────────────────────────────────
# Analytics
# ─────────────────────────────────────────────────────────────────────
def _compute_summary(trades: List[dict], caps: List[dict]) -> Dict:
    closed = [t for t in trades if t.get("exit_time") is not None]
    pnls = [float(t.get("realised_pnl") or 0.0) for t in closed]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]
    ending_capital = (
        float(caps[-1]["capital_after"]) if caps else STARTING_CAPITAL
    )
    peak = STARTING_CAPITAL
    max_dd = 0.0
    for r in caps:
        v = float(r["capital_after"])
        peak = max(peak, v)
        max_dd = min(max_dd, v - peak)
    net = ending_capital - STARTING_CAPITAL
    return {
        "starting": STARTING_CAPITAL,
        "ending": ending_capital,
        "net_pnl": net,
        "net_pct": (100.0 * net / STARTING_CAPITAL) if STARTING_CAPITAL else 0.0,
        "total_trades": len(closed),
        "winners": len(winners),
        "losers": len(losers),
        "win_rate": (100.0 * len(winners) / len(closed)) if closed else 0.0,
        "best": max(pnls) if pnls else 0.0,
        "worst": min(pnls) if pnls else 0.0,
        "max_drawdown": max_dd,
        "gates_blocked": 0,  # computed from logs externally; 0 if unknown
    }


def _compute_risk_metrics(trades: List[dict]) -> Dict:
    closed = [t for t in trades if t.get("exit_time") is not None]
    if not closed:
        return {
            "avg_hold_min": 0.0,
            "avg_pnl": 0.0,
            "max_wins_streak": 0,
            "max_losses_streak": 0,
            "profit_factor": 0.0,
            "recovery_factor": 0.0,
        }
    # Hold time
    holds: List[float] = []
    for t in closed:
        try:
            a = datetime.fromisoformat(t["entry_time"])
            b = datetime.fromisoformat(t["exit_time"])
            holds.append((b - a).total_seconds() / 60.0)
        except Exception:  # noqa: BLE001
            pass
    pnls = [float(t.get("realised_pnl") or 0.0) for t in closed]
    gross_p = sum(p for p in pnls if p > 0)
    gross_l = abs(sum(p for p in pnls if p < 0))
    pf = (gross_p / gross_l) if gross_l > 0 else (float("inf") if gross_p > 0 else 0.0)
    # streaks
    cur_w = cur_l = max_w = max_l = 0
    for p in pnls:
        if p > 0:
            cur_w += 1; cur_l = 0
            max_w = max(max_w, cur_w)
        elif p < 0:
            cur_l += 1; cur_w = 0
            max_l = max(max_l, cur_l)
        else:
            cur_w = cur_l = 0
    # Drawdown using running capital
    running = STARTING_CAPITAL
    peak = running
    max_dd = 0.0
    for p in pnls:
        running += p
        peak = max(peak, running)
        max_dd = min(max_dd, running - peak)
    net = running - STARTING_CAPITAL
    rf = (net / abs(max_dd)) if max_dd < 0 else (float("inf") if net > 0 else 0.0)
    return {
        "avg_hold_min": sum(holds) / len(holds) if holds else 0.0,
        "avg_pnl": sum(pnls) / len(pnls),
        "max_wins_streak": max_w,
        "max_losses_streak": max_l,
        "profit_factor": pf,
        "recovery_factor": rf,
    }


def _compute_indicator_accuracy(
    trades: List[dict], ind_rows: List[dict]
) -> List[Dict]:
    """
    For each indicator, count votes and measure how often the vote direction
    agreed with a profitable trade opened on that candle.
    """
    closed = [t for t in trades if t.get("exit_time") is not None]
    # map entry_time -> pnl sign
    outcomes = {t["entry_time"]: (float(t.get("realised_pnl") or 0.0) > 0) for t in closed}

    stats: Dict[str, Dict[str, int]] = {}
    for col, _label in INDICATOR_COLS:
        stats[col] = {"bull": 0, "bear": 0, "neut": 0, "correct": 0, "incorrect": 0}

    # Counts across all indicator rows
    for row in ind_rows:
        for col, _label in INDICATOR_COLS:
            v = int(row.get(col) or 0)
            s = stats[col]
            if v > 0:
                s["bull"] += 1
            elif v < 0:
                s["bear"] += 1
            else:
                s["neut"] += 1

    # Accuracy over rows matching trade entry timestamps
    ts_index = {r["timestamp"]: r for r in ind_rows}
    for entry_ts, profitable in outcomes.items():
        row = ts_index.get(entry_ts)
        if row is None:
            continue
        direction_long = profitable  # mirror: if trade profited and sign agrees
        for col, _label in INDICATOR_COLS:
            v = int(row.get(col) or 0)
            if v == 0:
                continue
            voted_long = v > 0
            trade_pnl = next(
                (float(t.get("realised_pnl") or 0.0) for t in closed if t["entry_time"] == entry_ts),
                0.0,
            )
            trade_is_long = next(
                (t["direction"] == "LONG" for t in closed if t["entry_time"] == entry_ts),
                True,
            )
            vote_agrees_with_trade = voted_long == trade_is_long
            if vote_agrees_with_trade and trade_pnl > 0:
                stats[col]["correct"] += 1
            elif vote_agrees_with_trade and trade_pnl < 0:
                stats[col]["incorrect"] += 1

    out: List[Dict] = []
    for col, label in INDICATOR_COLS:
        s = stats[col]
        total = s["correct"] + s["incorrect"]
        acc = (100.0 * s["correct"] / total) if total else 0.0
        out.append({
            "name": label,
            "bull": s["bull"],
            "bear": s["bear"],
            "neut": s["neut"],
            "correct": s["correct"],
            "incorrect": s["incorrect"],
            "accuracy": acc,
        })
    out.sort(key=lambda r: r["accuracy"], reverse=True)
    return out


# ─────────────────────────────────────────────────────────────────────
# HTML rendering
# ─────────────────────────────────────────────────────────────────────
def _money(x: float) -> str:
    sign = "-" if x < 0 else ""
    return f"{sign}\u20b9{abs(x):,.2f}"


def _cell_colour(v: int) -> str:
    if v > 0:
        return "#14532d"
    if v < 0:
        return "#7f1d1d"
    return "#27272a"


def _render_html(
    *,
    trade_date: str,
    summary: Dict,
    risk: Dict,
    equity_points: List[Dict],
    trades: List[Dict],
    ind_rows: List[Dict],
    accuracy: List[Dict],
) -> str:
    net_colour = "#22c55e" if summary["net_pnl"] >= 0 else "#ef4444"

    # Trade rows
    trow_html: List[str] = []
    for i, t in enumerate(trades, 1):
        pnl = float(t.get("realised_pnl") or 0.0)
        bg = "#14532d" if pnl > 0 else ("#7f1d1d" if pnl < 0 else "#27272a")
        trow_html.append(
            f"<tr><td>{i}</td><td>{t.get('entry_time','')}</td>"
            f"<td>{t.get('exit_time','') or '-'}</td>"
            f"<td>{t['direction']}</td>"
            f"<td>{float(t['entry_price']):,.2f}</td>"
            f"<td>{(float(t['exit_price']) if t.get('exit_price') is not None else 0):,.2f}</td>"
            f"<td>{float(t['units']):.2f}</td>"
            f"<td style='background:{bg}'>{_money(pnl)}</td>"
            f"<td>{t.get('exit_reason','') or '-'}</td>"
            f"<td>{t.get('score_at_entry', 0)}</td>"
            f"<td>{t.get('mode','')}</td></tr>"
        )

    # Heatmap rows
    heat_head = (
        "<tr><th>Time</th>" + "".join(f"<th>{lbl}</th>" for _, lbl in INDICATOR_COLS)
        + "<th>Total</th></tr>"
    )
    heat_rows: List[str] = []
    for r in ind_rows:
        cells = [
            f"<td style='background:{_cell_colour(int(r.get(col) or 0))}'>"
            f"{int(r.get(col) or 0):+d}</td>"
            for col, _ in INDICATOR_COLS
        ]
        total = int(r.get("total_score") or 0)
        bg = _cell_colour(1 if total > 0 else (-1 if total < 0 else 0))
        heat_rows.append(
            f"<tr><td>{r['timestamp'][-8:]}</td>{''.join(cells)}"
            f"<td style='background:{bg}'><b>{total:+d}</b></td></tr>"
        )

    # Accuracy rows
    acc_rows = "".join(
        f"<tr><td>{a['name']}</td><td>{a['bull']}</td><td>{a['bear']}</td>"
        f"<td>{a['neut']}</td><td>{a['correct']}</td><td>{a['incorrect']}</td>"
        f"<td>{a['accuracy']:.1f}%</td></tr>"
        for a in accuracy
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Nifty 50 Paper Bot Report — {trade_date}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  body {{ background:#0a0a0a; color:#e5e5e5; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; margin: 0; padding: 24px; }}
  h1, h2 {{ color:#fafafa; margin-bottom: 8px; }}
  .card {{ background:#18181b; border:1px solid #27272a; border-radius:10px; padding:16px; margin-bottom:20px; }}
  .grid {{ display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px; }}
  .kv {{ background:#0f172a; padding:10px 12px; border-radius:8px; }}
  .kv b {{ display:block; font-size:11px; color:#a1a1aa; text-transform: uppercase; letter-spacing:0.04em; }}
  .kv span {{ font-size:18px; }}
  table {{ width:100%; border-collapse: collapse; font-size:12px; }}
  th, td {{ padding:6px 8px; border:1px solid #27272a; text-align:right; white-space: nowrap; }}
  th {{ background:#1f2937; color:#f8fafc; }}
  td:first-child, th:first-child {{ text-align:left; }}
  .net {{ color:{net_colour}; font-weight:bold; }}
  .scroll {{ max-height: 500px; overflow:auto; }}
</style>
</head>
<body>
<h1>Nifty 50 Paper Bot — {trade_date}</h1>

<div class="card">
  <h2>Summary</h2>
  <div class="grid">
    <div class="kv"><b>Session</b><span>09:15 – 15:30 IST</span></div>
    <div class="kv"><b>Starting Capital</b><span>{_money(summary['starting'])}</span></div>
    <div class="kv"><b>Ending Capital</b><span>{_money(summary['ending'])}</span></div>
    <div class="kv"><b>Net P&amp;L</b><span class="net">{_money(summary['net_pnl'])} ({summary['net_pct']:+.2f}%)</span></div>
    <div class="kv"><b>Total Trades</b><span>{summary['total_trades']}</span></div>
    <div class="kv"><b>Winners</b><span>{summary['winners']}</span></div>
    <div class="kv"><b>Losers</b><span>{summary['losers']}</span></div>
    <div class="kv"><b>Win Rate</b><span>{summary['win_rate']:.1f}%</span></div>
    <div class="kv"><b>Best Trade</b><span>{_money(summary['best'])}</span></div>
    <div class="kv"><b>Worst Trade</b><span>{_money(summary['worst'])}</span></div>
    <div class="kv"><b>Max Drawdown</b><span>{_money(summary['max_drawdown'])}</span></div>
    <div class="kv"><b>Gates Blocked</b><span>{summary['gates_blocked']}</span></div>
  </div>
</div>

<div class="card">
  <h2>Equity Curve</h2>
  <canvas id="equity" height="140"></canvas>
</div>

<div class="card">
  <h2>Trade Log</h2>
  <div class="scroll">
  <table>
    <thead><tr>
      <th>#</th><th>Entry</th><th>Exit</th><th>Dir</th><th>Entry ₹</th>
      <th>Exit ₹</th><th>Units</th><th>P&amp;L</th><th>Reason</th>
      <th>Score</th><th>Mode</th>
    </tr></thead>
    <tbody>{''.join(trow_html) or '<tr><td colspan=11>No trades</td></tr>'}</tbody>
  </table>
  </div>
</div>

<div class="card">
  <h2>Indicator Vote Heatmap</h2>
  <div class="scroll">
  <table>
    <thead>{heat_head}</thead>
    <tbody>{''.join(heat_rows) or '<tr><td colspan=16>No indicator data</td></tr>'}</tbody>
  </table>
  </div>
</div>

<div class="card">
  <h2>Indicator Accuracy</h2>
  <table>
    <thead><tr><th>Name</th><th>Bull</th><th>Bear</th><th>Neut</th>
      <th>Correct</th><th>Incorrect</th><th>Accuracy</th></tr></thead>
    <tbody>{acc_rows}</tbody>
  </table>
</div>

<div class="card">
  <h2>Risk Metrics</h2>
  <div class="grid">
    <div class="kv"><b>Avg Hold (min)</b><span>{risk['avg_hold_min']:.1f}</span></div>
    <div class="kv"><b>Avg P&amp;L / Trade</b><span>{_money(risk['avg_pnl'])}</span></div>
    <div class="kv"><b>Max Win Streak</b><span>{risk['max_wins_streak']}</span></div>
    <div class="kv"><b>Max Loss Streak</b><span>{risk['max_losses_streak']}</span></div>
    <div class="kv"><b>Profit Factor</b><span>{risk['profit_factor']:.2f}</span></div>
    <div class="kv"><b>Recovery Factor</b><span>{risk['recovery_factor']:.2f}</span></div>
  </div>
</div>

<script>
const equityData = {json.dumps(equity_points)};
const ctx = document.getElementById('equity').getContext('2d');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: equityData.map(p => p.t.slice(-8)),
    datasets: [
      {{
        label: 'Capital ₹',
        data: equityData.map(p => p.y),
        borderColor: '#22c55e',
        backgroundColor: 'rgba(34,197,94,0.1)',
        pointRadius: 0,
        tension: 0.2,
        fill: true,
      }},
      {{
        label: 'Start ₹10,000',
        data: equityData.map(_ => {STARTING_CAPITAL}),
        borderColor: '#64748b',
        borderDash: [6, 4],
        pointRadius: 0,
        fill: false,
      }}
    ]
  }},
  options: {{
    plugins: {{ legend: {{ labels: {{ color: '#e5e5e5' }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#9ca3af' }}, grid: {{ color: '#27272a' }} }},
      y: {{ ticks: {{ color: '#9ca3af' }}, grid: {{ color: '#27272a' }} }}
    }}
  }}
}});
</script>
</body>
</html>
"""
