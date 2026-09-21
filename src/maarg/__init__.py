"""
maarg — zero-instrumentation experiment tracking for Python.

    from maarg import track

    @track
    def train_model(learning_rate, epochs):
        return {"accuracy": 0.95}
"""

from maarg.models import Run
from maarg.query import best_run, compare, filter_runs, top_n
from maarg.storage.base import StorageBackend
from maarg.storage.sqlite import SQLiteStorage
from maarg.tracking import track

__all__ = [
    "Run",
    "SQLiteStorage",
    "StorageBackend",
    "best_run",
    "compare",
    "filter_runs",
    "top_n",
    "track",
]