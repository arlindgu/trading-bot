"""Panic-Bot (for laughs): opens a random direction, then panics and flips
to the opposite side the instant price ticks against it by even a tiny
amount -- reactive to any noise at all, extremely high turnover. Genuinely
50/50 on the initial direction like Coinflip, not rigged to lose; the
panic-flipping is just a bad (very twitchy) exit/re-entry heuristic, not a
guaranteed-loss mechanism."""
from __future__ import annotations

import random

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.futures_single_lot import FuturesSingleLotStrategy


class PanicBotStrategy(FuturesSingleLotStrategy):
    def __init__(
        self, symbol: str, margin_pct: float = 0.03, leverage: int = 5,
        panic_threshold: float = 0.001, rng: random.Random | None = None,
    ):
        super().__init__(symbol, margin_pct, leverage, name="panic_bot")
        self.panic_threshold = panic_threshold
        self.rng = rng or random.Random()
        self.entry_price: float | None = None

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        if not self._is_new_bar(bar):
            return
        current = self._current_side(broker)

        if current is None:
            side = self.rng.choice(["long", "short"])
            self._enter(bar, broker, side)
            self.entry_price = bar.close
            return

        if self.entry_price is None:
            # Restart-safety: lot_ids survives via sync_with_broker but
            # entry_price is in-memory only -- seed it from the broker's
            # own record instead of freezing with no reference point.
            self.entry_price = broker.positions[self.lot_ids[-1]].entry_price

        move = (bar.close - self.entry_price) / self.entry_price
        if current == "short":
            move = -move
        if move <= -self.panic_threshold:
            self._exit_all(bar, broker, reason="panic_bot_flipped")
            new_side = "short" if current == "long" else "long"
            self._enter(bar, broker, new_side)
            self.entry_price = bar.close
