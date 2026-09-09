"""Long when RSI dips below the oversold threshold, exit once it climbs
back above the exit threshold. Mean-reversion, but on a much shorter leash
than Grid's wide price range."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import RSI
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class RsiReversionConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    period: int = 14
    oversold: float = 30.0
    exit_above: float = 60.0
    position_pct: float = 0.12
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class RsiReversionStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, period: int = 14, oversold: float = 30.0, exit_above: float = 60.0, position_pct: float = 0.12):
        super().__init__(symbol, position_pct)
        self.rsi = RSI(period)
        self.oversold = oversold
        self.exit_above = exit_above

    @classmethod
    def from_config(cls, cfg: RsiReversionConfig) -> "RsiReversionStrategy":
        return cls(cfg.symbol, cfg.period, cfg.oversold, cfg.exit_above, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        rsi = self.rsi.update(bar.close)
        if rsi is None:
            return

        if rsi < self.oversold:
            self._enter(bar, broker, tag=f"rsi_reversion:rsi{rsi:.1f}")
        elif rsi > self.exit_above:
            self._exit(bar, broker, reason="rsi_exit")
