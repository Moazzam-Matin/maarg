"""Tests for the top-level convenience layer (get_runs, and storage-aware
top_n / best_run / filter_runs)."""

import maarg
from maarg import best_run, filter_runs, get_runs, top_n
from maarg._models import Run
from maarg.storage._sqlite import SQLiteStorage


def make_run(**overrides):
    defaults = {
        "function": "train_model",
        "experiment": "my-experiment",
        "inputs": {"lr": 0.01},
        "metrics": {"accuracy": 0.9},
    }
    defaults.update(overrides)
    return Run(**defaults)


def seed(storage, runs):
    for r in runs:
        storage.save(r)
    return runs


def test_get_runs_with_no_filters_returns_everything(tmp_path):
    storage = SQLiteStorage(db_path=tmp_path / "t.db")
    r1, r2 = make_run(function="a"), make_run(function="b")
    seed(storage, [r1, r2])
    result = get_runs(storage=storage)
    assert {r.run_id for r in result} == {r1.run_id, r2.run_id}


def test_get_runs_filters_by_function(tmp_path):
    storage = SQLiteStorage(db_path=tmp_path / "t.db")
    r1, r2 = make_run(function="a"), make_run(function="b")
    seed(storage, [r1, r2])
    assert [r.run_id for r in get_runs(function="a", storage=storage)] == [r1.run_id]


def test_get_runs_filters_by_experiment(tmp_path):
    storage = SQLiteStorage(db_path=tmp_path / "t.db")
    r1, r2 = make_run(experiment="exp-a"), make_run(experiment="exp-b")
    seed(storage, [r1, r2])
    assert [r.run_id for r in get_runs(experiment="exp-a", storage=storage)] == [r1.run_id]


def test_get_runs_combines_function_and_experiment_filters(tmp_path):
    storage = SQLiteStorage(db_path=tmp_path / "t.db")
    r1 = make_run(function="a", experiment="exp-a")
    r2 = make_run(function="a", experiment="exp-b")
    r3 = make_run(function="b", experiment="exp-a")
    seed(storage, [r1, r2, r3])
    result = get_runs(function="a", experiment="exp-a", storage=storage)
    assert [r.run_id for r in result] == [r1.run_id]


def test_top_n_auto_fetches_from_storage_when_runs_not_given(tmp_path):
    storage = SQLiteStorage(db_path=tmp_path / "t.db")
    r1, r2 = make_run(metrics={"accuracy": 0.7}), make_run(metrics={"accuracy": 0.95})
    seed(storage, [r1, r2])
    assert top_n(metric="accuracy", n=1, storage=storage) == [r2]


def test_top_n_still_accepts_an_explicit_runs_list():
    r1, r2 = make_run(metrics={"accuracy": 0.7}), make_run(metrics={"accuracy": 0.95})
    assert top_n([r1, r2], metric="accuracy", n=1) == [r2]


def test_best_run_auto_fetches_from_storage(tmp_path):
    storage = SQLiteStorage(db_path=tmp_path / "t.db")
    r1, r2 = make_run(metrics={"accuracy": 0.7}), make_run(metrics={"accuracy": 0.95})
    seed(storage, [r1, r2])
    assert best_run(metric="accuracy", storage=storage) == r2


def test_filter_runs_auto_fetches_from_storage(tmp_path):
    storage = SQLiteStorage(db_path=tmp_path / "t.db")
    r1, r2 = make_run(experiment="exp-a"), make_run(experiment="exp-b")
    seed(storage, [r1, r2])
    assert filter_runs(experiment="exp-a", storage=storage) == [r1]


def test_query_is_no_longer_a_confusing_top_level_attribute():
    """Regression test for the maarg.query collision found during dogfooding —
    internal modules are now underscore-prefixed and shouldn't surface here."""
    assert "query" not in dir(maarg)