# maarg

**Experiment tracking with zero logging code.**

Put `@track` on a function. Every call is recorded (arguments, results, timing, even failures) and you can query the history from Python. No `log_param()`, no `log_metric()`, no server, no account.

```python
from maarg import track, SQLiteStorage, top_n

@track
def fit(learning_rate, epochs=100):
    w = 0.0
    for _ in range(epochs):
        grad = sum(2 * (w * x - 3 * x) * x for x in range(1, 6)) / 5
        w -= learning_rate * grad
    return {"error": abs(w - 3)}

for lr in (0.001, 0.003, 0.01):
    fit(learning_rate=lr)

for run in top_n(SQLiteStorage().list_all(), "error", n=3, higher_is_better=False):
    print(f"lr={run.inputs['learning_rate']:<6} epochs={run.inputs['epochs']}  error={run.metrics['error']:.2e}")
```

```text
lr=0.01   epochs=100  error=4.86e-11
lr=0.003  epochs=100  error=3.25e-03
lr=0.001  epochs=100  error=3.24e-01
```

You never told maarg about `learning_rate`, `epochs` or `error`. It read them from the function's signature and return value, including `epochs=100`, which no call ever passed.

> **Alpha.** The decorator, local storage and query API work. A command-line interface is planned, and the API may change before 1.0.

## Why maarg

- **Nothing to forget.** Every argument is captured, defaults included. With manual logging, each new parameter is another line to remember, and a forgotten line is a run you can't reproduce.
- **Every run counts, including the ones that crash.** Failed calls are saved with the error type and message, and the exception still reaches your code unchanged.
- **Works on any Python function.** Hyperparameter sweeps, algorithm benchmarks, backtests, simulations: anything you run repeatedly with different arguments and want to compare. It isn't tied to a framework or to machine learning.
- **Nothing to set up.** No server, no account, no dependencies. Runs are saved to a local SQLite file, behind a small interface so other backends can be added later.

## Before and after

Explicit logging (MLflow shown as one example) means listing every parameter and metric yourself:

```python
import mlflow

def train_model(learning_rate, epochs):
    with mlflow.start_run():
        mlflow.log_param("learning_rate", learning_rate)
        mlflow.log_param("epochs", epochs)
        accuracy = ...  # your code
        mlflow.log_metric("accuracy", accuracy)
        return accuracy
```

With maarg, the same function is just the function:

```python
from maarg import track

@track
def train_model(learning_rate, epochs):
    accuracy = ...  # your code
    return {"accuracy": accuracy}
```

Some frameworks offer autologging for their own training loops. maarg works on any function you can decorate.

## Installation

```bash
pip install maarg
```

Supports Python 3.9+ and has no required dependencies. To capture matplotlib figures, install the optional extra:

```bash
pip install "maarg[plotting]"
```

## Querying runs

Query functions are plain Python over a list of `Run` objects, so they work with any storage backend.

```python
from maarg import SQLiteStorage, filter_runs, top_n, best_run, compare

runs = SQLiteStorage().list_all()

best_run(runs, "error", higher_is_better=False)
# Run(function='fit', inputs={'learning_rate': 0.01, 'epochs': 100}, metrics={'error': 4.86e-11}, ...)

top_n(runs, "accuracy", n=5)                         # rank by a metric
filter_runs(runs, experiment="fit", learning_rate=0.01)  # exact-match on inputs

compare(top_n(runs, "error", n=3, higher_is_better=False))
# {'run_ids': [...],
#  'inputs':  {'epochs': [100, 100, 100], 'learning_rate': [0.01, 0.003, 0.001]},
#  'metrics': {'error': [4.86e-11, 3.25e-03, 3.24e-01]},
#  'status':  ['success', 'success', 'success']}
```

Failed runs are excluded by default. Pass `only_successful=False` to include them. Runs that lack the metric you rank by are skipped.

## What gets recorded

| Field | Contents |
| --- | --- |
| `run_id` | A UUID, generated automatically |
| `timestamp` | When the run happened (ISO 8601, UTC) |
| `function` | The name of the decorated function |
| `experiment` | A label for grouping runs. Defaults to the function name |
| `inputs` | The arguments the function was called with, defaults included |
| `metrics` | Numeric outputs |
| `artifacts` | Files produced by the run, as `{name, path, type}` entries |
| `other` | Anything that isn't a number or a file |
| `duration_sec` | How long the call took |

**Inputs** are recorded when they are small and simple: numbers, booleans, strings and `None`, plus lists, tuples and dicts of those. By default a scalar larger than about 1000 bytes in memory, or a collection with more than 20 items (checked recursively), is not recorded. Arrays, dataframes, models and any other objects are skipped instead of bloating your database. Both limits can be changed (see Configuration).

**Outputs** are sorted by type:

- Numbers, and dicts of numbers, become `metrics`.
- matplotlib figures are saved as PNG files under `.maarg/artifacts/<run_id>/` and listed in `artifacts` (requires the `plotting` extra).
- Strings, `None` and booleans go to `other` as they are. Anything unrecognised (a list, an array, a custom object) is stored in `other` as a `repr()` truncated to 200 characters, so nothing is silently dropped.
- A return value that isn't a dict is stored under the key `"result"`.

**Failures** are recorded too. If the function raises, maarg saves the run with `other["status"] = "failed"` plus the exception type and message, then re-raises the exception unchanged.

## Configuration

maarg works with no configuration. When you need control, pass options to the decorator:

```python
from maarg import track, SQLiteStorage

@track(experiment="lr-sweep", storage=SQLiteStorage("results/runs.db"))
def train_model(learning_rate, epochs):
    ...
```

All options are keyword-only and optional:

| Option | Default | Purpose |
| --- | --- | --- |
| `experiment` | the function's name | Label for grouping runs |
| `storage` | SQLite at `.maarg/runs.db` | Where runs are saved |
| `artifacts_dir` | `.maarg/artifacts` | Where files such as figures are written |
| `max_scalar_bytes` | `1000` | Size limit for a single recorded input |
| `max_collection_length` | `20` | Item limit for a recorded list, tuple or dict |

With the default backend, the database is created in the current working directory on the first tracked call, not on import.

## Custom storage

Subclass `StorageBackend` and implement five methods: `save`, `get_by_id`, `list_by_function`, `list_by_experiment` and `list_all`. The `list_*` methods must return runs newest-first. Pass your backend with `@track(storage=...)`.

## Roadmap

- A command-line interface to browse, filter and compare runs
- Support for registering new output types
- Hooks that run when a run completes (for example a notification)
- A separate dashboard package
- Additional storage backends

maarg deliberately does not include a hosted tracking server or experiment orchestration. It is meant to sit alongside tools like Optuna, Ray or Airflow, not replace them.

## About the name

*maarg* (मार्ग) is Hindi for "path" or "route".

## License

MIT