"""
Parity Health evidence-retrieval service.

PH-3b: PubMed adapter.
PH-3c: CMS (Medicare Coverage Database) + FDA (openFDA) adapters.

Turns the PHI-free clinical concepts of a denial (procedure terms, CPT codes)
into a small pack of *verified* citations from multiple sources, cached in the
migration-069 tables (evidence_item / evidence_query).

Design notes
------------
* Source-agnostic: retrieve_evidence() returns a source-keyed pack
  {"pubmed": [...], "cms": [...], "fda": [...], "gaps": [...]}. Adding a source
  is a new adapter + a new CHANNELS entry — no rewrite of the orchestration.
* PHI firewall, two layers:
    1. Construction safety — every build_*_query() takes ONLY procedure_terms and
       cpt_codes. They literally cannot receive the denial_analysis dict.
    2. Runtime guard — _assert_no_phi(url, denial_analysis) runs before EVERY
       outbound request (PubMed, CMS, FDA) and raises if any PHI value is a
       substring of the URL.
* HTTP via stdlib urllib (no new dependency; matches the PH-2 eval).
* Supabase writes reuse the backend/supabase_client.py pattern
  (create_client with SUPABASE_SERVICE_KEY — never the service-role key here).
* Honest degradation: any network/API failure yields an empty channel plus a
  gap note. retrieve_evidence() never raises to its caller (except a tripped PHI
  guard, which is a real bug and must surface loudly).

Verification, per source
------------------------
* PubMed  — esummary returns a docsum whose uid matches the PMID (2nd call).
* FDA     — openFDA returns a record whose trade_name/generic_name matches the
            searched device term.
* CMS     — the document is present in the authoritative CMS MCD *report* list
            (served by CMS over TLS) with a canonical title/url/effective_date.
            LCD/Article detail endpoints require an API key (401 keyless), so the
            report list is the keyless verification surface; retired documents
            are filtered out (currency gate, analogous to PubMed's retraction).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
OPENFDA_BASE = "https://api.fda.gov"
CMS_COVERAGE_BASE = "https://api.coverage.cms.gov/v1"

TOOL_NAME = "parity-health"
HTTP_TIMEOUT = 20.0           # seconds; fail closed if a source is slow
ESEARCH_RETMAX = 10           # PubMed candidate PMIDs before verification
MAX_VERIFIED_ITEMS = 5        # per channel
CACHE_TTL_DAYS = 90           # PubMed/FDA are stable
CMS_CACHE_TTL_DAYS = 30       # CMS coverage revises more often -> shorter TTL

# CMS report endpoints (each returns the FULL current list; filter client-side).
CMS_REPORTS = (
    ("local-coverage-final-lcds", "LCD"),
    ("local-coverage-articles", "Article"),
    ("national-coverage-ncd", "NCD"),
)

# PHI fields that must never reach the wire. Guard checks each of these.
PHI_FIELDS = ("patient_name", "member_id", "claim_number", "patient_address")

# esummary pubtype markers indicating a retraction (case-insensitive match).
_RETRACTION_MARKERS = ("retracted publication", "retraction of publication")

# CHANNELS map a logical channel -> (query-row source, item source(s)). The
# evidence_query.source CHECK requires a single enum value, so CMS uses
# 'cms_ncd_lcd' as the umbrella query source while individual items may be
# 'cms_moldx' or 'cms_ncd_lcd'.
CHANNELS = {
    "pubmed": {"query_source": "pubmed", "item_sources": ["pubmed"]},
    "cms": {"query_source": "cms_ncd_lcd", "item_sources": ["cms_moldx", "cms_ncd_lcd"]},
    "fda": {"query_source": "fda", "item_sources": ["fda"]},
}


# ---------------------------------------------------------------------------
# PHI runtime guard + shared HTTP
# ---------------------------------------------------------------------------

def _assert_no_phi(url, denial_analysis):
    """Raise if any PHI value appears as a substring of the outbound URL.

    Belt-and-suspenders on top of the query builders' construction safety.
    Checks both the raw URL and its percent-decoded form, case-insensitively.
    Never includes the PHI value itself in the raised message (would re-leak it).
    """
    if not denial_analysis:
        return
    haystacks = (url.lower(), urllib.parse.unquote_plus(url).lower())
    for field in PHI_FIELDS:
        val = denial_analysis.get(field)
        if not val:
            continue
        needle = str(val).strip().lower()
        if not needle:
            continue
        if any(needle in h for h in haystacks):
            raise ValueError(
                f"PHI guard tripped: value of denial_analysis['{field}'] "
                f"appears in an outbound URL. Refusing to send."
            )


def _http_get_json(url):
    """GET url and parse JSON. Returns dict on success, None on any failure.

    Single seam the deterministic tests monkeypatch so the offline suite replays
    recorded responses with no network. openFDA returns HTTP 404 for zero-hit
    searches, which we treat as an empty (non-error) result.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": TOOL_NAME}, method="GET")
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # openFDA "No matches found" — an empty result, not an outage.
            try:
                return json.loads(e.read().decode())
            except Exception:
                return {"error": {"code": "NOT_FOUND"}}
        return None
    except Exception:
        return None


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _content_hash(title, body, year):
    payload = f"{title or ''}\x1f{body or ''}\x1f{year or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _year_from(*candidates):
    """First 4-digit year found in any candidate string."""
    for c in candidates:
        if not c:
            continue
        m = re.search(r"(19|20|21)\d{2}", str(c))
        if m:
            return int(m.group(0))
    return None


