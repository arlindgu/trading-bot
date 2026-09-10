"""Micro-Donchian: the same breakout idea as the old Donchian Breakout, but
a 5-bar channel on 1-minute bars instead of a 20-bar channel on 1h -- the
channel is narrow enough that ordinary 1m noise breaks it every few
candles instead of waiting days for a real trend."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import Donchian
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class MicroDonchianConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    period: int = 5
    position_pct: float | list[float] = 0.05
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class MicroDonchianStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, period: int = 5, position_pct: float | list[float] = 0.05):
        super().__init__(symbol, position_pct)
        self.donchian = Donchian(period)

    @classmethod
    def from_config(cls, cfg: MicroDonchianConfig) -> "MicroDonchianStrategy":
        return cls(cfg.symbol, cfg.period, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        upper, lower = self.donchian.update(bar.high, bar.low)
        if upper is None:
            return

        if bar.close >= upper:
            self._enter(bar, broker, tag=f"micro_donchian:close>{upper:.4g}")
        elif bar.close <= lower:
            self._exit(bar, broker, reason="micro_donchian_breakdown")
