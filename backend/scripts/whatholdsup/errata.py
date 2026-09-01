#!/usr/bin/env python3
"""B10 — has anything we cite been corrected since we read it?

WHY THIS IS THE FIRST THING BUILT
---------------------------------
On 2026-09-01 the operator pasted a PubMed record into a chat while asking an
unrelated question. Sitting in it was one line:

    EIN - Ann Oncol. 2025 Dec;36(12):1556.

MONARCH 3's final overall-survival paper had been formally corrected nine months
earlier. This page prints six figures from it. Nothing in this repository knew.
An hour later a second correction turned up the same way, on MONALEESA-2's
updated-results paper, published in August 2019 — seven years unnoticed.

Both were found by a person's eye passing over a metadata field. Neither was
found by the gate, the ledger, the library, the quotation check or the
counterexample hunt, because none of them looks at bibliographic records; they
all look at the paper.

An erratum is the ONE class of secondary document that can silently falsify a
figure we have already published. Checking for one is free, mechanical, needs no
judgement, and takes a field lookup. That is why it is first in the build order
and why it runs before anything that costs money.

WHAT IT REFUSES TO DO
---------------------
It never reports "no corrections" for a source whose record it could not
retrieve. Those are two different states and collapsing them would be this
repository's recurring error in a new place: an absence reported by something
that was not in a position to observe it. A lookup that fails is recorded as
UNCHECKED and blocks nothing except the claim that we checked.

It also never types an identifier. Every DOI, PMID and PMCID is parsed out of a
URL we already hold in sources.json. On 2026-08-31 five DOIs typed from memory
went to Unpaywall and three of them resolved to entirely different papers — an
immunotherapy trial, a PET radiogenomics study, a neoadjuvant study.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store  # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = "whatholdsup-errata/1.0 (editorial fact-check; contact fred.ugast@uspv.co)"

# The corrections that matter. Europe PMC's commentCorrectionList types include
# several that are NOT corrections to the paper -- a comment on it, a reply, an
# expression of concern about something else. These are the ones that mean the
# document we hold may no longer say what its authors intend it to say.
# WHAT CAN CARRY AN ERRATUM.
#
# A ClinicalTrials.gov posting and an FDA label are not journal articles. They
# are not indexed by Europe PMC, they have no commentCorrectionList, and they
# change by VERSION rather than by correction -- which is B11's job, not this
# one's. Asking this question of them is asking a question out of turn, and on
# the first full run it produced four confident false answers: the HARMONIA
# registry record "matched" a JCO paper, and two MONALEESA postings "matched" a
# Clinical Pharmacokinetics article, because the fallback read the first DOI in
# the bytes and a registry record's bytes are full of DOIs it CITES.
# Stated as an EXCLUSION, not an allow-list.
#
# The first version listed the types that CAN carry an erratum. Run against
# issue three it marked twenty sources "not applicable" on the strength of type
# names — critique, secondary, synthesis, prior_art — that are simply this
# issue's vocabulary for journal articles. An allow-list built from one issue's
# nouns silently excuses every noun it has not met, which is the same shape as
# the wall blocklist that stored two cookie pages as full text.
#
# What actually cannot carry an erratum is a document that is not a journal
# article at all: a trial registry posting, a drug label, a guideline. Those
# change by version, which is B11's business. Everything else is asked, and
# whether an identifier resolves decides the rest.
NOT_JOURNAL_ARTICLES = {"registry", "label", "guideline"}

AMENDING = {"Erratum in", "Corrected and republished in", "Retraction in",
            "Expression of concern in", "Republished in", "Update in"}
DISCUSSING = {"Comment in", "Comment on", "Erratum for", "Retraction of"}


# ---------------------------------------------------------------------------
# identifiers, parsed and never typed
# ---------------------------------------------------------------------------

def identifier_of(src: dict) -> tuple[str, str] | None:
    """(kind, value) from a URL WE ALREADY HOLD, or None.

    Order matters: a DOI is more specific than a PMID, and a PMCID resolves to
    one article without ambiguity. Nothing here is guessed from a title.
    """
    url = src.get("url") or ""
    for pat, kind, group in (
        (r"/articles/(PMC\d+)", "PMCID", 1),
        (r"(?:^|/)(PMC\d+)", "PMCID", 1),
        (r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})", "PMID", 1),
        (r"(?:doi\.org/|/doi/(?:full/|pdf/|abs/)?)(10\.\d{4,9}/[^\s?#]+)", "DOI", 1),
    ):
        m = re.search(pat, url, re.I)
        if m:
            return kind, m.group(group).rstrip(".,;)")
    # Elsevier PII, as used by Annals of Oncology, carries the article identity
    m = re.search(r"/article/(S\d{4}-\d{4}\(\d{2}\)\d{5}-[\dX])", url, re.I)
    if m:
        return "PII", m.group(1)
    return None


def identifier_from_held(slug: str, src: dict) -> tuple[str, str] | None:
    """A DOI read OUT OF THE DOCUMENT WE HOLD, when the URL yields nothing.

    Europe PMC does not resolve Elsevier PIIs, so MONARCH 3's final
    overall-survival paper -- whose URL carries only S0923-7534(24)00139-X --
    could not be looked up, and it is the paper whose corrigendum started all
    of this.

    The rule against typed identifiers stands. This does not break it: the DOI
    is parsed out of the bytes in the library, which is the same provenance the
    identity test already relies on. An identifier resolved from something we
    hold is evidence; one recalled is a guess, and on 2026-08-31 three of five
    guesses resolved to entirely different papers.
    """
    if src.get("type") == "corrigendum":
        # A corrigendum prints the DOI of the article it corrects, prominently
        # and often first. Reading a DOI out of one and calling it that
        # document's own identifier resolves to the ORIGINAL PAPER, which then
        # reports its own corrigendum as an erratum on the corrigendum. Seen on
        # the first full run.
        return None
    rec = (store.held(slug) or {}).get(src.get("id") or "")
    if not rec:
        return None
    f = store.LIB / rec.get("file", "")
    if not f.exists():
        return None
    ct = {".pdf": "application/pdf", ".json": "application/json",
          ".html": "text/html", ".xml": "application/xml"}.get(f.suffix, "")
    try:
        text, _how = store.text_of(f.read_bytes(), ct, pages=0)
    except Exception:
        return None
    hits = re.findall(r"\b(10\.\d{4,9}/[^\s\"<>)\]]+)", text)
    for h in hits:
        h = h.rstrip(".,;)")
        # the article's own DOI, not one from its reference list: it appears in
        # the first pages and, for these publishers, beside the journal name
        if len(h) < 60:
            return "DOI", h
    return None


def query_for(kind: str, value: str) -> str:
    return {"DOI": 'DOI:"%s"', "PMID": "EXT_ID:%s", "PMCID": "PMCID:%s",
            "PII": '"%s"'}[kind] % value


def lookup(kind: str, value: str, *, timeout: int = 25) -> tuple[dict | None, str]:
    """(record, why). record is None when we could not look, not when there is
    nothing to find."""
    url = EPMC + "?" + urllib.parse.urlencode(
        {"query": query_for(kind, value), "resultType": "core",
         "format": "json", "pageSize": "1"})
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            data = json.loads(fh.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        return None, "HTTP %s from Europe PMC" % exc.code
    except Exception as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    hits = (data.get("resultList") or {}).get("result") or []
    if not hits:
        return None, "Europe PMC has no record for %s %s" % (kind, value)
    return hits[0], "matched on %s %s" % (kind, value)


def resolves_to_us(rec: dict, src: dict) -> tuple[bool, str]:
    """Is the record Europe PMC returned actually OUR source?

    The identity test this repository already applies to bytes, applied to a
    lookup. On 2026-08-31 five identifiers typed from memory went to Unpaywall
    and three resolved to different papers; the fix then was to print the
    resolved title and look at it. Printing is not enough when nobody is
    watching, so it is checked.
    """
    got = re.sub(r"[^a-z0-9 ]+", " ", (rec.get("title") or "").lower())
    want = re.sub(r"[^a-z0-9 ]+", " ", (src.get("title") or "").lower())
    gw = {w for w in got.split() if len(w) > 3 and w not in store.STOP}
    ww = {w for w in want.split() if len(w) > 3 and w not in store.STOP}
    if not ww or not gw:
        return False, "no comparable title on one side"
    shared = gw & ww
    # Our titles are shorthand ("MONARCH 3 - final overall survival"), so the
    # bar is deliberately low; it exists to catch a DIFFERENT PAPER, not to
    # demand a match. Two distinctive words shared, or a third of ours.
    if len(shared) >= 2 or len(shared) >= max(1, len(ww) // 3):
        return True, "resolved title shares %d word(s) with ours: %s" % (
            len(shared), ", ".join(sorted(shared))[:80])
    return False, ("resolved to a DIFFERENT document: %r shares nothing "
                   "distinctive with %r" % ((rec.get("title") or "")[:70],
                                            (src.get("title") or "")[:70]))


def amendments(rec: dict) -> tuple[list[dict], list[dict]]:
    items = (rec.get("commentCorrectionList") or {}).get("commentCorrection") or []
    if isinstance(items, dict):
        items = [items]
    amend = [i for i in items if (i.get("type") or "") in AMENDING]
    disc = [i for i in items if (i.get("type") or "") in DISCUSSING]
    return amend, disc


# ---------------------------------------------------------------------------
# the sweep
# ---------------------------------------------------------------------------

def record_path(slug: str) -> Path:
    return store.case_dir(slug) / "errata.json"


def load(slug: str) -> dict:
    p = record_path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"_what_this_is":
            "For every source, whether its bibliographic record names a "
            "correction, erratum, retraction or expression of concern -- and, "
            "when the lookup failed, that it failed. 'checked, none' and 'could "
            "not check' are different states and this file never merges them.",
            "checked": {}}


def save(slug: str, doc: dict) -> None:
    record_path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")


def sweep(slug: str, *, only: set[str] | None = None, pause: float = 1.0) -> dict:
    doc = load(slug)
    for src in store.sources(slug):
        sid = src.get("id")
        if only and sid not in only:
            continue
        row = {"source": sid, "title": (src.get("title") or "")[:120],
               "checked_on": date.today().isoformat()}
        if src.get("type") in NOT_JOURNAL_ARTICLES:
            row.update(state="NOT_APPLICABLE",
                       why="type %r is not a journal article; it has versions, "
                           "not errata, and B11 covers those"
                           % (src.get("type") or ""),
                       amendments=[], comments=[])
            doc["checked"][sid] = row
            print("  %-6s n/a          %s" % (sid, row["why"][:70]))
            continue
        ident = identifier_of(src)
        from_held = False
        if not ident:
            ident = identifier_from_held(slug, src)
            from_held = ident is not None
        if not ident:
            row.update(state="UNCHECKABLE",
                       why="no DOI, PMID, PMCID or PII can be parsed from the URL "
                           "we hold; nothing is typed from memory, so this source "
                           "cannot be looked up automatically",
                       amendments=[], comments=[])
            doc["checked"][sid] = row
            print("  %-6s UNCHECKABLE  %s" % (sid, row["why"][:70]))
            continue
        kind, value = ident
        rec, why = lookup(kind, value)
        # A PII resolves the article for its publisher and not for Europe PMC.
        # Falling back to a DOI READ OUT OF THE HELD BYTES is what makes MONARCH
        # 3 checkable at all, and it is the paper the corrigendum was on.
        if rec is None and not from_held:
            alt = identifier_from_held(slug, src)
            if alt:
                kind, value = alt
                from_held = True
                rec, why = lookup(kind, value)
        row["identifier"] = "%s %s" % (kind, value)
        row["identifier_from"] = "the held document" if from_held else "the source URL"
        if rec is None:
            row.update(state="UNCHECKED", why=why, amendments=[], comments=[])
            print("  %-6s UNCHECKED    %s" % (sid, why[:70]))
        else:
            same, why_same = resolves_to_us(rec, src)
            row["resolved_title"] = (rec.get("title") or "")[:160]
            if not same:
                row.update(state="UNCHECKED",
                           why="lookup on %s %s %s" % (kind, value, why_same),
                           amendments=[], comments=[])
                doc["checked"][sid] = row
                print("  %-6s UNCHECKED    %s" % (sid, why_same[:70]))
                time.sleep(pause)
                continue
            row["identity"] = why_same
            amend, disc = amendments(rec)
            row["amendments"] = amend
            row["comments"] = disc
            row["state"] = "AMENDED" if amend else "CLEAN"
            row["why"] = why
            if amend:
                for a in amend:
                    print("  %-6s AMENDED      %s: %s %s"
                          % (sid, a.get("type"), a.get("journalAbbreviation", ""),
                             a.get("id", "")))
            else:
                print("  %-6s clean        %s" % (sid, why[:60]))
        doc["checked"][sid] = row
        time.sleep(pause)
    save(slug, doc)
    return doc


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    try:
        srcs = store.sources(slug)
    except Exception as exc:
        return [("errata check", WARN, "could not read sources.json: %s" % exc)]
    doc = load(slug)
    checked = doc.get("checked") or {}
    ids = [s["id"] for s in srcs]

    never = [i for i in ids if i not in checked]
    unchecked = [i for i in ids if (checked.get(i) or {}).get("state") == "UNCHECKED"]
    uncheckable = [i for i in ids if (checked.get(i) or {}).get("state") == "UNCHECKABLE"]
    amended = [i for i in ids if (checked.get(i) or {}).get("amendments")]

    rows = []
    rows.append(("sources checked for corrections",
                 OK if not never else BAD,
                 "all %d source(s) have had their bibliographic record read for "
                 "errata" % len(ids) if not never else
                 "%d source(s) have never been checked: %s — an erratum is the one "
                 "document that can falsify a figure already published"
                 % (len(never), ", ".join(never[:8]))))
    if unchecked:
        rows.append(("correction lookups that failed", WARN,
                     "%d source(s) could not be looked up and are NOT known to be "
                     "clean: %s" % (len(unchecked), ", ".join(unchecked[:8]))))
    if uncheckable:
        rows.append(("sources with no resolvable identifier", WARN,
                     "%d source(s) carry no DOI, PMID, PMCID or PII in the URL we "
                     "hold, so no automatic check is possible: %s"
                     % (len(uncheckable), ", ".join(uncheckable[:8]))))
    if amended:
        # A correction that has been OBTAINED AND READ is accounted for, and a
        # check that keeps shouting about work already done is a check that
        # gets waived. The evidence is a source in this issue that declares it
        # amends the corrected one, and is itself held.
        held = set(store.held(slug) or {})
        accounted = {s.get("amends") for s in srcs
                     if s.get("amends") and s["id"] in held}
        open_ = [i for i in amended if i not in accounted]
        done = [i for i in amended if i in accounted]
        if done:
            rows.append(("corrections obtained and read", OK,
                         "%d correction(s) are in the library and their effect on "
                         "what we print is recorded: %s"
                         % (len(done), ", ".join(done))))
        if open_:
            detail = []
            for i in open_:
                for a in (checked[i].get("amendments") or []):
                    detail.append("%s: %s %s" % (i, a.get("type"),
                                                 a.get("id", "")))
            rows.append(("corrections not yet read", BAD,
                         "%d source(s) have been formally corrected and we do not "
                         "hold the correction: %s — until it is read we do not "
                         "know whether it touches a figure on this page"
                         % (len(open_), " || ".join(detail[:6]))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--only", default="", help="comma-separated source ids")
    ap.add_argument("--status", action="store_true", help="report without looking up")
    args = ap.parse_args()
    if args.status:
        print()
        for label, state, detail in preflight_rows(args.slug):
            print("  %-6s %-38s %s" % (state, label, detail))
        print()
        return 0
    print("\n  Reading bibliographic records for %s\n" % args.slug)
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    sweep(args.slug, only=only)
    print()
    for label, state, detail in preflight_rows(args.slug):
        print("  %-6s %-38s %s" % (state, label, detail))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
