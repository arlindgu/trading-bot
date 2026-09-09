import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.rsi_reversion import RsiReversionStrategy


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_after_a_sustained_decline_pushes_rsi_below_oversold():
    strategy = RsiReversionStrategy("BTC/USDT", period=3, oversold=30.0, exit_above=60.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, close in enumerate([100, 90, 80, 70, 60, 50]):
        strategy.on_bar(make_bar(i, close), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_rsi_recovers_above_the_exit_threshold():
    strategy = RsiReversionStrategy("BTC/USDT", period=3, oversold=30.0, exit_above=60.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    closes = [100, 90, 80, 70, 60, 50, 65, 80, 95, 110]
    for i, close in enumerate(closes):
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "rsi_exit" for t in broker.trade_log)
