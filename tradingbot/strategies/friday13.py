"""Freitag-13-Trader (for laughs): superstitiously closes out and stays in
cash on any Friday the 13th, holds a long position every other day."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


def is_friday_13th(timestamp) -> bool:
    dt = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
    return dt.weekday() == 4 and dt.day == 13


@dataclass
class Friday13Config:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    position_pct: float = 0.15
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class Friday13Strategy(SingleLotStrategy):
    @classmethod
    def from_config(cls, cfg: Friday13Config) -> "Friday13Strategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        if is_friday_13th(bar.timestamp):
            self._exit(bar, broker, reason="friday_13th_spooked")
        else:
            self._enter(bar, broker, tag="friday13:holding")
