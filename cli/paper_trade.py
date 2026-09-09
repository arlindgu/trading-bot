"""Run the paper-trading loop for one strategy (simulated fills only -- no
real orders, no API keys with trade permissions).

Usage:
    python cli/paper_trade.py config/grid_btc_usdt.yaml                # loop, poll every 5 min
    python cli/paper_trade.py config/grid_btc_usdt.yaml --once          # single pass
    python cli/paper_trade.py config/grid_btc_usdt.yaml --account run2  # separate ledger file
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradingbot.config import STATE_DIR, load_yaml
from tradingbot.core.live import run_loop, run_once
from tradingbot.core.state import load_broker, save_broker
from tradingbot.strategies import load_strategy


def main() -> None:
    config_path = Path(sys.argv[1])
    raw = dict(load_yaml(config_path))
    strategy_name = raw.pop("strategy")
    cfg, strategy = load_strategy(strategy_name, raw)

    account = "default"
    if "--account" in sys.argv:
        account = sys.argv[sys.argv.index("--account") + 1]
    state_path = STATE_DIR / f"{account}.json"

    broker = load_broker(state_path, cfg.starting_cash, cfg.fee_pct, cfg.slippage_pct)
    if hasattr(strategy, "sync_with_broker"):
        strategy.sync_with_broker(broker)  # restore filled-slot state after a restart

    if "--once" in sys.argv:
        run_once(strategy, cfg.symbol, cfg.timeframe, cfg.exchange, broker)
        save_broker(state_path, broker)
    else:
        run_loop(strategy, cfg.symbol, cfg.timeframe, cfg.exchange, broker, state_path)


if __name__ == "__main__":
    main()
