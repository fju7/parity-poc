#!/usr/bin/env python3
"""Acquire every source document this issue is written from, and hold it.

WHY IT RUNS HERE AND NOT IN THE ASSISTANT'S ENVIRONMENT
-------------------------------------------------------
This runs on the operator's machine, with the operator's own network and
access. That is not a workaround, it is the right architecture: the assistant's
retrieval tools return a MODEL'S SUMMARY of a page, not the page. A summary is
what we have been mistaking for a source all week -- it is how our own
observation ended up published under Tanguy's name, and how the Shaaban paper's
own "29 blocks with block size of four" got deleted from the page as if we had
made the number up.

You cannot check a sentence against a summary. You can only check it against
bytes you hold.

WHAT IT DOES
------------
For every source in the issue's sources.json:

  * fetches the URL, follows redirects, and stores the bytes under its source id
  * records the sha256, the size, the content type, the date and the route
  * promotes the ledger entry to full_text_held ONLY when bytes are actually held

and for everything it cannot get, prints a HUMAN SEARCH LIST: what is missing,
what we currently say we know about it, and what the ledger will permit until
somebody puts a copy in the store.

WHAT IT REFUSES TO DO
---------------------
It will not touch a source marked `licence_forbids_machine_reading`. NCCN's
licence forbids putting the guideline through any automated tool, so it can
never be held here and never machine-read. Its ceiling is human_read: a person
opens it and answers specific recorded questions, which is exactly how issue
two's NCCN claims were established.

It also does not judge what it got. A 403 page, a cookie wall and a real PDF are
all "bytes". Every response must pass source_store.held_check -- it identifies
itself, the substance check `source_store add` records finds the document for
the source's form, and its title is in the visible text -- or it is not
fetched, with the reason in the ledger entry's last_fetch (2026-10-22: a
publisher redirect page had been recorded as a corrigendum's full text).
Everything that passes is still only a candidate until somebody looks. A
store full of paywall notices is worse than an empty one, because it would
report full_text_held.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import source_store as store          # noqa: E402
import tls                             # noqa: E402

UA = {"User-Agent": tls.USER_AGENT,       # ruling A: generic automated client, never a browser string
      "Accept": "text/html,application/pdf,application/json;q=0.9,*/*;q=0.8"}

# A DOCUMENT IS ACCEPTED BECAUSE IT IDENTIFIES ITSELF, NOT BECAUSE IT FAILED TO
# LOOK LIKE A WALL.
#
# The first version of this file rejected responses by a blocklist -- "captcha",
# "subscribe to continue", "enable javascript". Within the hour of being written
# it stored TWO PubMed cookie-consent pages as full text, promoted both to
# full_text_held, and reported success, because "cookies required" was not a
# phrase anyone had been caught by yet.
#
# A blocklist can only refuse what has already gone wrong once. That is the same
# correction this project has now made in four places, and it is the same
# sentence every time: confirm the thing you want, do not merely fail to detect
# the thing you fear. source_store.identifies() asks whether the bytes contain
# the document's DOI, PMID, NCT number, or enough of its title.

# Registry records are a JS application at clinicaltrials.gov/study/NCT..., which
# fetches as an empty shell. The document is the API record, and it is also the
# only form of it we can check a claim against.
def acquisition_url(src: dict) -> str:
    url = (src.get("url") or "").strip()
    m = re.search(r"clinicaltrials\.gov/study/(NCT\d{8})", url, re.I)
    if m:
        return ("https://clinicaltrials.gov/api/v2/studies/%s?format=json"
                % m.group(1).upper())
    m = re.search(r"(?:pmc\.ncbi\.nlm\.nih\.gov|europepmc\.org)[^ ]*?(PMC\d{6,9})",
                  url, re.I)
    if m:
        return ("https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML"
                % m.group(1).upper())
    return url


# THE ASSESSMENT-SUMMARY RULE (post-study fix 3, 2026-10-27; the advisor's
# option 4 of docs/whu-omissions-investigation-2026-10.md). An issue that holds a
# chapter of an assessment report also holds that report's Summary for
# Policymakers: the judgements a reader would be told are the assessment's
# conclusions live there (WHU-S08 held WGII Chapter 6, and its answer key's
# conclusions sit in the WGII SPM, which nobody fetched). Detected from the
# chapter's URL on the publisher's own site, not its title (S08's title has no
# "Chapter"). IPCC AR6 WGII and WGIII only, to begin with: both SPM URLs are the
# ones this repository already holds (WHU-S04, WHU-S07); WGI's is not recorded
# here and is not guessed.
AR6_CHAPTER = re.compile(r"^https?://(?:www\.)?ipcc\.ch/report/ar6/(wg2|wg3)/downloads/report/"
                         r"IPCC_AR6_WGI{2,3}_Chapter\d+\.pdf$", re.I)
AR6_SPM = {
    "wg2": ("https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_SummaryForPolicymakers.pdf",
            "IPCC 2022. Summary for Policymakers. In: Climate Change 2022: Impacts, Adaptation and "
            "Vulnerability (AR6 WGII)"),
    "wg3": ("https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_SPM.pdf",
            "IPCC 2022. Summary for Policymakers. In: Climate Change 2022: Mitigation of Climate Change "
            "(AR6 WGIII)"),
}
SUMMARY_LICENCE = {
    "note": ("IPCC terms (https://www.ipcc.ch/copyright/): personal, non-commercial download and "
             "copying permitted; short excerpts may be quoted with the full report name. A note, "
             "not a legal opinion."),
    "terms": "https://www.ipcc.ch/copyright/",
    "terms_summary_by": "Fred's advisor (Claude), 2026-10-27",
    "machine_reading": "not forbidden by any recorded licence",
    "terms_checked": False,          # this script does not read the terms page itself
}
ADDED_BY = "acquire_sources.py: assessment-summary rule (post-study fix 3)"


def _next_id(srcs: list[dict]) -> str:
    n = max([int(m.group(1)) for s in srcs for m in [re.match(r"^S(\d+)$", s.get("id") or "")] if m] or [0])
    return "S%03d" % (n + 1)


def summaries_to_add(srcs: list[dict], today: str = "") -> list[dict]:
    """sources.json entries for the SPM of every AR6 WGII/WGIII chapter held,
    unless that SPM's URL is already a source. Writes nothing."""
    have = {(s.get("url") or "").strip().lower() for s in srcs}
    out: list[dict] = []
    for s in srcs:
        m = AR6_CHAPTER.match((s.get("url") or "").strip())
        if not m:
            continue
        url, title = AR6_SPM[m.group(1).lower()]
        if url.lower() in have:
            continue
        have.add(url.lower())
        out.append({"id": _next_id(srcs + out), "type": "synthesis", "form": "article", "title": title,
                    "url": url, "used_for": "the assessment's Summary for Policymakers, for the chapter(s) held "
                    "(%s); read by the coverage and assessment-judgement checks" % s.get("id"),
                    "added_by": ADDED_BY, "added_for": s.get("id"), "licence": dict(SUMMARY_LICENCE),
                    "access": {"state": "not_opened", "on": today, "by": ADDED_BY}})
    return out


