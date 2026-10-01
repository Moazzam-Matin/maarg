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
  Put <code>@track</code> on a function. Every execution—arguments,
  returns, metrics, execution timing, and failures—is automatically saved
  to local storage for instant querying.
</p>

---

## How It Works

`maarg` sits transparently at function boundaries. It reads signature parameter
defaults and runtime return payloads without requiring explicit parameter or
metric logging statements inside your function logic.

```text
  ┌────────────────────────┐
  │  @track decorated fn   │  ──► (Intercepts arguments & execution context)
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │   Function Execution   │  ──► (Captures return dict / scalars / figures)
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │   SQLite Persistence   │  ──► Saves to .maarg/runs.db (or custom backend)
  └───────────┬────────────┘
              │
              ▼
  ┌────────────────────────┐
  │  Query & Analysis API  │  ──► maarg.get_runs() ──► top_n() / filter_runs()
  └────────────────────────┘
```

---

## Quickstart

```python
from maarg import track, get_runs, top_n

@track(experiment="learning-rate-sweep")
def fit(learning_rate, epochs=100):
    w = 0.0
    for _ in range(epochs):
        grad = sum(2 * (w * x - 3 * x) * x for x in range(1, 6)) / 5
        w -= learning_rate * grad
    return {"error": abs(w - 3)}

# Run experiments across hyperparameters
for lr in (0.001, 0.003, 0.01):
    fit(learning_rate=lr)

# Query top 3 runs directly from default storage
for run in top_n(get_runs(), "error", n=3, higher_is_better=False):
    print(f"lr={run.inputs['learning_rate']:<6} epochs={run.inputs['epochs']}  error={run.metrics['error']:.2e}")
```

```text
lr=0.01   epochs=100  error=4.86e-11
lr=0.003  epochs=100  error=3.25e-03
lr=0.001  epochs=100  error=3.24e-01
```

---

## Project & Storage Structure

`maarg` enforces a clean public package API while automatically managing runtime
tracking databases and artifact outputs.

### Repository Layout

```text
maarg/
├── .github/
│   └── workflows/
│       └── ci.yaml
├── docs/
├── src/
│   └── maarg/
│       ├── storage/             # Storage backends package
│       │   ├── __init__.py
│       │   ├── _base.py         # StorageBackend base interface
│       │   └── _sqlite.py       # SQLiteStorage implementation
│       ├── __init__.py          # Public API exports (track, get_runs, top_n, etc.)
│       ├── _capture.py          # Value parsing & scalar payload truncation
│       ├── _convenience.py      # get_runs() wrapper & top-level defaults
│       ├── _models.py           # Core Run and Storage schema dataclasses
│       ├── _query.py            # Pure analytical query engine (top_n, filter_runs)
│       └── _tracking.py         # @track decorator implementation
├── tests/                       # Full test suite matching internal modules
│   ├── test_capture.py
│   ├── test_convenience.py
│   ├── test_models.py
│   ├── test_query.py
│   ├── test_storage.py
│   └── test_tracking.py
├── LICENSE
├── PLANNING.md
├── pyproject.toml
└── README.md
```

### Runtime Storage Directory (`.maarg/`)

When you execute tracked functions, `maarg` initializes a local directory
relative to your working workspace:

```text
your_project/
├── .maarg/
│   ├── runs.db                  # Local SQLite database containing experiment runs
│   └── artifacts/               # Generated PNG plots & exported binary files
│       └── <run_id>/
│           └── figure_1.png
├── train.py
└── notebook.ipynb
```

---

## Installation

```bash
pip install maarg
```

Supports Python 3.9+ with zero required external server dependencies.
To automatically capture Matplotlib plots into `.maarg/artifacts/`,
install with plotting support:

```bash
pip install "maarg[plotting]"
```

---

## Querying Runs

Query functions operate as pure functions on collections of `Run` objects.
You can fetch runs effortlessly using the top-level `get_runs()` helper or
pass custom storage backends explicitly.

```python
from maarg import get_runs, filter_runs, top_n, best_run, compare

# Fetch runs from default local storage (.maarg/runs.db)
runs = get_runs()

# Optionally scope by experiment
exp_runs = get_runs(experiment="learning-rate-sweep")

# Identify top performers
best = best_run(runs, "error", higher_is_better=False)
top_3 = top_n(runs, "error", n=3, higher_is_better=False)

# Filter by input configuration
specific = filter_runs(runs, learning_rate=0.01)

# Tabulate run comparisons
comparison = compare(top_3)
```

By default, failed runs are filtered out of ranking queries (`only_successful=True`).
Pass `only_successful=False` to include failed executions.

---

## What Gets Recorded

| Field | Description |
| --- | --- |
| `run_id` | Unique UUID generated automatically per call |
| `timestamp` | ISO 8601 UTC timestamp of call execution |
| `function` | Name of the decorated function |
| `experiment` | Experiment grouping label (defaults to function name) |
| `inputs` | Captured function call parameters (including defaults) |
| `metrics` | Numeric dictionary outputs returned by the function |
| `artifacts` | Saved files/figures stored as `{name, path, type}` |
| `other` | Unclassified outputs, strings, booleans, or truncated `repr()` representations |
| `duration_sec` | Execution duration in seconds |

### Value Safety & Limits

- **Inputs:** Simple scalar values (numbers, strings, booleans) and collections
with ≤ 20 elements or ≤ 1000 bytes are recorded. Large arrays, dataframes, or
complex objects are automatically skipped to avoid database bloat.
- **Outputs:** Dictionary return values with numeric scalars become `metrics`.
Returned Matplotlib figures are serialized to PNG artifacts inside `.maarg/artifacts/<run_id>/`.
- **Failures:** Exceptions are caught, recorded with `other["status"] = "failed"`
along with the exception class and traceback message, and then re-raised unchanged.

---

## Configuration

Pass optional controls directly to the `@track` decorator:

```python
from maarg import track
from maarg.storage import SQLiteStorage

@track(
    experiment="hyperparameter-sweep",
    storage=SQLiteStorage("results/custom_experiment.db"),
    artifacts_dir="results/artifacts"
)
def train(lr, batch_size):
    ...
```

| Option | Default | Description |
| --- | --- | --- |
| `experiment` | Function name | Label for grouping related runs |
| `storage` | SQLite at `.maarg/runs.db` | Target storage engine instance |
| `artifacts_dir` | `.maarg/artifacts` | Directory path for stored plots/files |
| `max_scalar_bytes` | `1000` | Max byte size allowed for individual scalar inputs |
| `max_collection_length` | `20` | Max items allowed in recorded input lists/dicts |

---

## Custom Storage Backends

You can define custom storage targets by subclassing `StorageBackend` and implementing `save`, `get_by_id`, `list_by_function`, `list_by_experiment`, and `list_all`:

```python
from maarg.storage import StorageBackend

class CustomStorage(StorageBackend):
    # Implement persistence methods
    ...
```

---

## Roadmap

- Command-line interface (CLI) for browsing and inspecting runs directly in the terminal
- Event hooks triggered on run completion (e.g., Slack or webhook notifications)
- Web dashboard extension package
- Additional remote storage backends

---

## About the Name

*maarg* (मार्ग) is Hindi for "path" or "route".

---

## License

MIT — see [LICENSE](LICENSE).
