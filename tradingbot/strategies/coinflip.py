"""Coinflip strategy -- for laughs. Each new candle, flip a coin for
long/short, a coin for leverage, and a coin for a take-profit/stop-loss
band; while any position is open, close each one once price crosses its
own threshold, otherwise flip a much smaller "impatience" coin each candle
to close it early anyway. No signal, no edge, purely random entries -- but
no longer purely random exits either: TP/SL give it bounded, visible risk
management instead of a 50/50 close every single candle (which almost
never gave a position time to move before this change). A benchmark for
"what does doing nothing smarter than chance look like, but not reckless
about when to leave".

Several lots on the same symbol can be open at once (up to
`max_concurrent`) instead of being capped at one -- each coinflipped
independently (its own side/leverage/tp/sl), so this symbol can end up
long and short at the same time across different lots.

Uses FuturesBroker (real long/short + leverage via Binance Futures Demo
Trading), not PaperBroker/GridStrategy's spot model -- this needs shorting
and leverage, which a spot ledger can't represent.
"""
from __future__ import annotations

import random

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.base import Strategy

TP_CHOICES = [0.02, 0.03, 0.05]  # take-profit, as a fraction of entry price
SL_CHOICES = [0.01, 0.02, 0.03]  # stop-loss, as a fraction of entry price
IMPATIENCE_EXIT_PCT = 0.15  # chance per candle to close early even if neither TP nor SL has hit


class CoinflipStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        leverage_choices: list[int],
        margin_pct: float,
        max_concurrent: int = 3,
        rng: random.Random | None = None,
    ):
        self.symbol = symbol
        self.leverage_choices = leverage_choices
        self.margin_pct = margin_pct
        self.max_concurrent = max_concurrent
        self.rng = rng or random.Random()
        self._last_bar_timestamp = None

    def _exit_reason(self, position, mark_price: float) -> str | None:
        move = (mark_price - position.entry_price) / position.entry_price
        if position.side == "short":
            move = -move
        if position.tp_pct is not None and move >= position.tp_pct:
            return "take_profit"
        if position.sl_pct is not None and move <= -position.sl_pct:
            return "stop_loss"
        if self.rng.random() < IMPATIENCE_EXIT_PCT:
            return "impatience"
        return None

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        # Only decide once per candle -- we poll faster than the timeframe,
        # so the same still-forming candle is seen on several polls.
        if bar.timestamp == self._last_bar_timestamp:
            return
        self._last_bar_timestamp = bar.timestamp

        open_lots = [lot_id for lot_id, p in broker.positions.items() if p.symbol == self.symbol]
        for lot_id in open_lots:
            position = broker.positions[lot_id]
            reason = self._exit_reason(position, bar.close)
            if reason is not None:
                broker.close_position(lot_id, bar.timestamp, reason=reason)

        open_count = sum(1 for p in broker.positions.values() if p.symbol == self.symbol)
        if open_count < self.max_concurrent:
            equity = broker.equity({self.symbol: bar.close})
            margin = equity * self.margin_pct
            side = self.rng.choice(["long", "short"])
            leverage = self.rng.choice(self.leverage_choices)
            tp_pct = self.rng.choice(TP_CHOICES)
            sl_pct = self.rng.choice(SL_CHOICES)
            broker.open_position(self.symbol, side, leverage, margin, bar.timestamp, tp_pct=tp_pct, sl_pct=sl_pct)
