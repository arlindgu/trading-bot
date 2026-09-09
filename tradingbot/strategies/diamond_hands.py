"""Diamond-Hands (for laughs): buys every red candle it sees (up to
`max_concurrent` lots), then never voluntarily sells any of it no matter
how far it drops -- the "never sell" meme taken completely literally."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class DiamondHandsConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    position_pct: float | list[float] = 0.15
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class DiamondHandsStrategy(SingleLotStrategy):
    @classmethod
    def from_config(cls, cfg: DiamondHandsConfig) -> "DiamondHandsStrategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return
        # No exit condition exists, ever -- only entries, on every dip.
        if bar.close < bar.open:
            self._enter(bar, broker, tag="diamond_hands:never_selling")
