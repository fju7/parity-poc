#!/usr/bin/env python3
"""
What Holds Up: deterministic claim lint.

WHY THIS EXISTS
---------------
Of the four findings a reader returned against issue two after publication, two
needed no model at all:

  "No study that compares them by other means finds a difference"
      A universal claim over a literature the same page admits it has not
      surveyed. An outside reviewer caught one instance of this class before
      publication; the fix did not reach the second instance, four sections
      away, and that instance published.

  "all three indirect comparisons"
      The page examines four. The section heading above the paragraph said
      "Three times, by three methods" while the paragraph beneath it said "This
      page examines four of them." Both sentences were written in the same
      editing pass, after a fourth study was added in review and the count above
      it was not updated.

Eighteen model-driven fact-check runs, costing $66.76, passed both. They were
looking at whether each figure was right. Both figures were right. The error was
in the quantifier and the count, which are syntax, and syntax is the one thing a
machine is unambiguously better at than a careful reader at four in the morning.

So this file has no model in it, makes no API call, costs nothing, and runs in
milliseconds. It is the cheapest check in the pipeline and it catches a class
that the most expensive one cannot.

WHAT A "BOUND" IS
-----------------
A universal claim is not wrong. It is wrong *unbounded*. "No study finds a
difference" is a claim about every study that exists. "None of the four
comparative studies examined on this page separates them" is a claim about four
studies, and it is one we can defend. The lint asks only whether the sentence
names its own scope — not whether the claim is true.
"""
from __future__ import annotations

import argparse
import html as _html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OK, BAD, WARN = "ok", "BLOCKED", "warn"

# ---------------------------------------------------------------------------

NUMWORD = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}

# Words that assert over a whole class.
UNIVERSAL = re.compile(
    r"\b("
    r"every|all|no|none|nobody|no one|not one|never|each|any|the only|only"
    r")\b", re.I)

# The nouns that make a universal claim dangerous. "All three drugs improve
# progression-free survival" is a claim over a set the page itself defines and
# lists; "no study finds a difference" is a claim over every study that exists.
# Only the second kind can be wrong in the way issue two was wrong, and firing
# on the first kind is how a lint gets switched off. The first version of this
# file returned 39 hits on a page with two real instances, which is a check
# nobody would keep.
EVIDENCE_BODY = (
    "study", "studies", "trial", "trials", "research", "literature",
    "analysis", "analyses", "comparison", "comparisons", "paper", "papers",
    "publication", "publications", "report", "reports", "coverage",
    "outlet", "outlets", "source", "sources", "evidence", "data",
)

GOVERNS = re.compile(
    r"\b(every|all|no|none|nobody|not one|never|each|any|the only|only)\b"
    r"(?:\s+\w+){0,3}?\s+(" + "|".join(EVIDENCE_BODY) + r")\b", re.I)

# Anything that names the scope the claim is actually made over. A sentence
# carrying one of these has told the reader what it surveyed. Attribution
# counts: a universal claim the page attributes to a named source is that
# source's claim, bounded by the citation, and the check for it is the ledger.
BOUND = re.compile(
    r"\b("
    r"this page|on this page|examined here|examined on this page|"
    r"we (?:examined|checked|read|could find|surveyed|have read)|"
    r"that we (?:examined|checked|read|found)|"
    r"of the (?:two|three|four|five|six|seven|eight|nine|ten|\d+)|"
    r"the (?:two|three|four|five|six|seven|eight|nine|ten|\d+) "
    r"(?:studies|trials|comparisons|sources|papers|analyses|readouts)|"
    r"(?:the guideline|the label|the paper|the authors?|its own) "
    r"(?:records?|states?|says?|reports?)|"
    r"named (?:in|below)|listed (?:in|below)|these four|these three|"
    r"not a literature|not the literature|four studies we read"
    r")\b", re.I)

# Countable things this publication makes claims about. Restricting the noun
# vocabulary is what keeps the count check from firing on every number on the
# page — "0.76" and "63.9 months" are not counts of anything.
COUNTABLE = (
    "studies", "study", "trials", "trial", "comparisons", "comparison",
    "sources", "papers", "analyses", "methods", "method", "readouts",
    "findings", "runs", "reviews", "places", "sentences", "drugs",
    "objections", "corrections", "programmes", "cohorts", "endpoints",
)

