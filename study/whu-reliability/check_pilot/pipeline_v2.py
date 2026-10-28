#!/usr/bin/env python3
"""Check an AI answer, v2 (docs/whu-check-an-answer-pilot.md §9, written before this code).

Everything is v1's (pipeline.py, imported unchanged) except how a cited address becomes a
snapshot (§9.1-§9.4):
  - identifiers: find_access.ids_from_url, with the pilot's own trim of a trailing /full etc.;
    else a DOI from the landing page's citation_doi / dc.identifier / prism.doi meta (only where
    robots.txt allows and the host is not barred), else a Crossref title lookup checked by
    find_access.titles_agree;
  - a work with an identifier: v1's licence rule (Creative Commons only);
  - a web page with no DOI: fetched where robots.txt allows, by routes (a) and (b), and judged;
  - the study's barred publishers are never fetched: Elsevier and NCCN always COULDN'T CHECK;
    Wiley- or SAGE-hosted works only from an open copy found by route (c), and only with a CC licence.
Network steps are passed in, so the offline tests run on recorded pages.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from pathlib import Path

import pipeline as V1
from pipeline import *  # noqa: F401,F403  the v1 API (judge, plan, labels, ...), unchanged

SUFFIX = re.compile(r"/(?:full|abstract|pdf|epdf|html|fulltext)/?$", re.I)
META_DOI = re.compile(r"""<meta\s+[^>]*?(?:name|property)\s*=\s*["'](?:citation_doi|dc\.identifier|prism\.doi)["'][^>]*?"""
                      r"""content\s*=\s*["']\s*(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^"'\s]+)["']""", re.I)
META_DOI_REV = re.compile(r"""<meta\s+[^>]*?content\s*=\s*["']\s*(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?(10\.\d{4,9}/[^"'\s]+)["']"""
                          r"""[^>]*?(?:name|property)\s*=\s*["'](?:citation_doi|dc\.identifier|prism\.doi)["']""", re.I)
LINK = re.compile(r"\[([^\]\n]{8,400})\]\(<?(https?://[^)\s>]+)>?\)")

ALWAYS_BARRED_HOSTS = {"sciencedirect.com": "Elsevier", "elsevier.com": "Elsevier", "thelancet.com": "Elsevier",
                       "cell.com": "Elsevier", "nccn.org": "NCCN"}
CC_ONLY_HOSTS = {"onlinelibrary.wiley.com": "Wiley", "cochranelibrary.com": "Wiley", "journals.sagepub.com": "SAGE"}
ALWAYS_BARRED_DOI = {"10.1016": "Elsevier"}
CC_ONLY_DOI = {"10.1002": "Wiley", "10.1111": "Wiley", "10.1177": "SAGE"}


def host(url: str) -> str:
    return (urllib.parse.urlsplit(url).hostname or "").lower()


def _host_in(h: str, table: dict) -> str | None:
    return next((v for k, v in table.items() if h == k or h.endswith("." + k)), None)


def barred_by_host(url: str) -> tuple[str | None, str | None]:
    """(publisher barred outright, publisher allowed only with a CC licence), from the host."""
    h = host(url)
    return _host_in(h, ALWAYS_BARRED_HOSTS), _host_in(h, CC_ONLY_HOSTS)


def barred_by_doi(doi: str | None) -> tuple[str | None, str | None]:
    pre = (doi or "").split("/", 1)[0]
    return ALWAYS_BARRED_DOI.get(pre), CC_ONLY_DOI.get(pre)


def ids_v2(url: str) -> dict:
    """find_access.ids_from_url, with a trailing /full (etc.) trimmed from the DOI (§9.1)."""
    import find_access as FA
    ids = dict(FA.ids_from_url(url))
    if ids.get("doi"):
        d = ids["doi"]
        while SUFFIX.search(d):
            d = SUFFIX.sub("", d)
        ids["doi"] = d
    return ids


def titles_from(text: str) -> dict:
    """{url: link text} from the answer's own [title](url) links; a link whose text is an address is skipped."""
    out = {}
    for t, u in LINK.findall(text or ""):
        t = t.strip()
        if t and not t.lower().startswith("http") and u not in out:
            out[V1.adapt.fragment_free(u)] = t
    return out


def doi_from_meta(html: str) -> str | None:
    m = META_DOI.search(html or "") or META_DOI_REV.search(html or "")
    return m.group(1).rstrip(".") if m else None


