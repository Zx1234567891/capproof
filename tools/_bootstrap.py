from __future__ import annotations

import sys
from pathlib import Path


def bootstrap() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    for path in (root, src):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
