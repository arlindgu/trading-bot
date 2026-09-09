"""Sternzeichen-Trader (for laughs): long or flat purely based on which
zodiac sign the current UTC date falls under, via a fixed table. As much
signal as astrology usually has -- none -- but fully deterministic."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy

# (month, day) the sign STARTS on, walking forward through the year.
_ZODIAC_STARTS = [
    ((1, 20), "aquarius"), ((2, 19), "pisces"), ((3, 21), "aries"), ((4, 20), "taurus"),
    ((5, 21), "gemini"), ((6, 21), "cancer"), ((7, 23), "leo"), ((8, 23), "virgo"),
    ((9, 23), "libra"), ((10, 23), "scorpio"), ((11, 22), "sagittarius"), ((12, 22), "capricorn"),
]

# Purely for the joke -- half the signs are "bullish", half aren't.
_BULLISH_SIGNS = {"aries", "leo", "sagittarius", "gemini", "libra", "aquarius"}


def zodiac_sign(month: int, day: int) -> str:
    current = (month, day)
    sign = _ZODIAC_STARTS[-1][1]  # wraps to capricorn (started last Dec) until the first Jan 20 boundary
    for (m, d), name in _ZODIAC_STARTS:
        if current >= (m, d):
            sign = name
        else:
            break
    return sign


@dataclass
class ZodiacConfig:
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


class ZodiacStrategy(SingleLotStrategy):
    @classmethod
    def from_config(cls, cfg: ZodiacConfig) -> "ZodiacStrategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        dt = bar.timestamp.to_pydatetime() if hasattr(bar.timestamp, "to_pydatetime") else bar.timestamp
        sign = zodiac_sign(dt.month, dt.day)

        if sign in _BULLISH_SIGNS:
            self._enter(bar, broker, tag=f"zodiac:{sign}:long")
        else:
            self._exit(bar, broker, reason=f"zodiac_{sign}_bearish")