COUNT_RE = re.compile(
    r"\b(" + "|".join(NUMWORD) + r"|\d{1,3})\s+(?:\w+\s+){0,2}?(" +
    "|".join(COUNTABLE) + r")\b", re.I)

SIDEDNESS = re.compile(r"\b(one|two)-sided\b", re.I)

SENTENCE = re.compile(r"(?<=[.!?])\s+")


def plain(html_text: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", " ", html_text))


def sentences(text: str) -> list[str]:
    return [re.sub(r"\s+", " ", s).strip()
            for s in SENTENCE.split(text) if s.strip()]


def sections(html_text: str) -> list[tuple[str, str]]:
    """(heading, plain text) per <section>, so a count is compared with the
    counts near it rather than with every number on the page."""
    out = []
    for block in re.split(r"(?=<section\b)", html_text):
        if not block.strip():
            continue
        m = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S)
        head = plain(m.group(1)).strip() if m else "(no heading)"
        out.append((head, plain(block)))
    return out


# ---------------------------------------------------------------------------
# the checks
# ---------------------------------------------------------------------------

def unbounded_universals(text: str) -> list[str]:
    hits = []
    for s in sentences(text):
        m = GOVERNS.search(s)
        if not m:
            continue
        if BOUND.search(s):
            continue
        hits.append(f"[{m.group(0)}] {s[:150]}")
    return hits


def count_disagreements(html_text: str) -> list[str]:
    """The same countable noun given two different numbers in one section."""
    out = []
    for head, text in sections(html_text):
        seen: dict[str, set[int]] = {}
        where: dict[str, list[str]] = {}
        for m in COUNT_RE.finditer(text):
            raw, noun = m.group(1).lower(), m.group(2).lower()
            n = NUMWORD.get(raw) or (int(raw) if raw.isdigit() else None)
            if n is None or n > 50:
                continue
            key = noun.rstrip("s")
            seen.setdefault(key, set()).add(n)
            where.setdefault(key, []).append(m.group(0))
        for key, ns in seen.items():
            if len(ns) > 1:
                out.append(f"'{head[:40]}' gives {key} as "
                           + " and ".join(str(n) for n in sorted(ns))
                           + f"  ({'; '.join(where[key][:4])})")
    return out


def enumeration_mismatch(text: str) -> list[str]:
    """A stated number followed by an explicit "not A, not B, not C" list.

    This is the highest-precision check in the file, because both halves are
    literal: the number is a word and the list is punctuation. It is the one
    that blocks.
    """
    out = []
    for s in sentences(text):
        # A list item is "not <determiner-or-Name>": "not the network
        # meta-analysis", "not P-VERIFY". This deliberately does not match "not
        # reached", "not significant" or "not powered" -- the table is full of
        # those, and the first version of this check counted them as list items
        # and blocked the publish on a hazard-ratio table.
        ITEM = r"(?:[:\u2014-]|,)\s+not\s+(?:the|a|an|its|our|their)\b|" \
               r"(?:[:\u2014-]|,)\s+not\s+[A-Z]"
        if not re.search(r"[:\u2014-]\s+not\s+(?:the|a|an|its|our|their)\b|"
                         r"[:\u2014-]\s+not\s+[A-Z]", s):
            continue
        items = len(re.findall(ITEM, s))
        nums = [NUMWORD.get(m.group(1).lower())
                if m.group(1).lower() in NUMWORD else int(m.group(1))
                for m in COUNT_RE.finditer(s)]
        nums = [n for n in nums if n and n <= 20]
        if items >= 2 and nums and items not in nums:
            out.append(f"says {nums[0]} and then lists {items}: {s[:170]}")
    return out


