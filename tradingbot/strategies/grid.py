from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.base import Strategy


@dataclass
class GridConfig:
    symbol: str
    exchange: str
    timeframe: str
    lower_price: float
    upper_price: float
    num_grids: int
    fee_pct: float
    slippage_pct: float
    geometric: bool = False
    lookback_days: int = 90
    investment_per_grid: float | None = None
    risk_pct_per_grid: float | None = None  # alternative to investment_per_grid: fraction of CURRENT equity per slot, recomputed on every buy
    initial_cash: float | None = None

    def __post_init__(self) -> None:
        if self.investment_per_grid is None and self.risk_pct_per_grid is None:
            raise ValueError("set either investment_per_grid or risk_pct_per_grid in the config")
        if self.risk_pct_per_grid is not None and self.initial_cash is None:
            raise ValueError("risk_pct_per_grid requires initial_cash to also be set (used to fund the broker)")

    @property
    def starting_cash(self) -> float:
        # By default, fund exactly enough cash to fill every grid slot once.
        return self.initial_cash if self.initial_cash is not None else self.num_grids * self.investment_per_grid


@dataclass
class _Slot:
    buy_price: float
    sell_price: float
    lot_id: str | None = None  # set while a lot bought at buy_price is open


class GridStrategy(Strategy):
    """Classic neutral grid trading.

    Splits [lower_price, upper_price] into `num_grids` slots. Each slot buys
    at its lower boundary and sells at its upper boundary, then resets to
    buy again -- so it profits from price oscillating inside the range,
    independent of overall trend. Price moving outside the range simply
    stops new activity on the slots beyond it (grid bots are range-bound by
    design, not a bet on the range holding forever).

    Pass exactly one of `investment_per_grid` (a fixed quote-currency amount
    per slot, same size every time -- no compounding) or `risk_pct_per_grid`
    (a fraction of CURRENT equity, recomputed on every buy -- realized gains
    grow future position sizes, and drawdowns shrink them, matching how a
    real account would size trades against its live balance).
    """

    def __init__(
        self,
        symbol: str,
        lower_price: float,
        upper_price: float,
        num_grids: int,
        geometric: bool = False,
        investment_per_grid: float | None = None,
        risk_pct_per_grid: float | None = None,
    ):
        if upper_price <= lower_price:
            raise ValueError("upper_price must be greater than lower_price")
        if num_grids < 1:
            raise ValueError("num_grids must be >= 1")
        if (investment_per_grid is None) == (risk_pct_per_grid is None):
            raise ValueError("pass exactly one of investment_per_grid or risk_pct_per_grid")

        self.symbol = symbol
        self.fixed_investment_per_grid = investment_per_grid
        self.risk_pct_per_grid = risk_pct_per_grid
        levels = self._build_levels(lower_price, upper_price, num_grids, geometric)
        self.slots = [_Slot(buy_price=levels[i], sell_price=levels[i + 1]) for i in range(num_grids)]

    @classmethod
    def from_config(cls, cfg: GridConfig) -> "GridStrategy":
        return cls(
            symbol=cfg.symbol,
            lower_price=cfg.lower_price,
            upper_price=cfg.upper_price,
            num_grids=cfg.num_grids,
            geometric=cfg.geometric,
            investment_per_grid=cfg.investment_per_grid,
            risk_pct_per_grid=cfg.risk_pct_per_grid,
        )

    def sync_with_broker(self, broker: PaperBroker) -> None:
        """Reconstruct which slots currently hold a position from the
        broker's actual open positions for this symbol.

        Slot-filled state (`_Slot.lot_id`) lives only in this strategy
        instance's memory, not in the broker/DB. A live process that
        restarts (crash, redeploy, Pi reboot) would otherwise "forget" every
        slot it had already bought and re-buy them all on the next bar --
        call this once right after constructing the strategy whenever the
        broker was loaded from persisted state.

        Matches by the slot index embedded in each position's tag
        (`grid:<index>`), not by nearest buy_price: a cold start can clamp
        several slots' fill price to the same bar.high (see `on_bar`),
        giving them identical entry_price -- nearest-price matching would
        collapse those onto one slot and leave the others looking empty.
        """
        for slot in self.slots:
            slot.lot_id = None
        for lot_id, position in broker.positions.items():
            if position.symbol != self.symbol or not position.tag.startswith("grid:"):
                continue
            index = int(position.tag.split(":", 1)[1])
            if 0 <= index < len(self.slots):
                self.slots[index].lot_id = lot_id

    @staticmethod
    def _build_levels(lower: float, upper: float, num_grids: int, geometric: bool) -> list[float]:
        if geometric:
            ratio = (upper / lower) ** (1 / num_grids)
            return [lower * ratio**i for i in range(num_grids + 1)]
        step = (upper - lower) / num_grids
        return [lower + step * i for i in range(num_grids + 1)]

    def _current_investment_per_grid(self, bar: Bar, broker: PaperBroker) -> float:
        if self.fixed_investment_per_grid is not None:
            return self.fixed_investment_per_grid
        equity = broker.equity({self.symbol: bar.close})
        return equity * self.risk_pct_per_grid

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        # Sells first so a slot that completes this bar frees its cash (and,
        # in risk_pct_per_grid mode, its realized gain) for this bar's buys.
        # Fill price is clamped to the bar's actual [low, high] -- if the
        # level sits outside that range (e.g. a resting sell far below a
        # price that gapped up), a real order fills at the best available
        # market price, not at the stale level price.
        for slot in self.slots:
            if slot.lot_id is not None and bar.high >= slot.sell_price:
                fill_price = max(slot.sell_price, bar.low)
                result = broker.sell(slot.lot_id, fill_price, bar.timestamp, reason="grid_sell")
                # None means the order failed (e.g. a live exchange rejected
                # it) -- the position is still actually held, so keep the
                # slot marked filled and retry on the next bar instead of
                # losing track of it.
                if result is not None:
                    slot.lot_id = None

        # One size for the whole bar: in risk_pct_per_grid mode this is a
        # snapshot of post-sell equity, not recomputed per slot -- buying
        # doesn't materially move mark-to-market equity, so recomputing
        # per-slot would cost more without changing the result.
        investment = self._current_investment_per_grid(bar, broker)

        # Nearest-to-price slots first: if a fast move triggers more buys
        # than available cash covers, fill the closest levels before the
        # deeper ones.
        indexed_slots = sorted(enumerate(self.slots), key=lambda pair: -pair[1].buy_price)
        for index, slot in indexed_slots:
            if slot.lot_id is not None or bar.low > slot.buy_price:
                continue
            fill_price = min(slot.buy_price, bar.high)
            required_cash = investment * (1 + broker.fee_pct + broker.slippage_pct)
            if broker.cash < required_cash:
                continue
            size = investment / fill_price
            slot.lot_id = broker.buy(self.symbol, fill_price, size, bar.timestamp, tag=f"grid:{index}")
