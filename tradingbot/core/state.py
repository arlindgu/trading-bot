from __future__ import annotations

import json
from pathlib import Path

from tradingbot.core.broker import PaperBroker


def load_broker(path: Path, initial_cash: float, fee_pct: float, slippage_pct: float) -> PaperBroker:
    if not Path(path).exists():
        return PaperBroker(cash=initial_cash, fee_pct=fee_pct, slippage_pct=slippage_pct)
    raw = json.loads(Path(path).read_text())
    return PaperBroker.from_dict(raw)


def save_broker(path: Path, broker: PaperBroker) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(broker.to_dict(), indent=2, default=str))
