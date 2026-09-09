import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.relative_momentum import RelativeMomentumStrategy


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_once_return_is_positive_and_accelerating():
    strategy = RelativeMomentumStrategy("BTC/USDT", return_period=2, average_period=3, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    # Each 2-bar return keeps getting bigger -- accelerating momentum.
    closes = [100, 101, 103, 108, 118, 140]
    for i, close in enumerate(closes):
        strategy.on_bar(make_bar(i, close), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_momentum_fades():
    strategy = RelativeMomentumStrategy("BTC/USDT", return_period=2, average_period=3, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    closes = [100, 101, 103, 108, 118, 140, 141, 140, 138]
    for i, close in enumerate(closes):
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "momentum_faded" for t in broker.trade_log)
