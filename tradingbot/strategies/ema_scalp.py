"""EMA-Scalp: 1-minute fast/slow EMA cross on futures, always in a
position -- long while the fast EMA is above the slow one, short while
below -- flipping direction the instant the cross reverses instead of
going flat in between."""
from __future__ import annotations

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.futures_single_lot import FuturesSingleLotStrategy
from tradingbot.strategies.indicators import EMA


class EmaScalpStrategy(FuturesSingleLotStrategy):
    def __init__(self, symbol: str, margin_pct: float = 0.03, leverage: int = 3, fast_period: int = 5, slow_period: int = 13):
        super().__init__(symbol, margin_pct, leverage, name="ema_scalp")
        self.fast = EMA(fast_period)
        self.slow = EMA(slow_period)

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        if not self._is_new_bar(bar):
            return
        fast_val, slow_val = self.fast.update(bar.close), self.slow.update(bar.close)
        desired = "long" if fast_val > slow_val else "short"

        current = self._current_side(broker)
        if current == desired:
            return
        if current is not None:
            self._exit_all(bar, broker, reason="ema_scalp_flip")
        self._enter(bar, broker, desired)
