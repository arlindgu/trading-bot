"""Shared long/flat, multi-lot-per-symbol mechanics used by every real and
joke strategy except Grid (its own slot-indexed multi-lot shape) and
Coinflip (futures, its own FuturesPosition shape + independent per-lot
TP/SL). A strategy here can hold several concurrent lots on its symbol (up
to `max_concurrent`), accumulated over separate candles while its entry
signal stays true, and closes all of them together once its exit signal
fires -- only the entry/exit *decision* differs between subclasses, so
that decision is the only thing each one implements; entering, exiting,
and surviving a restart are identical across all of them and live here
once.
"""
from __future__ import annotations

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.base import Strategy


class SingleLotStrategy(Strategy):
    def __init__(self, symbol: str, position_pct: float, max_concurrent: int = 3):
        self.symbol = symbol
        self.position_pct = position_pct
        self.max_concurrent = max_concurrent
        self.lot_ids: list[str] = []
        self._last_bar_timestamp = None

    @property
    def lot_id(self) -> str | None:
        """Convenience for subclasses that only need "are we holding
        anything at all" -- the most recently opened lot, or None if flat."""
        return self.lot_ids[-1] if self.lot_ids else None

    def _is_new_bar(self, bar: Bar) -> bool:
        """Live/paper polling is much faster than the 1h candle timeframe,
        so the same still-forming candle is seen on many consecutive polls
        -- every subclass must call this first and bail out on a repeat,
        or its indicators get fed the same bar's close/volume repeatedly
        and end up corrupted (over-weighted, double-counted volume, etc).
        Always true in a backtest, where every bar has a unique timestamp.
        """
        if bar.timestamp == self._last_bar_timestamp:
            return False
        self._last_bar_timestamp = bar.timestamp
        return True

    def sync_with_broker(self, broker: PaperBroker) -> None:
        """Restore `lot_ids` after a restart by finding this symbol's open
        lots in the broker's actual positions."""
        self.lot_ids = [lot_id for lot_id, position in broker.positions.items() if position.symbol == self.symbol]

    def _enter(self, bar: Bar, broker: PaperBroker, tag: str) -> None:
        if len(self.lot_ids) >= self.max_concurrent:
            return
        equity = broker.equity({self.symbol: bar.close})
        investment = equity * self.position_pct
        required = investment * (1 + broker.fee_pct + broker.slippage_pct)
        if broker.cash < required:
            return
        size = investment / bar.close
        lot_id = broker.buy(self.symbol, bar.close, size, bar.timestamp, tag=tag)
        if lot_id is not None:
            self.lot_ids.append(lot_id)

    def _exit(self, bar: Bar, broker: PaperBroker, reason: str) -> None:
        """Closes every open lot on this symbol -- the exit signal (e.g. a
        bearish crossover) applies to the whole accumulated position, not
        just the most recent piece of it."""
        still_open = []
        for lot_id in self.lot_ids:
            pnl = broker.sell(lot_id, bar.close, bar.timestamp, reason=reason)
            if pnl is None:  # sell failed (e.g. a live exchange rejected it) -- retry next bar
                still_open.append(lot_id)
        self.lot_ids = still_open
