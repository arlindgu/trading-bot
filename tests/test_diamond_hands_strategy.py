import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.diamond_hands import DiamondHandsStrategy


def make_bar(hours_offset, open_, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, open_, max(open_, close), min(open_, close), close, 100.0)


def test_buys_every_red_candle_up_to_max_concurrent():
    strategy = DiamondHandsStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    for i in range(5):  # every bar is red (close < open)
        strategy.on_bar(make_bar(i, 100, 90), broker)

    assert len(broker.positions) == strategy.max_concurrent


def test_never_sells_no_matter_what_happens():
    strategy = DiamondHandsStrategy("BTC/USDT", position_pct=0.2)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(0, 100, 90), broker)  # red -- buys
    strategy.on_bar(make_bar(1, 90, 130), broker)  # big green candle, huge gain -- still no sell
    strategy.on_bar(make_bar(2, 130, 10), broker)  # crash -- still no sell

    assert all(t["side"] == "buy" for t in broker.trade_log)
