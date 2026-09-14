"""Tests for input-filtering logic (is_loggable / filter_inputs)."""

from maarg.capture import is_loggable, filter_inputs


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