"""Buy-High-Sell-Low (for laughs): buys every fresh N-period high it sees
(chasing strength, up to `max_concurrent` lots -- keeps adding more on
each new high even while already holding) and panic-sells everything on
the very next red candle -- deliberately the opposite of good trade
timing, taken literally."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import Donchian
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class BuyHighSellLowConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    period: int = 20
    position_pct: float = 0.15
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class BuyHighSellLowStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, period: int = 20, position_pct: float = 0.15):
        super().__init__(symbol, position_pct)
        self.donchian = Donchian(period)

    @classmethod
    def from_config(cls, cfg: BuyHighSellLowConfig) -> "BuyHighSellLowStrategy":
        return cls(cfg.symbol, cfg.period, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        upper, _lower = self.donchian.update(bar.high, bar.low)

        if self.lot_id is not None and bar.close < bar.open:
            self._exit(bar, broker, reason="panic_sold_the_dip")
            return  # sold everything -- don't also chase a high on the same bar

        if upper is not None and bar.close >= upper:
            self._enter(bar, broker, tag=f"buy_high_sell_low:chasing{upper:.4g}")
