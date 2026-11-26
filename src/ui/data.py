"""Data loading, flattening, filtering, comparison, and export helpers for the UI."""

from __future__ import annotations

import csv
import html
import json
import math
import sqlite3
import sys
import tempfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any


def ensure_maarg_importable() -> None:
    """Ensure local ``src/`` is on ``sys.path`` when running without editable install."""
    src_dir = Path(__file__).resolve().parent.parent
    if src_dir.is_dir():
        src_str = str(src_dir)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)


ensure_maarg_importable()

import pandas as pd  # noqa: E402
from maarg import Run, SQLiteStorage, compare  # noqa: E402
from maarg.storage._sqlite import DEFAULT_DB_PATH  # noqa: E402


def is_numeric_value(value: Any) -> bool:
    """Return True for finite int/float values, excluding booleans."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def run_status(run: Run) -> str:
    """Return ``'failed'`` if explicitly marked failed, else ``'success'``."""
    return "failed" if run.other.get("status") == "failed" else "success"


def flatten_dict(data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    """
    Flatten nested dictionaries using dot notation.

    Example: ``{"precision_at_k": {"5": 0.061}}`` -> ``{"precision_at_k.5": 0.061}``.
    """
    flat: dict[str, Any] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict) and value:
            flat.update(flatten_dict(value, prefix=full_key))
        else:
            flat[full_key] = value
    return flat


def format_cell_value(value: Any) -> Any:
    """Format complex leaf values cleanly for DataFrame cells."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, (int, str)):
        return value
    return json.dumps(value, ensure_ascii=False)


def format_timestamp_short(ts: str) -> str:
    """Format an ISO-8601 timestamp into a concise UTC display string."""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ts


def load_runs_safe(db_path: str | Path) -> tuple[list[Run], str | None]:
    """
    Load runs from SQLite without auto-creating a missing database file.

    Returns ``(runs, status_message)``. ``status_message`` is None when loaded cleanly.
    """
    raw = str(db_path).strip()
    path = Path(raw) if raw else DEFAULT_DB_PATH
    if not path.exists():
        return (
            [],
            f"Database not found at `{path}`. Run `@track` functions or click **Seed Demo Runs**.",
        )

    try:
        storage = SQLiteStorage(db_path=path)
        runs = storage.list_all()
    except (sqlite3.Error, ValueError, OSError) as exc:
        return ([], f"Failed to read database `{path}`: {exc}")

    if not runs:
        return (
            [],
            f"Database `{path}` has no recorded runs yet. Click **Seed Demo Runs** to explore.",
        )
    return (runs, None)


def get_experiment_counts(runs: Sequence[Run]) -> list[tuple[str, int]]:
    """Return ``(experiment_name, count)`` pairs sorted by latest run appearance."""
    counts: dict[str, int] = {}
    for run in runs:
        counts[run.experiment] = counts.get(run.experiment, 0) + 1
    return list(counts.items())


