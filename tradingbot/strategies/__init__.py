from __future__ import annotations

from tradingbot.strategies.base import Strategy
from tradingbot.strategies.grid import GridConfig, GridStrategy

# Registry a new strategy joins by adding one line here -- CLI scripts and
# tests never need to change to pick it up.
STRATEGIES: dict[str, tuple[type, type[Strategy]]] = {
    "grid": (GridConfig, GridStrategy),
}


def load_strategy(name: str, raw_config: dict) -> tuple[object, Strategy]:
    config_cls, strategy_cls = STRATEGIES[name]
    cfg = config_cls(**raw_config)
    return cfg, strategy_cls.from_config(cfg)
