import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.grid import GridStrategy


def make_bar(hours_offset, o, h, l, c):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, o, h, l, c, 0.0)


def new_strategy(**overrides):
    params = dict(symbol="BTC/USDT", lower_price=90, upper_price=110, num_grids=2, investment_per_grid=100)
    params.update(overrides)
    return GridStrategy(**params)


def test_builds_arithmetic_levels_by_default():
    strategy = new_strategy(num_grids=4)
    levels = [strategy.slots[0].buy_price] + [s.sell_price for s in strategy.slots]
    assert levels == [90, 95, 100, 105, 110]


def test_buys_when_price_drops_to_a_grid_level():
    strategy = new_strategy()  # levels: 90, 100, 110
    broker = PaperBroker(cash=1000)
    strategy.on_bar(make_bar(0, 105, 105, 99, 100), broker)
    assert len(broker.positions) == 1
    position = next(iter(broker.positions.values()))
    assert position.entry_price == 100


def test_sells_at_upper_boundary_and_reopens_the_slot_for_rebuy():
    strategy = new_strategy()  # levels: 90, 100, 110
    broker = PaperBroker(cash=1000)

    strategy.on_bar(make_bar(0, 100, 100, 99, 99), broker)  # buys at 100
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(1, 105, 110, 101, 108), broker)  # rallies through 110, low stays above 100
    assert len(broker.positions) == 0
    assert broker.trade_log[-1]["pnl"] > 0

    strategy.on_bar(make_bar(2, 105, 105, 99, 100), broker)  # dips back, slot rebuys
    assert len(broker.positions) == 1


class _SellFailsOnceBroker(PaperBroker):
    """Stub for a live-exchange broker whose first sell attempt is
    rejected (e.g. by the exchange) and returns None instead of a pnl."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sell_attempts = 0

    def sell(self, lot_id, price, timestamp, reason=""):
        self.sell_attempts += 1
        if self.sell_attempts == 1:
            return None
        return super().sell(lot_id, price, timestamp, reason)


def test_keeps_slot_filled_when_a_sell_order_fails_instead_of_losing_the_position():
    strategy = new_strategy()  # levels: 90, 100, 110
    broker = _SellFailsOnceBroker(cash=1000)

    strategy.on_bar(make_bar(0, 100, 100, 99, 99), broker)  # buys at 100
    assert len(broker.positions) == 1

    strategy.on_bar(make_bar(1, 105, 110, 101, 108), broker)  # sell rejected -- position must stay open
    assert len(broker.positions) == 1
    assert strategy.slots[1].lot_id is not None

    strategy.on_bar(make_bar(2, 105, 110, 101, 108), broker)  # retried, this time it succeeds
    assert len(broker.positions) == 0


def test_does_not_buy_while_price_stays_above_the_range():
    strategy = new_strategy()  # buy levels at 90 and 100
    broker = PaperBroker(cash=1000)
    strategy.on_bar(make_bar(0, 115, 118, 112, 116), broker)
    assert len(broker.positions) == 0


def test_skips_a_buy_it_cannot_afford_instead_of_going_negative():
    strategy = new_strategy()  # needs 100 cash per slot
    broker = PaperBroker(cash=50)
    strategy.on_bar(make_bar(0, 105, 105, 95, 100), broker)
    assert len(broker.positions) == 0
    assert broker.cash == 50


def test_buy_fill_is_clamped_to_the_bars_actual_high_not_the_stale_level_price():
    strategy = new_strategy(num_grids=1)  # single slot: buy_price=90, sell_price=110
    broker = PaperBroker(cash=1000)
    # Price never got near 90 -- the whole bar traded far below it (e.g. cold
    # start on history where price starts under the whole grid range).
    strategy.on_bar(make_bar(0, 60, 70, 50, 65), broker)
    position = next(iter(broker.positions.values()))
    assert position.entry_price == 70  # clamped to bar.high, not the stale level price of 90


def test_sell_fill_is_clamped_to_the_bars_actual_low_not_the_stale_level_price():
    strategy = new_strategy(num_grids=1)  # single slot: buy_price=90, sell_price=110
    broker = PaperBroker(cash=1000)
    strategy.on_bar(make_bar(0, 95, 95, 90, 92), broker)  # buys at 90
    strategy.on_bar(make_bar(1, 150, 160, 140, 155), broker)  # gaps straight through 110
    assert broker.trade_log[-1]["price"] == 140  # clamped to bar.low, not the stale level price of 110


def test_sync_with_broker_restores_filled_slots_after_a_restart():
    strategy = new_strategy(num_grids=2)  # levels: 90, 100, 110
    broker = PaperBroker(cash=1000)
    strategy.on_bar(make_bar(0, 105, 105, 99, 100), broker)  # buys the 100-110 slot
    assert len(broker.positions) == 1

    # Simulate a process restart: a fresh strategy instance knows nothing
    # about which slots are filled until synced against the broker's
    # actual (persisted) positions.
    restarted = new_strategy(num_grids=2)
    restarted.sync_with_broker(broker)
    assert restarted.slots[1].lot_id is not None  # the 100-110 slot is recognized as filled
    assert restarted.slots[0].lot_id is None  # the untouched 90-100 slot stays empty

    # Without the fix, the same bar would trigger a duplicate buy here.
    restarted.on_bar(make_bar(1, 100, 100, 99, 100), broker)
    assert len(broker.positions) == 1


def test_risk_pct_per_grid_sizes_from_current_equity_not_a_fixed_amount():
    strategy = GridStrategy(
        symbol="BTC/USDT", lower_price=90, upper_price=110, num_grids=2, risk_pct_per_grid=0.5
    )
    broker = PaperBroker(cash=100)

    strategy.on_bar(make_bar(0, 100, 100, 99, 99), broker)  # buys at 100, size = (100 * 0.5) / 100
    first_size = next(iter(broker.positions.values())).size
    assert first_size == 0.5

    strategy.on_bar(make_bar(1, 105, 110, 101, 108), broker)  # sells at 110, cash grows to 105
    strategy.on_bar(make_bar(2, 105, 105, 99, 100), broker)  # rebuys at 100 against the larger equity
    second_size = next(iter(broker.positions.values())).size

    assert second_size > first_size  # realized gains compounded into a bigger position
