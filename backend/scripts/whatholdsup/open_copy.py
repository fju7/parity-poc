"""Open copies of a source whose own copy could not be held (advisor's ruling on P107, 2026-11-25).

Found on orchestrator trial 1 attempt 24 (WHU-OT1-02za): S002's publisher copy answered HTTP 403 (a wall), and the
orchestrated acquire tried nothing else, although a permitted open copy exists in a repository (eScholarship,
CC BY-NC-ND, listed by OpenAlex). Ruled: the orchestrated acquire runs the open-copy routes, so a walled publisher
copy falls back to a permitted open copy; licence and robots/TDM checks run BEFORE any fetch; never past a wall; an
honest user agent.

  * WHERE THE IDENTIFIER COMES FROM: only the source's own `doi` in sources.json, which the confirm step took from a
    registry record (never a searched or typed one: find_access.py's lesson of 2026-09-01).
  * THE LOOKUP: OpenAlex's work record for that DOI (keyless; no email is sent -- find_access.py's Unpaywall route
    sends one, so it is not used here). Its `locations` are the candidates.
  * THE COPY RULE, before any fetch: a repository copy that is free to read (rule a), or any other copy only with a
    Creative Commons licence (rule b). A copy on the host that already refused, or a doi.org landing (it leads back
    to the publisher), is skipped. Each candidate's licence and version are recorded as OpenAlex states them.
  * ROBOTS AND TDM, before the document is fetched: the host's robots.txt must allow it (a 401/403/429 there, or an
    HTML page in its place, is a wall: the copy is refused); /.well-known/tdmrep.json must reserve nothing for the
    path; and the fetched page's own tdm-reservation header or meta tag refuses it after the fact (its bytes unused).
  * NEVER PAST A WALL: a 401/403/429 at any step ends that copy; nothing is retried with other headers.
  * The bytes are then held only if source_store.held_check identifies them as the document, as for any copy.
  * An OpenAlex that does not answer (after the retries) is an outage, not evidence of absence: the caller records
    it as registry unavailable, and the orchestrator stops the run ("registry unavailable; run again later").
"""
from __future__ import annotations

import fnmatch
import json
import re
import urllib.error
import urllib.parse
import urllib.robotparser

OPENALEX = "https://api.openalex.org/works/https://doi.org/%s"
ROUTE = "open copy via OpenAlex"
AGENT = "WHU-fetch"                      # the product token of tls.USER_AGENT, for robots.txt
WALL_CODES = (401, 403, 429)


class Unavailable(Exception):
    """OpenAlex (or a copy's host) did not answer after the retries: not evidence of absence."""


def _host(url: str) -> str:
    return (urllib.parse.urlsplit(url or "").hostname or "").lower()


