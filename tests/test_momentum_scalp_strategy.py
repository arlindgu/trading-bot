import itertools

import pandas as pd

from tradingbot.core.types import Bar
from tradingbot.strategies.momentum_scalp import MomentumScalpStrategy


class _StubPosition:
    def __init__(self, symbol, side, entry_price):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price


class _StubBroker:
    def __init__(self, cash: float = 1000.0):
        self.cash = cash
        self.positions: dict[str, _StubPosition] = {}
        self.opens: list[tuple] = []
        self.closes: list[str] = []
        self._lot_counter = itertools.count(1)

    def equity(self, marks):
        return self.cash

    def open_position(self, symbol, side, leverage, margin, timestamp, tp_pct=None, sl_pct=None, strategy="coinflip"):
        lot_id = f"{symbol}-{next(self._lot_counter)}"
        self.positions[lot_id] = _StubPosition(symbol, side, 0.0)
        self.opens.append((symbol, side, leverage))
        return lot_id

    def close_position(self, lot_id, timestamp, reason="exit"):
        self.positions.pop(lot_id, None)
        self.closes.append(reason)
        return 0.0


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_goes_long_on_positive_momentum():
    strategy = MomentumScalpStrategy("BTC/USDT", lookback_bars=3)
    broker = _StubBroker()

    for i, close in enumerate([100, 102, 105, 110]):
        strategy.on_bar(make_bar(i, close), broker)

    assert broker.opens[-1][1] == "long"


def test_flips_to_short_on_negative_momentum():
    strategy = MomentumScalpStrategy("BTC/USDT", lookback_bars=3)
    broker = _StubBroker()

    for i, close in enumerate([100, 102, 105, 110, 100, 90, 80]):
        strategy.on_bar(make_bar(i, close), broker)

    assert broker.opens[-1][1] == "short"
    assert "momentum_scalp_flip" in broker.closes
