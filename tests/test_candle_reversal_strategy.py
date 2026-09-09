import itertools

import pandas as pd

from tradingbot.core.types import Bar
from tradingbot.strategies.candle_reversal import CandleReversalStrategy


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


def make_bar(hours_offset, open_, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, open_, max(open_, close), min(open_, close), close, 100.0)


def test_goes_long_after_a_red_candle():
    strategy = CandleReversalStrategy("BTC/USDT")
    broker = _StubBroker()

    strategy.on_bar(make_bar(0, 100, 90), broker)  # red

    assert broker.opens == [("BTC/USDT", "long", 3)]


def test_goes_short_after_a_green_candle():
    strategy = CandleReversalStrategy("BTC/USDT")
    broker = _StubBroker()

    strategy.on_bar(make_bar(0, 90, 100), broker)  # green

    assert broker.opens == [("BTC/USDT", "short", 3)]


def test_holds_through_candle_2_and_closes_on_candle_3_then_reenters():
    strategy = CandleReversalStrategy("BTC/USDT")
    broker = _StubBroker()

    strategy.on_bar(make_bar(0, 100, 90), broker)  # candle 1: red -> long
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(1, 90, 95), broker)  # candle 2: hold, no action
    assert len(broker.closes) == 0
    assert len(broker.opens) == 1

    strategy.on_bar(make_bar(2, 95, 80), broker)  # candle 3: close old, then fade itself (red -> long)
    assert broker.closes == ["candle_reversal_exit"]
    assert broker.opens[-1] == ("BTC/USDT", "long", 3)
    assert len(broker.positions) == 1
