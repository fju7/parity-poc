"""The literature registry adapter: DOI, PMID, PMCID, NCT.

resolve() is scripts/signal/verify_sources.resolve() behind the shared
interface, with the same registries in the same order and the same lesson
kept: an NCT resolves to THREE titles (official, brief, acronym), because
ours is the acronym. fetch() adds what Signal never had -- bytes.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html as _html
import json
import re
import urllib.parse

from . import http
from .types import Document, Exists, Identifier, Provenance, Resolution

_NOW = lambda: dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()  # noqa: E731


def identify(url_or_id: str, provenance: Provenance = Provenance.TYPED) -> Identifier | None:
    """(system, value) for a resolvable literature identifier in a URL or bare id, or None."""
    u = (url_or_id or "").strip()
    if not u:
        return None
    if "doi.org/" in u:
        return Identifier("doi", u.split("doi.org/")[-1].strip().rstrip("/").lower(), u, provenance)
    m = re.match(r"^(?:doi:)?(10\.\d{4,9}/\S+)$", u, re.I)
    if m:
        return Identifier("doi", m.group(1).rstrip(".,)").lower(), u, provenance)
    m = re.search(r"(NCT\d{8})", u, re.I)
    if m:
        return Identifier("nct", m.group(1).upper(), u, provenance)
    m = re.search(r"(PMC\d{6,9})", u, re.I)
    if m:
        return Identifier("pmcid", m.group(1).upper(), u, provenance)
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", u) or re.match(r"^(?:pmid:?\s*)?(\d{6,9})$", u, re.I)
    if m:
        return Identifier("pmid", m.group(1), u, provenance)
    return None


def _json(body: bytes):
    try:
        return json.loads(body.decode("utf-8", "replace"))
    except Exception:
        return None


def resolve(ident: Identifier) -> Resolution:
    res = Resolution(ident, Exists.UNCHECKED, checked_at=_NOW())
    if ident.system == "doi":
        # The Handle System covers every registration agency, not just
        # CrossRef -- checked before trusting a 404, so a DataCite DOI is never
        # reported as fabricated.
        st, body, _ = http.get("https://doi.org/api/handles/" + urllib.parse.quote(ident.value))
        h = _json(body)
        if st == 0:
            return res
        if st == 404 or (h and h.get("responseCode") != 1):
            res.exists = Exists.NONEXISTENT; res.registry = "handle"; return res
        res.exists = Exists.EXISTS; res.registry = "handle"
        res.canonical = "https://doi.org/" + ident.value
        st, body, _ = http.get("https://api.crossref.org/works/" + urllib.parse.quote(ident.value))
        cr = _json(body) if st == 200 else None
        if cr:
            msg = cr.get("message", {})
            res.registry = "crossref"; res.registry_id = msg.get("DOI")
            res.heading = (msg.get("title") or [None])[0]
            parts = (msg.get("published") or msg.get("issued") or {}).get("date-parts", [[None]])[0]
            res.extra = {"container": (msg.get("container-title") or [None])[0],
                         "type": msg.get("type"),
                         "published": parts, "year": parts[0] if parts else None,
                         "abstract": re.sub(r"<[^>]+>", "", msg.get("abstract") or "") or None}
        return res

    if ident.system in ("pmid", "pmcid"):
        q = f"EXT_ID:{ident.value} AND SRC:MED" if ident.system == "pmid" else f"PMCID:{ident.value}"
        st, body, _ = http.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
                               + urllib.parse.quote(q) + "&format=json&pageSize=1&resultType=core")
        d = _json(body) if st == 200 else None
        if d is None:
            return res
        hits = (d.get("resultList") or {}).get("result") or []
        res.registry = "europepmc"
        if not hits:
            res.exists = Exists.NONEXISTENT; return res
        r0 = hits[0]
        res.exists = Exists.EXISTS; res.heading = r0.get("title"); res.registry_id = r0.get("id")
        res.canonical = ("https://pubmed.ncbi.nlm.nih.gov/" + r0["pmid"] + "/") if r0.get("pmid") else None
        res.extra = {"pmid": r0.get("pmid"), "pmcid": r0.get("pmcid"), "doi": r0.get("doi"),
                     "inEPMC": r0.get("inEPMC"), "isOpenAccess": r0.get("isOpenAccess"),
                     "journal": r0.get("journalTitle"), "year": r0.get("pubYear"),
                     "abstract": r0.get("abstractText")}
        return res

    if ident.system == "nct":
        st, body, _ = http.get(f"https://clinicaltrials.gov/api/v2/studies/{ident.value}"
                               "?fields=protocolSection.identificationModule,protocolSection.statusModule,"
                               "protocolSection.designModule,resultsSection")
        res.registry = "clinicaltrials.gov"
        if st == 404:
            res.exists = Exists.NONEXISTENT; return res
        d = _json(body) if st == 200 else None
        if d is None:
            return res
        idm = (d.get("protocolSection") or {}).get("identificationModule") or {}
        cands = [idm.get("officialTitle"), idm.get("briefTitle"), idm.get("acronym")]
        res.exists = Exists.EXISTS
        res.heading = " || ".join(c for c in cands if c) or None
        res.canonical = f"https://clinicaltrials.gov/study/{ident.value}"
        res.registry_id = ident.value
        res.extra = {"status": ((d.get("protocolSection") or {}).get("statusModule") or {}),
                     "record": d}
        return res
    return res


def _epmc_xml_text(xml: bytes) -> str:
    t = re.sub(r"<[^>]+>", " ", xml.decode("utf-8", "replace"))
    return re.sub(r"\s+", " ", _html.unescape(t)).strip()


def _doc(ident: Identifier, text: str, route: str, kind: str, url: str | None,
         content_type: str = "text/plain") -> Document:
    return Document(ident, hashlib.sha256(text.encode()).hexdigest(), text, content_type,
                    _NOW(), url, route, kind)


def fetch(res: Resolution) -> Document | None:
    """Bytes for a resolved literature identifier: full text where an open copy exists,
    the abstract otherwise, the registry record for a trial. None when nothing was got."""
    ident = res.identifier
    if res.exists != Exists.EXISTS:
        return None
    if ident.system == "nct":
        rec = res.extra.get("record")
        if rec:
            text = json.dumps(rec, ensure_ascii=False)
            return _doc(ident, re.sub(r"[\"{}\[\],]", " ", text), "ctgov_v2", "record", res.canonical, "application/json")
        return None
    # A DOI/PMID/PMCID: ask Europe PMC for the record, then full text if it holds it.
    pmcid = res.extra.get("pmcid")
    if ident.system == "doi" or not pmcid:
        # The DOI is quoted: an Elsevier PII DOI's parentheses otherwise break
        # the query and the search returns nothing -- which on 2026-09-14 read
        # as "fetch: nothing retrieved" for Wakefield 1998 and nine others.
        q = f'DOI:"{ident.value}"' if ident.system == "doi" else (
            f"EXT_ID:{ident.value} AND SRC:MED" if ident.system == "pmid" else f"PMCID:{ident.value}")
        st, body, _ = http.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
                               + urllib.parse.quote(q) + "&format=json&pageSize=1&resultType=core")
        d = _json(body) if st == 200 else None
        hits = ((d or {}).get("resultList") or {}).get("result") or []
        r0 = hits[0] if hits else {}
        pmcid = r0.get("pmcid") or pmcid
        in_epmc = r0.get("inEPMC")
        abstract = r0.get("abstractText") or res.extra.get("abstract")
    else:
        in_epmc = res.extra.get("inEPMC"); abstract = res.extra.get("abstract")
    if pmcid and in_epmc == "Y":
        st, body, _ = http.get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
        if st == 200 and len(body) > 2000:
            return _doc(ident, _epmc_xml_text(body), "europepmc_fulltext_xml", "full_text",
                        f"https://europepmc.org/article/PMC/{pmcid}", "application/xml")
    if abstract:
        text = re.sub(r"<[^>]+>", " ", abstract)
        return _doc(ident, (res.heading or "") + "\n" + _html.unescape(text), "europepmc_abstract", "abstract", res.canonical)
    return None
