"""Broker for REAL long/short futures positions with leverage, via Binance
USDT-M Futures Demo Trading (demo.binance.com -- fake funds, real order
execution/API; classic futures testnet sandbox mode was deprecated by
Binance/ccxt in favor of this).

Not derived from PaperBroker/ExchangeBroker: leverage and short positions
don't map onto a spot ledger's "hold some amount of an asset" model, so
this keeps its own simpler shape (positions tracked by side/leverage/margin
per lot, keyed by lot id like PaperBroker -- several concurrent lots on the
same symbol are allowed) instead of forcing a fit.

Bookkeeping note: several lots on the same symbol are OUR ledger's view --
Binance nets same-symbol exposure into one real position per account
(one-way mode), same as any other case in this project where multiple
bots/lots share one real demo account. Each lot's own entry price/margin/
PnL is still tracked correctly on our side; only the real exchange's net
position size can drift from "sum of our lots" if lots on the same symbol
end up on opposite sides.

`cash` is a self-tracked budget, same principle as ExchangeBroker: caps
what this bot is allowed to use of the demo account's real balance.
"""
from __future__ import annotations

import itertools

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
        tp_pct: float | None = None,
        sl_pct: float | None = None,
        strategy: str = "coinflip",
        entry_fee: float = 0.0,
    ):
        self.lot_id = lot_id
        self.symbol = symbol
        self.side = side  # "long" or "short"
        self.leverage = leverage
        self.entry_price = entry_price
        self.size = size  # contracts (base asset units)
        self.entry_time = entry_time
        self.margin = margin  # capital committed as collateral for this position
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        # Real fee (in margin_asset) charged when this lot opened -- netted
        # against the closing fee into close_position's reported pnl, so
        # "pnl" is the true round-trip result, not just the raw price move.
        self.entry_fee = entry_fee
        # `strategy` is the tag prefix, not just cosmetic -- webapp/app.py's
        # `_coinflip_info` only renders the structured Side/Lev columns for
        # tags starting "coinflip:"; every other futures strategy falls
        # through to the generic Info column via its own prefix instead.
        if tp_pct is not None and sl_pct is not None:
            self.tag = f"{strategy}:{side}:{leverage}:tp{tp_pct}:sl{sl_pct}"
        else:
            self.tag = f"{strategy}:{side}:{leverage}"


class FuturesBroker:
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        capital: float,
        margin_asset: str = "USDT",
        demo: bool = True,
        exchange: "ccxt.Exchange | None" = None,
    ):
        if exchange is not None:
            # Shared, already-authenticated, already-load_markets()'d client
            # (see cli/futures_fleet.py) -- every coinflip account already
            # trades under the same real demo account/API key, so there is
            # no reason for each account's broker to redo load_markets().
            self.exchange = exchange
        else:
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
        self.positions: dict[str, FuturesPosition] = {}  # keyed by lot id -- several lots per symbol allowed
        self.trade_log: list[dict] = []
        self.last_marks: dict[str, float] = {}
        self._lot_counter = itertools.count(1)

    def _fetch_fee(self, symbol: str, order: dict) -> float:
        """Unlike spot, a futures create_order response never includes fee
        info inline -- Binance charges it in the margin asset (confirmed
        against the real demo account: ~0.04% taker on a USDT-margined
        fill), a real cost against `self.cash`, not a side cost in a
        different asset like spot's BNB fee often is. Requires one extra
        call per fill; on failure, treat the fee as unknown (0.0) rather
        than blocking the trade that already went through."""
        try:
            trades = self.exchange.fetch_my_trades(symbol, params={"orderId": order.get("id")})
            return sum(float((t.get("fee") or {}).get("cost") or 0.0) for t in trades)
        except Exception as exc:
            print(f"[fee lookup failed] {symbol}: {exc}")
            return 0.0

    def open_position(
        self,
        symbol: str,
        side: str,
        leverage: int,
        margin: float,
        timestamp,
        tp_pct: float | None = None,
        sl_pct: float | None = None,
        strategy: str = "coinflip",
    ) -> str | None:
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
        entry_fee = self._fetch_fee(symbol, order)

        lot_id = f"{symbol.replace('/', '')}-{next(self._lot_counter)}"
        position = FuturesPosition(
            lot_id, symbol, side, leverage, fill_price, filled_qty, str(timestamp), margin,
            tp_pct, sl_pct, strategy, entry_fee,
        )
        self.positions[lot_id] = position
        self.cash -= margin + entry_fee
        self.trade_log.append(
            {
                "lot_id": lot_id,
                "symbol": symbol,
                "side": "buy" if side == "long" else "sell",
                "price": fill_price,
                "size": filled_qty,
                "timestamp": str(timestamp),
                "tag": position.tag,
                "reason": None,
                "pnl": None,
                "fee_cost": entry_fee,
                "fee_currency": self.margin_asset,
            }
        )
        return lot_id

    def close_position(self, lot_id: str, timestamp, reason: str = "coinflip_exit") -> float | None:
        position = self.positions.get(lot_id)
        if position is None:
            return None
        symbol = position.symbol

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
            raw_pnl = (fill_price - position.entry_price) * position.size
        else:
            raw_pnl = (position.entry_price - fill_price) * position.size

        close_fee = self._fetch_fee(symbol, order)
        # `pnl` (reported/displayed) nets BOTH fees for the true round-trip
        # result. `cash` only gets close_fee subtracted here -- entry_fee
        # already left cash back at open_position time, subtracting it
        # again here would double-count it.
        pnl = raw_pnl - position.entry_fee - close_fee
        self.cash += position.margin + raw_pnl - close_fee
        del self.positions[lot_id]
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
                "fee_cost": close_fee,
                "fee_currency": self.margin_asset,
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
