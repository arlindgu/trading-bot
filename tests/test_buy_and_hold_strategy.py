import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.buy_and_hold import BuyAndHoldStrategy


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_accumulates_lots_up_to_max_concurrent_and_never_sells():
    strategy = BuyAndHoldStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    for i, close in enumerate([100, 50, 10, 200, 5]):  # wild swings shouldn't matter -- it never checks price to exit
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == strategy.max_concurrent
    assert all(t["side"] == "buy" for t in broker.trade_log)


def test_does_not_buy_beyond_max_concurrent():
    strategy = BuyAndHoldStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    for i in range(10):  # far more bars than max_concurrent
        strategy.on_bar(make_bar(i, 100), broker)

    assert len(broker.trade_log) == strategy.max_concurrent
