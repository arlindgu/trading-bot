"""RAIDBOSS -- the wildcard. No signal, no risk plan, no consistency: every
candle it rolls a "mood" from a weighted table and does whatever that mood
says, from nibbling a small position to going all-in with max leverage to
rage-quitting everything it holds. The point is exactly that it's
unpredictable -- a genuine wildcard to compare every disciplined strategy
against, not a rigged-to-lose joke (all moods are real position moves with
real up/downside) and not a rigged-to-win one either.

Futures only (long/short/leverage via FuturesBroker directly -- needs its
own on_bar since "close everything then flip side" doesn't fit
FuturesSingleLotStrategy's one-side-at-a-time contract). No spot variant:
both spot budget pools sit at exactly 5,000/5,000 with zero buffer by
design, and there's no existing tier the user wants shrunk to make room.
"""
from __future__ import annotations

import random

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.base import Strategy

# (mood, weight) -- higher weight = rolled more often. Skewed toward the
# tamer moods so it doesn't churn fees into dust every single candle, but
# every mood is on the table every time.
FUTURES_MOODS = [("nibble", 4), ("yolo", 1), ("double_down", 2), ("flip", 1), ("rage_quit", 2), ("hodl", 4)]


class RaidBossFuturesStrategy(Strategy):
    def __init__(self, symbol: str, margin_pct: float = 0.03, max_concurrent: int = 5, rng: random.Random | None = None):
        self.symbol = symbol
        self.margin_pct = margin_pct
        self.max_concurrent = max_concurrent
        self.rng = rng or random.Random()
        self.lot_ids: list[str] = []
        self._last_bar_timestamp = None

    def _is_new_bar(self, bar: Bar) -> bool:
        if bar.timestamp == self._last_bar_timestamp:
            return False
        self._last_bar_timestamp = bar.timestamp
        return True

    def sync_with_broker(self, broker: FuturesBroker) -> None:
        self.lot_ids = [lot_id for lot_id, p in broker.positions.items() if p.symbol == self.symbol]

    def _close_all(self, bar: Bar, broker: FuturesBroker, reason: str) -> None:
        still_open = []
        for lot_id in self.lot_ids:
            pnl = broker.close_position(lot_id, bar.timestamp, reason=reason)
            if pnl is None:
                still_open.append(lot_id)
        self.lot_ids = still_open

    def _open(self, bar: Bar, broker: FuturesBroker, side: str, margin_pct: float, leverage: int, mood: str) -> None:
        if len(self.lot_ids) >= self.max_concurrent:
            return
        equity = broker.equity({self.symbol: bar.close})
        margin = equity * margin_pct
        lot_id = broker.open_position(self.symbol, side, leverage, margin, bar.timestamp, strategy=f"raidboss_{mood}")
        if lot_id is not None:
            self.lot_ids.append(lot_id)

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        if not self._is_new_bar(bar):
            return

        mood = self.rng.choices(*zip(*FUTURES_MOODS))[0]

        if mood == "hodl":
            return

        if mood == "rage_quit":
            self._close_all(bar, broker, reason="raidboss_rage_quit")
            return

        if mood == "flip":
            last_side = broker.positions[self.lot_ids[-1]].side if self.lot_ids else None
            self._close_all(bar, broker, reason="raidboss_flip")
            new_side = "short" if last_side == "long" else "long"
            self._open(bar, broker, new_side, self.margin_pct * 2, self.rng.choice([5, 10, 20]), mood)
            return

        if mood == "double_down":
            last_side = broker.positions[self.lot_ids[-1]].side if self.lot_ids else self.rng.choice(["long", "short"])
            self._open(bar, broker, last_side, self.margin_pct, self.rng.choice([3, 5, 10]), mood)
            return

        side = self.rng.choice(["long", "short"])
        if mood == "yolo":
            self._open(bar, broker, side, self.margin_pct * 3, self.rng.choice([20, 25, 50]), mood)
        else:  # nibble
            self._open(bar, broker, side, self.margin_pct, self.rng.choice([1, 2, 3]), mood)
