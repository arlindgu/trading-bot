"""Pendel-Bot (for laughs): swings back and forth like a pendulum -- long
on every even-numbered candle, flat on every odd one, no signal or
randomness involved, just a deterministic metronome on 1-minute bars. The
least clever possible way to guarantee a trade attempt on every single
candle."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class PendelBotConfig:
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


class PendelBotStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, position_pct: float | list[float] = 0.04):
        super().__init__(symbol, position_pct, max_concurrent=1)
        self.tick = 0

    @classmethod
    def from_config(cls, cfg: PendelBotConfig) -> "PendelBotStrategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        swing_in = self.tick % 2 == 0
        self.tick += 1

        if swing_in:
            self._enter(bar, broker, tag=f"pendel:tick#{self.tick}:in")
        else:
            self._exit(bar, broker, reason="pendel_swing_out")
