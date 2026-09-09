from __future__ import annotations

import random
from abc import ABC, abstractmethod

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar


def sample_pct(value: float | list[float] | tuple[float, float], rng: random.Random) -> float:
    """A risk/position-pct config value is either a flat fraction or a
    [min, max] range -- resample the range on every call so a bot doesn't
    size every trade at the same fixed pct for its whole run."""
    if isinstance(value, (list, tuple)):
        low, high = value
        return rng.uniform(low, high)
    return value


class Strategy(ABC):
    """Contract every strategy implements.

    A strategy owns all of its trading logic and state between bars (e.g.
    which grid levels are currently filled) and calls `broker.buy`/`sell`
    itself when it decides to trade -- including any intrabar high/low
    checks it needs. The backtest engine and the live/paper loop both just
    call `on_bar` once per bar, so a strategy runs identically in both and
    adding a new one never requires touching the engine.
    """

    @abstractmethod
    def on_bar(self, bar: Bar, broker: PaperBroker) -> None: ...
