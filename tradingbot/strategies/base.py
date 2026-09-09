from __future__ import annotations

from abc import ABC, abstractmethod

from tradingbot.core.broker import PaperBroker
from tradingbot.core.types import Bar


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
