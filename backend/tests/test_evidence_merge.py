"""PH: diagnosis-enhanced second PubMed search merged with the broad search.

Deterministic, offline: no live network and no DB. We stub the PubMed fetch to
return a "broad" list for the broad query and a "diagnosis" list for the
diagnosis-enhanced query (dispatched by whether the diagnosis text is in the
query), stub CMS/FDA to empty, and set the cache client to None so _run_channel
always takes the fetch path with no DB. Then we assert the enhance-never-limit,
de-dup, overlap-ranking, and merged-cap behavior of retrieve_evidence.
"""

import os
import sys

import pytest

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from utils import evidence_retrieval as er  # noqa: E402


def _it(uid):
    return {"source": "pubmed", "source_uid": uid, "title": f"t{uid}",
            "verified": True, "retracted": False}


def _install(monkeypatch, broad, diag):
    """Stub retrieval so pubmed returns `broad` for the broad query and `diag` for
    the diagnosis-enhanced query; CMS/FDA empty; no cache client."""
    monkeypatch.setattr(er, "_get_client", lambda: None)
    monkeypatch.setattr(er, "_fetch_cms", lambda *a, **k: [])
    monkeypatch.setattr(er, "_fetch_fda", lambda *a, **k: [])

    def _fake_fetch_pubmed(query, denial_analysis):
        dg = (denial_analysis.get("patient_diagnosis") or "").strip().lower()
        if dg and dg in (query or "").lower():
            return [dict(x) for x in diag]     # diagnosis-enhanced query
        return [dict(x) for x in broad]        # broad query

    monkeypatch.setattr(er, "_fetch_pubmed", _fake_fetch_pubmed)


def _da(diagnosis=None):
    d = {"procedure_terms": ["Signatera"], "cpt_codes": ["0340U"], "icd_codes": []}
    if diagnosis is not None:
        d["patient_diagnosis"] = diagnosis
    return d


def _uids(pack):
    return [it["source_uid"] for it in pack["pubmed"]]


# 5.1 — ENHANCE: diagnosis adds a NEW condition-specific PMID; broad items kept.
def test_enhance_adds_new_item_keeps_broad(monkeypatch):
    _install(monkeypatch, broad=[_it("A"), _it("B")], diag=[_it("C")])
    pack = er.retrieve_evidence(_da("colon cancer"))
    uids = _uids(pack)
    assert "C" in uids                       # new diagnosis-specific item present
    assert "A" in uids and "B" in uids       # broad items NOT lost
    assert len(uids) == 3


# 5.2 — NEVER-LIMIT (no diagnosis): pubmed equals today's broad result exactly.
def test_no_diagnosis_equals_broad(monkeypatch):
    _install(monkeypatch, broad=[_it("A"), _it("B")], diag=[_it("C")])
    pack = er.retrieve_evidence(_da(None))
    assert _uids(pack) == ["A", "B"]         # broad only; second search never runs


# 5.3 — NEVER-LIMIT (empty second search): merged equals broad unchanged.
def test_empty_second_search_equals_broad(monkeypatch):
    _install(monkeypatch, broad=[_it("A"), _it("B")], diag=[])   # diagnosis search returns nothing
    pack = er.retrieve_evidence(_da("colon cancer"))
    assert _uids(pack) == ["A", "B"]


# 5.4 — DE-DUP + OVERLAP RANKING: an item in BOTH appears once and ranks first.
def test_overlap_dedup_and_ranked_first(monkeypatch):
    _install(monkeypatch, broad=[_it("A"), _it("B")], diag=[_it("B"), _it("C")])
    uids = _uids(er.retrieve_evidence(_da("colon cancer")))
    assert uids.count("B") == 1              # overlap de-duped
    assert uids[0] == "B"                    # overlap ranked first (most relevant)
    assert set(uids) == {"A", "B", "C"}


# 5.5 — CAP: >7 unique; capped at MAX_MERGED_ITEMS_PER_SOURCE, diagnosis kept over surplus broad.
def test_merged_cap_prefers_diagnosis_items(monkeypatch):
    broad = [_it(x) for x in ["A", "B", "C", "D", "E"]]           # 5
    diag = [_it(x) for x in ["D", "E", "F", "G", "H"]]            # D,E overlap; F,G,H new -> 8 unique total
    _install(monkeypatch, broad=broad, diag=diag)
    uids = _uids(er.retrieve_evidence(_da("colon cancer")))
    assert len(uids) == er.MAX_MERGED_ITEMS_PER_SOURCE == 7
    for u in ["D", "E", "F", "G", "H"]:      # all diagnosis/overlap items retained
        assert u in uids
    assert "C" in uids or "B" in uids or "A" in uids   # some broad kept to fill the cap
    # exactly one surplus broad item is dropped (8 unique -> 7)
    assert len([u for u in ["A", "B", "C"] if u in uids]) == 2
