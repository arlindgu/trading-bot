from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Bar:
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float
