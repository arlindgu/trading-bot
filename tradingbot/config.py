from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATE_DIR = ROOT / "paper_state"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def load_symbols() -> dict[str, list[str]]:
    """The single source of truth for which symbols every bot trades (see
    config/symbols.yaml) -- {"usdt": [...], "usdc": [...]}. Change the list
    there, every strategy/fleet config picks it up automatically."""
    return load_yaml(ROOT / "config" / "symbols.yaml")
