"""
Input filtering logic for maarg.

Decides which of a function's arguments are simple "settings" worth
logging automatically, versus large/complex objects (datasets, models,
file handles) that should be skipped.
"""

from __future__ import annotations

import sys
from typing import Any

import os
from pathlib import Path

# Defaults — overridable per-call via the @track decorator later.
DEFAULT_MAX_SCALAR_BYTES = 1000
DEFAULT_MAX_COLLECTION_LENGTH = 20

_SCALAR_TYPES = (int, float, bool, str, type(None))
_COLLECTION_TYPES = (list, tuple, dict)


def is_loggable(
    value: Any,
    max_scalar_bytes: int = DEFAULT_MAX_SCALAR_BYTES,
    max_collection_length: int = DEFAULT_MAX_COLLECTION_LENGTH,
) -> bool:
    """
    Decide whether `value` is simple enough to log automatically.

    Scalars (int, float, bool, str, None) are loggable if they're under
    `max_scalar_bytes` in size. Collections (list, tuple, dict) are
    loggable if they have at most `max_collection_length` items AND
    every item inside them is itself loggable (checked recursively).
    Anything else (DataFrames, arrays, custom objects, file handles,
    etc.) is never loggable.
    """
    if isinstance(value, _SCALAR_TYPES):
        return sys.getsizeof(value) <= max_scalar_bytes

    if isinstance(value, _COLLECTION_TYPES):
        if len(value) > max_collection_length:
            return False

        items = value.values() if isinstance(value, dict) else value
        return all(
            is_loggable(item, max_scalar_bytes, max_collection_length)
            for item in items
        )

    # DataFrames, ndarrays, custom classes, file handles, etc.
    return False


def filter_inputs(
    args: dict[str, Any],
    max_scalar_bytes: int = DEFAULT_MAX_SCALAR_BYTES,
    max_collection_length: int = DEFAULT_MAX_COLLECTION_LENGTH,
) -> dict[str, Any]:
    """
    Given a dict of {param_name: value} (e.g. from a function's bound
    arguments), return only the entries that pass `is_loggable`.
    """
    return {
        name: value
        for name, value in args.items()
        if is_loggable(value, max_scalar_bytes, max_collection_length)
    }


# ── Output splitting ─────────────────────────────────────────────────


OTHER_REPR_MAX_LEN = 200


def _is_matplotlib_figure(value: Any) -> bool:
    """Check for a matplotlib Figure without hard-depending on matplotlib."""
    try:
        import matplotlib.figure
        return isinstance(value, matplotlib.figure.Figure)
    except ImportError:
        return False


def _save_figure(fig: Any, name: str, artifacts_dir: str | Path) -> str:
    """Save a figure to `artifacts_dir/<name>.png` and return the path."""
    artifacts_dir = Path(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    path = artifacts_dir / f"{name}.png"
    fig.savefig(path)
    return str(path)


def split_output(
    output: Any,
    artifacts_dir: str | Path,
) -> tuple[dict[str, float], list[dict[str, str]], dict[str, Any]]:
    """
    Classify a function's return value into (metrics, artifacts, other).

    - A dict return value is walked key by key, classifying each value.
    - A non-dict return value is treated as a single item named "result".

    Classification rules, in order:
      - bool         -> other (never treated as a number)
      - int / float  -> metrics
      - a known artifact type (currently: matplotlib Figure) -> saved to
        disk under `artifacts_dir`, recorded in artifacts
      - str / None   -> other, stored as-is
      - anything else (unrecognized object) -> other, as a truncated repr
    """
    metrics: dict[str, float] = {}
    artifacts: list[dict[str, str]] = []
    other: dict[str, Any] = {}

    items = output.items() if isinstance(output, dict) else [("result", output)]

    for name, value in items:
        if isinstance(value, bool):
            other[name] = value
        elif isinstance(value, (int, float)):
            metrics[name] = value
        elif _is_matplotlib_figure(value):
            path = _save_figure(value, name, artifacts_dir)
            artifacts.append({"name": name, "path": path, "type": "chart"})
        elif isinstance(value, (str, type(None))):
            other[name] = value
        else:
            other[name] = repr(value)[:OTHER_REPR_MAX_LEN]

    return metrics, artifacts, other