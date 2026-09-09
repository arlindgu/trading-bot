import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.fomo_bot import FomoBotStrategy


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_only_after_a_pump_past_the_threshold():
    strategy = FomoBotStrategy("BTC/USDT", lookback_bars=3, pump_threshold=0.05, position_pct=0.2)
    broker = PaperBroker(cash=1000)

    for i, close in enumerate([100, 101, 102, 103]):  # +3% over 3 bars -- below the 5% threshold
        strategy.on_bar(make_bar(i, close), broker)
    assert len(broker.positions) == 0

    strategy.on_bar(make_bar(4, 115), broker)  # now +13.6% over the lookback window -- chases it
    assert len(broker.positions) == 1


def test_exits_once_momentum_stalls():
    strategy = FomoBotStrategy("BTC/USDT", lookback_bars=3, pump_threshold=0.05, position_pct=0.2)
    broker = PaperBroker(cash=1000)

    closes = [100, 101, 102, 103, 115, 116, 116, 115]  # pumps, chased, then flattens out
    for i, close in enumerate(closes):
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "fomo_momentum_stalled" for t in broker.trade_log)
