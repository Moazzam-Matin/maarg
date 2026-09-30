"""Tests for the query/comparison layer (filter_runs, top_n, best_run, compare)."""

from maarg._models import Run
from maarg._query import best_run, compare, filter_runs, top_n


def make_run(**overrides):
    defaults = {
        "function" : "train_model",
        "experiment" : "my-experiment",
        "inputs" : {"lr": 0.01},
        "metrics" : {"accuracy": 0.9},
    }
    defaults.update(overrides)
    return Run(**defaults)


def make_failed_run(**overrides):
    """A run that failed — has the 'status': 'failed' marker, no metrics."""
    defaults = {
        "function" : "train_model",
        "experiment" : "my-experiment",
        "inputs" : {"lr": 0.01},
        "metrics" : {},
        "other" : {"status": "failed", "error_type": "ValueError", "error_message": "boom"},
    }
    defaults.update(overrides)
    return Run(**defaults)


# ── filter_runs ──────────────────────────────────────────────────────

def test_filter_runs_default_keeps_successful_and_drops_failed():
    """
    This is the exact bug we caught: a successful run has NO 'status' key
    at all (absence means success). filter_runs(runs) with defaults must
    keep successful runs, not silently drop everything.
    """
    good = make_run()
    bad = make_failed_run()

    result = filter_runs([good, bad])

    assert good in result
    assert bad not in result
    assert len(result) == 1


def test_filter_runs_only_successful_false_keeps_everything():
    good = make_run()
    bad = make_failed_run()

    result = filter_runs([good, bad], only_successful=False)

    assert len(result) == 2


def test_filter_runs_by_experiment():
    r1 = make_run(experiment="exp-a")
    r2 = make_run(experiment="exp-b")

    result = filter_runs([r1, r2], experiment="exp-a")

    assert result == [r1]


def test_filter_runs_by_exact_input_match():
    r1 = make_run(inputs={"lr": 0.01, "epochs": 5})
    r2 = make_run(inputs={"lr": 0.02, "epochs": 5})

    result = filter_runs([r1, r2], lr=0.01)

    assert result == [r1]


def test_filter_runs_with_no_matches_returns_empty_list():
    r1 = make_run(experiment="exp-a")
    assert filter_runs([r1], experiment="nonexistent") == []


# ── top_n / best_run ─────────────────────────────────────────────────

def test_top_n_ranks_by_metric_descending_when_higher_is_better():
    r1 = make_run(metrics={"accuracy": 0.7})
    r2 = make_run(metrics={"accuracy": 0.95})
    r3 = make_run(metrics={"accuracy": 0.8})

    result = top_n([r1, r2, r3], metric="accuracy", n=2)

    assert result == [r2, r3]  # highest first, top 2 only


def test_top_n_ranks_ascending_when_higher_is_better_false():
    r1 = make_run(metrics={"loss": 0.5})
    r2 = make_run(metrics={"loss": 0.1})
    r3 = make_run(metrics={"loss": 0.3})

    result = top_n([r1, r2, r3], metric="loss", higher_is_better=False, n=2)

    assert result == [r2, r3]  # lowest first, top 2 only


def test_top_n_silently_excludes_runs_missing_the_metric():
    with_metric = make_run(metrics={"accuracy": 0.9})
    without_metric = make_run(metrics={"loss": 0.1})  # no "accuracy" key at all

    result = top_n([with_metric, without_metric], metric="accuracy")

    assert result == [with_metric]


def test_top_n_excludes_failed_runs_by_default():
    good = make_run(metrics={"accuracy": 0.9})
    bad = make_failed_run(metrics={"accuracy": 0.99})  # even if it somehow had one

    result = top_n([good, bad], metric="accuracy")

    assert result == [good]


def test_top_n_on_empty_list_returns_empty_list():
    assert top_n([], metric="accuracy") == []


def test_best_run_returns_the_single_top_result():
    r1 = make_run(metrics={"accuracy": 0.7})
    r2 = make_run(metrics={"accuracy": 0.95})

    assert best_run([r1, r2], metric="accuracy") == r2


def test_best_run_returns_none_when_no_runs_qualify():
    r1 = make_run(metrics={"loss": 0.1})  # no "accuracy" metric
    assert best_run([r1], metric="accuracy") is None


# ── compare ──────────────────────────────────────────────────────────

def test_compare_on_empty_list_returns_empty_structure():
    result = compare([])
    assert result == {"run_ids": [], "inputs": {}, "metrics": {}, "status": []}


def test_compare_aligns_inputs_and_metrics_across_runs():
    r1 = make_run(inputs={"lr": 0.01}, metrics={"accuracy": 0.9})
    r2 = make_run(inputs={"lr": 0.02}, metrics={"accuracy": 0.95})

    result = compare([r1, r2])

    assert result["run_ids"] == [r1.run_id, r2.run_id]
    assert result["inputs"]["lr"] == [0.01, 0.02]
    assert result["metrics"]["accuracy"] == [0.9, 0.95]


def test_compare_handles_runs_with_different_keys_using_none_for_missing():
    r1 = make_run(inputs={"lr": 0.01})
    r2 = make_run(inputs={"epochs": 5})  # different key entirely

    result = compare([r1, r2])

    assert result["inputs"]["lr"] == [0.01, None]
    assert result["inputs"]["epochs"] == [None, 5]


def test_compare_correctly_labels_success_and_failure_status():
    good = make_run()
    bad = make_failed_run()

    result = compare([good, bad])

    assert result["status"] == ["success", "failed"]