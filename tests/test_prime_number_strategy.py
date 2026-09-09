import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.prime_number import PrimeNumberStrategy, is_prime


def make_bar(timestamp, close=100.0):
    return Bar(timestamp, close, close, close, close, 100.0)


def test_is_prime_basic_cases():
    assert not is_prime(1)
    assert is_prime(2)
    assert is_prime(13)
    assert not is_prime(4)
    assert not is_prime(15)


def test_enters_on_a_prime_day_of_month():
    strategy = PrimeNumberStrategy("BTC/USDT", position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(pd.Timestamp("2024-01-13", tz="UTC")), broker)  # 13th, prime

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_exits_on_a_composite_day_of_month():
    strategy = PrimeNumberStrategy("BTC/USDT", position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(pd.Timestamp("2024-01-13", tz="UTC")), broker)  # 13th, prime -- enter
    strategy.on_bar(make_bar(pd.Timestamp("2024-01-14", tz="UTC")), broker)  # 14th, composite -- exit

    assert len(broker.positions) == 0
