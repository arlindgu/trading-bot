"""Trommelwirbel-Bot (for laughs): a drumroll -- builds up a position over
3 candles in a row (accumulating separate lots, the one thing this base
class is built for), then dumps the entire thing on the 4th candle for the
big reveal, and immediately starts building the next drumroll. Trades
every single 1-minute candle, either adding to the roll or cashing it in."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class TrommelwirbelBotConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    build_bars: int = 3
    position_pct: float | list[float] = 0.03
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class TrommelwirbelBotStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, build_bars: int = 3, position_pct: float | list[float] = 0.03):
        super().__init__(symbol, position_pct, max_concurrent=build_bars)
        self.build_bars = build_bars

    @classmethod
    def from_config(cls, cfg: TrommelwirbelBotConfig) -> "TrommelwirbelBotStrategy":
        return cls(cfg.symbol, cfg.build_bars, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        if len(self.lot_ids) >= self.build_bars:
            self._exit(bar, broker, reason="trommelwirbel_reveal")
            return

        self._enter(bar, broker, tag=f"trommelwirbel:roll#{len(self.lot_ids) + 1}/{self.build_bars}")