def _origin(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    return "%s://%s" % (p.scheme, p.netloc)


def lookup(doi: str, fetch) -> dict | None:
    """OpenAlex's work record for DOI, or None if it has none (404). Raises Unavailable if it does not answer."""
    url = OPENALEX % urllib.parse.quote(doi.strip().lower(), safe="/")
    try:
        data, _ct, _final = fetch(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise Unavailable("OpenAlex HTTP %s for %s" % (e.code, doi))
    except Exception as e:
        raise Unavailable("OpenAlex %s for %s" % (type(e).__name__, doi))
    try:
        return json.loads(data.decode("utf-8", "replace"))
    except ValueError:
        raise Unavailable("OpenAlex answered with no JSON for %s" % doi)


def candidates(record: dict, refused_hosts: set) -> list[dict]:
    """Every location OpenAlex lists, each with whether the copy rule permits it and why (none fetched yet)."""
    out = []
    for loc in (record or {}).get("locations") or []:
        src = loc.get("source") or {}
        url = loc.get("pdf_url") or loc.get("landing_page_url") or ""
        lic = loc.get("license")
        row = {"where": src.get("display_name") or _host(url) or "unnamed location",
               "host_type": src.get("type"), "url": url, "version": loc.get("version"),
               "is_oa": bool(loc.get("is_oa")), "licence": lic or "none stated",
               "licence_from": "OpenAlex location record"}
        if not url:
            row.update(permitted=False, why="no URL")
        elif not row["is_oa"]:
            row.update(permitted=False, why="not free to read (OpenAlex is_oa false)")
        elif _host(url) == "doi.org" or _host(url) in refused_hosts:
            row.update(permitted=False, why="the copy that was already refused (%s)" % _host(url))
        elif src.get("type") == "repository":
            row.update(permitted=True, why="a repository copy, free to read (copy rule a)")
        elif str(lic or "").lower().startswith("cc"):
            row.update(permitted=True, why="a copy under a Creative Commons licence, %s (copy rule b)" % lic)
        else:
            row.update(permitted=False, why="not a repository copy and no Creative Commons licence (%s)" % (lic or
                                                                                                            "none"))
        out.append(row)
    return out


def _looks_html(data: bytes) -> bool:
    head = (data or b"")[:400].lstrip().lower()
    return head.startswith(b"<!doctype") or head.startswith(b"<html") or b"<html" in head


def robots(url: str, fetch) -> tuple[bool, str]:
    """(allowed, why), read BEFORE the copy is fetched. A wall in place of robots.txt refuses the copy."""
    where = _origin(url) + "/robots.txt"
    try:
        data, ct, _final = fetch(where)
    except urllib.error.HTTPError as e:
        if e.code in WALL_CODES:
            return False, "robots.txt answered HTTP %d: a wall, not passed" % e.code
        if e.code in (404, 410):
            return True, "no robots.txt (HTTP %d)" % e.code
        return False, "robots.txt could not be read (HTTP %d)" % e.code
    except Exception as e:
        return False, "robots.txt could not be read (%s)" % type(e).__name__
    if "html" in (ct or "").lower() or _looks_html(data):
        return False, "robots.txt answered with an HTML page (a challenge or error page): a wall, not passed"
    rp = urllib.robotparser.RobotFileParser()
    rp.parse((data or b"").decode("utf-8", "replace").splitlines())
    ok = rp.can_fetch(AGENT, url)
    return ok, "robots.txt %s it" % ("allows" if ok else "disallows")


def tdm_site(url: str, fetch) -> tuple[bool, str]:
    """(reserved, why) from the host's /.well-known/tdmrep.json (W3C TDMRep), read BEFORE the copy is fetched."""
    where = _origin(url) + "/.well-known/tdmrep.json"
    try:
        data, _ct, _final = fetch(where)
    except urllib.error.HTTPError as e:
        if e.code in WALL_CODES:
            return True, "tdmrep.json answered HTTP %d: a wall, not passed" % e.code
        return False, "no tdmrep.json (HTTP %d)" % e.code
    except Exception as e:
        return True, "tdmrep.json could not be read (%s): not fetched" % type(e).__name__
    try:
        rules = json.loads((data or b"").decode("utf-8", "replace"))
    except ValueError:
        return False, "tdmrep.json is not JSON: no reservation read"
    path = urllib.parse.urlsplit(url).path or "/"
    for e in rules if isinstance(rules, list) else []:
        if not isinstance(e, dict):
            continue
        loc = str(e.get("location") or "")
        pat = loc if loc.startswith("/") else "/" + loc
        if fnmatch.fnmatchcase(path, pat):
            if str(e.get("tdm-reservation")) == "1":
                return True, "tdmrep.json reserves %s" % loc
            return False, "tdmrep.json: no reservation for %s" % loc
    return False, "no TDM reservation in tdmrep.json"


META_TDM = re.compile(r"""<meta\s+[^>]*name\s*=\s*["']tdm-reservation["'][^>]*content\s*=\s*["']\s*1\s*["']|"""
                      r"""<meta\s+[^>]*content\s*=\s*["']\s*1\s*["'][^>]*name\s*=\s*["']tdm-reservation["']""", re.I)


def tdm_page(data: bytes) -> bool:
    return bool(META_TDM.search((data or b"")[:60000].decode("utf-8", "replace")))


def find(src: dict, refused_url: str, fetch, held_check) -> dict:
    """Try the permitted open copies of SRC in OpenAlex's order. FETCH(url) -> (bytes, content type, final url),
    raising urllib errors (the caller's honest, retrying client). HELD_CHECK(bytes, content type) -> (ok, check).
    Returns {"record": what was looked up, found and tried, for sources.json; "data", "ct", "final", "check",
    "copy" when a copy is held; "unavailable": True on an outage}."""
    doi = str(src.get("doi") or "").strip()
    rec = {"route": ROUTE, "doi": doi or None, "found": [], "tried": []}
    if not doi:
        rec["outcome"] = "no DOI recorded for this source: nothing looked up (nothing is ever guessed)"
        return {"record": rec}
    try:
        work = lookup(doi, fetch)
    except Unavailable as e:
        rec["outcome"] = "OpenAlex did not answer (%s): not evidence of absence" % e
        return {"record": rec, "unavailable": True}
    if work is None:
        rec["outcome"] = "OpenAlex has no record of %s" % doi
        return {"record": rec}
    rec["found"] = candidates(work, {_host(refused_url)} if refused_url else set())
    for c in rec["found"]:
        if not c["permitted"]:
            continue
        step = {"url": c["url"], "where": c["where"]}
        rec["tried"].append(step)
        ok, why = robots(c["url"], fetch)
        step["robots"] = why
        if not ok:
            step["result"] = "not fetched: %s" % why
            continue
        reserved, why = tdm_site(c["url"], fetch)
        step["tdm"] = why
        if reserved:
            step["result"] = "not fetched: %s" % why
            continue
        try:
            data, ct, final = fetch(c["url"])
        except urllib.error.HTTPError as e:
            step["result"] = ("HTTP %d: a wall, not passed" % e.code) if e.code in WALL_CODES else \
                "HTTP %d" % e.code
            continue
        except Exception as e:
            step["result"] = "%s" % type(e).__name__
            continue
        if tdm_page(data):
            step["result"] = "the page reserves text and data mining (tdm-reservation): its bytes are not used"
            continue
        held, check = held_check(data, ct)
        if not held:
            step["result"] = "not the document: %s" % check.get("why")
            continue
        step["result"] = "held"
        rec["outcome"] = "held from %s" % c["where"]
        return {"record": rec, "data": data, "ct": ct, "final": final, "check": check, "copy": c}
    permitted = [c for c in rec["found"] if c["permitted"]]
    rec["outcome"] = ("no permitted open copy listed" if not permitted else
                      "%d permitted open cop%s listed, none could be held" % (len(permitted),
                                                                              "y" if len(permitted) == 1 else "ies"))
    return {"record": rec}
