import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.atr_breakout import AtrBreakoutStrategy


def make_bar(hours_offset, high, low, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, high, low, close, 100.0)


def test_enters_on_a_volatility_breakout_above_the_recent_mean():
    strategy = AtrBreakoutStrategy("BTC/USDT", mean_period=3, atr_period=3, atr_multiplier=1.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    bars = [(101, 99, 100), (101, 99, 100), (101, 99, 100), (140, 100, 135)]
    for i, (h, l, c) in enumerate(bars):
        strategy.on_bar(make_bar(i, h, l, c), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_trailing_stop_exits_once_price_falls_back_from_the_peak():
    strategy = AtrBreakoutStrategy("BTC/USDT", mean_period=3, atr_period=3, atr_multiplier=1.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    bars = [(101, 99, 100), (101, 99, 100), (101, 99, 100), (140, 100, 135), (150, 145, 148), (100, 95, 98)]
    for i, (h, l, c) in enumerate(bars):
        strategy.on_bar(make_bar(i, h, l, c), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "atr_trailing_stop" for t in broker.trade_log)


def test_survives_a_restart_without_a_trailing_peak_in_memory():
    # sync_with_broker restores lot_id after a restart but not the
    # in-memory trailing_peak -- on_bar must seed it instead of crashing
    # on max(None, bar.close).
    strategy = AtrBreakoutStrategy("BTC/USDT", mean_period=3, atr_period=3, atr_multiplier=1.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    # Warm up the indicators first (flat price, no entry yet).
    for i in range(3):
        strategy.on_bar(make_bar(i, 101, 99, 100), broker)
    assert len(broker.positions) == 0

    # Simulate a restart: a position exists on the broker (e.g. from before
    # the process died) but this fresh-ish strategy instance's
    # trailing_peak was never set.
    broker.buy("BTC/USDT", 100.0, 1.0, "t0", tag="atr_breakout:restored")
    strategy.sync_with_broker(broker)
    assert strategy.lot_id is not None
    assert strategy.trailing_peak is None

    strategy.on_bar(make_bar(3, 101, 99, 100), broker)  # must not raise
    assert strategy.trailing_peak == 100
