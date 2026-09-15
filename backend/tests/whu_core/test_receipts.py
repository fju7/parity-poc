from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from whu_core.receipts import ExecutionAttempt, ExecutionReceipt, ReceiptError
from whu_core.states import CoverageState, ExecutionState, PricingState

NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)


def completed_attempt(**overrides):
    values = {
        "attempt_id": uuid4(),
        "ordinal": 1,
        "state": ExecutionState.COMPLETED,
        "started_at": NOW,
        "finished_at": NOW + timedelta(seconds=2),
        "response_hash": "a" * 64,
    }
    values.update(overrides)
    return ExecutionAttempt(**values)


def receipt(**overrides):
    values = {
        "execution_id": uuid4(),
        "operation": "model.claim_support",
        "operation_version": "1",
        "caller": "test",
        "subject_versions": ("prop:P1:v3:sha256:abc",),
        "request_payload_submitted_to_sdk": {"model": "example", "messages": [{"role": "user", "content": "claim"}]},
        "code_identity": {"repository": "fju7/parity-poc", "tree": "abc"},
        "config_identity": {"temperature": 0},
        "created_at": NOW,
        "coverage_state": CoverageState.EVALUATED,
        "pricing_state": PricingState.KNOWN,
        "cost_usd": Decimal("0.42"),
        "attempts": (completed_attempt(),),
    }
    values.update(overrides)
    return ExecutionReceipt(**values)


def test_complete_evaluated_priced_receipt_is_mechanically_eligible():
    got = receipt()
    assert got.authority_eligible is True
    assert got.authority_blockers() == ()


@pytest.mark.parametrize("state", [
    CoverageState.NOT_EVALUATED,
    CoverageState.PARTIALLY_EVALUATED,
    CoverageState.INVALIDATED,
])
def test_non_evaluated_coverage_never_becomes_eligible(state):
    got = receipt(coverage_state=state)
    assert got.authority_eligible is False
    assert got.authority_blockers() == (f"coverage:{state.value}",)


def test_error_attempt_never_becomes_eligible():
    attempt = ExecutionAttempt(
        attempt_id=uuid4(), ordinal=1, state=ExecutionState.ERROR,
        started_at=NOW, finished_at=NOW, error_code="provider_timeout",
    )
    got = receipt(attempts=(attempt,))
    assert got.authority_eligible is False
    assert got.authority_blockers() == ("execution:ERROR",)


def test_unknown_cost_is_not_zero_and_blocks_authority():
    got = receipt(pricing_state=PricingState.UNKNOWN, cost_usd=None)
    assert got.cost_usd is None
    assert got.authority_eligible is False
    assert got.authority_blockers() == ("pricing:UNKNOWN",)


def test_unknown_price_rejects_numeric_cost():
    with pytest.raises(ReceiptError, match="unknown price"):
        receipt(pricing_state=PricingState.UNKNOWN, cost_usd=Decimal("0"))


def test_completed_attempt_requires_response_hash():
    with pytest.raises(ReceiptError, match="response hash"):
        completed_attempt(response_hash=None)


def test_attempt_ordinals_cannot_hide_a_dropped_attempt():
    with pytest.raises(ReceiptError, match="contiguous"):
        receipt(attempts=(completed_attempt(ordinal=2),))


def test_idempotency_key_is_bound_to_consequential_inputs():
    original = receipt()
    with pytest.raises(ReceiptError, match="idempotency"):
        receipt(idempotency_key=original.derived_idempotency_key,
                request_payload_submitted_to_sdk={"different": True})


def test_payload_mapping_is_defensively_copied():
    payload = {"messages": []}
    got = receipt(request_payload_submitted_to_sdk=payload)
    before = got.request_payload_hash
    payload["messages"].append("late mutation")
    assert got.request_payload_hash == before
    with pytest.raises(AttributeError):
        got.request_payload_submitted_to_sdk["messages"].append("direct mutation")
