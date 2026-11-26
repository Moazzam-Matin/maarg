"""MLflow-inspired Gradio Tracking UI for maarg."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

_SRC_DIR = str(Path(__file__).resolve().parent.parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from ui.charts import (  # noqa: E402
    make_compare_bar_chart,
    make_metric_trend_chart,
    make_parallel_coordinates_chart,
    make_param_vs_metric_chart,
)
from ui.data import (  # noqa: E402
    build_comparison_dataframe,
    build_kpi_html,
    build_run_detail_payload,
    collect_schema_keys,
    ensure_maarg_importable,
    export_runs_csv,
    export_runs_json,
    filter_runs_ui,
    get_experiment_counts,
    load_runs_safe,
    runs_to_dataframe,
)
from ui.demo_seed import seed_demo_runs  # noqa: E402

ensure_maarg_importable()

import starlette.status as _starlette_status  # noqa: E402

# Gradio 6.30 references HTTP_422_UNPROCESSABLE_CONTENT (added in starlette 0.48+),
# which raises AttributeError on older starlette releases (e.g. 0.46.2).
if not hasattr(_starlette_status, "HTTP_422_UNPROCESSABLE_CONTENT"):
    _starlette_status.HTTP_422_UNPROCESSABLE_CONTENT = (  # type: ignore[attr-defined]
        _starlette_status.HTTP_422_UNPROCESSABLE_ENTITY
    )

import gradio as gr  # noqa: E402
from maarg import Run  # noqa: E402
from maarg.storage._sqlite import DEFAULT_DB_PATH  # noqa: E402

HEADER_LOGO_SVG = """
<svg width="32" height="32" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="maargGrad" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0194E2"/>
      <stop offset="100%" stop-color="#06B6D4"/>
    </linearGradient>
  </defs>
  <rect x="2" y="2" width="32" height="32" rx="8" fill="url(#maargGrad)"/>
  <path d="M10 24L15.5 13L20.5 20L26 11" stroke="white" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="10" cy="24" r="2.2" fill="white"/>
  <circle cx="15.5" cy="13" r="2.2" fill="white"/>
  <circle cx="20.5" cy="20" r="2.2" fill="white"/>
  <circle cx="26" cy="11" r="2.2" fill="white"/>
