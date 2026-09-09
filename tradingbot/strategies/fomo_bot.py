"""FOMO-Bot (for laughs): only buys after price has already pumped past a
threshold over the last N candles -- chasing strength on purpose, the
textbook-bad way to trade -- and sells the moment that momentum stalls."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class FomoBotConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    lookback_bars: int = 6
    pump_threshold: float = 0.05
    position_pct: float = 0.15
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class FomoBotStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, lookback_bars: int = 6, pump_threshold: float = 0.05, position_pct: float = 0.15):
        super().__init__(symbol, position_pct)
        self.closes: deque[float] = deque(maxlen=lookback_bars + 1)
        self.pump_threshold = pump_threshold

    @classmethod
    def from_config(cls, cfg: FomoBotConfig) -> "FomoBotStrategy":
        return cls(cfg.symbol, cfg.lookback_bars, cfg.pump_threshold, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        self.closes.append(bar.close)
        if len(self.closes) < self.closes.maxlen:
            return
        pump = (self.closes[-1] - self.closes[0]) / self.closes[0]

        if pump >= self.pump_threshold:
            self._enter(bar, broker, tag=f"fomo_bot:pump{pump:+.1%}")
        elif pump <= 0:
            self._exit(bar, broker, reason="fomo_momentum_stalled")
