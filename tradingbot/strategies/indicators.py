"""Small streaming/incremental indicators shared by several strategies.
Each is fed one value per bar via `.update(...)` and returns None until it
has enough history to mean anything -- this matches the engine's one-bar-
at-a-time `on_bar` contract, so no strategy needs to keep its own raw price
history just to compute a moving average.
"""
from __future__ import annotations

from collections import deque


class EMA:
    def __init__(self, period: int):
        self.alpha = 2 / (period + 1)
        self.value: float | None = None

    def update(self, x: float) -> float:
        self.value = x if self.value is None else self.alpha * x + (1 - self.alpha) * self.value
        return self.value


class RollingMean:
    def __init__(self, period: int):
        self.period = period
        self.buf: deque[float] = deque(maxlen=period)

    def update(self, x: float) -> float | None:
        self.buf.append(x)
        return sum(self.buf) / len(self.buf) if len(self.buf) == self.period else None


class RSI:
    """Wilder's smoothing, the standard RSI formula."""

    def __init__(self, period: int):
        self.period = period
        self.avg_gain: float | None = None
        self.avg_loss: float | None = None
        self.prev: float | None = None

    def update(self, close: float) -> float | None:
        if self.prev is None:
            self.prev = close
            return None
        change = close - self.prev
        self.prev = close
        gain, loss = max(change, 0.0), max(-change, 0.0)
        if self.avg_gain is None:
            self.avg_gain, self.avg_loss = gain, loss
        else:
            self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
            self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period
        if self.avg_loss == 0:
            return 100.0
        rs = self.avg_gain / self.avg_loss
        return 100 - 100 / (1 + rs)


class MACD:
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = EMA(fast)
        self.slow = EMA(slow)
        self.signal = EMA(signal)
        self._warm = 0
        self._warmup_bars = slow

    def update(self, close: float) -> tuple[float, float] | tuple[None, None]:
        fast_val, slow_val = self.fast.update(close), self.slow.update(close)
        self._warm += 1
        if self._warm < self._warmup_bars:
            return None, None
        macd = fast_val - slow_val
        signal = self.signal.update(macd)
        return macd, signal


class ATR:
    """Wilder's average true range."""

    def __init__(self, period: int):
        self.period = period
        self.prev_close: float | None = None
        self.avg: float | None = None

    def update(self, high: float, low: float, close: float) -> float:
        tr = (high - low) if self.prev_close is None else max(
            high - low, abs(high - self.prev_close), abs(low - self.prev_close)
        )
        self.prev_close = close
        self.avg = tr if self.avg is None else (self.avg * (self.period - 1) + tr) / self.period
        return self.avg


class Donchian:
    """Returns the channel from the *prior* `period` bars, not including the
    bar just passed in -- a breakout signal compares the current bar's
    close against the range that came before it, not a range that already
    absorbed this same bar (which would make breaking out nearly
    impossible)."""

    def __init__(self, period: int):
        self.period = period
        self.highs: deque[float] = deque(maxlen=period)
        self.lows: deque[float] = deque(maxlen=period)

    def update(self, high: float, low: float) -> tuple[float, float] | tuple[None, None]:
        channel = (max(self.highs), min(self.lows)) if len(self.highs) == self.period else (None, None)
        self.highs.append(high)
        self.lows.append(low)
        return channel


class BollingerBands:
    def __init__(self, period: int, num_std: float = 2.0):
        self.period = period
        self.num_std = num_std
        self.buf: deque[float] = deque(maxlen=period)

    def update(self, close: float) -> tuple[float, float, float] | tuple[None, None, None]:
        self.buf.append(close)
        if len(self.buf) < self.period:
            return None, None, None
        mean = sum(self.buf) / len(self.buf)
        variance = sum((x - mean) ** 2 for x in self.buf) / len(self.buf)
        std = variance**0.5
        return mean - self.num_std * std, mean, mean + self.num_std * std
