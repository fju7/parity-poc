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
CROSSREF = "https://api.crossref.org/works/"
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
    # ONLY AN ARTICLE'S OWN BYTES CARRY ITS OWN DOI.
    #
    # The two guards below name TYPES — coverage, corrigendum — which is an
    # allow-list built from the two cases that had bitten us, and on 3 September
    # a third walked straight past it. Issue three's S035 is a Science Media
    # Centre expert-reaction page, typed `critique`. It prints the DOI of the
    # Budzyn colonoscopy paper it is reacting to. Read out and filed as the SMC
    # page's own identifier, Europe PMC reported the PAPER's erratum against the
    # PAGE — and resolves_to_us waved it through, because our shorthand title
    # for the page says "colonoscopy deskilling study" and so does the paper's.
    #
    # Both identity checks failed together, which is what happens when the thing
    # being identified is genuinely about the thing it is being confused with.
    #
    # So the test is FORM, not type: a document that is not an article is not
    # the article whose DOI it prints. That is the distinction `form` was added
    # for, and it covers the cases nobody has met yet.
    form = store.form_of(src)
    if form != "article":
        # An UNDECLARED form is not permission either. Reading a DOI out of a
        # document nobody has classified is a guess about what the document is,
        # and this function's whole justification is that it does not guess.
        # The remedy is two words in sources.json, and coverage.py already
        # reports every source that needs them.
        return None
    if src.get("type") == "coverage":
        # A NEWS ARTICLE ABOUT A PAPER PRINTS THE PAPER'S DOI. Reading it out
        # and treating it as the news article's own identifier is the
        # corrigendum mistake wearing a different hat: it asks Europe PMC for
        # errata on somebody else's document and reports the answer against
        # ours. On 2026-09-01 an MLQ News article yielded 10.1200/JCO.2026.44.
        # 16_suppl.9500 -- a JCO meeting abstract it cites. Nothing came back,
        # so nothing was misfiled, which is luck and not a control.
        #
        # Coverage has no errata. It has corrections, which are printed on the
        # article itself and need the document, not a bibliographic database.
        return None
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
    for h in re.findall(r"\b(10\.\d{4,9}/[^\s\"<>\]]+)", text):
        h = clean_doi(h)
        # the article's own DOI, not one from its reference list: it appears in
        # the first pages and, for these publishers, beside the journal name
        if h and len(h) < 60:
            return "DOI", h
    return None


def clean_doi(raw: str) -> str:
    """Trim a DOI read out of running text, WITHOUT breaking Elsevier's.

    Two failures, both found on 3 September by running this over every source
    in the estate:

      * a query string became part of the DOI. Issue three's S016 was looked up
        as "10.5117/EJEP2025.1.001.TUOM?ref=404media.co" — a referrer parameter
        from the URL the document happened to print. A DOI ends at "?" or "#".

      * a closing bracket ended the match, and Elsevier DOIs contain brackets.
        S035 was looked up as "10.1016/S2468-1253(25" — the real DOI is
        10.1016/S2468-1253(25)00294-8. Excluding ")" from the character class
        cut every Annals-of-Oncology-style DOI in half, and the ones it cut
        returned "no record", which reads exactly like a clean lookup of a
        document nobody has corrected.

    So ")" is allowed through and then UNBALANCED trailing brackets are dropped
    — a DOI in prose is usually inside a parenthesis of somebody else's.
    """
    h = raw.split("?", 1)[0].split("#", 1)[0]
    h = h.rstrip(".,;:")
    while h.endswith(")") and h.count(")") > h.count("("):
        h = h[:-1].rstrip(".,;:")
    return h


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


