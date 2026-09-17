"""
Decorator module for maarg.

Provides the @track decorator to automatically inspect function parameters,
filter inputs, time execution, split outputs into metrics and artifacts,
and persist the resulting Run to a storage backend.
"""

from __future__ import annotations

import functools
import inspect
import time
import uuid
from pathlib import Path
from typing import Any, Callable, TypeVar, overload

from maarg.capture import (
    DEFAULT_MAX_COLLECTION_LENGTH,
    DEFAULT_MAX_SCALAR_BYTES,
    filter_inputs,
    split_output,
)
from maarg.models import Run
from maarg.storage.base import StorageBackend
from maarg.storage.sqlite import SQLiteStorage

F = TypeVar("F", bound=Callable[..., Any])

_DEFAULT_STORAGE: StorageBackend | None = None


def _get_default_storage() -> StorageBackend:
    """Lazy singleton initializer for the default SQLite storage backend."""
    global _DEFAULT_STORAGE
    if _DEFAULT_STORAGE is None:
        _DEFAULT_STORAGE = SQLiteStorage()
    return _DEFAULT_STORAGE


@overload
def track(_func: F) -> F: ...


@overload
def track(
    _func: None = None,
    *,
    experiment: str = "default",
    storage: StorageBackend | None = None,
    artifacts_dir: str | Path = Path(".maarg") / "artifacts",
    max_scalar_bytes: int = DEFAULT_MAX_SCALAR_BYTES,
    max_collection_length: int = DEFAULT_MAX_COLLECTION_LENGTH,
) -> Callable[[F], F]: ...


def track(
    _func: F | None = None,
    *,
    experiment: str = "default",
    storage: StorageBackend | None = None,
    artifacts_dir: str | Path = Path(".maarg") / "artifacts",
    max_scalar_bytes: int = DEFAULT_MAX_SCALAR_BYTES,
    max_collection_length: int = DEFAULT_MAX_COLLECTION_LENGTH,
) -> Any:
    """
    Decorator to track function execution, parameters, metrics, and artifacts.

    Usage:
        @track
        def train(lr=0.01, epochs=10):
            return {"accuracy": 0.95}

        @track(experiment="resnet-50", max_scalar_bytes=2000)
        def evaluate(model, dataset):
            return {"loss": 0.12}
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            backend = storage if storage is not None else _get_default_storage()

            # 1. Generate run_id early so artifact subdirectories are predictable
            run_id = str(uuid.uuid4())
            run_artifacts_dir = Path(artifacts_dir) / run_id

            # 2. Bind parameter values including defaults
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            # 3. Filter bound inputs
            filtered_inputs = filter_inputs(
                bound.arguments,
                max_scalar_bytes=max_scalar_bytes,
                max_collection_length=max_collection_length,
            )

            # 4. Execute wrapped function and handle exceptions
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                duration_sec = time.perf_counter() - start_time
                failed_run = Run(
                    run_id=run_id,
                    function=func.__name__,
                    experiment=experiment,
                    inputs=filtered_inputs,
                    duration_sec=duration_sec,
                    other={
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    },
                )
                backend.save(failed_run)
                raise

            duration_sec = time.perf_counter() - start_time

            # 5. Split output into metrics, artifacts, and other metadata
            metrics, artifacts, other = split_output(result, run_artifacts_dir)

            # 6. Save successful Run
            successful_run = Run(
                run_id=run_id,
                function=func.__name__,
                experiment=experiment,
                inputs=filtered_inputs,
                metrics=metrics,
                artifacts=artifacts,
                other=other,
                duration_sec=duration_sec,
            )

            backend.save(successful_run)
            return result

        return wrapper  # type: ignore[return-value]

    if _func is None:
        return decorator
    return decorator(_func)