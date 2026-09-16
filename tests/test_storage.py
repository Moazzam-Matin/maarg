"""Tests for the SQLite storage backend."""

import sqlite3
import time

import pytest

from maarg.models import Run
from maarg.storage.sqlite import SQLiteStorage


def make_run(**overrides):
    defaults = dict(
        function="train_model",
        experiment="my-experiment",
        inputs={"lr": 0.01},
        metrics={"accuracy": 0.9},
    )
    defaults.update(overrides)
    return Run(**defaults)


@pytest.fixture
def storage(tmp_path):
    """A fresh SQLiteStorage backed by a throwaway .db file per test."""
    return SQLiteStorage(db_path=tmp_path / "test_runs.db")


# ── Setup / schema ───────────────────────────────────────────────────

def test_db_file_and_parent_folder_are_created(tmp_path):
    db_path = tmp_path / "nested" / "does" / "not" / "exist" / "runs.db"
    SQLiteStorage(db_path=db_path)
    assert db_path.exists()


def test_default_db_path_is_dot_maarg_runs_db():
    assert SQLiteStorage.__init__.__defaults__ is not None  # sanity: has a default
    from maarg.storage.sqlite import DEFAULT_DB_PATH
    assert str(DEFAULT_DB_PATH) == str(__import__("pathlib").Path(".maarg") / "runs.db")


# ── save + get_by_id ─────────────────────────────────────────────────

def test_save_and_get_by_id_round_trips_a_run(storage):
    run = make_run()
    storage.save(run)

    retrieved = storage.get_by_id(run.run_id)

    assert retrieved is not None
    assert retrieved.run_id == run.run_id
    assert retrieved.function == run.function
    assert retrieved.experiment == run.experiment
    assert retrieved.inputs == run.inputs
    assert retrieved.metrics == run.metrics
    assert retrieved.artifacts == run.artifacts
    assert retrieved.other == run.other


def test_get_by_id_returns_none_for_missing_run(storage):
    assert storage.get_by_id("does-not-exist") is None


def test_saving_duplicate_run_id_raises(storage):
    run = make_run()
    storage.save(run)
    with pytest.raises(sqlite3.IntegrityError):
        storage.save(run)


def test_nested_fields_survive_json_round_trip(storage):
    run = make_run(
        inputs={"layers": [128, 64], "config": {"beta1": 0.9}},
        artifacts=[{"name": "chart", "path": "x.png", "type": "chart"}],
        other={"status": "converged", "flag": True},
    )
    storage.save(run)
    retrieved = storage.get_by_id(run.run_id)

    assert retrieved.inputs == {"layers": [128, 64], "config": {"beta1": 0.9}}
    assert retrieved.artifacts == [{"name": "chart", "path": "x.png", "type": "chart"}]
    assert retrieved.other == {"status": "converged", "flag": True}


# ── list_by_function / list_by_experiment / list_all ────────────────

def test_list_by_function_returns_only_matching_runs(storage):
    r1 = make_run(function="train_model")
    r2 = make_run(function="train_model")
    r3 = make_run(function="other_function")
    for r in (r1, r2, r3):
        storage.save(r)

    results = storage.list_by_function("train_model")

    assert {r.run_id for r in results} == {r1.run_id, r2.run_id}


def test_list_by_experiment_returns_only_matching_runs(storage):
    r1 = make_run(experiment="exp-a")
    r2 = make_run(experiment="exp-b")
    storage.save(r1)
    storage.save(r2)

    results = storage.list_by_experiment("exp-a")

    assert len(results) == 1
    assert results[0].run_id == r1.run_id


def test_list_all_returns_every_run(storage):
    runs = [make_run() for _ in range(3)]
    for r in runs:
        storage.save(r)

    results = storage.list_all()

    assert {r.run_id for r in results} == {r.run_id for r in runs}


def test_list_methods_return_empty_list_when_nothing_matches(storage):
    assert storage.list_by_function("nonexistent") == []
    assert storage.list_by_experiment("nonexistent") == []
    assert storage.list_all() == []


def test_results_are_ordered_newest_first(storage):
    r1 = make_run()
    storage.save(r1)
    time.sleep(0.01)  # ensure a distinct timestamp
    r2 = make_run()
    storage.save(r2)

    results = storage.list_all()

    assert results[0].run_id == r2.run_id  # newest first
    assert results[1].run_id == r1.run_id


def test_list_by_function_is_also_ordered_newest_first(storage):
    r1 = make_run(function="train_model")
    storage.save(r1)
    time.sleep(0.01)
    r2 = make_run(function="train_model")
    storage.save(r2)

    results = storage.list_by_function("train_model")

    assert results[0].run_id == r2.run_id
    assert results[1].run_id == r1.run_id