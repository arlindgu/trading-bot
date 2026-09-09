"""Flask API for the live paper-trading dashboard. Reads the SQLite database
that cli/portfolio_paper_trade.py writes to -- never places orders or writes
trading state itself. Serves the built React dashboard as static files
(see dashboard/README) plus the JSON endpoints it polls.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, abort, jsonify, request, send_from_directory
from sqlalchemy.orm import scoped_session

from tradingbot.config import STATE_DIR
from tradingbot.core import db

# Every account this dashboard can display, and how much starting capital
# to compute Total PnL % against. Add an entry here for any new parallel
# bot account (paper or testnet) that should be selectable in the UI.
ACCOUNTS = {
    "alts8_testnet_500": {"label": "500 USDT", "starting_cash": 500.0},
    "alts8_testnet_1000": {"label": "1,000 USDT", "starting_cash": 1000.0},
    "alts8_testnet_2000": {"label": "2,000 USDT", "starting_cash": 2000.0},
    "alts8_testnet_4000": {"label": "4,000 USDT", "starting_cash": 4000.0},
    "alts8_testnet_8000": {"label": "8,000 USDT", "starting_cash": 8000.0},
}
DEFAULT_ACCOUNT = "alts8_testnet_500"

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


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_dashboard(path: str):
    full_path = DIST_DIR / path
    if path and full_path.exists():
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
