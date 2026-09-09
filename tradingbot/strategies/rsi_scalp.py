"""RSI-Scalp: 1-minute RSI mean-reversion on futures, so it can actually
short an overbought move instead of only fading longs like the spot
RSI-Reversion strategy. Long when RSI < 20, short when RSI > 80, closes
once RSI crosses back through 50."""
from __future__ import annotations

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.futures_single_lot import FuturesSingleLotStrategy
from tradingbot.strategies.indicators import RSI


class RsiScalpStrategy(FuturesSingleLotStrategy):
    def __init__(
        self, symbol: str, margin_pct: float | list[float] = 0.03, leverage: int = 3,
        period: int = 14, oversold: float = 20.0, overbought: float = 80.0,
    ):
        super().__init__(symbol, margin_pct, leverage, name="rsi_scalp")
        self.rsi = RSI(period)
        self.oversold = oversold
        self.overbought = overbought

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        if not self._is_new_bar(bar):
            return
        rsi = self.rsi.update(bar.close)
        if rsi is None:
            return

        side = self._current_side(broker)
        if side is not None:
            if (side == "long" and rsi >= 50) or (side == "short" and rsi <= 50):
                self._exit_all(bar, broker, reason="rsi_scalp_exit")
            return

        if rsi < self.oversold:
            self._enter(bar, broker, "long")
        elif rsi > self.overbought:
            self._enter(bar, broker, "short")