def _params_common():
    """tool identifier + optional email/api_key (NCBI), keyless-friendly."""
    params = {"tool": TOOL_NAME}
    email = os.environ.get("NCBI_EMAIL")
    if email:
        params["email"] = email
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


# ===========================================================================
# Adapter 1 — PubMed (PH-3b)
# ===========================================================================

def build_pubmed_query(procedure_terms, cpt_codes):
    """Build a PubMed term query from PHI-free clinical concepts.

    Takes ONLY procedure_terms and cpt_codes — deliberately NOT denial_analysis —
    so it is structurally incapable of leaking PHI.

    - Multi-word procedure phrases are quoted and OR-joined.
    - CPT codes are EXCLUDED: PLA/Category-III codes such as "0340U" are
      proprietary billing identifiers that essentially never appear as indexed
      terms in the literature, so they only add noise. The parameter is kept for
      interface stability; its values are not placed on the wire.

    Returns the raw (un-encoded) query string; URL-encoding happens at call time.
    """
    terms = []
    for t in (procedure_terms or []):
        s = str(t).strip()
        if not s:
            continue
        terms.append(f'"{s}"' if " " in s else s)

    seen, uniq = set(), []
    for t in terms:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return " OR ".join(uniq)


def _build_esearch_url(query):
    params = _params_common()
    params.update({
        "db": "pubmed", "term": query, "retmode": "json",
        "retmax": str(ESEARCH_RETMAX), "sort": "relevance",
    })
    return f"{EUTILS_BASE}/esearch.fcgi?" + urllib.parse.urlencode(params)


def _build_esummary_url(pmids):
    params = _params_common()
    params.update({"db": "pubmed", "id": ",".join(str(p) for p in pmids), "retmode": "json"})
    return f"{EUTILS_BASE}/esummary.fcgi?" + urllib.parse.urlencode(params)


def _pubmed_esearch(query, denial_analysis):
    if not query:
        return []
    url = _build_esearch_url(query)
    _assert_no_phi(url, denial_analysis)
    data = _http_get_json(url)
    if not data:
        return []
    idlist = (((data or {}).get("esearchresult") or {}).get("idlist")) or []
    return [str(p) for p in idlist]


def _pubmed_esummary(pmids, denial_analysis):
    if not pmids:
        return {}
    url = _build_esummary_url(pmids)
    _assert_no_phi(url, denial_analysis)
    data = _http_get_json(url)
    if not data:
        return {}
    return (data or {}).get("result") or {}


# Tight title markers for society guidelines that PubMed often tags only as
# "Review"/"Systematic Review" (e.g. PMID 36252154 "ASCO Guideline" carries
# pubtype ["Systematic Review", "Journal Article"], no "Guideline" tag). Kept
# narrow so ordinary reviews are not swept in.
_GUIDELINE_TITLE_MARKERS = ("asco guideline", "nccn guideline", "practice guideline")


