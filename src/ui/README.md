# maarg Tracking UI (`src/ui/`)

An MLflow-inspired Gradio UI for inspecting, ranking, visualizing, comparing, and exporting experiments tracked with `maarg`.

## Features

- **Experiments Sidebar**: Browse experiments with run counts, filter by function or status (`Success` / `Failed`), search across parameters/metrics/errors, and rank Top-N runs by any numeric metric.
- **Runs Table & Run Inspector**: Click any row in the Runs table to inspect its metadata, parameters, flattened and raw structured metrics (`v0.4.0+` nested dicts), Matplotlib image artifacts, and full `Run` JSON.
- **Charts**: Interactive Plotly visualizations for **Metric Trend over Time**, **Parameter vs. Metric Scatter**, and **Parallel Coordinates**.
- **Compare Runs**: Multi-select runs for side-by-side parameter/metric diffing (with a *Show differences only* toggle), grouped bar charts, and artifact comparison.
- **Safe Read-Only & Export**: Never auto-creates an empty SQLite file on missing paths; includes one-click **Export CSV** / **Export JSON** and a **Seed Demo Runs** button using `@track`.

## Design Principles

- Keep UI dependencies separate from core `maarg` dependencies.
- Do not modify core tracking behavior to support the UI.
- Use existing `maarg` storage and query APIs wherever possible.
- Keep the interface local-first initially.

## Quick Start

Install the UI dependencies (Gradio, Starlette, Plotly, Pandas, Matplotlib):

```bash
pip install -r src/ui/requirements.txt
```

Launch the UI (from the repository root):

```bash
python src/ui/app.py
```

Or run as a module with `src` on `PYTHONPATH`:

```powershell
$env:PYTHONPATH="src"; python -m ui.app
```

```bash
PYTHONPATH=src python -m ui.app
```

Optional CLI flags:

```bash
python src/ui/app.py --db path/to/runs.db --port 7860 --host 127.0.0.1
```

If `.maarg/runs.db` does not exist yet, click **Seed Demo Runs** in the top bar to populate sample ML, RecSys, and RAG experiments with Matplotlib artifacts.

## Running UI Tests

```bash
python -m unittest discover -s src/ui/tests -t src -v
```
