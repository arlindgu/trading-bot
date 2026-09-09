"""Vollmond-Trader (for laughs): long during the days around a full moon,
flat otherwise. Moon phase is computed directly from the bar's own UTC
date via the synodic month -- no external ephemeris needed, and it's
fully deterministic so the same date always gives the same phase."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.single_lot import SingleLotStrategy

SYNODIC_MONTH_DAYS = 29.530588853
KNOWN_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
FULL_MOON_WINDOW_DAYS = 1.5  # within this many days of exact full (phase 0.5), count as "full"


def moon_phase(timestamp) -> float:
    """0.0/1.0 = new moon, 0.5 = full moon."""
    dt = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
    days_since = (dt - KNOWN_NEW_MOON).total_seconds() / 86400
    return math.fmod(days_since, SYNODIC_MONTH_DAYS) / SYNODIC_MONTH_DAYS


def is_near_full_moon(timestamp) -> bool:
    phase = moon_phase(timestamp)
    return abs(phase - 0.5) <= FULL_MOON_WINDOW_DAYS / SYNODIC_MONTH_DAYS


@dataclass
class MoonPhaseConfig:
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


class MoonPhaseStrategy(SingleLotStrategy):
    @classmethod
    def from_config(cls, cfg: MoonPhaseConfig) -> "MoonPhaseStrategy":
        return cls(cfg.symbol, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        if is_near_full_moon(bar.timestamp):
            self._enter(bar, broker, tag="moon_phase:full")
        else:
            self._exit(bar, broker, reason="moon_phase_waning")
