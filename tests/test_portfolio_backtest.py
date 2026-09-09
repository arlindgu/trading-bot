import pandas as pd

from tradingbot.core.broker import PaperBroker
from tradingbot.core.portfolio_backtest import run_portfolio_backtest
from tradingbot.strategies.grid import GridStrategy


def make_ohlcv(start_hour, prices):
    rows = []
    for i, (o, h, l, c) in enumerate(prices):
        rows.append(
            {
                "timestamp": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(hours=start_hour + i),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": 0.0,
            }
        )
    return pd.DataFrame(rows)


def test_symbols_share_one_cash_pool_not_independent_budgets():
    strategy_a = GridStrategy(symbol="A/USDT", lower_price=95, upper_price=110, num_grids=1, investment_per_grid=80)
    strategy_b = GridStrategy(symbol="B/USDT", lower_price=95, upper_price=110, num_grids=1, investment_per_grid=80)

    bar = [(100, 100, 95, 99)]
    broker = PaperBroker(cash=100)  # enough for ONE 80-cost buy, not both
    run_portfolio_backtest(
        {"A/USDT": strategy_a, "B/USDT": strategy_b},
        {"A/USDT": make_ohlcv(0, bar), "B/USDT": make_ohlcv(0, bar)},
        broker,
    )

    assert len(broker.positions) == 1  # only one of the two symbols could afford to buy
    assert broker.cash == 20


def test_only_the_overlapping_time_range_is_simulated():
    strategy_a = GridStrategy(symbol="A/USDT", lower_price=95, upper_price=110, num_grids=1, investment_per_grid=10)
    strategy_b = GridStrategy(symbol="B/USDT", lower_price=95, upper_price=110, num_grids=1, investment_per_grid=10)

    # A has 3 hours of history, B only exists for the last 2 of them --
    # the portfolio should only simulate where both have data (a
    # later-listed symbol bounds the whole portfolio's start).
    flat_bar = (100, 100, 100, 100)
    ohlcv_a = make_ohlcv(0, [flat_bar, flat_bar, flat_bar])
    ohlcv_b = make_ohlcv(1, [flat_bar, flat_bar])

    broker = PaperBroker(cash=1000)
    result = run_portfolio_backtest(
        {"A/USDT": strategy_a, "B/USDT": strategy_b},
        {"A/USDT": ohlcv_a, "B/USDT": ohlcv_b},
        broker,
    )
    assert len(result.equity_curve) == 2
