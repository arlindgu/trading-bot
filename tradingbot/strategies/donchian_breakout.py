"""Long on a close above the N-period Donchian high (a fresh breakout),
flat on a close below the N-period Donchian low. Trend-following, no
shorting (spot-only)."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import Donchian
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class DonchianBreakoutConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    period: int = 20
    position_pct: float = 0.12
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class DonchianBreakoutStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, period: int = 20, position_pct: float = 0.12):
        super().__init__(symbol, position_pct)
        self.donchian = Donchian(period)

    @classmethod
    def from_config(cls, cfg: DonchianBreakoutConfig) -> "DonchianBreakoutStrategy":
        return cls(cfg.symbol, cfg.period, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        upper, lower = self.donchian.update(bar.high, bar.low)
        if upper is None:
            return

        if bar.close >= upper:
            self._enter(bar, broker, tag=f"donchian_breakout:close>{upper:.4g}")
        elif bar.close <= lower:
            self._exit(bar, broker, reason="donchian_breakdown")
