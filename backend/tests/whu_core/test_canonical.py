from datetime import datetime, timezone

import pytest

from whu_core.canonical import CanonicalizationError, canonical_json, content_hash


def test_dict_order_does_not_change_identity():
    assert content_hash({"a": 1, "b": [2, 3]}) == content_hash({"b": [2, 3], "a": 1})


def test_list_order_does_change_identity():
    assert content_hash([1, 2]) != content_hash([2, 1])


def test_datetime_is_normalized_to_utc():
    value = datetime(2026, 9, 15, 12, 30, tzinfo=timezone.utc)
    assert canonical_json({"at": value}) == b'{"at":"2026-09-15T12:30:00Z"}'


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1: "not a string key"}])
def test_lossy_or_non_json_values_are_refused(value):
    with pytest.raises(CanonicalizationError):
        canonical_json(value)


def test_naive_datetime_is_refused():
    with pytest.raises(CanonicalizationError, match="naive"):
        canonical_json(datetime(2026, 9, 15, 12, 30))
