# maarg

[![CI](https://github.com/Moazzam-Matin/maarg/workflows/CI/badge.svg)](https://github.com/Moazzam-Matin/maarg/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![PyPI version](https://img.shields.io/pypi/v/maarg.svg)](https://pypi.org/project/maarg/)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Moazzam-Matin/maarg/main/docs/assets/maarg_logo_dark.svg">
    <img alt="maarg - Zero-Boilerplate Experiment Tracking"
    src="https://raw.githubusercontent.com/Moazzam-Matin/maarg/main/docs/assets/maarg_logo.svg"
    width="320">
  </picture>
</p>

<h3 align="center">Experiment tracking with zero logging code.</h3>

<p align="center">
  Put <code>@track</code> on a function. maarg automatically captures
  inputs, outputs, execution timing, failures, and supported artifacts,
  then stores each run locally for querying and comparison.
</p>

---

## What is maarg?

**maarg** is a lightweight, zero-instrumentation experiment tracker for Python.

Instead of adding `log_param()`, `log_metric()`, or framework-specific
autologging calls, decorate a function with `@track`. maarg inspects the
function signature and return value, records the useful parts of the
execution, and persists the resulting `Run`.

It is designed for parameterized functions such as:

- hyperparameter sweeps
- algorithm benchmarks
- backtests and simulations
- repeated data-science experiments
- small local experiments that do not need a tracking server

The core API is Python-first and local-first.

---

## How It Works

```text
  ┌────────────────────────┐
  │      @track function   │
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │ Capture inputs & time  │
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │ Execute user function  │
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │ Classify return value   │
  │ metrics / artifacts /   │
  │ other                   │
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │ SQLite persistence     │
  │ .maarg/runs.db         │
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │ Query & compare runs   │
  │ get_runs / top_n /     │
  │ best_run / filter /    │
  │ compare                │
  └────────────────────────┘
```

No tracking server is required.

---

## Quickstart

### Install

```bash
pip install maarg
```

For automatic Matplotlib figure capture:

```bash
pip install "maarg[plotting]"
```

### Track a function

```python
from maarg import track, get_runs, top_n

@track(experiment="learning-rate-sweep")
def fit(learning_rate, epochs=100):
    w = 0.0

    for _ in range(epochs):
        grad = sum(
            2 * (w * x - 3 * x) * x
            for x in range(1, 6)
        ) / 5
        w -= learning_rate * grad

    return {"error": abs(w - 3)}

for lr in (0.001, 0.003, 0.01):
    fit(learning_rate=lr)

for run in top_n(
    get_runs(),
    metric="error",
    n=3,
    higher_is_better=False,
):
    print(
        f"lr={run.inputs['learning_rate']:<6} "
        f"epochs={run.inputs['epochs']} "
        f"error={run.metrics['error']:.2e}"
    )
```

A tracked execution creates a local SQLite database automatically:

```text
your_project/
├── .maarg/
│   ├── runs.db
│   └── artifacts/
│       └── <run_id>/
│           └── <artifact>.png
├── train.py
└── notebook.ipynb
```

---

## Public API

The package currently exports:

```python
from maarg import (
    track,
    get_runs,
    filter_runs,
    top_n,
    best_run,
    compare,
    Run,
    StorageBackend,
    SQLiteStorage,
    MaargTrackingError,
    MaargTrackingWarning,
)
```

### `@track`

The decorator supports both forms:

```python
@track
def train(lr=0.01):
    return {"accuracy": 0.95}
```

and:

```python
@track(
    experiment="resnet-50",
    artifacts_dir="results/artifacts",
    max_scalar_bytes=2000,
    max_collection_length=20,
)
def evaluate(lr, batch_size):
    return {"loss": 0.12}
```

The experiment name defaults to the decorated function's name.

### Querying

```python
from maarg import get_runs, filter_runs, top_n, best_run, compare

runs = get_runs()

exp_runs = get_runs(experiment="learning-rate-sweep")

specific = filter_runs(
    runs,
    learning_rate=0.01,
)

top_3 = top_n(
    runs,
    metric="error",
    n=3,
    higher_is_better=False,
)

best = best_run(
    runs,
    metric="error",
    higher_is_better=False,
)

comparison = compare(top_3)
```

Top-level query helpers can read directly from storage, or operate on an
already-fetched collection of `Run` objects.

By default, ranking and filtering helpers exclude runs explicitly marked as
failed. Use `only_successful=False` to include failed runs.

---

## What Gets Recorded

Each tracked execution produces an immutable `Run` containing:

| Field | Description |
| --- | --- |
| `run_id` | Unique UUID for the execution |
| `timestamp` | ISO 8601 UTC timestamp |
| `function` | Decorated function name |
| `experiment` | Experiment label |
| `inputs` | Loggable function arguments, including defaults |
| `metrics` | Numeric values returned by the function |
| `artifacts` | Serialized supported artifacts with name, path, and type |
| `other` | Strings, `None`, booleans, failed-run metadata, or truncated representations |
| `duration_sec` | Function execution time in seconds |

### Input filtering

maarg intentionally avoids putting large or complex Python objects into the
tracking database.

By default:

- simple scalars are recorded when they fit within `max_scalar_bytes`
- lists, tuples, and dictionaries are recorded only when they contain at most
  `max_collection_length` items and all nested values are loggable
- large arrays, dataframes, custom objects, file handles, and other complex
  objects are skipped

Defaults:

| Option | Default |
| --- | ---: |
| `max_scalar_bytes` | `1000` |
| `max_collection_length` | `20` |

---

## Output Capture

maarg classifies return values into three categories:

### Metrics

Numeric `int` and `float` values become metrics.

```python
return {"accuracy": 0.95, "loss": 0.12}
```

### Artifacts

Supported artifact types are serialized to the configured artifacts directory.

Matplotlib figures are supported when Matplotlib is installed:

```python
import matplotlib.pyplot as plt

@track(experiment="plot-test")
def make_plot():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3])
    return {"figure": fig, "score": 0.91}
```

The current implementation uses an internal serializer registry so artifact
handling can be extended without hard-coding every output type into the main
classification logic.

Artifact filenames are sanitized before being converted into filesystem paths.

### Other values

Strings and `None` are stored as-is. Booleans are stored as non-metric
values. Unrecognized objects are represented using a truncated `repr()`
to avoid storing arbitrarily large values.

---

## Failure-Safe Tracking

Tracking failures should not replace the user's actual function failures.

If the decorated function raises an exception, maarg:

1. records the failed run when possible
2. stores the exception type and message
3. emits a `MaargTrackingWarning` if persistence itself fails
4. re-raises the original user exception unchanged

### Strict mode

For successful functions, persistence failures can be made fatal:

```python
from maarg import track

@track(experiment="important-run", strict=True)
def train():
    return {"accuracy": 0.95}
```

With `strict=False` (the default), a failure to persist a successful run
emits `MaargTrackingWarning` and the user's result is returned normally.

With `strict=True`, a persistence failure raises `MaargTrackingError`.

The original exception from a failed user function is always preserved,
regardless of `strict`.

---

## Storage

### Default SQLite storage

The default backend stores runs in:

```text
.maarg/runs.db
```

SQLite uses indexes on:

- `function`
- `experiment`
- `timestamp`

This keeps common lookup paths efficient as the local run history grows.

### Custom database location

```python
from maarg import SQLiteStorage, track

storage = SQLiteStorage("results/experiments.db")

@track(
    experiment="benchmark",
    storage=storage,
    artifacts_dir="results/artifacts",
)
def benchmark():
    return {"score": 0.91}
```

### Custom storage backends

The storage layer is defined by the `StorageBackend` interface. A custom
backend can implement the persistence and retrieval methods used by maarg:

```python
from maarg.storage import StorageBackend

class CustomStorage(StorageBackend):
    def save(self, run):
        ...

    def get_by_id(self, run_id):
        ...

    def list_by_function(self, function):
        ...

    def list_by_experiment(self, experiment):
        ...

    def list_all(self):
        ...
```

SQLite is the built-in backend; remote/distributed backends are not currently
included.

---

## Configuration

`@track` currently accepts:

| Option | Default | Description |
| --- | --- | --- |
| `experiment` | Function name | Label used to group related runs |
| `storage` | Local SQLite | Storage backend instance |
| `artifacts_dir` | `.maarg/artifacts` | Directory for serialized artifacts |
| `max_scalar_bytes` | `1000` | Maximum size for a recorded scalar |
| `max_collection_length` | `20` | Maximum number of items in a recorded collection |
| `strict` | `False` | Whether successful-run persistence failures raise `MaargTrackingError` |

---

## Repository Structure

The current repository is organized as:

```text
maarg/
├── .github/
│   └── workflows/
│       └── ci.yaml
├── docs/
│   └── assets/
│       ├── maarg_logo.svg
│       └── maarg_logo_dark.svg
├── src/
│   └── maarg/
│       ├── __init__.py          # Public API exports
│       ├── _capture.py          # Input filtering and output classification
│       ├── _convenience.py      # Storage-aware query helpers
│       ├── _exceptions.py       # Tracking error and warning types
│       ├── _models.py           # Immutable Run model
│       ├── _query.py            # Pure query/comparison functions
│       ├── _tracking.py         # @track implementation
│       └── storage/
│           ├── __init__.py      # Storage API exports
│           ├── _base.py         # StorageBackend interface
│           └── _sqlite.py       # SQLiteStorage implementation
├── tests/
│   ├── test_capture.py
│   ├── test_convenience.py
│   ├── test_models.py
│   ├── test_query.py
│   ├── test_storage.py
│   └── test_tracking.py
├── CHANGELOG.md
├── LICENSE
├── PLANNING.md
├── pyproject.toml
└── README.md
```

The package uses a `src/` layout and supports Python 3.9 through 3.13.

---

## Development

Clone the repository and install the development dependencies:

```bash
git clone https://github.com/Moazzam-Matin/maarg.git
cd maarg
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest
```

The repository also contains a GitHub Actions CI workflow under
`.github/workflows/ci.yaml`.

---

## Current Scope

maarg 0.3.0 focuses on reliable local experiment tracking.

### Included

- zero-instrumentation `@track` decorator
- automatic input filtering
- automatic metric/output classification
- Matplotlib artifact capture
- local SQLite persistence
- pluggable storage interface
- Python query and comparison API
- failure tracking
- failure-safe persistence behavior
- `strict` mode for successful-run persistence
- tracking error and warning types
- artifact filename sanitization
- SQLite indexes for common lookup fields
- internal serializer registry

### Not currently included

- command-line interface
- web dashboard
- distributed or multi-machine tracking server
- experiment orchestration
- authentication or permissions
- model registry
- remote storage backends
- step-wise/imperative metric logging
- free-form run tags

---

## Roadmap

The roadmap is intentionally small and follows the project's planning document.

- **CLI:** possible future addition if real user demand emerges
- **Capture hooks/callbacks:** future support for integrations such as webhooks
  or notifications
- **Additional storage backends:** future remote or alternative persistence
- **Dashboard:** planned as a separate package rather than part of core maarg
- **Run tags:** a future first-class run metadata feature
- **Step-wise logging:** requires a separate design before implementation

See [PLANNING.md](PLANNING.md) for the current project decisions and
non-goals.

---

## Version

The current package version is **0.3.0**.

See [CHANGELOG.md](CHANGELOG.md) for release history.

---

## About the Name

*maarg* (मार्ग) is Hindi for "path" or "route".

---

## License

MIT — see [LICENSE](LICENSE).
