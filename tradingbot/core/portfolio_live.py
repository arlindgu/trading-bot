"""Paper-trading loop for several strategies sharing ONE cash pool, backed by
the SQLite dashboard database (tradingbot/core/db.py). Polls each symbol's
most recent bar on the same cadence and feeds them to a shared broker,
mirroring cli/portfolio_backtest.py's shared-cash semantics for live/paper
trading. No exchange API key with order permissions is used or required --
this never touches real money or places real orders.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from tradingbot.core import db
from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.data.fetch import fetch_recent
from tradingbot.strategies.base import Strategy

BARS_TO_FETCH = 5  # only the latest closed bar is acted on; a few extra as a sanity margin


def run_once(
    strategies: dict[str, Strategy],
    timeframe: str,
    exchange: str,
    broker: PaperBroker,
    session: Session,
    account: str,
) -> float:
    latest_close: dict[str, float] = {}
    for symbol, strategy in strategies.items():
        recent = fetch_recent(symbol, timeframe, BARS_TO_FETCH, exchange)
        if recent.empty:
            print(f"[skip] {symbol}: no data returned")
            continue
        row = recent.iloc[-1]
        bar = Bar(row["timestamp"], row["open"], row["high"], row["low"], row["close"], row["volume"])
        strategy.on_bar(bar, broker)
        latest_close[symbol] = bar.close
        print(f"[{bar.timestamp}] {symbol} close={bar.close:.6g}")

    timestamp = datetime.now(timezone.utc).isoformat()
    equity = broker.equity(latest_close)

    db.append_portfolio_snapshot(session, account, timestamp, equity, broker.cash)
    for symbol, mark_price in latest_close.items():
        realized = sum(t["pnl"] for t in broker.trade_log if t["symbol"] == symbol and t["side"] == "sell")
        unrealized = sum(p.size * (mark_price - p.entry_price) for p in broker.positions.values() if p.symbol == symbol)
        db.append_symbol_snapshot(session, account, symbol, timestamp, mark_price, realized, unrealized)

    open_by_symbol: dict[str, int] = {}
    for position in broker.positions.values():
        open_by_symbol[position.symbol] = open_by_symbol.get(position.symbol, 0) + 1
    print(f"  equity={equity:.2f} cash={broker.cash:.2f} open_positions={len(broker.positions)} {open_by_symbol}")

    return equity


def run_loop(
    strategies: dict[str, Strategy],
    timeframe: str,
    exchange: str,
    broker: PaperBroker,
    session: Session,
    account: str,
    poll_seconds: int = 300,
) -> None:
    print(
        f"Starting portfolio paper trading loop for {', '.join(strategies)} "
        f"({exchange}, {timeframe}), polling every {poll_seconds}s. Ctrl+C to stop."
    )
    while True:
        run_once(strategies, timeframe, exchange, broker, session, account)
        db.save_broker(session, account, broker)
        time.sleep(poll_seconds)
