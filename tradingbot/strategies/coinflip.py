"""Coinflip strategy -- for laughs. Each new candle, flip a coin for
long/short and a coin for leverage; while a position is open, flip a coin
each new candle whether to close it. No signal, no edge, purely random --
a benchmark for "what does doing nothing smarter than chance look like".

Uses FuturesBroker (real long/short + leverage via Binance Futures Demo
Trading), not PaperBroker/GridStrategy's spot model -- this needs shorting
and leverage, which a spot ledger can't represent.
"""
from __future__ import annotations

import random

from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.base import Strategy


class CoinflipStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        leverage_choices: list[int],
        margin_pct: float,
        rng: random.Random | None = None,
    ):
        self.symbol = symbol
        self.leverage_choices = leverage_choices
        self.margin_pct = margin_pct
        self.rng = rng or random.Random()
        self._last_bar_timestamp = None

    def on_bar(self, bar: Bar, broker: FuturesBroker) -> None:
        # Only decide once per candle -- we poll faster than the timeframe,
        # so the same still-forming candle is seen on several polls.
        if bar.timestamp == self._last_bar_timestamp:
            return
        self._last_bar_timestamp = bar.timestamp

        if self.symbol in broker.positions:
            if self.rng.choice([True, False]):
                broker.close_position(self.symbol, bar.timestamp)

        if self.symbol not in broker.positions:
            equity = broker.equity({self.symbol: bar.close})
            margin = equity * self.margin_pct
            side = self.rng.choice(["long", "short"])
            leverage = self.rng.choice(self.leverage_choices)
            broker.open_position(self.symbol, side, leverage, margin, bar.timestamp)
