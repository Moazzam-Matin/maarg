"""
Query and comparison utilities for maarg.

These are pure functions operating on already-fetched lists of Run
objects — deliberately decoupled from StorageBackend, so this layer
stays trivially testable (hand-built Run lists, no database involved)
and independent of which backend produced the data.
"""

from __future__ import annotations

from collections.abc import Sequence

from maarg._models import Run


def _is_failed(run: Run) -> bool:
    """A run is failed only if explicitly marked so; absence means success."""
    return run.other.get("status") == "failed"


def filter_runs(
    runs: Sequence[Run],
    *,
    only_successful: bool = True,
    experiment: str | None = None,
    **inputs,
) -> list[Run]:
    """
    Filter runs by success status, experiment, and/or exact input values.

    `only_successful=True` (the default) excludes runs marked failed.
    Any extra keyword arguments are treated as exact-match filters against
    a run's `inputs` dict, e.g. filter_runs(runs, learning_rate=0.01).
    """
    result = []
    for r in runs:
        if only_successful and _is_failed(r):
            continue
        if experiment is not None and r.experiment != experiment:
            continue
        if any(r.inputs.get(k) != v for k, v in inputs.items()):
            continue
        result.append(r)
    return result


def top_n(
    runs: Sequence[Run],
    metric: str,
    n: int = 5,
    *,
    higher_is_better: bool = True,
    only_successful: bool = True,
) -> list[Run]:
    """
    Rank the top N runs by a metric. Runs missing that metric (or where
    it isn't numeric) are silently excluded, not treated as an error.
    """
    candidates = filter_runs(runs, only_successful=only_successful)
    valid = [
        r for r in candidates
        if isinstance(r.metrics.get(metric), (int, float))
    ]
    return sorted(
        valid,
        key=lambda r: r.metrics[metric],
        reverse=higher_is_better,
    )[:n]


def best_run(
    runs: Sequence[Run],
    metric: str,
    *,
    higher_is_better: bool = True,
    only_successful: bool = True,
) -> Run | None:
    """Return the single best run for a metric, or None if none qualify."""
    results = top_n(
        runs, metric, n=1,
        higher_is_better=higher_is_better,
        only_successful=only_successful,
    )
    return results[0] if results else None


def compare(runs: Sequence[Run]) -> dict:
    """Build a side-by-side view of inputs, metrics, and status across runs."""
    if not runs:
        return {"run_ids": [], "inputs": {}, "metrics": {}, "status": []}

    all_input_keys = {k for r in runs for k in r.inputs}
    all_metric_keys = {k for r in runs for k in r.metrics}

    return {
        "run_ids": [r.run_id for r in runs],
        "inputs": {k: [r.inputs.get(k) for r in runs] for k in sorted(all_input_keys)},
        "metrics": {k: [r.metrics.get(k) for r in runs] for k in sorted(all_metric_keys)},
        "status": ["failed" if _is_failed(r) else "success" for r in runs],
    }