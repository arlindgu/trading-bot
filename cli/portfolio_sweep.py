"""Grid-search shared grid parameters (num_grids, risk_pct_per_grid,
geometric) applied UNIFORMLY across several symbols tested together against
ONE shared cash pool, ranked by calmar (return_pct / |max_drawdown_pct|).

Usage:
    python cli/portfolio_sweep.py --total-cash 500 \\
        --num-grids 10,20,30,50,80 --risk-pct 0.005,0.01,0.02,0.0333,0.05 --geometric true,false \\
        config/grid_btc_usdt.yaml config/grid_link_usdt.yaml ...

CAUTION: same overfitting caveat as cli/sweep.py -- this ranks against one
historical window, it's a shortlist tool, not an answer. Additionally, only
the time range where ALL given symbols already existed is simulated (the
latest-listed symbol bounds the whole portfolio's start), so adding a very
recently listed symbol can shrink the tested window a lot.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from tradingbot.config import load_yaml
from tradingbot.core.broker import PaperBroker
from tradingbot.core.portfolio_backtest import run_portfolio_backtest
from tradingbot.data.fetch import load_cached
from tradingbot.strategies import load_strategy


def parse_list(raw: str, cast):
    return [cast(v) for v in raw.split(",")]


def parse_bool(v: str) -> bool:
    return v.strip().lower() in ("true", "1", "yes")


def parse_flag(argv: list[str], name: str) -> str | None:
    if name not in argv:
        return None
    return argv[argv.index(name) + 1]


def main() -> None:
    argv = sys.argv[1:]
    config_paths = [a for a in argv if a.endswith(".yaml")]
    if not config_paths:
        print("Pass one or more config yaml paths.")
        sys.exit(1)

    total_cash = float(parse_flag(argv, "--total-cash") or 500)
    top = int(parse_flag(argv, "--top") or 15)

    param_grid: dict[str, list] = {}
    num_grids = parse_flag(argv, "--num-grids")
    if num_grids:
        param_grid["num_grids"] = parse_list(num_grids, int)
    risk_pct = parse_flag(argv, "--risk-pct")
    if risk_pct:
        param_grid["risk_pct_per_grid"] = parse_list(risk_pct, float)
    geometric = parse_flag(argv, "--geometric")
    if geometric:
        param_grid["geometric"] = parse_list(geometric, parse_bool)

    if not param_grid:
        print("Pass at least one of --num-grids / --risk-pct / --geometric (comma-separated values).")
        sys.exit(1)

    base_raw: dict[str, dict] = {}
    ohlcv_by_symbol = {}
    fee_pct = slippage_pct = None
    strategy_name = None
    for path in config_paths:
        raw = dict(load_yaml(Path(path)))
        strategy_name = raw.pop("strategy")
        raw.pop("investment_per_grid", None)  # risk_pct_per_grid (being swept) overrides a fixed amount
        raw["initial_cash"] = total_cash
        symbol = raw["symbol"]
        base_raw[symbol] = raw
        ohlcv_by_symbol[symbol] = load_cached(raw["symbol"], raw["timeframe"], raw["exchange"])
        if fee_pct is None:
            fee_pct, slippage_pct = raw["fee_pct"], raw["slippage_pct"]

    keys = list(param_grid.keys())
    rows = []
    for values in itertools.product(*param_grid.values()):
        overrides = dict(zip(keys, values))
        strategies = {}
        for symbol, raw in base_raw.items():
            cfg, strategy = load_strategy(strategy_name, {**raw, **overrides})
            strategies[symbol] = strategy

        broker = PaperBroker(cash=total_cash, fee_pct=fee_pct, slippage_pct=slippage_pct)
        result = run_portfolio_backtest(strategies, ohlcv_by_symbol, broker)
        summary = result.summary()
        calmar = summary["total_return_pct"] / abs(summary["max_drawdown_pct"]) if summary["max_drawdown_pct"] else 0.0
        rows.append({**overrides, **summary, "calmar": round(calmar, 3)})

    results = pd.DataFrame(rows).sort_values("calmar", ascending=False).reset_index(drop=True)
    print(results.head(top).to_string(index=False))
    print(f"\n({len(results)} combinations tested total, symbols: {', '.join(base_raw)})")


if __name__ == "__main__":
    main()