# ---------- network steps (replaced in tests) ----------

_robots_cache: dict = {}


def robots_allows(url: str) -> tuple[bool, str]:
    """(allowed, why) for snapshot.UA. 4xx robots.txt allows; unreachable or 5xx disallows."""
    import urllib.robotparser
    import requests
    import snapshot as SN
    parts = urllib.parse.urlsplit(url)
    base = "%s://%s" % (parts.scheme, parts.netloc)
    if base not in _robots_cache:
        try:
            r = requests.get(base + "/robots.txt", headers={"User-Agent": SN.UA}, timeout=30)
            code, body = r.status_code, r.text
        except Exception as e:
            code, body = 0, str(e)
        if code and 400 <= code < 500:
            _robots_cache[base] = (None, "robots.txt HTTP %d: allowed" % code)
        elif code != 200:
            _robots_cache[base] = (False, "robots.txt could not be read (%s)" % (code or body[:80]))
        else:
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(body.splitlines())
            _robots_cache[base] = (rp, "robots.txt read")
    rp, why = _robots_cache[base]
    if rp is None:
        return True, why
    if rp is False:
        return False, why
    import snapshot as SN
    ok = rp.can_fetch(SN.UA, url)
    return ok, "robots.txt %s it" % ("allows" if ok else "disallows")


def fetch_page(url: str) -> str:
    import snapshot as SN
    data, _row = SN.fetch(url)
    return data.decode("utf-8", "replace")


def crossref_doi(title: str) -> tuple[str | None, str]:
    import requests
    import find_access as FA
    try:
        r = requests.get("https://api.crossref.org/works", params={"query.bibliographic": title, "rows": 1,
                                                                   "mailto": FA.MAIL}, timeout=30)
        items = (r.json().get("message") or {}).get("items") or []
    except Exception as e:
        return None, "Crossref lookup failed: %s" % str(e)[:80]
    time.sleep(1)
    if not items:
        return None, "Crossref: no match for the title"
    it = items[0]
    ok, why = FA.titles_agree(title, (it.get("title") or [""])[0])
    return (it.get("DOI"), "Crossref title match (%s)" % why) if ok else (None, "Crossref top hit's title does not agree (%s)" % why)


def licence_of_ids(ids: dict) -> dict:
    """v1's licence rule (pipeline.licence_of), on identifiers already found."""
    import find_access as FA
    rec = None
    for field, key in (("PMCID", "pmcid"), ("EXT_ID", "pmid"), ("DOI", "doi")):
        if key in ids:
            rec = FA.epmc(ids[key], field)
            time.sleep(1)
            if rec:
                break
    if rec and V1.is_open(rec.get("license")):
        return {"licence": rec["license"], "by": "Europe PMC license field (%s)" % (rec.get("pmcid") or rec.get("pmid"))}
    doi = ids.get("doi") or (rec or {}).get("doi")
    if doi:
        up = FA.unpaywall(doi)
        time.sleep(1)
        for loc in (up or {}).get("oa_locations") or []:
            if V1.is_open(loc.get("license")):
                return {"licence": loc["license"], "by": "Unpaywall location %s" % loc.get("host_type")}
    return {"licence": None, "by": "no Creative Commons licence in Europe PMC or Unpaywall for %s" % json.dumps(ids)}


def retrieve_open_copy(url: str, work: Path) -> dict:
    """Route (c) only, from open-access locations, never a barred host: for a Wiley or SAGE work with a
    CC licence, whose publisher site is not fetched."""
    import retrieve_sources as RN
    import snapshot as SN
    RN.RUN = work
    (work / "sources").mkdir(parents=True, exist_ok=True)
    row = {"url": url, "source_id": SN.source_id(url), "extent": "unreachable", "extent_why": "no open copy held"}
    locs, _ev = RN.oa_locations(url)
    for loc in locs:
        a, b = barred_by_host(loc["url"])
        if a or b:
            continue
        got, r = RN.by_script(loc["url"])
        if not got:
            got, r = RN.by_curl(loc["url"])
        if got:
            data, text, ctype, final = got
            ext, why = SN.extent(url, data, text, ctype)
            (work / "sources" / (row["source_id"] + ".txt")).write_text(text, encoding="utf-8")
            row.update(extent=ext, extent_why=why, abstract_only=(ext == "abstract only"), retrieved_from=loc["url"],
                       version=loc.get("version"))
            break
    return row