def crossref(doi: str, *, timeout: int = 25) -> tuple[dict | None, str]:
    """The registration agency's own record. (record, why); None means we could
    not look, never that there is nothing to find.

    WHY A SECOND INDEX, AND WHY IT IS NOT AS GOOD AS THE FIRST.

    Europe PMC indexes what PubMed and PMC index. On 3 September it had no
    record for either of issue one's two ASCO documents — the JCO Oncology
    Advances three-year paper and the ASCO 2026 meeting abstract — and the
    check reported both as "could not look up".

    That collapses the distinction this whole file exists to keep. "The lookup
    failed" and "this index does not carry this journal" are different states,
    and only the first is a reason to try again. Both DOIs are registered, both
    resolve at Crossref, and both titles match ours.

    Crossref's answer is weaker and must not be reported as though it were the
    same answer. Europe PMC records a correction because a curator linked it.
    Crossref records one only if the PUBLISHER deposited the relation. So a
    publisher who registers no Crossmark update policy cannot produce a
    correction here even when one exists, and an absence from that publisher is
    not evidence of anything. JCO Oncology Advances is exactly that case today.
    """
    url = CROSSREF + urllib.parse.quote(doi, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            data = json.loads(fh.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        return None, "HTTP %s from Crossref" % exc.code
    except Exception as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    msg = data.get("message")
    if not isinstance(msg, dict):
        return None, "Crossref returned no record for DOI %s" % doi
    return msg, "matched on DOI %s at Crossref" % doi


# Relations a publisher deposits when a work has been corrected, withdrawn or
# replaced. Not an allow-list of vocabulary we have met: these are the names
# Crossref defines for the relation, and one we have never seen is still one of
# these names.
CROSSREF_AMENDING = ("is-corrected-by", "has-correction", "is-retracted-by",
                     "is-replaced-by", "is-expressed-by-erratum")


def crossref_amendments(msg: dict) -> list[dict]:
    out = []
    rel = msg.get("relation") or {}
    for name in CROSSREF_AMENDING:
        for item in (rel.get(name) or []):
            out.append({"type": name, "id": item.get("id"),
                        "source": "Crossref relation"})
    for item in (msg.get("updated-by") or []):
        out.append({"type": item.get("type") or "update",
                    "id": item.get("DOI"), "source": "Crossref updated-by"})
    return out


def crossref_title_record(msg: dict) -> dict:
    """Shaped like a Europe PMC hit, so resolves_to_us can judge it unchanged."""
    return {"title": (msg.get("title") or [""])[0]}


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
        if rec is None and kind == "DOI":
            # Europe PMC does not carry every journal. Ask the agency that
            # registered the DOI before reporting that we could not look.
            msg, why_cr = crossref(value)
            if msg is not None:
                same, why_same = resolves_to_us(crossref_title_record(msg), src)
                if same:
                    amend = crossref_amendments(msg)
                    policy = msg.get("update-policy")
                    row["identity"] = why_same
                    row["resolved_title"] = (msg.get("title") or [""])[0][:160]
                    row["index"] = "Crossref"
                    row["update_policy"] = policy
                    row["amendments"] = amend
                    row["comments"] = []
                    if amend:
                        row["state"] = "AMENDED"
                        row["why"] = why_cr
                        for a in amend:
                            print("  %-6s AMENDED      %s: %s"
                                  % (sid, a.get("type"), a.get("id")))
                    elif policy:
                        row["state"] = "CLEAN"
                        row["why"] = (why_cr + "; not in Europe PMC. The publisher "
                                      "registers a Crossmark update policy, so a "
                                      "correction would have been deposited here")
                        print("  %-6s clean        %s" % (sid, "Crossref, publisher deposits updates"))
                    else:
                        row["state"] = "UNCHECKED"
                        row["why"] = (why_cr + "; not in Europe PMC, and the "
                                      "publisher registers NO update policy — so "
                                      "Crossref would not know of a correction "
                                      "even if one existed. This is not a pass")
                        print("  %-6s UNCHECKED    %s"
                              % (sid, "at Crossref but publisher deposits no updates"))
                    doc["checked"][sid] = row
                    time.sleep(pause)
                    continue
                why = "%s; Crossref %s" % (why, why_same)
            else:
                why = "%s; %s" % (why, why_cr)
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
