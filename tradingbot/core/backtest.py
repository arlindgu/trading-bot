from __future__ import annotations

import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.base import Strategy


class BacktestResult:
    def __init__(self, broker: PaperBroker, equity_curve: pd.DataFrame):
        self.broker = broker
        self.equity_curve = equity_curve

    @property
    def starting_equity(self) -> float:
        return self.equity_curve["equity"].iloc[0]

    @property
    def total_return_pct(self) -> float:
        eq = self.equity_curve["equity"]
        return (eq.iloc[-1] / eq.iloc[0] - 1) * 100

    @property
    def max_drawdown_pct(self) -> float:
        eq = self.equity_curve["equity"]
        running_max = eq.cummax()
        return ((eq - running_max) / running_max).min() * 100

    @property
    def closed_trades(self) -> list[dict]:
        return [t for t in self.broker.trade_log if t["side"] == "sell"]

    @property
    def win_rate_pct(self) -> float:
        closed = self.closed_trades
        if not closed:
            return 0.0
        wins = sum(1 for t in closed if t["pnl"] > 0)
        return wins / len(closed) * 100

    def summary(self) -> dict:
        return {
            "starting_equity": round(self.starting_equity, 2),
            "final_equity": round(self.equity_curve["equity"].iloc[-1], 2),
            "total_return_pct": round(self.total_return_pct, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "num_trades": len(self.closed_trades),
            "win_rate_pct": round(self.win_rate_pct, 2),
            "open_positions": len(self.broker.positions),
        }


def run_backtest(strategy: Strategy, symbol: str, ohlcv: pd.DataFrame, broker: PaperBroker) -> BacktestResult:
    """Feed bars to `strategy.on_bar` one at a time and mark equity after
    each bar. The engine never contains trading logic itself -- it only
    executes what the strategy decides and keeps the books -- so any
    Strategy subclass backtests exactly the way it runs in paper trading.
    """
    equity_rows = []
    for row in ohlcv.itertuples(index=False):
        bar = Bar(row.timestamp, row.open, row.high, row.low, row.close, row.volume)
        strategy.on_bar(bar, broker)
        equity_rows.append({"timestamp": bar.timestamp, "equity": broker.equity({symbol: bar.close})})

    equity_curve = pd.DataFrame(equity_rows)
    return BacktestResult(broker, equity_curve)