def _map_study_type(pubtypes, title=""):
    lowered = [str(p).strip().lower() for p in (pubtypes or [])]
    if any("meta-analysis" in p for p in lowered):
        return "meta_analysis"
    if any("randomized controlled trial" in p for p in lowered):
        return "RCT"
    # Guideline wins over review/other: honor the PubMed "Guideline" pubtype OR a
    # tight society-guideline title marker (PubMed frequently omits the tag).
    title_low = (title or "").lower()
    if (any("guideline" in p for p in lowered)
            or any(m in title_low for m in _GUIDELINE_TITLE_MARKERS)):
        return "guideline"
    if any("review" in p for p in lowered):
        return "review"
    return "other"


def _is_retracted(pubtypes):
    lowered = [str(p).strip().lower() for p in (pubtypes or [])]
    return any(any(m in p for m in _RETRACTION_MARKERS) for p in lowered)


def _format_pubmed_citation(docsum, title, year):
    authors = [a.get("name") for a in (docsum.get("authors") or []) if a.get("name")]
    journal = docsum.get("fulljournalname") or docsum.get("source") or ""
    lead = (authors[0] if len(authors) == 1 else
            (f"{authors[0]} et al." if authors else ""))
    bits = [b for b in [lead, title, journal, (str(year) if year else "")] if b]
    out = ". ".join(bits)
    return out + ("." if out and not out.endswith(".") else "")


def _build_pubmed_items(pmids, esummary_result):
    """Verify PMIDs vs esummary (uid match), drop retractions, build items."""
    items = []
    for pmid in pmids:
        docsum = (esummary_result or {}).get(str(pmid))
        if not isinstance(docsum, dict) or str(docsum.get("uid")) != str(pmid):
            continue                                  # verification gate
        pubtypes = docsum.get("pubtype") or []
        if _is_retracted(pubtypes):
            continue                                  # retraction filter
        title = (docsum.get("title") or "").strip()
        year = _year_from(docsum.get("pubdate"), docsum.get("epubdate"), docsum.get("sortpubdate"))
        journal = docsum.get("fulljournalname") or docsum.get("source") or ""
        authors = [a.get("name") for a in (docsum.get("authors") or []) if a.get("name")]
        items.append({
            "source": "pubmed",
            "source_uid": str(pmid),
            "title": title or None,
            "citation": _format_pubmed_citation(docsum, title, year),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pub_year": year,
            "study_type": _map_study_type(pubtypes, title),
            "content_tier": "full",
            "summary": (f"{title} ({journal}, {year})." if title else None),
            "abstract": None,          # esummary carries no abstract; efetch (deferred). tier=full permits it.
            "metadata": {"authors": authors, "journal": journal, "pubtype": pubtypes},
            "verified": True,
            "verified_at": _now_iso(),
            "verification_method": "esummary 200 + uid match",
            "retracted": False,
            "content_hash": _content_hash(title, None, year),
            "fetched_at": _now_iso(),
        })
        if len(items) >= MAX_VERIFIED_ITEMS:
            break
    return items


def _fetch_pubmed(query, denial_analysis):
    try:
        pmids = _pubmed_esearch(query, denial_analysis)
        if not pmids:
            return []
        result = _pubmed_esummary(pmids, denial_analysis)
        return _build_pubmed_items(pmids, result)
    except ValueError:
        raise
    except Exception:
        return []


# ===========================================================================
# Adapter 2 — CMS Medicare Coverage Database (PH-3c)
# ===========================================================================

def build_cms_query(procedure_terms, cpt_codes):
    """Return PHI-free lowercased match terms for CMS title filtering.

    Takes ONLY procedure_terms and cpt_codes. CPT codes are excluded from title
    matching (CMS document titles never contain PLA codes); they remain in the
    interface for future coding-article body matching.
    """
    terms = []
    for t in (procedure_terms or []):
        s = str(t).strip().lower()
        if s and s not in terms:
            terms.append(s)
    return terms


def _build_cms_report_url(report):
    return f"{CMS_COVERAGE_BASE}/reports/{report}"