NET = {"robots": robots_allows, "page": fetch_page, "crossref": crossref_doi, "licence": licence_of_ids,
       "retrieve": V1.retrieve_url, "open_copy": retrieve_open_copy}


def _no(u: str, why: str, kind: str, **kw) -> dict:
    return {"url": u, "extent": "unreachable", "extent_why": why, "licence": None, "why_kind": kind, **kw}


def source_v2(u: str, title: str | None, work: Path, net: dict) -> dict:
    """One cited address -> a manifest row (§9.1-§9.4)."""
    hard, cc_only = barred_by_host(u)
    if hard:
        return _no(u, "barred publisher (%s): never fetched" % hard, "barred publisher")
    ids, how = ids_v2(u), "from the address"
    if not ids and not cc_only:
        ok, why = net["robots"](u)
        if ok:
            try:
                d = doi_from_meta(net["page"](u))
            except Exception:
                d = None
            if d:
                ids, how = {"doi": d}, "from the landing page's meta tags"
    if not ids and title:
        d, why = net["crossref"](title)
        if d:
            ids, how = {"doi": d}, why
    if ids:
        hard2, cc2 = barred_by_doi(ids.get("doi"))
        if hard2:
            return _no(u, "barred publisher (%s, DOI %s): never fetched" % (hard2, ids["doi"]), "barred publisher", ids=ids)
        cc_only = cc_only or cc2
        lic = net["licence"](ids)
        if not V1.is_open(lic["licence"]):
            if cc_only:
                return _no(u, "barred publisher (%s) without a Creative Commons licence: never fetched" % cc_only,
                           "barred publisher", ids=ids)
            return _no(u, "no open-licence copy: " + lic["by"], "no open licence", ids=ids)
        row = net["open_copy"](u, work) if cc_only else net["retrieve"](u, work)
        row.update(licence=lic["licence"], licence_by=lic["by"], ids=ids, ids_how=how)
        if row.get("extent") == "unreachable":
            row["why_kind"] = "not retrieved"
        return row
    if cc_only:
        return _no(u, "barred publisher (%s) and no identifier to check a licence: never fetched" % cc_only,
                   "barred publisher")
    ok, why = net["robots"](u)
    if not ok:
        return _no(u, "web page; %s" % why, "robots.txt disallows")
    row = net["retrieve"](u, work)
    row.update(licence=None, licence_by="web page, not a journal work; %s" % why, kind="web page")
    a, b = barred_by_host(row.get("final_url") or u)
    if a or b:  # redirected onto a barred host: not used
        return _no(u, "web page redirected to a barred publisher (%s)" % (a or b), "barred publisher")
    if row.get("extent") == "unreachable":
        row["why_kind"] = "not retrieved"
    return row


def snapshots_v2(claims: list[dict], work: Path, titles: dict, net: dict) -> dict:
    man = {}
    for c in claims:
        for ct in c["citations"]:
            u = ct.get("url")
            if u and u not in man:
                man[u] = source_v2(u, titles.get(u), work, net)
    (work / "sources").mkdir(parents=True, exist_ok=True)
    (work / "sources" / "manifest.json").write_text(json.dumps(list(man.values()), indent=1, default=str))
    return man


def prepare(text: str, work: Path, fmt: str | None = None, max_claims: int = V1.MAX_CLAIMS,
            licence_fn=None, retrieve_fn=None, count=None, system: str = "answer", net: dict | None = None) -> dict:
    """v1's prepare with §9's snapshot step. licence_fn / retrieve_fn are accepted for the v1
    call shape; v2's network steps are in NET (or NET overridden by `net`)."""
    n = dict(NET)
    if retrieve_fn:
        n["retrieve"] = retrieve_fn
    n.update(net or {})
    md, cited, fmt = V1.adapt_answer(text, fmt)
    rows, refs = V1.sentences(md, cited, work, system)
    claims, beyond = V1.claims_of(rows, refs, max_claims)
    man = snapshots_v2(claims, work, titles_from(text), n)
    planned = V1.plan(claims, man, work, count)
    return {"format": fmt, "rows": rows, "refs": refs, "claims": claims, "beyond_limit": beyond,
            "manifest": man, "planned": planned, "version": 2,
            "worst_usd": round(sum(p.get("worst") or 0 for p in planned), 4),
            "calls": sum(1 for p in planned if p["label"] is None)}
