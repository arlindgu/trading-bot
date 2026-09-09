import itertools

import pandas as pd

from tradingbot.core.types import Bar
from tradingbot.strategies.coinflip import CoinflipStrategy


class _StubPosition:
    def __init__(self, symbol, side, entry_price, tp_pct, sl_pct):
        self.symbol = symbol
        self.side = side
        self.entry_price = entry_price
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct


class _StubBroker:
    """Stands in for FuturesBroker without touching a real exchange --
    CoinflipStrategy only ever calls .positions, .equity(), .open_position(),
    .close_position(), all reproduced here minimally. Keyed by lot id, like
    the real broker, so several lots on the same symbol can coexist."""

    def __init__(self, cash: float = 1000.0, entry_price: float = 100.0):
        self.cash = cash
        self.entry_price = entry_price
        self.positions: dict[str, _StubPosition] = {}
        self.opens: list[tuple] = []
        self.closes: list[tuple] = []
        self._lot_counter = itertools.count(1)

    def equity(self, marks):
        return self.cash

    def open_position(self, symbol, side, leverage, margin, timestamp, tp_pct=None, sl_pct=None):
        lot_id = f"{symbol}-{next(self._lot_counter)}"
        self.positions[lot_id] = _StubPosition(symbol, side, self.entry_price, tp_pct, sl_pct)
        self.opens.append((symbol, side, leverage, margin, tp_pct, sl_pct))
        return lot_id

    def close_position(self, lot_id, timestamp, reason="coinflip_exit"):
        position = self.positions.pop(lot_id, None)
        if position is not None:
            self.closes.append((position.symbol, reason))
        return 0.0


class _FixedChoiceRng:
    """Deterministic stand-in for random.Random -- pops from a fixed queue
    for .choice() calls and another for .random() calls, so tests aren't
    flaky."""

    def __init__(self, choices=(), randoms=()):
        self.choice_queue = list(choices)
        self.random_queue = list(randoms)

    def choice(self, seq):
        return self.choice_queue.pop(0)

    def random(self):
        return self.random_queue.pop(0)


def make_bar(hours_offset, close=100.0):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 0.0)


def open_symbols(broker):
    return [p.symbol for p in broker.positions.values()]


def test_opens_a_position_when_flat():
    rng = _FixedChoiceRng(choices=["long", 5, 0.03, 0.02])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1, 5], margin_pct=0.05, rng=rng)
    broker = _StubBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)

    assert broker.opens == [("BTC/USDT", "long", 5, 50.0, 0.03, 0.02)]


def test_does_not_reflip_on_repeated_polls_of_the_same_candle():
    rng = _FixedChoiceRng(choices=["long", 5, 0.03, 0.02])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1, 5], margin_pct=0.05, rng=rng)
    broker = _StubBroker(cash=1000)

    strategy.on_bar(make_bar(0), broker)  # consumes the queue
    strategy.on_bar(make_bar(0), broker)  # same timestamp again -- must not touch rng/broker again

    assert len(broker.opens) == 1


def test_opens_additional_concurrent_lots_up_to_max_concurrent():
    # Each bar checks the impatience roll once per ALREADY-open lot before
    # possibly opening a new one: bar0 opens lot A (0 checks), bar1 checks
    # A then opens B (1 check), bar2 checks A+B then opens C (2 checks) --
    # 0+1+2 = 3 random() calls total.
    rng = _FixedChoiceRng(choices=["long", 1, 0.05, 0.05] * 3, randoms=[0.9, 0.9, 0.9])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1], margin_pct=0.05, max_concurrent=3, rng=rng)
    broker = _StubBroker(cash=1000, entry_price=100.0)

    for i in range(3):
        strategy.on_bar(make_bar(i, close=100.0), broker)  # flat price, high impatience roll -- never closes

    assert len(broker.positions) == 3
    assert open_symbols(broker) == ["BTC/USDT", "BTC/USDT", "BTC/USDT"]


def test_does_not_open_a_fourth_lot_once_at_max_concurrent():
    # bar0: 0 checks, opens A. bar1: 1 check, opens B. bar2: 2 checks, opens
    # C (now at max_concurrent=3). bar3: 3 checks, does NOT open a 4th --
    # 0+1+2+3 = 6 random() calls total, and only 3 opens' worth of choices.
    rng = _FixedChoiceRng(choices=["long", 1, 0.05, 0.05] * 3, randoms=[0.9] * 6)
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1], margin_pct=0.05, max_concurrent=3, rng=rng)
    broker = _StubBroker(cash=1000, entry_price=100.0)

    for i in range(4):
        strategy.on_bar(make_bar(i, close=100.0), broker)

    assert len(broker.positions) == 3  # the rng choice queue for a 4th open would have raised if it were consumed


def test_take_profit_closes_a_long_once_price_crosses_the_tp_band():
    rng = _FixedChoiceRng(choices=["long", 5, 0.03, 0.02, "short", 1, 0.03, 0.02])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1, 5], margin_pct=0.05, max_concurrent=1, rng=rng)
    broker = _StubBroker(cash=1000, entry_price=100.0)

    strategy.on_bar(make_bar(0, close=100.0), broker)
    assert open_symbols(broker) == ["BTC/USDT"]

    # +4% move, past the 3% TP -- random() is never consulted since TP hits first
    strategy.on_bar(make_bar(1, close=104.0), broker)

    assert broker.closes == [("BTC/USDT", "take_profit")]
    assert broker.opens[-1] == ("BTC/USDT", "short", 1, 50.0, 0.03, 0.02)  # closed, then re-opened fresh


def test_stop_loss_closes_a_short_once_price_crosses_the_sl_band():
    rng = _FixedChoiceRng(choices=["short", 1, 0.05, 0.02, "long", 5, 0.05, 0.02])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1, 5], margin_pct=0.05, max_concurrent=1, rng=rng)
    broker = _StubBroker(cash=1000, entry_price=100.0)

    strategy.on_bar(make_bar(0, close=100.0), broker)
    assert open_symbols(broker) == ["BTC/USDT"]

    # price up 3% is a LOSS for a short, past the 2% SL
    strategy.on_bar(make_bar(1, close=103.0), broker)

    assert broker.closes == [("BTC/USDT", "stop_loss")]


def test_impatience_coinflip_can_close_before_tp_or_sl_hit():
    rng = _FixedChoiceRng(choices=["long", 1, 0.05, 0.05, "short", 1, 0.05, 0.05], randoms=[0.05])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1], margin_pct=0.05, max_concurrent=1, rng=rng)
    broker = _StubBroker(cash=1000, entry_price=100.0)

    strategy.on_bar(make_bar(0, close=100.0), broker)
    # unchanged price -- neither TP nor SL hit, but the impatience roll (0.05) beats the threshold
    strategy.on_bar(make_bar(1, close=100.0), broker)

    assert broker.closes == [("BTC/USDT", "impatience")]


def test_hold_when_neither_threshold_nor_impatience_triggers():
    rng = _FixedChoiceRng(choices=["short", 1, 0.05, 0.05], randoms=[0.9])
    strategy = CoinflipStrategy("BTC/USDT", leverage_choices=[1], margin_pct=0.05, max_concurrent=1, rng=rng)
    broker = _StubBroker(cash=1000, entry_price=100.0)

    strategy.on_bar(make_bar(0, close=100.0), broker)
    strategy.on_bar(make_bar(1, close=100.0), broker)  # flat price, high impatience roll -- holds

    assert open_symbols(broker) == ["BTC/USDT"]
    assert broker.closes == []
    assert len(broker.opens) == 1
