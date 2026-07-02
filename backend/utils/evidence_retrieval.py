"""
PH-3b — Parity Health evidence-retrieval service (PubMed only).

Standalone retrieval pipeline that turns the PHI-free clinical concepts of a
denial (procedure terms, CPT codes) into a small pack of *verified* PubMed
citations, cached in the migration-069 tables (evidence_item / evidence_query).

Design notes
------------
* PubMed ONLY in this phase. CMS/FDA adapters are PH-3c. The public entry point
  retrieve_evidence() returns a source-keyed pack ({"pubmed": [...], "gaps": [...]})
  so additional sources become new keys + new adapter functions, no rewrite.
* PHI firewall, two layers:
    1. Construction safety — build_pubmed_query() takes ONLY procedure_terms and
       cpt_codes. It literally cannot receive the denial_analysis dict, so it
       cannot leak PHI.
    2. Runtime guard — _assert_no_phi(url, denial_analysis) runs before EVERY
       outbound request and raises if any PHI value is a substring of the URL.
* HTTP via stdlib urllib (no new dependency; matches the PH-2 eval).
* Supabase writes reuse the backend/supabase_client.py pattern
  (create_client with SUPABASE_SERVICE_KEY — never the service-role key here).
* Honest degradation: any network/API failure yields pubmed=[] plus a gap note.
  retrieve_evidence() never raises to its caller.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL_NAME = "parity-health"
HTTP_TIMEOUT = 15.0          # seconds; NCBI is usually fast, fail closed if not
ESEARCH_RETMAX = 10          # candidate PMIDs to pull before verification
MAX_VERIFIED_ITEMS = 5       # keep at most this many verified, non-retracted items
CACHE_TTL_DAYS = 90          # PubMed is stable; long TTL is fine

# PHI fields that must never reach the wire. Guard checks each of these.
PHI_FIELDS = ("patient_name", "member_id", "claim_number", "patient_address")

# esummary pubtype markers indicating a retraction (case-insensitive match).
_RETRACTION_MARKERS = ("retracted publication", "retraction of publication")


# ---------------------------------------------------------------------------
# Task 2 — PHI-free query builder (construction safety)
# ---------------------------------------------------------------------------

def build_pubmed_query(procedure_terms, cpt_codes):
    """Build a PubMed term query from PHI-free clinical concepts.

    Takes ONLY procedure_terms and cpt_codes — deliberately NOT the denial_analysis
    dict — so it is structurally incapable of leaking PHI.

    - Multi-word procedure phrases are quoted and OR-joined.
    - CPT codes are intentionally EXCLUDED from the term query: PLA/Category-III
      codes such as "0340U" are proprietary billing identifiers that essentially
      never appear as indexed terms in the biomedical literature, so including
      them only adds noise / zero-hit AND clauses. The parameter is kept for
      interface stability and future heuristics (e.g. mapping a CPT to a MeSH
      term), but its values are not placed on the wire here.

    Returns the raw (un-encoded) query string; URL-encoding happens at call time.
    """
    terms = []
    for t in (procedure_terms or []):
        s = str(t).strip()
        if not s:
            continue
        # Quote multi-word phrases so PubMed treats them as a phrase.
        terms.append(f'"{s}"' if " " in s else s)

    # De-duplicate while preserving order.
    seen = set()
    uniq = []
    for t in terms:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(t)

    return " OR ".join(uniq)


# ---------------------------------------------------------------------------
# Task 3 — PHI runtime guard + PubMed HTTP client (keyless)
# ---------------------------------------------------------------------------

def _assert_no_phi(url, denial_analysis):
    """Raise if any PHI value appears as a substring of the outbound URL.

    Belt-and-suspenders on top of build_pubmed_query()'s construction safety.
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
                f"appears in an outbound PubMed URL. Refusing to send."
            )


def _params_common():
    """tool identifier + optional email/api_key, keyless-friendly."""
    params = {"tool": TOOL_NAME}
    email = os.environ.get("NCBI_EMAIL")
    if email:
        params["email"] = email
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def _build_esearch_url(query):
    params = _params_common()
    params.update({
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": str(ESEARCH_RETMAX),
        "sort": "relevance",
    })
    return f"{EUTILS_BASE}/esearch.fcgi?" + urllib.parse.urlencode(params)


def _build_esummary_url(pmids):
    params = _params_common()
    params.update({
        "db": "pubmed",
        "id": ",".join(str(p) for p in pmids),
        "retmode": "json",
    })
    return f"{EUTILS_BASE}/esummary.fcgi?" + urllib.parse.urlencode(params)


