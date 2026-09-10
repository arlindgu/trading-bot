import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.sekundenschlaf_bot import SekundenschlafBotStrategy


class _FixedRandint:
    def __init__(self, values):
        self.queue = list(values)

    def randint(self, low, high):
        return self.queue.pop(0)


def make_bar(minutes_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_naps_for_the_rolled_length_then_wakes_and_closes():
    rng = _FixedRandint([2])
    strategy = SekundenschlafBotStrategy("BTC/USDT", position_pct=0.2, rng=rng)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)  # opens, rolls a 2-bar nap
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(1), broker)  # still napping
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(2), broker)  # still napping (1 bar left -> 0)
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(3), broker)  # wakes up, closes
    assert len(broker.positions) == 0


def test_rolls_a_fresh_nap_on_the_next_round():
    rng = _FixedRandint([1, 1])
    strategy = SekundenschlafBotStrategy("BTC/USDT", position_pct=0.2, rng=rng)
    broker = PaperBroker(cash=1000)

    for i in range(4):
        strategy.on_bar(make_bar(i), broker)

    buys = [t for t in broker.trade_log if t["side"] == "buy"]
    assert len(buys) == 2
