"""
maarg — zero-instrumentation experiment tracking for Python.

    from maarg import track

    @track
    def train_model(learning_rate, epochs):
        return {"accuracy": 0.95}
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("maarg")
except PackageNotFoundError:
    # Fallback for uninstalled local development mode
    __version__ = "0.2.0.post1"

from maarg._convenience import best_run, filter_runs, get_runs, top_n
from maarg._models import Run
from maarg._query import compare
from maarg._tracking import track
from maarg.storage._base import StorageBackend as StorageBackend
from maarg.storage._sqlite import SQLiteStorage as SQLiteStorage

__all__ = [
    "Run",
    "SQLiteStorage",
    "StorageBackend",
    "best_run",
    "compare",
    "filter_runs",
    "get_runs",
    "top_n",
    "track",
]