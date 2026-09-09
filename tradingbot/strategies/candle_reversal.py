"""Candle-Reversal: fades the candle it just saw -- long after a red
candle (close < open), short after a green one -- and holds for exactly
one more full candle before closing, right as the 3rd candle begins. That
3rd candle immediately becomes the next cycle's "candle 1" (it fades
itself the same way), so this runs continuously: enter, hold, close+
reenter, hold, close+reenter..."""
from __future__ import annotations

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.futures_single_lot import FuturesSingleLotStrategy


class CandleReversalStrategy(FuturesSingleLotStrategy):
    def __init__(self, symbol: str, margin_pct: float | list[float] = 0.03, leverage: int = 3):
        super().__init__(symbol, margin_pct, leverage, name="candle_reversal")
        self.bars_since_entry: int | None = None  # None = flat

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        if not self._is_new_bar(bar):
            return

        if self.bars_since_entry is not None:
            self.bars_since_entry += 1
            if self.bars_since_entry >= 2:  # this bar IS candle 3 -- close now, before anything else
                self._exit_all(bar, broker, reason="candle_reversal_exit")
                self.bars_since_entry = None

        if self.bars_since_entry is None:
            side = "long" if bar.close < bar.open else "short"
            self._enter(bar, broker, side)
            self.bars_since_entry = 0