def _cms_is_current(row):
    """Drop retired/expired coverage documents (currency gate)."""
    note = (row.get("note") or "").strip().lower()
    if "retired" in note:
        return False
    ret = (row.get("retirement_date") or "").strip()
    if ret and ret.upper() not in ("N/A", "NA", "NONE"):
        return False
    return True


def _cms_source_for(title):
    return "cms_moldx" if "moldx" in (title or "").lower() else "cms_ncd_lcd"


def _cms_public_url(row):
    url = (row.get("url") or "").strip()
    if url.startswith("http"):
        return url
    # NCD rows return a relative "/data/ncd?..." API path; map to the public view.
    if row.get("document_type") == "NCD":
        return (f"https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?"
                f"ncdid={row.get('document_id')}&ncdver={row.get('document_version')}")
    return url or None


def _term_matches_title(term, title_low):
    """A procedure term matches a CMS title if the whole term is present, or any
    consecutive word-bigram of the term is present. The bigram rule bridges
    clinically-equivalent phrasings (e.g. the denial's "molecular residual
    disease" vs CMS's "minimal residual disease" both share "residual disease")
    without hardcoded synonyms, while staying specific enough to avoid the
    false positives a bare single-word match would produce."""
    t = (term or "").strip().lower()
    if not t:
        return False
    if t in title_low:
        return True
    words = t.split()
    for i in range(len(words) - 1):
        if f"{words[i]} {words[i + 1]}" in title_low:
            return True
    return False


def _cms_match(rows, terms, doc_type):
    """Filter report rows whose title matches any term and are current."""
    hits = []
    for row in rows:
        low = (row.get("title") or "").lower()
        if not any(_term_matches_title(term, low) for term in terms):
            continue
        if not _cms_is_current(row):
            continue
        hits.append(row)
    return hits


def _build_cms_item(row, report_name):
    title = (row.get("title") or "").strip()
    display_id = row.get("document_display_id") or str(row.get("document_id"))
    contractor = " ".join((row.get("contractor_name_type") or "").split())
    eff = (row.get("effective_date") or "").strip()
    year = _year_from(eff, row.get("updated_on"))
    citation_bits = [title, f"{row.get('document_type')} {display_id}"]
    if contractor:
        citation_bits.append(contractor)
    if eff:
        citation_bits.append(f"effective {eff}")
    return {
        "source": _cms_source_for(title),
        "source_uid": str(display_id),
        "title": title or None,
        "citation": ". ".join(citation_bits) + ".",
        "url": _cms_public_url(row),
        "pub_year": year,
        "study_type": "coverage_policy",
        "content_tier": "full",       # US government policy — storable
        "summary": (f"CMS {row.get('document_type')} {display_id}: {title}"
                    + (f" ({contractor})" if contractor else "")
                    + (f", effective {eff}." if eff else ".")),
        "abstract": None,             # LCD/Article body requires an API key (401 keyless); deferred.
        "metadata": {
            "document_type": row.get("document_type"),
            "document_display_id": display_id,
            "contractor_name_type": contractor or None,
            "effective_date": eff or None,
            "updated_on": row.get("updated_on"),
            "report": report_name,
        },
        "verified": True,
        "verified_at": _now_iso(),
        "verification_method": f"present in CMS MCD {report_name} report",
        "retracted": False,
        "content_hash": _content_hash(title, display_id, year),
        "fetched_at": _now_iso(),
    }


def _fetch_cms(terms, denial_analysis):
    """Match current CMS coverage docs by title across the report endpoints.

    Dedupes by normalized title (LCDs come from multiple MAC contractors with
    identical titles); LCDs are preferred over Articles over NCDs. Never raises
    except on a tripped PHI guard.
    """
    if not terms:
        return []
    try:
        items, seen_titles = [], set()
        for report_name, _dtype in CMS_REPORTS:
            url = _build_cms_report_url(report_name)
            _assert_no_phi(url, denial_analysis)      # guard every outbound URL
            data = _http_get_json(url)
            rows = (data or {}).get("data") or []
            for row in _cms_match(rows, terms, _dtype):
                tkey = " ".join((row.get("title") or "").lower().split())
                if tkey in seen_titles:
                    continue                          # dedupe near-identical policies
                seen_titles.add(tkey)
                items.append(_build_cms_item(row, report_name))
                if len(items) >= MAX_VERIFIED_ITEMS:
                    return items
        return items
    except ValueError:
        raise
    except Exception:
        return []