ROBOTS_UNKNOWN = "robots.txt unknown"


def robots_allow(url: str, agent: str = "*") -> tuple[bool, str]:
    """robots.txt of the URL's host, read before fetching an added summary.

    Fetched with the same client and headers as the document (fetch(): tls.urlopen,
    UA). Post-study, mid-rerun tool fix (2026-10-28): RobotFileParser.read() used
    its own urllib client, and it reads a 401/403 as "disallow all" -- so a bot
    wall in front of robots.txt (WHU-S01r/S07r) read as the site forbidding every
    fetch. A robots.txt that does not come back is now UNKNOWN, said so, and the
    document goes through the normal fetch rules; a Disallow that is read is
    obeyed exactly as before."""
    import urllib.robotparser as rp
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    where = "%s://%s/robots.txt" % (parts.scheme, parts.netloc)
    try:
        data, _ct, _final = fetch(where, timeout=30)
    except urllib.error.HTTPError as e:
        return True, "%s (HTTP %s at %s): not read as disallowing; fetched under the normal rules" \
            % (ROBOTS_UNKNOWN, e.code, where)
    except Exception as e:
        return False, "robots.txt could not be read (%s): not fetched" % type(e).__name__
    r = rp.RobotFileParser(where)
    r.parse((data or b"").decode("utf-8", "replace").splitlines())
    ok = r.can_fetch(agent, url)
    return ok, "robots.txt %s it" % ("allows" if ok else "disallows")


