import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.tick_momentum import TickMomentumStrategy


def make_bar(minutes_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_on_positive_two_bar_momentum():
    strategy = TickMomentumStrategy("BTC/USDT", lookback_bars=2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, c in enumerate([100, 101, 105]):
        strategy.on_bar(make_bar(i, c), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_momentum_fades():
    strategy = TickMomentumStrategy("BTC/USDT", lookback_bars=2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, c in enumerate([100, 101, 105, 104, 95]):
        strategy.on_bar(make_bar(i, c), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "tick_momentum_faded" for t in broker.trade_log)
