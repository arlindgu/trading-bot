"""Long when this bar's volume spikes well above its recent average AND
price closes higher than it opened (a real thrust, not just noisy volume),
exit once volume falls back to normal."""
from __future__ import annotations

from dataclasses import dataclass

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar
from tradingbot.strategies.indicators import RollingMean
from tradingbot.strategies.single_lot import SingleLotStrategy


@dataclass
class VolumeSpikeConfig:
    symbol: str
    exchange: str
    timeframe: str
    fee_pct: float
    slippage_pct: float
    volume_period: int = 20
    spike_multiplier: float = 2.0
    position_pct: float = 0.12
    lookback_days: int = 90
    initial_cash: float | None = None

    @property
    def starting_cash(self) -> float:
        return self.initial_cash if self.initial_cash is not None else 1000.0


class VolumeSpikeStrategy(SingleLotStrategy):
    def __init__(self, symbol: str, volume_period: int = 20, spike_multiplier: float = 2.0, position_pct: float = 0.12):
        super().__init__(symbol, position_pct)
        self.avg_volume = RollingMean(volume_period)
        self.spike_multiplier = spike_multiplier

    @classmethod
    def from_config(cls, cfg: VolumeSpikeConfig) -> "VolumeSpikeStrategy":
        return cls(cfg.symbol, cfg.volume_period, cfg.spike_multiplier, cfg.position_pct)

    def on_bar(self, bar: Bar, broker: PaperBroker) -> None:
        if not self._is_new_bar(bar):
            return

        avg = self.avg_volume.update(bar.volume)
        if avg is None:
            return

        is_thrust_up = bar.volume > self.spike_multiplier * avg and bar.close > bar.open
        if is_thrust_up:
            self._enter(bar, broker, tag=f"volume_spike:vol{bar.volume:.4g}>{self.spike_multiplier}xavg")
        elif bar.volume < avg:
            self._exit(bar, broker, reason="volume_normalized")
