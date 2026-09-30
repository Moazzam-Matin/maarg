"""
Core data model for maarg.

A Run is an immutable record of one execution of a tracked function:
what it was called with, what it produced, and when.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class Run:
    """An immutable record of a single tracked function execution."""

    function: str
    experiment: str
    inputs: dict[str, Any]
    metrics: dict[str, float] = field(default_factory=dict)
    artifacts: list[dict[str, str]] = field(default_factory=list)
    other: dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 0.0

    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize this run to a plain dict (e.g. for JSON/SQLite storage)."""
        return asdict(self)