# ===========================================================================
# Adapter 3 — FDA (openFDA device) (PH-3c)
# ===========================================================================

def build_fda_query(procedure_terms, cpt_codes):
    """Return PHI-free candidate device/brand terms for openFDA search.

    Takes ONLY procedure_terms and cpt_codes. Returns the cleaned procedure
    terms; the adapter tries each against trade_name then generic_name.
    """
    terms = []
    for t in (procedure_terms or []):
        s = str(t).strip()
        if s and s.lower() not in [x.lower() for x in terms]:
            terms.append(s)
    return terms


def _build_openfda_url(endpoint, field, term):
    params = {"search": f'{field}:"{term}"', "limit": "5"}
    return f"{OPENFDA_BASE}/device/{endpoint}.json?" + urllib.parse.urlencode(params)


_FDA_ENDPOINTS = (
    ("pma", "trade_name", "pma_number"),
    ("pma", "generic_name", "pma_number"),
    ("510k", "device_name", "k_number"),
)


def _fda_public_url(endpoint, uid):
    if endpoint == "pma":
        return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMA/pma.cfm?id={uid}"
    return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfPMN/pmn.cfm?ID={uid}"


def _extract_fda_indication(ao_statement):
    """Extract the SPECIFIC indicated use (disease + associated therapy) from an
    openFDA PMA approval-order statement (ao_statement), generically — no
    hardcoded disease/drug names. Returns {} when nothing is found so callers
    degrade to a generic summary rather than implying a broader approval.

    The PMA ao_statement lists indicated use in an "Indicated Use and Associated
    Therapy" table, e.g. "... Muscle Invasive Bladder Cancer (MIBC) TECENTRIQ
    (atezolizumab) ...". We capture the '<...> Cancer (<ABBR>)' indication and
    the first lowercase parenthetical drug (INN) that follows it.
    """
    if not ao_statement:
        return {}
    s = " ".join(str(ao_statement).split())
    out = {}
    # Each leading word must be Titlecase (uppercase + a lowercase letter), so
    # all-caps tokens (MRD) and run-on header fragments are not swept in; cap the
    # phrase at 5 words ending in "Cancer" with an optional (ABBR).
    m = re.search(r"((?:[A-Z][a-z][A-Za-z/&\-]* ){1,5}Cancer(?:\s*\([A-Za-z]+\))?)", s)
    if m:
        out["disease"] = m.group(1).strip()
        tail = s[m.end():]
        t = re.search(r"\(([a-z][a-z0-9\- ]{3,})\)", tail)   # first lowercase parenthetical = generic drug
        if t:
            out["therapy"] = t.group(1).strip()
    return out


def _build_fda_item(rec, endpoint, uid_field):
    uid = str(rec.get(uid_field) or "").strip()
    trade = (rec.get("trade_name") or "").strip()
    generic = (rec.get("generic_name") or "").strip()
    applicant = (rec.get("applicant") or "").strip()
    decision_date = (rec.get("decision_date") or "").strip()
    ao_statement = (rec.get("ao_statement") or "").strip()
    year = _year_from(decision_date, rec.get("date_received"))
    kind = "PMA" if endpoint == "pma" else "510(k)"
    title = " — ".join([b for b in [trade or generic, generic if trade else ""] if b]) or (trade or generic)

    # Record the SPECIFIC indication so PH-4 states it precisely and never
    # implies a broader approval than exists.
    ind = _extract_fda_indication(ao_statement)
    disease = ind.get("disease")
    therapy = ind.get("therapy")
    base = f"FDA {kind} {uid} — {trade or generic}" + (f" by {applicant}" if applicant else "")
    if disease:
        summary = (base + f": FDA indicated use — {disease}"
                   + (f" with {therapy}" if therapy else "")
                   + (f" (decision {decision_date})." if decision_date else "."))
    else:
        summary = base + (f", decision {decision_date}." if decision_date else ".")

    return {
        "source": "fda",
        "source_uid": uid,
        "title": title or None,
        "citation": (f"FDA {kind} {uid}"
                     + (f" — {trade}" if trade else "")
                     + (f" ({applicant})" if applicant else "")
                     + (f", decision {decision_date}" if decision_date else "") + "."),
        "url": _fda_public_url(endpoint, uid),
        "pub_year": year,
        "study_type": "device_approval",
        "content_tier": "full",       # US government data — storable
        "summary": summary,
        "abstract": None,
        "metadata": {
            "endpoint": endpoint,
            "applicant": applicant or None,
            "trade_name": trade or None,
            "generic_name": generic or None,
            "decision_code": rec.get("decision_code"),
            "decision_date": decision_date or None,
            "product_code": rec.get("product_code"),
            "advisory_committee_description": rec.get("advisory_committee_description"),
            "indication": disease,                 # specific indicated-use disease
            "indication_therapy": therapy,         # associated FDA-labeled therapy
            "ao_statement": ao_statement or None,  # authoritative FDA text, verbatim
        },
        "verified": True,
        "verified_at": _now_iso(),
        "verification_method": f"openFDA {endpoint} 200 + name match",
        "retracted": False,
        "content_hash": _content_hash(title, uid, year),
        "fetched_at": _now_iso(),
    }


