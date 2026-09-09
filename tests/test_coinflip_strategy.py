import pandas as pd

from tradingbot.core.types import Bar
from tradingbot.strategies.coinflip import CoinflipStrategy


class _StubBroker:
    """Stands in for FuturesBroker without touching a real exchange --
    CoinflipStrategy only ever calls .positions, .equity(), .open_position(),
    .close_position(), all reproduced here minimally."""

    def __init__(self, cash: float = 1000.0):
        self.cash = cash
        self.positions: dict[str, object] = {}
        self.opens: list[tuple] = []
        self.closes: list[str] = []

    def equity(self, marks):
        return self.cash

    def open_position(self, symbol, side, leverage, margin, timestamp):
        self.positions[symbol] = object()
        self.opens.append((symbol, side, leverage, margin))
        return f"{symbol}-lot"

    def close_position(self, symbol, timestamp, reason="coinflip_exit"):
        self.positions.pop(symbol, None)
        self.closes.append(symbol)
        return 0.0


class _FixedChoiceRng:
    """Deterministic stand-in for random.Random -- pops values from a fixed
    queue instead of actually randomizing, so tests aren't flaky."""

    def __init__(self, queue):
        self.queue = list(queue)

    def choice(self, seq):
        return self.queue.pop(0)


def make_bar(hours_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 0.0)


def test_opens_a_position_when_flat():
    rng = _FixedChoiceRng(["long", 5])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1, 5], margin_pct=0.05, rng=rng)
    broker = _StubBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)

    assert broker.opens == [("BTC/USDT", "long", 5, 50.0)]


def test_does_not_reflip_on_repeated_polls_of_the_same_candle():
    rng = _FixedChoiceRng(["long", 5])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1, 5], margin_pct=0.05, rng=rng)
    broker = _StubBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)  # consumes the queue
    strategy.on_bar(make_bar(0), broker)  # same timestamp again -- must not touch rng/broker again

    assert len(broker.opens) == 1


def test_exit_coinflip_closes_the_position_then_immediately_flips_a_fresh_one():
    # Closing frees the symbol up again within the SAME candle-transition
    # call, so a fresh entry coinflip follows right after -- there's no
    # separate "next candle" tick to defer it to in a bar-driven strategy.
    rng = _FixedChoiceRng(["long", 5, True, "short", 1])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1, 5], margin_pct=0.05, rng=rng)
    broker = _StubBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)
    assert "BTC/USDT" in broker.positions

    strategy.on_bar(make_bar(1), broker)
    assert broker.closes == ["BTC/USDT"]
    assert broker.opens[-1] == ("BTC/USDT", "short", 1, 50.0)
    assert "BTC/USDT" in broker.positions  # closed, then re-opened fresh


def test_hold_coinflip_keeps_the_position_and_does_not_reopen():
    rng = _FixedChoiceRng(["short", 1, False])  # open short, then coinflip False = hold
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1], margin_pct=0.05, rng=rng)
    broker = _StubBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)
    strategy.on_bar(make_bar(1), broker)

    assert "BTC/USDT" in broker.positions
    assert broker.closes == []
    assert len(broker.opens) == 1
