"""Run every spot-side account (grid + the long/flat real & joke strategies)
in ONE process against the demo account's spot wallet, instead of one
Docker container per account. Each account keeps its own ExchangeBroker
(own cash/positions/trade_log) and Strategy instances -- only the
authenticated ccxt client and each poll cycle's bar fetches are shared
across accounts, which is what actually cuts the per-account overhead
(see config/fleet_spot.yaml and README.md's "Live order execution" section
for why this exists and how the budget tiers are sized).

Usage:
    python cli/spot_fleet.py config/fleet_spot.yaml
    python cli/spot_fleet.py config/fleet_spot.yaml --once
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ccxt
from dotenv import load_dotenv

from tradingbot.config import ROOT, STATE_DIR, load_symbols, load_yaml
from tradingbot.core import db
from tradingbot.core.db import CashBalanceRow
from tradingbot.core.exchange_broker import ExchangeBroker
from tradingbot.core.portfolio_live import run_once
from tradingbot.data.fetch import fetch_latest_bars
from tradingbot.strategies import load_strategy

DB_PATH = STATE_DIR / "trading.db"


class SpotAccount:
    def __init__(
        self,
        account: str,
        total_cash: float,
        overrides: dict,
        quote_currency: str,
        configs: list[str] | str | None = None,
        config: str | None = None,
    ):
        """Two ways to define an account's per-symbol configs:
        - `configs`: one yaml path per symbol (grid's style -- needed since
          grid's price range genuinely differs per symbol). Pass the
          literal string "auto" to derive the list from config/symbols.yaml
          instead of enumerating paths by hand -- config/grid_<slug>_usdt.yaml
          per symbol, skipping any that doesn't exist yet (not every symbol
          has a hand-calibrated grid range).
        - `config`: ONE yaml path shared by every symbol (every other
          strategy here -- their params don't vary by symbol). The symbol
          list itself always comes from config/symbols.yaml, keyed by this
          account's `quote_currency` -- never repeated per strategy file.
        """
        self.account = account
        self.quote_currency = quote_currency
        self.strategies = {}
        self.timeframe = self.exchange_id = None

        if configs == "auto":
            configs = []
            for symbol in load_symbols()["usdt"]:  # grid is USDT-only by convention
                slug = symbol.split("/")[0].lower()
                path = f"config/grid_{slug}_usdt.yaml"
                if (ROOT / path).exists():
                    configs.append(path)
                else:
                    print(f"[skip] {account}: no grid config for {symbol} yet ({path})")

        if configs is not None:
            raw_configs = [dict(load_yaml(ROOT / path)) for path in configs]
        else:
            shared = dict(load_yaml(ROOT / config))
            symbols = load_symbols()[quote_currency.lower()]
            raw_configs = [dict(shared, symbol=symbol) for symbol in symbols]

        for raw in raw_configs:
            strategy_name = raw.pop("strategy")
            if "risk_pct_per_grid" in overrides:
                raw.pop("investment_per_grid", None)
            raw["initial_cash"] = total_cash  # only satisfies Config validation -- real cash is shared per account
            raw.update(overrides)
            cfg, strategy = load_strategy(strategy_name, raw)
            self.strategies[cfg.symbol] = strategy
            if self.timeframe is None:
                self.timeframe, self.exchange_id = cfg.timeframe, cfg.exchange
            elif cfg.timeframe != self.timeframe or cfg.exchange != self.exchange_id:
                raise ValueError(f"{account}: every config must share the same timeframe/exchange")
        self.symbols = set(self.strategies)
        self.total_cash = total_cash
        self.broker: ExchangeBroker | None = None
        self.session = None

    def attach(self, shared_exchange: ccxt.Exchange, session_factory) -> None:
        self.session = session_factory()
        existing = self.session.get(CashBalanceRow, self.account)
        capital = existing.cash if existing is not None else self.total_cash
        self.broker = ExchangeBroker(
            self.exchange_id, api_key="", api_secret="", capital=capital,
            quote_currency=self.quote_currency, exchange=shared_exchange,
        )
        db.restore_positions(self.broker, self.session, self.account)
        for strategy in self.strategies.values():
            if hasattr(strategy, "sync_with_broker"):
                strategy.sync_with_broker(self.broker)


def load_fleet(fleet_config_path: str) -> list[SpotAccount]:
    raw = load_yaml(Path(fleet_config_path))
    accounts = []
    for entry in raw["accounts"]:
        overrides = {k: v for k, v in entry.items() if k in ("num_grids", "risk_pct", "geometric")}
        if "risk_pct" in overrides:
            overrides["risk_pct_per_grid"] = overrides.pop("risk_pct")
        accounts.append(
            SpotAccount(
                account=entry["account"],
                configs=entry.get("configs"),
                config=entry.get("config"),
                total_cash=float(entry["total_cash"]),
                overrides=overrides,
                quote_currency=entry.get("quote_currency", "USDT"),
            )
        )
    return accounts


def run_cycle(accounts: list[SpotAccount]) -> None:
    unique = {(symbol, acc.timeframe) for acc in accounts for symbol in acc.symbols}
    exchange_ids = {acc.exchange_id for acc in accounts}
    assert len(exchange_ids) == 1, f"fleet spans multiple exchanges: {exchange_ids}"
    fetched = fetch_latest_bars(unique, exchange_ids.pop())
    bars_by_timeframe: dict[str, dict] = {}
    for (symbol, timeframe), bar in fetched.items():
        bars_by_timeframe.setdefault(timeframe, {})[symbol] = bar

    for acc in accounts:
        bars = bars_by_timeframe.get(acc.timeframe, {})
        run_once(acc.strategies, acc.timeframe, acc.exchange_id, acc.broker, acc.session, acc.account, bars=bars)
        db.save_broker(acc.session, acc.account, acc.broker)


def main() -> None:
    argv = sys.argv[1:]
    fleet_paths = [a for a in argv if a.endswith(".yaml")]
    if not fleet_paths:
        print("Pass a fleet config yaml path, e.g. config/fleet_spot.yaml")
        sys.exit(1)

    load_dotenv()
    api_key = os.environ.get("BINANCE_DEMO_KEY")
    api_secret = os.environ.get("BINANCE_DEMO_SECRET")
    if not api_key or not api_secret:
        print("Set BINANCE_DEMO_KEY and BINANCE_DEMO_SECRET in a .env file.")
        sys.exit(1)

    shared_exchange = ccxt.binance({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
    shared_exchange.enable_demo_trading(True)
    shared_exchange.load_markets()
    print(f"[spot-fleet] connected, one shared client for every account")

    accounts = load_fleet(fleet_paths[0])
    session_factory = db.get_session_factory(DB_PATH)
    for acc in accounts:
        acc.attach(shared_exchange, session_factory)
    print(f"[spot-fleet] {len(accounts)} accounts loaded: {', '.join(a.account for a in accounts)}")

    poll_seconds = 300
    if "--once" in argv:
        run_cycle(accounts)
    else:
        print(f"Starting spot fleet loop, polling every {poll_seconds}s. Ctrl+C to stop.")
        while True:
            run_cycle(accounts)
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
