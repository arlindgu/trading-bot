"""Hash-Sentiment-Bot (for laughs): pretends to read "crowd sentiment" but
actually just hashes the bar's own OHLCV values into a deterministic
pseudo-score in [0, 1) -- long above the threshold, flat otherwise. A
parody of black-box "sentiment" signals with no real data behind them."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy


def sentiment_score(bar: Bar) -> float:
    raw = f"{bar.timestamp}{bar.open}{bar.high}{bar.low}{bar.close}{bar.volume}".encode()
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


@dataclass
class HashSentimentConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    threshold: float = 0.6
    position_pct: float = 0.15
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class HashSentimentStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, threshold: float = 0.6, position_pct: float = 0.15):
        super().__init__(symbol, position_pct)
        self.threshold = threshold

    @classmethod
    def from_config(cls, cfg: HashSentimentConfig) -> "HashSentimentStrategy":
        return cls(cfg.symbol, cfg.threshold, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        score = sentiment_score(bar)
        if score >= self.threshold:
            self._enter(bar, broker, tag=f"hash_sentiment:{score:.2f}:long")
        else:
            self._exit(bar, broker, reason=f"hash_sentiment_{score:.2f}_bearish")
