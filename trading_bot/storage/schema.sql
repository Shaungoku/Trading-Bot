-- SQLite schema for the Nifty 50 paper trading bot.
-- Four tables: trades (one row per closed trade), candles (raw 1-min OHLCV),
-- capital_log (every capital change event), indicator_log (per-candle votes).

CREATE TABLE IF NOT EXISTS trades (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    date              TEXT NOT NULL,
    entry_time        TEXT NOT NULL,
    exit_time         TEXT,
    direction         TEXT NOT NULL,
    entry_price       REAL NOT NULL,
    exit_price        REAL,
    units             REAL NOT NULL,
    sl_price          REAL NOT NULL,
    tp_price          REAL NOT NULL,
    realised_pnl      REAL,
    exit_reason       TEXT,
    mode              TEXT NOT NULL,
    score_at_entry    INTEGER NOT NULL,
    indicator_votes   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date);

CREATE TABLE IF NOT EXISTS candles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    open        REAL NOT NULL,
    high        REAL NOT NULL,
    low         REAL NOT NULL,
    close       REAL NOT NULL,
    volume      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_candles_timestamp ON candles(timestamp);

CREATE TABLE IF NOT EXISTS capital_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    event           TEXT NOT NULL,
    capital_before  REAL NOT NULL,
    capital_after   REAL NOT NULL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_capital_log_timestamp ON capital_log(timestamp);

CREATE TABLE IF NOT EXISTS indicator_log (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp          TEXT NOT NULL,
    rsi_vote           INTEGER NOT NULL,
    williams_r_vote    INTEGER NOT NULL,
    stochastic_vote    INTEGER NOT NULL,
    cci_vote           INTEGER NOT NULL,
    mfi_vote           INTEGER NOT NULL,
    vwap_vote          INTEGER NOT NULL,
    orb_vote           INTEGER NOT NULL,
    pivot_vote         INTEGER NOT NULL,
    bb_vote            INTEGER NOT NULL,
    keltner_vote       INTEGER NOT NULL,
    psar_vote          INTEGER NOT NULL,
    atr_trend_vote     INTEGER NOT NULL,
    pattern_vote       INTEGER NOT NULL,
    volume_vote        INTEGER NOT NULL,
    total_score        INTEGER NOT NULL,
    signal             TEXT NOT NULL,
    adx_value          REAL,
    vix_value          REAL
);

CREATE INDEX IF NOT EXISTS idx_indicator_log_timestamp ON indicator_log(timestamp);