def subhead_counts(html_text: str) -> list[str]:
    """A count in a section's standfirst that appears nowhere in its body.

    Issue two's comparative-studies section was subheaded "Three times, by three
    methods" over a body whose first line read "This page examines four of
    them." The same-noun check misses it -- "times" and "methods" against
    "them" -- so this one ignores nouns and asks only whether the number in the
    subhead is a number the section ever uses again.

    IT WARNS, IT DOES NOT BLOCK, and its first live firing is why. On
    2026-08-29 it stopped issue one over "Our published six-dimension rubric",
    a section that then lists exactly six dimensions -- source quality, data
    support, reproducibility, consensus, recency, rigor -- and never writes the
    word "six" again because it enumerates them instead. The count was right.
    A section that ENUMERATES what it counted is the normal way to write this,
    and a check that cannot tell enumeration from contradiction has no business
    stopping a publish. The same reasoning as the universal-quantifier check:
    the ones that block are literal, the ones that need judgement are lists to
    walk.
    """
    out = []
    for block in re.split(r"(?=<section\b)", html_text):
        m = re.search(r"<h2[^>]*>(.*?)</h2>\s*<p[^>]*>(.*?)</p>", block, re.S)
        if not m:
            continue
        head, sub = plain(m.group(1)).strip(), plain(m.group(2))
        body = plain(block[m.end():])
        for w in re.findall(r"\b(" + "|".join(NUMWORD) + r")\b", sub, re.I):
            n = NUMWORD[w.lower()]
            words = [k for k, v in NUMWORD.items() if v == n]
            pat = r"\b(?:" + "|".join(words + [str(n)]) + r")\b"
            if not re.search(pat, body, re.I):
                out.append(f"'{head[:34]}' is subheaded {w!r} and the section "
                           f"never says {n} again: {sub[:90]}")
    return out


def sidedness_claims(text: str) -> list[str]:
    return [f"[{m.group(0)}] {s[:130]}"
            for s in sentences(text)
            for m in [SIDEDNESS.search(s)] if m]


# A page that has been corrected describes what it used to say. That is a
# confession, not an offence, and a check that cannot tell them apart trains
# people to ignore it. The first version of this file excluded the <footer> to
# get that right -- and thereby stopped detecting the very error it was written
# for, because issue two's stale "Draft." sat IN the footer. So the test is
# tense, not location.
HISTORICAL = re.compile(
    r"\b(an earlier version|the version published|described this page|"
    r"used to (?:say|read)|had said|for the first hours|"
    r"was fixed|fixed the same day|no longer|previously|"
    r"before publication it|earlier draft)\b", re.I)


# ---------------------------------------------------------------------------
# attributions and unknowability
# ---------------------------------------------------------------------------
#
# Both of these are here because of the second post-publication review of issue
# two, and both are things a machine can find and a person kept not finding.

# "Jacot and colleagues made it formally in npj Breast Cancer in 2018" was put
# on the page on 2026-08-29, taken from a COVERAGE finding, while FIXING an
# attribution gap. The paper is by Tanguy, Cabel, Berger, Pierga, Savignoni and
# Bidard, and contains no Jacot. The standing rule against publishing a claim
# about a third party's document unread has been in the fixture since the 0.754
# incident and its banner prints on every RECENCY run. It did not fire, because
# a rule in prose fires only for someone already looking.
#
# A name is a findable pattern. This does not check whether the name is right --
# nothing here can -- it produces the list that has to be checked, and blocks
# when a name on the page is not in the issue's verified-attributions record.
ATTRIBUTION = re.compile(
    r"\b([A-Z][a-zA-Zà-ÿ'\u2019-]+)\s+"
    r"(?:et\s+al\.?|and\s+colleagues|and\s+co-?workers)")

# "We have not established the direction of that test" was written about a fact
# published on ClinicalTrials.gov's results tab. "MONALEESA-7's direction could
# not be determined" was written when it was in an ASCO abstract. Twice, in one
# document, we turned a thing we had not found into evidence that did not exist.
# Tense matters and this regex did not cover it. On 2026-08-31 the fatal-class
# recall harness seeded "cannot be established from anything published" and the
# check did not fire: it knew "could not be established" and not "cannot be".
# A claim of unknowability is the same claim in either tense, and the present
# tense is the one a page reaches for when the thing is still unknown -- which
# is exactly when the registry has not been searched. Found by the ruler within
# minutes of the ruler existing, which is the argument for building it first.
UNKNOWABILITY = re.compile(
    r"\b(we (?:have not|could not|cannot|can't|are unable to) "
    r"(?:establish|determine|verify|confirm|source|say)|"
    r"(?:can|could)ot be (?:established|determined|verified|confirmed|sourced)|"
    r"cannot be (?:established|determined|verified|confirmed|sourced)|"
    r"could not be (?:established|determined|verified|confirmed|sourced)|"
    r"(?:is|are|remains?) (?:not|un)(?:established|determined|verifiable|knowable)|"
    r"not established by us|we do not know|no way (?:for us )?to (?:know|tell)|"
    r"behind a wall we could not open|every route we tried returned a block)\b", re.I)