def fetch(url: str, timeout: int = 45) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers=UA)
    with tls.urlopen(req, timeout=timeout) as r:      # completes a chain short of its intermediate
        return r.read(), r.headers.get("Content-Type", ""), r.geturl()


# A registry that times out or errors is retried in orchestrated runs (advisor's ruling 2 after attempt 11,
# 2026-11-23): 4 attempts in all, with backoff; still unavailable -> the fetch record says so and the
# orchestrator stops the run ("registry unavailable; run again later"), never treating it as not found.
FETCH_ATTEMPTS = 4
BACKOFF = (2, 4, 8)
_sleep = __import__("time").sleep


EPMC_FULLTEXT = re.compile(r"europepmc/webservices/rest/(PMC\d+)/fullTextXML", re.I)


def epmc_not_served(url: str, lookup=None, misses: list | None = None) -> str | None:
    """In an orchestrated run, before a Europe PMC full text is requested, its record's metadata is read
    (advisor's ruling after attempt 13). Returns the reason it is not requested, or None to request it. A
    metadata lookup that fails is an outage, which the run-wide wrapper records; the request then goes ahead (and,
    since the ruling after the fallback build, falls back to NCBI PMC). MISSES collects an unanswered lookup, so a
    fallback that answers can mark it covered."""
    m = EPMC_FULLTEXT.search(url or "")
    if not m or not os.environ.get("WHU_ORCH_STEP"):
        return None
    import errata as E
    if lookup is not None:
        rec, _why = lookup("PMCID", m.group(1))
    else:
        import registries as RG
        ans = RG.epmc_id("PMCID", m.group(1))      # the same request errata.lookup makes
        rec = ans.record
        if not ans.answered and misses is not None:
            misses.append(ans)
    if rec is not None and not E.epmc_full_text_served(rec):
        return "not served: Europe PMC metadata for %s says isOpenAccess %s (not requested)" % (
            m.group(1), rec.get("isOpenAccess"))
    return None


def pmc_fallback(url: str, misses: list, fetcher=None) -> tuple[bytes | None, str, str, dict]:
    """Europe PMC gave no full text at URL -- unavailable after the retries, a 4xx, or its metadata says not served
    (ruling 3 after P091) -- so NCBI PMC's copy through
    E-utilities, under Europe PMC's copy rule (registries.pmc_fulltext: the open-access body, with its licence
    statement; ruling 2 after the fallback build). Returns (bytes or None, content type, final URL, record). A PMC
    answer -- a copy, or "not served" -- covers the Europe PMC outages in MISSES; a PMC outage covers nothing."""
    import registries as RG
    m = EPMC_FULLTEXT.search(url or "")
    ans = (fetcher or RG.pmc_fulltext)(m.group(1))
    rec = {"route": "NCBI PMC (E-utilities efetch db=pmc)", "url": ans.url, "answered": ans.answered,
           "why": ans.why}
    if not ans.answered:
        return None, "", ans.url or "", rec
    for miss in misses:
        RG.covered(miss, ["PMC"])
    if ans.record is None:
        return None, "", ans.url, rec
    rec["licence"] = ans.record["licence"]
    return ans.record["xml"].encode("utf-8"), "application/xml", ans.url, rec


