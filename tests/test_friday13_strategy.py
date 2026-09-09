import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.friday13 import Friday13Strategy, is_friday_13th


def make_bar(timestamp, close=100.0):
    return Bar(timestamp, close, close, close, close, 100.0)


def test_is_friday_13th_true_for_a_known_friday_the_13th():
    assert is_friday_13th(pd.Timestamp("2024-09-13", tz="UTC"))  # a real Friday the 13th


def test_is_friday_13th_false_for_an_ordinary_friday():
    assert not is_friday_13th(pd.Timestamp("2024-09-20", tz="UTC"))


def test_holds_on_an_ordinary_day():
    strategy = Friday13Strategy("BTC/USDT", position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(pd.Timestamp("2024-09-12", tz="UTC")), broker)

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_closes_out_on_friday_the_13th():
    strategy = Friday13Strategy("BTC/USDT", position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(pd.Timestamp("2024-09-12", tz="UTC")), broker)
    strategy.on_bar(make_bar(pd.Timestamp("2024-09-13", tz="UTC")), broker)

    assert len(broker.positions) == 0
    assert any(t.get("reason") == "friday_13th_spooked" for t in broker.trade_log)
