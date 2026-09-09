"""Primzahl-Trader (for laughs): only holds a long position on days whose
day-of-month is a prime number, flat on every composite day."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for d in range(2, int(n**0.5) + 1):
        if n % d == 0:
            return False
    return True


@dataclass
class PrimeNumberConfig:
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


class PrimeNumberStrategy(SingleLotStrategy):
    @classmethod
    def from_config(cls, cfg: PrimeNumberConfig) -> "PrimeNumberStrategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        dt = bar.timestamp.to_pydatetime() if hasattr(bar.timestamp, "to_pydatetime") else bar.timestamp
        if is_prime(dt.day):
            self._enter(bar, broker, tag=f"prime_number:day{dt.day}")
        else:
            self._exit(bar, broker, reason="not_a_prime_day")
