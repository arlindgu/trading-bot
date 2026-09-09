import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.bollinger_reversion import BollingerReversionStrategy


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_on_a_sharp_dip_below_the_lower_band():
    strategy = BollingerReversionStrategy("BTC/USDT", period=4, num_std=1.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, close in enumerate([100, 100, 100, 100, 60]):
        strategy.on_bar(make_bar(i, close), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_price_reverts_back_to_the_middle_band():
    strategy = BollingerReversionStrategy("BTC/USDT", period=4, num_std=1.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    closes = [100, 100, 100, 100, 60, 90, 95, 98, 100]
    for i, close in enumerate(closes):
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "bollinger_reversion_exit" for t in broker.trade_log)
