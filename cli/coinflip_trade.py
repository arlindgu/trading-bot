"""Run the coinflip strategy (real long/short + leverage via Binance
Futures Demo Trading) across several symbols sharing ONE self-tracked
margin budget. For laughs -- no signal, purely random entries/exits.

Usage:
    python cli/coinflip_trade.py --account coinflip_usdt_500 --total-cash 500 \\
        --margin-asset USDT --leverage 1,2,3,5 --margin-pct 0.03 \\
        --key-prefix BINANCE_DEMO_FUTURES \\
        LINK/USDT TIA/USDT DOT/USDT ETH/USDT WIF/USDT AVAX/USDT SOL/USDT ARB/USDT

Symbols are passed in the same "BASE/USDT" shape as the grid configs --
they get rewritten to the actual futures market (e.g. "LINK/USDC:USDC")
based on --margin-asset. A symbol with no market in that margin asset
(e.g. DOT has no USDC perpetual) is skipped with a warning, not fatal.

--once for a single pass, otherwise loops forever polling every
--poll-seconds (default 300, matching the grid bots' cadence).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from tradingbot.config import STATE_DIR
from tradingbot.core import db
from tradingbot.core.coinflip_live import run_loop, run_once
from tradingbot.core.db import CashBalanceRow
from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.strategies.coinflip import CoinflipStrategy

DB_PATH = STATE_DIR / "trading.db"
TIMEFRAME = "1h"
EXCHANGE = "binance"


def parse_flag(argv: list[str], name: str) -> str | None:
    if name not in argv:
        return None
    return argv[argv.index(name) + 1]


def futures_symbol(spot_symbol: str, margin_asset: str, markets: dict) -> str | None:
    base = spot_symbol.split("/")[0]
    candidate = f"{base}/{margin_asset}:{margin_asset}"
    return candidate if candidate in markets else None


def main() -> None:
    argv = sys.argv[1:]
    input_symbols = [a for a in argv if "/" in a]
    if not input_symbols:
        print("Pass one or more symbols, e.g. LINK/USDT TIA/USDT ...")
        sys.exit(1)

    load_dotenv()
    account = parse_flag(argv, "--account") or "coinflip"
    total_cash = float(parse_flag(argv, "--total-cash") or 500)
    margin_asset = parse_flag(argv, "--margin-asset") or "USDT"
    margin_pct = float(parse_flag(argv, "--margin-pct") or 0.03)
    leverage_choices = [int(x) for x in (parse_flag(argv, "--leverage") or "1,2,3,5").split(",")]
    poll_seconds = int(parse_flag(argv, "--poll-seconds") or 300)
    key_prefix = parse_flag(argv, "--key-prefix") or "BINANCE_DEMO_FUTURES"

    api_key = os.environ.get(f"{key_prefix}_KEY")
    api_secret = os.environ.get(f"{key_prefix}_SECRET")
    if not api_key or not api_secret:
        print(f"Set {key_prefix}_KEY and {key_prefix}_SECRET in a .env file.")
        sys.exit(1)

    session_factory = db.get_session_factory(DB_PATH)
    session = session_factory()

    existing = session.get(CashBalanceRow, account)
    capital = existing.cash if existing is not None else total_cash

    broker = FuturesBroker(api_key, api_secret, capital=capital, margin_asset=margin_asset, demo=True)
    db.restore_futures_positions(broker, session, account)
    print(f"[coinflip] connected, tracked budget: {broker.cash:.2f} {margin_asset}")

    strategies = {}
    for spot_symbol in input_symbols:
        symbol = futures_symbol(spot_symbol, margin_asset, broker.exchange.markets)
        if symbol is None:
            print(f"[skip] no {margin_asset} futures market for {spot_symbol}")
            continue
        strategies[symbol] = CoinflipStrategy(symbol, leverage_choices, margin_pct)

    if "--once" in argv:
        run_once(strategies, TIMEFRAME, EXCHANGE, broker, session, account)
        db.save_broker(session, account, broker)
    else:
        run_loop(strategies, TIMEFRAME, EXCHANGE, broker, session, account, poll_seconds=poll_seconds)


if __name__ == "__main__":
    main()
