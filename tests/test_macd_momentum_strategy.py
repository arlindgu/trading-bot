import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.macd_momentum import MacdMomentumStrategy


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_on_a_sustained_uptrend_bullish_crossover():
    strategy = MacdMomentumStrategy("BTC/USDT", fast_period=2, slow_period=4, signal_period=2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, close in enumerate([100, 105, 112, 120, 130, 142, 155]):
        strategy.on_bar(make_bar(i, close), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_momentum_turns_bearish():
    strategy = MacdMomentumStrategy("BTC/USDT", fast_period=2, slow_period=4, signal_period=2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    closes = [100, 105, 112, 120, 130, 142, 155, 130, 105, 85, 70]
    for i, close in enumerate(closes):
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "macd_bearish_cross" for t in broker.trade_log)
