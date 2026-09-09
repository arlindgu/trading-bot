"""Adrenaline-Junkie (for laughs): can't commit to a direction -- flips
side on literally every new candle (long, short, long, short...) at a
random leverage each time, never sits still. The futures cousin of
Zappelphilipp, minus the coinflip: this one alternates deterministically,
not randomly, so it's always exactly 50% long-time / 50% short-time over
any stretch, not left to chance."""
from __future__ import annotations

import random

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.futures_single_lot import FuturesSingleLotStrategy


class AdrenalineJunkieStrategy(FuturesSingleLotStrategy):
    def __init__(
        self, symbol: str, margin_pct: float | list[float] = 0.03, leverage_choices: list[int] | None = None,
        rng: random.Random | None = None,
    ):
        super().__init__(symbol, margin_pct, leverage=1, name="adrenaline_junkie")
        self.leverage_choices = leverage_choices or [1, 2, 3, 5, 10]
        self.rng = rng or random.Random()
        self._next_side = "long"

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        if not self._is_new_bar(bar):
            return
        if self.lot_ids:
            self._exit_all(bar, broker, reason="adrenaline_junkie_flip")
        self.leverage = self.rng.choice(self.leverage_choices)
        self._enter(bar, broker, self._next_side)
        self._next_side = "short" if self._next_side == "long" else "long"
