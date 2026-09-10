import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.wackelkontakt_bot import WackelkontaktBotStrategy, flicker_score


def make_bar(minutes_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(minutes=minutes_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_enters_when_the_hash_score_clears_the_threshold():
    bar = make_bar(0)
    score = flicker_score(bar)
    strategy = WackelkontaktBotStrategy("BTC/USDT", threshold=score, position_pct=0.2)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(bar, broker)

    assert len(broker.positions) == 1


def test_stays_flat_when_the_hash_score_misses_the_threshold():
    bar = make_bar(0)
    score = flicker_score(bar)
    strategy = WackelkontaktBotStrategy("BTC/USDT", threshold=score + 0.01, position_pct=0.2)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(bar, broker)

    assert len(broker.positions) == 0


def test_is_deterministic_for_the_same_bar():
    bar = make_bar(0)
    assert flicker_score(bar) == flicker_score(bar)
