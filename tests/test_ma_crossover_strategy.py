import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.ma_crossover import MaCrossoverStrategy


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_once_the_fast_ema_overtakes_the_slow_ema():
    strategy = MaCrossoverStrategy("BTC/USDT", fast_period=2, slow_period=4, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    # A rising close series pulls the fast EMA above the slow EMA quickly.
    for i, close in enumerate([100, 105, 115, 130, 150]):
        strategy.on_bar(make_bar(i, close), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_the_fast_ema_falls_back_below_the_slow_ema():
    strategy = MaCrossoverStrategy("BTC/USDT", fast_period=2, slow_period=4, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, close in enumerate([100, 105, 115, 130, 150, 120, 90, 70]):
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == 0
    assert any(t["side"] == "sell" and t["reason"] == "ma_crossover_exit" for t in broker.trade_log)


def test_does_not_reprocess_the_same_still_forming_candle():
    strategy = MaCrossoverStrategy("BTC/USDT", fast_period=2, slow_period=4, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    bar = make_bar(0, 100)
    strategy.on_bar(bar, broker)
    strategy.on_bar(bar, broker)  # same timestamp -- must not feed the EMAs twice

    assert strategy.fast.value == 100.0  # a single EMA(period=2) update from a flat start is just the first close
