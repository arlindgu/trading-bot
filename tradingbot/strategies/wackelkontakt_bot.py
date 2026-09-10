"""Wackelkontakt-Bot (for laughs): a loose connection -- hashes the bar's
own OHLCV into a deterministic pseudo-coin every single candle and jumps
to whatever side that coin says, long or flat, no memory of what it just
did. Like Hash-Sentiment-Bot's parody of black-box "signals", but
re-rolled every 1-minute candle with a threshold that lands close to 50/50
so it flickers on almost every bar instead of holding a read for hours."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


def flicker_score(bar: Bar) -> float:
    raw = f"{bar.timestamp}{bar.open}{bar.high}{bar.low}{bar.close}{bar.volume}".encode()
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


@dataclass
class WackelkontaktBotConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    threshold: float = 0.5
    position_pct: float | list[float] = 0.04
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class WackelkontaktBotStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, threshold: float = 0.5, position_pct: float | list[float] = 0.04):
        super().__init__(symbol, position_pct, max_concurrent=1)
        self.threshold = threshold

    @classmethod
    def from_config(cls, cfg: WackelkontaktBotConfig) -> "WackelkontaktBotStrategy":
        return cls(cfg.symbol, cfg.threshold, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        score = flicker_score(bar)
        if score >= self.threshold:
            self._enter(bar, broker, tag=f"wackelkontakt:{score:.2f}:contact")
        else:
            self._exit(bar, broker, reason=f"wackelkontakt_{score:.2f}_lost_contact")
