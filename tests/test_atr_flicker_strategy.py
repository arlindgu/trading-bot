import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.atr_flicker import AtrFlickerStrategy


def make_bar(minutes_offset, open_, high, low, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, open_, high, low, close, 100.0)


def test_enters_on_a_green_burst_bar():
    strategy = AtrFlickerStrategy("BTC/USDT", atr_period=3, burst_multiplier=1.2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    # A few tight, quiet candles to establish a small ATR...
    for i in range(4):
        strategy.on_bar(make_bar(i, 100, 101, 99, 100), broker)
    # ...then a big green candle whose range dwarfs that ATR.
    strategy.on_bar(make_bar(4, 100, 130, 100, 128), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_on_a_red_burst_bar():
    strategy = AtrFlickerStrategy("BTC/USDT", atr_period=3, burst_multiplier=1.2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i in range(4):
        strategy.on_bar(make_bar(i, 100, 101, 99, 100), broker)
    strategy.on_bar(make_bar(4, 100, 130, 100, 128), broker)
    assert len(broker.positions) > 0

    strategy.on_bar(make_bar(5, 128, 128, 90, 91), broker)  # big red burst

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "atr_flicker_burst_down" for t in broker.trade_log)
