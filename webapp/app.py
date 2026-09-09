"""Flask API for the live paper-trading dashboard. Reads the SQLite database
that cli/portfolio_paper_trade.py writes to -- never places orders or writes
trading state itself. Serves the built React dashboard as static files
(see dashboard/README) plus the JSON endpoints it polls.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ccxt
from dotenv import load_dotenv
from flask import Flask, abort, jsonify, request, send_from_directory
from sqlalchemy.orm import scoped_session

from tradingbot.config import ROOT, STATE_DIR, load_yaml
from tradingbot.core import db
from tradingbot.strategies.grid import GridStrategy

load_dotenv()


def _grid_levels(symbol: str) -> list[float]:
    """Rebuild a symbol's grid price ladder from its config yaml -- the
    same levels GridStrategy computed when it opened each position, used to
    show each open position's sell target in the dashboard (the target
    itself isn't stored in the DB, only the slot index via the trade tag)."""
    slug = symbol.split("/")[0].lower()
    raw = load_yaml(ROOT / "config" / f"grid_{slug}_usdt.yaml")
    return GridStrategy._build_levels(raw["lower_price"], raw["upper_price"], raw["num_grids"], raw.get("geometric", False))


def _target_price(tag: str, levels: list[float]) -> float | None:
    if not tag or not tag.startswith("grid:"):
        return None
    try:
        index = int(tag.split(":", 1)[1])
    except ValueError:
        return None
    return levels[index + 1] if 0 <= index + 1 < len(levels) else None


def _coinflip_info(tag: str) -> dict | None:
    if not tag or not tag.startswith("coinflip:"):
        return None
    parts = tag.split(":")
    _, side, leverage = parts[0], parts[1], parts[2]
    return {"side": side, "leverage": int(leverage)}


def _info(tag: str) -> str | None:
    """Generic fallback for any strategy that isn't grid/coinflip: every
    strategy writes a short human-readable state into its Position.tag
    (e.g. "moon:full", "fomo:pump:+6.2%") -- shown verbatim by the
    dashboard's generic Info column so a new strategy needs zero UI code
    to be visible, only a good tag string."""
    if not tag or tag.startswith("grid:") or tag.startswith("coinflip:"):
        return None
    return tag

# Every account this dashboard can display, grouped by which strategy runs
# it, with how much starting capital to compute Total PnL % against. Add an
# entry here for any new parallel bot account that should be selectable.
ACCOUNTS = {
    "grid_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "grid"},
    "ma_crossover_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "ma_crossover"},
    "donchian_breakout_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "donchian_breakout"},
    "rsi_reversion_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "rsi_reversion"},
    "bollinger_reversion_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "bollinger_reversion"},
    "macd_momentum_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "macd_momentum"},
    "atr_breakout_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "atr_breakout"},
    "volume_spike_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "volume_spike"},
    "relative_momentum_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "relative_momentum"},
    "buy_and_hold_500": {"label": "500 USDT", "starting_cash": 500.0, "strategy": "buy_and_hold"},
    "coinflip_usdt_500": {"label": "500 USDT (1-5x)", "starting_cash": 500.0, "strategy": "coinflip"},
    "coinflip_usdc_500": {"label": "500 USDC (1-20x)", "starting_cash": 500.0, "strategy": "coinflip"},
    "moon_phase_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "moon_phase"},
    "friday13_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "friday13"},
    "prime_number_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "prime_number"},
    "contrarian_self_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "contrarian_self"},
    "fomo_bot_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "fomo_bot"},
    "diamond_hands_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "diamond_hands"},
    "buy_high_sell_low_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "buy_high_sell_low"},
    "zodiac_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "zodiac"},
    "hash_sentiment_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "hash_sentiment"},
    "zappelphilipp_500": {"label": "500 USDC", "starting_cash": 500.0, "strategy": "zappelphilipp"},
}
DEFAULT_ACCOUNT = "grid_500"

DB_PATH = STATE_DIR / "trading.db"
DIST_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "dist"

app = Flask(__name__, static_folder=None)
# scoped_session hands out one Session per request and session.remove() (in
# the teardown handler below) returns its connection to the pool -- without
# this, every request leaked a connection and the pool filled up within a
# couple of dashboard polling cycles.
Session = scoped_session(db.get_session_factory(DB_PATH))


@app.teardown_appcontext
def remove_session(exception=None):
    Session.remove()


def _account() -> str:
    account = request.args.get("account", DEFAULT_ACCOUNT)
    if account not in ACCOUNTS:
        abort(400, f"unknown account {account!r}")
    return account


@app.route("/api/accounts")
def accounts():
    return jsonify([{"id": account_id, **meta} for account_id, meta in ACCOUNTS.items()])


# One Binance Demo Trading account, two balance pools (spot, futures) --
# both endpoints below read the same BINANCE_DEMO_KEY/_SECRET now. Cached so
# the dashboard's ~30s polling (times however many people have it open)
# doesn't add to the same account's Binance rate limit the bots already
# compete for.
_wallet_cache: dict = {"value": None, "fetched_at": 0.0}
WALLET_CACHE_SECONDS = 60


