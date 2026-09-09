from tradingbot.core.futures_broker import FuturesBroker


class _StubExchange:
    """Just enough of ccxt's binanceusdm surface for FuturesBroker to run
    against, with a scripted fee so the math can be asserted exactly."""

    def __init__(self, fill_price: float, fee_cost: float):
        self.fill_price = fill_price
        self.fee_cost = fee_cost
        self.next_order_id = 1

    def set_leverage(self, leverage, symbol):
        pass

    def fetch_ticker(self, symbol):
        return {"last": self.fill_price}

    def amount_to_precision(self, symbol, amount):
        return amount

    def create_market_buy_order(self, symbol, qty, params=None):
        order_id = self.next_order_id
        self.next_order_id += 1
        return {"id": order_id, "average": self.fill_price, "filled": qty}

    def create_market_sell_order(self, symbol, qty, params=None):
        order_id = self.next_order_id
        self.next_order_id += 1
        return {"id": order_id, "average": self.fill_price, "filled": qty}

    def fetch_my_trades(self, symbol, params=None):
        return [{"fee": {"cost": self.fee_cost, "currency": "USDT"}}]


def test_entry_fee_is_subtracted_from_cash_immediately():
    exchange = _StubExchange(fill_price=100.0, fee_cost=0.5)
    broker = FuturesBroker("k", "s", capital=1000.0, margin_asset="USDT", exchange=exchange)

    broker.open_position("BTC/USDT:USDT", "long", leverage=1, margin=100.0, timestamp="t0")

    assert broker.cash == 1000.0 - 100.0 - 0.5  # margin + entry fee both left cash


def test_close_pnl_nets_both_entry_and_close_fees():
    exchange = _StubExchange(fill_price=100.0, fee_cost=1.0)
    broker = FuturesBroker("k", "s", capital=1000.0, margin_asset="USDT", exchange=exchange)

    lot_id = broker.open_position("BTC/USDT:USDT", "long", leverage=1, margin=100.0, timestamp="t0")
    cash_after_open = broker.cash  # 1000 - 100 margin - 1 entry fee = 899

    exchange.fill_price = 110.0  # price moved up 10 -- a real gain before fees
    pnl = broker.close_position(lot_id, timestamp="t1")

    # raw price pnl = (110-100)*1 = 10; net of both $1 fees = 8
    assert pnl == 10.0 - 1.0 - 1.0
    # cash: margin (100) returned + raw pnl (10) - close fee (1) -- entry
    # fee is NOT subtracted again, it already left cash at open time.
    assert broker.cash == cash_after_open + 100.0 + 10.0 - 1.0


def test_trade_log_records_fee_cost_and_currency_on_both_legs():
    exchange = _StubExchange(fill_price=100.0, fee_cost=0.3)
    broker = FuturesBroker("k", "s", capital=1000.0, margin_asset="USDT", exchange=exchange)

    lot_id = broker.open_position("BTC/USDT:USDT", "long", leverage=1, margin=100.0, timestamp="t0")
    broker.close_position(lot_id, timestamp="t1")

    assert broker.trade_log[0]["fee_cost"] == 0.3
    assert broker.trade_log[0]["fee_currency"] == "USDT"
    assert broker.trade_log[1]["fee_cost"] == 0.3
    assert broker.trade_log[1]["fee_currency"] == "USDT"
