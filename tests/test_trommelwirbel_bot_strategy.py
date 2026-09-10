import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.trommelwirbel_bot import TrommelwirbelBotStrategy


def make_bar(minutes_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_builds_over_three_bars_then_dumps_on_the_fourth():
    strategy = TrommelwirbelBotStrategy("BTC/USDT", build_bars=3, position_pct=0.1)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(1), broker)
    assert len(broker.positions) == 2

    strategy.on_bar(make_bar(2), broker)
    assert len(broker.positions) == 3

    strategy.on_bar(make_bar(3), broker)  # the reveal -- dumps everything
    assert len(broker.positions) == 0
    assert any(t.get("reason") == "trommelwirbel_reveal" for t in broker.trade_log)


def test_starts_a_fresh_roll_right_after_the_reveal():
    strategy = TrommelwirbelBotStrategy("BTC/USDT", build_bars=3, position_pct=0.1)
    broker = PaperBroker(cash=1000)

    for i in range(5):
        strategy.on_bar(make_bar(i), broker)

    assert len(broker.positions) == 1  # bar 4 starts building the next roll
