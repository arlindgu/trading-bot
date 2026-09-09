"""Contrarian-Self (for laughs): holds for a fixed number of candles, then
closes -- if that trade lost money, sits out the next entry opportunity
out of spite; if it won, jumps right back in. Anti-momentum on its own
track record, not the market's."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class ContrarianSelfConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    hold_bars: int = 6
    position_pct: float | list[float] = 0.15
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class ContrarianSelfStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, hold_bars: int = 6, position_pct: float | list[float] = 0.15):
        super().__init__(symbol, position_pct)
        self.hold_bars = hold_bars
        self.bars_held = 0
        self.skip_next_entry = False

    @classmethod
    def from_config(cls, cfg: ContrarianSelfConfig) -> "ContrarianSelfStrategy":
        return cls(cfg.symbol, cfg.hold_bars, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        if self.lot_id is not None:
            self.bars_held += 1
            if self.bars_held >= self.hold_bars:
                self._exit(bar, broker, reason="contrarian_self_cycle_end")
                if self.lot_id is None:  # exit actually went through
                    self.bars_held = 0
                    last_pnl = broker.trade_log[-1].get("pnl")
                    self.skip_next_entry = last_pnl is not None and last_pnl < 0
            return

        if self.skip_next_entry:
            self.skip_next_entry = False
            return
        self._enter(bar, broker, tag="contrarian_self:entering")