def collect_schema_keys(
    runs: Sequence[Run],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Extract sorted metadata & flattened keys across runs.

    Returns ``(experiments, functions, input_keys, numeric_metric_keys)``.
    """
    experiments = sorted({r.experiment for r in runs})
    functions = sorted({r.function for r in runs})
    input_keys = sorted({k for r in runs for k in flatten_dict(r.inputs)})
    numeric_metric_keys = sorted(
        {
            k
            for r in runs
            for k, v in flatten_dict(r.metrics).items()
            if is_numeric_value(v)
        }
    )
    return experiments, functions, input_keys, numeric_metric_keys


def filter_runs_ui(
    runs: Sequence[Run],
    *,
    experiment: str = "All Experiments",
    function: str = "All Functions",
    status: str = "All",
    search_text: str = "",
    sort_by: str = "timestamp",
    higher_is_better: bool = True,
    top_n_limit: int = 0,
) -> list[Run]:
    """Filter, search, sort, and optionally limit runs for the UI."""
    # Strip trailing count badge if the sidebar label looks like "exp-name (5)"
    exp_filter = experiment.rsplit(" (", 1)[0] if " (" in experiment else experiment
    query = search_text.strip().lower()

    filtered: list[Run] = []
    for run in runs:
        if exp_filter and exp_filter != "All Experiments" and run.experiment != exp_filter:
            continue
        if function and function != "All Functions" and run.function != function:
            continue
        st = run_status(run)
        if status == "Success" and st != "success":
            continue
        if status == "Failed" and st != "failed":
            continue
        if query:
            haystack = " ".join(
                [
                    run.run_id,
                    run.experiment,
                    run.function,
                    st,
                    json.dumps(run.inputs, ensure_ascii=False),
                    json.dumps(run.metrics, ensure_ascii=False),
                    json.dumps(run.other, ensure_ascii=False),
                ]
            ).lower()
            if query not in haystack:
                continue
        filtered.append(run)

    if sort_by == "timestamp":
        ordered = sorted(filtered, key=lambda r: r.timestamp, reverse=higher_is_better)
    elif sort_by == "duration_sec":
        ordered = sorted(filtered, key=lambda r: r.duration_sec, reverse=higher_is_better)
    else:
        # Rank by flattened numeric metric; runs missing it (or failed if top_n_limit > 0)
        with_metric: list[tuple[float, Run]] = []
        without_metric: list[Run] = []
        for run in filtered:
            flat_metrics = flatten_dict(run.metrics)
            val = flat_metrics.get(sort_by)
            is_valid = is_numeric_value(val) and (
                top_n_limit <= 0 or run_status(run) == "success"
            )
            if is_valid:
                with_metric.append((float(val), run))
            else:
                without_metric.append(run)

        with_metric.sort(key=lambda pair: pair[0], reverse=higher_is_better)
        ordered = [r for _, r in with_metric]
        if top_n_limit <= 0:
            ordered.extend(without_metric)

    if top_n_limit > 0:
        return ordered[:top_n_limit]
    return ordered


def runs_to_dataframe(runs: Sequence[Run]) -> tuple[pd.DataFrame, list[str]]:
    """
    Convert runs into an MLflow-style DataFrame and parallel full ``run_ids`` list.
    """
    if not runs:
        empty = pd.DataFrame(
            columns=["Status", "Run ID", "Experiment", "Function", "Created", "Duration (s)"]
        )
        return empty, []

    flat_inputs_list = [flatten_dict(r.inputs) for r in runs]
    flat_metrics_list = [flatten_dict(r.metrics) for r in runs]

    all_input_keys = sorted({k for d in flat_inputs_list for k in d})
    all_metric_keys = sorted({k for d in flat_metrics_list for k in d})

    rows: list[dict[str, Any]] = []
    run_ids: list[str] = []

    for run, f_in, f_met in zip(runs, flat_inputs_list, flat_metrics_list):
        st = run_status(run)
        row: dict[str, Any] = {
            "Status": "✅ success" if st == "success" else "❌ failed",
            "Run ID": run.run_id[:8],
            "Experiment": run.experiment,
            "Function": run.function,
            "Created": format_timestamp_short(run.timestamp),
            "Duration (s)": round(run.duration_sec, 4),
        }
        for key in all_input_keys:
            row[f"param:{key}"] = format_cell_value(f_in.get(key))
        for key in all_metric_keys:
            row[f"metric:{key}"] = format_cell_value(f_met.get(key))
        row["Artifacts"] = len(run.artifacts)
        rows.append(row)
        run_ids.append(run.run_id)

    return pd.DataFrame(rows), run_ids


def build_kpi_html(runs: Sequence[Run], db_path: str | Path) -> str:
    """Build MLflow-style summary KPI strip HTML."""
    total = len(runs)
    experiments = len({r.experiment for r in runs})
    successes = sum(1 for r in runs if run_status(r) == "success")
    rate = f"{(successes / total * 100):.0f}%" if total else "—"
    avg_dur = f"{(sum(r.duration_sec for r in runs) / total):.3f}s" if total else "—"
    safe_path = html.escape(str(db_path))

    return f"""
    <div class="maarg-kpi-strip">
      <div class="maarg-kpi-card">
        <span class="maarg-kpi-label">Total Runs</span>
        <span class="maarg-kpi-value">{total}</span>
      </div>
      <div class="maarg-kpi-card">
        <span class="maarg-kpi-label">Experiments</span>
        <span class="maarg-kpi-value">{experiments}</span>
      </div>
      <div class="maarg-kpi-card">
        <span class="maarg-kpi-label">Success Rate</span>
        <span class="maarg-kpi-value">{rate}</span>
      </div>
      <div class="maarg-kpi-card">
        <span class="maarg-kpi-label">Avg Duration</span>
        <span class="maarg-kpi-value">{avg_dur}</span>
      </div>
      <div class="maarg-kpi-card maarg-kpi-path">
        <span class="maarg-kpi-label">Storage</span>
        <span class="maarg-kpi-value"><code>{safe_path}</code></span>
      </div>
    </div>
    """


def build_run_detail_payload(run: Run | None) -> dict[str, Any]:
    """Build structured tables, HTML header, JSON views, and gallery items for a Run."""
    if run is None:
        return {
            "header_html": (
                "<div class='maarg-empty-detail'>Select any run from the table above "
                "to inspect its parameters, metrics, artifacts, and execution metadata.</div>"
            ),
            "params_df": pd.DataFrame(columns=["Parameter", "Value"]),
            "metrics_df": pd.DataFrame(columns=["Metric", "Value"]),
            "artifacts_df": pd.DataFrame(columns=["Name", "Type", "Path", "Exists"]),
            "gallery_items": [],
            "raw_json": {},
        }

    st = run_status(run)
    badge_cls = "maarg-badge-success" if st == "success" else "maarg-badge-failed"
    badge_text = "SUCCESS" if st == "success" else "FAILED"

    error_html = ""
    if st == "failed":
        err_type = html.escape(str(run.other.get("error_type", "Exception")))
        err_msg = html.escape(str(run.other.get("error_message", "")))
        error_html = (
            f"<div class='maarg-error-box'><strong>{err_type}:</strong> {err_msg}</div>"
        )

    header_html = f"""
    <div class="maarg-run-header">
      <div class="maarg-run-title-row">
        <span class="maarg-badge {badge_cls}">{badge_text}</span>
        <span class="maarg-run-id">Run <code>{html.escape(run.run_id)}</code></span>
      </div>
      <div class="maarg-run-meta">
        <span><strong>Experiment:</strong> {html.escape(run.experiment)}</span>
        <span><strong>Function:</strong> <code>{html.escape(run.function)}()</code></span>
        <span><strong>Created:</strong> {html.escape(format_timestamp_short(run.timestamp))} UTC</span>
        <span><strong>Duration:</strong> {run.duration_sec:.4f}s</span>
        <span><strong>Artifacts:</strong> {len(run.artifacts)}</span>
      </div>
      {error_html}
    </div>
    """

    flat_inputs = flatten_dict(run.inputs)
    params_df = (
        pd.DataFrame(
            [{"Parameter": k, "Value": format_cell_value(v)} for k, v in sorted(flat_inputs.items())]
        )
        if flat_inputs
        else pd.DataFrame(columns=["Parameter", "Value"])
    )

    flat_metrics = flatten_dict(run.metrics)
    metrics_df = (
        pd.DataFrame(
            [{"Metric": k, "Value": format_cell_value(v)} for k, v in sorted(flat_metrics.items())]
        )
        if flat_metrics
        else pd.DataFrame(columns=["Metric", "Value"])
    )

    artifact_rows: list[dict[str, Any]] = []
    gallery_items: list[tuple[str, str]] = []
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}

    for art in run.artifacts:
        art_path = Path(art.get("path", ""))
        exists = art_path.is_file()
        artifact_rows.append(
            {
                "Name": art.get("name", ""),
                "Type": art.get("type", ""),
                "Path": str(art_path),
                "Exists": "Yes" if exists else "Missing",
            }
        )
        if exists and art_path.suffix.lower() in image_exts:
            gallery_items.append(
                (str(art_path.resolve()), f"{art.get('name', 'artifact')} ({run.run_id[:8]})")
            )

    artifacts_df = (
        pd.DataFrame(artifact_rows)
        if artifact_rows
        else pd.DataFrame(columns=["Name", "Type", "Path", "Exists"])
    )

    return {
        "header_html": header_html,
        "params_df": params_df,
        "metrics_df": metrics_df,
        "artifacts_df": artifacts_df,
        "gallery_items": gallery_items,
        "raw_json": run.to_dict(),
    }


def build_comparison_dataframe(
    runs: Sequence[Run],
    *,
    differences_only: bool = False,
) -> pd.DataFrame:
    """
    Build a side-by-side MLflow-style comparison DataFrame across ``runs``.

    Uses ``maarg.compare(runs)`` for top-level structure and flattens nested dicts
    for granular cell-by-cell diffing.
    """
    if not runs:
        return pd.DataFrame(columns=["Category", "Field", "Differs"])

    # Leverage core maarg.compare() alongside flattened views for nested metrics
    _core_cmp = compare(runs)
    run_cols = [f"{r.run_id[:8]} ({r.experiment})" for r in runs]

    rows: list[dict[str, Any]] = []

    def _add_row(category: str, field: str, values: list[Any]) -> None:
        formatted = [format_cell_value(v) for v in values]
        serialized = {json.dumps(v, sort_keys=True, default=str) for v in formatted}
        differs = len(serialized) > 1
        if differences_only and not differs:
            return
        entry: dict[str, Any] = {
            "Category": category,
            "Field": field,
            "Differs": "Yes" if differs else "No",
        }
        for col, val in zip(run_cols, formatted):
            entry[col] = val
        rows.append(entry)

    _add_row("Metadata", "experiment", [r.experiment for r in runs])
    _add_row("Metadata", "function", [r.function for r in runs])
    _add_row("Metadata", "status", _core_cmp["status"])
    _add_row("Metadata", "duration_sec", [round(r.duration_sec, 4) for r in runs])
    _add_row("Metadata", "timestamp", [format_timestamp_short(r.timestamp) for r in runs])

    flat_inputs = [flatten_dict(r.inputs) for r in runs]
    for key in sorted({k for d in flat_inputs for k in d}):
        _add_row("Parameter", key, [d.get(key) for d in flat_inputs])

    flat_metrics = [flatten_dict(r.metrics) for r in runs]
    for key in sorted({k for d in flat_metrics for k in d}):
        _add_row("Metric", key, [d.get(key) for d in flat_metrics])

    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Category", "Field", "Differs", *run_cols])


def export_runs_csv(runs: Sequence[Run], output_path: Path | None = None) -> str:
    """Export runs (with flattened inputs & metrics) to a CSV file and return its path."""
    if output_path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(tempfile.gettempdir()) / f"maarg_runs_{stamp}.csv"

    df, full_ids = runs_to_dataframe(runs)
    if not df.empty:
        df["Run ID"] = full_ids
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, quoting=csv.QUOTE_MINIMAL)
    return str(output_path)


def export_runs_json(runs: Sequence[Run], output_path: Path | None = None) -> str:
    """Export runs as structured JSON and return the created file path."""
    if output_path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(tempfile.gettempdir()) / f"maarg_runs_{stamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_dict() for r in runs]
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(output_path)
