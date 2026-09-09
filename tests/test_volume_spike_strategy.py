import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.volume_spike import VolumeSpikeStrategy


def make_bar(hours_offset, open_, close, volume):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, open_, max(open_, close), min(open_, close), close, volume)


def test_enters_on_a_volume_thrust_up():
    strategy = VolumeSpikeStrategy("BTC/USDT", volume_period=3, spike_multiplier=2.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    bars = [(100, 100, 50), (100, 100, 50), (100, 100, 50), (100, 110, 300)]
    for i, (o, c, v) in enumerate(bars):
        strategy.on_bar(make_bar(i, o, c, v), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_does_not_enter_on_a_volume_thrust_down():
    strategy = VolumeSpikeStrategy("BTC/USDT", volume_period=3, spike_multiplier=2.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    bars = [(100, 100, 50), (100, 100, 50), (100, 100, 50), (100, 90, 300)]  # spike, but close < open
    for i, (o, c, v) in enumerate(bars):
        strategy.on_bar(make_bar(i, o, c, v), broker)

    assert len(broker.positions) == 0


def test_exits_once_volume_falls_back_below_average():
    strategy = VolumeSpikeStrategy("BTC/USDT", volume_period=3, spike_multiplier=2.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    bars = [(100, 100, 50), (100, 100, 50), (100, 100, 50), (100, 110, 300), (110, 111, 10)]
    for i, (o, c, v) in enumerate(bars):
        strategy.on_bar(make_bar(i, o, c, v), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "volume_normalized" for t in broker.trade_log)
