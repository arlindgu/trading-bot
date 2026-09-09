import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.hash_sentiment import HashSentimentStrategy, sentiment_score


def make_bar(hours_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_sentiment_score_is_deterministic_for_the_same_bar():
    bar = make_bar(0)
    assert sentiment_score(bar) == sentiment_score(bar)


def test_sentiment_score_differs_for_different_bars():
    assert sentiment_score(make_bar(0, 100.0)) != sentiment_score(make_bar(0, 100.01))


def test_enters_when_score_is_at_or_above_a_low_threshold():
    strategy = HashSentimentStrategy("BTC/USDT", threshold=0.0, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)  # threshold 0.0 -- any score qualifies

    assert any(p.symbol == "BTC/USDT" for p in broker.positions.values())


def test_stays_flat_when_score_is_below_an_unreachable_threshold():
    strategy = HashSentimentStrategy("BTC/USDT", threshold=1.1, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)  # threshold above the [0,1) range -- never qualifies

    assert len(broker.positions) == 0
