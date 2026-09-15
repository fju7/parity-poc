"""Canonical serialization used for identities, idempotency, and receipts."""

from __future__ import annotations

import dataclasses
import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class CanonicalizationError(TypeError):
    """Raised when a value cannot be represented without losing meaning."""


def _normalize(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return _normalize(dataclasses.asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise CanonicalizationError("naive datetimes have no stable identity")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise CanonicalizationError("canonical object keys must be strings")
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise CanonicalizationError("NaN and infinity have no canonical JSON form")
        return value
    raise CanonicalizationError(f"unsupported canonical value: {type(value).__name__}")


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON without silently coercing values."""
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def content_hash(value: Any) -> str:
    """SHA-256 identity of a canonical value."""
    return hashlib.sha256(canonical_json(value)).hexdigest()
