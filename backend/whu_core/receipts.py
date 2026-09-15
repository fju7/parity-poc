"""Immutable execution receipts for epistemically consequential operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid4

from .canonical import content_hash
from .states import CoverageState, ExecutionState, PricingState


class ReceiptError(ValueError):
    """A receipt violates an invariant and cannot acquire authority."""


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None:
        raise ReceiptError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _immutable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _immutable(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_immutable(item) for item in value)
    return value


def _frozen(mapping: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return _immutable(dict(mapping or {}))


@dataclass(frozen=True)
class ExecutionAttempt:
    attempt_id: UUID
    ordinal: int
    state: ExecutionState
    started_at: datetime
    finished_at: datetime | None = None
    provider_request_id: str | None = None
    response_hash: str | None = None
    error_code: str | None = None
    error_detail: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "started_at", _utc(self.started_at, "started_at"))
        if self.ordinal < 1:
            raise ReceiptError("attempt ordinal must be positive")
        if self.finished_at is not None:
            object.__setattr__(self, "finished_at", _utc(self.finished_at, "finished_at"))
            if self.finished_at < self.started_at:
                raise ReceiptError("attempt cannot finish before it starts")
        terminal = self.state in {
            ExecutionState.COMPLETED,
            ExecutionState.ERROR,
            ExecutionState.CANCELLED,
        }
        if terminal != (self.finished_at is not None):
            raise ReceiptError("terminal attempts require finished_at; active attempts forbid it")
        if self.state is ExecutionState.COMPLETED and not self.response_hash:
            raise ReceiptError("completed attempts require a response hash")
        if self.state is ExecutionState.ERROR and not self.error_code:
            raise ReceiptError("error attempts require an error code")
        if self.state is not ExecutionState.ERROR and (self.error_code or self.error_detail):
            raise ReceiptError("only error attempts may carry error details")


@dataclass(frozen=True)
class ExecutionReceipt:
    execution_id: UUID
    operation: str
    operation_version: str
    caller: str
    subject_versions: tuple[str, ...]
    request_payload_submitted_to_sdk: Mapping[str, Any]
    code_identity: Mapping[str, Any]
    config_identity: Mapping[str, Any]
    created_at: datetime
    coverage_state: CoverageState
    pricing_state: PricingState
    attempts: tuple[ExecutionAttempt, ...] = ()
    requested_provider: str | None = None
    requested_model: str | None = None
    resolved_model: str | None = None
    prompt_hashes: tuple[str, ...] = ()
    policy_hashes: tuple[str, ...] = ()
    fixture_hashes: tuple[str, ...] = ()
    input_population_id: str | None = None
    downstream_object_versions: tuple[str, ...] = ()
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: Decimal | None = None
    idempotency_key: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", _utc(self.created_at, "created_at"))
        object.__setattr__(self, "request_payload_submitted_to_sdk", _frozen(self.request_payload_submitted_to_sdk))
        object.__setattr__(self, "code_identity", _frozen(self.code_identity))
        object.__setattr__(self, "config_identity", _frozen(self.config_identity))
        object.__setattr__(self, "metadata", _frozen(self.metadata))
        if not self.operation.strip() or not self.operation_version.strip() or not self.caller.strip():
            raise ReceiptError("operation, operation_version, and caller are required")
        if not self.subject_versions:
            raise ReceiptError("at least one exact subject version is required")
        if not self.code_identity:
            raise ReceiptError("code identity is required")
        ordinals = [attempt.ordinal for attempt in self.attempts]
        if ordinals != list(range(1, len(ordinals) + 1)):
            raise ReceiptError("attempt ordinals must be contiguous and ordered from one")
        if len({attempt.attempt_id for attempt in self.attempts}) != len(self.attempts):
            raise ReceiptError("attempt IDs must be unique")
        if self.pricing_state is PricingState.UNKNOWN and self.cost_usd is not None:
            raise ReceiptError("unknown price must not carry a numeric cost")
        if self.pricing_state in {PricingState.KNOWN, PricingState.ESTIMATED} and self.cost_usd is None:
            raise ReceiptError("known or estimated pricing requires a cost")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise ReceiptError("cost cannot be negative")
        for name, count in (("input_tokens", self.input_tokens), ("output_tokens", self.output_tokens)):
            if count is not None and count < 0:
                raise ReceiptError(f"{name} cannot be negative")
        expected_key = self.derived_idempotency_key
        if self.idempotency_key is not None and self.idempotency_key != expected_key:
            raise ReceiptError("idempotency key does not match the consequential input identity")

    @classmethod
    def new(cls, **values: Any) -> "ExecutionReceipt":
        values.setdefault("execution_id", uuid4())
        values.setdefault("created_at", datetime.now(timezone.utc))
        return cls(**values)

    @property
    def request_payload_hash(self) -> str:
        return content_hash(self.request_payload_submitted_to_sdk)

    @property
    def derived_idempotency_key(self) -> str:
        return content_hash({
            "operation": self.operation,
            "operation_version": self.operation_version,
            "subjects": self.subject_versions,
            "payload": self.request_payload_hash,
            "code": self.code_identity,
            "config": self.config_identity,
            "prompts": self.prompt_hashes,
            "policies": self.policy_hashes,
            "fixtures": self.fixture_hashes,
        })

    @property
    def execution_state(self) -> ExecutionState:
        if not self.attempts:
            return ExecutionState.PENDING
        return self.attempts[-1].state

    @property
    def authority_eligible(self) -> bool:
        """Mechanical eligibility only; never a semantic truth judgment."""
        return (
            self.execution_state is ExecutionState.COMPLETED
            and self.coverage_state is CoverageState.EVALUATED
            and self.pricing_state is not PricingState.UNKNOWN
        )

    def authority_blockers(self) -> tuple[str, ...]:
        blockers = []
        if self.execution_state is not ExecutionState.COMPLETED:
            blockers.append(f"execution:{self.execution_state.value}")
        if self.coverage_state is not CoverageState.EVALUATED:
            blockers.append(f"coverage:{self.coverage_state.value}")
        if self.pricing_state is PricingState.UNKNOWN:
            blockers.append("pricing:UNKNOWN")
        return tuple(blockers)
