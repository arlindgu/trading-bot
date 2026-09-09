import itertools

import pandas as pd

from tradingbot.core.types import Bar
from tradingbot.strategies.rsi_scalp import RsiScalpStrategy


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


def test_enters_long_when_oversold():
    strategy = RsiScalpStrategy("BTC/USDT", period=3, oversold=30.0, overbought=70.0)
    broker = _StubBroker()

    for i, close in enumerate([100, 90, 80, 70, 60, 50]):
        strategy.on_bar(make_bar(i, close), broker)

    assert any(side == "long" for _, side, _ in broker.opens)


def test_enters_short_when_overbought():
    strategy = RsiScalpStrategy("BTC/USDT", period=3, oversold=30.0, overbought=70.0)
    broker = _StubBroker()

    for i, close in enumerate([100, 110, 120, 130, 140, 150]):
        strategy.on_bar(make_bar(i, close), broker)

    assert any(side == "short" for _, side, _ in broker.opens)


def test_exits_once_rsi_crosses_back_through_50():
    strategy = RsiScalpStrategy("BTC/USDT", period=3, oversold=30.0, overbought=70.0)
    broker = _StubBroker()

    # A steady downtrend (RSI pinned near 0) then a sharp bounce that
    # carries RSI back through 50, triggering the exit.
    closes = [100, 90, 80, 70, 60, 50, 65, 80]
    for i, close in enumerate(closes):
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == 0
    assert "rsi_scalp_exit" in broker.closes
