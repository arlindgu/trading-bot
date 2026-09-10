"""ATR-Flicker: the same volatility-breakout idea as the old ATR Breakout,
but reacting to single-bar volatility bursts on 1-minute bars instead of a
multi-bar trend above a rolling mean -- enters the instant one candle's
true range blows past its recent ATR to the upside (green), exits the
instant a burst that size shows up to the downside (red) instead of
riding a trailing stop for days."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import ATR
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class AtrFlickerConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    atr_period: int = 7
    burst_multiplier: float = 1.2
    position_pct: float | list[float] = 0.05
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class AtrFlickerStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, atr_period: int = 7, burst_multiplier: float = 1.2, position_pct: float | list[float] = 0.05):
        super().__init__(symbol, position_pct)
        self.atr = ATR(atr_period)
        self.burst_multiplier = burst_multiplier

    @classmethod
    def from_config(cls, cfg: AtrFlickerConfig) -> "AtrFlickerStrategy":
        return cls(cfg.symbol, cfg.atr_period, cfg.burst_multiplier, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        prior_atr = self.atr.avg
        atr = self.atr.update(bar.high, bar.low, bar.close)
        if prior_atr is None:
            return

        is_burst = (bar.high - bar.low) >= self.burst_multiplier * prior_atr
        if not is_burst:
            return

        if bar.close > bar.open:
            self._enter(bar, broker, tag=f"atr_flicker:range{bar.high - bar.low:.4g}>=atr{atr:.4g}")
        elif bar.close < bar.open:
            self._exit(bar, broker, reason="atr_flicker_burst_down")