def _fda_name_matches(rec, term):
    low = term.lower()
    return (low in (rec.get("trade_name") or "").lower()
            or low in (rec.get("generic_name") or "").lower()
            or low in (rec.get("device_name") or "").lower())


def _fetch_fda(terms, denial_analysis):
    """Search openFDA device endpoints for each term; keep verified name matches.

    A record is verified only if the searched term is a substring of its
    trade_name/generic_name/device_name (guards against openFDA fuzzy hits).
    Never raises except on a tripped PHI guard.
    """
    if not terms:
        return []
    try:
        items, seen_uids = [], set()
        for term in terms:
            for endpoint, field, uid_field in _FDA_ENDPOINTS:
                url = _build_openfda_url(endpoint, field, term)
                _assert_no_phi(url, denial_analysis)  # guard every outbound URL
                data = _http_get_json(url)
                if not data or (data.get("error")):
                    continue
                for rec in (data.get("results") or []):
                    if not _fda_name_matches(rec, term):
                        continue                      # verification gate
                    uid = str(rec.get(uid_field) or "").strip()
                    if not uid or ("fda", uid) in seen_uids:
                        continue
                    seen_uids.add(("fda", uid))
                    items.append(_build_fda_item(rec, endpoint, uid_field))
                    if len(items) >= MAX_VERIFIED_ITEMS:
                        return items
        return items
    except ValueError:
        raise
    except Exception:
        return []


# ===========================================================================
# Cache layer (migration-069 tables, service_role client)
# ===========================================================================

