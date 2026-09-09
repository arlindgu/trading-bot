from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass


@dataclass
class Position:
    lot_id: str
    symbol: str
    size: float
    entry_price: float
    entry_time: str
    tag: str = ""


class PaperBroker:
    """Simulated multi-position ledger shared by backtest and paper trading.

    Positions are keyed by lot id rather than symbol, so a strategy can hold
    several concurrent open lots on the same symbol (e.g. one per grid
    level). Never places real orders or touches a real exchange account --
    buy/sell only mutate this in-memory/JSON-persisted state.
    """

    def __init__(self, cash: float, fee_pct: float = 0.0, slippage_pct: float = 0.0):
        self.cash = cash
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.positions: dict[str, Position] = {}
        self.trade_log: list[dict] = []
        self._lot_counter = itertools.count(1)
        self.last_marks: dict[str, float] = {}

    def buy(self, symbol: str, price: float, size: float, timestamp: str, tag: str = "") -> str:
        fill_price = price * (1 + self.slippage_pct)
        cost = size * fill_price
        fee = cost * self.fee_pct
        self.cash -= cost + fee

        lot_id = f"{symbol}-{next(self._lot_counter)}"
        self.positions[lot_id] = Position(lot_id, symbol, size, fill_price, timestamp, tag)
        self.trade_log.append(
            {
                "lot_id": lot_id,
                "symbol": symbol,
                "side": "buy",
                "price": fill_price,
                "size": size,
                "timestamp": str(timestamp),
                "tag": tag,
            }
        )
        return lot_id

    def sell(self, lot_id: str, price: float, timestamp: str, reason: str = "") -> float:
        position = self.positions.pop(lot_id)
        fill_price = price * (1 - self.slippage_pct)
        proceeds = position.size * fill_price
        fee = proceeds * self.fee_pct
        self.cash += proceeds - fee
        pnl = proceeds - fee - position.size * position.entry_price

        self.trade_log.append(
            {
                "lot_id": lot_id,
                "symbol": position.symbol,
                "side": "sell",
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
        # Remembers marks across calls so that in a shared, multi-symbol
        # broker (e.g. a portfolio backtest), a strategy that only knows its
        # own symbol's price still gets an accurate total-equity figure for
        # sizing -- other symbols fall back to their last-seen mark instead
        # of a stale entry_price.
        self.last_marks.update(marks)
        holdings = sum(p.size * self.last_marks.get(p.symbol, p.entry_price) for p in self.positions.values())
        return self.cash + holdings

    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "fee_pct": self.fee_pct,
            "slippage_pct": self.slippage_pct,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
            "trade_log": self.trade_log,
            "last_marks": self.last_marks,
        }

    @classmethod
    def from_dict(cls, raw: dict) -> "PaperBroker":
        broker = cls(raw["cash"], raw.get("fee_pct", 0.0), raw.get("slippage_pct", 0.0))
        broker.positions = {k: Position(**v) for k, v in raw["positions"].items()}
        broker.trade_log = raw["trade_log"]
        broker.last_marks = raw.get("last_marks", {})
        # Resume the lot counter above the highest id seen so far so new lots
        # from future symbols/strategies never collide with restored ones.
        used = [int(lot_id.rsplit("-", 1)[-1]) for lot_id in broker.positions]
        broker._lot_counter = itertools.count(max(used, default=0) + 1)
        return broker
