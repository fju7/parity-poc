"""Re-level a frozen publication record through the current gate_claim, offline.

Rebuilds each source's Resolution and Document from the record and the
content-addressed held text (data/verify/docs), then runs gate_claim -- with
SUBJECT -- over every claim exactly as publish would, without a registry
call, a fetch, or a write. Used by the discovering test and by the operator
to see a re-level's numbers BEFORE a republish changes the page.
"""
from __future__ import annotations

import gzip
import json
import os
from collections import Counter
from pathlib import Path

from . import publish as P
from .types import Document, Exists, Identifier, Provenance, Resolution

BACKEND = Path(__file__).resolve().parent.parent


def rebuild_sources(rec: dict) -> dict:
    gated = {}
    for s in rec["sources"]:
        g = dict(s)
        idd = s.get("identifier") or {}
        prov = Provenance(idd["provenance"]) if idd.get("provenance") in Provenance.__members__ else Provenance.TYPED
        ident = Identifier(idd.get("system", "url"), idd.get("value", ""), idd.get("raw", ""), prov)
        r = s.get("resolution") or {}
        g["_res"] = Resolution(ident, Exists(r.get("exists", "UNCHECKED")), heading=r.get("heading"), canonical=r.get("canonical"),
                               registry=r.get("registry"), registry_id=r.get("registry_id"), checked_at=r.get("checked_at"),
                               extra={k: v for k, v in r.items() if k in ("published", "effective", "first_author", "container", "year", "status", "abstract")})
        d = s.get("document")
        path = BACKEND / d["path"] if d and d.get("path") else None
        if path and path.exists():
            g["_doc"] = Document(ident, d["sha256"], gzip.open(path, "rt", encoding="utf-8").read(), kind=d.get("kind", "full_text"),
                                 text_layer=d.get("text_layer", "DECLARED_SOUND"), path=str(path))
        else:
            g["_doc"] = None
        gated[s["source_id"]] = g
    return gated


def relevel(rec: dict, without_register: bool = False) -> list[dict]:
    """`without_register`: ignore the operator's withhold register, so that a
    binding can be tested against the claims the operator withheld by hand."""
    gated = rebuild_sources(rec)
    if without_register:
        saved = P.WITHHELD_CLAIMS; P.WITHHELD_CLAIMS = Path("/nonexistent/withheld_claims.json")   # FileNotFoundError -> None
    try:
        return _relevel(rec, gated)
    finally:
        if without_register:
            P.WITHHELD_CLAIMS = saved


def _stored_erratum(rec: dict):
    """The ERRATUM binding as the record stored it, so the offline re-level does
    not fetch an erratum live (the network answer varies run to run and would
    read as a level change that is nothing of the kind)."""
    stored = {}
    for c in rec["claims"]:
        for p in c["per_source"]:
            for b in p.get("bindings", []):
                if b["kind"] == "ERRATUM":
                    stored[(c["claim_id"], p["source_id"])] = b
    return stored


def _relevel(rec: dict, gated: dict) -> list[dict]:
    stored = _stored_erratum(rec)
    real = P.erratum_check
    current = {"claim": None}

    def offline_erratum(figs, src):
        b = stored.get((current["claim"], src["source_id"]))
        return dict(b) if b else real(figs, src)
    P.erratum_check = offline_erratum
    try:
        return _relevel_inner(rec, gated, current)
    finally:
        P.erratum_check = real


def _relevel_inner(rec: dict, gated: dict, current: dict) -> list[dict]:
    claims = [{"id": c["claim_id"], "claim_text": c["claim_text"], "category": c.get("category")} for c in rec["claims"]]
    links = {c["claim_id"]: [{"claim_id": c["claim_id"], "source_id": p["source_id"], "source_context": None} for p in c["per_source"]] for c in rec["claims"]}
    ctx = P.subject_context(claims, gated, rec["topic"]["title"])
    out = []
    for c in claims:
        current["claim"] = c["id"]
        out.append(P.gate_claim(c, links[c["id"]], gated, ctx))
    work_of = {sid: k for k, w in P.works_index(list(gated.values())).items() for sid in w["entries"]}
    for c in out:
        c["works"] = sorted({work_of[sid] for sid in c.get("supported_by", []) if sid in work_of}); c["work_count"] = len(c["works"])
    return out


def compare(rec: dict, new: list[dict]) -> dict:
    old = {c["claim_id"]: c["support"] for c in rec["claims"]}
    moves = Counter((old[c["claim_id"]], c["support"]) for c in new if old[c["claim_id"]] != c["support"])
    return {"old": dict(Counter(old.values())), "new": dict(Counter(c["support"] for c in new)),
            "moves": {f"{a} -> {b}": n for (a, b), n in moves.items()},
            "shown_old": sum(1 for v in old.values() if v in P.SHOWN or v == "IDENTITY_ONLY"),   # under the old ladder IDENTITY_ONLY was shown
            "shown_new": sum(1 for c in new if c["support"] in P.SHOWN)}


if __name__ == "__main__":
    import sys
    slug = sys.argv[1] if len(sys.argv) > 1 else "mmr-vaccine-autism"
    rec = json.load(open(BACKEND / "data" / "verify" / "published" / slug / "latest.json"))
    new = relevel(rec)
    print(json.dumps(compare(rec, new), indent=1))
    if "--list" in sys.argv:
        old = {c["claim_id"]: c for c in rec["claims"]}
        for c in new:
            if old[c["claim_id"]]["support"] != c["support"]:
                why = "; ".join(f"{p['source_id'][:8]}: {b.get('reason') or b.get('evidence')}" for p in c["per_source"] for b in p.get("bindings", []) if b["kind"] == "SUBJECT")
                print(f"  {c['claim_id'][:8]} {old[c['claim_id']]['support']} -> {c['support']} | {c['claim_text'][:80]}\n        {why[:200]}")
