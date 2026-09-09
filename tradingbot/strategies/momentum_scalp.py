"""Momentum-Scalp: 1-minute, follows the sign of the last N-bar return on
futures -- long on positive momentum, short on negative -- flipping fast
as momentum direction changes."""
from __future__ import annotations

from collections import deque

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.futures_single_lot import FuturesSingleLotStrategy


class MomentumScalpStrategy(FuturesSingleLotStrategy):
    def __init__(self, symbol: str, margin_pct: float = 0.03, leverage: int = 3, lookback_bars: int = 5):
        super().__init__(symbol, margin_pct, leverage, name="momentum_scalp")
        self.closes: deque[float] = deque(maxlen=lookback_bars + 1)

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        if not self._is_new_bar(bar):
            return
        self.closes.append(bar.close)
        if len(self.closes) < self.closes.maxlen:
            return
        momentum = self.closes[-1] - self.closes[0]
        desired = "long" if momentum > 0 else "short" if momentum < 0 else None
        if desired is None:
            return

        current = self._current_side(broker)
        if current == desired:
            return
        if current is not None:
            self._exit_all(bar, broker, reason="momentum_scalp_flip")
        self._enter(bar, broker, desired)