def transient(e: Exception) -> bool:
    """A failure that says nothing about the source: timeout, connection error, HTTP 5xx or 429."""
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500 or e.code == 429
    return isinstance(e, (TimeoutError, ConnectionError, urllib.error.URLError, OSError))


def fetch_retrying(url: str) -> tuple[bytes, str, str]:
    """fetch(), retried on a transient failure in an orchestrated run (WHU_ORCH_STEP set); once otherwise."""
    tries = FETCH_ATTEMPTS if os.environ.get("WHU_ORCH_STEP") and not os.environ.get("WHU_ORCH_UNAVAILABLE_LOG") else 1
    for i in range(tries):
        try:
            return fetch(url)
        except Exception as e:
            if i + 1 >= tries or not transient(e):
                raise
            _sleep(BACKOFF[min(i, len(BACKOFF) - 1)])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--only", help="comma-separated source ids")
    ap.add_argument("--refetch", action="store_true",
                    help="fetch even sources already in the store")
    ap.add_argument("--no-summaries", action="store_true",
                    help="do not add the Summary for Policymakers of an assessment chapter held "
                         "(post-study fix 3); the default adds it")
    ap.add_argument("--use-routes", action="store_true",
                    help="try the free routes find_access.py recorded, in order, "
                         "before the source's own url")
    ap.add_argument("--open-copies", action="store_true",
                    help="when a source's own copy cannot be held, try the permitted open copies OpenAlex lists for "
                         "its recorded DOI (open_copy.py: copy rule, robots.txt and TDM before any fetch, never past "
                         "a wall); the orchestrated acquire passes it (advisor's ruling on P107)")
    ap.add_argument("--out", help="also write this run's acquire record as JSON: every source held and every "
                                  "source not held with its reason (the orchestrator's proof of completion)")
    args = ap.parse_args(argv)
    case = store.case_dir(args.slug)

    # The free routes found by find_access.py. A publisher url that 403s a
    # script often has an open repository copy or a Europe PMC copy that does
    # not, and those are the SAME DOCUMENT -- the identity test decides that,
    # not the hostname.
    routes = {}
    if args.use_routes:
        rp = case / "access-routes.json"
        if rp.exists():
            for sid, r in (json.loads(rp.read_text(encoding="utf-8"))
                           .get("sources") or {}).items():
                # Repositories and Europe PMC first: they are archives, they do
                # not run bot detection, and a publisher 403 is what sent us
                # here in the first place.
                ordered = sorted(r.get("routes") or [],
                                 key=lambda x: (0 if ("PMC" in (x[0] or "")
                                                      or "repository" in (x[0] or ""))
                                                else 1))
                routes[sid] = [u for _s, _st, u in ordered if u]

    sp = case / "sources.json"
    doc = json.loads(sp.read_text(encoding="utf-8"))
    srcs = doc.get("sources", doc)
    only = {x.strip() for x in args.only.split(",")} if args.only else None
    have = store.library_held(args.slug)     # what is already fetched (a writer's view; blocked included)

    got, failed, skipped = [], [], []
    added = [] if args.no_summaries else summaries_to_add(srcs, store.utc_today())
    for e in added:
        srcs.append(e)
        print("  ADDED    %-6s %s (for %s)" % (e["id"], e["title"][:60], e["added_for"]))
    added_ids = {e["id"] for e in added} | {s.get("id") for s in srcs if s.get("added_by") == ADDED_BY}
    print()
    for s in srcs:
        sid, url = s.get("id"), (s.get("url") or "").strip()
        acc = s.setdefault("access", {})
        if only and sid not in only:
            continue
        if acc.get(store.__dict__.get("_LICENCE", "licence_forbids_machine_reading")) \
                or s.get("licence_forbids_machine_reading"):
            skipped.append((sid, "licence forbids machine reading — a person must read it"))
            continue
        if sid in have and not args.refetch:
            skipped.append((sid, "already held"))
            continue
        if not url:
            failed.append((sid, "no url recorded", s.get("title", "")))
            continue
        if sid in added_ids:
            ok, why_r = robots_allow(url)
            acc["robots"] = {"on": store.utc_today(), "by": "acquire_sources.py", "why": why_r,
                             "result": "unknown" if why_r.startswith(ROBOTS_UNKNOWN)
                             else ("allows" if ok else "not fetched")}
            if not ok:
                acc["last_fetch"] = {"on": store.utc_today(), "by": "acquire_sources.py",
                                     "result": "not fetched", "why": why_r}
                failed.append((sid, why_r, s.get("title", "")))
                continue
        targets = list(routes.get(sid) or []) + [acquisition_url(s)]
        data = ct = final = None
        why, check, tried = "no route tried", {}, []
        unavailable = False
        via_pmc = None
        for target in targets:
            misses = []
            epmc_ft = bool(EPMC_FULLTEXT.search(target)) and bool(os.environ.get("WHU_ORCH_STEP"))
            lacked = None            # why Europe PMC gave no copy: an outage, a 4xx, or its metadata says not served
            nsv = epmc_not_served(target, misses=misses)
            if nsv:                  # the record's metadata says this endpoint serves no full text: not requested
                why = nsv
                tried.append({"url": target, "result": why, "unavailable": False})
                if not epmc_ft:
                    continue
                lacked = nsv
            else:
                try:
                    data, ct, final = fetch_retrying(target)
                except Exception as e:
                    why = ("HTTP %s at %s" % (e.code, target[:60]) if isinstance(e, urllib.error.HTTPError)
                           else "%s at %s" % (type(e).__name__, target[:60]))
                    data = None
                    down = transient(e)
                    tried.append({"url": target, "result": why, "unavailable": down})
                    if not epmc_ft:
                        unavailable = unavailable or down
                        continue
                    if down:
                        import registries as RG
                        misses.append(RG.Answer(RG.EUROPE_PMC, False, why=why, url=target))
                    lacked = why
                else:
                    if misses:       # the metadata lookup failed but Europe PMC served the full text itself
                        import registries as RG
                        for miss in misses:
                            RG.covered(miss, ["Europe PMC full text"])
            if lacked is not None:
                # NCBI PMC, under the same licence rule (ruling 2 after the fallback build, extended by ruling 3 after
                # P091 to a copy Europe PMC lacks: a 404, or its metadata says not served); neither serving it: not held
                data, ct, final, via_pmc = pmc_fallback(target, misses)
                tried.append({"url": via_pmc["url"], "result": via_pmc["why"], "unavailable": not via_pmc["answered"]})
                if data is None:
                    why = "Europe PMC: %s; NCBI PMC: %s" % (lacked[:160], via_pmc["why"][:200])
                    unavailable = unavailable or not via_pmc["answered"]     # PMC down: not evidence of absence
                    continue
            # Identity is not substance, for EVERY type (2026-10-22). Until
            # then only article types were asked whether the bytes are the
            # document; any other type that identified itself was recorded as
            # full text, and on WHU-S01 a 2,606-byte publisher redirect page
            # was. source_store.held_check asks what `add` records -- the
            # substance check by the source's form -- and that the title is
            # in the visible text.
            ok, check = store.held_check(args.slug, sid, s, data, ct)
            why = check["why"]
            if ok:
                break
            why = "%s (%d bytes at %s)" % (why, len(data), target[:60]); data = None
            tried.append({"url": target, "result": why})
        via_open = None
        if data is None and args.open_copies and not unavailable:
            # the source's own copy could not be held: its permitted open copies (open_copy.py, ruling on P107)
            import open_copy as OC
            res = OC.find(s, url, fetch_retrying,
                          lambda d, c, _sid=sid, _s=s: store.held_check(args.slug, _sid, _s, d, c))
            acc["open_copies"] = dict(res["record"], on=store.utc_today())
            tried.append({"url": OC.ROUTE, "result": res["record"].get("outcome"),
                          "unavailable": bool(res.get("unavailable"))})
            if res.get("unavailable"):
                unavailable = True
                why = "%s; %s" % (why, res["record"]["outcome"])
            elif res.get("data") is not None:
                data, ct, final, check, via_open = res["data"], res["ct"], res["final"], res["check"], res["copy"]
                why = check["why"]
            else:
                why = "%s; %s: %s" % (why, OC.ROUTE, res["record"].get("outcome"))
        if data is None:
            # NOT FETCHED, and the ledger says why. The state is left as it was:
            # nothing was stored, so nothing is claimed.
            acc["last_fetch"] = {"on": store.utc_today(), "by": "acquire_sources.py",
                                 "result": "not fetched", "why": why, "tried": tried}
            if unavailable:          # a route timed out or errored, after the retries: not evidence of absence
                acc["last_fetch"]["registry_unavailable"] = True
            failed.append((sid, why, s.get("title", ""))); continue
        row = store.put(args.slug, sid, data, url=final, via="acquire_sources.py on the "
                        "operator's machine", content_type=ct, title=s.get("title", ""))
        acc["state"] = check["state"]
        acc.pop("last_fetch", None)
        acc["held"] = {"file": row["file"], "sha256": row["sha256"], "bytes": row["bytes"],
                       "identified_by": why, "kind": row["kind"], "kind_why": row["kind_why"]}
        if via_pmc and via_pmc.get("licence"):   # held through the NCBI PMC fallback: its route and licence
            acc["held"]["route"] = via_pmc["route"]
            acc["held"]["licence"] = via_pmc["licence"]
        if via_open:                             # held through an open copy: where, its version and its licence
            acc["held"]["route"] = "%s: %s (%s)" % (OC.ROUTE, via_open["where"], via_open["why"])
            acc["held"]["version"] = via_open["version"]
            acc["held"]["licence"] = {"name": via_open["licence"], "from": via_open["licence_from"],
                                      "url": via_open["url"]}
        acc.setdefault("on", row["retrieved"])
        got.append((sid, row["file"], row["bytes"]))
        print("  HELD     %-6s %-46s %8d B  (%s)"
              % (sid, row["sha256"][:12], row["bytes"], why))

    sp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.out:
        # Written last, after sources.json: a run that crashes part-way leaves no fresh record (advisor's ruling
        # after attempt 8: exit 1 is accepted only with this record as proof).
        rec = {"slug": args.slug, "complete": True, "held": [g[0] for g in got],
               "not_held": [{"id": sid, "title": title, "reason": why} for sid, why, title in failed],
               "skipped": [x[0] if isinstance(x, (list, tuple)) else x for x in skipped]}
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print("  held now: %d   failed: %d   skipped: %d" % (len(got), len(failed), len(skipped)))
    if failed and os.environ.get("WHU_ORCH_ISSUE") == args.slug:
        # An orchestrated run keeps no human search list (ruling (a), 2026-11-07): a source not held is recorded
        # not held, nothing on the page draws on it, and the page says so.
        print()
        for sid, why, title in failed:
            print("  NOT HELD %-6s %s" % (sid, title[:62]))
            print("           why: %s" % why)
        print()
    elif failed:
        print()
        print("  " + "=" * 68)
        print("  HUMAN SEARCH LIST — nobody holds these, so nothing may characterise them")
        print("  " + "=" * 68)
        for sid, why, title in failed:
            print("    %-6s %s" % (sid, title[:62]))
            print("           why: %s" % why)
            print("           put a copy in the store with:")
            print("             python3 backend/scripts/whatholdsup/source_store.py %s \\"
                  % args.slug)
            print("               add %s <path-to-file> --url <url> --via \"how you got it\""
                  % sid)
        print()
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
