from tradingbot.core.broker import PaperBroker, Position
from tradingbot.core.db import get_session_factory, restore_futures_positions, restore_positions, save_broker
from tradingbot.core.futures_broker import FuturesBroker


def test_restore_positions_handles_lot_ids_without_a_numeric_suffix(tmp_path):
    # A broker whose lot ids aren't "<symbol>-<counter>" (e.g. FuturesBroker,
    # whose lot id is just the symbol) shouldn't crash restore_positions --
    # this is also used read-only by the dashboard API to display ANY
    # account regardless of which broker wrote it.
    session = get_session_factory(tmp_path / "test.db")()
    writer = PaperBroker(cash=1000)
    writer.positions["ARBUSDT:USDT"] = Position("ARBUSDT:USDT", "ARB/USDT:USDT", 1.0, 0.5, "t0", "coinflip:long:5")
    save_broker(session, "test-account", writer)

    reader = PaperBroker(cash=0)
    restore_positions(reader, session, "test-account")

    assert "ARBUSDT:USDT" in reader.positions


def test_restore_futures_positions_parses_tp_sl_from_the_tag(tmp_path):
    session = get_session_factory(tmp_path / "test.db")()
    writer = FuturesBroker("k", "s", capital=1000, exchange=object())
    # open_position needs a real exchange to fill an order -- build the
    # position by hand instead, same shape a real fill would produce.
    from tradingbot.core.futures_broker import FuturesPosition

    writer.positions["ARBUSDT:USDT-1"] = FuturesPosition(
        "ARBUSDT:USDT-1", "ARB/USDT:USDT", "long", 5, 0.5, 100.0, "t0", 50.0, tp_pct=0.03, sl_pct=0.02
    )
    save_broker(session, "test-account", writer)

    reader = FuturesBroker("k", "s", capital=0, exchange=object())
    restore_futures_positions(reader, session, "test-account")

    restored = reader.positions["ARBUSDT:USDT-1"]
    assert restored.tp_pct == 0.03
    assert restored.sl_pct == 0.02


def test_restore_futures_positions_handles_the_old_tag_format_without_tp_sl(tmp_path):
    session = get_session_factory(tmp_path / "test.db")()
    writer = FuturesBroker("k", "s", capital=1000, exchange=object())
    from tradingbot.core.futures_broker import FuturesPosition

    writer.positions["ARBUSDT:USDT"] = FuturesPosition("ARBUSDT:USDT", "ARB/USDT:USDT", "long", 5, 0.5, 100.0, "t0", 50.0)
    save_broker(session, "test-account", writer)

    reader = FuturesBroker("k", "s", capital=0, exchange=object())
    restore_futures_positions(reader, session, "test-account")

    restored = reader.positions["ARBUSDT:USDT"]
    assert restored.tp_pct is None
    assert restored.sl_pct is None


def test_restore_futures_positions_resumes_the_lot_counter_above_the_highest_seen(tmp_path):
    session = get_session_factory(tmp_path / "test.db")()
    writer = FuturesBroker("k", "s", capital=1000, exchange=object())
    from tradingbot.core.futures_broker import FuturesPosition

    writer.positions["ARBUSDT:USDT-3"] = FuturesPosition("ARBUSDT:USDT-3", "ARB/USDT:USDT", "long", 5, 0.5, 100.0, "t0", 50.0)
    save_broker(session, "test-account", writer)

    reader = FuturesBroker("k", "s", capital=0, exchange=object())
    restore_futures_positions(reader, session, "test-account")

    assert next(reader._lot_counter) == 4
