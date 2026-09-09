"""Paper/live-trading loop for CoinflipStrategy bots. Mirrors
tradingbot/core/portfolio_live.py's polling structure, but computes
side-aware (long AND short) unrealized PnL -- portfolio_live's calc
assumes a spot, long-only position, which is wrong for a short.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from tradingbot.core import db
from tradingbot.core.futures_broker import FuturesBroker, FuturesPosition
from tradingbot.core.types import Bar
from tradingbot.data.fetch import fetch_recent
from tradingbot.strategies.base import Strategy

BARS_TO_FETCH = 5


def _unrealized_pnl(position: FuturesPosition, mark_price: float) -> float:
    diff = (mark_price - position.entry_price) if position.side == "long" else (position.entry_price - mark_price)
    return diff * position.size


def run_once(
    strategies: dict[str, Strategy],
    timeframe: str,
    exchange: str,
    broker: FuturesBroker,
    session: Session,
    account: str,
    bars: dict[str, Bar] | None = None,
) -> float:
    """`bars`, when given, is a pre-fetched {symbol: Bar} map -- see
    portfolio_live.run_once's docstring; same dedup, used by
    cli/futures_fleet.py."""
    latest_close: dict[str, float] = {}
    for symbol, strategy in strategies.items():
        if bars is not None:
            bar = bars.get(symbol)
            if bar is None:
                print(f"[skip] {symbol}: no data available this cycle")
                continue
        else:
            recent = fetch_recent(symbol, timeframe, BARS_TO_FETCH, exchange)
            if recent.empty:
                print(f"[skip] {symbol}: no data returned")
                continue
            row = recent.iloc[-1]
            bar = Bar(row["timestamp"], row["open"], row["high"], row["low"], row["close"], row["volume"])
        strategy.on_bar(bar, broker)
        latest_close[symbol] = bar.close
        open_lots = [p for p in broker.positions.values() if p.symbol == symbol]
        state = ", ".join(f"{p.side} {p.leverage}x" for p in open_lots) if open_lots else "flat"
        print(f"[{bar.timestamp}] {symbol} close={bar.close:.6g} ({state})")

    timestamp = datetime.now(timezone.utc).isoformat()
    equity = broker.equity(latest_close)

    db.append_portfolio_snapshot(session, account, timestamp, equity, broker.cash)
    for symbol, mark_price in latest_close.items():
        realized = sum(t["pnl"] for t in broker.trade_log if t["symbol"] == symbol and t["pnl"] is not None)
        open_lots = [p for p in broker.positions.values() if p.symbol == symbol]
        unrealized = sum(_unrealized_pnl(p, mark_price) for p in open_lots)
        db.append_symbol_snapshot(session, account, symbol, timestamp, mark_price, realized, unrealized)

    open_by_symbol: dict[str, list[str]] = {}
    for p in broker.positions.values():
        open_by_symbol.setdefault(p.symbol, []).append(f"{p.side} {p.leverage}x")
    print(f"  equity={equity:.2f} cash={broker.cash:.2f} open_positions={len(broker.positions)} {open_by_symbol}")

    return equity


def run_loop(
    strategies: dict[str, Strategy],
    timeframe: str,
    exchange: str,
    broker: FuturesBroker,
    session: Session,
    account: str,
    poll_seconds: int = 300,
) -> None:
    print(
        f"Starting coinflip loop for {', '.join(strategies)} ({exchange}, {timeframe}), "
        f"polling every {poll_seconds}s. Ctrl+C to stop."
    )
    while True:
        run_once(strategies, timeframe, exchange, broker, session, account)
        db.save_broker(session, account, broker)
        time.sleep(poll_seconds)
