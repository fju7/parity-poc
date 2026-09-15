"""Closed state vocabularies and legal transition rules.

Execution, population coverage, and price knowledge are deliberately separate.
A completed call can still be partially evaluated or have unknown cost.
"""

from __future__ import annotations

from enum import Enum


class ExecutionState(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


class CoverageState(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    PARTIALLY_EVALUATED = "PARTIALLY_EVALUATED"
    EVALUATED = "EVALUATED"
    INVALIDATED = "INVALIDATED"


class PricingState(str, Enum):
    KNOWN = "KNOWN"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


LEGAL_EXECUTION_TRANSITIONS = {
    ExecutionState.PENDING: {ExecutionState.RUNNING, ExecutionState.CANCELLED},
    ExecutionState.RUNNING: {
        ExecutionState.COMPLETED,
        ExecutionState.ERROR,
        ExecutionState.CANCELLED,
    },
    ExecutionState.COMPLETED: set(),
    ExecutionState.ERROR: set(),
    ExecutionState.CANCELLED: set(),
}


def can_transition(before: ExecutionState, after: ExecutionState) -> bool:
    return after in LEGAL_EXECUTION_TRANSITIONS[before]


def require_transition(before: ExecutionState, after: ExecutionState) -> None:
    if not can_transition(before, after):
        raise ValueError(f"illegal execution transition: {before.value} -> {after.value}")
