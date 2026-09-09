"""Backtest several strategies together against ONE shared cash pool
(instead of each with its own independent capital).

Usage:
    python cli/portfolio_backtest.py --total-cash 500 \\
        config/grid_btc_usdt.yaml config/grid_link_usdt.yaml ...
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradingbot.config import load_yaml
from tradingbot.core.broker import PaperBroker
from tradingbot.core.portfolio_backtest import run_portfolio_backtest
from tradingbot.data.fetch import load_cached
from tradingbot.strategies import load_strategy


def parse_flag(argv: list[str], name: str) -> str | None:
    if name not in argv:
        return None
    return argv[argv.index(name) + 1]


def main() -> None:
    argv = sys.argv[1:]
    total_cash = float(parse_flag(argv, "--total-cash") or 500)
    config_paths = [a for a in argv if a.endswith(".yaml")]
    if not config_paths:
        print("Pass one or more config yaml paths.")
        sys.exit(1)

    strategies = {}
    ohlcv_by_symbol = {}
    fee_pct = slippage_pct = None
    for path in config_paths:
        raw = dict(load_yaml(Path(path)))
        strategy_name = raw.pop("strategy")
        raw["initial_cash"] = total_cash  # only satisfies GridConfig validation -- the broker's real cash is shared/external
        cfg, strategy = load_strategy(strategy_name, raw)
        strategies[cfg.symbol] = strategy
        ohlcv_by_symbol[cfg.symbol] = load_cached(cfg.symbol, cfg.timeframe, cfg.exchange)
        if fee_pct is None:
            fee_pct, slippage_pct = cfg.fee_pct, cfg.slippage_pct  # assumed shared across all configs passed in

    broker = PaperBroker(cash=total_cash, fee_pct=fee_pct, slippage_pct=slippage_pct)
    result = run_portfolio_backtest(strategies, ohlcv_by_symbol, broker)

    print(f"=== Portfolio: {', '.join(strategies)} (shared {total_cash} cash, {len(result.equity_curve)} bars) ===")
    for key, value in result.summary().items():
        print(f"  {key}: {value}")

    print("\nPer symbol:")
    for symbol in strategies:
        closed = [t for t in broker.trade_log if t["symbol"] == symbol and t["side"] == "sell"]
        open_lots = [p for p in broker.positions.values() if p.symbol == symbol]
        print(f"  {symbol}: {len(closed)} closed trades, {len(open_lots)} open positions")


if __name__ == "__main__":
    main()
