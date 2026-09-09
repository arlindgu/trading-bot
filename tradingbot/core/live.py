"""Paper-trading loop: polls recent market data and feeds bars to the
strategy exactly like the backtest engine does, so behavior is identical
between backtest and paper trading. No exchange API key with order
permissions is used or required -- this never touches real money or places
real orders.
"""
from __future__ import annotations

import time
from pathlib import Path

from tradingbot.core.broker import PaperBroker
from tradingbot.core.state import save_broker
from tradingbot.core.types import Bar
from tradingbot.data.fetch import fetch_recent
from tradingbot.strategies.base import Strategy

BARS_TO_FETCH = 5  # only the latest closed bar is acted on; a few extra as a sanity margin


def run_once(strategy: Strategy, symbol: str, timeframe: str, exchange: str, broker: PaperBroker) -> None:
    recent = fetch_recent(symbol, timeframe, BARS_TO_FETCH, exchange)
    if recent.empty:
        print(f"[skip] {symbol}: no data returned")
        return

    row = recent.iloc[-1]
    bar = Bar(row["timestamp"], row["open"], row["high"], row["low"], row["close"], row["volume"])
    strategy.on_bar(bar, broker)
    equity = broker.equity({symbol: bar.close})
    print(
        f"[{bar.timestamp}] {symbol} close={bar.close:.4f} "
        f"equity={equity:.2f} open_positions={len(broker.positions)}"
    )


def run_loop(
    strategy: Strategy,
    symbol: str,
    timeframe: str,
    exchange: str,
    broker: PaperBroker,
    state_path: Path,
    poll_seconds: int = 300,
) -> None:
    print(
        f"Starting paper trading loop for {symbol} ({exchange}, {timeframe}), "
        f"polling every {poll_seconds}s. Ctrl+C to stop."
    )
    while True:
        run_once(strategy, symbol, timeframe, exchange, broker)
        save_broker(state_path, broker)
        time.sleep(poll_seconds)
