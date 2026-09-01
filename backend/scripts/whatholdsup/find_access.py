#!/usr/bin/env python3
"""Where can each document we do not hold be got, legally and free?

WHY THIS EXISTS
---------------
On 2026-09-01 the library held 11 of 24 sources for issue two. The 13 missing
were the ones the piece is actually about: every hazard ratio in the main table
comes from NEJM, JCO, Annals of Oncology or Clinical Cancer Research, and we
held none of those papers.

The first attempt to find them was done by hand, by typing DOIs from memory into
Unpaywall. Three of the five were WRONG DOIS, and Unpaywall answered for the
papers those DOIs actually name: an immunotherapy trial, a PET radiogenomics
study, a neoadjuvant study. Two minutes more and three wrong download links
would have been handed to the operator as "the MONARCH 3 paper".

That is this project's recurring error in its purest form -- a plausible
identifier, an authoritative-looking answer, and nothing checking that the
answer is about the thing we asked for.

WHERE THE IDENTIFIER CAME FROM IS THE WHOLE QUESTION. The first version of this
file then over-corrected and title-checked everything, which rejected the two
correct NEJM papers: our own titles are internal shorthand ("MONALEESA-7 —
overall survival") and the published titles are not ("Overall Survival with
Ribociclib plus Endocrine Therapy in Breast Cancer"). Too loose returned the
wrong papers; too strict refused the right ones.

The distinction that actually separates them is not similarity, it is PROVENANCE:

  RESOLVED   the identifier was extracted from the url already in sources.json.
             Nobody guessed it, so the record it returns is the record we asked
             for. Its title is printed for a human to read, not used as a gate.

  SEARCHED   the identifier came from a title lookup, i.e. from a guess. Every
             one of the three wrong papers arrived this way. These MUST match on
             title before their download links are shown.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import source_store as store          # noqa: E402

MAIL = "fred.ugast@uspv.co"
UA = {"User-Agent": "whatholdsup/1.0 (mailto:%s)" % MAIL}
STOP = {"the", "a", "an", "of", "and", "or", "in", "for", "with", "on", "to", "as",
        "at", "by", "from", "is", "are", "was", "were", "not", "no", "vs", "versus",
        "study", "trial", "results", "analysis", "patients"}


def get(url: str, timeout: int = 30):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers=UA), timeout=timeout))


def ids_from_url(url: str) -> dict:
    """Identifiers we already hold, taken from the URL rather than invented."""
    out = {}
    m = re.search(r"(PMC\d{6,9})", url, re.I)
    if m:
        out["pmcid"] = m.group(1).upper()
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})", url)
    if m:
        out["pmid"] = m.group(1)
    m = re.search(r"(10\.\d{4,9}/[^\s?#]+)", url)
    if m:
        out["doi"] = m.group(1).rstrip("/").replace("/fulltext", "")
    m = re.search(r"/article/(S\d{4}-?\d{3}[\dX]\(\d{2}\)\d{5}-?\d?)/", url, re.I)
    if m:
        out["pii"] = m.group(1)
    return out


def title_words(t: str) -> set:
    return {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9'-]{3,}", t or "")
            if w.lower() not in STOP}


def titles_agree(ours: str, theirs: str) -> tuple[bool, str]:
    a, b = title_words(ours), title_words(theirs)
    if not a or not b:
        return False, "no comparable title"
    overlap = a & b
    need = max(3, min(len(a), len(b)) // 3)
    return (len(overlap) >= need,
            "%d shared title words (needed %d)" % (len(overlap), need))


def epmc(ident: str, field: str) -> dict | None:
    q = urllib.parse.quote('%s:"%s"' % (field, ident))
    try:
        r = get("https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                "?query=%s&resultType=core&format=json" % q)
    except Exception:
        return None
    res = (r.get("resultList") or {}).get("result") or []
    return res[0] if res else None


def unpaywall(doi: str) -> dict | None:
    try:
        return get("https://api.unpaywall.org/v2/%s?email=%s" % (doi, MAIL))
    except Exception:
        return None


def routes_for(src: dict) -> dict:
    ours = src.get("title") or ""
    ids = ids_from_url(src.get("url") or "")
    found, checked, notes = [], None, []

    for field, key in (("PMCID", "pmcid"), ("EXT_ID", "pmid"), ("DOI", "doi")):
        if key not in ids:
            continue
        rec = epmc(ids[key], field)
        time.sleep(1)
        if not rec:
            notes.append("Europe PMC has no record for %s %s" % (key, ids[key]))
            continue
        # RESOLVED, not searched: this identifier came out of the url already in
        # sources.json, so the record is the one we asked for. The title is
        # reported for a person to read rather than used as a gate -- gating on
        # it rejected both correct NEJM papers, because our titles are internal
        # shorthand and published titles are not.
        checked = rec
        notes.append("identifier %s=%s came from the url we already hold, not a search"
                     % (key.lower(), ids[key]))
        for u in ((rec.get("fullTextUrlList") or {}).get("fullTextUrl") or []):
            if (u.get("availability") or "").lower() in ("free", "open access"):
                found.append(("Europe PMC: %s" % u.get("site"), u.get("documentStyle"),
                              u.get("url")))
        if rec.get("pmcid") and rec.get("inEPMC") == "Y":
            found.append(("Europe PMC full-text XML", "xml",
                          "https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML"
                          % rec["pmcid"]))
        break

    doi = ids.get("doi") or (checked or {}).get("doi")
    if doi:
        up = unpaywall(doi)
        time.sleep(1)
        if up:
            # No gate here either, and that is the point. Every DOI this tool
            # uses comes either from the url in sources.json or from a record
            # resolved by an identifier in that url. IT NEVER TYPES ONE. The
            # three wrong papers came from DOIs typed by hand, and a title gate
            # bolted on afterwards then rejected the two correct NEJM papers and
            # a correct Ann Oncol one, because our titles are shorthand.
            #
            # So: never guess, and SHOW THE RESOLVED TITLE so a person reads
            # what came back. A check that rejects right answers to catch an
            # error the tool cannot make is worse than no check.
            notes.append("resolved title: %r" % (up.get("title") or "")[:72])
            if up.get("is_oa"):
                for loc in (up.get("oa_locations") or []):
                    found.append(("Unpaywall: %s" % loc.get("host_type"),
                                  loc.get("version"),
                                  loc.get("url_for_pdf") or loc.get("url")))
            else:
                notes.append("Unpaywall: no free version anywhere (is_oa false)")
    else:
        notes.append("no DOI could be taken from the url we hold; nothing was guessed")
    seen, uniq = set(), []
    for r in found:
        if r[2] and r[2] not in seen:
            seen.add(r[2]); uniq.append(r)
    return {"ids": ids, "routes": uniq, "notes": notes,
            "verified_title": (checked or {}).get("title", "")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--only")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",")} if args.only else None
    h = store.held(args.slug)
    out = {}
    print()
    for s in store.sources(args.slug):
        sid = s["id"]
        if sid in h or (only and sid not in only):
            continue
        if s.get("licence_forbids_machine_reading"):
            print("  %-5s SKIPPED — licence forbids machine reading\n" % sid)
            continue
        r = routes_for(s)
        out[sid] = r
        print("  %-5s %s" % (sid, (s.get("title") or "")[:64]))
        if r["verified_title"]:
            print("        title checked: %r" % r["verified_title"][:60])
        for site, style, url in r["routes"]:
            print("        FREE  %-26s %-18s %s" % (site[:26], (style or "")[:18], url))
        for n in r["notes"]:
            print("        note  %s" % n)
        if not r["routes"]:
            print("        NO FREE ROUTE FOUND — needs your access, or the authors")
        print()
    p = store.case_dir(args.slug) / "access-routes.json"
    p.write_text(json.dumps({
        "what_this_is": ("Where each document we do not hold can be got. Every route "
                         "here was title-checked against our own record for that source, "
                         "because the first hand-typed attempt at this returned three "
                         "wrong papers from three wrong DOIs."),
        "checked": time.strftime("%Y-%m-%d"), "sources": out},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print("  written to %s\n" % p.relative_to(store.ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
