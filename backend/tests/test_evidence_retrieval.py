"""
PH-3b/PH-3c — multi-source evidence-retrieval tests (PubMed + CMS + FDA).

Two layers (mirroring the PH-2 Signatera harness):
  * Deterministic suite (default, CI-safe, NO network, NO DB): replays recorded
    PubMed/CMS/FDA responses and stubs storage. Proves each adapter's
    verification gate, the retraction/retired/name-match filters, gap notes,
    content_tier, and — the load-bearing gate — that no PHI reaches any
    outbound URL (PubMed, CMS, or FDA).
  * Live eval (@pytest.mark.eval, on-demand): hits real PubMed/CMS/FDA and
    asserts drift-tolerant structural properties only.

Deterministic run: python3 -m pytest backend/tests/test_evidence_retrieval.py -v
Eval run:          python3 -m pytest backend/tests/test_evidence_retrieval.py -m eval -v -s
"""

import copy
import json
import os
import sys
import urllib.parse

import pytest

# Make backend/ importable so `utils...` resolves regardless of invocation dir.
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from utils import evidence_retrieval as er  # noqa: E402

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_FIX = os.path.join(_REPO, "test-data", "appeals", "signatera_cigna")

# Sentinel PHI the guard must never let onto the wire (matches the fixture).
SENTINELS = {
    "patient_name": "Jane A. Doe",
    "member_id": "MEMBER-TEST-001",
    "claim_number": "CLAIM-TEST-0340U",
    "patient_address": "123 Main St, Wesley Chapel, FL 33543",
}


def _load(name):
    with open(os.path.join(_FIX, name)) as f:
        return json.load(f)


def _denial():
    return _load("expected_extraction.json")


def _recorded_esearch():
    return _load("pubmed_esearch_response.json")


def _recorded_esummary():
    return _load("pubmed_esummary_response.json")


def _recorded_http_map():
    """url -> payload map for CMS report + openFDA responses (CMS trimmed)."""
    return _load("cms_fda_http_cache.json")


# ---------------------------------------------------------------------------
# Offline HTTP replay: dispatch PubMed by URL family, CMS/FDA by exact URL.
# ---------------------------------------------------------------------------

def _make_replay(esearch=None, esummary=None, http_map=None):
    esearch = esearch if esearch is not None else _recorded_esearch()
    esummary = esummary if esummary is not None else _recorded_esummary()
    http_map = http_map if http_map is not None else _recorded_http_map()

    def _replay(url):
        if "esearch.fcgi" in url:
            return esearch
        if "esummary.fcgi" in url:
            return esummary
        if url in http_map:
            return http_map[url]
        # Sensible empties for any un-recorded probe (no network).
        if "/device/" in url:
            return {"error": {"code": "NOT_FOUND"}}
        if "/reports/" in url:
            return {"data": []}
        return None
    return _replay


@pytest.fixture
def offline(monkeypatch):
    """Replay recorded responses; guarantee NO network and NO DB write."""
    monkeypatch.setattr(er, "_http_get_json", _make_replay())
    monkeypatch.setattr(er, "_get_client", lambda: None)   # storage stub: no DB
    return monkeypatch


# ===========================================================================
# Deterministic — pack shape & PubMed (PH-3b)
# ===========================================================================

class TestPackAndPubmed:
    def test_pack_has_all_channels(self, offline):
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        for key in ("pubmed", "cms", "fda", "gaps"):
            assert key in pack

    def test_pubmed_returns_verified_items(self, offline):
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        assert len(pack["pubmed"]) >= 1

    def test_every_pubmed_pmid_in_recorded_esummary(self, offline):
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        recorded = set((_recorded_esummary().get("result") or {}).get("uids") or [])
        for item in pack["pubmed"]:
            assert item["source_uid"] in recorded

    def test_content_tier_full_all_channels(self, offline):
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        for chan in ("pubmed", "cms", "fda"):
            assert pack[chan]
            assert all(it["content_tier"] == "full" for it in pack[chan])

    def test_gap_note_for_missing_icd(self, offline):
        da = _denial()
        assert da["icd_codes"] == []
        pack = er.retrieve_evidence(da, force_refresh=True)
        assert any("No diagnosis (ICD) code" in g for g in pack["gaps"])

    def test_pubmed_retracted_item_dropped(self, monkeypatch):
        fake = "99999999"
        esearch = copy.deepcopy(_recorded_esearch())
        esearch["esearchresult"]["idlist"] = [fake] + esearch["esearchresult"]["idlist"]
        esummary = copy.deepcopy(_recorded_esummary())
        esummary["result"]["uids"] = [fake] + esummary["result"]["uids"]
        esummary["result"][fake] = {
            "uid": fake, "title": "A now-retracted study on ctDNA.",
            "pubdate": "2020 Jan", "source": "J Retractions",
            "authors": [{"name": "Ghost A"}],
            "pubtype": ["Journal Article", "Retracted Publication"],
        }
        monkeypatch.setattr(er, "_http_get_json", _make_replay(esearch, esummary))
        monkeypatch.setattr(er, "_get_client", lambda: None)
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        assert fake not in {it["source_uid"] for it in pack["pubmed"]}
        assert len(pack["pubmed"]) >= 1

    def test_society_guideline_classified_as_guideline(self, offline):
        """A society guideline PubMed tags only as a (systematic) review must
        still be study_type 'guideline' (PMID 36252154 'ASCO Guideline'), while
        content_tier stays 'full' and ordinary reviews are not swept in."""
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        g = next(it for it in pack["pubmed"] if it["source_uid"] == "36252154")
        assert g["study_type"] == "guideline"
        assert g["content_tier"] == "full"
        others = [it for it in pack["pubmed"] if it["source_uid"] != "36252154"]
        assert all(it["study_type"] != "guideline" for it in others)


