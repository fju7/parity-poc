"""The allow-list: which provisions THIS letter may cite, and their fetched text.

Design doc §5. Built per request from the curated candidate table
(backend/data/verify/candidates.json): rows for the practice's state, the
payer type and the denial code, **only where reviewed_by is set**, each
resolved, fetched and bound (HEADING, APPLICABILITY) with the row's own
characterisation. A row that fails is not in the list, with the reason kept.

An empty list is the normal case today and the intended case for any state
without reviewed rows (§5b): the letter cites nothing. The list only grows.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from . import law
from .bind import bind_all
from .types import Context, Document, Identifier, Resolution

CANDIDATES = Path(__file__).resolve().parents[1] / "data" / "verify" / "candidates.json"


@dataclass
class Allowed:
    row: dict
    identifier: Identifier
    resolution: Resolution
    document: Document
    excerpt: str          # what the model is handed to quote from


@dataclass
class Rejected:
    row: dict
    reason: str


def _rows() -> list[dict]:
    return json.loads(CANDIDATES.read_text(encoding="utf-8"))["rows"]


def candidates_for(state: str | None, payer_type: str, denial_code: str, *, include_drafts: bool = False) -> list[dict]:
    out = []
    for r in _rows():
        if r["state"] != state or r["payer_type"] != payer_type or r["denial_code"] != denial_code:
            continue
        if not r.get("reviewed_by") and not include_drafts:
            continue
        out.append(r)
    return out


def build(state: str | None, payer_type: str, denial_code: str, *, include_drafts: bool = False,
          excerpt_chars: int = 900) -> tuple[list[Allowed], list[Rejected]]:
    """(allowed, rejected) for one letter. include_drafts is for tests and for a
    reviewer previewing a row; production never sets it."""
    ctx = Context(payer_type=payer_type, state=state)
    allowed, rejected = [], []
    for row in candidates_for(state, payer_type, denial_code, include_drafts=include_drafts):
        ident = law.identify(row["cite"])
        if ident is None:
            rejected.append(Rejected(row, "no resolvable identifier in the cite")); continue
        res = law.resolve(ident)
        doc = law.fetch(res)
        if doc is None:
            rejected.append(Rejected(row, f"resolve: {res.exists.value}; nothing fetched")); continue
        ok, bs = bind_all(row["may_assert"], res, doc, ctx, characterisation=row["characterisation"])
        if not ok:
            rejected.append(Rejected(row, "; ".join(f"{b.kind.value}: {b.reason}" for b in bs if not b.ok))); continue
        allowed.append(Allowed(row, ident, res, doc, doc.text[:excerpt_chars]))
    return allowed, rejected


def prompt_block(allowed: list[Allowed]) -> str:
    """The text handed to the model when the list is not empty. Absent otherwise."""
    if not allowed:
        return ""
    parts = ["PERMITTED CITATIONS. You may cite ONLY the provisions below, by the exact citation "
             "string given, and only for what the excerpt supports. Any other statute, rule, CFR, "
             "manual or section number is forbidden; the letter will be refused if one appears."]
    for a in allowed:
        parts.append(f"\n[{a.row['cite']}] — {a.resolution.heading}\n"
                     f"You may assert: {a.row['may_assert']}\n"
                     f"Excerpt: {a.excerpt}")
    return "\n".join(parts)
