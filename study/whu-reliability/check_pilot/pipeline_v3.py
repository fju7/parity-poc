#!/usr/bin/env python3
"""Check an AI answer, v3 (docs/whu-check-an-answer-pilot.md §10, written before this code).

v1 (pipeline.py) and v2 (pipeline_v2.py) are imported unchanged; the judge is judge_m1's, through
v1's plan and judge (no prompt is restated here). What v3 adds:
  §10.1  every BACKED / NOT BACKED verdict carries the judge's span, found word for word in the text
         judged, under 60 words, with its location and a link; no passage -> COULDN'T CHECK
  §10.3  which copies may be fetched: (a) repository copies, free to read; (b) a publisher's copy
         only with a Creative Commons licence; (c) web pages that are not journal works; (d)
         robots.txt, TDMRep, the barred publishers, never past a wall. A challenge page ends that copy.
         Rendering in headless Chromium for a page with too little text; an open copy by identifier.
  §10.4  the abstract, from Europe PMC or Crossref, when no full text is held
  §10.5  a passage the user supplies (at most 300 words), never written anywhere
  §10.6  claims ranked: numbers, cause and effect, conclusions, then the rest; or the user's ticks
  §10.9  one named reason per COULDN'T CHECK
Network steps are in NET, so the offline tests run on recorded replies.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pipeline as V1
import pipeline_v2 as V2
from pipeline import BACKED, COULDNT, LABELS, NO_SOURCE, NOT_BACKED, Stop  # noqa: F401

J, S, adapt = V1.J, V1.S, V1.adapt
# snapshot.py sets no_proxy on import, because on macOS a process that has looked up the system proxy
# settings forks children that die on signal 11 (pdftotext, curl, Playwright's driver). v3 can reach
# find_access's urllib calls before its first fetch, so the setting is made here, at import.
if sys.platform == "darwin":
    os.environ.setdefault("no_proxy", "*")
import snapshot as _SN  # noqa: E402,F401

# --------------------------------------------------------------------------
# §10.9 reasons, and the sub-kinds of a verdict (§10.2)
# --------------------------------------------------------------------------
R_BARRED, R_ROBOTS, R_TDM, R_WALL, R_SIGNIN = ("barred publisher", "robots.txt disallows", "TDM reservation",
                                               "bot wall or CAPTCHA", "sign-in or paywall")
R_NOLICENCE, R_NOCOPY, R_CONN = "publisher copy without licence", "no copy found", "connection failed or timed out"
R_ABSTRACT, R_DELIVERY, R_NOPASSAGE = "abstract does not state it", "delivery check", "no passage to show"
R_REFUSED, R_UNPARSED, R_MARKER = "refused", "unparsed", "marker outside the reference list"
REASONS = (R_BARRED, R_ROBOTS, R_TDM, R_WALL, R_SIGNIN, R_NOLICENCE, R_NOCOPY, "HTTP error", R_CONN,
           R_ABSTRACT, R_DELIVERY, R_NOPASSAGE, R_REFUSED, R_UNPARSED, R_MARKER)
ABSTRACT_ONLY = "checked against the abstract only"
SUPPLIED = "checked against a passage you supplied"
SUPPLIED_NOTICE = "Paste only text you have the right to use."
SUPPLIED_MAX_WORDS = 300
PASSAGE_MAX_WORDS = 59                      # "under 60 words"
RULE_A, RULE_B, RULE_C, RULE_ABS = ("(a) repository copy", "(b) publisher copy with a Creative Commons licence",
                                    "(c) web page, not a journal work", "abstract (§10.4)")

# --------------------------------------------------------------------------
# §10.6 claim ranking
# --------------------------------------------------------------------------
NUMBER = re.compile(r"\d")
CAUSAL = re.compile(r"\b(caus\w*|lead(s|ing)? to|led to|because|due to|result(s|ed|ing)? in|driv(e|es|en|ing)|"
                    r"reduc\w*|increas\w*|decreas\w*|improv\w*|prevent\w*|lower(s|ed)?|rais(e|es|ed)|"
                    r"effect(s|ive|iveness)?|impact\w*|benefit\w*|harm\w*)\b", re.I)
CONCLUSION = re.compile(r"\b(therefore|thus|hence|overall|in conclusion|in summary|taken together|"
                        r"conclud\w*|suggest\w*|indicat\w*|shows? that|means that|the evidence)\b", re.I)


def claim_rank(text: str) -> int:
    """0 a number, 1 a cause and effect, 2 a conclusion, 3 the rest. Citation markers are not numbers."""
    t = V1.MARK.sub(" ", text)
    if NUMBER.search(t):
        return 0
    if CAUSAL.search(t):
        return 1
    if CONCLUSION.search(t):
        return 2
    return 3


def claims_v3(rows: list[dict], refs: list[str], selected: list[int] | None = None,
              max_claims: int = V1.MAX_CLAIMS) -> tuple[list[dict], list[dict], int]:
    """(claims to check in the answer's order, claim-like sentences not checked, claim-like found)."""
    pool, _ = V1.claims_of(rows, refs, max_claims=10 ** 6)
    if selected is not None:
        want = list(dict.fromkeys(selected))[:max_claims]
        chosen = [c for c in pool if c["idx"] in set(want)]
    else:
        chosen = sorted(pool, key=lambda c: (claim_rank(c["claim"]), c["idx"]))[:max_claims]
    keep = {c["idx"] for c in chosen}
    for c in chosen:
        c["rank"] = claim_rank(c["claim"])
    return (sorted(chosen, key=lambda c: c["idx"]), [c for c in pool if c["idx"] not in keep], len(pool))


# --------------------------------------------------------------------------
# Formats: v1's, plus round 1's two (prepare_round1.tool_answer)
# --------------------------------------------------------------------------

def adapt_answer(text: str, fmt: str | None = None) -> tuple[str, list[str] | None, str]:
    if fmt in ("claude_sources_r1", "perplexity_footnotes"):
        body, cited = getattr(adapt, fmt)(text)
        return body, cited, fmt
    return V1.adapt_answer(text, fmt)


# --------------------------------------------------------------------------
# §10.3 hosts
# --------------------------------------------------------------------------
REPOSITORY_HOSTS = ("europepmc.org", "ebi.ac.uk", "pmc.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov/pmc", "arxiv.org",
                    "biorxiv.org", "medrxiv.org", "psyarxiv.com", "osf.io", "ssrn.com", "zenodo.org",
                    "hal.science", "hal.archives-ouvertes.fr", "researchsquare.com", "preprints.org",
                    "repec.org", "core.ac.uk", "semanticscholar.org", "escholarship.org", "figshare.com")
REPOSITORY_PATTERNS = ("eprints.", "repository.", "ore.", "dspace.", "researchportal.", "/handle/",
                       "researchonline.", "discovery.", "pure.", "research-repository.", "openaccess.")
CHALLENGE_MARKERS = ("just a moment", "cf-chl", "challenge-platform", "captcha", "are you a robot",
                     "verify you are human", "awswaf", "attention required", "_incapsula_", "datadome", "px-captcha",
                     # served with HTTP 200 (seen in v3's free pass, 2026-10-30): F5 at Springer Nature, NCBI's
                     # reCAPTCHA browser check, UNT's request validation
                     "client challenge", "/_fs-ch-", "checking your browser", "validating your request",
                     "verifying you are human", "browser check", "bot protection")
SIGNIN_MARKERS = ("sign in to continue", "log in to continue", "please sign in", "please log in",
                  "subscribe to continue", "purchase this article", "buy this article", "institutional login",
                  "access through your institution")
SIGNIN_PATH = re.compile(r"/(login|signin|sign-in|sso|auth|idp|shibboleth|subscribe|paywall)\b", re.I)
RENDER_TIMEOUT_MS = 20_000


def is_repository(url: str) -> bool:
    """§10.3 (a) by address: a listed repository or preprint host, or a repository host pattern."""
    h, low = V2.host(url), url.lower()
    path = urllib.parse.urlsplit(low).path
    for r in REPOSITORY_HOSTS:
        if ("/" in r and r in low) or ("/" not in r and (h == r or h.endswith("." + r))):
            return True
    return any((p in path) if p.startswith("/") else (h.startswith(p) or ("." + p) in h)
               for p in REPOSITORY_PATTERNS)


def barred(url: str, doi: str | None = None) -> tuple[str | None, str | None]:
    """(barred outright, allowed only with CC), by host and, once known, DOI (v2 §9.4)."""
    a, b = V2.barred_by_host(url)
    c, d = V2.barred_by_doi(doi)
    return a or c, b or d


# --------------------------------------------------------------------------
# Network (replaced in tests)
# --------------------------------------------------------------------------

class Refused(Exception):
    """A copy that may not be read, or could not be: .kind is a §10.9 reason."""

    def __init__(self, kind: str, why: str):
        super().__init__(why)
        self.kind, self.why = kind, why


def _challenge(status: int, headers: dict, body: bytes) -> bool:
    h = {k.lower(): str(v).lower() for k, v in (headers or {}).items()}
    if h.get("cf-mitigated") == "challenge" or h.get("x-amzn-waf-action") in ("challenge", "captcha"):
        return True
    low = body[:6000].decode("utf-8", "replace").lower()
    if status in (202, 403, 429, 503) and (not body.strip() or any(m in low for m in CHALLENGE_MARKERS)):
        return True
    return len(body) < 100000 and any(m in low for m in CHALLENGE_MARKERS)


def _signin(final_url: str, body: bytes) -> bool:
    low = body[:20000].decode("utf-8", "replace").lower()
    return bool(SIGNIN_PATH.search(urllib.parse.urlsplit(final_url or "").path)) or (
        len(body) < 60000 and any(m in low for m in SIGNIN_MARKERS))


def http_get(url: str, timeout: int = 30) -> dict:
    """One GET as snapshot.UA: {status, headers, body, final_url, content_type}; raises Refused on a
    network failure. Redirects are followed by requests (a loop raises)."""
    import requests
    import snapshot as SN
    try:
        r = requests.get(url, headers={"User-Agent": SN.UA, "Accept-Language": "en"}, timeout=timeout,
                         allow_redirects=True)
    except requests.exceptions.TooManyRedirects:
        raise Refused("HTTP error", "HTTP error (redirect loop)")
    except requests.exceptions.SSLError:
        try:
            data, row = SN.fetch(url, timeout=timeout)             # snapshot's own certificate-chain repair
        except Exception as e:
            raise Refused(R_CONN, "connection failed: %s" % str(e)[:120])
        return {"status": row.get("status", 200), "headers": {}, "body": data, "final_url": row.get("final_url") or url,
                "content_type": row.get("content_type", "")}
    except requests.exceptions.Timeout:
        raise Refused(R_CONN, "timed out after %d s" % timeout)
    except requests.exceptions.RequestException as e:
        raise Refused(R_CONN, "connection failed: %s" % type(e).__name__)
    return {"status": r.status_code, "headers": dict(r.headers), "body": r.content, "final_url": r.url,
            "content_type": r.headers.get("content-type", "")}


_cache_lock = threading.Lock()
_robots: dict = {}
_tdm: dict = {}


def _origin(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    return "%s://%s" % (p.scheme, p.netloc)


def robots_v3(url: str, get=http_get) -> tuple[bool, str, str | None]:
    """(allowed, why, kind when refused). v2 §9.3's reading (4xx allows; unreadable or 5xx disallows),
    except that a challenge in place of robots.txt is a bot wall."""
    import urllib.robotparser
    import snapshot as SN
    base = _origin(url)
    with _cache_lock:
        got = _robots.get(base)
    if got is None:
        try:
            r = get(base + "/robots.txt")
            if _challenge(r["status"], r["headers"], r["body"]):
                got = ("wall", "robots.txt answered with a challenge (HTTP %d)" % r["status"])
            elif 400 <= r["status"] < 500:
                got = (None, "robots.txt HTTP %d: allowed" % r["status"])
            elif r["status"] != 200:
                got = (False, "robots.txt could not be read (HTTP %d)" % r["status"])
            else:
                rp = urllib.robotparser.RobotFileParser()
                rp.parse(r["body"].decode("utf-8", "replace").splitlines())
                got = (rp, "robots.txt read")
        except Refused as e:
            got = (False, "robots.txt could not be read (%s)" % e.why)
        with _cache_lock:
            _robots[base] = got
    rp, why = got
    if rp == "wall":
        return False, why, R_WALL
    if rp is None:
        return True, why, None
    if rp is False:
        return False, why, R_ROBOTS
    ok = rp.can_fetch(SN.UA, url)
    return ok, "robots.txt %s it" % ("allows" if ok else "disallows"), (None if ok else R_ROBOTS)


def tdm_site(url: str, get=http_get) -> tuple[bool, str]:
    """(reserved, why) from the site's /.well-known/tdmrep.json (W3C TDMRep): the first entry whose
    `location` pattern matches the path decides."""
    base = _origin(url)
    with _cache_lock:
        rules = _tdm.get(base)
    if rules is None:
        rules = []
        try:
            r = get(base + "/.well-known/tdmrep.json")
            if r["status"] == 200:
                data = json.loads(r["body"].decode("utf-8", "replace"))
                rules = [e for e in data if isinstance(e, dict)] if isinstance(data, list) else []
        except (Refused, ValueError):
            rules = []
        with _cache_lock:
            _tdm[base] = rules
    path = urllib.parse.urlsplit(url).path or "/"
    for e in rules:
        loc = str(e.get("location") or "")
        pat = loc if loc.startswith("/") else "/" + loc
        if fnmatch.fnmatchcase(path, pat) or fnmatch.fnmatchcase(path, pat.rstrip("*") + "*") and pat.endswith("*"):
            if str(e.get("tdm-reservation")) == "1":
                return True, "tdmrep.json reserves %s" % loc
            return False, "tdmrep.json: no reservation for %s" % loc
    return False, "no TDM reservation in tdmrep.json"


META_TDM = re.compile(r"""<meta\s+[^>]*name\s*=\s*["']tdm-reservation["'][^>]*content\s*=\s*["']\s*1\s*["']|"""
                      r"""<meta\s+[^>]*content\s*=\s*["']\s*1\s*["'][^>]*name\s*=\s*["']tdm-reservation["']""", re.I)


def tdm_page(headers: dict, body: bytes) -> bool:
    h = {k.lower(): str(v).strip() for k, v in (headers or {}).items()}
    return h.get("tdm-reservation") == "1" or bool(META_TDM.search(body[:60000].decode("utf-8", "replace")))


def render(url: str) -> bytes:
    """The page as headless Chromium renders it: no cookies kept, no sign-in, no clicks, 20 s."""
    from playwright.sync_api import sync_playwright
    import snapshot as SN
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        try:
            ctx = b.new_context(user_agent=SN.UA, java_script_enabled=True)
            pg = ctx.new_page()
            pg.goto(url, timeout=RENDER_TIMEOUT_MS, wait_until="domcontentloaded")
            try:
                pg.wait_for_load_state("networkidle", timeout=RENDER_TIMEOUT_MS // 2)
            except Exception:
                pass
            return pg.content().encode("utf-8")
        finally:
            b.close()


def crossref_title(doi: str) -> str | None:
    import requests
    import find_access as FA
    try:
        r = requests.get("https://api.crossref.org/works/" + urllib.parse.quote(doi), params={"mailto": FA.MAIL},
                         timeout=30)
        return ((r.json().get("message") or {}).get("title") or [None])[0] if r.status_code == 200 else None
    except Exception:
        return None


def crossref_abstract(doi: str) -> str | None:
    import requests
    import find_access as FA
    try:
        r = requests.get("https://api.crossref.org/works/" + urllib.parse.quote(doi), params={"mailto": FA.MAIL},
                         timeout=30)
        a = (r.json().get("message") or {}).get("abstract") if r.status_code == 200 else None
    except Exception:
        return None
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", a)).strip() if a else None


def epmc_record(ids: dict) -> dict | None:
    import find_access as FA
    for field, key in (("PMCID", "pmcid"), ("EXT_ID", "pmid"), ("DOI", "doi")):
        if key in ids:
            rec = FA.epmc(ids[key], field)
            time.sleep(1)
            if rec:
                return rec
    return None


def unpaywall_record(doi: str) -> dict | None:
    import find_access as FA
    up = FA.unpaywall(doi)
    time.sleep(1)
    return up


NET = {"get": http_get, "render": render, "crossref_doi": V2.crossref_doi, "crossref_title": crossref_title,
       "crossref_abstract": crossref_abstract, "epmc": epmc_record, "unpaywall": unpaywall_record}


# --------------------------------------------------------------------------
# One copy: fetched under §10.3 (d), its text decided by snapshot.extent
# --------------------------------------------------------------------------

def fetch_copy(url: str, net: dict, log: list) -> tuple[bytes, str, str, str]:
    """(bytes, text, content type, final url) of a full-text or abstract copy; raises Refused."""
    import snapshot as SN
    a, b = barred(url)
    if a or b:
        raise Refused(R_BARRED, "barred publisher (%s): never fetched" % (a or b))
    ok, why, kind = robots_v3(url, net["get"])
    if not ok:
        raise Refused(kind, why)
    reserved, why_t = tdm_site(url, net["get"])
    if reserved:
        raise Refused(R_TDM, why_t)
    r = net["get"](url)
    log.append({"url": url, "status": r["status"], "final_url": r["final_url"]})
    a, b = barred(r["final_url"])
    if a or b:
        raise Refused(R_BARRED, "redirected to a barred publisher (%s): not used" % (a or b))
    if _challenge(r["status"], r["headers"], r["body"]):
        raise Refused(R_WALL, "challenge page (HTTP %d): not worked around" % r["status"])
    if r["status"] >= 400:
        raise Refused("HTTP error", "HTTP error (%d)" % r["status"])
    if tdm_page(r["headers"], r["body"]):
        raise Refused(R_TDM, "the page reserves text and data mining (tdm-reservation)")
    data = r["body"]
    text = SN.text_of(data)
    ext, why_e = SN.extent(url, data, text, r["content_type"])
    if ext == "unreachable" and "readable characters" in why_e and data[:5] != b"%PDF-":
        if _signin(r["final_url"], data):
            raise Refused(R_SIGNIN, "sign-in or paywall page")
        log.append({"url": url, "render_because": why_e, "bytes": len(data)})
        try:
            data = net["render"](url)
        except Exception as e:
            raise Refused(R_CONN, "rendering failed: %s" % str(e)[:120])
        log.append({"url": url, "rendered": True})
        if _challenge(200, {}, data):
            raise Refused(R_WALL, "challenge page after rendering: not worked around")
        if tdm_page({}, data):
            raise Refused(R_TDM, "the rendered page reserves text and data mining")
        text = SN.text_of(data)
        ext, why_e = SN.extent(url, data, text, "text/html")
    if ext == "unreachable":
        if "bot wall" in why_e:
            raise Refused(R_WALL, why_e)
        if _signin(r["final_url"], data):
            raise Refused(R_SIGNIN, "sign-in or paywall page")
        raise Refused(R_NOCOPY, "no readable text: " + why_e)
    return data, text, ext, r["final_url"]


# --------------------------------------------------------------------------
# One cited address -> a manifest row (§10.3, steps 1-5)
# --------------------------------------------------------------------------
META_TITLE = re.compile(r"""<meta\s+[^>]*name\s*=\s*["']citation_title["'][^>]*content\s*=\s*["']([^"']+)["']""", re.I)
HTML_TITLE = re.compile(r"<title[^>]*>([^<]+)</title>", re.I)


def _page_title(html: str) -> str | None:
    m = META_TITLE.search(html or "") or HTML_TITLE.search(html or "")
    return m.group(1).strip() if m else None


def _no(u: str, kind: str, why: str, **kw) -> dict:
    return {"url": u, "extent": "unreachable", "extent_why": why, "why_kind": kind, "licence": None, **kw}


def _keep(u: str, work: Path, text: str, ext: str, rule: str, via: str, **kw) -> dict:
    import snapshot as SN
    sid = SN.source_id(u)
    (work / "sources").mkdir(parents=True, exist_ok=True)
    (work / "sources" / (sid + ".txt")).write_text(text, encoding="utf-8")
    return {"url": u, "source_id": sid, "extent": ext, "abstract_only": ext == "abstract only", "rule": rule,
            "retrieved_from": via, **kw}


def _locations(ids: dict, rec: dict | None, up: dict | None) -> list[dict]:
    """Open copies of the work: Europe PMC full text, Europe PMC free links, Unpaywall locations; each with
    the rule that could admit it and the licence it carries."""
    out = []
    if rec and rec.get("pmcid") and rec.get("inEPMC") == "Y":
        out.append({"url": "https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % rec["pmcid"],
                    "repository": True, "licence": rec.get("license"), "via": "Europe PMC full text"})
    for u in ((rec or {}).get("fullTextUrlList") or {}).get("fullTextUrl") or []:
        if (u.get("availability") or "").lower() in ("free", "open access") and u.get("url"):
            out.append({"url": u["url"], "repository": is_repository(u["url"]), "licence": (rec or {}).get("license"),
                        "via": "Europe PMC link (%s)" % u.get("site")})
    for loc in (up or {}).get("oa_locations") or []:
        for u in (loc.get("url_for_pdf"), loc.get("url")):
            if u:
                out.append({"url": u, "repository": loc.get("host_type") == "repository" or is_repository(u),
                            "licence": loc.get("license"), "via": "Unpaywall (%s)" % loc.get("host_type")})
    seen, keep = set(), []
    for l in out:
        if l["url"] not in seen:
            seen.add(l["url"])
            keep.append(l)
    return keep


def source_v3(u: str, title: str | None, work: Path, net: dict) -> dict:
    log: list = []
    hard, cc_only = barred(u)
    if hard:                                                           # step 1: before any request
        return _no(u, R_BARRED, "barred publisher (%s): never fetched" % hard)
    first_refusal: Refused | None = None
    page, page_tried = None, False                                     # the cited address, fetched once
    held_abstract, unconfirmed_doi = None, None
    ids, how = V2.ids_v2(u), "from the address"
    if not ids and not cc_only and not is_repository(u):
        page_tried = True
        try:
            page = fetch_copy(u, net, log)
        except Refused as e:
            first_refusal = e
        html = page[0].decode("utf-8", "replace") if page and page[0][:5] != b"%PDF-" else ""
        d = V2.doi_from_meta(html) if html else None
        if d:                                                          # step 2: a meta DOI, checked
            want = title or _page_title(html)
            got = net["crossref_title"](d) if want else None
            if want and got and _agree(want, got):
                ids, how = {"doi": d}, "landing page meta, Crossref title agrees"
            else:                                                      # a journal page all the same
                unconfirmed_doi = d
                log.append({"meta_doi_rejected": d, "title": want, "crossref_title": got})
    if not ids and title and page is None and not unconfirmed_doi:
        # only when the cited page was not read: a page that was read and names no DOI is a web page, and
        # a loose title match (v2: a UN report given a journal's DOI) must not turn it into a journal work
        d, why = net["crossref_doi"](title)                            # v2's lookup: titles_agree inside
        if d:
            ids, how = {"doi": d}, why
    doi = (ids or {}).get("doi")
    hard2, cc2 = barred(u, doi)
    if hard2:
        return _no(u, R_BARRED, "barred publisher (%s, DOI %s): never fetched" % (hard2, doi), ids=ids, log=log)
    cc_only = cc_only or cc2
    base = {"ids": ids, "ids_how": how if ids else None, "log": log}

    # step 3: the cited address
    rec = up = None
    if ids:
        rec = net["epmc"](ids)
        doi = doi or (rec or {}).get("doi")
        up = net["unpaywall"](doi) if doi else None
    if not cc_only:
        if is_repository(u):
            rule, admitted = RULE_A, True
        elif ids:
            lic = (rec or {}).get("license") if V1.is_open((rec or {}).get("license")) else next(
                (l.get("license") for l in (up or {}).get("oa_locations") or [] if V1.is_open(l.get("license"))), None)
            rule, admitted = RULE_B, bool(lic)
            base["licence"] = lic
            if not admitted:
                first_refusal = first_refusal or Refused(R_NOLICENCE, "publisher copy without a Creative Commons licence")
        elif unconfirmed_doi:
            rule, admitted = RULE_B, False
            first_refusal = first_refusal or Refused(
                R_NOLICENCE, "a journal page (citation_doi %s, not confirmed by its title): no licence could be read"
                % unconfirmed_doi)
        else:
            rule, admitted = RULE_C, True
        if admitted:
            try:
                if page_tried and page is None:
                    raise first_refusal or Refused(R_NOCOPY, "no copy found")
                got = page or fetch_copy(u, net, log)
                if got[2] == "full text" or not ids:
                    return {**base, **_keep(u, work, got[1], got[2], rule, got[3])}
                held_abstract = got                                    # an abstract on the cited page
            except Refused as e:
                first_refusal = first_refusal or e
    else:
        first_refusal = Refused(R_BARRED, "barred publisher (%s): read only from an open copy with a CC licence" % cc_only)

    # step 4: an open copy of the same work
    for loc in _locations(ids or {}, rec, up) if ids else []:
        if loc["url"].split("#")[0] == u:
            continue
        a, b = barred(loc["url"])
        if a or b:
            continue
        if cc_only and not V1.is_open(loc["licence"]):
            continue
        if not loc["repository"] and not V1.is_open(loc["licence"]):
            log.append({"skipped": loc["url"], "why": R_NOLICENCE})
            continue
        try:
            data, text, ext, final = fetch_copy(loc["url"], net, log)
        except Refused as e:
            log.append({"skipped": loc["url"], "why": e.why})
            continue
        if ext == "full text":
            return {**base, **_keep(u, work, text, ext, RULE_A if loc["repository"] else RULE_B, loc["url"],
                                    licence=loc["licence"], version_via=loc["via"])}

    # step 5: the abstract (not for a barred publisher's work)
    if ids and not cc_only:
        ab = (rec or {}).get("abstractText")
        ab = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", ab)).strip() if ab else None
        via = "Europe PMC abstractText"
        if not ab and doi:
            ab, via = net["crossref_abstract"](doi), "Crossref abstract"
        if ab and len(ab) >= 200:
            t = ("%s\n\n%s" % ((rec or {}).get("title") or "", ab)).strip()
            return {**base, **_keep(u, work, t, "abstract only", RULE_ABS, via)}
        if held_abstract:
            return {**base, **_keep(u, work, held_abstract[1], "abstract only", RULE_ABS, held_abstract[3])}
    e = first_refusal or Refused(R_NOCOPY, "no copy found")
    return {**base, **_no(u, e.kind, e.why)}


def _agree(a: str, b: str) -> bool:
    import find_access as FA
    return FA.titles_agree(a, b)[0]


def snapshots_v3(claims: list[dict], work: Path, titles: dict, net: dict, workers: int = 8) -> dict:
    """{url: manifest row}, one row per distinct address; addresses on one host one at a time."""
    urls = list(dict.fromkeys(ct["url"] for c in claims for ct in c["citations"] if ct.get("url")))
    by_host: dict = {}
    for u in urls:
        by_host.setdefault(V2.host(u), []).append(u)
    man: dict = {}

    def one_host(us):
        for u in us:
            t0 = time.time()
            try:
                row = source_v3(u, titles.get(u), work, net)
            except Exception as e:                                     # a finding, not a crash
                row = _no(u, R_CONN, "error: %s" % str(e)[:160])
            row["seconds"] = round(time.time() - t0, 2)
            man[u] = row

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one_host, by_host.values()))
    (work / "sources").mkdir(parents=True, exist_ok=True)
    (work / "sources" / "manifest.json").write_text(json.dumps([man[u] for u in urls], indent=1, default=str))
    return {u: man[u] for u in urls}


# --------------------------------------------------------------------------
# §10.1 the passage
# --------------------------------------------------------------------------

def _find(span: str, text: str) -> int | None:
    """Offset of SPAN in TEXT, compared as judge_m1.norm compares them."""
    i = text.find(span)
    if i >= 0:
        return i
    ns = J.norm(span)
    if not ns:
        return None
    # map normalised positions back: normalise word by word
    words = list(re.finditer(r"\S+", text))
    target = ns.split()
    nw = [J.norm(w.group(0)) for w in words]
    for k in range(len(nw) - len(target) + 1):
        if nw[k:k + len(target)] == target:
            return words[k].start()
    return J.norm(text).find(ns) if ns in J.norm(text) else None


def location(text: str, at: int, pdf: bool) -> str:
    before = text[:at]
    if pdf and "\f" in text:
        return "page %d" % (before.count("\f") + 1)
    paras = [p for p in re.split(r"\n\s*\n", before)]
    heading = None
    for line in reversed(before.splitlines()):
        s = line.strip()
        if 3 <= len(s) <= 120 and not s.endswith(".") and (s.isupper() or s.istitle() or s.startswith("#")
                                                           or len(s.split()) <= 8):
            heading = s.lstrip("# ").strip()
            break
    return ("under \"%s\", paragraph %d" % (heading, len(paras))) if heading else "paragraph %d" % len(paras)


def text_fragment(url: str, quote: str) -> str:
    w = quote.replace("...", " ").split()
    if not w:
        return url
    q = urllib.parse.quote
    frag = q(" ".join(w[:4]), safe="") + ("," + q(" ".join(w[-4:]), safe="") if len(w) > 8 else "")
    return url.split("#")[0] + "#:~:text=" + frag


def passage(span: str, docs: list[dict]) -> dict | None:
    """{quote, words, location, link, source} for SPAN in the first document holding it, or None."""
    span = (span or "").strip()
    if not span:
        return None
    for d in docs:
        at = _find(span, d["text"])
        if at is None:
            continue
        words = span.split()
        quote = " ".join(words[:PASSAGE_MAX_WORDS]) + (" ..." if len(words) > PASSAGE_MAX_WORDS else "")
        link_to = d.get("retrieved_from") or d["url"]
        return {"quote": quote, "words": min(len(words), PASSAGE_MAX_WORDS), "location": location(
            d["text"], at, str(link_to).lower().endswith(".pdf") or "\f" in d["text"]),
            "link": text_fragment(link_to if str(link_to).startswith("http") else d["url"], quote),
            "source": d["url"]}
    return None


# --------------------------------------------------------------------------
# Judge, in parallel; then passages, sub-kinds and reasons
# --------------------------------------------------------------------------

def _reason_kind(r: dict, man: dict) -> str | None:
    if r["label"] != COULDNT:
        return None
    why = r.get("reason") or ""
    if "refused" in why:
        return R_REFUSED
    if "did not parse" in why:
        return R_UNPARSED
    if "only the abstract could be read" in why:
        return R_ABSTRACT
    if why.startswith("no passage"):
        return R_NOPASSAGE
    for ct in r["citations"]:
        if not ct.get("url"):
            return R_MARKER
        m = man.get(ct["url"]) or {}
        if m.get("extent") == "unreachable":
            k = m.get("why_kind") or R_NOCOPY
            return "HTTP error" if k.startswith("HTTP error") else k
    return R_DELIVERY


def plan_v3(claims: list[dict], man: dict, work: Path, count, workers: int = 8) -> list[dict]:
    """v1's plan, a claim at a time in parallel (count_tokens calls are the slow part)."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return [p for ps in ex.map(lambda c: V1.plan([c], man, work, count), claims) for p in ps]


def judge_v3(planned: list[dict], man: dict, work: Path, client, before_call=None, workers: int = 8) -> list[dict]:
    """v1's judge, one claim per thread; before_call is held under a lock so cap checks do not race."""
    V1.prompt_ok()
    lock = threading.Lock()

    def guarded(worst):
        if before_call:
            with lock:
                before_call(worst)

    docs_of = {id(p): p.get("docs") or [] for p in planned}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [(p, ex.submit(V1.judge, [p], client, guarded)) for p in planned]
        results = []
        for p, f in futs:
            r = f.result()[0]
            results.append(finish(r, docs_of[id(p)], man))
    return results


def finish(r: dict, docs: list[dict], man: dict) -> dict:
    """§10.1 and §10.2 on one judged row: the passage (or COULDN'T CHECK), the sub-kind, the reason."""
    r = dict(r)
    for d in docs:
        d.setdefault("retrieved_from", (man.get(d["url"]) or {}).get("retrieved_from"))
    if r["label"] in (BACKED, NOT_BACKED):
        p = passage(r.get("span") or "", docs)
        if p is None:
            r.update(label=COULDNT, verdict_withheld=r["label"],
                     reason="no passage to show: the judge's quotation was %s" % (
                         "empty" if not (r.get("span") or "").strip() else "not found in the text judged"))
        else:
            r["passage"] = p
            if any(d.get("abstract_only") for d in docs):
                r["kind"] = ABSTRACT_ONLY
    r["reason_kind"] = _reason_kind(r, man)
    return r


# --------------------------------------------------------------------------
# §10.5 a passage the user supplies
# --------------------------------------------------------------------------

def check_supplied(claim: dict, text: str, url: str, client, count, before_call=None) -> dict:
    """Judge one claim against a passage the user pasted, and nothing else. Nothing is written."""
    words = (text or "").split()
    if not words:
        raise ValueError("no passage")
    if len(words) > SUPPLIED_MAX_WORDS:
        raise ValueError("the passage has %d words; at most %d" % (len(words), SUPPLIED_MAX_WORDS))
    if not str(url or "").startswith(("http://", "https://")):
        raise ValueError("the source link must be an http(s) address")
    doc = {"source_id": "supplied", "url": url, "extent": "passage supplied by the user", "abstract_only": False,
           "tokens": count(text), "chunked": False, "text": text}
    c = {k: claim[k] for k in ("idx", "claim", "context", "citations") if k in claim}
    c.setdefault("context", "")
    prefix, rest = J.build(c, [doc])
    n_in = count(prefix + rest)
    planned = [{**c, "label": None, "docs": [doc], "prefix": prefix, "rest": rest, "n_in": n_in,
                "worst": V1.worst_cost(n_in)}]
    r = finish(V1.judge(planned, client, before_call)[0], [doc], {})
    r.pop("attempts", None)                                            # the raw reply quotes the passage
    if r["label"] in (BACKED, NOT_BACKED):
        r["kind"] = SUPPLIED
    r["notice"] = SUPPLIED_NOTICE
    return r


# --------------------------------------------------------------------------
# Whole answer
# --------------------------------------------------------------------------

def summary(results: list[dict], found: int) -> str:
    t = {k: sum(r["label"] == k for r in results) for k in LABELS}
    abs_ = sum(r.get("kind") == ABSTRACT_ONLY for r in results)
    return ("%d of %d claims checked: %d BACKED, %d NOT BACKED, %d NO SOURCE, %d COULDN'T CHECK"
            "%s." % (len(results), found, t[BACKED], t[NOT_BACKED], t[NO_SOURCE], t[COULDNT],
                     ("; %d %s" % (abs_, ABSTRACT_ONLY)) if abs_ else ""))


def prepare(text: str, work: Path, fmt: str | None = None, count=None, system: str = "answer",
            net: dict | None = None, selected: list[int] | None = None, max_claims: int = V1.MAX_CLAIMS) -> dict:
    """Steps before the first model call: adapt, sentences, ranked claims, copies, plan (count_tokens only)."""
    n = {**NET, **(net or {})}
    md, cited, fmt = adapt_answer(text, fmt)
    rows, refs = V1.sentences(md, cited, work, system)
    claims, beyond, found = claims_v3(rows, refs, selected, max_claims)
    man = snapshots_v3(claims, work, V2.titles_from(text), n)
    planned = plan_v3(claims, man, work, count)
    return {"format": fmt, "rows": rows, "refs": refs, "claims": claims, "beyond_limit": beyond, "found": found,
            "manifest": man, "planned": planned, "version": 3,
            "worst_usd": round(sum(p.get("worst") or 0 for p in planned), 4),
            "calls": sum(1 for p in planned if p["label"] is None)}


def check(text: str, work: Path, client, count, fmt: str | None = None, system: str = "answer",
          net: dict | None = None, selected: list[int] | None = None, before_call=None) -> dict:
    t0 = time.time()
    prep = prepare(text, work, fmt, count, system, net, selected)
    results = judge_v3(prep["planned"], prep["manifest"], work, client, before_call)
    return {**{k: v for k, v in prep.items() if k != "planned"}, "results": results,
            "summary": summary(results, prep["found"]), "seconds": round(time.time() - t0, 1)}


def public(results: list[dict], man: dict) -> list[dict]:
    """What a reader is shown per claim: label, sub-kind, reason, the passage and the source links."""
    out = []
    for r in results:
        out.append({"idx": r["idx"], "claim": r["claim"], "label": r["label"], "kind": r.get("kind"),
                    "reason": r["reason"], "reason_kind": r.get("reason_kind"), "passage": r.get("passage"),
                    "sources": [{"url": ct["url"], "rule": (man.get(ct["url"]) or {}).get("rule")}
                                for ct in r["citations"] if ct.get("url")]})
    return out
