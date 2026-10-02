"""Tests for input-filtering logic (is_loggable / filter_inputs)."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from maarg._capture import filter_inputs, is_loggable

matplotlib.use("Agg")  # non-interactive backend, no display needed for tests

from maarg._capture import split_output

# ── Scalars ──────────────────────────────────────────────────────────

def test_small_scalars_are_loggable():
    assert is_loggable(0.01)
    assert is_loggable(32)
    assert is_loggable(True)
    assert is_loggable(None)
    assert is_loggable("relu")


def test_oversized_string_is_not_loggable():
    huge_string = "x" * 5000  # well over the 1000-byte default
    assert not is_loggable(huge_string)


def test_custom_scalar_byte_limit_is_respected():
    value = "x" * 50
    assert not is_loggable(value, max_scalar_bytes=10)
    assert is_loggable(value, max_scalar_bytes=1000)


# ── Collections ──────────────────────────────────────────────────────

def test_small_collection_of_scalars_is_loggable():
    assert is_loggable([128, 64, 32])
    assert is_loggable({"beta1": 0.9, "beta2": 0.999})
    assert is_loggable((1, 2, 3))


def test_oversized_collection_is_not_loggable():
    big_list = list(range(1000))  # well over the 20-item default
    assert not is_loggable(big_list)


def test_custom_collection_length_limit_is_respected():
    value = list(range(30))
    assert not is_loggable(value, max_collection_length=20)
    assert is_loggable(value, max_collection_length=50)


def test_nested_collection_checks_every_item_recursively():
    # Small collection, but contains one item that's individually too big
    value = ["ok", "x" * 5000]
    assert not is_loggable(value)


def test_dict_values_checked_but_keys_ignored():
    # Keys are never size-checked, only values
    value = {"short_key": 0.5}
    assert is_loggable(value)


# ── Non-loggable types ───────────────────────────────────────────────

def test_arbitrary_object_is_not_loggable():
    class Dataset:
        pass

    assert not is_loggable(Dataset())


def test_dict_containing_a_dataset_object_is_not_loggable():
    class Dataset:
        pass

    value = {"lr": 0.01, "dataset": Dataset()}
    assert not is_loggable(value)


# ── filter_inputs ────────────────────────────────────────────────────

def test_filter_inputs_keeps_only_loggable_entries():
    class Dataset:
        pass

    args = {
        "learning_rate": 0.01,
        "epochs": 10,
        "dataset": Dataset(),
        "huge_blob": "x" * 5000,
    }
    result = filter_inputs(args)

    assert result == {"learning_rate": 0.01, "epochs": 10}


def test_filter_inputs_respects_custom_thresholds():
    args = {"layers": list(range(30))}
    assert filter_inputs(args) == {}
    assert filter_inputs(args, max_collection_length=50) == args


def test_filter_inputs_on_empty_dict_returns_empty_dict():
    assert filter_inputs({}) == {}


# ── split_output ─────────────────────────────────────────────────────


def test_numeric_values_go_to_metrics():
    metrics, artifacts, other = split_output({"accuracy": 0.95, "loss": 0.08}, artifacts_dir="unused")
    assert metrics == {"accuracy": 0.95, "loss": 0.08}
    assert artifacts == []
    assert other == {}


def test_bool_goes_to_other_not_metrics():
    metrics, _artifacts, other = split_output({"converged": True}, artifacts_dir="unused")
    assert metrics == {}
    assert other == {"converged": True}


def test_string_goes_to_other():
    metrics, _artifacts, other = split_output({"status": "converged"}, artifacts_dir="unused")
    assert other == {"status": "converged"}
    assert metrics == {}


def test_none_goes_to_other():
    _metrics, _artifacts, other = split_output({"checkpoint": None}, artifacts_dir="unused")
    assert other == {"checkpoint": None}


def test_mixed_dict_splits_correctly_by_key():
    output = {
        "accuracy": 0.95,
        "converged": True,
        "status": "early stopping",
    }
    metrics, artifacts, other = split_output(output, artifacts_dir="unused")

    assert metrics == {"accuracy": 0.95}
    assert other == {"converged": True, "status": "early stopping"}
    assert artifacts == []


def test_non_dict_scalar_wraps_in_result_key():
    metrics, _artifacts, other = split_output(0.87, artifacts_dir="unused")
    assert metrics == {"result": 0.87}
    assert other == {}


def test_non_dict_string_wraps_in_result_key():
    metrics, _artifacts, other = split_output("converged", artifacts_dir="unused")
    assert other == {"result": "converged"}
    assert metrics == {}


def test_unrecognized_object_falls_back_to_truncated_repr():
    class CustomResult:
        def __repr__(self):
            return "x" * 500  # deliberately longer than OTHER_REPR_MAX_LEN

    metrics, artifacts, other = split_output(CustomResult(), artifacts_dir="unused")
    assert metrics == {}
    assert artifacts == []
    assert len(other["result"]) == 200  # truncated to OTHER_REPR_MAX_LEN


def test_matplotlib_figure_is_saved_as_artifact(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])

    metrics, artifacts, other = split_output({"chart": fig}, artifacts_dir=tmp_path)
    plt.close(fig)

    assert metrics == {}
    assert other == {}
    assert len(artifacts) == 1
    assert artifacts[0]["name"] == "chart"
    assert artifacts[0]["type"] == "chart"

    saved_path = Path(artifacts[0]["path"])
    assert saved_path.exists()
    assert saved_path.suffix == ".png"


def test_artifact_name_cannot_escape_artifacts_directory(tmp_path):
    fig, _ax = plt.subplots()

    _metrics, artifacts, _other = split_output(
        {"../../outside": fig},
        artifacts_dir=tmp_path,
    )
    plt.close(fig)

    saved_path = Path(artifacts[0]["path"])

    assert saved_path.exists()
    assert saved_path.parent == tmp_path
    assert artifacts[0]["name"] == "../../outside"


def test_artifacts_dir_is_created_if_missing(tmp_path):
    fig, _ax = plt.subplots()
    nested_dir = tmp_path / "does" / "not" / "exist" / "yet"

    _metrics, artifacts, _other = split_output(fig, artifacts_dir=nested_dir)
    plt.close(fig)

    assert nested_dir.exists()
    assert Path(artifacts[0]["path"]).exists()


def test_empty_dict_output_returns_all_empty():
    metrics, artifacts, other = split_output({}, artifacts_dir="unused")
    assert metrics == {} and artifacts == [] and other == {}