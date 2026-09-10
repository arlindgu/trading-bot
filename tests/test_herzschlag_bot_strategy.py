import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.herzschlag_bot import HerzschlagBotStrategy


def make_bar(minutes_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_holds_exactly_one_bar_then_closes_and_reopens():
    strategy = HerzschlagBotStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    for i in range(4):
        strategy.on_bar(make_bar(i), broker)

    assert len(broker.positions) == 1  # always holding exactly one open lot
    buys = [t for t in broker.trade_log if t["side"] == "buy"]
    sells = [t for t in broker.trade_log if t["side"] == "sell"]
    assert len(buys) == 4
    assert len(sells) == 3


def test_never_stacks_beyond_one_lot():
    strategy = HerzschlagBotStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    for i in range(10):
        strategy.on_bar(make_bar(i), broker)

    assert len(broker.positions) == 1
