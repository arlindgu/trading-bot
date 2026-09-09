import itertools

import pandas as pd

from tradingbot.core.types import Bar
from tradingbot.strategies.panic_bot import PanicBotStrategy


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
        self.positions[lot_id] = _StubPosition(symbol, side, 100.0)
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


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_opens_a_random_direction_when_flat():
    rng = _FixedChoiceRng(["long"])
    strategy = PanicBotStrategy("BTC/USDT", panic_threshold=0.001, rng=rng)
    broker = _StubBroker()

    strategy.on_bar(make_bar(0, 100.0), broker)

    assert broker.opens == [("BTC/USDT", "long", 5)]


def test_panics_and_flips_on_the_smallest_adverse_move():
    rng = _FixedChoiceRng(["long"])
    strategy = PanicBotStrategy("BTC/USDT", panic_threshold=0.001, rng=rng)
    broker = _StubBroker()

    strategy.on_bar(make_bar(0, 100.0), broker)  # long @ 100
    strategy.on_bar(make_bar(1, 99.5), broker)  # -0.5% move against a long -- past the 0.1% threshold

    assert broker.closes == ["panic_bot_flipped"]
    assert broker.opens[-1] == ("BTC/USDT", "short", 5)


def test_holds_when_price_moves_in_its_favor():
    rng = _FixedChoiceRng(["long"])
    strategy = PanicBotStrategy("BTC/USDT", panic_threshold=0.001, rng=rng)
    broker = _StubBroker()

    strategy.on_bar(make_bar(0, 100.0), broker)  # long @ 100
    strategy.on_bar(make_bar(1, 101.0), broker)  # +1% move -- in its favor, no panic

    assert broker.closes == []
    assert len(broker.opens) == 1
