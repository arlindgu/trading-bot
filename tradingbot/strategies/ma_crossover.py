"""Long while the fast EMA is above the slow EMA, flat otherwise -- classic
trend-following, the structural opposite of Grid's mean-reversion bet.
"""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import EMA
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class MaCrossoverConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    fast_period: int = 9
    slow_period: int = 21
    position_pct: float | list[float] = 0.12
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class MaCrossoverStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, fast_period: int = 9, slow_period: int = 21, position_pct: float | list[float] = 0.12):
        super().__init__(symbol, position_pct)
        self.fast = EMA(fast_period)
        self.slow = EMA(slow_period)

    @classmethod
    def from_config(cls, cfg: MaCrossoverConfig) -> "MaCrossoverStrategy":
        return cls(cfg.symbol, cfg.fast_period, cfg.slow_period, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        fast_val, slow_val = self.fast.update(bar.close), self.slow.update(bar.close)
        bullish = fast_val > slow_val

        if bullish:
            self._enter(bar, broker, tag=f"ma_crossover:ema{fast_val:.4g}>ema{slow_val:.4g}")
        else:
            self._exit(bar, broker, reason="ma_crossover_exit")
