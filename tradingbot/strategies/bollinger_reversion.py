"""Long when price closes at/below the lower Bollinger band, exit once it
reaches the middle band (the rolling mean) again."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import BollingerBands
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class BollingerReversionConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    period: int = 20
    num_std: float = 2.0
    position_pct: float = 0.12
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class BollingerReversionStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, period: int = 20, num_std: float = 2.0, position_pct: float = 0.12):
        super().__init__(symbol, position_pct)
        self.bands = BollingerBands(period, num_std)

    @classmethod
    def from_config(cls, cfg: BollingerReversionConfig) -> "BollingerReversionStrategy":
        return cls(cfg.symbol, cfg.period, cfg.num_std, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        lower, mid, _upper = self.bands.update(bar.close)
        if lower is None:
            return

        if bar.close <= lower:
            self._enter(bar, broker, tag=f"bollinger_reversion:close<={lower:.4g}")
        elif bar.close >= mid:
            self._exit(bar, broker, reason="bollinger_reversion_exit")
