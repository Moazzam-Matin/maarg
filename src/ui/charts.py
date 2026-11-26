"""Plotly visualization builders for the MLflow-style maarg Gradio UI."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import plotly.graph_objects as go

from ui.data import flatten_dict, format_timestamp_short, is_numeric_value, run_status
from maarg import Run

PALETTE = [
    "#0194E2",  # MLflow blue
    "#10B981",  # emerald
    "#F59E0B",  # amber
    "#8B5CF6",  # violet
    "#EF4444",  # coral
    "#06B6D4",  # cyan
    "#EC4899",  # pink
]


def _base_layout(title: str) -> dict[str, Any]:
    return {
        "title": {"text": title, "font": {"size": 15}},
        "template": "plotly_white",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(248, 250, 252, 0.65)",
        "margin": {"l": 56, "r": 24, "t": 48, "b": 52},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        "hovermode": "closest",
    }


def _empty_figure(title: str, message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        **_base_layout(title),
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 13, "color": "#64748B"},
            }
        ],
    )
    return fig


def make_metric_trend_chart(
    runs: Sequence[Run],
    metric_key: str | None,
    color_by: str = "experiment",
) -> go.Figure:
    """Line + marker trend of a numeric metric across chronological runs."""
    if not runs:
        return _empty_figure("Metric Trend", "No runs match the current filters.")
    if not metric_key:
        return _empty_figure("Metric Trend", "Select a numeric metric to plot.")

    ordered = sorted(runs, key=lambda r: r.timestamp)
    groups: dict[str, list[tuple[Run, float]]] = {}

    for run in ordered:
        val = (
            run.duration_sec
            if metric_key == "duration_sec"
            else flatten_dict(run.metrics).get(metric_key)
        )
        if not is_numeric_value(val):
            continue
        group_name = getattr(run, color_by, run.experiment)
        groups.setdefault(str(group_name), []).append((run, float(val)))

    if not groups:
        return _empty_figure(
            f"Trend: {metric_key}",
            f"No finite numeric values found for '{metric_key}'.",
        )

    fig = go.Figure()
    for idx, (group_name, points) in enumerate(groups.items()):
        color = PALETTE[idx % len(PALETTE)]
        xs = [format_timestamp_short(r.timestamp) for r, _ in points]
        ys = [v for _, v in points]
        hovers = [
            f"<b>{r.run_id[:8]}</b> ({r.experiment})<br>"
            f"Function: {r.function}<br>"
            f"{metric_key}: {v:.5g}<br>"
            f"Status: {run_status(r)}"
            for r, v in points
        ]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines+markers",
                name=group_name,
                line={"color": color, "width": 2},
                marker={"size": 8, "color": color},
                text=hovers,
                hovertemplate="%{text}<extra></extra>",
            )
        )

    fig.update_layout(
        **_base_layout(f"Metric Trend — {metric_key}"),
        xaxis_title="Run Timestamp (UTC)",
        yaxis_title=metric_key,
    )
    return fig


def make_param_vs_metric_chart(
    runs: Sequence[Run],
    x_field: str | None,
    y_metric: str | None,
    color_by: str = "experiment",
) -> go.Figure:
    """Scatter plot of an input parameter (or duration) against a numeric metric."""
    if not runs:
        return _empty_figure("Parameter vs. Metric", "No runs match the current filters.")
    if not x_field or not y_metric:
        return _empty_figure("Parameter vs. Metric", "Choose both an X parameter and a Y metric.")

    groups: dict[str, list[tuple[Run, Any, float]]] = {}
    for run in runs:
        flat_in = flatten_dict(run.inputs)
        flat_met = flatten_dict(run.metrics)
        x_val = run.duration_sec if x_field == "duration_sec" else flat_in.get(x_field)
        y_val = run.duration_sec if y_metric == "duration_sec" else flat_met.get(y_metric)
        if x_val is None or not is_numeric_value(y_val):
            continue
        group_name = str(getattr(run, color_by, run.experiment))
        x_display = x_val if isinstance(x_val, (int, float, str)) and not isinstance(x_val, bool) else str(x_val)
        groups.setdefault(group_name, []).append((run, x_display, float(y_val)))

    if not groups:
        return _empty_figure(
            f"{x_field} vs {y_metric}",
            f"No runs contain both '{x_field}' and numeric '{y_metric}'.",
        )

    fig = go.Figure()
    for idx, (group_name, points) in enumerate(groups.items()):
        color = PALETTE[idx % len(PALETTE)]
        xs = [x for _, x, _ in points]
        ys = [y for _, _, y in points]
        hovers = [
            f"<b>{r.run_id[:8]}</b> ({r.experiment})<br>"
            f"{x_field}: {x}<br>"
            f"{y_metric}: {y:.5g}"
            for r, x, y in points
        ]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers",
                name=group_name,
                marker={"size": 10, "color": color, "opacity": 0.88},
                text=hovers,
                hovertemplate="%{text}<extra></extra>",
            )
        )

    fig.update_layout(
        **_base_layout(f"{x_field} vs {y_metric}"),
        xaxis_title=x_field,
        yaxis_title=y_metric,
    )
    return fig


def make_parallel_coordinates_chart(
    runs: Sequence[Run],
    dimensions: Sequence[str],
    color_metric: str | None,
) -> go.Figure:
    """Build an MLflow-style Parallel Coordinates plot over numeric params and metrics."""
    if len(runs) < 2:
        return _empty_figure(
            "Parallel Coordinates",
            "Need at least 2 runs to draw parallel coordinates.",
        )

    selected = list(dimensions)
    if len(selected) < 2:
        return _empty_figure(
            "Parallel Coordinates",
            "Select at least 2 numeric parameters or metrics.",
        )

    def _extract_field(run: Run, spec: str) -> Any:
        if spec == "duration_sec":
            return run.duration_sec
        if spec.startswith("param:"):
            return flatten_dict(run.inputs).get(spec[6:])
        if spec.startswith("metric:"):
            return flatten_dict(run.metrics).get(spec[7:])
        return flatten_dict(run.metrics).get(spec)

    # Filter to runs where every chosen dimension has a finite numeric value
    valid_runs: list[Run] = []
    for run in runs:
        if all(is_numeric_value(_extract_field(run, d)) for d in selected):
            valid_runs.append(run)

    if len(valid_runs) < 2:
        return _empty_figure(
            "Parallel Coordinates",
            "Fewer than 2 runs have numeric values for all selected dimensions.",
        )

    parcoords_dims = [
        {
            "label": dim.replace("param:", "").replace("metric:", ""),
            "values": [float(_extract_field(r, dim)) for r in valid_runs],
        }
        for dim in selected
    ]

    color_field = color_metric if color_metric in selected else selected[-1]
    color_vals = [float(_extract_field(r, color_field)) for r in valid_runs]

    fig = go.Figure(
        data=[
            go.Parcoords(
                line={
                    "color": color_vals,
                    "colorscale": "Viridis",
                    "showscale": True,
                    "colorbar": {"title": color_field.replace("metric:", "").replace("param:", "")},
                },
                dimensions=parcoords_dims,
            )
        ]
    )
    fig.update_layout(**_base_layout("Parallel Coordinates — Hyperparameters & Metrics"))
    return fig


def make_compare_bar_chart(
    runs: Sequence[Run],
    metric_keys: Sequence[str],
) -> go.Figure:
    """Grouped bar chart comparing numeric metrics across selected runs."""
    if not runs:
        return _empty_figure("Compare Metrics", "Select 2 or more runs to compare.")
    keys = list(metric_keys)
    if not keys:
        return _empty_figure("Compare Metrics", "No numeric metrics selected for comparison.")

    fig = go.Figure()
    run_labels = [f"{r.run_id[:8]} ({r.function})" for r in runs]

    for idx, key in enumerate(keys):
        y_vals = []
        for run in runs:
            val = (
                run.duration_sec
                if key == "duration_sec"
                else flatten_dict(run.metrics).get(key)
            )
            y_vals.append(float(val) if is_numeric_value(val) else 0.0)
        fig.add_trace(
            go.Bar(
                name=key,
                x=run_labels,
                y=y_vals,
                marker_color=PALETTE[idx % len(PALETTE)],
            )
        )

    fig.update_layout(
        **_base_layout("Run Metrics Comparison"),
        barmode="group",
        xaxis_title="Run",
        yaxis_title="Value",
    )
    return fig
