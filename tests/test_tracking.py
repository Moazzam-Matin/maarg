"""Tests for the @track decorator module."""

import pytest

from maarg._exceptions import MaargTrackingError, MaargTrackingWarning
from maarg._tracking import track
from maarg.storage._sqlite import SQLiteStorage


@pytest.fixture
def storage(tmp_path):
    return SQLiteStorage(db_path=tmp_path / "test_tracking.db")


class FailingStorage:
    def save(self, run):
        raise RuntimeError("storage is unavailable")


def test_track_bare_decorator_records_run(storage):
    @track(storage=storage)
    def compute_loss(learning_rate=0.01):
        return {"loss": 0.05}

    result = compute_loss(learning_rate=0.02)

    assert result == {"loss": 0.05}

    runs = storage.list_by_function("compute_loss")
    assert len(runs) == 1
    run = runs[0]
    assert run.function == "compute_loss"
    assert run.experiment == "compute_loss"  # defaults to function name
    assert run.inputs == {"learning_rate": 0.02}
    assert run.metrics == {"loss": 0.05}
    assert run.duration_sec >= 0.0


def test_tracking_save_failure_does_not_replace_success_result():
    @track(storage=FailingStorage())
    def compute():
        return {"accuracy": 0.95}

    with pytest.warns(
    MaargTrackingWarning,
    match="Failed to save tracking data",
):
        result = compute()

    assert result == {"accuracy": 0.95}


def test_tracking_save_failure_raises_in_strict_mode():
    @track(storage=FailingStorage(), strict=True)
    def compute():
        return {"accuracy": 0.95}

    with pytest.raises(MaargTrackingError) as exc_info:
        compute()

    assert "Failed to save tracking data" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == "storage is unavailable"


def test_tracking_save_failure_preserves_original_exception():
    @track(storage=FailingStorage(), strict=True)
    def compute():
        raise ValueError("original function error")

    with pytest.warns(
        MaargTrackingWarning,
        match="Failed to save tracking data",
    ), pytest.raises(ValueError, match="original function error"):
        compute()


def test_track_strict_defaults_to_false():
    @track(storage=FailingStorage())
    def compute():
        return 42

    with pytest.warns(
        MaargTrackingWarning,
        match="Failed to save tracking data",
    ):
        result = compute()

    assert result == 42


def test_track_with_custom_experiment_and_limits(storage):
    class LargeDataset:
        pass

    @track(
        experiment="exp-custom",
        storage=storage,
        max_scalar_bytes=50,
    )
    def train(epochs, dataset, desc):
        return {"accuracy": 0.98, "status": "done"}

    train(10, LargeDataset(), desc="a-very-long-description-string-exceeding-limit")

    runs = storage.list_by_experiment("exp-custom")
    assert len(runs) == 1
    run = runs[0]
    assert run.inputs == {"epochs": 10}
    assert run.metrics == {"accuracy": 0.98}
    assert run.other == {"status": "done"}


def test_track_captures_exception_and_reraises(storage):
    @track(storage=storage, experiment="crash-test")
    def faulty_function(x=5):
        raise ValueError("Something went wrong")

    with pytest.raises(ValueError, match="Something went wrong"):
        faulty_function(x=10)

    runs = storage.list_by_experiment("crash-test")
    assert len(runs) == 1
    run = runs[0]
    assert run.inputs == {"x": 10}
    assert run.metrics == {}
    assert run.other == {
        "status": "failed",
        "error_type": "ValueError",
        "error_message": "Something went wrong",
    }


def test_track_preserves_function_metadata():
    @track
    def sample_function():
        """Sample docstring."""
        return 42

    assert sample_function.__name__ == "sample_function"
    assert sample_function.__doc__ == "Sample docstring."


def test_track_experiment_defaults_to_function_name_not_shared_across_functions(storage):
    """Two different functions, both bare @track, should NOT collide under
    a shared 'default' experiment label — each gets its own function name."""

    @track(storage=storage)
    def func_a():
        return 1

    @track(storage=storage)
    def func_b():
        return 2

    func_a()
    func_b()

    assert storage.list_by_experiment("func_a")[0].function == "func_a"
    assert storage.list_by_experiment("func_b")[0].function == "func_b"

def test_track_save_failure_strict_false_preserves_original_exception():
    @track(storage=FailingStorage(), strict=False)
    def compute():
        raise ValueError("original error")

    with pytest.warns(MaargTrackingWarning, match="Failed to save tracking data"), \
         pytest.raises(ValueError, match="original error"):
        compute()

def test_track_returns_non_dict_scalar(storage):
    @track(storage=storage)
    def compute_scalar():
        return 42

    result = compute_scalar()
    assert result == 42
    runs = storage.list_by_function("compute_scalar")
    assert runs[0].metrics == {"result": 42}