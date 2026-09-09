from tradingbot.core.broker import PaperBroker


def test_buy_deducts_cash_and_fee_and_opens_a_position():
    broker = PaperBroker(cash=1000, fee_pct=0.001)
    lot_id = broker.buy("BTC/USDT", price=100, size=2, timestamp="t0")
    assert lot_id in broker.positions
    assert broker.cash == 1000 - 200 - 0.2


def test_sell_realizes_pnl_and_closes_the_position():
    broker = PaperBroker(cash=1000)
    lot_id = broker.buy("BTC/USDT", price=100, size=1, timestamp="t0")
    pnl = broker.sell(lot_id, price=110, timestamp="t1", reason="test")
    assert lot_id not in broker.positions
    assert pnl == 10
    assert broker.cash == 1000 - 100 + 110


def test_slippage_worsens_fills_in_both_directions():
    broker = PaperBroker(cash=1000, slippage_pct=0.01)
    lot_id = broker.buy("BTC/USDT", price=100, size=1, timestamp="t0")
    assert broker.positions[lot_id].entry_price == 101
    pnl = broker.sell(lot_id, price=110, timestamp="t1")
    assert pnl == (110 * 0.99) - 101


def test_equity_marks_open_positions_to_current_price():
    broker = PaperBroker(cash=500)
    broker.buy("BTC/USDT", price=100, size=1, timestamp="t0")
    assert broker.equity({"BTC/USDT": 150}) == 400 + 150


def test_multiple_lots_on_the_same_symbol_stay_independent():
    broker = PaperBroker(cash=1000)
    lot_a = broker.buy("BTC/USDT", price=100, size=1, timestamp="t0")
    lot_b = broker.buy("BTC/USDT", price=110, size=1, timestamp="t1")
    assert lot_a != lot_b
    assert len(broker.positions) == 2
    broker.sell(lot_a, price=120, timestamp="t2")
    assert len(broker.positions) == 1
    assert lot_b in broker.positions


def test_equity_falls_back_to_last_known_mark_for_a_symbol_not_in_this_call():
    broker = PaperBroker(cash=1000)
    broker.buy("A/USDT", price=100, size=1, timestamp="t0")
    broker.buy("B/USDT", price=50, size=2, timestamp="t0")

    broker.equity({"A/USDT": 100, "B/USDT": 50})  # primes the cache for both
    # This call only knows A's fresh price -- B should use its last-seen
    # mark (50), not silently drop out of the total or fall back to a stale
    # entry_price if the real price had moved since entry.
    equity = broker.equity({"A/USDT": 120})
    assert equity == broker.cash + 1 * 120 + 2 * 50


def test_round_trip_through_dict_preserves_state_and_lot_counter():
    broker = PaperBroker(cash=1000, fee_pct=0.001, slippage_pct=0.0005)
    broker.buy("BTC/USDT", price=100, size=1, timestamp="t0")
    restored = PaperBroker.from_dict(broker.to_dict())
    assert restored.cash == broker.cash
    assert restored.positions.keys() == broker.positions.keys()
    new_lot = restored.buy("BTC/USDT", price=100, size=1, timestamp="t1")
    assert new_lot not in broker.positions
