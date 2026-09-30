"""
Convenience layer for maarg's public API.

maarg._query's functions are deliberately pure — they operate only on an
already-fetched list[Run], with no storage dependency, so they stay
trivially testable with hand-built Run lists. The wrappers here add the
"just fetch it for me" convenience most people actually want at the top
level, without touching that pure core: if `runs` isn't given, fetch from
storage first, then delegate to the pure implementation.
"""

from __future__ import annotations

from collections.abc import Sequence

from maarg._models import Run
from maarg._query import best_run as _pure_best_run
from maarg._query import filter_runs as _pure_filter_runs
from maarg._query import top_n as _pure_top_n
from maarg._tracking import _get_default_storage
from maarg.storage._base import StorageBackend


def get_runs(
    function: str | None = None,
    experiment: str | None = None,
    *,
    storage: StorageBackend | None = None,
) -> list[Run]:
    """
    Fetch runs from storage, optionally filtered by function and/or experiment.

    Defaults to the same storage backend @track uses when none is given.
    """
    backend = storage if storage is not None else _get_default_storage()

    if function is not None:
        runs = backend.list_by_function(function)
        if experiment is not None:
            runs = [r for r in runs if r.experiment == experiment]
        return runs

    if experiment is not None:
        return backend.list_by_experiment(experiment)

    return backend.list_all()


def top_n(
    runs: Sequence[Run] | None = None,
    *,
    metric: str,
    n: int = 5,
    higher_is_better: bool = True,
    only_successful: bool = True,
    function: str | None = None,
    experiment: str | None = None,
    storage: StorageBackend | None = None,
) -> list[Run]:
    """Like the pure top_n, but fetches from storage when `runs` isn't given."""
    if runs is None:
        runs = get_runs(function=function, experiment=experiment, storage=storage)
    return _pure_top_n(
        runs, metric, n=n,
        higher_is_better=higher_is_better,
        only_successful=only_successful,
    )


def best_run(
    runs: Sequence[Run] | None = None,
    *,
    metric: str,
    higher_is_better: bool = True,
    only_successful: bool = True,
    function: str | None = None,
    experiment: str | None = None,
    storage: StorageBackend | None = None,
) -> Run | None:
    """Like the pure best_run, but fetches from storage when `runs` isn't given."""
    if runs is None:
        runs = get_runs(function=function, experiment=experiment, storage=storage)
    return _pure_best_run(
        runs, metric,
        higher_is_better=higher_is_better,
        only_successful=only_successful,
    )


def filter_runs(
    runs: Sequence[Run] | None = None,
    *,
    only_successful: bool = True,
    experiment: str | None = None,
    function: str | None = None,
    storage: StorageBackend | None = None,
    **inputs,
) -> list[Run]:
    """Like the pure filter_runs, but fetches from storage when `runs` isn't given."""
    if runs is None:
        runs = get_runs(function=function, experiment=experiment, storage=storage)
    return _pure_filter_runs(
        runs, only_successful=only_successful, experiment=experiment, **inputs
    )