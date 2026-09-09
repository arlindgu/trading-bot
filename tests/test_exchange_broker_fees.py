from tradingbot.core.exchange_broker import ExchangeBroker


class _StubExchange:
    def __init__(self, fill_price: float, fee_cost: float, fee_currency: str):
        self.fill_price = fill_price
        self.fee_cost = fee_cost
        self.fee_currency = fee_currency

    def amount_to_precision(self, symbol, amount):
        return amount

    def _order(self, qty):
        return {
            "average": self.fill_price,
            "filled": qty,
            "fee": {"cost": self.fee_cost, "currency": self.fee_currency},
        }

    def create_market_buy_order(self, symbol, qty):
        return self._order(qty)

    def create_market_sell_order(self, symbol, qty):
        return self._order(qty)


def _broker(exchange, quote_currency="USDT"):
    return ExchangeBroker("binance", "k", "s", capital=1000.0, quote_currency=quote_currency, exchange=exchange)


def test_bnb_denominated_fee_is_recorded_but_not_subtracted_from_cash():
    # This is the real, common case: Binance discounts the taker fee when
    # paid in BNB, a currency our tracked `cash` (USDT/USDC) has nothing to
    # do with -- the cost is real, just entirely outside our budget.
    exchange = _StubExchange(fill_price=10.0, fee_cost=0.00001, fee_currency="BNB")
    broker = _broker(exchange)

    broker.buy("LINK/USDT", price=10.0, size=1.0, timestamp="t0")

    assert broker.cash == 1000.0 - 10.0  # only the trade cost left cash, not the BNB fee
    assert broker.trade_log[0]["fee_cost"] == 0.00001
    assert broker.trade_log[0]["fee_currency"] == "BNB"


def test_quote_currency_fee_is_subtracted_from_cash():
    # If BNB ever runs out, Binance falls back to charging the fee in the
    # quote currency itself -- that IS a real hit to our tracked cash.
    exchange = _StubExchange(fill_price=10.0, fee_cost=0.05, fee_currency="USDT")
    broker = _broker(exchange)

    broker.buy("LINK/USDT", price=10.0, size=1.0, timestamp="t0")

    assert broker.cash == 1000.0 - 10.0 - 0.05


def test_sell_fee_in_quote_currency_reduces_reported_pnl():
    exchange = _StubExchange(fill_price=10.0, fee_cost=0.0, fee_currency="BNB")
    broker = _broker(exchange)
    lot_id = broker.buy("LINK/USDT", price=10.0, size=1.0, timestamp="t0")

    exchange.fill_price = 12.0
    exchange.fee_cost = 0.06
    exchange.fee_currency = "USDT"
    pnl = broker.sell(lot_id, price=12.0, timestamp="t1")

    assert pnl == (12.0 - 10.0) - 0.06
