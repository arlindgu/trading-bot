import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.volume_pulse import VolumePulseStrategy


def make_bar(minutes_offset, open_, close, volume):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, open_, max(open_, close), min(open_, close), close, volume)


def test_enters_on_a_green_volume_thrust():
    strategy = VolumePulseStrategy("BTC/USDT", volume_period=3, spike_multiplier=1.2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i in range(3):
        strategy.on_bar(make_bar(i, 100, 100, 100), broker)
    strategy.on_bar(make_bar(3, 100, 105, 500), broker)  # green candle, volume way above average

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_volume_normalizes():
    strategy = VolumePulseStrategy("BTC/USDT", volume_period=3, spike_multiplier=1.2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i in range(3):
        strategy.on_bar(make_bar(i, 100, 100, 100), broker)
    strategy.on_bar(make_bar(3, 100, 105, 500), broker)
    assert len(broker.positions) > 0

    strategy.on_bar(make_bar(4, 105, 105, 50), broker)  # volume drops well under average

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "volume_pulse_normalized" for t in broker.trade_log)
