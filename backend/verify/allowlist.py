"""The allow-list -- CLOSED 2026-09-17 (APPEALS-3, Fred's ruling): appeal letters cite
EVIDENCE, never LAW. No letter path calls this module any more; the prompt-injection
half (prompt_block) is gone, so no statutory text can be handed to the model from here.

What remains is the read side over the curated candidate table
(backend/data/verify/candidates.json) -- twelve Ohio rows drafted 2026-09-14, all
`reviewed_by: null`, kept as a historical record with the review that was never
commissioned (docs/legal-review/README.md). build() still resolves/fetches/binds a row so
the record can be re-checked; nothing downstream consumes the result. Evidence citations
(PMID/DOI/NCT, the payer's own documents, the patient's record) never flowed through
here; they are verified in verify/evidence.py.

Design doc §5 described the original intent: rows for the practice's state, the payer
type and the denial code, only where reviewed_by is set, each resolved, fetched and
bound (HEADING, APPLICABILITY) with the row's own characterisation.
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
