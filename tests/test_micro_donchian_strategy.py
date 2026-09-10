import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.micro_donchian import MicroDonchianStrategy


def make_bar(minutes_offset, high, low, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, high, low, close, 100.0)


def test_does_not_enter_on_a_close_that_is_only_inside_its_own_bar():
    strategy = MicroDonchianStrategy("BTC/USDT", period=3, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i in range(3):
        strategy.on_bar(make_bar(i, 100, 100, 100), broker)
    assert len(broker.positions) == 0


def test_enters_on_a_real_breakout_above_the_prior_channel():
    strategy = MicroDonchianStrategy("BTC/USDT", period=3, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, (h, l, c) in enumerate([(100, 95, 98), (101, 96, 99), (102, 97, 100), (110, 100, 110)]):
        strategy.on_bar(make_bar(i, h, l, c), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_on_a_breakdown_below_the_prior_channel():
    strategy = MicroDonchianStrategy("BTC/USDT", period=3, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    bars = [(100, 95, 98), (101, 96, 99), (102, 97, 100), (110, 100, 110), (95, 80, 85)]
    for i, (h, l, c) in enumerate(bars):
        strategy.on_bar(make_bar(i, h, l, c), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "micro_donchian_breakdown" for t in broker.trade_log)
