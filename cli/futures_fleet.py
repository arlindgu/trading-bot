"""Run every coinflip (futures) account in ONE process against the demo
account's futures wallet, instead of one Docker container per account.
Mirrors cli/spot_fleet.py's structure -- see its docstring and
config/fleet_futures.yaml.

Usage:
    python cli/futures_fleet.py config/fleet_futures.yaml
    python cli/futures_fleet.py config/fleet_futures.yaml --once
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ccxt
from dotenv import load_dotenv

from tradingbot.config import STATE_DIR, load_yaml
from tradingbot.core import db
from tradingbot.core.coinflip_live import run_once
from tradingbot.core.db import CashBalanceRow
from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.data.fetch import fetch_latest_bars
from tradingbot.strategies.coinflip import CoinflipStrategy

DB_PATH = STATE_DIR / "trading.db"
TIMEFRAME = "1h"
EXCHANGE = "binance"


def futures_symbol(spot_symbol: str, margin_asset: str, markets: dict) -> str | None:
    base = spot_symbol.split("/")[0]
    candidate = f"{base}/{margin_asset}:{margin_asset}"
    return candidate if candidate in markets else None


class FuturesAccount:
    def __init__(
        self, account: str, margin_asset: str, leverage: list[int], margin_pct: float, total_cash: float,
        symbols: list[str], max_concurrent: int = 3,
    ):
        self.account = account
        self.margin_asset = margin_asset
        self.leverage = leverage
        self.margin_pct = margin_pct
        self.total_cash = total_cash
        self.input_symbols = symbols
        self.max_concurrent = max_concurrent
        self.strategies: dict[str, CoinflipStrategy] = {}
        self.broker: FuturesBroker | None = None
        self.session = None

    def attach(self, shared_exchange: ccxt.Exchange, session_factory) -> None:
        self.session = session_factory()
        existing = self.session.get(CashBalanceRow, self.account)
        capital = existing.cash if existing is not None else self.total_cash
        self.broker = FuturesBroker(
            api_key="", api_secret="", capital=capital, margin_asset=self.margin_asset, exchange=shared_exchange,
        )
        db.restore_futures_positions(self.broker, self.session, self.account)
        for spot_symbol in self.input_symbols:
            symbol = futures_symbol(spot_symbol, self.margin_asset, shared_exchange.markets)
            if symbol is None:
                print(f"[skip] no {self.margin_asset} futures market for {spot_symbol}")
                continue
            self.strategies[symbol] = CoinflipStrategy(symbol, self.leverage, self.margin_pct, self.max_concurrent)


def load_fleet(fleet_config_path: str) -> list[FuturesAccount]:
    raw = load_yaml(Path(fleet_config_path))
    return [
        FuturesAccount(
            account=entry["account"], margin_asset=entry["margin_asset"], leverage=list(entry["leverage"]),
            margin_pct=float(entry["margin_pct"]), total_cash=float(entry["total_cash"]), symbols=list(entry["symbols"]),
            max_concurrent=int(entry.get("max_concurrent", 3)),
        )
        for entry in raw["accounts"]
    ]


def run_cycle(accounts: list[FuturesAccount]) -> None:
    unique = {(symbol, TIMEFRAME) for acc in accounts for symbol in acc.strategies}
    fetched = fetch_latest_bars(unique, EXCHANGE)
    bars = {symbol: bar for (symbol, _tf), bar in fetched.items()}

    for acc in accounts:
        run_once(acc.strategies, TIMEFRAME, EXCHANGE, acc.broker, acc.session, acc.account, bars=bars)
        db.save_broker(acc.session, acc.account, acc.broker)


def main() -> None:
    argv = sys.argv[1:]
    fleet_paths = [a for a in argv if a.endswith(".yaml")]
    if not fleet_paths:
        print("Pass a fleet config yaml path, e.g. config/fleet_futures.yaml")
        sys.exit(1)

    load_dotenv()
    api_key = os.environ.get("BINANCE_DEMO_KEY")
    api_secret = os.environ.get("BINANCE_DEMO_SECRET")
    if not api_key or not api_secret:
        print("Set BINANCE_DEMO_KEY and BINANCE_DEMO_SECRET in a .env file.")
        sys.exit(1)

    shared_exchange = ccxt.binanceusdm({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
    shared_exchange.enable_demo_trading(True)
    shared_exchange.load_markets()
    print(f"[futures-fleet] connected, one shared client for every account")

    accounts = load_fleet(fleet_paths[0])
    session_factory = db.get_session_factory(DB_PATH)
    for acc in accounts:
        acc.attach(shared_exchange, session_factory)
    print(f"[futures-fleet] {len(accounts)} accounts loaded: {', '.join(a.account for a in accounts)}")

    poll_seconds = 300
    if "--once" in argv:
        run_cycle(accounts)
    else:
        print(f"Starting futures fleet loop, polling every {poll_seconds}s. Ctrl+C to stop.")
        while True:
            run_cycle(accounts)
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
