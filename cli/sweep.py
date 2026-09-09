"""Grid-search a strategy's tunable parameters against cached history and
rank combinations by risk-adjusted return (calmar = return_pct / |drawdown|).

Usage:
    python cli/sweep.py config/grid_xrp_usdt.yaml \\
        --num-grids 10,20,30,50,80 \\
        --risk-pct 0.005,0.01,0.02,0.0333 \\
        --geometric true,false

CAUTION: this ranks parameters against ONE historical window (whatever
cli/fetch_data.py cached). Picking the single top row is overfitting to that
window's specific price path -- it's a shortlist tool, not an answer. Sanity
-check a few top candidates by eye (num_trades too low/high, drawdown you'd
actually tolerate) and ideally re-check them against a different time period
before trusting one.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradingbot.config import load_yaml
from tradingbot.core.sweep import run_sweep


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
    config_path = Path(argv[0])
    raw = dict(load_yaml(config_path))
    strategy_name = raw.pop("strategy")

    param_grid: dict[str, list] = {}

    num_grids = parse_flag(argv, "--num-grids")
    if num_grids:
        param_grid["num_grids"] = parse_list(num_grids, int)

    risk_pct = parse_flag(argv, "--risk-pct")
    if risk_pct:
        param_grid["risk_pct_per_grid"] = parse_list(risk_pct, float)
        raw.pop("investment_per_grid", None)  # risk_pct_per_grid overrides a fixed investment_per_grid

    geometric = parse_flag(argv, "--geometric")
    if geometric:
        param_grid["geometric"] = parse_list(geometric, parse_bool)

    if not param_grid:
        print("Pass at least one of --num-grids / --risk-pct / --geometric (comma-separated values).")
        sys.exit(1)

    top = int(parse_flag(argv, "--top") or 15)

    results = run_sweep(strategy_name, raw, param_grid)
    print(results.head(top).to_string(index=False))
    print(f"\n({len(results)} combinations tested total)")


if __name__ == "__main__":
    main()