def _http_get_json(url):
    """GET url and parse JSON. Returns dict on success, None on any failure.

    This is the single seam the deterministic test monkeypatches so the offline
    suite replays recorded PubMed responses with no network.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": TOOL_NAME}, method="GET")
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            if resp.status != 200:
                return None
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _pubmed_esearch(query, denial_analysis):
    """Return a list of candidate PMIDs (strings) for query, or []."""
    if not query:
        return []
    url = _build_esearch_url(query)
    _assert_no_phi(url, denial_analysis)          # guard EVERY outbound URL
    data = _http_get_json(url)
    if not data:
        return []
    idlist = (((data or {}).get("esearchresult") or {}).get("idlist")) or []
    return [str(p) for p in idlist]


def _pubmed_esummary(pmids, denial_analysis):
    """Return the esummary 'result' dict for pmids, or {}."""
    if not pmids:
        return {}
    url = _build_esummary_url(pmids)
    _assert_no_phi(url, denial_analysis)          # guard EVERY outbound URL
    data = _http_get_json(url)
    if not data:
        return {}
    return (data or {}).get("result") or {}


# ---------------------------------------------------------------------------
# Task 4 — verification gate, retraction filter, item construction
# ---------------------------------------------------------------------------

def _map_study_type(pubtypes):
    """Map an esummary pubtype list to a coarse study_type."""
    lowered = [str(p).strip().lower() for p in (pubtypes or [])]
    if any("meta-analysis" in p for p in lowered):
        return "meta_analysis"
    if any("randomized controlled trial" in p for p in lowered):
        return "RCT"
    if any("guideline" in p for p in lowered):        # Guideline / Practice Guideline
        return "guideline"
    if any("review" in p for p in lowered):           # Review / Systematic Review
        return "review"
    return "other"


def _is_retracted(pubtypes):
    lowered = [str(p).strip().lower() for p in (pubtypes or [])]
    return any(any(m in p for m in _RETRACTION_MARKERS) for p in lowered)


def _extract_year(docsum):
    for key in ("pubdate", "epubdate", "sortpubdate"):
        raw = (docsum.get(key) or "").strip()
        if len(raw) >= 4 and raw[:4].isdigit():
            return int(raw[:4])
    return None


def _format_citation(docsum, title, year):
    authors = [a.get("name") for a in (docsum.get("authors") or []) if a.get("name")]
    journal = docsum.get("fulljournalname") or docsum.get("source") or ""
    if len(authors) == 1:
        lead = authors[0]
    elif len(authors) > 1:
        lead = f"{authors[0]} et al."
    else:
        lead = ""
    bits = [b for b in [lead, title, journal, (str(year) if year else "")] if b]
    return ". ".join(bits).replace("..", ".") + ("." if bits and not bits[-1].endswith(".") else "")


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _content_hash(title, abstract, year):
    payload = f"{title or ''}\x1f{abstract or ''}\x1f{year or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_verified_items(pmids, esummary_result):
    """Verify PMIDs against esummary, drop retractions, build evidence items.

    A PMID is VERIFIED only if esummary_result contains a docsum whose 'uid'
    matches. Retracted items are dropped. Returns up to MAX_VERIFIED_ITEMS items.
    """
    items = []
    for pmid in pmids:
        docsum = (esummary_result or {}).get(str(pmid))
        # Verification gate: docsum must exist AND its uid must match.
        if not isinstance(docsum, dict):
            continue
        if str(docsum.get("uid")) != str(pmid):
            continue

        pubtypes = docsum.get("pubtype") or []
        if _is_retracted(pubtypes):
            continue                                  # retraction filter

        title = (docsum.get("title") or "").strip()
        year = _extract_year(docsum)
        journal = docsum.get("fulljournalname") or docsum.get("source") or ""
        authors = [a.get("name") for a in (docsum.get("authors") or []) if a.get("name")]
        abstract = None    # esummary carries no abstract; efetch would (deferred). tier=full permits it.
        summary = f"{title} ({journal}, {year})." if title else None

        items.append({
            "source": "pubmed",
            "source_uid": str(pmid),
            "title": title or None,
            "citation": _format_citation(docsum, title, year),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "pub_year": year,
            "study_type": _map_study_type(pubtypes),
            "content_tier": "full",                   # PubMed abstracts are storable
            "summary": summary,
            "abstract": abstract,
            "metadata": {
                "authors": authors,
                "journal": journal,
                "pubtype": pubtypes,
            },
            "verified": True,
            "verified_at": _now_iso(),
            "verification_method": "esummary 200 + uid match",
            "retracted": False,
            "content_hash": _content_hash(title, abstract, year),
            "fetched_at": _now_iso(),
        })
        if len(items) >= MAX_VERIFIED_ITEMS:
            break
    return items


# ---------------------------------------------------------------------------
# Task 5 — cache layer (migration-069 tables, service_role client)
# ---------------------------------------------------------------------------

def _get_client():
    """Lazy Supabase client, reusing the backend/supabase_client.py pattern
    (SUPABASE_SERVICE_KEY — never the service-role key). Returns None if the
    env is not configured, so offline/test paths degrade instead of crashing.
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
    """Normalized, PHI-free cache key for a (source, query) pair."""
    return " ".join((query or "").split()).lower()


