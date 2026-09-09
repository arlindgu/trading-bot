"""Shared long/short, single-direction-at-a-time futures mechanics for
strategies that aren't Coinflip (its own fully-random shape with
independent per-lot TP/SL and several simultaneous opposite-side lots).
A strategy here decides a side (long, short, or flat) each bar and calls
`_enter`/`_exit_all`/`_current_side`; entering, exiting, and surviving a
restart are handled once, here.
"""
from __future__ import annotations

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.base import Strategy


class FuturesSingleLotStrategy(Strategy):
    def __init__(self, symbol: str, margin_pct: float, leverage: int, name: str, max_concurrent: int = 1):
        self.symbol = symbol
        self.margin_pct = margin_pct
        self.leverage = leverage
        self.name = name  # tag prefix, e.g. "rsi_scalp" -- keeps this off Coinflip's dashboard columns
        self.max_concurrent = max_concurrent
        self.lot_ids: list[str] = []
        self._last_bar_timestamp = None

    @property
    def lot_id(self) -> str | None:
        return self.lot_ids[-1] if self.lot_ids else None

    def _is_new_bar(self, bar: Bar) -> bool:
        if bar.timestamp == self._last_bar_timestamp:
            return False
        self._last_bar_timestamp = bar.timestamp
        return True

    def sync_with_broker(self, broker: FuturesBroker) -> None:
        self.lot_ids = [lot_id for lot_id, p in broker.positions.items() if p.symbol == self.symbol]

    def _current_side(self, broker: FuturesBroker) -> str | None:
        if not self.lot_ids:
            return None
        position = broker.positions.get(self.lot_ids[-1])
        return position.side if position else None

    def _enter(self, bar: Bar, broker: FuturesBroker, side: str) -> None:
        if len(self.lot_ids) >= self.max_concurrent:
            return
        equity = broker.equity({self.symbol: bar.close})
        margin = equity * self.margin_pct
        lot_id = broker.open_position(self.symbol, side, self.leverage, margin, bar.timestamp, strategy=self.name)
        if lot_id is not None:
            self.lot_ids.append(lot_id)

    def _exit_all(self, bar: Bar, broker: FuturesBroker, reason: str) -> None:
        still_open = []
        for lot_id in self.lot_ids:
            pnl = broker.close_position(lot_id, bar.timestamp, reason=reason)
            if pnl is None:  # close failed -- retry next bar
                still_open.append(lot_id)
        self.lot_ids = still_open
