"""Bollinger-Pinch: the same mean-reversion idea as the old Bollinger
Reversion, but a tight 10-bar/1-std band on 1-minute bars instead of a
20-bar/2-std band on 1h -- a band that narrow gets tagged by ordinary
1m wiggle constantly instead of only during a real dip."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import BollingerBands
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class BollingerPinchConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    period: int = 10
    num_std: float = 1.0
    position_pct: float | list[float] = 0.05
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class BollingerPinchStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, period: int = 10, num_std: float = 1.0, position_pct: float | list[float] = 0.05):
        super().__init__(symbol, position_pct)
        self.bands = BollingerBands(period, num_std)

    @classmethod
    def from_config(cls, cfg: BollingerPinchConfig) -> "BollingerPinchStrategy":
        return cls(cfg.symbol, cfg.period, cfg.num_std, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        lower, mid, _upper = self.bands.update(bar.close)
        if lower is None:
            return

        if bar.close <= lower:
            self._enter(bar, broker, tag=f"bollinger_pinch:close<={lower:.4g}")
        elif bar.close >= mid:
            self._exit(bar, broker, reason="bollinger_pinch_exit")
