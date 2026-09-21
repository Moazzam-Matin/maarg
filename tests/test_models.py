"""Tests for the Run data model."""

import dataclasses

import pytest

from maarg.models import Run


def make_run(**overrides):
    """Helper: build a Run with sensible defaults, override only what you need."""
    defaults = {
        "function" : "train_model",
        "experiment" : "my-experiment",
        "inputs" : {"lr": 0.01, "epochs": 5},
    }
    defaults.update(overrides)
    return Run(**defaults)


def test_run_id_is_auto_generated_and_unique():
    r1 = make_run()
    r2 = make_run()
    assert r1.run_id != r2.run_id
    assert len(r1.run_id) > 0


def test_timestamp_is_auto_generated():
    r = make_run()
    assert r.timestamp != ""
    # Should be a valid ISO 8601 string — this will raise if it isn't
    from datetime import datetime
    datetime.fromisoformat(r.timestamp)


def test_defaults_are_not_shared_between_instances():
    """Guards against the classic mutable-default-argument bug."""
    r1 = make_run()
    r2 = make_run()
    r1.artifacts.append({"name": "x", "path": "x.png", "type": "chart"})
    assert r2.artifacts == []  # r2 must NOT see r1's mutation


def test_experiment_defaults_can_differ_from_function():
    r = make_run(function="train_model", experiment="custom-label")
    assert r.function == "train_model"
    assert r.experiment == "custom-label"


def test_metrics_artifacts_other_store_correctly():
    r = make_run(
        metrics={"accuracy": 0.95},
        artifacts=[{"name": "curve", "path": "curve.png", "type": "chart"}],
        other={"status": "converged"},
    )
    assert r.metrics == {"accuracy": 0.95}
    assert r.artifacts == [{"name": "curve", "path": "curve.png", "type": "chart"}]
    assert r.other == {"status": "converged"}


def test_run_is_immutable():
    r = make_run()
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.metrics = {}


def test_to_dict_round_trips_all_fields():
    r = make_run(metrics={"accuracy": 0.95})
    d = r.to_dict()

    assert d["function"] == "train_model"
    assert d["experiment"] == "my-experiment"
    assert d["inputs"] == {"lr": 0.01, "epochs": 5}
    assert d["metrics"] == {"accuracy": 0.95}
    assert d["artifacts"] == []
    assert d["other"] == {}
    assert d["run_id"] == r.run_id
    assert d["timestamp"] == r.timestamp
    assert isinstance(d, dict)