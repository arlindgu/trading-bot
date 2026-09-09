"""Fetch and cache OHLCV history for a strategy config's symbol.

Usage:
    python cli/fetch_data.py config/grid_btc_usdt.yaml
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradingbot.config import load_yaml
from tradingbot.data.fetch import fetch_and_cache


def main() -> None:
    raw = load_yaml(Path(sys.argv[1]))
    path = fetch_and_cache(raw["symbol"], raw["timeframe"], raw.get("lookback_days", 90), raw["exchange"])
    print(f"Cached to {path}")


if __name__ == "__main__":
    main()
