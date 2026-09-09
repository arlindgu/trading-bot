import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.zodiac import ZodiacStrategy, zodiac_sign


def make_bar(timestamp, close=100.0):
    return Bar(timestamp, close, close, close, close, 100.0)


def test_zodiac_sign_matches_known_dates():
    assert zodiac_sign(3, 25) == "aries"
    assert zodiac_sign(1, 1) == "capricorn"
    assert zodiac_sign(12, 25) == "capricorn"
    assert zodiac_sign(10, 25) == "scorpio"


def test_enters_on_a_bullish_sign():
    strategy = ZodiacStrategy("BTC/USDT", position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(pd.Timestamp("2024-03-25", tz="UTC")), broker)  # aries -- bullish

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_on_a_bearish_sign():
    strategy = ZodiacStrategy("BTC/USDT", position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(pd.Timestamp("2024-03-25", tz="UTC")), broker)  # aries -- bullish, enters
    strategy.on_bar(make_bar(pd.Timestamp("2024-10-25", tz="UTC")), broker)  # scorpio -- bearish, exits

    assert len(broker.positions) == 0
