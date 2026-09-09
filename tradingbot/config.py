from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATE_DIR = ROOT / "paper_state"


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(Path(path).read_text())
