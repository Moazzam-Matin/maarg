"""Unit tests for frontend data, charts, seeding, and app construction."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from ui.app import create_app
from ui.charts import (
    make_compare_bar_chart,
    make_metric_trend_chart,
    make_parallel_coordinates_chart,
    make_param_vs_metric_chart,
)
from ui.data import (
    build_comparison_dataframe,
    build_run_detail_payload,
    export_runs_csv,
    export_runs_json,
    filter_runs_ui,
    flatten_dict,
    load_runs_safe,
    runs_to_dataframe,
)
from ui.demo_seed import seed_demo_runs
from maarg import Run, SQLiteStorage


class TestFrontendDataAndCharts(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.db_path = self.tmp_path / "runs.db"

    def tearDown(self) -> None:
        self.tmp_dir.cleanup()

    def test_load_runs_safe_does_not_create_missing_db(self) -> None:
        missing = self.tmp_path / "nonexistent" / "runs.db"
        runs, msg = load_runs_safe(missing)
        self.assertEqual(runs, [])
        self.assertIsNotNone(msg)
        self.assertFalse(missing.exists())

    def test_flatten_dict_handles_nested_evaluation_metrics(self) -> None:
        nested = {
            "ndcg": 0.14,
            "precision_at_k": {"5": 0.061, "10": 0.058},
            "diagnostics": {"converged": True},
        }
        self.assertEqual(
            flatten_dict(nested),
            {
                "ndcg": 0.14,
                "precision_at_k.5": 0.061,
                "precision_at_k.10": 0.058,
                "diagnostics.converged": True,
            },
        )

    def test_seed_demo_runs_and_query_pipeline(self) -> None:
        artifacts_dir = self.tmp_path / "artifacts"
        count = seed_demo_runs(db_path=self.db_path, artifacts_dir=artifacts_dir)
        self.assertGreaterEqual(count, 10)

        runs, msg = load_runs_safe(self.db_path)
        self.assertIsNone(msg)
        self.assertEqual(len(runs), count)

        # Verify failed run is surfaced cleanly and excluded when Top-N ranking
        failed = filter_runs_ui(runs, status="Failed")
        self.assertEqual(len(failed), 1)
        self.assertIn("CUDA out of memory", failed[0].other["error_message"])

        top3 = filter_runs_ui(
            runs,
            experiment="mnist-cnn-sweep (7)",
            sort_by="accuracy",
            higher_is_better=True,
            top_n_limit=3,
        )
        self.assertEqual(len(top3), 3)
        accs = [r.metrics["accuracy"] for r in top3]
        self.assertEqual(accs, sorted(accs, reverse=True))

        df, run_ids = runs_to_dataframe(runs)
        self.assertEqual(len(df), len(runs))
        self.assertEqual(len(run_ids), len(runs))
        self.assertIn("metric:precision_at_k.5", df.columns)

    def test_comparison_and_exports(self) -> None:
        storage = SQLiteStorage(self.db_path)
        r1 = Run(
            function="train",
            experiment="exp-a",
            inputs={"lr": 0.01, "epochs": 10},
            metrics={"accuracy": 0.9, "nested": {"f1": 0.88}},
        )
        r2 = Run(
            function="train",
            experiment="exp-a",
            inputs={"lr": 0.02, "epochs": 10},
            metrics={"accuracy": 0.95, "nested": {"f1": 0.93}},
        )
        storage.save(r1)
        storage.save(r2)
        runs = storage.list_all()

        cmp_all = build_comparison_dataframe(runs, differences_only=False)
        cmp_diff = build_comparison_dataframe(runs, differences_only=True)
        self.assertGreater(len(cmp_all), len(cmp_diff))
        self.assertNotIn("epochs", cmp_diff["Field"].tolist())
        self.assertIn("lr", cmp_diff["Field"].tolist())
        self.assertIn("nested.f1", cmp_diff["Field"].tolist())

        csv_path = Path(export_runs_csv(runs, self.tmp_path / "out.csv"))
        with csv_path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)

        json_path = Path(export_runs_json(runs, self.tmp_path / "out.json"))
        parsed = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(len(parsed), 2)

    def test_run_detail_and_charts_and_app_build(self) -> None:
        r1 = Run(
            function="train",
            experiment="exp-a",
            inputs={"lr": 0.01},
            metrics={"accuracy": 0.9},
            duration_sec=1.2,
        )
        r2 = Run(
            function="train",
            experiment="exp-a",
            inputs={"lr": 0.02},
            metrics={"accuracy": 0.94},
            duration_sec=1.5,
        )
        detail = build_run_detail_payload(r1)
        self.assertIn(r1.run_id, detail["header_html"])

        fig1 = make_metric_trend_chart([r1, r2], "accuracy")
        fig2 = make_param_vs_metric_chart([r1, r2], "lr", "accuracy")
        fig3 = make_parallel_coordinates_chart([r1, r2], ["param:lr", "metric:accuracy"], "metric:accuracy")
        fig4 = make_compare_bar_chart([r1, r2], ["accuracy", "duration_sec"])
        self.assertEqual(len(fig1.data), 1)
        self.assertEqual(len(fig2.data), 1)
        self.assertEqual(len(fig3.data), 1)
        self.assertEqual(len(fig4.data), 2)

        app = create_app(default_db_path=self.db_path)
        self.assertIsNotNone(app)


if __name__ == "__main__":
    unittest.main()
