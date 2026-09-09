"""Enter long on a volatility breakout -- close moves more than
`atr_multiplier` ATRs above its recent rolling mean -- then ride it with a
trailing stop that follows the highest close seen since entry, exiting
once price falls `atr_multiplier` ATRs below that peak."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import ATR, RollingMean
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class AtrBreakoutConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    mean_period: int = 20
    atr_period: int = 14
    atr_multiplier: float = 2.0
    position_pct: float = 0.12
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class AtrBreakoutStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, mean_period: int = 20, atr_period: int = 14, atr_multiplier: float = 2.0, position_pct: float = 0.12):
        super().__init__(symbol, position_pct)
        self.mean = RollingMean(mean_period)
        self.atr = ATR(atr_period)
        self.atr_multiplier = atr_multiplier
        self.trailing_peak: float | None = None  # highest close since entry

    @classmethod
    def from_config(cls, cfg: AtrBreakoutConfig) -> "AtrBreakoutStrategy":
        return cls(cfg.symbol, cfg.mean_period, cfg.atr_period, cfg.atr_multiplier, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        mean = self.mean.update(bar.close)
        atr = self.atr.update(bar.high, bar.low, bar.close)
        if mean is None:
            return

        if self.lot_id is not None:
            # trailing_peak lives only in memory (like GridStrategy's slot
            # state) -- after a restart it's None even though a position is
            # open, so seed it from the current bar instead of crashing.
            self.trailing_peak = bar.close if self.trailing_peak is None else max(self.trailing_peak, bar.close)
            if bar.close <= self.trailing_peak - self.atr_multiplier * atr:
                self._exit(bar, broker, reason="atr_trailing_stop")
                self.trailing_peak = None
            return

        if bar.close > mean + self.atr_multiplier * atr:
            self._enter(bar, broker, tag=f"atr_breakout:close>{mean:.4g}+{self.atr_multiplier}xATR")
            if self.lot_id is not None:
                self.trailing_peak = bar.close
