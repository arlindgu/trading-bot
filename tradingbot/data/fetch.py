from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import ccxt
import pandas as pd

from tradingbot.config import DATA_DIR

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
