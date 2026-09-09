import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.moon_phase import MoonPhaseStrategy, is_near_full_moon


def make_bar(timestamp, close=100.0):
    return Bar(timestamp, close, close, close, close, 100.0)


def test_is_near_full_moon_matches_a_known_full_moon_date():
    # 2024-01-25 was a real full moon.
    assert is_near_full_moon(pd.Timestamp("2024-01-25", tz="UTC"))


def test_is_near_full_moon_false_for_a_known_new_moon_date():
    # 2024-01-11 was a real new moon.
    assert not is_near_full_moon(pd.Timestamp("2024-01-11", tz="UTC"))


def test_enters_on_a_full_moon_bar():
    strategy = MoonPhaseStrategy("BTC/USDT", position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(pd.Timestamp("2024-01-25", tz="UTC")), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_once_the_moon_wanes():
    strategy = MoonPhaseStrategy("BTC/USDT", position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(pd.Timestamp("2024-01-25", tz="UTC")), broker)
    strategy.on_bar(make_bar(pd.Timestamp("2024-01-11", tz="UTC")), broker)

    assert len(broker.positions) == 0
