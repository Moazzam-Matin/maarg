"""
Abstract storage interface for maarg.

Any storage backend (SQLite, JSON files, a future Postgres backend, etc.)
must implement this interface. Code elsewhere in maarg (the decorator,
the query layer, the CLI) depends only on this contract — never on any
specific backend's internals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from maarg.models import Run


class StorageBackend(ABC):
    """Contract that every maarg storage backend must implement."""

    @abstractmethod
    def save(self, run: Run) -> None:
        """Persist a completed Run."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, run_id: str) -> Run | None:
        """Retrieve a single Run by its ID, or None if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def list_by_function(self, function: str) -> list[Run]:
        """
        Return all Runs recorded for a given function name,
        newest-first by timestamp.
        """
        raise NotImplementedError

    @abstractmethod
    def list_by_experiment(self, experiment: str) -> list[Run]:
        """
        Return all Runs recorded under a given experiment label,
        newest-first by timestamp.
        """
        raise NotImplementedError

    @abstractmethod
    def list_all(self) -> list[Run]:
        """
        Return every Run this backend has stored,
        newest-first by timestamp.
        """
        raise NotImplementedError