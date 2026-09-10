import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.macd_pulse import MacdPulseStrategy


def make_bar(minutes_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_on_a_bullish_crossover():
    strategy = MacdPulseStrategy("BTC/USDT", fast_period=3, slow_period=8, signal_period=3, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    closes = [100] * 8 + [110] * 3  # flat, then a push up
    for i, c in enumerate(closes):
        strategy.on_bar(make_bar(i, c), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_on_a_bearish_crossover():
    strategy = MacdPulseStrategy("BTC/USDT", fast_period=3, slow_period=8, signal_period=3, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    closes = [100] * 8 + [110] * 3 + [90] * 4  # push up, then a drop
    for i, c in enumerate(closes):
        strategy.on_bar(make_bar(i, c), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "macd_pulse_bearish_cross" for t in broker.trade_log)