# Where a fact about a trial actually lives when the journal is shut.
REGISTRY = re.compile(
    r"\b(clinicaltrials\.gov|clinical trials\.gov|the registry|trial registry|"
    r"registry record|NCT\d{8}|"
    r"FDA review|FDA (?:medical|statistical) review|drugs@fda|accessdata\.fda\.gov|"
    r"EMA assessment|EPAR|ISRCTN|EudraCT|WHO ICTRP)\b", re.I)

# Not every unknowable thing is a trial fact. On 2026-08-31 this check failed a
# sentence on issue three that named THREE places it had looked -- the College's
# report, the review's source, and NHS Digital's annual report -- because none of
# them is a trial registry, and there is no registry of cytology laboratory
# counts. Demanding the wrong artefact teaches people to satisfy the check rather
# than do the search, which is worse than not having it. The rule the docstring
# actually wants is: SAY WHERE YOU LOOKED. For a trial fact that place is a
# registry and the message still says so; for anything else a named place will do.
# A named place, not a gesture: "the paper's statistical section" is not a place
# that was searched, and still fails.
NAMED_PLACE = re.compile(
    r"\b(europe ?pmc|pubmed|\bPMC\b|pmc\d+|crossref|unpaywall|openalex|"
    r"google scholar|researchgate|osf|arxiv|medrxiv|biorxiv|"
    r"the publisher(?:'s|&rsquo;s)? (?:own )?site|publisher(?:'s|&rsquo;s)? site|"
    r"NHS Digital|the College(?:'s|&rsquo;s)? report|"
    r"[A-Z][a-z]+(?:'s|&rsquo;s)? (?:own )?(?:annual )?report|"
    r"university repository|institutional repository|WRAP)\b")


def attributions(text: str) -> list[str]:
    out = []
    for s in sentences(text):
        for m in ATTRIBUTION.finditer(s):
            out.append(f"{m.group(0)} — {s[:120]}")
    return out


def unknowability(text: str) -> list[str]:
    """Claims of unknowability that never name a registry.

    A registry named anywhere in the same sentence is taken as evidence
    somebody went and looked. That is a weak test and deliberately so: the
    point is to make the absence visible, not to adjudicate the search.
    """
    return [f"{s[:170]}" for s in sentences(text)
            if UNKNOWABILITY.search(s)
            and not REGISTRY.search(s) and not NAMED_PLACE.search(s)]


def verified_attributions(slug: str | None) -> set[str]:
    """Names an issue has recorded as checked against the source itself."""
    if not slug:
        return set()
    import json
    for d in (ROOT / "issues").glob("WHU-*-%s" % slug):
        f = d / "attributions.json"
        if f.exists():
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                return set()
            return {a.get("name", "").strip() for a in rec.get("verified", [])
                    if a.get("checked_against")}
    return set()


def self_description(html_text: str) -> list[str]:
    """The page's account of itself, against the page.

    Issue two went live with a footer opening "Draft." and closing "Outstanding:
    not re-gated on this revision, not outside-reviewed, not published", beneath
    a masthead reading "Published 28 August 2026", and stayed that way for
    hours. Nothing checked, because nothing was looking at the page as a
    statement about itself.
    """
    t = plain(html_text)
    published = re.search(r"\bPublished\s+\d{1,2}\s+\w+\s+\d{4}", t)
    if not published:
        return []
    out = []
    for sent in sentences(t):
        if HISTORICAL.search(sent):
            continue
        m = re.search(r"(?:^|\s)(Draft\.|Draft\s*[:\u2014-]|not published|"
                      r"unpublished|not yet published|Outstanding:)", sent)
        if m:
            out.append(f"masthead says {published.group(0)!r}, and the page "
                       f"says {m.group(1)!r}: {sent[:110]}")
    return out


# ---------------------------------------------------------------------------

