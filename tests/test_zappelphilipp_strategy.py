import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.zappelphilipp import ZappelphilippStrategy


class _FixedChoiceRng:
    def __init__(self, choices):
        self.queue = list(choices)

    def choice(self, seq):
        return self.queue.pop(0)


def make_bar(minutes_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_closes_then_reopens_when_the_coinflip_says_yes():
    rng = _FixedChoiceRng([True, True, True])
    strategy = ZappelphilippStrategy("BTC/USDT", position_pct=0.2, rng=rng)
    broker = PaperBroker(cash=1000)

    for i in range(3):
        strategy.on_bar(make_bar(i), broker)

    assert len(broker.positions) == 1
    buys = [t for t in broker.trade_log if t["side"] == "buy"]
    sells = [t for t in broker.trade_log if t["side"] == "sell"]
    assert len(buys) == 3
    assert len(sells) == 2  # closed before each of the 2 re-entries after bar 0


def test_closes_and_stays_flat_when_the_coinflip_says_no():
    rng = _FixedChoiceRng([True, False])
    strategy = ZappelphilippStrategy("BTC/USDT", position_pct=0.2, rng=rng)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)  # coinflip True -- opens
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(1), broker)  # closes, then coinflip False -- stays flat
    assert len(broker.positions) == 0


def test_never_stacks_beyond_one_lot():
    rng = _FixedChoiceRng([True] * 10)
    strategy = ZappelphilippStrategy("BTC/USDT", position_pct=0.2, rng=rng)
    broker = PaperBroker(cash=1000)

    for i in range(10):
        strategy.on_bar(make_bar(i), broker)

    assert len(broker.positions) == 1


def test_does_not_reprocess_the_same_still_forming_candle():
    rng = _FixedChoiceRng([True])
    strategy = ZappelphilippStrategy("BTC/USDT", position_pct=0.2, rng=rng)
    broker = PaperBroker(cash=1000)

    bar = make_bar(0)
    strategy.on_bar(bar, broker)
    strategy.on_bar(bar, broker)  # same timestamp again -- must not touch rng/broker again

    assert len(broker.trade_log) == 1
