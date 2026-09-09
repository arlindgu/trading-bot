"""Broker that places REAL orders against an authenticated exchange account
(the spot side of Binance Demo Trading by default) instead of simulating
fills.

Same buy/sell/equity interface as PaperBroker (it subclasses it), so
GridStrategy works against either unmodified. Only buy/sell differ: they
submit a real market order and use the REAL fill price/quantity the
exchange reports, not the theoretical grid price.

`cash` is a self-tracked budget (like PaperBroker's), NOT the account's
real wallet balance -- a testnet (or real) account can hold far more than
you want this bot to touch, so `capital` caps what it's allowed to use,
same as choosing how much of a real exchange balance to risk.

Position bookkeeping (which "lot" belongs to which grid level) is tracked
entirely on our side, same as PaperBroker -- a real spot wallet only holds
a pooled balance per asset, it has no concept of individual lots. As long
as this bot is the only thing trading the account, our ledger and the real
wallet stay in sync for whatever slice of the balance it's using.
"""
from __future__ import annotations

import ccxt

from tradingbot.core.broker import PaperBroker, Position


class ExchangeBroker(PaperBroker):
    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        api_secret: str,
        capital: float,
        quote_currency: str = "USDT",
        demo: bool = True,
        exchange: "ccxt.Exchange | None" = None,
    ):
        super().__init__(cash=capital, fee_pct=0.0, slippage_pct=0.0)
        self.quote_currency = quote_currency

        if exchange is not None:
            # Shared, already-authenticated, already-load_markets()'d client
            # (see cli/spot_fleet.py) -- every account in a fleet process
            # already trades under the same real demo account/API key, so
            # there is no reason for each account's broker to redo the
            # network round trips (load_markets, fetch_wallet_balance) that
            # constructing its own client from scratch would cost.
            self.exchange = exchange
            return

        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
        if demo:
            self.exchange.enable_demo_trading(True)
        self.exchange.load_markets()  # needed for amount_to_precision below

        wallet_balance = self.fetch_wallet_balance()
        if wallet_balance < capital:
            print(
                f"[warning] requested budget {capital} {quote_currency} exceeds the account's "
                f"free balance ({wallet_balance} {quote_currency}) -- orders may fail once it runs out."
            )

    def fetch_wallet_balance(self) -> float:
        """The account's REAL free balance -- informational only (e.g. a
        startup sanity check). Trading decisions use `self.cash`, the
        self-tracked budget, not this."""
        balance = self.exchange.fetch_balance()
        return float(balance.get("free", {}).get(self.quote_currency, 0.0))

    @staticmethod
    def _extract_fee(order: dict) -> tuple[float, str | None]:
        """Binance includes fee info directly in a spot market order's
        response (unlike futures, which needs a separate fetch_my_trades
        call) -- but the fee is very often charged in BNB, not the quote
        currency, if the account holds any (a BNB discount on the standard
        taker fee). `self.cash` only tracks `quote_currency`, so a
        BNB-denominated fee is a real cost that happens entirely outside
        our tracked budget -- still recorded on the trade for display, just
        not subtracted from `cash` unless the currencies actually match
        (e.g. BNB balance ran out and Binance fell back to the quote asset)."""
        fee = order.get("fee") or (order.get("fees") or [None])[0] or {}
        return float(fee.get("cost") or 0.0), fee.get("currency")

    def buy(self, symbol: str, price: float, size: float, timestamp, tag: str = "") -> str | None:
        try:
            size = float(self.exchange.amount_to_precision(symbol, size))
            order = self.exchange.create_market_buy_order(symbol, size)
        except Exception as exc:
            print(f"[order failed] buy {symbol} size={size}: {exc}")
            return None

        fill_price = float(order.get("average") or order.get("price") or price)
        filled_size = float(order.get("filled") or size)
        fee_cost, fee_currency = self._extract_fee(order)
        self.cash -= filled_size * fill_price
        if fee_currency == self.quote_currency:
            self.cash -= fee_cost

        lot_id = f"{symbol}-{next(self._lot_counter)}"
        self.positions[lot_id] = Position(lot_id, symbol, filled_size, fill_price, str(timestamp), tag)
        self.trade_log.append(
            {
                "lot_id": lot_id,
                "symbol": symbol,
                "side": "buy",
                "price": fill_price,
                "size": filled_size,
                "timestamp": str(timestamp),
                "tag": tag,
                "fee_cost": fee_cost,
                "fee_currency": fee_currency,
            }
        )
        return lot_id

    def sell(self, lot_id: str, price: float, timestamp, reason: str = "") -> float | None:
        position = self.positions.get(lot_id)
        if position is None:
            return None

        try:
            sell_size = float(self.exchange.amount_to_precision(position.symbol, position.size))
            order = self.exchange.create_market_sell_order(position.symbol, sell_size)
        except Exception as exc:
            print(f"[order failed] sell {position.symbol} size={position.size}: {exc}")
            return None

        del self.positions[lot_id]
        fill_price = float(order.get("average") or order.get("price") or price)
        filled_size = float(order.get("filled") or position.size)
        fee_cost, fee_currency = self._extract_fee(order)
        proceeds = filled_size * fill_price
        self.cash += proceeds
        pnl = proceeds - position.size * position.entry_price
        if fee_currency == self.quote_currency:
            self.cash -= fee_cost
            pnl -= fee_cost

        self.trade_log.append(
            {
                "lot_id": lot_id,
                "symbol": position.symbol,
                "side": "sell",
                "price": fill_price,
                "size": filled_size,
                "timestamp": str(timestamp),
                "reason": reason,
                "pnl": pnl,
                "tag": position.tag,
                "fee_cost": fee_cost,
                "fee_currency": fee_currency,
            }
        )
        return pnl
