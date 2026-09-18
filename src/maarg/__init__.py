"""
maarg — zero-instrumentation experiment tracking for Python.

    from maarg import track

    @track
    def train_model(learning_rate, epochs):
        return {"accuracy": 0.95}
"""

from maarg.tracking import track
from maarg.models import Run
from maarg.storage.base import StorageBackend
from maarg.storage.sqlite import SQLiteStorage
from maarg.query import filter_runs, top_n, best_run, compare

__all__ = [
    "track", "Run", "StorageBackend", "SQLiteStorage",
    "filter_runs", "top_n", "best_run", "compare",
]