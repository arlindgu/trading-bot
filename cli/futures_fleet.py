"""Run every futures account (Coinflip + the high-frequency scalp/joke
strategies) in ONE process against the demo account's futures wallet,
instead of one Docker container per account. Mirrors cli/spot_fleet.py's
structure -- see its docstring and config/fleet_futures.yaml.

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

from tradingbot.config import STATE_DIR, load_symbols, load_yaml
from tradingbot.core import db
from tradingbot.core.coinflip_live import run_once
from tradingbot.core.db import CashBalanceRow
from tradingbot.core.futures_broker import FuturesBroker
from tradingbot.data.fetch import fetch_latest_bars
from tradingbot.strategies.adrenaline_junkie import AdrenalineJunkieStrategy
from tradingbot.strategies.candle_reversal import CandleReversalStrategy
from tradingbot.strategies.coinflip import CoinflipStrategy
from tradingbot.strategies.ema_scalp import EmaScalpStrategy
from tradingbot.strategies.momentum_scalp import MomentumScalpStrategy
from tradingbot.strategies.panic_bot import PanicBotStrategy
from tradingbot.strategies.raidboss import RaidBossFuturesStrategy
from tradingbot.strategies.rsi_scalp import RsiScalpStrategy

DB_PATH = STATE_DIR / "trading.db"
EXCHANGE = "binance"

# Registry a new futures strategy joins by adding one line here -- the
# `params:` dict in fleet_futures.yaml's account entry is passed straight
# through as this class's kwargs (after `symbol`).
FUTURES_STRATEGIES = {
    "coinflip": CoinflipStrategy,
    "rsi_scalp": RsiScalpStrategy,
    "candle_reversal": CandleReversalStrategy,
    "ema_scalp": EmaScalpStrategy,
    "momentum_scalp": MomentumScalpStrategy,
    "adrenaline_junkie": AdrenalineJunkieStrategy,
    "panic_bot": PanicBotStrategy,
    "raidboss": RaidBossFuturesStrategy,
}


def futures_symbol(spot_symbol: str, margin_asset: str, markets: dict) -> str | None:
    base = spot_symbol.split("/")[0]
    candidate = f"{base}/{margin_asset}:{margin_asset}"
    return candidate if candidate in markets else None


class FuturesAccount:
    def __init__(self, account: str, margin_asset: str, strategy: str, total_cash: float, timeframe: str = "1h", params: dict | None = None):
        self.account = account
        self.margin_asset = margin_asset
        self.strategy_name = strategy
        self.total_cash = total_cash
        self.timeframe = timeframe
        self.params = params or {}
        # config/symbols.yaml's "usdt" list -- just the base names to feed
        # futures_symbol(), which converts to whichever margin market this
        # account actually trades. Same list regardless of margin_asset.
        self.input_symbols = load_symbols()["usdt"]
        self.strategies: dict[str, object] = {}
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
        strategy_cls = FUTURES_STRATEGIES[self.strategy_name]
        for spot_symbol in self.input_symbols:
            symbol = futures_symbol(spot_symbol, self.margin_asset, shared_exchange.markets)
            if symbol is None:
                print(f"[skip] no {self.margin_asset} futures market for {spot_symbol}")
                continue
            strategy = strategy_cls(symbol, **self.params)
            self.strategies[symbol] = strategy
            if hasattr(strategy, "sync_with_broker"):
                strategy.sync_with_broker(self.broker)


def load_fleet(fleet_config_path: str) -> list[FuturesAccount]:
    raw = load_yaml(Path(fleet_config_path))
    return [
        FuturesAccount(
            account=entry["account"], margin_asset=entry["margin_asset"], strategy=entry["strategy"],
            total_cash=float(entry["total_cash"]), timeframe=entry.get("timeframe", "1h"),
            params=entry.get("params"),
        )
        for entry in raw["accounts"]
    ]


def run_cycle(accounts: list[FuturesAccount]) -> None:
    unique = {(symbol, acc.timeframe) for acc in accounts for symbol in acc.strategies}
    fetched = fetch_latest_bars(unique, EXCHANGE)
    bars_by_timeframe: dict[str, dict] = {}
    for (symbol, timeframe), bar in fetched.items():
        bars_by_timeframe.setdefault(timeframe, {})[symbol] = bar

    for acc in accounts:
        bars = bars_by_timeframe.get(acc.timeframe, {})
        run_once(acc.strategies, acc.timeframe, EXCHANGE, acc.broker, acc.session, acc.account, bars=bars)
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
