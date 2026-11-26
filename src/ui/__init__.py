"""MLflow-style Gradio frontend for maarg experiment tracking."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_maarg_importable() -> None:
    """Ensure local ``src/`` is on ``sys.path`` when running from a source checkout."""
    src_dir = Path(__file__).resolve().parent.parent
    if src_dir.is_dir():
        src_str = str(src_dir)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


ensure_maarg_importable()
