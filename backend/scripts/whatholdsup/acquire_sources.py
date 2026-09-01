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
all "bytes"; the size and content-type checks below reject the obvious cases,
and everything that passes is still only a candidate until somebody looks. A
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


def fetch(url: str, timeout: int = 45) -> tuple[bytes, str, str]:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", ""), r.geturl()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--only", help="comma-separated source ids")
    ap.add_argument("--refetch", action="store_true",
                    help="fetch even sources already in the store")
    args = ap.parse_args()

    case = store.case_dir(args.slug)
    sp = case / "sources.json"
    doc = json.loads(sp.read_text(encoding="utf-8"))
    srcs = doc.get("sources", doc)
    only = {x.strip() for x in args.only.split(",")} if args.only else None
    have = store.held(args.slug)

    got, failed, skipped = [], [], []
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
        target = acquisition_url(s)
        try:
            data, ct, final = fetch(target)
        except urllib.error.HTTPError as e:
            failed.append((sid, "HTTP %s" % e.code, s.get("title", ""))); continue
        except Exception as e:
            failed.append((sid, "%s: %s" % (type(e).__name__, e), s.get("title", ""))); continue
        ok, why = store.identifies(data, s, ct)
        if not ok:
            failed.append((sid, why, s.get("title", ""))); continue
        row = store.put(args.slug, sid, data, url=final, via="acquire_sources.py on the "
                        "operator's machine", content_type=ct, title=s.get("title", ""))
        acc["state"] = "full_text_held"
        acc["held"] = {"file": row["file"], "sha256": row["sha256"], "bytes": row["bytes"],
                       "identified_by": why}
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
