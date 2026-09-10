#!/usr/bin/env python3
"""Sentences claiming what we know, against what the store says we hold.

WHY THIS EXISTS
---------------
Every check in this repository asks whether a claim about the WORLD is
supported. None asked whether a claim about OURSELVES was true -- and this
publication's most load-bearing sentences are the second kind: what we hold,
what we have read, what we could not reach, what nobody has opened. Those are
the claims the source store can adjudicate, because the store is where the
answer lives.

Three went wrong in two days, and every one of them passed every gate:

  * the cdk46 corrigendum note said "we have now read it" and, four sentences
    later, that we could not know what it touched "because that requires reading
    it". Both sentences, one passage, both green.
  * corrections.md said the same notice "remains unread". True on 31 August,
    false on 1 September, unnoticed until 10 September.
  * a 4 September correction announced that a clause had been replaced. It had
    not been. It stayed on the page for five more days.

THE CLASS, AND WHY IT IS THE CHEAP THIRD OF A PROBLEM THAT LOOKED EXPENSIVE
---------------------------------------------------------------------------
Passage coherence was filed as needing "a different kind of machinery".
Decomposed it is three problems, not one:

  contradiction    two sentences that cannot both be true
  STALE PREDICATE  a sentence asserting a state the system already tracks and
                   that has since changed          <-- this file
  legibility       nothing false; the passage is hard to parse

Only the middle one is mechanical, and it is the one that caused the harm. The
other two are a reading, not a detector -- see the passage-reading stage in
docs/whatholdsup-process.md.

WHAT IT WILL NOT DO
-------------------
It does not adjudicate PAYWALLED or OPEN ACCESS. Holding a PDF and the article
being paywalled are compatible facts -- the operator obtained several of these
by hand -- so `access.state` cannot settle a licence question and this file does
not pretend it can. That is a claim about the world wearing a claim about
ourselves, and it is checked by going and looking, as it was on 2026-09-10.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import source_store as store          # noqa: E402

OK, WARN, BAD = "ok", "warn", "STOP"

PASS, FAIL, NOT_EVALUATED = "PASS", "FAIL", "NOT EVALUATED"

# THREE OUTCOMES, NEVER TWO.
#
# A check that cannot determine a sentence's subject reports NOT EVALUATED. It
# never reports PASS. Silence about what was not examined is the difference
# between a coverage number and a false assurance — and the first run of this
# file produced four findings, all false positives, from which the flattering
# reading was "the corpus is clean". Four false positives and zero true
# positives establishes nothing about the corpus. It establishes that the
# predicate half works.

READ, UNREAD, HOLD, UNREACHED = "READ", "UNREAD", "HOLD", "UNREACHED"

# PREDICATES ARE NOT BINARY, AND THE STORE HAS SIX STATES.
#
# "The five-year release we hold" is TRUE at abstract_held — the release is
# held, as an abstract. The first version of this file called that a
# contradiction, because it collapsed six states into held/not-held. "We hold"
# and "we have read" make different claims about the same state and only the
# second is false at abstract_held.
SATISFIED_BY = {
    HOLD:      {"full_text_held", "human_read", "abstract_held", "fragment_only"},
    READ:      {"full_text_held", "human_read"},
    UNREAD:    {"blocked", "fragment_only", "abstract_held", "not_opened",
                "unchecked", ""},
    UNREACHED: {"blocked", "not_opened", ""},
}

# A source may be held in full and still be the wrong document to ask. S030 is
# the PubMed RECORD for an erratum whose notice nobody has read; its state is
# full_text_held and what is held is a bibliographic stub. Without this, the
# most careful disclosure on the melanoma page reads as a lie.
RECORD_FORMS = {"record", "notice_record", "bibliographic"}
RECORD_TYPES = {"reference"}

HELD_STATES = {"full_text_held", "human_read"}
NOT_HELD_STATES = {"blocked", "fragment_only", "abstract_held", "unchecked", ""}

_UNREAD = re.compile(
    r"\b(remains? unread|still unread|have not (?:yet )?read|has not (?:yet )?been read"
    r"|have not been able to read|requires reading it|cannot say .{0,80}reading"
    r"|nobody (?:here )?(?:has|had) (?:ever )?opened|never (?:been )?read"
    r"|we have never read|unread by us|have not obtained)\b", re.I)
_READ = re.compile(
    r"\b(we have (?:now )?read|read in full|read it in full|having read it"
    r"|read at source|we have opened)\b", re.I)
_HOLD = re.compile(r"\b(we hold|held in full|the .{0,40}we hold|do not hold)\b", re.I)
_UNREACHED = re.compile(
    r"\b(could not reach|cannot reach|every retrieval route .{0,40}block"
    r"|returned a block|we could not open)\b", re.I)

def _asserted(sentence: str):
    """The claim this sentence makes about our own access. Order matters: the
    negative forms are checked first because "do not hold" contains "hold"."""
    if _UNREAD.search(sentence):
        return UNREAD
    if _UNREACHED.search(sentence):
        return UNREACHED
    if _READ.search(sentence):
        return READ
    if _HOLD.search(sentence):
        return HOLD
    return None


# "the clause has been replaced / removed / now reads" -- a claim about the page.
_CLAIMED_CHANGE = re.compile(
    r"\b(has been (?:replaced|removed|deleted|dropped|withdrawn|cut)"
    r"|is gone|no longer (?:appears|carries|says|characterises|characterizes)"
    r"|the sentence now reads|now says instead)\b", re.I)


def _sources(slug: str) -> list[dict]:
    cd = store.case_dir(slug)
    raw = json.loads((cd / "sources.json").read_text(encoding="utf-8"))
    rows = raw.get("sources") or raw
    return rows if isinstance(rows, list) else list(rows.values())


def is_record_about(sid: str, slug: str) -> bool:
    """True when this id holds a document ABOUT another document.

    The store already carries the discriminator and nothing read it: `form:
    record`, `type: reference`, or an access note saying what section is held.
    """
    for r in _sources(slug):
        if r.get("id") != sid:
            continue
        if (r.get("form") or "").lower() in RECORD_FORMS:
            return True
        if (r.get("type") or "").lower() in RECORD_TYPES:
            return True
        secs = " ".join((r.get("access") or {}).get("sections") or []).lower()
        return "bibliographic" in secs or "record" == secs.strip()
    return False


def _names(r: dict) -> list[str]:
    out = [r.get("id") or ""]
    out += [a for a in (r.get("also_called") or []) if a]
    t = r.get("title") or ""
    m = re.match(r"([A-Za-z0-9–— .\-]{6,60}?)\s*[—\-:,]", t)
    if m:
        out.append(m.group(1).strip())
    return [n for n in out if len(n) >= 4]


def resolve(sentence: str, slug: str) -> list[str]:
    """Which source(s) a sentence is talking about.

    THE SPECIFIC ALIAS WINS. "The MONARCH 3 corrigendum" matches both the
    corrigendum and the trial paper it corrects, because one alias contains the
    other. Reporting both makes the check name a source the sentence was not
    about, and a check that reports the wrong subject is worse than one that
    reports nothing -- it sends the reader to the wrong document. So a match
    whose alias is a substring of another match's alias is dropped.
    """
    hits = {}
    for r in _sources(slug):
        best = ""
        for nm in _names(r):
            if re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(nm),
                         sentence, re.I) and len(nm) > len(best):
                best = nm
        if best:
            hits[r["id"]] = best.lower()
    out = [sid for sid, alias in hits.items()
           if not any(alias != other and alias in other for other in hits.values())]
    return out


def declared_sources(sentence: str, slug: str) -> list[str]:
    """Source ids the BINDING for this sentence declares.

    Not proof of subject — a sentence can be supported by one document and
    predicate about another — but far stronger evidence than a title appearing
    in the string, which is what produced two of the four false positives on the
    first corpus run.
    """
    try:
        import bindings as B
        rows = json.loads((store.case_dir(slug) / "bindings.json")
                          .read_text(encoding="utf-8")).get("bindings") or []
    except Exception:
        return []
    if isinstance(rows, dict):
        rows = list(rows.values())
    key = " ".join(sentence.split())
    for r in rows:
        if " ".join((r.get("sentence") or "").split()) != key:
            continue
        blob = json.dumps(r)
        return sorted(set(re.findall(r"\bS\d{3}\b", blob)))
    return []


def check_sentence(sentence: str, slug: str) -> list[dict]:
    """One verdict per epistemic sentence: PASS, FAIL or NOT EVALUATED.

    NOT EVALUATED is never silence. It is the passage-reading stage's worklist.
    """
    asserted = _asserted(sentence)
    if not asserted:
        return []

    by_string = resolve(sentence, slug)
    by_binding = declared_sources(sentence, slug)

    # Where the binding and the string agree, the subject is resolved. Where
    # they disagree, or the sentence is unbound, it is not.
    if by_binding:
        agreed = [s for s in by_string if s in by_binding]
        subjects, how = (agreed, "binding and text agree") if agreed else ([], "binding and text disagree")
    elif len(by_string) == 1:
        subjects, how = by_string, "one source named, unbound"
    elif len(by_string) > 1:
        subjects, how = [], "names %d sources; which one it is about is not decidable" % len(by_string)
    else:
        subjects, how = [], "no source resolved"

    if not subjects:
        return [{"verdict": NOT_EVALUATED, "asserted": asserted, "why": how,
                 "candidates": by_string or by_binding,
                 "sentence": " ".join(sentence.split())[:220]}]

    out = []
    for sid in subjects:
        row = next((r for r in _sources(slug) if r.get("id") == sid), {})
        klass = (row.get("document_class") or "").lower()
        # A record ABOUT a document cannot answer a question about the document.
        # Unclassified is NOT EVALUATED, never an assumed `document`.
        if not klass:
            out.append({"verdict": NOT_EVALUATED, "asserted": asserted,
                        "source": sid, "why": "document_class not set on this source",
                        "sentence": " ".join(sentence.split())[:220]})
            continue
        if klass == "record_about":
            out.append({"verdict": NOT_EVALUATED, "asserted": asserted,
                        "source": sid,
                        "why": "this id holds a record ABOUT a document; the claim is "
                               "about the document",
                        "sentence": " ".join(sentence.split())[:220]})
            continue
        state = ((row.get("access") or {}).get("state") or "").lower()
        good = state in SATISFIED_BY.get(asserted, set())
        out.append({"verdict": PASS if good else FAIL, "asserted": asserted,
                    "source": sid, "recorded": state or "(no access state)",
                    "why": how, "sentence": " ".join(sentence.split())[:220]})
    return out


def check_claimed_change(correction: str, page_text: str) -> list[dict]:
    """A correction announcing a change, against the page that should carry it.

    The 4 September notice said the Morning Glory clause had been replaced. It
    was on the page when that correction published and stayed five more days.
    """
    if not _CLAIMED_CHANGE.search(correction):
        return []
    quoted = re.findall(r"[“\"']([^”\"']{12,180})[”\"']", correction)
    subject = quoted or re.findall(
        r"\b((?:[A-Z][\w'’]+ ){1,4}(?:clause|sentence|paragraph|phrase|wording))\b",
        correction)
    flat = " ".join(page_text.split()).lower()
    out = []
    for s in subject:
        key = re.sub(r"\b(clause|sentence|paragraph|phrase|wording)\b", "",
                     s, flags=re.I)
        key = re.sub(r"^\s*(the|this|that|a|an)\s+", "", key, flags=re.I)
        key = " ".join(key.split()).lower()
        if key and key in flat:
            out.append({"claimed": "removed/replaced", "still_on_page": key,
                        "correction": " ".join(correction.split())[:220]})
    return out


def _sentences(text: str) -> list[str]:
    import source_ledger as led
    return [" ".join(s.split()) for s in led.sentences(led.plain(text))]


def alias_coverage(slug: str) -> dict:
    """How many sources can be named at all.

    A source with no aliases is NOT CHECKED, not checked-and-passed. S025 had
    none, which made the source at the centre of two of the three incidents
    invisible to resolution. Reported as a number rather than left silent.
    """
    rows = _sources(slug)
    named = [r for r in rows if (r.get("also_called") or [])]
    classed = [r for r in rows if r.get("document_class")]
    return {"sources": len(rows), "with_aliases": len(named),
            "with_document_class": len(classed)}


def scan(slug: str) -> dict:
    """Every epistemic claim in the page, its log and corrections.md, triaged.

    Returns verdicts and a coverage fraction. The coverage fraction is the
    point: this file's job is to narrow the field for the passage-reading stage
    (docs/whatholdsup-process.md §5.5), not to decide.
    """
    import publish as P
    verdicts = []
    page = (P.ROOT / P.ISSUES[slug]["page"]).read_text(encoding="utf-8")
    for s in _sentences(page):
        for f in check_sentence(s, slug):
            f["where"] = "page"
            verdicts.append(f)
    cm = store.case_dir(slug) / "corrections.md"
    if cm.exists():
        body = cm.read_text(encoding="utf-8")
        for s in _sentences(body):
            for f in check_sentence(s, slug):
                f["where"] = "corrections.md"
                verdicts.append(f)
            for f in check_claimed_change(s, page):
                f["verdict"] = FAIL
                f["where"] = "corrections.md (claimed change)"
                verdicts.append(f)
    n = len(verdicts)
    ev = len([v for v in verdicts if v["verdict"] in (PASS, FAIL)])
    return {"slug": slug, "verdicts": verdicts, "epistemic_sentences": n,
            "evaluated": ev, "coverage": (ev / n) if n else 0.0,
            "aliases": alias_coverage(slug)}


def appendix_d_lines(slug: str) -> list[str]:
    """The coverage statement, for the appendix that records where the machinery
    has not looked.

    THIS WORDING FAILED QUESTION 3 AND WAS REWRITTEN. The first version said
    "evaluated 1 of 89 sentences", which is true and invites a false reading —
    that only 1% of this publication's claims are checked. Those sentences WERE
    checked, by readers, at the time, against documents, several of them by name
    in adjudications. What is 1 of 89 is a NEW automated subject-resolving
    cross-check that did not exist the day before.

    A disclosure that is inaccurate in the unflattering direction is still
    inaccurate, and being modest does not excuse it. So the number carries its
    own scope.

    Recorded because it is evidence: the passage-reading stage caught a false
    impression in the very disclosure written to describe that stage's own
    machinery, on its first use, leaning the direction this cycle has NOT been
    leaning.
    """
    r = scan(slug)
    a = r["aliases"]
    out = [
        "**A new automated cross-check, and what it can and cannot yet see.** "
        "Every sentence in which we say what we know about a source — that we "
        "hold it, have read it, could not reach it — is now read by a check that "
        "compares the claim against the source store.",
        "",
        "It can currently resolve which source is meant in **%d of %d** such "
        "sentences on this page. The other %d it reports as NOT EVALUATED rather "
        "than passing them."
        % (r["evaluated"], r["epistemic_sentences"],
           r["epistemic_sentences"] - r["evaluated"]),
        "",
        "**This measures the check and the store's metadata, not the sentences.** "
        "Each of them was checked by a reader when it was written. Nothing on "
        "this page is yet established as sound or stale by machine, in either "
        "direction, and a low number here is a fact about a three-day-old "
        "instrument rather than about the page.",
        "",
        "Of %d sources, %d can be named by an alias and %d declare whether they "
        "are a document or a record *about* a document. A source that is neither "
        "is not checked, rather than checked and passed."
        % (a["sources"], a["with_aliases"], a["with_document_class"]),
        "",
        "The NOT EVALUATED sentences are the passage-reading worklist: a human "
        "reads them, because no machine here can yet tell which document each "
        "one is about.",
    ]
    return out


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    """NOT wired into check yet -- see docs/whatholdsup-open-gaps.md. Present so
    that wiring it in is one line when the coverage fraction justifies it."""
    r = scan(slug)
    fails = [v for v in r["verdicts"] if v["verdict"] == FAIL]
    return [("claims about what we hold",
             OK if not fails else BAD,
             "%d of %d epistemic sentence(s) evaluated (%.0f%%); %d disagree with the store"
             % (r["evaluated"], r["epistemic_sentences"], 100 * r["coverage"], len(fails)))]


def main() -> int:
    import publish as P
    tot_f = 0
    for slug in sorted(P.ISSUES):
        r = scan(slug)
        f = [v for v in r["verdicts"] if v["verdict"] == FAIL]
        ne = [v for v in r["verdicts"] if v["verdict"] == NOT_EVALUATED]
        p = [v for v in r["verdicts"] if v["verdict"] == PASS]
        tot_f += len(f)
        print("\n  %-11s %d epistemic sentence(s): %d PASS, %d FAIL, %d NOT EVALUATED"
              "  — coverage %.0f%%"
              % (slug, r["epistemic_sentences"], len(p), len(f), len(ne),
                 100 * r["coverage"]))
        a = r["aliases"]
        print("              %d/%d sources aliased, %d/%d classed document|record_about"
              % (a["with_aliases"], a["sources"], a["with_document_class"], a["sources"]))
        for v in f:
            if "still_on_page" in v:
                print("   FAIL  [%s] a correction says %r was removed; it is on the page"
                      % (v["where"], v["still_on_page"]))
                print("         %s" % v.get("correction", "")[:130])
                continue
            print("   FAIL  [%s] %s: asserts %s, store records %s"
                  % (v["where"], v.get("source", "?"), v.get("asserted"), v.get("recorded", "?")))
            print("         %s" % v.get("sentence", "")[:130])
        for v in ne[:6]:
            print("   n/e   [%s] %s — %s" % (v["where"], v.get("source", ""), v["why"]))
            print("         %s" % v.get("sentence", "")[:130])
        if len(ne) > 6:
            print("   n/e   ... %d more, all of them passage-reading worklist" % (len(ne) - 6))
    print("\n  %d FAIL across all issues. NOT EVALUATED is not a pass.\n" % tot_f)
    return 1 if tot_f else 0


if __name__ == "__main__":
    raise SystemExit(main())
