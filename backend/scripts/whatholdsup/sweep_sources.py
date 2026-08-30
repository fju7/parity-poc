#!/usr/bin/env python3
"""
What Holds Up: the source sweep — citations and corrections.

WHY THIS EXISTS
---------------
On 2026-08-30 an outside reviewer found a study we had said did not exist.

The page for issue three said "the honest position on a null result is that we
do not have one." Pedersen et al., a prospective multicentre trial that removed
CADe and measured what happened, had been published in Endoscopy on 3 June 2026
— nearly three months earlier. It cites our central study. Yuichi Mori, that
study's senior author, is on it. Two fact-check gate runs at roughly $18, five
counterexample hunts, a source-advocate pass and a lint pass all went over the
page without finding it.

The same day we discovered that the central study had carried a correction
since 11 September 2025 — eleven months — which we found only because a gate's
coverage role stumbled over the PubMed record.

Neither was hidden. Both were one free API call away:

    /MED/40816301/citations   ->  126 citing papers, Pedersen among them
    /search?query=DOI:...     ->  commentCorrectionList: [Erratum in, 40946709]

WHAT WAS ACTUALLY BROKEN
------------------------
The weekly scanner (scan_leads.py) watches GDELT and Wikipedia pageviews. Both
measure ATTENTION — what is being published and read in the news. That is the
right instrument for finding a SUBJECT, and it is the wrong one for watching a
subject we have already published. Nothing we owned looked at the literature.

Meanwhile watch.json for issue three named 28 specific queries across 8
questions and nothing executed any of them. The 2026-08-30 watch entry records,
in writing, under not_checked: "W1 — no registry search run" and "W2 — no
citation sweep run". The record existed. Nothing consulted it. That is the same
failure shape as an unrun check reported as a pass, one layer up.

WHAT THIS DOES
--------------
    citations   For every source with a resolvable identifier, ask Europe PMC
                who has cited it since the last sweep. New citations only — the
                baseline is stored, so a sweep that finds nothing says so, and
                a sweep that finds four says which four.

    status      For the same sources, read commentCorrectionList: errata,
                retractions, corrections, expressions of concern, and comments.
                This is the check that had been available for eleven months.

THE RULE THIS FILE IS BUILT AROUND
----------------------------------
An unrun check is not a pass, and a source this cannot reach is not a source
with nothing to report. Only 13 of issue three's 42 sources carry a DOI, a PMID
or an arXiv id. The other 29 are news articles, labels, institutional reports
and preprints outside the index. This tool reports them as UNSWEEPABLE, by name,
every run. A sweep covering a third of the ledger that prints "nothing new"
without saying so would be worse than no sweep, because it would look like
diligence.

No model, no API key, no cost. Europe PMC's REST service is open.

Usage:

    sweep_sources.py citations <slug> [--all] [--json]
    sweep_sources.py status    <slug> [--json]
    sweep_sources.py resolve   <slug>          which sources can be swept at all
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

ROOT = Path(__file__).resolve().parents[3]
ISSUES = ROOT / "issues"
BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = "whatholdsup-source-sweep/1.0 (corrections@whatholdsup.org)"
TIMEOUT = 30
PAUSE = 0.34          # Europe PMC asks for courtesy; three a second is polite.

# Correction types worth waking someone up for, versus ones that are just
# scholarly conversation. Both are reported; only the first group is loud.
LOUD = {"retraction in", "erratum in", "expression of concern in",
        "corrected and republished in", "republished in"}


# ----------------------------------------------------------------- identifiers

def identifiers(src: dict) -> dict | None:
    """(kind, value) for a source, from an explicit field or its URL.

    Explicit fields win. A DOI dug out of a URL is still a DOI, but a URL that
    merely CONTAINS digits is not a PMID, so the patterns are anchored.
    """
    url = src.get("url") or ""
    doi = src.get("doi")
    if not doi:
        m = re.search(r"(10\.\d{4,9}/[^\s\"'<>?&#]+)", url)
        if m:
            doi = m.group(1).rstrip(").,;")
    pmid = src.get("pmid")
    if not pmid:
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})", url)
        if m:
            pmid = m.group(1)
    # arXiv ids are read from the URL and the TITLE only, never from the whole
    # record. The first version searched json.dumps(src), and resolved the
    # scoping review (S029) to arXiv 2411.00998 — an id quoted inside its own
    # notes, belonging to a different paper. A sweep that silently swaps one
    # paper for another is worse than a sweep that reports a gap.
    arxiv = None
    for field in (url, src.get("title") or ""):
        m = (re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", field)
             or re.search(r"\barXiv[:\s]\s*(\d{4}\.\d{4,5})\b", field))
        if m:
            arxiv = m.group(1)
            break
    if pmid:
        return {"kind": "pmid", "value": str(pmid)}
    if doi:
        return {"kind": "doi", "value": doi}
    if arxiv:
        return {"kind": "arxiv", "value": arxiv}
    return None


def _get(path: str, params: dict) -> dict:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def lookup(ident: dict) -> dict | None:
    """Resolve an identifier to a Europe PMC record (source + id + core fields).

    Three things learned by getting each of them wrong on 2026-08-30:

    PMIDs must NOT be quoted. `EXT_ID:"42235541" AND SRC:"MED"` returns zero
    hits; `EXT_ID:42235541 AND SRC:MED` returns the paper. The first form
    reported the Pedersen study — the one this whole file exists because of —
    as "not in the index".

    A bare arXiv number must never be searched as a phrase. `"2506.08872"`
    returns 31 unrelated hits, the first of which is a different paper
    entirely. Silently resolving a source to somebody else's article is the
    worst thing this tool could do, so an arXiv id is looked up only through
    its registered DOI, and anything else is reported unresolved.

    Some DOIs are genuinely absent: Europe PMC does not index MDPI's Societies
    or Wiley's Journal of Computer Assisted Learning. That is a real gap in
    coverage and is reported as one, not smoothed over.
    """
    if ident["kind"] == "pmid":
        q = "EXT_ID:%s AND SRC:MED" % ident["value"]
    elif ident["kind"] == "doi":
        q = 'DOI:"%s"' % ident["value"]
    else:
        q = 'DOI:"10.48550/arXiv.%s"' % ident["value"]
    time.sleep(PAUSE)
    d = _get("/search", {"query": q, "resultType": "core", "format": "json",
                         "pageSize": 1})
    hits = d.get("resultList", {}).get("result", [])
    return hits[0] if hits else None


def published_version(src: dict) -> list:
    """Candidate published versions of a preprint, by exact title.

    For the preprints this page leans on, the question that matters is watch
    question W3: has it been peer reviewed, revised or withdrawn? A title
    search can answer that, and can also match the wrong paper, so results are
    returned as CANDIDATES for a person to confirm and are never written into a
    baseline as a resolution.
    """
    title = (src.get("title") or "")
    m = re.search(r"\u2014\s*(.+?)(?:\.|,|\s+arXiv|\s+\d{4};)", title)
    phrase = (m.group(1) if m else title).strip()
    phrase = re.sub(r'["\\]', " ", phrase)[:120].strip()
    if len(phrase) < 25:
        return []
    try:
        time.sleep(PAUSE)
        d = _get("/search", {"query": 'TITLE:"%s"' % phrase, "resultType": "lite",
                             "format": "json", "pageSize": 5})
    except Exception:
        return []
    return d.get("resultList", {}).get("result", []) or []


# ---------------------------------------------------------------------- state

def state_path(slug_dir: Path) -> Path:
    return slug_dir / "sweeps.json"


def load_state(slug_dir: Path) -> dict:
    p = state_path(slug_dir)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"what_this_is": ("Baselines for sweep_sources.py. Which citations and "
                            "which correction notices we had already seen, so a "
                            "later run can report what is NEW rather than "
                            "re-reporting the world."),
            "citations": {}, "status": {}, "runs": []}


def save_state(slug_dir: Path, st: dict) -> None:
    state_path(slug_dir).write_text(
        json.dumps(st, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_issue(slug: str) -> Path:
    for d in sorted(ISSUES.glob("WHU-*")):
        if (d / "sources.json").exists() and slug.lower() in d.name.lower():
            return d
    for d in sorted(ISSUES.glob("*")):
        if (d / "sources.json").exists() and slug.lower() in d.name.lower():
            return d
    raise SystemExit("no issue directory matching %r under %s" % (slug, ISSUES))


def sweepable(slug_dir: Path):
    """-> (list of (src, ident), list of unsweepable src). Never silently drops."""
    doc = json.loads((slug_dir / "sources.json").read_text(encoding="utf-8"))
    rows = doc["sources"] if isinstance(doc, dict) else doc
    ok, no = [], []
    for r in rows:
        ident = identifiers(r)
        (ok.append((r, ident)) if ident else no.append(r))
    return ok, no


def _title(r: dict) -> str:
    return (r.get("title") or "").strip()


# ------------------------------------------------------------------ citations

def cmd_citations(args) -> int:
    d = find_issue(args.slug)
    ok, no = sweepable(d)
    st = load_state(d)
    base = st.setdefault("citations", {})
    today = date.today().isoformat()

    print("\n  CITATION SWEEP — %s" % d.name)
    print("  %d source(s) with an identifier, %d without\n" % (len(ok), len(no)))

    new_total, unresolved, checked = 0, [], 0
    for src, ident in ok:
        try:
            rec = lookup(ident)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            unresolved.append((src["id"], "%s: %s" % (ident["value"], exc)))
            continue
        if not rec:
            unresolved.append((src["id"], "%s not in the index" % ident["value"]))
            continue
        source, pid = rec.get("source"), rec.get("id")
        try:
            time.sleep(PAUSE)
            c = _get("/%s/%s/citations" % (source, pid),
                     {"format": "json", "pageSize": 1000})
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            unresolved.append((src["id"], "citations call failed: %s" % exc))
            continue
        checked += 1
        cits = c.get("citationList", {}).get("citation", []) or []
        seen = set(base.get(src["id"], {}).get("ids", []))
        fresh = [x for x in cits if str(x.get("id")) not in seen]
        if args.all:
            fresh = cits
        if fresh:
            new_total += len(fresh)
            print("  %s  %s" % (src["id"], _title(src)[:66]))
            print("      %d citing paper(s)%s" %
                  (len(fresh), " — FIRST SWEEP, so all of them" if not seen else " NEW since last sweep"))
            for x in sorted(fresh, key=lambda z: str(z.get("pubYear") or ""), reverse=True)[:args.show]:
                print("        %s  %-11s %s" % (x.get("pubYear") or "????",
                                                (x.get("journalAbbreviation") or "")[:11],
                                                (x.get("title") or "")[:62]))
                print("                              %s" % (x.get("authorString") or "")[:62])
            if len(fresh) > args.show:
                print("        ... and %d more, in sweeps.json" % (len(fresh) - args.show))
            print()
        base[src["id"]] = {"ids": [str(x.get("id")) for x in cits],
                           "count": len(cits), "swept": today,
                           "resolved_as": "%s/%s" % (source, pid)}

    print("  " + "-" * 66)
    print("  %d source(s) queried, %d new citation(s)." % (checked, new_total))
    if unresolved:
        print("\n  COULD NOT RESOLVE — not the same as nothing to report:")
        for sid, why in unresolved:
            print("    %-6s %s" % (sid, why))
    if no:
        print("\n  NOT SWEEPABLE — no DOI, PMID or arXiv id. These are watched by")
        print("  hand or not at all, and this list is the honest size of that gap:")
        for r in no:
            print("    %-6s %s" % (r["id"], _title(r)[:64]))
    st["runs"].append({"on": today, "command": "citations",
                       "sources_queried": checked, "new_citations": new_total,
                       "unresolved": [s for s, _ in unresolved],
                       "unsweepable": [r["id"] for r in no]})
    save_state(d, st)
    print("\n  baseline written to %s\n" % state_path(d).relative_to(ROOT))
    return 0


# --------------------------------------------------------------------- status

def cmd_status(args) -> int:
    d = find_issue(args.slug)
    ok, no = sweepable(d)
    st = load_state(d)
    base = st.setdefault("status", {})
    today = date.today().isoformat()

    print("\n  CORRECTION AND RETRACTION SWEEP — %s" % d.name)
    print("  %d source(s) with an identifier, %d without\n" % (len(ok), len(no)))

    loud, quiet, unresolved, candidates, checked = [], [], [], [], 0
    for src, ident in ok:
        try:
            rec = lookup(ident)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            unresolved.append((src["id"], str(exc)))
            continue
        if not rec:
            unresolved.append((src["id"], "%s not in the index" % ident["value"]))
            if ident["kind"] == "arxiv":
                for cand in published_version(src):
                    candidates.append((src, cand))
            continue
        checked += 1
        notes = rec.get("commentCorrectionList", {}).get("commentCorrection", []) or []
        prev = set(base.get(src["id"], {}).get("seen", []))
        for n in notes:
            key = "%s:%s" % (n.get("type"), n.get("id"))
            row = (src, n, key not in prev)
            (loud if (n.get("type") or "").lower() in LOUD else quiet).append(row)
        base[src["id"]] = {"seen": ["%s:%s" % (n.get("type"), n.get("id")) for n in notes],
                           "swept": today,
                           "resolved_as": "%s/%s" % (rec.get("source"), rec.get("id"))}

    if loud:
        print("  CORRECTIONS, ERRATA AND RETRACTIONS")
        for src, n, is_new in loud:
            print("    %s%s  %s" % ("NEW " if is_new else "    ", src["id"], _title(src)[:58]))
            print("           %s — europepmc.org/article/MED/%s" % (n.get("type"), n.get("id")))
        print()
    else:
        print("  No corrections, errata or retractions on any source we could resolve.\n")

    if quiet and not args.quiet:
        print("  COMMENTS AND REPLIES (conversation, not correction)")
        for src, n, is_new in quiet[:args.show]:
            print("    %s%s  %s — MED/%s" % ("NEW " if is_new else "    ",
                                             src["id"], n.get("type"), n.get("id")))
        if len(quiet) > args.show:
            print("    ... and %d more" % (len(quiet) - args.show))
        print()

    if candidates:
        print("  POSSIBLE PUBLISHED VERSIONS OF PREPRINTS — CANDIDATES ONLY")
        print("  A title search finds these. It also finds the wrong paper: on")
        print("  2026-08-30 a search for \"Your Brain on ChatGPT\" returned a")
        print("  different 2025 article with almost the same title. Nothing here")
        print("  is recorded as a resolution. Open it, or leave it.")
        for src, cand in candidates[:args.show]:
            print("    %-6s -> %s/%s (%s)  %s" % (src["id"], cand.get("source"),
                                                  cand.get("id"), cand.get("pubYear"),
                                                  (cand.get("title") or "")[:48]))
        print()

    print("  " + "-" * 66)
    print("  %d source(s) queried." % checked)
    if unresolved:
        print("\n  COULD NOT RESOLVE — not the same as nothing to report:")
        for sid, why in unresolved:
            print("    %-6s %s" % (sid, why))
        print("    Europe PMC indexes the biomedical literature. It does not")
        print("    carry MDPI's Societies, Wiley's J Comput Assist Learn,")
        print("    Elsevier's Computers & Education, OSF preprints, or arXiv")
        print("    computer-science preprints. Those are watched by hand.")
    if no:
        print("\n  NOT SWEEPABLE — no DOI, PMID or arXiv id:")
        for r in no:
            print("    %-6s %s" % (r["id"], _title(r)[:64]))
    st["runs"].append({"on": today, "command": "status", "sources_queried": checked,
                       "loud": len(loud), "quiet": len(quiet),
                       "preprint_candidates": len(candidates),
                       "unresolved": [s for s, _ in unresolved],
                       "unsweepable": [r["id"] for r in no]})
    save_state(d, st)
    print("\n  baseline written to %s\n" % state_path(d).relative_to(ROOT))
    return 0


def cmd_resolve(args) -> int:
    d = find_issue(args.slug)
    ok, no = sweepable(d)
    print("\n  %s — what can be swept at all\n" % d.name)
    for src, ident in ok:
        print("    %-6s %-5s %-34s %s" % (src["id"], ident["kind"],
                                          ident["value"][:34], _title(src)[:40]))
    print("\n  %d of %d sweepable. The rest carry no DOI, PMID or arXiv id:\n"
          % (len(ok), len(ok) + len(no)))
    for r in no:
        print("    %-6s %-9s %s" % (r["id"], (r.get("type") or "")[:9], _title(r)[:56]))
    print("\n  That gap is the honest limit of this instrument. News articles,")
    print("  labels, institutional reports and off-index preprints are watched")
    print("  by hand or not at all.\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, helptext in (
            ("citations", cmd_citations, "who has cited our sources since the last sweep"),
            ("status", cmd_status, "corrections, errata and retractions on our sources"),
            ("resolve", cmd_resolve, "which sources carry an identifier at all")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("slug", help="issue slug or directory fragment, e.g. deskilling")
        p.add_argument("--show", type=int, default=6, help="how many to print per source")
        if name == "citations":
            p.add_argument("--all", action="store_true",
                           help="print every citation, not only new ones")
        if name == "status":
            p.add_argument("--quiet", action="store_true",
                           help="corrections only; hide comments and replies")
        p.set_defaults(fn=fn)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
