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

READ, UNREAD = "READ", "UNREAD"

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
    r"|we have never read|unread by us|do not hold|have not obtained)\b", re.I)
_READ = re.compile(
    r"\b(we have (?:now )?read|read in full|held in full|we hold(?: the)?\b"
    r"|having read it|read at source|we have opened)\b", re.I)

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


def check_sentence(sentence: str, slug: str) -> list[dict]:
    """Disagreements between what this sentence asserts and what the store holds."""
    asserted = UNREAD if _UNREAD.search(sentence) else (
        READ if _READ.search(sentence) else None)
    if not asserted:
        return []
    out = []
    for sid in resolve(sentence, slug):
        # A sentence saying "we have not read the notice" is not contradicted by
        # holding the RECORD that describes the notice.
        if asserted == UNREAD and is_record_about(sid, slug):
            continue
        row = next((r for r in _sources(slug) if r.get("id") == sid), {})
        state = ((row.get("access") or {}).get("state") or "").lower()
        clash = (asserted == UNREAD and state in HELD_STATES) or \
                (asserted == READ and state in NOT_HELD_STATES)
        if clash:
            out.append({"source": sid, "asserted": asserted,
                        "recorded": state or "(no access state)",
                        "sentence": " ".join(sentence.split())[:220]})
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


def scan(slug: str) -> list[dict]:
    """Every epistemic disagreement in the page, its log and corrections.md."""
    import publish as P
    found = []
    page = (P.ROOT / P.ISSUES[slug]["page"]).read_text(encoding="utf-8")
    for s in _sentences(page):
        for f in check_sentence(s, slug):
            f["where"] = "page"
            found.append(f)
    cd = store.case_dir(slug)
    cm = cd / "corrections.md"
    if cm.exists():
        body = cm.read_text(encoding="utf-8")
        for s in _sentences(body):
            for f in check_sentence(s, slug):
                f["where"] = "corrections.md"
                found.append(f)
        for s in _sentences(body):
            for f in check_claimed_change(s, page):
                f["where"] = "corrections.md (claimed change)"
                found.append(f)
    return found


def main() -> int:
    import publish as P
    total = 0
    for slug in sorted(P.ISSUES):
        rows = scan(slug)
        total += len(rows)
        print("\n  %-11s %d disagreement(s)" % (slug, len(rows)))
        for f in rows:
            if "asserted" in f:
                print("   !! [%s] %s: page asserts %s, store records %s"
                      % (f["where"], f["source"], f["asserted"], f["recorded"]))
                print("      %s" % f["sentence"])
            else:
                print("   !! [%s] a correction says %r was removed; it is on the page"
                      % (f["where"], f["still_on_page"]))
                print("      %s" % f["correction"])
    print("\n  %d total\n" % total)
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
