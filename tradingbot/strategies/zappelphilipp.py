"""Zappelphilipp (for laughs): can't sit still for even one candle. Closes
whatever it's holding on every single new candle, then flips a coin on
whether to immediately reopen -- using 1-minute bars instead of the usual
1h, this is the "high velocity" joke strategy: far more trade attempts per
hour than anything else here. Genuinely 50/50 like Coinflip, not rigged to
lose -- it can be profitable if the coinflips happen to land on the right
side of the market's actual moves, same as any other unbiased random
entry. No capped lot accumulation (max_concurrent=1, unlike the other
strategies here) since the whole point is rapid in-and-out, not building
a position.

Note: the fleet process polls once every 300s, so at 1m candles this
samples roughly one bar every 5 minutes rather than literally every
candle -- still far more frequent than every other strategy here, which
all run on 1h bars (~12x more round-trips per hour than a strategy that
trades once an hour).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class ZappelphilippConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    position_pct: float = 0.15
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class ZappelphilippStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, position_pct: float = 0.15, rng: random.Random | None = None):
        super().__init__(symbol, position_pct, max_concurrent=1)
        self.rng = rng or random.Random()
        self.trade_count = 0

    @classmethod
    def from_config(cls, cfg: ZappelphilippConfig) -> "ZappelphilippStrategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return
        if self.lot_id is not None:
            self._exit(bar, broker, reason="zappelphilipp_cant_sit_still")
        self.trade_count += 1
        if self.rng.choice([True, False]):
            self._enter(bar, broker, tag=f"zappelphilipp:trade#{self.trade_count}")