def lint(html_text: str, slug: str | None = None) -> list[tuple[str, str, str]]:
    """Rows for the board.

    WHAT BLOCKS AND WHAT DOES NOT
    -----------------------------
    Two of these checks are literal — a list length against a stated number,
    and a page calling itself a draft while its masthead says published. Those
    block, because there is no defensible reading in which they are fine.

    The other two are checklists. "Every universal claim on this page, and
    whether it names its scope" is a useful thing to walk before publishing and
    a terrible thing to block on: the first version of this file returned 39
    hits on a page with two real instances. A check that blocks on judgement
    gets waived, and a habit of waiving is worse than no check, because it
    launders the ones that mattered along with the ones that did not.
    """
    text = plain(html_text)
    rows: list[tuple[str, str, str]] = []

    e = enumeration_mismatch(text)
    rows.append(("stated counts match their lists", OK if not e else BAD,
                 "no list contradicts its own count"
                 if not e else " || ".join(e[:3])))

    sd = self_description(html_text)
    rows.append(("page describes itself accurately", OK if not sd else BAD,
                 "the page's account of its own status is consistent"
                 if not sd else " || ".join(sd)))

    names = attributions(text)
    known = verified_attributions(slug)
    unchecked = [a for a in names if a.split()[0] not in known]
    rows.append(("attributions checked against the source",
                 OK if not unchecked else BAD,
                 f"{len(names)} attribution(s), each recorded as checked"
                 if not unchecked else
                 f"{len(unchecked)} name(s) on the page with no record that anyone "
                 f"opened the author list. 'Jacot and colleagues' was published this "
                 f"way, from gate output, while fixing an attribution gap; the paper "
                 f"is by Tanguy et al.: " + " || ".join(unchecked[:3])))

    unk = unknowability(text)
    rows.append(("unknowability claims searched the registries",
                 OK if not unk else BAD,
                 "every claim that something could not be established names where it looked"
                 if not unk else
                 f"{len(unk)} claim(s) that something is unestablished without naming a "
                 f"registry. Two of five findings in the second review were facts sitting "
                 f"on ClinicalTrials.gov: " + " || ".join(x[:90] for x in unk[:3])))

    u = unbounded_universals(text)
    rows.append(("universal claims — scope named?", OK if not u else WARN,
                 "every universal claim over a body of evidence names what it surveyed"
                 if not u else
                 f"{len(u)} claim(s) over studies, trials, literature or coverage with "
                 f"no scope and no attribution. Walk each: " + " || ".join(u[:3])))

    sc = subhead_counts(html_text)
    rows.append(("subhead counts corroborated", OK if not sc else WARN,
                 "every count in a section standfirst is used again in that section"
                 if not sc else " || ".join(sc[:3])))

    c = count_disagreements(html_text)
    rows.append(("counts within a section", OK if not c else WARN,
                 "no section gives one thing two numbers"
                 if not c else " || ".join(c[:3])))

    d = sidedness_claims(text)
    rows.append(("p-value sidedness claims", OK if not d else WARN,
                 "none on the page" if not d else
                 f"{len(d)} claim(s) about the direction of a statistical test. "
                 "Each must trace to a source the ledger says someone opened — "
                 "five of these were published about a paywalled section: "
                 + " || ".join(x[:70] for x in d[:2])))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="deterministic claim lint")
    ap.add_argument("page", help="repo-relative or absolute path to an HTML page")
    ap.add_argument("--slug", help="issue slug, for the verified-attributions record")
    ap.add_argument("--verbose", action="store_true",
                    help="print every hit, not the first few")
    args = ap.parse_args()
    p = Path(args.page)
    if not p.is_absolute():
        p = ROOT / args.page
    html_text = p.read_text(encoding="utf-8")
    rows = lint(html_text, args.slug)
    print()
    for label, st, detail in rows:
        mark = {OK: "  ok ", BAD: " STOP", WARN: " warn"}[st]
        print(f"{mark:>7}  {label:32} {detail if args.verbose else detail[:200]}")
    print()
    if args.verbose:
        text = plain(html_text)
        for name, fn in (("universals", lambda: unbounded_universals(text)),
                         ("counts", lambda: count_disagreements(html_text)),
                         ("enumerations", lambda: enumeration_mismatch(text)),
                         ("subhead counts", lambda: subhead_counts(html_text)),
                         ("sidedness", lambda: sidedness_claims(text))):
            hits = fn()
            if hits:
                print(f"--- {name} ({len(hits)}) ---")
                for h in hits:
                    print("   ", h)
                print()
    return 0 if not any(st == BAD for _l, st, _d in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
