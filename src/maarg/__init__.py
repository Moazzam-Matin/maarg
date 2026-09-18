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

__all__ = ["track", "Run", "StorageBackend", "SQLiteStorage"]