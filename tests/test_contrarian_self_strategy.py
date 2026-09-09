import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.contrarian_self import ContrarianSelfStrategy


def make_bar(hours_offset, close):
    ts = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=hours_offset)
    return Bar(ts, close, close, close, close, 100.0)


def test_closes_after_hold_bars_and_reenters_on_the_next_bar_after_a_win():
    strategy = ContrarianSelfStrategy("BTC/USDT", hold_bars=2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, close in enumerate([100, 100, 110]):  # entry at 100, price rises -- closes as a win on bar 2
        strategy.on_bar(make_bar(i, close), broker)

    assert any(t["side"] == "sell" for t in broker.trade_log)
    assert len(broker.positions) == 0  # closed, re-entry happens on the NEXT bar, not the same one
    assert strategy.skip_next_entry is False

    strategy.on_bar(make_bar(3, 110), broker)
    assert len(broker.positions) == 1  # re-entered since the last trade won


def test_skips_the_next_entry_after_a_loss():
    strategy = ContrarianSelfStrategy("BTC/USDT", hold_bars=2, position_pct=0.5)
    broker = PaperBroker(cash=1000)

    for i, close in enumerate([100, 100, 80]):  # entry at 100, price falls -- closes as a loss on bar 2
        strategy.on_bar(make_bar(i, close), broker)

    assert len(broker.positions) == 0
    assert strategy.skip_next_entry is True  # not consumed yet -- happens on the next flat bar

    strategy.on_bar(make_bar(3, 80), broker)  # skip consumed here, no entry
    assert len(broker.positions) == 0
    assert strategy.skip_next_entry is False

    strategy.on_bar(make_bar(4, 80), broker)  # resumes normally
    assert len(broker.positions) == 1
