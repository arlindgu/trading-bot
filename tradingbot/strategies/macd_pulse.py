"""MACD-Pulse: the same crossover idea as the old MACD Momentum, but a
3/8/3 MACD on 1-minute bars instead of the standard 12/26/9 on 1h -- fast
enough to cross back and forth many times an hour instead of a couple
times a month."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import MACD
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class MacdPulseConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    fast_period: int = 3
    slow_period: int = 8
    signal_period: int = 3
    position_pct: float | list[float] = 0.05
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class MacdPulseStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, fast_period: int = 3, slow_period: int = 8, signal_period: int = 3, position_pct: float | list[float] = 0.05):
        super().__init__(symbol, position_pct)
        self.macd = MACD(fast_period, slow_period, signal_period)

    @classmethod
    def from_config(cls, cfg: MacdPulseConfig) -> "MacdPulseStrategy":
        return cls(cfg.symbol, cfg.fast_period, cfg.slow_period, cfg.signal_period, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        macd, signal = self.macd.update(bar.close)
        if macd is None:
            return

        if macd > signal:
            self._enter(bar, broker, tag=f"macd_pulse:macd{macd:.4g}>sig{signal:.4g}")
        else:
            self._exit(bar, broker, reason="macd_pulse_bearish_cross")
