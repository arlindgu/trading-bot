from __future__ import annotations

import itertools

import pandas as pd

from tradingbot.core.backtest import run_backtest
from tradingbot.core.broker import PaperBroker
from tradingbot.data.fetch import load_cached
from tradingbot.strategies import load_strategy


def run_sweep(strategy_name: str, base_config: dict, param_grid: dict[str, list]) -> pd.DataFrame:
    """Backtest every combination in `param_grid` (cartesian product) on top
    of `base_config`, on the same cached history. Returns one row per
    combination with the swept params plus the backtest summary, including a
    `calmar` score (return_pct / abs(max_drawdown_pct)) -- ranking by raw
    return alone rewards reckless drawdown, this doesn't.
    """
    keys = list(param_grid.keys())
    rows = []
    for values in itertools.product(*param_grid.values()):
        overrides = dict(zip(keys, values))
        raw = {**base_config, **overrides}
        cfg, strategy = load_strategy(strategy_name, raw)
        ohlcv = load_cached(cfg.symbol, cfg.timeframe, cfg.exchange)
        broker = PaperBroker(cash=cfg.starting_cash, fee_pct=cfg.fee_pct, slippage_pct=cfg.slippage_pct)
        result = run_backtest(strategy, cfg.symbol, ohlcv, broker)
        summary = result.summary()
        calmar = summary["total_return_pct"] / abs(summary["max_drawdown_pct"]) if summary["max_drawdown_pct"] else 0.0
        rows.append({**overrides, **summary, "calmar": round(calmar, 3)})

    return pd.DataFrame(rows).sort_values("calmar", ascending=False).reset_index(drop=True)
