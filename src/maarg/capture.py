"""
Input filtering logic for maarg.

Decides which of a function's arguments are simple "settings" worth
logging automatically, versus large/complex objects (datasets, models,
file handles) that should be skipped.
"""

from __future__ import annotations

import sys
from typing import Any

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