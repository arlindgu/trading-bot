import itertools

import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.raidboss import RaidBossFuturesStrategy, RaidBossSpotStrategy


class _StubPosition:
    def __init__(self, symbol, side, entry_price):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price


class _StubFuturesBroker:
    def __init__(self, cash: float = 1000.0):
        self.cash = cash
        self.positions: dict[str, _StubPosition] = {}
        self.opens: list[tuple] = []
        self.closes: list[str] = []
        self._lot_counter = itertools.count(1)

    def equity(self, marks):
        return self.cash

    def open_position(self, symbol, side, leverage, margin, timestamp, tp_pct=None, sl_pct=None, strategy="raidboss"):
        lot_id = f"{symbol}-{next(self._lot_counter)}"
        self.positions[lot_id] = _StubPosition(symbol, side, 100.0)
        self.opens.append((symbol, side, leverage, strategy))
        return lot_id

    def close_position(self, lot_id, timestamp, reason="exit"):
        self.positions.pop(lot_id, None)
        self.closes.append(reason)
        return 0.0


class _FixedRng:
    """Every method returns a value fed from a fixed queue, so a test can
    force a specific mood/side/leverage roll instead of depending on real
    randomness. `choice` calls (side, then leverage, ...) drain `choice_queue`
    in order, falling back to the first candidate once it's empty."""

    def __init__(self, choices_queue=None, choice_queue=None, uniform_value=0.1):
        self.choices_queue = list(choices_queue or [])
        self.choice_queue = list(choice_queue or [])
        self.uniform_value = uniform_value

    def choices(self, population, weights):
        return [self.choices_queue.pop(0)]

    def choice(self, seq):
        return self.choice_queue.pop(0) if self.choice_queue else seq[0]

    def uniform(self, a, b):
        return self.uniform_value


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_futures_hodl_does_nothing():
    rng = _FixedRng(choices_queue=["hodl"])
    strategy = RaidBossFuturesStrategy("BTC/USDT:USDT", rng=rng)
    broker = _StubFuturesBroker()

    strategy.on_bar(make_bar(0, 100.0), broker)

    assert broker.opens == []


def test_futures_yolo_opens_with_high_leverage():
    rng = _FixedRng(choices_queue=["yolo"], choice_queue=["long"])
    strategy = RaidBossFuturesStrategy("BTC/USDT:USDT", rng=rng)
    broker = _StubFuturesBroker()

    strategy.on_bar(make_bar(0, 100.0), broker)

    assert len(broker.opens) == 1
    symbol, side, leverage, tag = broker.opens[0]
    assert side == "long"
    assert leverage >= 20


def test_futures_rage_quit_closes_everything():
    rng = _FixedRng(choices_queue=["yolo", "rage_quit"], choice_queue=["long"])
    strategy = RaidBossFuturesStrategy("BTC/USDT:USDT", rng=rng)
    broker = _StubFuturesBroker()

    strategy.on_bar(make_bar(0, 100.0), broker)
    strategy.on_bar(make_bar(1, 100.0), broker)

    assert broker.closes == ["raidboss_rage_quit"]
    assert broker.positions == {}


def test_futures_flip_closes_then_opens_opposite_side():
    rng = _FixedRng(choices_queue=["yolo", "flip"], choice_queue=["long"])
    strategy = RaidBossFuturesStrategy("BTC/USDT:USDT", rng=rng)
    broker = _StubFuturesBroker()

    strategy.on_bar(make_bar(0, 100.0), broker)  # opens long
    strategy.on_bar(make_bar(1, 100.0), broker)  # flip -> close, reopen short

    assert broker.closes == ["raidboss_flip"]
    assert broker.opens[-1][1] == "short"


def test_spot_hodl_does_not_buy():
    rng = _FixedRng(choices_queue=["hodl"])
    strategy = RaidBossSpotStrategy("BTC/USDT", rng=rng)
    broker = PaperBroker(cash=1000.0, fee_pct=0.001, slippage_pct=0.0005)

    strategy.on_bar(make_bar(0, 100.0), broker)

    assert broker.positions == {}


def test_spot_yolo_commits_a_large_chunk_of_equity():
    rng = _FixedRng(choices_queue=["yolo"], uniform_value=0.5)
    strategy = RaidBossSpotStrategy("BTC/USDT", rng=rng)
    broker = PaperBroker(cash=1000.0, fee_pct=0.001, slippage_pct=0.0005)

    strategy.on_bar(make_bar(0, 100.0), broker)

    assert len(broker.positions) == 1
    position = next(iter(broker.positions.values()))
    assert position.size * 100.0 > 400.0  # roughly half of equity, not a nibble
