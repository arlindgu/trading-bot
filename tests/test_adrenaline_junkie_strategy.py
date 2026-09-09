import itertools

import pandas as pd

from tradingbot.core.types import Bar
from tradingbot.strategies.adrenaline_junkie import AdrenalineJunkieStrategy


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


class _FixedChoiceRng:
    def __init__(self, choices):
        self.queue = list(choices)

    def choice(self, seq):
        return self.queue.pop(0)


def make_bar(hours_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_alternates_side_every_single_bar():
    rng = _FixedChoiceRng([5, 3, 1])
    strategy = AdrenalineJunkieStrategy("BTC/USDT", leverage_choices=[1, 3, 5], rng=rng)
    broker = _StubBroker()

    for i in range(3):
        strategy.on_bar(make_bar(i), broker)

    sides = [side for _, side, _ in broker.opens]
    assert sides == ["long", "short", "long"]
    assert len(broker.closes) == 2  # closed before bar 2 and bar 3's re-entries
