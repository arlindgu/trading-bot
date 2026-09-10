"""Sekundenschlaf-Bot (for laughs): a micro-sleeper -- opens a tiny
position, immediately rolls a nap length of 1-3 candles, and does
absolutely nothing until it wakes back up, closes, and rolls a fresh nap.
On 1-minute bars that's still a full trade cycle every couple of minutes
at most, just with a snooze button between rounds instead of Herzschlag's
zero rest."""
from __future__ import annotations

import random
from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class SekundenschlafBotConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    min_nap_bars: int = 1
    max_nap_bars: int = 3
    position_pct: float | list[float] = 0.04
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class SekundenschlafBotStrategy(SingleLotStrategy):
    def __init__(
        self, symbol: str, min_nap_bars: int = 1, max_nap_bars: int = 3,
        position_pct: float | list[float] = 0.04, rng: random.Random | None = None,
    ):
        super().__init__(symbol, position_pct, max_concurrent=1, rng=rng)
        self.min_nap_bars = min_nap_bars
        self.max_nap_bars = max_nap_bars
        self.nap_bars_left = 0
        self.round = 0

    @classmethod
    def from_config(cls, cfg: SekundenschlafBotConfig) -> "SekundenschlafBotStrategy":
        return cls(cfg.symbol, cfg.min_nap_bars, cfg.max_nap_bars, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        if self.lot_id is None:
            self.round += 1
            self._enter(bar, broker, tag=f"sekundenschlaf:round#{self.round}:awake")
            self.nap_bars_left = self.rng.randint(self.min_nap_bars, self.max_nap_bars)
            return

        if self.nap_bars_left > 0:
            self.nap_bars_left -= 1
            return

        self._exit(bar, broker, reason="sekundenschlaf_wakes_up")
