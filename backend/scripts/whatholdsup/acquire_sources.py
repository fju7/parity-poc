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
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import source_store as store          # noqa: E402
import tls                             # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
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
    "note": ("a free public PDF on the publisher's own site (ipcc.ch); no recorded licence forbids "
             "machine reading; reuse of its text is subject to the publisher's terms on ipcc.ch, "
             "which this script did not read -- confirm them before quoting at length"),
    "machine_reading": "not forbidden by any recorded licence",
    "terms_checked": False,
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


def robots_allow(url: str, agent: str = "*") -> tuple[bool, str]:
    """robots.txt of the URL's host, read before fetching an added summary."""
    import urllib.robotparser as rp
    from urllib.parse import urlsplit
    parts = urlsplit(url)
    r = rp.RobotFileParser("%s://%s/robots.txt" % (parts.scheme, parts.netloc))
    try:
        r.read()
    except Exception as e:
        return False, "robots.txt could not be read (%s): not fetched" % type(e).__name__
    return (r.can_fetch(agent, url), "robots.txt %s it" % ("allows" if r.can_fetch(agent, url) else "disallows"))


def fetch(url: str, timeout: int = 45) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers=UA)
    with tls.urlopen(req, timeout=timeout) as r:      # completes a chain short of its intermediate
        return r.read(), r.headers.get("Content-Type", ""), r.geturl()


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
    have = store.held(args.slug)

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
            if not ok:
                acc["last_fetch"] = {"on": store.utc_today(), "by": "acquire_sources.py",
                                     "result": "not fetched", "why": why_r}
                failed.append((sid, why_r, s.get("title", "")))
                continue
        targets = list(routes.get(sid) or []) + [acquisition_url(s)]
        data = ct = final = None
        why, check, tried = "no route tried", {}, []
        for target in targets:
            try:
                data, ct, final = fetch(target)
            except urllib.error.HTTPError as e:
                why = "HTTP %s at %s" % (e.code, target[:60]); data = None
                tried.append({"url": target, "result": why}); continue
            except Exception as e:
                why = "%s at %s" % (type(e).__name__, target[:60]); data = None
                tried.append({"url": target, "result": why}); continue
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
        if data is None:
            # NOT FETCHED, and the ledger says why. The state is left as it was:
            # nothing was stored, so nothing is claimed.
            acc["last_fetch"] = {"on": store.utc_today(), "by": "acquire_sources.py",
                                 "result": "not fetched", "why": why, "tried": tried}
            failed.append((sid, why, s.get("title", ""))); continue
        row = store.put(args.slug, sid, data, url=final, via="acquire_sources.py on the "
                        "operator's machine", content_type=ct, title=s.get("title", ""))
        acc["state"] = check["state"]
        acc.pop("last_fetch", None)
        acc["held"] = {"file": row["file"], "sha256": row["sha256"], "bytes": row["bytes"],
                       "identified_by": why, "kind": row["kind"], "kind_why": row["kind_why"]}
        acc.setdefault("on", row["retrieved"])
        got.append((sid, row["file"], row["bytes"]))
        print("  HELD     %-6s %-46s %8d B  (%s)"
              % (sid, row["sha256"][:12], row["bytes"], why))

    sp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("  held now: %d   failed: %d   skipped: %d" % (len(got), len(failed), len(skipped)))
    if failed:
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
