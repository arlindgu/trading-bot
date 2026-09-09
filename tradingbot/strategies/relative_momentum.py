"""Long when this symbol's own N-bar return is both positive and above its
own recent average return (rewards accelerating strength over its own
history) -- a single-symbol stand-in for ranking across a whole basket
(true cross-sectional ranking would need every symbol's strategy instance
to share mutable state across accounts, which risks exactly the kind of
accidental cross-account state-sharing bug the fleet consolidation was
built to avoid), flat otherwise."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import RollingMean
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class RelativeMomentumConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    return_period: int = 10
    average_period: int = 20
    position_pct: float = 0.12
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class RelativeMomentumStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, return_period: int = 10, average_period: int = 20, position_pct: float = 0.12):
        super().__init__(symbol, position_pct)
        self.return_period = return_period
        self.closes: deque[float] = deque(maxlen=return_period + 1)
        self.avg_return = RollingMean(average_period)

    @classmethod
    def from_config(cls, cfg: RelativeMomentumConfig) -> "RelativeMomentumStrategy":
        return cls(cfg.symbol, cfg.return_period, cfg.average_period, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        self.closes.append(bar.close)
        if len(self.closes) < self.closes.maxlen:
            return
        current_return = (self.closes[-1] - self.closes[0]) / self.closes[0]
        avg_return = self.avg_return.update(current_return)
        if avg_return is None:
            return

        if current_return > 0 and current_return > avg_return:
            self._enter(bar, broker, tag=f"relative_momentum:ret{current_return:.2%}")
        else:
            self._exit(bar, broker, reason="momentum_faded")
