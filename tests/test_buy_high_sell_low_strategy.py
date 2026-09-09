import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.buy_high_sell_low import BuyHighSellLowStrategy


def make_bar(hours_offset, high, low, close, open_=None):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, open_ if open_ is not None else close, high, low, close, 100.0)


def test_chases_a_fresh_high():
    strategy = BuyHighSellLowStrategy("BTC/USDT", period=3, position_pct=0.2)
    broker = PaperBroker(cash=1000)

    bars = [(100, 95, 98), (101, 96, 99), (102, 97, 100), (110, 100, 110)]
    for i, (h, l, c) in enumerate(bars):
        strategy.on_bar(make_bar(i, h, l, c), broker)

    assert len(broker.positions) == 1


def test_panic_sells_everything_on_the_next_red_candle():
    strategy = BuyHighSellLowStrategy("BTC/USDT", period=3, position_pct=0.2)
    broker = PaperBroker(cash=1000)

    bars = [(100, 95, 98), (101, 96, 99), (102, 97, 100), (110, 100, 110), (110, 95, 96)]
    for i, (h, l, c) in enumerate(bars):
        strategy.on_bar(make_bar(i, h, l, c, open_=h if i == 4 else None), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "panic_sold_the_dip" for t in broker.trade_log)