def _get_client():
    """Lazy Supabase client, reusing the backend/supabase_client.py pattern
    (SUPABASE_SERVICE_KEY — never the service-role key). Returns None if the env
    is not configured, so offline/test paths degrade instead of crashing.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception:
        return None


def _normalize_query_key(query):
    """Normalized, PHI-free cache key. Accepts a string or a list of terms."""
    if isinstance(query, (list, tuple)):
        query = " | ".join(str(q) for q in query)
    return " ".join((query or "").split()).lower()


def _cache_lookup(client, query_source, query_key):
    if client is None:
        return None
    try:
        resp = (client.table("evidence_query").select("*")
                .eq("source", query_source).eq("query_key", query_key)
                .gt("expires_at", _now_iso()).limit(1).execute())
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _load_items_by_uids(client, item_sources, uids):
    if client is None or not uids:
        return []
    try:
        resp = (client.table("evidence_item").select("*")
                .in_("source", list(item_sources))
                .eq("verified", True).eq("retracted", False)
                .in_("source_uid", list(uids)).execute())
        return resp.data or []
    except Exception:
        return []


def _upsert_items(client, items):
    if client is None or not items:
        return
    try:
        client.table("evidence_item").upsert(items, on_conflict="source,source_uid").execute()
    except Exception:
        pass


def _upsert_query(client, query_source, query_key, cpt_code, denial_category, result_uids, ttl_days):
    if client is None:
        return
    now = datetime.now(timezone.utc)
    row = {
        "source": query_source,
        "query_key": query_key,
        "cpt_code": cpt_code,
        "denial_category": denial_category,
        "result_uids": list(result_uids),
        "result_count": len(result_uids),
        "fetched_at": now.isoformat(),
        "expires_at": (now + timedelta(days=ttl_days)).isoformat(),
    }
    try:
        client.table("evidence_query").upsert(row, on_conflict="source,query_key").execute()
    except Exception:
        pass


# ===========================================================================
# Orchestration
# ===========================================================================

def _run_channel(client, channel, query_key, fetch_fn, cpt_code, denial_category,
                 force_refresh, ttl_days):
    """Cache-lookup -> (miss) fetch+verify -> persist. Returns item list.

    PHI-guard ValueErrors propagate; all other failures degrade to [].
    """
    cfg = CHANNELS[channel]
    items = []
    if not force_refresh:
        cached = _cache_lookup(client, cfg["query_source"], query_key)
        if cached is not None:
            items = _load_items_by_uids(client, cfg["item_sources"], cached.get("result_uids") or [])
    if not items:
        fetched = fetch_fn()                          # may raise ValueError (PHI)
        if fetched:
            _upsert_items(client, fetched)
            _upsert_query(client, cfg["query_source"], query_key, cpt_code,
                          denial_category, [it["source_uid"] for it in fetched], ttl_days)
        items = fetched
    return items


def retrieve_evidence(denial_analysis, force_refresh=False):
    """Retrieve a verified multi-source evidence pack for a denial.

    Only procedure_terms + cpt_codes are used to build queries (via the
    build_*_query functions). The full denial_analysis is passed ONLY to the PHI
    runtime guard. Returns {"pubmed": [...], "cms": [...], "fda": [...],
    "gaps": [...]} and never raises (except a tripped PHI guard).
    """
    denial_analysis = denial_analysis or {}
    procedure_terms = denial_analysis.get("procedure_terms") or []
    cpt_codes = denial_analysis.get("cpt_codes") or []
    icd_codes = denial_analysis.get("icd_codes") or []
    denial_category = denial_analysis.get("denial_category")
    cpt0 = cpt_codes[0] if cpt_codes else None
    client = _get_client()

    # Build PHI-free queries once.
    pubmed_query = build_pubmed_query(procedure_terms, cpt_codes)
    cms_terms = build_cms_query(procedure_terms, cpt_codes)
    fda_terms = build_fda_query(procedure_terms, cpt_codes)

    pubmed_items = cms_items = fda_items = []
    try:
        pubmed_items = _run_channel(
            client, "pubmed", _normalize_query_key(pubmed_query),
            lambda: _fetch_pubmed(pubmed_query, denial_analysis),
            cpt0, denial_category, force_refresh, CACHE_TTL_DAYS)

        cms_items = _run_channel(
            client, "cms", _normalize_query_key(cms_terms),
            lambda: _fetch_cms(cms_terms, denial_analysis),
            cpt0, denial_category, force_refresh, CMS_CACHE_TTL_DAYS)

        fda_items = _run_channel(
            client, "fda", _normalize_query_key(fda_terms),
            lambda: _fetch_fda(fda_terms, denial_analysis),
            cpt0, denial_category, force_refresh, CACHE_TTL_DAYS)
    except ValueError:
        raise                                         # PHI guard — surface loudly
    except Exception:
        pass                                          # honest degradation

    # Gaps are computed per-call.
    gaps = []
    if not icd_codes:
        gaps.append("No diagnosis (ICD) code supplied — diagnosis-specific evidence not retrieved.")
    term_list = ", ".join(str(t) for t in procedure_terms) or "(none)"
    if not pubmed_items:
        gaps.append(f"No PubMed evidence retrieved for terms: {term_list}")
    if not cms_items:
        gaps.append(f"No CMS coverage policy found for terms: {term_list}")
    if not fda_items:
        gaps.append(f"No FDA device record found for terms: {term_list}")

    return {"pubmed": pubmed_items, "cms": cms_items, "fda": fda_items, "gaps": gaps}
