import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.pendel_bot import PendelBotStrategy


def make_bar(minutes_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_swings_in_on_even_ticks_and_out_on_odd_ticks():
    strategy = PendelBotStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(1), broker)
    assert len(broker.positions) == 0

    strategy.on_bar(make_bar(2), broker)
    assert len(broker.positions) == 1


def test_trades_on_every_single_new_bar():
    strategy = PendelBotStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    for i in range(6):
        strategy.on_bar(make_bar(i), broker)

    assert len(broker.trade_log) == 6


def test_does_not_reprocess_the_same_still_forming_candle():
    strategy = PendelBotStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    bar = make_bar(0)
    strategy.on_bar(bar, broker)
    strategy.on_bar(bar, broker)

    assert len(broker.trade_log) == 1