@app.route("/api/wallet_balance")
def wallet_balance():
    """Spot side of the demo account (USDT + USDC), used by grid and the
    other spot-side strategies."""
    now = time.time()
    if _wallet_cache["value"] is None or now - _wallet_cache["fetched_at"] > WALLET_CACHE_SECONDS:
        api_key = os.environ.get("BINANCE_DEMO_KEY")
        api_secret = os.environ.get("BINANCE_DEMO_SECRET")
        if not api_key or not api_secret:
            return jsonify({"usdt": None, "usdc": None, "error": "no demo API key configured"}), 200
        exchange = ccxt.binance({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
        exchange.enable_demo_trading(True)
        balance = exchange.fetch_balance()
        _wallet_cache["value"] = {
            "usdt": float(balance.get("free", {}).get("USDT", 0.0)),
            "usdc": float(balance.get("free", {}).get("USDC", 0.0)),
        }
        _wallet_cache["fetched_at"] = now
    return jsonify(_wallet_cache["value"])


_futures_wallet_cache: dict = {"value": None, "fetched_at": 0.0}


@app.route("/api/futures_wallet_balance")
def futures_wallet_balance():
    """Futures side of the same demo account (USDT + USDC margin), used by
    coinflip."""
    now = time.time()
    if _futures_wallet_cache["value"] is None or now - _futures_wallet_cache["fetched_at"] > WALLET_CACHE_SECONDS:
        api_key = os.environ.get("BINANCE_DEMO_KEY")
        api_secret = os.environ.get("BINANCE_DEMO_SECRET")
        if not api_key or not api_secret:
            return jsonify({"usdt": None, "usdc": None, "error": "no demo API key configured"}), 200
        exchange = ccxt.binanceusdm({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
        exchange.enable_demo_trading(True)
        balance = exchange.fetch_balance()
        _futures_wallet_cache["value"] = {
            "usdt": float(balance.get("free", {}).get("USDT", 0.0)),
            "usdc": float(balance.get("free", {}).get("USDC", 0.0)),
        }
        _futures_wallet_cache["fetched_at"] = now
    return jsonify(_futures_wallet_cache["value"])


@app.route("/api/status")
def status():
    account = _account()
    starting_cash = ACCOUNTS[account]["starting_cash"]
    session = Session()
    broker_positions = db.load_broker(session, account, 0, 0, 0).positions
    symbols = db.get_symbols(session, account)

    per_symbol = {}
    total_realized = 0.0
    total_unrealized = 0.0
    for symbol in symbols:
        history = db.get_symbol_history(session, account, symbol)
        latest = history[-1] if history else None
        open_count = sum(1 for p in broker_positions.values() if p.symbol == symbol)
        closed_count = sum(1 for t in db.get_trades_for_symbol(session, account, symbol) if t["side"] == "sell")
        realized = latest["realized_pnl"] if latest else 0.0
        unrealized = latest["unrealized_pnl"] if latest else 0.0
        total_realized += realized
        total_unrealized += unrealized
        per_symbol[symbol] = {
            "open_positions": open_count,
            "closed_trades": closed_count,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
            "total_pnl": realized + unrealized,
            "mark_price": latest["mark_price"] if latest else None,
        }

    portfolio_history = db.get_portfolio_history(session, account)
    latest_snapshot = portfolio_history[-1] if portfolio_history else None

    total_pnl = total_realized + total_unrealized
    return jsonify(
        {
            "equity": latest_snapshot["equity"] if latest_snapshot else None,
            "cash": latest_snapshot["cash"] if latest_snapshot else None,
            "starting_cash": starting_cash,
            "total_realized_pnl": total_realized,
            "total_unrealized_pnl": total_unrealized,
            "total_pnl": total_pnl,
            "total_pnl_pct": (total_pnl / starting_cash * 100) if starting_cash else None,
            "open_positions": len(broker_positions),
            "last_updated": latest_snapshot["timestamp"] if latest_snapshot else None,
            "per_symbol": per_symbol,
        }
    )


@app.route("/api/equity_history")
def equity_history():
    session = Session()
    return jsonify(db.get_portfolio_history(session, _account()))


@app.route("/api/symbols/<path:symbol>/history")
def symbol_history(symbol: str):
    session = Session()
    return jsonify(db.get_symbol_history(session, _account(), symbol))


@app.route("/api/symbols/<path:symbol>/trades")
def symbol_trades(symbol: str):
    session = Session()
    return jsonify(db.get_trades_for_symbol(session, _account(), symbol))


@app.route("/api/symbols/<path:symbol>/positions")
def symbol_positions(symbol: str):
    session = Session()
    positions = db.get_open_positions_for_symbol(session, _account(), symbol)
    try:
        levels = _grid_levels(symbol)
    except FileNotFoundError:
        levels = []
    for p in positions:
        p["target_price"] = _target_price(p["tag"], levels) if levels else None
        p["coinflip"] = _coinflip_info(p["tag"])
        p["info"] = _info(p["tag"])
    return jsonify(positions)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_dashboard(path: str):
    full_path = DIST_DIR / path
    if path and full_path.exists():
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