# ===========================================================================
# Deterministic — CMS adapter (PH-3c)
# ===========================================================================

class TestCms:
    def test_cms_returns_verified_coverage(self, offline):
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        assert len(pack["cms"]) >= 1
        for it in pack["cms"]:
            assert it["source"] in ("cms_moldx", "cms_ncd_lcd")
            assert it["study_type"] == "coverage_policy"
            assert "CMS MCD" in it["verification_method"]

    def test_cms_moldx_classification(self, offline):
        """MolDX titles map to the cms_moldx source."""
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        moldx = [it for it in pack["cms"] if "moldx" in (it["title"] or "").lower()]
        assert moldx and all(it["source"] == "cms_moldx" for it in moldx)

    def test_cms_bigram_bridges_molecular_vs_minimal(self, offline):
        """The denial says 'molecular residual disease'; CMS says 'minimal
        residual disease'. The shared bigram must still match."""
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        assert any("minimal residual disease" in (it["title"] or "").lower()
                   for it in pack["cms"])

    def test_cms_retired_document_filtered(self, monkeypatch):
        """A retired coverage doc must be dropped (currency gate)."""
        http_map = copy.deepcopy(_recorded_http_map())
        lcd_url = next(u for u in http_map if "local-coverage-final-lcds" in u)
        http_map[lcd_url]["data"] = [{
            "document_id": 99999, "document_version": 1,
            "document_display_id": "L99999", "document_type": "LCD",
            "note": "Retired",
            "title": "MolDX: Minimal Residual Disease Testing for Cancer",
            "contractor_name_type": "Test MAC",
            "effective_date": "01/01/2020", "retirement_date": "01/01/2024",
            "url": "https://www.cms.gov/x",
        }]
        monkeypatch.setattr(er, "_http_get_json", _make_replay(http_map=http_map))
        monkeypatch.setattr(er, "_get_client", lambda: None)
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        assert "L99999" not in {it["source_uid"] for it in pack["cms"]}


# ===========================================================================
# Deterministic — FDA adapter (PH-3c)
# ===========================================================================

class TestFda:
    def test_fda_returns_verified_device(self, offline):
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        assert len(pack["fda"]) >= 1
        for it in pack["fda"]:
            assert it["source"] == "fda"
            assert "name match" in it["verification_method"]
            assert it["url"].startswith("https://www.accessdata.fda.gov/")

    def test_fda_records_specific_indication(self, offline):
        """The FDA item must record the SPECIFIC approved indication (MIBC +
        atezolizumab), not a blanket 'approved' label — so PH-4 never implies a
        broader approval. (The FDA ao_statement writes 'Muscle Invasive Bladder
        Cancer' without a hyphen; accept either spacing.)"""
        import re
        fda = next(it for it in er.retrieve_evidence(_denial(), force_refresh=True)["fda"])
        summ = fda["summary"].lower()
        assert re.search(r"muscle[\s-]invasive bladder cancer", summ), fda["summary"]
        assert "atezolizumab" in summ
        # metadata carries the specific indication + verbatim FDA source text.
        assert fda["metadata"]["indication_therapy"] == "atezolizumab"
        assert "bladder cancer" in (fda["metadata"]["indication"] or "").lower()
        assert "Table 1" in (fda["metadata"]["ao_statement"] or "")

    def test_fda_name_match_gate_drops_mismatch(self, monkeypatch):
        """An openFDA hit whose name doesn't contain the term is rejected."""
        http_map = copy.deepcopy(_recorded_http_map())
        for u in list(http_map):
            if "/device/" in u:
                http_map[u] = {"results": [{
                    "pma_number": "P00000", "trade_name": "Totally Unrelated Device",
                    "generic_name": "unrelated", "applicant": "Nobody",
                }]}
        monkeypatch.setattr(er, "_http_get_json", _make_replay(http_map=http_map))
        monkeypatch.setattr(er, "_get_client", lambda: None)
        pack = er.retrieve_evidence(_denial(), force_refresh=True)
        assert pack["fda"] == []                       # mismatch rejected
        assert any("No FDA device record" in g for g in pack["gaps"])


