"""Herzschlag-Bot (for laughs): a heartbeat -- buys, holds for exactly one
candle, sells, and immediately buys again on 1-minute bars. Unlike
Zappelphilipp it never skips a beat (no coinflip on reopening), so it is
in and out of a tiny position on literally every single candle, forever."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class HerzschlagBotConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    position_pct: float | list[float] = 0.04
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class HerzschlagBotStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, position_pct: float | list[float] = 0.04):
        super().__init__(symbol, position_pct, max_concurrent=1)
        self.beat = 0

    @classmethod
    def from_config(cls, cfg: HerzschlagBotConfig) -> "HerzschlagBotStrategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        if self.lot_id is not None:
            self._exit(bar, broker, reason="herzschlag_beat")
        self.beat += 1
        self._enter(bar, broker, tag=f"herzschlag:beat#{self.beat}")