def _cache_lookup(client, query_key):
    """Return a fresh (unexpired) evidence_query row for this key, or None."""
    if client is None:
        return None
    try:
        resp = (
            client.table("evidence_query")
            .select("*")
            .eq("source", "pubmed")
            .eq("query_key", query_key)
            .gt("expires_at", _now_iso())
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _load_items_by_uids(client, uids):
    """Load verified, non-retracted evidence_item rows for the given source_uids."""
    if client is None or not uids:
        return []
    try:
        resp = (
            client.table("evidence_item")
            .select("*")
            .eq("source", "pubmed")
            .eq("verified", True)
            .eq("retracted", False)
            .in_("source_uid", list(uids))
            .execute()
        )
        return resp.data or []
    except Exception:
        return []


def _upsert_items(client, items):
    """Upsert evidence_item rows on conflict (source, source_uid)."""
    if client is None or not items:
        return
    try:
        client.table("evidence_item").upsert(
            items, on_conflict="source,source_uid"
        ).execute()
    except Exception:
        pass


def _upsert_query(client, query_key, cpt_code, denial_category, result_uids):
    """Upsert the evidence_query cache row on conflict (source, query_key)."""
    if client is None:
        return
    now = datetime.now(timezone.utc)
    row = {
        "source": "pubmed",
        "query_key": query_key,
        "cpt_code": cpt_code,
        "denial_category": denial_category,
        "result_uids": list(result_uids),
        "result_count": len(result_uids),
        "fetched_at": now.isoformat(),
        "expires_at": (now + timedelta(days=CACHE_TTL_DAYS)).isoformat(),
    }
    try:
        client.table("evidence_query").upsert(
            row, on_conflict="source,query_key"
        ).execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Task 6 — public entry point
# ---------------------------------------------------------------------------

def _fetch_pubmed(query, denial_analysis):
    """esearch -> esummary -> verified items. Never raises; returns [] on failure."""
    try:
        pmids = _pubmed_esearch(query, denial_analysis)
        if not pmids:
            return []
        result = _pubmed_esummary(pmids, denial_analysis)
        return _build_verified_items(pmids, result)
    except ValueError:
        # PHI guard tripping is a real bug — let it surface loudly.
        raise
    except Exception:
        return []


def retrieve_evidence(denial_analysis, force_refresh=False):
    """Retrieve a verified PubMed evidence pack for a denial.

    Only procedure_terms + cpt_codes are used to build the query (via
    build_pubmed_query). The full denial_analysis is passed ONLY to the PHI
    runtime guard. Returns {"pubmed": [items], "gaps": [notes]} and never raises.
    """
    denial_analysis = denial_analysis or {}
    procedure_terms = denial_analysis.get("procedure_terms") or []
    cpt_codes = denial_analysis.get("cpt_codes") or []
    icd_codes = denial_analysis.get("icd_codes") or []
    denial_category = denial_analysis.get("denial_category")

    query = build_pubmed_query(procedure_terms, cpt_codes)
    query_key = _normalize_query_key(query)
    client = _get_client()

    pubmed_items = []
    try:
        # Cache hit: no network.
        if not force_refresh:
            cached = _cache_lookup(client, query_key)
            if cached is not None:
                pubmed_items = _load_items_by_uids(client, cached.get("result_uids") or [])

        # Cache miss (or forced): go to PubMed, then persist.
        if not pubmed_items:
            fetched = _fetch_pubmed(query, denial_analysis)
            if fetched:
                _upsert_items(client, fetched)
                _upsert_query(
                    client,
                    query_key,
                    cpt_codes[0] if cpt_codes else None,
                    denial_category,
                    [it["source_uid"] for it in fetched],
                )
            pubmed_items = fetched
    except ValueError:
        raise                                        # PHI guard — surface it
    except Exception:
        pubmed_items = []                            # honest degradation

    # Gaps are computed per-call.
    gaps = []
    if not icd_codes:
        gaps.append("No diagnosis (ICD) code supplied — diagnosis-specific evidence not retrieved.")
    if not pubmed_items:
        term_list = ", ".join(str(t) for t in procedure_terms) or "(none)"
        gaps.append(f"No PubMed evidence retrieved for terms: {term_list}")

    return {"pubmed": pubmed_items, "gaps": gaps}
