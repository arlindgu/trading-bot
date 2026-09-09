"""Broker for REAL long/short futures positions with leverage, via Binance
USDT-M Futures Demo Trading (demo.binance.com -- fake funds, real order
execution/API; classic futures testnet sandbox mode was deprecated by
Binance/ccxt in favor of this).

Not derived from PaperBroker/ExchangeBroker: leverage and short positions
don't map onto a spot ledger's "hold some amount of an asset" model, so
this keeps its own simpler shape (one open position per symbol, tracked by
side/leverage/margin) instead of forcing a fit.

`cash` is a self-tracked budget, same principle as ExchangeBroker: caps
what this bot is allowed to use of the demo account's real balance.
"""
from __future__ import annotations

import ccxt


class FuturesPosition:
    def __init__(
        self,
        lot_id: str,
        symbol: str,
        side: str,
        leverage: int,
        entry_price: float,
        size: float,
        entry_time: str,
        margin: float,
    ):
        self.lot_id = lot_id
        self.symbol = symbol
        self.side = side  # "long" or "short"
        self.leverage = leverage
        self.entry_price = entry_price
        self.size = size  # contracts (base asset units)
        self.entry_time = entry_time
        self.margin = margin  # capital committed as collateral for this position
        self.tag = f"coinflip:{side}:{leverage}"


class FuturesBroker:
    def __init__(self, api_key: str, api_secret: str, capital: float, margin_asset: str = "USDT", demo: bool = True):
        self.exchange = ccxt.binanceusdm({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
        if demo:
            self.exchange.enable_demo_trading(True)
        self.exchange.load_markets()

        self.margin_asset = margin_asset
        self.cash = capital
        # Present so db.save_broker's CashBalanceRow write works unchanged --
        # not semantically used here (real fills already reflect fees/slippage).
        self.fee_pct = 0.0
        self.slippage_pct = 0.0
        self.positions: dict[str, FuturesPosition] = {}  # keyed by symbol -- one bet per symbol at a time
        self.trade_log: list[dict] = []
        self.last_marks: dict[str, float] = {}

    def open_position(self, symbol: str, side: str, leverage: int, margin: float, timestamp) -> str | None:
        if symbol in self.positions:
            return None

        try:
            self.exchange.set_leverage(leverage, symbol)
        except Exception as exc:
            print(f"[leverage failed] {symbol} {leverage}x: {exc}")  # often just "already set", non-fatal

        notional = margin * leverage
        try:
            price = self.exchange.fetch_ticker(symbol)["last"]
            qty = float(self.exchange.amount_to_precision(symbol, notional / price))
            if qty <= 0:
                return None
            if side == "long":
                order = self.exchange.create_market_buy_order(symbol, qty)
            else:
                order = self.exchange.create_market_sell_order(symbol, qty)
        except Exception as exc:
            print(f"[order failed] open {side} {symbol} {leverage}x: {exc}")
            return None

        fill_price = float(order.get("average") or order.get("price") or price)
        filled_qty = float(order.get("filled") or qty)

        lot_id = symbol.replace("/", "")
        self.positions[symbol] = FuturesPosition(lot_id, symbol, side, leverage, fill_price, filled_qty, str(timestamp), margin)
        self.cash -= margin
        self.trade_log.append(
            {
                "lot_id": lot_id,
                "symbol": symbol,
                "side": "buy" if side == "long" else "sell",
                "price": fill_price,
                "size": filled_qty,
                "timestamp": str(timestamp),
                "tag": f"coinflip:{side}:{leverage}",
                "reason": None,
                "pnl": None,
            }
        )
        return lot_id

    def close_position(self, symbol: str, timestamp, reason: str = "coinflip_exit") -> float | None:
        position = self.positions.get(symbol)
        if position is None:
            return None

        try:
            qty = float(self.exchange.amount_to_precision(symbol, position.size))
            if position.side == "long":
                order = self.exchange.create_market_sell_order(symbol, qty, params={"reduceOnly": True})
            else:
                order = self.exchange.create_market_buy_order(symbol, qty, params={"reduceOnly": True})
            fill_price = order.get("average") or order.get("price")
            if fill_price is None:
                # Order went through (the exchange really did close it) but the
                # response omitted a fill price -- fall back to the current
                # ticker rather than crash and leave our books out of sync
                # with a position that's actually already gone.
                fill_price = self.exchange.fetch_ticker(symbol)["last"]
            fill_price = float(fill_price)
        except Exception as exc:
            print(f"[order failed] close {symbol}: {exc}")
            return None

        if position.side == "long":
            pnl = (fill_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - fill_price) * position.size

        self.cash += position.margin + pnl
        del self.positions[symbol]
        self.trade_log.append(
            {
                "lot_id": position.lot_id,
                "symbol": symbol,
                "side": "sell" if position.side == "long" else "buy",
                "price": fill_price,
                "size": position.size,
                "timestamp": str(timestamp),
                "reason": reason,
                "pnl": pnl,
                "tag": position.tag,
            }
        )
        return pnl

    def equity(self, marks: dict[str, float]) -> float:
        self.last_marks.update(marks)
        unrealized = 0.0
        margin_committed = 0.0
        for p in self.positions.values():
            mark = self.last_marks.get(p.symbol, p.entry_price)
            diff = (mark - p.entry_price) if p.side == "long" else (p.entry_price - mark)
            unrealized += diff * p.size
            margin_committed += p.margin
        return self.cash + margin_committed + unrealized
