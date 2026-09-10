import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.bollinger_pinch import BollingerPinchStrategy


def make_bar(minutes_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_at_or_below_the_lower_band():
    strategy = BollingerPinchStrategy("BTC/USDT", period=3, num_std=1.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    closes = [100, 100, 100, 80]  # sharp drop breaks below the lower band
    for i, c in enumerate(closes):
        strategy.on_bar(make_bar(i, c), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_price_reaches_the_middle_band():
    strategy = BollingerPinchStrategy("BTC/USDT", period=3, num_std=1.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    closes = [100, 100, 100, 80, 100, 100]
    for i, c in enumerate(closes):
        strategy.on_bar(make_bar(i, c), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "bollinger_pinch_exit" for t in broker.trade_log)