</svg>
"""

CUSTOM_CSS = """
.maarg-topbar {
  border-bottom: 1px solid var(--border-color-primary);
  padding-bottom: 12px;
  margin-bottom: 10px;
}
.maarg-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.maarg-brand-title {
  font-size: 1.3rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin: 0;
}
.maarg-brand-sub {
  font-size: 0.82rem;
  color: var(--body-text-color-subdued);
  margin: 0;
}
.maarg-kpi-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 6px 0 4px 0;
}
.maarg-kpi-card {
  flex: 1 1 130px;
  background: var(--background-fill-secondary);
  border: 1px solid var(--border-color-primary);
  border-radius: 8px;
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.maarg-kpi-path {
  flex: 2 1 220px;
}
.maarg-kpi-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--body-text-color-subdued);
}
.maarg-kpi-value {
  font-size: 1.05rem;
  font-weight: 600;
}
.maarg-run-header {
  border: 1px solid var(--border-color-primary);
  background: var(--background-fill-secondary);
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
}
.maarg-run-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.maarg-run-id {
  font-size: 0.98rem;
  font-weight: 600;
}
.maarg-run-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 0.88rem;
  color: var(--body-text-color-subdued);
}
.maarg-badge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  letter-spacing: 0.04em;
}
.maarg-badge-success {
  background: rgba(16, 185, 129, 0.16);
  color: #059669;
  border: 1px solid rgba(16, 185, 129, 0.4);
}
.maarg-badge-failed {
  background: rgba(239, 68, 68, 0.16);
  color: #DC2626;
  border: 1px solid rgba(239, 68, 68, 0.4);
}
.maarg-error-box {
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.1);
  border-left: 3px solid #EF4444;
  font-size: 0.88rem;
}
.maarg-empty-detail {
  padding: 18px;
  border: 1px dashed var(--border-color-primary);
  border-radius: 8px;
  color: var(--body-text-color-subdued);
  text-align: center;
}
"""


def _run_choice_labels(runs: list[Run]) -> list[tuple[str, str]]:
    return [
        (f"{r.run_id[:8]} · {r.experiment} · {r.function}()", r.run_id)
        for r in runs
    ]


def create_app(default_db_path: str | Path = DEFAULT_DB_PATH) -> gr.Blocks:
    """Create and configure the Gradio Blocks application."""
    initial_db = str(default_db_path)

    with gr.Blocks(title="maarg Tracking UI", fill_width=True) as demo:
        all_runs_state = gr.State([])
        filtered_runs_state = gr.State([])
        filtered_ids_state = gr.State([])

        # ── Left Sidebar (MLflow Experiments & Filters) ──────────────────
        with gr.Sidebar(open=True, width=300, position="left"):
            gr.Markdown("### Experiments & Filters")
            experiment_radio = gr.Radio(
                choices=["All Experiments"],
                value="All Experiments",
                label="Experiments",
            )
            function_dd = gr.Dropdown(
                choices=["All Functions"],
                value="All Functions",
                label="Function",
            )
            status_radio = gr.Radio(
                choices=["All", "Success", "Failed"],
                value="All",
                label="Run Status",
            )
            search_box = gr.Textbox(
                label="Search Runs",
                placeholder="Filter by run ID, param, metric, error...",
            )

            gr.Markdown("### Ranking & Top-N")
            sort_metric_dd = gr.Dropdown(
                choices=["timestamp", "duration_sec"],
                value="timestamp",
                label="Sort / Rank by",
            )
            higher_better_cb = gr.Checkbox(
                value=True,
                label="Descending / Higher is better",
            )
            top_n_slider = gr.Slider(
                minimum=0,
                maximum=50,
                step=1,
                value=0,
                label="Top N Limit (0 = all)",
            )

            gr.Markdown("### Export Filtered Runs")
            with gr.Row():
                export_csv_btn = gr.DownloadButton("Export CSV", size="sm")
                export_json_btn = gr.DownloadButton("Export JSON", size="sm")

        # ── Header Bar ───────────────────────────────────────────────────
        with gr.Row(elem_classes=["maarg-topbar"]):
            with gr.Column(scale=5):
                gr.HTML(
                    f"""
                    <div class="maarg-brand">
                      {HEADER_LOGO_SVG}
                      <div>
                        <p class="maarg-brand-title">maarg Tracking UI</p>
                        <p class="maarg-brand-sub">Local-first experiment tracking</p>
                      </div>
                    </div>
                    """
                )
            with gr.Column(scale=4):
                db_path_tb = gr.Textbox(
                    value=initial_db,
                    label="SQLite Database Path",
                    placeholder=".maarg/runs.db",
                )
            with gr.Column(scale=3):
                with gr.Row():
                    refresh_btn = gr.Button("Refresh", variant="secondary")
                    seed_btn = gr.Button("Seed Demo Runs", variant="primary")

        kpi_html = gr.HTML(build_kpi_html([], initial_db))
        notice_md = gr.Markdown("", visible=False)

        # ── Main Tabs ────────────────────────────────────────────────────
        with gr.Tabs():
            # ── Tab 1: Runs Table + Run Inspector ────────────────────────
            with gr.Tab("Runs"):
                runs_count_md = gr.Markdown("Showing **0** runs")
                runs_df = gr.Dataframe(
                    interactive=False,
                    show_row_numbers=True,
                    show_search="filter",
                    buttons=["fullscreen", "copy"],
                    max_height=380,
                    wrap=False,
                )

                gr.Markdown("### Run Inspector")
                selected_run_dd = gr.Dropdown(
                    choices=[],
                    value=None,
                    label="Inspect Run (or click any row in the table above)",
                )
                run_header_html = gr.HTML(build_run_detail_payload(None)["header_html"])

                with gr.Tabs():
                    with gr.Tab("Parameters"):
                        detail_params_df = gr.Dataframe(
                            interactive=False,
                            buttons=["copy"],
                            max_height=280,
                        )
                    with gr.Tab("Metrics"):
                        detail_metrics_df = gr.Dataframe(
                            interactive=False,
                            buttons=["copy"],
                            max_height=280,
                        )
                    with gr.Tab("Artifacts"):
                        detail_gallery = gr.Gallery(
                            label="Captured Image Artifacts",
                            columns=2,
                            height=340,
                            object_fit="contain",
                            buttons=["download", "fullscreen"],
                        )
                        detail_artifacts_df = gr.Dataframe(
                            interactive=False,
                            buttons=["copy"],
                            max_height=200,
                        )
                    with gr.Tab("Raw JSON"):
                        detail_raw_json = gr.JSON(label="Run Record (Run.to_dict())")

            # ── Tab 2: Charts ────────────────────────────────────────────
            with gr.Tab("Charts"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Metric Trend Over Time")
                        with gr.Row():
                            trend_metric_dd = gr.Dropdown(
                                choices=["duration_sec"],
                                value="duration_sec",
                                label="Metric",
                            )
                            trend_color_dd = gr.Dropdown(
                                choices=["experiment", "function"],
                                value="experiment",
                                label="Color By",
                            )
                        trend_plot = gr.Plot(label="Metric Trend")

                    with gr.Column():
                        gr.Markdown("#### Parameter vs. Metric Scatter")
                        with gr.Row():
                            scatter_x_dd = gr.Dropdown(
                                choices=["duration_sec"],
                                value="duration_sec",
                                label="X (Parameter / Duration)",
                            )
                            scatter_y_dd = gr.Dropdown(
                                choices=["duration_sec"],
                                value="duration_sec",
                                label="Y (Numeric Metric)",
                            )
                            scatter_color_dd = gr.Dropdown(
                                choices=["experiment", "function"],
                                value="experiment",
                                label="Color By",
                            )
                        scatter_plot = gr.Plot(label="Parameter vs Metric")

                gr.Markdown("#### Parallel Coordinates")
                with gr.Row():
                    parcoords_dims_dd = gr.Dropdown(
                        choices=[],
                        value=[],
                        multiselect=True,
                        label="Dimensions (Numeric Params & Metrics)",
                        scale=3,
                    )
                    parcoords_color_dd = gr.Dropdown(
                        choices=[],
                        value=None,
                        label="Color Scale Dimension",
                        scale=1,
                    )
                parcoords_plot = gr.Plot(label="Parallel Coordinates")

            # ── Tab 3: Compare Runs ──────────────────────────────────────
            with gr.Tab("Compare Runs"):
                with gr.Row():
                    compare_runs_dd = gr.Dropdown(
                        choices=[],
                        value=[],
                        multiselect=True,
                        label="Runs to Compare",
                        scale=4,
                    )
                    with gr.Column(scale=2):
                        with gr.Row():
                            cmp_latest_btn = gr.Button("Select Latest 4", size="sm")
                            cmp_top5_btn = gr.Button("Select Top 5", size="sm")
                            cmp_clear_btn = gr.Button("Clear", size="sm")
                        cmp_diff_cb = gr.Checkbox(
                            value=False,
                            label="Show differences only",
                        )

                cmp_metrics_dd = gr.Dropdown(
                    choices=[],
                    value=[],
                    multiselect=True,
                    label="Metrics for Grouped Bar Chart",
                )
                compare_plot = gr.Plot(label="Metrics Comparison")
                compare_df = gr.Dataframe(
                    interactive=False,
                    buttons=["fullscreen", "copy"],
                    max_height=420,
                )
                compare_gallery = gr.Gallery(
                    label="Artifacts Across Compared Runs",
                    columns=3,
                    height=300,
                    object_fit="contain",
                    buttons=["download", "fullscreen"],
                )

        # ── Event Callbacks ──────────────────────────────────────────────
        def _refresh_all(
            db_path: str,
            exp_val: str,
            fn_val: str,
            status_val: str,
            search_val: str,
            sort_val: str,
            higher_val: bool,
            top_n_val: int,
        ):
            runs, message = load_runs_safe(db_path)
            _exps, fns, in_keys, met_keys = collect_schema_keys(runs)
            exp_choices = ["All Experiments"] + [
                f"{name} ({cnt})" for name, cnt in get_experiment_counts(runs)
            ]
            exp_clean = exp_val if exp_val in exp_choices else "All Experiments"
            fn_choices = ["All Functions", *fns]
            fn_clean = fn_val if fn_val in fn_choices else "All Functions"

            sort_choices = ["timestamp", "duration_sec", *met_keys]
            sort_clean = sort_val if sort_val in sort_choices else "timestamp"

            filtered = filter_runs_ui(
                runs,
                experiment=exp_clean,
                function=fn_clean,
                status=status_val,
                search_text=search_val,
                sort_by=sort_clean,
                higher_is_better=higher_val,
                top_n_limit=int(top_n_val),
            )
            df, run_ids = runs_to_dataframe(filtered)
            count_text = f"Showing **{len(filtered)}** of **{len(runs)}** recorded runs"
            notice_update = gr.update(value=message or "", visible=bool(message))

            # Default selections for charts & inspector
            default_inspect = run_ids[0] if run_ids else None
            detail = build_run_detail_payload(filtered[0] if filtered else None)

            default_metric = met_keys[0] if met_keys else "duration_sec"
            default_param = in_keys[0] if in_keys else "duration_sec"
            scatter_x_choices = [*in_keys, "duration_sec"]
            metric_choices = [*met_keys, "duration_sec"]

            # Numeric dimensions for parallel coordinates
            par_dims = [f"param:{k}" for k in in_keys] + [f"metric:{k}" for k in met_keys] + ["duration_sec"]
            default_par_dims = par_dims[: min(4, len(par_dims))]
            default_par_color = default_par_dims[-1] if default_par_dims else None

            cmp_choices = _run_choice_labels(filtered)
            default_cmp_ids = [r.run_id for r in filtered[: min(3, len(filtered))]]
            default_cmp_metrics = met_keys[: min(4, len(met_keys))]

            cmp_runs = [r for r in filtered if r.run_id in set(default_cmp_ids)]
            cmp_table = build_comparison_dataframe(cmp_runs, differences_only=False)
            cmp_chart = make_compare_bar_chart(cmp_runs, default_cmp_metrics)
            cmp_gallery_items = _collect_gallery_items(cmp_runs)

            return (
                runs,
                filtered,
                run_ids,
                build_kpi_html(runs, db_path),
                notice_update,
                gr.update(choices=exp_choices, value=exp_clean),
                gr.update(choices=fn_choices, value=fn_clean),
                gr.update(choices=sort_choices, value=sort_clean),
                count_text,
                df,
                gr.update(choices=cmp_choices, value=default_inspect),
                detail["header_html"],
                detail["params_df"],
                detail["metrics_df"],
                detail["artifacts_df"],
                detail["gallery_items"],
                detail["raw_json"],
                gr.update(choices=metric_choices, value=default_metric),
                make_metric_trend_chart(filtered, default_metric, "experiment"),
                gr.update(choices=scatter_x_choices, value=default_param),
                gr.update(choices=metric_choices, value=default_metric),
                make_param_vs_metric_chart(filtered, default_param, default_metric, "experiment"),
                gr.update(choices=par_dims, value=default_par_dims),
                gr.update(choices=par_dims, value=default_par_color),
                make_parallel_coordinates_chart(filtered, default_par_dims, default_par_color),
                gr.update(choices=cmp_choices, value=default_cmp_ids),
                gr.update(choices=metric_choices, value=default_cmp_metrics),
                cmp_chart,
                cmp_table,
                cmp_gallery_items,
            )

        def _apply_filters(
            runs: list[Run],
            exp_val: str,
            fn_val: str,
            status_val: str,
            search_val: str,
            sort_val: str,
            higher_val: bool,
            top_n_val: int,
            trend_met: str,
            trend_col: str,
            scat_x: str,
            scat_y: str,
            scat_col: str,
            par_dims: list[str],
            par_col: str,
            cmp_diff: bool,
            cmp_mets: list[str],
        ):
            filtered = filter_runs_ui(
                runs,
                experiment=exp_val,
                function=fn_val,
                status=status_val,
                search_text=search_val,
                sort_by=sort_val,
                higher_is_better=higher_val,
                top_n_limit=int(top_n_val),
            )
            df, run_ids = runs_to_dataframe(filtered)
            count_text = f"Showing **{len(filtered)}** of **{len(runs)}** recorded runs"
            default_inspect = run_ids[0] if run_ids else None
            detail = build_run_detail_payload(filtered[0] if filtered else None)
            cmp_choices = _run_choice_labels(filtered)
            default_cmp_ids = [r.run_id for r in filtered[: min(3, len(filtered))]]
            cmp_runs = [r for r in filtered if r.run_id in set(default_cmp_ids)]

            return (
                filtered,
                run_ids,
                count_text,
                df,
                gr.update(choices=cmp_choices, value=default_inspect),
                detail["header_html"],
                detail["params_df"],
                detail["metrics_df"],
                detail["artifacts_df"],
                detail["gallery_items"],
                detail["raw_json"],
                make_metric_trend_chart(filtered, trend_met, trend_col),
                make_param_vs_metric_chart(filtered, scat_x, scat_y, scat_col),
                make_parallel_coordinates_chart(filtered, par_dims, par_col),
                gr.update(choices=cmp_choices, value=default_cmp_ids),
                make_compare_bar_chart(cmp_runs, cmp_mets),
                build_comparison_dataframe(cmp_runs, differences_only=cmp_diff),
                _collect_gallery_items(cmp_runs),
            )

        def _seed_and_refresh(
            db_path: str,
            exp_val: str,
            fn_val: str,
            status_val: str,
            search_val: str,
            sort_val: str,
            higher_val: bool,
            top_n_val: int,
        ):
            target = Path(db_path.strip()) if db_path.strip() else DEFAULT_DB_PATH
            artifacts_dir = target.parent / "artifacts"
            count = seed_demo_runs(db_path=target, artifacts_dir=artifacts_dir)
            results = list(
                _refresh_all(
                    str(target),
                    "All Experiments",
                    "All Functions",
                    "All",
                    "",
                    "timestamp",
                    True,
                    0,
                )
            )
            # Surface a clear confirmation banner in notice_md (index 4)
            results[4] = gr.update(
                value=f"Seeded **{count}** demo runs into `{target}`.",
                visible=True,
            )
            return tuple(results)

        def _inspect_by_id(run_id: str | None, runs: list[Run]):
            target = next((r for r in runs if r.run_id == run_id), None)
            detail = build_run_detail_payload(target)
            return (
                detail["header_html"],
                detail["params_df"],
                detail["metrics_df"],
                detail["artifacts_df"],
                detail["gallery_items"],
                detail["raw_json"],
            )

        def _on_table_select(evt: gr.SelectData, run_ids: list[str], runs: list[Run]):
            row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
            if row_idx is None or row_idx < 0 or row_idx >= len(run_ids):
                return (gr.update(),) + _inspect_by_id(None, runs)
            selected_id = run_ids[row_idx]
            return (selected_id,) + _inspect_by_id(selected_id, runs)

        def _update_compare(
            selected_ids: list[str],
            metric_keys: list[str],
            diffs_only: bool,
            runs: list[Run],
        ):
            id_order = {rid: i for i, rid in enumerate(selected_ids or [])}
            cmp_runs = sorted(
                [r for r in runs if r.run_id in id_order],
                key=lambda r: id_order[r.run_id],
            )
            return (
                make_compare_bar_chart(cmp_runs, metric_keys),
                build_comparison_dataframe(cmp_runs, differences_only=diffs_only),
                _collect_gallery_items(cmp_runs),
            )

        def _select_latest_4(runs: list[Run]):
            return [r.run_id for r in runs[:4]]

        def _select_top_5(runs: list[Run], sort_metric: str, higher: bool):
            ranked = filter_runs_ui(
                runs,
                status="Success",
                sort_by=sort_metric,
                higher_is_better=higher,
                top_n_limit=5,
            )
            return [r.run_id for r in ranked]

        refresh_outputs = [
            all_runs_state,
            filtered_runs_state,
            filtered_ids_state,
            kpi_html,
            notice_md,
            experiment_radio,
            function_dd,
            sort_metric_dd,
            runs_count_md,
            runs_df,
            selected_run_dd,
            run_header_html,
            detail_params_df,
            detail_metrics_df,
            detail_artifacts_df,
            detail_gallery,
            detail_raw_json,
            trend_metric_dd,
            trend_plot,
            scatter_x_dd,
            scatter_y_dd,
            scatter_plot,
            parcoords_dims_dd,
            parcoords_color_dd,
            parcoords_plot,
            compare_runs_dd,
            cmp_metrics_dd,
            compare_plot,
            compare_df,
            compare_gallery,
        ]

        refresh_inputs = [
            db_path_tb,
            experiment_radio,
            function_dd,
            status_radio,
            search_box,
            sort_metric_dd,
            higher_better_cb,
            top_n_slider,
        ]

        demo.load(_refresh_all, inputs=refresh_inputs, outputs=refresh_outputs)
        refresh_btn.click(_refresh_all, inputs=refresh_inputs, outputs=refresh_outputs)
        db_path_tb.submit(_refresh_all, inputs=refresh_inputs, outputs=refresh_outputs)
        seed_btn.click(_seed_and_refresh, inputs=refresh_inputs, outputs=refresh_outputs)

        filter_inputs_list = [
            all_runs_state,
            experiment_radio,
            function_dd,
            status_radio,
            search_box,
            sort_metric_dd,
            higher_better_cb,
            top_n_slider,
            trend_metric_dd,
            trend_color_dd,
            scatter_x_dd,
            scatter_y_dd,
            scatter_color_dd,
            parcoords_dims_dd,
            parcoords_color_dd,
            cmp_diff_cb,
            cmp_metrics_dd,
        ]
        filter_outputs_list = [
            filtered_runs_state,
            filtered_ids_state,
            runs_count_md,
            runs_df,
            selected_run_dd,
            run_header_html,
            detail_params_df,
            detail_metrics_df,
            detail_artifacts_df,
            detail_gallery,
            detail_raw_json,
            trend_plot,
            scatter_plot,
            parcoords_plot,
            compare_runs_dd,
            compare_plot,
            compare_df,
            compare_gallery,
        ]
        for ctrl in [
            experiment_radio,
            function_dd,
            status_radio,
            search_box,
            sort_metric_dd,
            higher_better_cb,
            top_n_slider,
        ]:
            ctrl.change(_apply_filters, inputs=filter_inputs_list, outputs=filter_outputs_list)

        runs_df.select(
            _on_table_select,
            inputs=[filtered_ids_state, filtered_runs_state],
            outputs=[
                selected_run_dd,
                run_header_html,
                detail_params_df,
                detail_metrics_df,
                detail_artifacts_df,
                detail_gallery,
                detail_raw_json,
            ],
        )
        selected_run_dd.change(
            _inspect_by_id,
            inputs=[selected_run_dd, filtered_runs_state],
            outputs=[
                run_header_html,
                detail_params_df,
                detail_metrics_df,
                detail_artifacts_df,
                detail_gallery,
                detail_raw_json,
            ],
        )

        # Chart controls
        for ctrl in [trend_metric_dd, trend_color_dd]:
            ctrl.change(
                make_metric_trend_chart,
                inputs=[filtered_runs_state, trend_metric_dd, trend_color_dd],
                outputs=trend_plot,
            )
        for ctrl in [scatter_x_dd, scatter_y_dd, scatter_color_dd]:
            ctrl.change(
                make_param_vs_metric_chart,
                inputs=[filtered_runs_state, scatter_x_dd, scatter_y_dd, scatter_color_dd],
                outputs=scatter_plot,
            )
        for ctrl in [parcoords_dims_dd, parcoords_color_dd]:
            ctrl.change(
                make_parallel_coordinates_chart,
                inputs=[filtered_runs_state, parcoords_dims_dd, parcoords_color_dd],
                outputs=parcoords_plot,
            )

        # Compare controls
        for ctrl in [compare_runs_dd, cmp_metrics_dd, cmp_diff_cb]:
            ctrl.change(
                _update_compare,
                inputs=[compare_runs_dd, cmp_metrics_dd, cmp_diff_cb, filtered_runs_state],
                outputs=[compare_plot, compare_df, compare_gallery],
            )
        cmp_latest_btn.click(_select_latest_4, inputs=[filtered_runs_state], outputs=compare_runs_dd)
        cmp_top5_btn.click(
            _select_top_5,
            inputs=[filtered_runs_state, sort_metric_dd, higher_better_cb],
            outputs=compare_runs_dd,
        )
        cmp_clear_btn.click(lambda: [], outputs=compare_runs_dd)

        # Export buttons
        export_csv_btn.click(export_runs_csv, inputs=[filtered_runs_state], outputs=export_csv_btn)
        export_json_btn.click(export_runs_json, inputs=[filtered_runs_state], outputs=export_json_btn)

    return demo


def _collect_gallery_items(runs: list[Run]) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for run in runs:
        items.extend(build_run_detail_payload(run)["gallery_items"])
    return items


def main() -> None:
    """CLI entrypoint for launching the maarg Gradio UI."""
    parser = argparse.ArgumentParser(description="Launch the MLflow-style Gradio UI for maarg.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to SQLite runs database.")
    parser.add_argument("--host", default="127.0.0.1", help="Server host address.")
    parser.add_argument("--port", type=int, default=7860, help="Server port.")
    parser.add_argument("--share", action="store_true", help="Create a public Gradio share link.")
    args = parser.parse_args()

    app = create_app(default_db_path=args.db)
    icon_path = Path(__file__).resolve().parent.parent.parent / "docs" / "assets" / "maarg_icon.svg"
    allowed = [
        str(Path.cwd().resolve()),
        str(Path(args.db).resolve().parent),
        str((Path.cwd() / ".maarg").resolve()),
    ]
    app.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        theme=gr.themes.Soft(primary_hue="blue", secondary_hue="slate"),
        css=CUSTOM_CSS,
        favicon_path=str(icon_path) if icon_path.is_file() else None,
        allowed_paths=allowed,
    )


if __name__ == "__main__":
    main()