# ===========================================================================
# Deterministic — PHI firewall (the load-bearing gate)
# ===========================================================================

class TestPhiFirewall:
    def test_query_builders_cannot_receive_phi(self):
        import inspect
        for fn in (er.build_pubmed_query, er.build_cms_query, er.build_fda_query):
            assert list(inspect.signature(fn).parameters) == ["procedure_terms", "cpt_codes"]

    def test_no_phi_on_any_outbound_url(self):
        """Build every outbound URL family from a PHI-carrying denial; assert
        none of the four sentinels appears on the wire (PubMed, CMS, FDA)."""
        da = _denial()
        for field, val in SENTINELS.items():
            assert da[field] == val

        pubmed_q = er.build_pubmed_query(da["procedure_terms"], da["cpt_codes"])
        cms_terms = er.build_cms_query(da["procedure_terms"], da["cpt_codes"])
        fda_terms = er.build_fda_query(da["procedure_terms"], da["cpt_codes"])

        urls = [er._build_esearch_url(pubmed_q), er._build_esummary_url(["12345678"])]
        urls += [er._build_cms_report_url(r) for r, _ in er.CMS_REPORTS]
        for term in fda_terms:
            for endpoint, field, _uid in er._FDA_ENDPOINTS:
                urls.append(er._build_openfda_url(endpoint, field, term))

        surfaces = [pubmed_q.lower()]
        for u in urls:
            surfaces.append(u.lower())
            surfaces.append(urllib.parse.unquote_plus(u).lower())

        for field, val in SENTINELS.items():
            for surface in surfaces:
                assert val.lower() not in surface, f"PHI '{field}' leaked into {surface[:80]}"

        assert "Signatera" in pubmed_q                 # real term still present

    def test_guard_raises_when_phi_in_url(self):
        da = _denial()
        leaky = "https://api.fda.gov/device/pma.json?search=" + da["patient_name"].replace(" ", "+")
        with pytest.raises(ValueError):
            er._assert_no_phi(leaky, da)

    def test_guard_passes_clean_urls(self):
        da = _denial()
        er._assert_no_phi(er._build_cms_report_url("national-coverage-ncd"), da)
        er._assert_no_phi(er._build_openfda_url("pma", "trade_name", "Signatera"), da)


# ===========================================================================
# Live eval (marked; excluded from default runs) — hits real PubMed/CMS/FDA
# ===========================================================================

@pytest.mark.eval
def test_live_multisource_retrieval_eval():
    """Drift-tolerant structural eval against live sources. No exact-ID asserts."""
    da = _denial()
    pack = er.retrieve_evidence(da, force_refresh=True)

    # Each source returns at least one verified item.
    assert len(pack["pubmed"]) >= 1, "expected >=1 live PubMed item"
    assert len(pack["cms"]) >= 1, "expected >=1 live CMS coverage doc"
    assert len(pack["fda"]) >= 1, "expected >=1 live FDA device record"

    # PubMed PMIDs re-resolve via a fresh esummary (uid match).
    pmids = [it["source_uid"] for it in pack["pubmed"]]
    fresh = er._pubmed_esummary(pmids, da)
    for pmid in pmids:
        ds = fresh.get(pmid)
        assert isinstance(ds, dict) and str(ds.get("uid")) == pmid

    # No PHI sentinel in any outbound URL family.
    pubmed_q = er.build_pubmed_query(da["procedure_terms"], da["cpt_codes"])
    fda_terms = er.build_fda_query(da["procedure_terms"], da["cpt_codes"])
    urls = [er._build_esearch_url(pubmed_q), er._build_esummary_url(pmids)]
    urls += [er._build_cms_report_url(r) for r, _ in er.CMS_REPORTS]
    for term in fda_terms:
        for endpoint, field, _uid in er._FDA_ENDPOINTS:
            urls.append(er._build_openfda_url(endpoint, field, term))
    for url in urls:
        decoded = urllib.parse.unquote_plus(url).lower()
        for val in SENTINELS.values():
            assert val.lower() not in decoded

    assert any("ICD" in g for g in pack["gaps"])

    wrote = bool(er._get_client())
    for chan in ("pubmed", "cms", "fda"):
        print(f"\n[eval] {chan} = {len(pack[chan])}")
        for it in pack[chan]:
            print(f"  {it['source']:<11} {it['source_uid']:<10} [{it['study_type']:<15}] "
                  f"{it['pub_year']} {it['title']}")
    print(f"[eval] cache written = {wrote}; "
          f"source_uids = { {c: [i['source_uid'] for i in pack[c]] for c in ('pubmed','cms','fda')} }")
