"""Tick-Momentum: the same idea as the old Relative Momentum, but a
2-bar lookback on 1-minute bars instead of a 10-bar lookback on 1h --
long the instant the last 2 candles net positive, flat the instant they
net negative or flat, flipping on almost every bar instead of riding a
multi-day trend."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class TickMomentumConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    lookback_bars: int = 2
    position_pct: float | list[float] = 0.05
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class TickMomentumStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, lookback_bars: int = 2, position_pct: float | list[float] = 0.05):
        super().__init__(symbol, position_pct)
        self.closes: deque[float] = deque(maxlen=lookback_bars + 1)

    @classmethod
    def from_config(cls, cfg: TickMomentumConfig) -> "TickMomentumStrategy":
        return cls(cfg.symbol, cfg.lookback_bars, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        self.closes.append(bar.close)
        if len(self.closes) < self.closes.maxlen:
            return

        momentum = self.closes[-1] - self.closes[0]
        if momentum > 0:
            self._enter(bar, broker, tag=f"tick_momentum:+{momentum:.4g}")
        else:
            self._exit(bar, broker, reason="tick_momentum_faded")
