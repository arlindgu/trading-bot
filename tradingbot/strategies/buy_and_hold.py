"""Buys once on the first bar it sees, then holds forever. No exit logic
at all -- a pure passive benchmark to check whether any of the other
strategies actually beat just buying and sitting still."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class BuyAndHoldConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    position_pct: float = 0.9  # no rotation ever frees this cash back up, so commit most of it up front
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class BuyAndHoldStrategy(SingleLotStrategy):
    @classmethod
    def from_config(cls, cfg: BuyAndHoldConfig) -> "BuyAndHoldStrategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        self._enter(bar, broker, tag="buy_and_hold:holding")
