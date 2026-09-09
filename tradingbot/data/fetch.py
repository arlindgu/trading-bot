from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import pandas as pd

from tradingbot.config import DATA_DIR
from tradingbot.core.types import Bar

MAX_BARS_PER_CALL = 1000


def _make_exchange(exchange_id: str) -> ccxt.Exchange:
    exchange_class = getattr(ccxt, exchange_id)
    return exchange_class({"enableRateLimit": True})


def fetch_ohlcv(symbol: str, timeframe: str, lookback_days: int, exchange_id: str = "binance") -> pd.DataFrame:
    """Fetch OHLCV history via the exchange's public API (no keys required)
    and page backwards in time until lookback_days is covered."""
    exchange = _make_exchange(exchange_id)
    since = int((datetime.now(timezone.utc) - timedelta(days=lookback_days)).timestamp() * 1000)

    all_rows: list[list] = []
    cursor = since
    while True:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=MAX_BARS_PER_CALL)
        if not batch:
            break
        all_rows.extend(batch)
        last_ts = batch[-1][0]
        if last_ts <= cursor:
            break
        cursor = last_ts + 1
        if len(batch) < MAX_BARS_PER_CALL:
            break
        time.sleep(exchange.rateLimit / 1000)

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    return df


def cache_path(symbol: str, timeframe: str, exchange_id: str) -> Path:
    slug = symbol.replace("/", "_")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return Path(DATA_DIR) / f"{exchange_id}_{slug}_{timeframe}.parquet"


def fetch_and_cache(symbol: str, timeframe: str, lookback_days: int, exchange_id: str = "binance") -> Path:
    df = fetch_ohlcv(symbol, timeframe, lookback_days, exchange_id)
    path = cache_path(symbol, timeframe, exchange_id)
    df.to_parquet(path, index=False)
    return path


def load_cached(symbol: str, timeframe: str, exchange_id: str = "binance") -> pd.DataFrame:
    path = cache_path(symbol, timeframe, exchange_id)
    if not path.exists():
        raise FileNotFoundError(f"No cached data at {path}. Run cli/fetch_data.py first.")
    return pd.read_parquet(path)


def fetch_recent(symbol: str, timeframe: str, bars: int, exchange_id: str = "binance") -> pd.DataFrame:
    """Fetch the most recent `bars` candles, for live/paper trading."""
    exchange = _make_exchange(exchange_id)
    batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=bars)
    df = pd.DataFrame(batch, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    return df


def fetch_latest_bars(
    symbol_timeframes: set[tuple[str, str]], exchange_id: str = "binance", bars: int = 5
) -> dict[tuple[str, str], Bar]:
    """Fetch the latest bar for each unique (symbol, timeframe) pair once --
    used by cli/spot_fleet.py and cli/futures_fleet.py to fetch each symbol
    exactly once per poll cycle and share the result across every account
    trading that symbol, instead of one redundant fetch per account (this
    endpoint is public/unauthenticated, so the dedup is safe regardless of
    which real account each broker is trading under)."""
    exchange = _make_exchange(exchange_id)
    result: dict[tuple[str, str], Bar] = {}
    for symbol, timeframe in symbol_timeframes:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=bars)
        if not batch:
            continue
        row = batch[-1]
        result[(symbol, timeframe)] = Bar(
            pd.to_datetime(row[0], unit="ms", utc=True), row[1], row[2], row[3], row[4], row[5]
        )
    return result
