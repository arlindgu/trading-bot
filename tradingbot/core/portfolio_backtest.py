from __future__ import annotations

import pandas as pd

from tradingbot.core.backtest import BacktestResult
from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.base import Strategy


def run_portfolio_backtest(
    strategies: dict[str, Strategy],
    ohlcv_by_symbol: dict[str, pd.DataFrame],
    broker: PaperBroker,
) -> BacktestResult:
    """Run several single-symbol strategies against ONE shared broker/cash
    pool, stepping through time bar-by-bar across all symbols together so
    they compete for the same capital -- unlike backtesting each in
    isolation with its own capital.

    Only the overlapping time range across all symbols is simulated: a
    symbol listed later than the others bounds the whole portfolio's start.
    Symbols are processed in dict order within each timestamp, so on a bar
    where cash is scarce, earlier symbols get first claim on it.
    """
    indexed = {sym: df.set_index("timestamp").sort_index() for sym, df in ohlcv_by_symbol.items()}
    common_index = None
    for df in indexed.values():
        common_index = df.index if common_index is None else common_index.intersection(df.index)
    common_index = common_index.sort_values()
    if len(common_index) == 0:
        raise ValueError("no overlapping timestamps across the given symbols' history")

    symbols = list(strategies.keys())
    iterators = [indexed[sym].loc[common_index].itertuples(index=False) for sym in symbols]

    equity_rows = []
    for ts, *rows in zip(common_index, *iterators):
        latest_close = {}
        for symbol, row in zip(symbols, rows):
            bar = Bar(ts, row.open, row.high, row.low, row.close, row.volume)
            strategies[symbol].on_bar(bar, broker)
            latest_close[symbol] = bar.close
        equity_rows.append({"timestamp": ts, "equity": broker.equity(latest_close)})

    equity_curve = pd.DataFrame(equity_rows)
    return BacktestResult(broker, equity_curve)
