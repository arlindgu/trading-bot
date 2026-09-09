from tradingbot.core.broker import PaperBroker, Position
from tradingbot.core.db import get_session_factory, restore_positions, save_broker


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
