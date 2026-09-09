"""Run the paper-trading loop for several strategies sharing ONE cash pool.
State is persisted to the SQLite dashboard database (paper_state/trading.db).

Usage:
    python cli/portfolio_paper_trade.py --total-cash 500 --account alts8 \\
        --num-grids 20 --risk-pct 0.01 --geometric true \\
        config/grid_link_usdt.yaml config/grid_tia_usdt.yaml ...     # loop, poll every 5 min
    ... --once   # single check-and-trade pass across all symbols

    ... --testnet --account alts8_testnet --key-prefix BINANCE_TESTNET_API_500
        # REAL orders against Binance Spot Testnet (fake funds, real order
        # execution/API). Requires <prefix>_KEY / <prefix>_SECRET in a .env
        # file (see .env.example; prefix defaults to BINANCE_TESTNET_API).
        # Give each parallel testnet bot its own key/testnet account (via
        # --key-prefix) so they don't compete for the same real balance.

--num-grids/--risk-pct/--geometric override every config's own value with
one shared setting (e.g. a sweep's chosen combo) instead of editing each
yaml file by hand.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from tradingbot.config import STATE_DIR, load_yaml
from tradingbot.core import db
from tradingbot.core.portfolio_live import run_loop, run_once
from tradingbot.strategies import load_strategy

DB_PATH = STATE_DIR / "trading.db"


def parse_flag(argv: list[str], name: str) -> str | None:
    if name not in argv:
        return None
    return argv[argv.index(name) + 1]


def parse_bool(v: str) -> bool:
    return v.strip().lower() in ("true", "1", "yes")


def main() -> None:
    argv = sys.argv[1:]
    config_paths = [a for a in argv if a.endswith(".yaml")]
    if not config_paths:
        print("Pass one or more config yaml paths.")
        sys.exit(1)

    total_cash = float(parse_flag(argv, "--total-cash") or 500)
    account = parse_flag(argv, "--account") or "portfolio"
    testnet = "--testnet" in argv

    overrides: dict = {}
    if parse_flag(argv, "--num-grids"):
        overrides["num_grids"] = int(parse_flag(argv, "--num-grids"))
    if parse_flag(argv, "--risk-pct"):
        overrides["risk_pct_per_grid"] = float(parse_flag(argv, "--risk-pct"))
    if parse_flag(argv, "--geometric"):
        overrides["geometric"] = parse_bool(parse_flag(argv, "--geometric"))

    strategies = {}
    timeframe = exchange = fee_pct = slippage_pct = None
    for path in config_paths:
        raw = dict(load_yaml(Path(path)))
        strategy_name = raw.pop("strategy")
        if "risk_pct_per_grid" in overrides:
            raw.pop("investment_per_grid", None)
        raw["initial_cash"] = total_cash  # only satisfies GridConfig validation -- the broker's real cash is shared
        raw.update(overrides)
        cfg, strategy = load_strategy(strategy_name, raw)
        strategies[cfg.symbol] = strategy
        if timeframe is None:
            timeframe, exchange, fee_pct, slippage_pct = cfg.timeframe, cfg.exchange, cfg.fee_pct, cfg.slippage_pct
        elif cfg.timeframe != timeframe or cfg.exchange != exchange:
            raise ValueError(f"{cfg.symbol}: portfolio mode requires the same timeframe/exchange across all configs")

    session_factory = db.get_session_factory(DB_PATH)
    session = session_factory()

    if testnet:
        load_dotenv()
        key_prefix = parse_flag(argv, "--key-prefix") or "BINANCE_TESTNET_API"
        api_key = os.environ.get(f"{key_prefix}_KEY")
        api_secret = os.environ.get(f"{key_prefix}_SECRET")
        if not api_key or not api_secret:
            print(f"Set {key_prefix}_KEY and {key_prefix}_SECRET in a .env file to use --testnet.")
            sys.exit(1)
        from tradingbot.core.exchange_broker import ExchangeBroker
        from tradingbot.core.db import CashBalanceRow

        # Resume the tracked budget from a prior run if there is one --
        # only fall back to --total-cash on a first-ever run for this
        # account, same restart semantics as the paper-trading path.
        existing = session.get(CashBalanceRow, account)
        capital = existing.cash if existing is not None else total_cash

        broker = ExchangeBroker(exchange, api_key, api_secret, capital=capital, testnet=True)
        db.restore_positions(broker, session, account)
        print(f"[testnet] connected, tracked budget: {broker.cash:.2f} (real wallet: {broker.fetch_wallet_balance():.2f})")
    else:
        broker = db.load_broker(session, account, total_cash, fee_pct, slippage_pct)

    for strategy in strategies.values():
        if hasattr(strategy, "sync_with_broker"):
            strategy.sync_with_broker(broker)  # restore filled-slot state after a restart

    poll_seconds = int(parse_flag(argv, "--poll-seconds") or 300)

    if "--once" in argv:
        run_once(strategies, timeframe, exchange, broker, session, account)
        db.save_broker(session, account, broker)
    else:
        run_loop(strategies, timeframe, exchange, broker, session, account, poll_seconds=poll_seconds)


if __name__ == "__main__":
    main()
