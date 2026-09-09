"""Backtest a strategy against its cached OHLCV history.

Usage:
    python cli/backtest.py config/grid_btc_usdt.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradingbot.config import load_yaml
from tradingbot.core.backtest import run_backtest
from tradingbot.core.broker import PaperBroker
from tradingbot.data.fetch import load_cached
from tradingbot.strategies import load_strategy


def main() -> None:
    config_path = Path(sys.argv[1])
    raw = dict(load_yaml(config_path))
    strategy_name = raw.pop("strategy")
    cfg, strategy = load_strategy(strategy_name, raw)

    ohlcv = load_cached(cfg.symbol, cfg.timeframe, cfg.exchange)
    broker = PaperBroker(cash=cfg.starting_cash, fee_pct=cfg.fee_pct, slippage_pct=cfg.slippage_pct)

    result = run_backtest(strategy, cfg.symbol, ohlcv, broker)
    print(f"=== {strategy_name} / {cfg.symbol} ({len(ohlcv)} bars) ===")
    for key, value in result.summary().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
