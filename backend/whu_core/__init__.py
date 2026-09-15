"""The minimal, side-effect-free foundation for the rebuilt WHU core.

Nothing in this package publishes, deploys, sends email, or calls a model.
Those effects must enter through adapters that persist an ExecutionReceipt.
"""

from .canonical import canonical_json, content_hash
from .receipts import ExecutionAttempt, ExecutionReceipt, ReceiptError
from .states import CoverageState, ExecutionState, PricingState

__all__ = [
    "CoverageState",
    "ExecutionAttempt",
    "ExecutionReceipt",
    "ExecutionState",
    "PricingState",
    "ReceiptError",
    "canonical_json",
    "content_hash",
]
