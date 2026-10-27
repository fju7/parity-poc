#!/usr/bin/env python3
"""The binding store — which words in which document support this sentence.

WHY
---
Every control in this repository is about a DOCUMENT: is it held, what kind is
it, was it read, does the ledger overstate it. None is about a SENTENCE. So
nothing anywhere records the only thing that would make verification complete,
deterministic, cheap and repeatable:

    this sentence rests on this source, at this locator, supported by
    these exact words.

Spec: docs/whatholdsup-claim-bindings-spec.md. This module is step 2 of its
build order — the store, and B1, the check that every empirical sentence has a
row. The span checks (B2, B3, B5, B6) come next and all of them need this.

WHAT B1 ALONE IS WORTH
----------------------
On 2026-09-01 the published page carried eight figures from a reconstructed
patient-data comparison that had its own entry in the visible source list and
NO entry in sources.json. No id, no access record, nothing in the library, no
row in the twenty-five sources we publish as our count. It was invisible to the
ledger, the quotation check, the gap list and preflight, because every one of
those starts from the source list and it was not in the source list.

B1 starts from the PAGE. A sentence carrying a figure, a trial name, a registry
id or a quotation, with no binding row, is a defect — whether or not anybody
remembered to write the source down.

R1 FROM THE SPEC, RESTATED HERE BECAUSE IT GOVERNS THIS FILE
-----------------------------------------------------------
This layer may assert only the presence or absence of a span. It may never
assert that a sentence is true. It reports what it can observe and hands the
resolution to a person: a block is a question, not a verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store      # noqa: E402
import source_ledger as ledger    # noqa: E402
import figure_text as FT          # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"
# INFO is a severity, never a preflight state: publish.show() turns any state
# other than ok / BLOCKED / warn into a STOP, so an INFO note is carried in an
# ok row's detail and nowhere else.
INFO = "info"

BUCKETS = ("deterministic", "context", "judgement", "figure")
QUESTIONS = ("locatable", "faithful", "warranted")


# ---------------------------------------------------------------------------
# which sentences must be bound
# ---------------------------------------------------------------------------

FIGURE = re.compile(r"\b\d+\.\d+\b|\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s?%")

# A BARE INTEGER IS A CLAIM, AND FIGURE COULD NOT SEE ONE.
#
# FIGURE matches a decimal, a thousands-separated number, or a percentage.
# Every plain integer was therefore invisible to is_empirical, so the sentences
# below were never classified as empirical, never bound, never counted in the
# 82, and never subject to rule 1 or rule 2:
#
#     "0 Phase 3 efficacy numbers released"      <- the article's whole thesis
#     "14 deaths the whole survival analysis"
#     "That sense is drawn from 157 patients in an open-label trial"
#
# The first of those is the largest type on the page. It survived four gate
# runs and every binder pass by being a number with no decimal point.
#
# This is the same blind spot as modelbind._weight, found the same day in a
# different module: a rule written for what a number LOOKS LIKE, standing in
# for whether it is a claim. There it made a furniture mark unable to see any
# integer under 100. Here it made the binder unable to see any integer at all.
#
# What has to be excluded is not small numbers but NAMES that contain digits.
# Measured on issue one before writing this: adding bare integers alone turned
# 24 more sentences empirical, and 15 of them were "Phase 3" — a study's name,
# no more a quantity than KEYNOTE-054 is. Excluding phase names, calendar dates
# and years leaves NINE, and every one is a real quantitative claim: the zero
# card, the fourteen deaths, three sentences about 157 patients, a 20
# percentage-point gap, a 48-month landmark, and two rubric scores.
#
# Trial names are already dropped by _claim_figures from the ledger's own
# also_called. These three are the same kind of thing and are not in it.
PHASE_NAME = re.compile(r"\bphase\s*\d+[a-z]?\b", re.I)
DAY_MONTH = re.compile(r"\b\d{1,2}\s+(?:January|February|March|April|May|June|"
                       r"July|August|September|October|November|December)\b", re.I)
YEAR = re.compile(r"\b(?:19|20)\d\d\b")
BARE_INT = re.compile(r"(?<![A-Za-z0-9.,-])\d{1,3}(?![0-9.,%])")


def counts_as_claim(sent: str, names: set[str]) -> str:
    """The first bare integer in this sentence that is a quantity, or ""."""
    t = YEAR.sub(" ", DAY_MONTH.sub(" ", PHASE_NAME.sub(" ", sent)))
    for n in names:
        t = re.sub(r"\b%s\b" % re.escape(n), " ", t)
    m = BARE_INT.search(t)
    return m.group(0) if m else ""
NCT = re.compile(r"\bNCT\d{8}\b")
DOI = re.compile(r"\b10\.\d{4,9}/\S+")
QUOTED = re.compile(r"[“\"][^”\"]{25,}[”\"]")


def trial_names(srcs: list[dict]) -> set[str]:
    names = set()
    for s in srcs:
        for n in (s.get("also_called") or []):
            if len(n) > 3:
                names.add(n)
    return names


# CLAIMS IN WORDS, AND CLAIMS ABOUT OURSELVES.
#
# Every trigger above looks for a number, an identifier, a quotation or a
# trial's name. A sentence that says a study is a preprint, retrospective or
# randomised, that its authors "call" or "report" something, or that we "read
# it at source", carries none of those, so it never got a row and no check
# ever read it. Read by hand on 2026-10-18, 282 such sentences on the
# deskilling page held 53 errors -- "the review's body says so" of a word the
# review never uses, a "preprint" that had been published, "read at the
# publisher" of a copy fetched from PubMed Central.
#
# Two triggers, added AFTER the old ones so nothing the old rule bound changes
# reason. A source claim describes a document in words; a process claim says
# what we did or hold, and is routed to B21's store check (is_holdings). The
# lists are words, not grammar: a heading that happens to contain "published"
# is excluded by its markup (page_markup), never by guessing at its wording.
SOURCE_CLAIM = re.compile(
    r"\b(?:preprints?|working\s+papers?|published|accepted|retract(?:ed|ion)"
    r"|corrections?|corrigend(?:um|a)|errat(?:um|a)|peer[-\s]review(?:ed)?"
    r"|conference\s+paper|retrospective|prospective|observational"
    r"|cross-sectional|randomi[sz]ed|cross-?over|colleagues|the\s+authors"
    r"|their\s+own|says|said|calls|called|describes|described|reports|reported"
    r"|finds)\b|\bet\s+al\.|(?<!we )(?<!We )\bfound\b", re.I)
PROCESS_CLAIM = re.compile(
    r"\b(?:read\s+at\s+source|read\s+in\s+full|read\s+directly|at\s+the\s+publisher"
    r"|we\s+read|we\s+opened|opened|could\s+not\s+open|could\s+not\s+read"
    r"|ha(?:ve|s)\s+not\s+read|ha(?:ve|s)\s+not\s+been\s+able|we\s+checked|we\s+check"
    r"|we\s+hold|we\s+found|we\s+searched|we\s+missed|checked\s+against)\b", re.I)
SOURCE_TRIGGER, PROCESS_TRIGGER = "source_claim", "process_claim"


def claim_trigger(sent: str) -> tuple[str, str]:
    """(trigger, why) for a sentence the number-and-name rule does not reach.
    A process claim wins over a source claim: what we did is settled by the
    store, whatever document it also names."""
    m = PROCESS_CLAIM.search(sent)
    if m:
        return PROCESS_TRIGGER, "process claim: %r" % m.group(0)
    m = SOURCE_CLAIM.search(sent)
    if m:
        return SOURCE_TRIGGER, "source claim: %r" % m.group(0)
    return "", ""


def is_empirical(sent: str, names: set[str], *, heading: bool = False,
                 label: str = "") -> tuple[bool, str]:
    """(must_be_bound, why). The why is printed, so a person can disagree with
    the classifier rather than guess at it.

    EVERY SENTENCE GETS A ROW (2026-10-18). The writing rule adopted on
    2026-09-02 is that every sentence in the article is either bound to the
    words it rests on, declared as an inference and shown, or off the page. A
    filter that decided which sentences were "empirical" -- a figure, an
    identifier, a quotation, a trial's name -- left 282 sentences on the
    deskilling page with no row, and 53 of them were wrong. No word list
    recovered them: the best reached 81% of what a reader sorted by hand, and
    the misses were exactly the sentences with no marker at all ("It had not.").

    So the only sentences without a row are the ones the MARKUP says are not
    prose: a heading (h1-h4 -- page_markup) and a source-list role label
    standing alone. The old triggers still name the
    reason when they fire; otherwise the reason is the claim_trigger tag, or
    "sentence" when no word marks it. The tags route, they do not admit."""
    flat = " ".join(sent.split())
    if heading or (label and flat == label):
        return False, ""
    must, why = _old_empirical(sent, names)
    if must:
        return must, why
    rest = sent[len(label):].strip() if label and flat.startswith(label + " ") else sent
    trig, twhy = claim_trigger(rest)
    return True, (twhy if trig else "sentence")


def page_markup(slug: str) -> tuple[set[str], list[str], list[tuple[str, list[str]]]]:
    """(heading texts, source-list labels, source-list entries) from the page.

    Headings are h1-h4. Labels are the source list's <span class="tag">. An
    entry is a <div class="src"> block: its links and its plain text, so a
    sentence such as "Read at source." can be tied to the entry it sits in."""
    import html as _h
    raw = HEAD.sub(" ", _page_html(slug) if not hasattr(ledger, "page_text")
                   else (ledger.page_text(slug) or _page_html(slug)))

    def txt(s: str) -> str:
        return " ".join(_h.unescape(re.sub(r"<[^>]+>", " ", s)).split())
    heads = {txt(m) for m in re.findall(r"<h[1-4]\b[^>]*>(.*?)</h[1-4]>", raw, re.S | re.I)}
    # NOT A RUN-IN BOLD LEAD. <p><strong>…</strong> at a paragraph's start
    # carries headings ("Peer review.") and emphatic claims alike ("It is a
    # retrospective observational study, and that governs everything you can
    # take from it."), and markup cannot tell them apart; a claim without a row
    # is the failure this rule exists to prevent, so only h1-h4 are headings.
    labels = sorted({txt(m) for m in re.findall(r'<span class="tag">(.*?)</span>', raw, re.S)},
                    key=len, reverse=True)
    entries = [(txt(b), re.findall(r'href="([^"]+)"', b))
               for b in re.findall(r'<div class="src">(.*?)</div>', raw, re.S)]
    return {h for h in heads if h}, [l for l in labels if l], entries


def _url_key(u: str) -> str:
    u = (u or "").lower().strip()
    u = re.sub(r"^https?://(?:www\.|dx\.)?", "", u).replace("doi.org/", "")
    return u.rstrip("/")


def entry_subject(sent: str, entries, srcs: list[dict]) -> list[str]:
    """The source a source-list sentence is about, from the entry's link."""
    key = " ".join(sent.split())
    for text, hrefs in entries:
        if key and key in text:
            out = []
            for h in hrefs:
                k = _url_key(h)
                hit = next((s["id"] for s in srcs if k and k in
                            (_url_key(s.get("url")), _url_key("doi.org/" + (s.get("doi") or "")))), None)
                if not hit and "/" in k:
                    hit = next((s["id"] for s in srcs if k.split("/", 1)[-1] and
                                k.split("/", 1)[-1] in json.dumps(s).lower()), None)
                if hit and hit not in out:
                    out.append(hit)
            return out
    return []


def _old_empirical(sent: str, names: set[str]) -> tuple[bool, str]:
    if NCT.search(sent):
        return True, "registry identifier"
    if DOI.search(sent):
        return True, "DOI"
    if QUOTED.search(sent):
        return True, "quoted passage"
    if FIGURE.search(sent):
        return True, "figure"
    bare = counts_as_claim(sent, names)
    if bare:
        return True, "the bare integer %s is a quantity" % bare
    hit = next((n for n in names if re.search(r"\b%s\b" % re.escape(n), sent)), None)
    if hit:
        return True, "names %s" % hit
    return False, ""


# Page furniture is not a claim.
#
# The pages carry no <main> or <article>, so sentence extraction was taking the
# whole document — and the first "empirical sentence" needing a binding was the
# site navigation: "The Category Difference — What Holds Up What Holds Up What
# this is Issue one Issue two Who pays for this". It contains digits and proper
# nouns, so it looked empirical to a check counting digits and proper nouns.
#
# Every denominator this file has reported was inflated by it. Removing the nav,
# header and footer is not cosmetic: it changes what "141 sentences rest on
# nothing" means, and a number that is wrong in our favour is worse than one
# that is merely large.
FURNITURE = re.compile(r"<(nav|header|footer|aside)\b[^>]*>.*?</\1>",
                       re.S | re.I)

# THE HEAD IS NOT PROSE.
#
# <title> is a text node, so tag-stripping leaves it in the page text, and it
# carries no full stop — so the splitter glued the document title to the first
# thing after it and produced this, which B5 then checked against a press
# release as though somebody had written it:
#
#   "The Melanoma Result — What Holds Up 1,137 patients in the Phase 3 trial"
#
# That is the heading-fusion defect plain()'s block sentinel was written to
# stop, arriving from a part of the document plain() never expected to see.
# Nothing in <head> is prose a reader meets as a sentence.
#
# One thing in there IS a claim and is now unchecked either way: the meta
# description says the companies "released no Phase 3 numbers". It ships, it is
# read, and no binding covers it. Recorded in docs/whatholdsup-open-gaps.md.
HEAD = re.compile(r"<head\b[^>]*>.*?</head>", re.S | re.I)

# THE HEADER'S PROSE IS PROSE (2026-10-19).
#
# FURNITURE took the whole <header>, and with it the standfirst -- the first
# five sentences a reader meets, and on deskilling the page's whole argument in
# small: "That study is retrospective, confounded, and its authors list eleven
# limitations." The 19 October revision read "every sentence on the page" and
# corrected 125; none of the standfirst's sentences had a row, so none had been
# read. The masthead's meta line carries dates a reader takes as facts about the
# page. Both are kept, by their markup (p.standfirst, span.meta); the pills, the
# title (an h1, excluded as a heading) and the domain line are still furniture.
# A test draft's <header><h2>…</h2></header> section heads carry neither class
# and are unaffected.
HEADER = re.compile(r"<header\b[^>]*>(.*?)</header>", re.S | re.I)
HEADER_PROSE = re.compile(r'<(p|span)\b[^>]*\bclass="(?:standfirst|meta)"[^>]*>.*?</\1>',
                          re.S | re.I)
FOOTER = re.compile(r"<footer\b[^>]*>(.*?)</footer>", re.S | re.I)
FOOTER_WHY = "footer update entry: a claim about what we changed, bindable to records"


def _header_prose(m: re.Match) -> str:
    return " ".join("<p>%s</p>" % x.group(0) for x in HEADER_PROSE.finditer(m.group(1)))


# A SOURCE-LIST TAG IS NOT PART OF THE SENTENCE (GAP-017, 2026-10-20).
#
# The source list's <span class="tag">Methods</span> sits before the entry's
# text, so the splitter folded it in: "Methods Hall KD, ... ." The audit read
# the tag as the sentence's own words and a ruling removed it (WHU-P02 u70).
# On a study issue the tag is dropped before splitting. NOT on a published
# issue: melanoma, cdk46 and deskilling hold 65 bound rows whose fingerprints
# include their tag, and dropping it there would orphan every one of them.
TAG_LABEL = re.compile(r'<span class="tag">.*?</span>', re.S)


def drop_tag_labels(html: str) -> str:
    """The page without its source-list tags (GAP-017)."""
    return TAG_LABEL.sub(" ", html or "")


def _is_study(slug: str) -> bool:
    try:
        import publish
        return bool(publish.is_study(slug))
    except Exception:
        return False


def page_sentences(slug: str, html: str | None = None) -> list[str]:
    """The page body's sentences. HTML, when given, is read instead of the page
    on disk -- a past commit's page, split exactly as the current one is
    (protected.py compares the first full draft with the page now)."""
    if html is None:
        html = ledger.page_text(slug) if hasattr(ledger, "page_text") else None
    if html is None:
        html = _page_html(slug)
    html = HEAD.sub(" ", html)
    if _is_study(slug):
        html = drop_tag_labels(html)
    html = HEADER.sub(_header_prose, html)
    html = FURNITURE.sub(" ", html)
    # Text the page generates about itself -- an axis, a scorecard's working, a
    # table restating what the article proved -- is checked by furniture.py
    # against the claim its mark makes, not bound to a source. Removing it here
    # stops rule 1 demanding a document for an axis tick. It is NOT skipped:
    # see furniture.py, where each mark buys an obligation rather than a pass.
    import furniture
    html = furniture.strip_marked(html)
    return [" ".join(s.split()) for s in ledger.sentences(ledger.plain(html))]


def footer_sentences(slug: str) -> list[str]:
    """The change log's sentences: what we say we changed, and when.

    corrections_check.py (B18) reads the footer for its figures; nothing gave
    its sentences rows, so a footer claim about our own process -- "we can see
    a trial registry move" -- could be corrected in the body and stand in the
    footer (2026-10-19). Each gets a row tagged process_claim, bindable to
    WHU's records; page_sentences() still excludes the footer, so the body's
    counts and their callers are unchanged."""
    html = ledger.page_text(slug) if hasattr(ledger, "page_text") else None
    if html is None:
        html = _page_html(slug)
    html = HEAD.sub(" ", html)
    out = []
    for m in FOOTER.finditer(html):
        out += [" ".join(s.split()) for s in ledger.sentences(ledger.plain(m.group(1)))]
    return [s for s in out if s]


def _publish():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pub", str(Path(__file__).resolve().parent / "publish.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _page_html(slug: str) -> str:
    m = _publish()
    # issue_cfg, not ISSUES: a study issue (issue.json "study": true) is read
    # the same way (protocol rev 27). An unknown slug still raises.
    cfg = m.issue_cfg(slug)
    return (m.ROOT / cfg["page"]).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# the store
# ---------------------------------------------------------------------------

def fingerprint(sent: str) -> str:
    return hashlib.sha256(" ".join(sent.split()).encode("utf-8")).hexdigest()[:16]


def path(slug: str) -> Path:
    return store.case_dir(slug) / "bindings.json"


def load(slug: str) -> dict:
    p = path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "_what_this_is":
            "One row per empirical sentence on the page: the source it rests "
            "on, the exact words in that source that support it, and who "
            "signed for each of the three questions. Spec: "
            "docs/whatholdsup-claim-bindings-spec.md.",
        "_r1":
            "This file records the presence or absence of a span. It does not "
            "record that a sentence is true. A row with every verdict signed "
            "means the sentence is WARRANTED by named evidence and named "
            "signers -- which is not the same claim and must never be printed "
            "as though it were.",
        "bindings": {},
    }


def save(slug: str, doc: dict) -> None:
    path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def blank_row(sent: str, why: str) -> dict:
    # NOT sent[:600]. It was, to keep the JSON readable, and that quietly made
    # the row's text a DIFFERENT SENTENCE from the one the row is keyed by:
    # three rows across the three issues -- every sentence on the site longer
    # than 600 characters -- stored a version cut off mid-clause. The melanoma
    # one lost "coverage we hold" from the end of a universal negative, and the
    # outside-review packet, which prints this field, asked a reviewer to judge
    # a claim the piece does not make. The identity of a row and the text of a
    # row have to be the same sentence. See test_whatholdsup_packet.py.
    return {
        "sentence": sent,
        "sentence_sha": fingerprint(sent),
        "why_empirical": why,
        "bucket": None,          # declared by whoever writes the sentence
        "source_id": None,
        "document_sha": None,
        "locator_type": None,    # prose | table | field | figure | none
        "locator": None,
        "span": None,
        "envelope": None,
        "scope_words": [],
        "falsifier": None,       # what would show this sentence wrong
        "verdicts": {q: None for q in QUESTIONS},
        "first_seen": date.today().isoformat(),
    }


def scan(slug: str) -> tuple[dict, list[str], list[str]]:
    """(doc, unbound, stale). Adds a blank row for every empirical sentence
    that has none; never deletes, because a sentence that has left the page is
    evidence about a correction and belongs in the record."""
    doc = load(slug)
    rows = doc.setdefault("bindings", {})
    names = trial_names(store.sources(slug))
    # TWO DIFFERENT QUESTIONS, AND THEY WERE THE SAME SET.
    #
    # `live` is "the empirical rule obliges us to bind this". `present` is "this
    # sentence is on the page". The loop below used `live` for both, so a row
    # for a sentence the rule does not call empirical -- a judgement someone
    # chose to show premises for, a comparison carrying no figure of its own --
    # was stamped on_page False with a left_page date while the sentence sat on
    # the page. On 2026-09-08 that happened to "The earlier interval is the wider
    # of the two", and 24 rows across this issue were already carrying the same
    # false departure, the oldest from 1 September.
    #
    # A row saying a sentence left the page when it did not is the failure this
    # file exists to prevent, committed by the file itself: it is a record of a
    # correction that never happened, and Appendix A drops the row from the
    # packet, so the reasoning disappears from the reader's view without anyone
    # deciding that it should.
    present, live, unbound = set(), set(), []
    heads, labels, entries = page_markup(slug)
    srcs = store.sources(slug)
    for sent in page_sentences(slug):
        sha = fingerprint(sent)
        present.add(sha)
        flat = " ".join(sent.split())
        label = next((l for l in labels if flat.startswith(l + " ") or flat == l), "")
        must, why = is_empirical(sent, names, heading=flat in heads, label=label)
        if not must:
            continue
        live.add(sha)
        if sha not in rows:
            rows[sha] = blank_row(sent, why)
            trig = claim_trigger(flat[len(label):] if label else flat)[0]
            if trig:
                rows[sha]["trigger"] = trig
                subj = entry_subject(sent, entries, srcs)
                if subj:
                    # The source-list entry this sentence sits in, read from its
                    # link: what the sentence is ABOUT, not what supports it.
                    rows[sha]["store_subject_markup"] = subj
        rows[sha]["on_page"] = True
        if not rows[sha].get("span"):
            unbound.append(sha)
    for sent in footer_sentences(slug):
        sha = fingerprint(sent)
        if sha in live:
            continue
        present.add(sha)
        live.add(sha)
        if sha not in rows:
            rows[sha] = blank_row(sent, FOOTER_WHY)
            rows[sha]["trigger"] = PROCESS_TRIGGER
            rows[sha]["region"] = "footer"
        rows[sha]["on_page"] = True
        if not rows[sha].get("span"):
            unbound.append(sha)
    stale = []
    for sha, row in rows.items():
        if sha in live:
            row.pop("left_page", None)
            continue
        if sha in present:
            # On the page, just not a sentence the empirical rule obliges us to
            # bind. Whatever else is true of it, it has not left.
            row["on_page"] = True
            row.pop("left_page", None)
            continue
        row["on_page"] = False
        row["left_page"] = row.get("left_page") or date.today().isoformat()
        stale.append(sha)
    save(slug, doc)
    return doc, unbound, stale


# ---------------------------------------------------------------------------
# running the checks FROM the binding, never from a caller's choice
# ---------------------------------------------------------------------------

def covering_spans(row: dict) -> list[tuple[str, str]]:
    """Every (source, span) this row rests on, primary first.

    also_rests_on always counts. premises count for a judgement, whose whole
    claim to rule 2 is that its step runs over them; for any other bucket a
    premise is not what the sentence rests on.

    A span with no source, or a source with no span, is not evidence and is
    dropped rather than defaulting to the primary source — a premise the writer
    did not attribute is exactly the thing a check should not quietly attribute
    for them.
    """
    sid, span = row.get("source_id") or "", row.get("span") or ""
    out = [(sid, span)]
    extra = list(row.get("also_rests_on") or [])
    if (row.get("bucket") or "") == "judgement":
        extra += list(row.get("premises") or [])
    out += [(x.get("source_id") or "", x.get("span") or "") for x in extra]
    seen, keep = set(), []
    for a, b in out:
        if a and b and (a, b) not in seen:
            seen.add((a, b))
            keep.append((a, b))
    return keep


# A NEGATION CAN BE A VALUE RATHER THAN A WORD.
#
# "NCT05933577 still carries no posted results" rests on the trial's own
# registry record, bound BY FIELD PATH -- $.hasResults -- whose value is false.
# B6 looked for a word carrying negative force and reported that the span had
# none. It was right: the record contains no "no results", no "not posted", no
# "none" anywhere in it. The negation is a JSON boolean.
#
# So the check learns to read one evidence format. It is not an exemption: a
# row whose locator resolves to true, or to a value not in this set, flags
# exactly as before.
FIELD_NEGATIVES = {"false", "null", "none", "0", "[]", "{}", '""',
                   "not_posted", "no", "n/a"}
NEGATION_WORDS = {"no", "none", "never", "nothing", "neither", "not"}
_FIELD = re.compile(r'^\s*"[^"]+"\s*:\s*(.+?)\s*$', re.S)


def field_negation(row: dict, cover: list) -> str:
    """Why a structured field carries this row's negation, or "".

    EXACTLY ONE COVERING SPAN, and it must be a field the row named by path.
    A sentence resting on several spans is making a claim wider than any one of
    them, and a single boolean cannot carry a wider claim. Issue one has the
    case that proves it: "no hazard ratio ... appears in either company
    release, in any of the specialist or general coverage we hold, or in the
    trial's own registry record" ALSO rests on $.hasResults, and that field
    settles the registry clause and says nothing whatever about the coverage.
    Clearing its negation on the strength of one boolean would be the check
    reporting an absence over documents it never looked at -- this repository's
    oldest error, committed by the fix for it.
    """
    if not (row.get("locator") or "").strip() or len(cover) != 1:
        return ""
    m = _FIELD.match(cover[0][1])
    if not m:
        return ""
    value = m.group(1).strip().strip(",").strip('"').lower()
    if value not in FIELD_NEGATIVES:
        return ""
    return ("the row names the field %s, and its value is %r — the negation is "
            "the value, not a word in the document"
            % (row.get("locator"), m.group(1).strip()))


# A QUANTIFIER OVER NAMED THINGS IS A COUNT, NOT A WORD.
#
# "KEYNOTE-054 and KEYNOTE-716 are both pembrolizumab against placebo; EACH
# lists overall survival as a secondary endpoint, and EACH registry record
# marks that result NOT_POSTED" -- B6 reported that no span carried the force
# of "each", and no span ever will. "Each" is not a word to be matched. It is
# a claim that the row rests on every thing the sentence names, and that is
# checkable: the sentence names two trials, the ledger resolves both to
# sources, and the row must carry a covering span from each of them.
#
# It fails the way it should. Cite only KEYNOTE-054's record, leave "each" in
# the sentence, and the count comes up short.
#
# ONLY THE DISTRIBUTIVE QUANTIFIERS. "each", "every" and "both" range over
# items. "all" and "any" usually range over a corpus nobody enumerated -- "any
# of the specialist coverage we hold", "no posted results at all" -- and an
# enumeration of named trials says nothing about those.
ENUMERATING = {"each", "every", "both"}


def named_sources(sent: str, slug: str) -> dict:
    """{name found in this sentence: the source id it resolves to}.

    From the ledger's own also_called, which is where trial names are already
    kept, so this cannot become a list of names we happened to meet.
    """
    out = {}
    for src in store.sources(slug):
        sid = src.get("id")
        for name in (src.get("also_called") or []):
            if len(name) > 3 and re.search(r"\b%s\b" % re.escape(name), sent):
                out[name] = sid
    return out


def enumeration_covered(sent: str, cover: list, slug: str) -> str:
    """Why the row covers everything the sentence enumerates, or "".

    Two or more named things, because a quantifier over one thing is not a
    quantifier. Every one of them must resolve to a source the row rests on.
    """
    named = named_sources(sent, slug)
    if len(set(named.values())) < 2:
        return ""
    have = {sid for sid, _ in cover}
    missing = sorted(set(named.values()) - have)
    if missing:
        return ""
    return ("the sentence names %s, and this row rests on a span from every one "
            "of them (%s)"
            % (", ".join(sorted(named)), ", ".join(sorted(set(named.values())))))


# B14 — A BOUNDED NEGATIVE ABOUT ONE DOCUMENT WE HOLD IN FULL.
#
# "Of the 1,137-patient trial it is announcing, the release states that both
# endpoints were met and gives NO FIGURE for either." B6 said no span carried
# "no", and no span will: the claim is about what the whole document does not
# contain, and a span is a thing it does contain.
#
# But this negative is BOUNDED — one source, held in full — which makes it the
# tractable corner of GAP-001. The library-wide version stays open; this one
# can be searched.
#
# WHAT IT DOES NOT DO. It does not decide the sentence is true. It asks one
# mechanical question: does this document carry a figure of the class the
# sentence says is absent, in a sentence that is about the document's OWN
# subject rather than about some other trial? S001 carries exactly one
# efficacy-figure sentence and it names KEYNOTE-942/Phase 2b — the earlier
# trial — so the release does state figures and states none for the trial it
# is announcing, which is what the page says.
#
# IT FAILS PROPERLY. A figure sentence naming the source's own subject, or
# naming no trial at all, is reported with the sentence quoted, for a person to
# read. And a source with no declared `about` cannot be checked at all: the
# check reports that rather than clearing, because a subject nobody declared is
# a subject nobody can be wrong about.
FIGURE_NEGATIVE = re.compile(
    r"\bno\s+(?:\w+\s+){0,3}?(?:figure|number|hazard ratio|interval|p-value|"
    r"percentage|effect size|estimate)s?\b", re.I)
EFFICACY_NOTATION = re.compile(
    r"\b(?:HR\s*[=:]|hazard ratio|95%\s*CI|confidence interval|"
    r"p\s*[=<>]\s*0?\.\d+|one-sided p|two-sided p)", re.I)


def bounded_figure_negative(row: dict, cover: list, sent: str,
                            slug: str) -> tuple[str, str]:
    """(verdict, why). verdict is "clear", "candidates", or "" for not applicable."""
    if not FIGURE_NEGATIVE.search(sent):
        return "", ""
    sids = {sid for sid, _ in cover}
    if len(sids) != 1:
        return "", ""
    sid = sids.pop()
    if sid not in store.held(slug):
        return "", ""
    src = next((x for x in store.sources(slug) if x.get("id") == sid), {})
    subject = (src.get("about") or "").strip()
    if not subject:
        return "candidates", ("%s declares no `about`, so nothing here knows which "
                              "trial the document is the announcement OF, and a "
                              "subject nobody declared is a subject nobody can be "
                              "wrong about" % sid)
    import spancheck as SC
    text = SC._norm(SC._text(slug, sid) or "")
    subj = re.compile(r"\b%s\b" % re.escape(subject), re.I)
    others = trial_names(store.sources(slug)) - {subject}
    bad = []
    for piece in re.split(r"(?<=[.!?])\s+", text):
        if not EFFICACY_NOTATION.search(piece):
            continue
        names_other = any(re.search(r"\b%s\b" % re.escape(n), piece, re.I)
                          for n in others)
        if subj.search(piece) or not names_other:
            bad.append(piece[:180])
    if bad:
        return "candidates", ("%d figure sentence(s) in %s are about its own subject "
                              "or name no other trial — read them: %s"
                              % (len(bad), sid, " || ".join(bad[:2])))
    return "clear", ("every sentence in %s carrying a hazard ratio, interval or "
                     "p-value names a trial other than %s, which is what the "
                     "document is announcing" % (sid, subject))


# ---------------------------------------------------------------------------
# B19, B20, B21 — a sentence may not be surer than what it rests on
# ---------------------------------------------------------------------------
#
# A three-judge read of all 80 judgement sentences in the four WHU test issues
# (2026-10) found that every confirmed reasoning error leaned the same way:
# toward more certainty than the cited source allows.
#
#   "The evidence does not support choosing between those three on the basis
#    of age or sex."  Its premise says the moderators "should be interpreted
#    cautiously". The caution became a verdict.
#   "Confidence in direction is high ..."  The premise it cites says the Task
#    Force concludes "with moderate certainty".
#
# B6 asks whether a hedge in the SENTENCE maps to the span. Nothing asked the
# converse -- whether a hedge in the SPAN survives into the sentence -- and
# B6's flags are read by negatives.py as its own worklist, so these are numbered
# rather than filed under B6.
#
# R1 still governs. B19 reports a dropped word, not a false sentence; B20
# compares two stated grades, not the evidence; B21 routes a sentence to the
# store and lets epistemic.py answer. Each says what it saw and stops.

EVIDENCE_HEDGES = (
    "may", "might", "could", "possibly", "probably", "likely", "suggest",
    "suggests", "suggestive", "appear", "appears", "appeared", "cautious",
    "cautiously", "preliminary", "tentative", "uncertain", "uncertainty",
    "exploratory", "hypothesis", "hypothesis-generating", "limited",
    "low certainty", "very low", "low quality", "not statistically significant",
    "trend", "perhaps", "would tend to", "arguably",
    # 2026-10-18: "The population being examined plausibly changed" (deskilling
    # faec9851) carries its hedge and was reported as carrying none.
    "plausibly", "plausible")
SENTENCE_HEDGES = EVIDENCE_HEDGES + (
    "modest", "unclear", "not a finding", "cannot", "does not show", "too few",
    "low", "weak")
# A sentence that NEGATES what the evidence hedges has turned "we cannot tell"
# into "it is not so" -- the T01 s85 failure. Round 1 let a negation cancel
# every hedge in the sentence, and that silenced T02 s40 ("limited evidence,
# graded as no evidence") and s68 ("at very low certainty ... no evidence"),
# which keep their hedges. A negation now removes the hedge only where the
# sentence has no other hedge word -- which is to say it never cancels one; it
# only names what the sentence did in the report.
NEGATING = ("does not support", "no evidence")


def _words(words) -> re.Pattern:
    alts = sorted(words, key=len, reverse=True)
    return re.compile(r"\b(?:%s)\b" % "|".join(
        r"\s+".join(re.escape(p) for p in w.split()) for w in alts), re.I)


_EVIDENCE_HEDGE = _words(EVIDENCE_HEDGES)
_SENTENCE_HEDGE = _words(SENTENCE_HEDGES)
_NEGATING = _words(NEGATING)


def evidence_spans(row: dict) -> list[tuple[str, str]]:
    """What a sentence's certainty is measured against.

    A judgement: its premises, which are what its step runs over. Anything
    else: its span and its also_rests_on. Not covering_spans(), which also
    counts a judgement's primary span -- the brief for these checks names the
    premises, and a judgement here carries none.
    """
    if (row.get("bucket") or "") == "judgement":
        extra = list(row.get("premises") or [])
        out = []
    else:
        extra = list(row.get("also_rests_on") or [])
        out = [(row.get("source_id") or "", row.get("span") or "")]
    out += [(x.get("source_id") or "", x.get("span") or "") for x in extra]
    return [(a, b) for a, b in out if b]


# "Between February 2014 and May 2015" is a date, not a hedge (T04 s16). Only
# the capitalised word, and only where a date says it is the month: followed
# by a year, a day number or "of", or preceded by a day number. A lowercase
# "may" is always read as a hedge.
_MAY_MONTH_AFTER = re.compile(r"\s+(?:\d{4}\b|\d{1,2}(?:st|nd|rd|th)?\b|of\b)")
_MAY_MONTH_BEFORE = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+$")


def _hedges(pattern: re.Pattern, text: str) -> list[str]:
    out = []
    for m in pattern.finditer(text or ""):
        if m.group(0) == "May" and (_MAY_MONTH_AFTER.match(text, m.end())
                                    or _MAY_MONTH_BEFORE.search(text[:m.start()])):
            continue
        out.append(" ".join(m.group(0).lower().split()))
    return out


def sentence_hedges(sent: str) -> list[str]:
    return _hedges(_SENTENCE_HEDGE, sent)


def hedge_dispositions(row: dict) -> dict[str, dict]:
    """word -> entry, for the row's signed B19 dispositions.

    A HEDGE WORD MAY BE DISPOSED OF, BY A PERSON, IN THE ROW -- the same
    discipline as B6's scope_words and B20's grade_departure. "they appear in
    about 36% of the included studies" trips B19 on 'appear', which there
    means 'occur': the source states a count and hedges nothing. Left alone
    that flag is the one the operator learns to scroll past. So the row may
    carry `hedge_dispositions`: [{word, why, by, on}]. An entry with a blank
    why or by is not a signature and is ignored. 2026-10-18.
    """
    out = {}
    for d in (row.get("hedge_dispositions") or []):
        if isinstance(d, dict) and (d.get("word") or "").strip() and \
                (d.get("why") or "").strip() and (d.get("by") or "").strip():
            out[" ".join(d["word"].lower().split())] = d
    return out


def b19_hedge_dropped(row: dict) -> list[dict]:
    """The evidence hedges and the sentence does not. WARN, never a block.

    A hedge word the row disposes of (hedge_dispositions) is reported as INFO,
    with the signer's reason, rather than dropped: the record still says the
    evidence used the word."""
    sent = row.get("sentence") or ""
    hits = []
    for sid, span in evidence_spans(row):
        for w in _hedges(_EVIDENCE_HEDGE, span):
            if (w, sid) not in hits:
                hits.append((w, sid))
    if not hits or sentence_hedges(sent):
        return []
    disposed = hedge_dispositions(row)
    live = [(w, sid) for w, sid in hits if w not in disposed]
    done = [(w, sid) for w, sid in hits if w in disposed]
    out = []
    if live:
        why = "the evidence says %s; the sentence carries no hedge" % ", ".join(
            "%r (%s)" % (w, sid) for w, sid in live[:4])
        if _NEGATING.search(sent):
            why += (" -- it negates (%r), which turns the evidence's caution into "
                    "a verdict" % _NEGATING.search(sent).group(0))
        # An ADDED sentence (fix 2: a finding the page left out, drafted by the
        # omission ruling) is a STOP, not a WARN: it was written from the span,
        # so a dropped hedge is the draft's error, never a judgement call.
        added = (row.get("origin") or "") == OMISSION_ADD
        out.append({"check": "B19", "verdict": HEDGE_DROPPED_ADDED if added else "evidence hedge dropped",
                    "hedge": live[0][0], "why": why})
    if done:
        why = "; ".join("the evidence says %r (%s), disposed of by %s%s: %s"
                        % (w, sid, disposed[w]["by"],
                           " on %s" % disposed[w]["on"] if disposed[w].get("on") else "",
                           disposed[w]["why"]) for w, sid in done[:4])
        out.append({"check": "B19", "verdict": "evidence hedge disposed",
                    "hedge": done[0][0], "why": why})
    return out


# B19, the significance qualifier. A source's "no significant change" is not
# "no change": the first says the test could not tell the phases apart, the
# second says they are the same. Deskilling printed "which is no change" for
# S043's "no significant change", and "their confidence did not fall" for
# S017's "did not significantly decline (p = 0.202)". The general hedge list
# could not see either: "significant" is a hedge only in this construction.
# So: evidence that negates significance ABOUT A CHANGE OR DIFFERENCE, and a
# sentence asserting no change with no significance word, is a WARN. It is
# disposable through hedge_dispositions on the word "significant". 2026-10-18.
_SIG_NEGATED = re.compile(
    r"\b(?:no|not|non-?)\s?(?:statistically\s)?significant(?:ly)?\b"
    r"|\bdid not (?:statistically\s)?significantly\b"
    r"|\bnot statistically (?:significant|different)\b", re.I)
_SIG_ABOUT = re.compile(
    r"\b(?:chang\w*|differ\w*|effect\w*|declin\w*|decreas\w*|increas\w*|"
    r"improv\w*|reduc\w*|rise|rose|fall|fell|drop\w*|impact\w*|associat\w*)\b", re.I)
_SENT_NO_CHANGE = re.compile(
    r"\b(?:no (?:change|difference|effect|increase|decrease|decline|improvement|"
    r"reduction|rise|fall|drop)|did not (?:fall|change|decline|drop|rise|differ|"
    r"increase|decrease|improve)|unchanged|indistinguishable|no (?:faster|slower|"
    r"better|worse))\b", re.I)
_SENT_SIG = re.compile(r"significan|statistical", re.I)


def b19_significance_dropped(row: dict) -> list[dict]:
    """'no significant change' in the evidence, 'no change' in the sentence."""
    sent = row.get("sentence") or ""
    said = _SENT_NO_CHANGE.search(sent)
    if not said or _SENT_SIG.search(sent):
        return []
    hits = []
    for sid, span in evidence_spans(row):
        for m in _SIG_NEGATED.finditer(span or ""):
            if _SIG_ABOUT.search(span[m.start():m.end() + 40]) or "differ" in m.group(0).lower():
                hits.append((m.group(0), sid))
                break
    if not hits:
        return []
    disposed = hedge_dispositions(row)
    if "significant" in disposed:
        d = disposed["significant"]
        return [{"check": "B19", "verdict": "evidence hedge disposed", "hedge": "significant",
                 "why": "the evidence says %r (%s), disposed of by %s%s: %s"
                        % (hits[0][0], hits[0][1], d["by"], " on %s" % d["on"] if d.get("on") else "",
                           d["why"])}]
    return [{"check": "B19", "verdict": "significance qualifier dropped", "hedge": "significant",
             "why": "the evidence says %s; the sentence says %r with no significance qualifier"
                    % (", ".join("%r (%s)" % h for h in hits[:3]), said.group(0))}]


# B20. The ladder is the brief's. "moderate to good" and "reasonably high" sit
# between moderate and high: above anything a source grades moderate, below a
# source's "high".
WHU_LEVELS = {"very low": 0, "low": 1, "moderate": 2, "moderate to good": 3,
              "moderate-to-good": 3, "reasonably high": 3, "high": 4}
GRADE_RANK = {"very low": 0, "low": 1, "moderate": 2, "high": 4}
GRADE_ANCHORS = {"certainty", "quality", "confidence", "grade", "cinema"}
CONFIDENCE_SENTENCE = re.compile(r"^\W*confidence\b(?:\s+(?:in|that)\b|.*?\bis\b)",
                                 re.I | re.S)
_WHU_LEVEL = _words(WHU_LEVELS)


def whu_level(sent: str) -> str:
    """The level a 'Confidence ...' sentence states, or "". "" for a sentence
    that is not one."""
    m = CONFIDENCE_SENTENCE.match(sent)
    if not m:
        return ""
    after = sent[m.end():]
    if not re.search(r"\bis\b", sent[:m.end()], re.I):
        is_ = re.search(r"\bis\b", after, re.I)
        if is_:
            after = after[is_.end():]
    lv = _WHU_LEVEL.search(after)
    return " ".join(lv.group(0).lower().split()) if lv else "?"


def stated_grades(span: str) -> list[str]:
    """Every certainty grade the span states: very low, low, moderate or high
    within six words of certainty, quality, confidence, GRADE or CINeMA."""
    toks = re.findall(r"[A-Za-z]+", span)
    low = [t.lower() for t in toks]
    out = []
    for i, t in enumerate(low):
        if t not in ("low", "moderate", "high"):
            continue
        g = "very low" if t == "low" and i and low[i - 1] == "very" else t
        near = low[max(0, i - 6):i] + low[i + 1:i + 7]
        if GRADE_ANCHORS & set(near):
            out.append(g)
    return out


def b20_confidence_ceiling(row: dict) -> list[dict]:
    """WHU's stated confidence against the highest grade its evidence states.

    STOP when the sentence is surer than every grade it cites, unless the row
    carries `grade_departure`: a person's written reason for going above it.
    STOP, too, when no premise states a grade at all and the sentence claims
    more than low confidence: a level with no cited grade is a level nobody can
    check (T03 s53 and T01 s82 rest on reviews that grade their evidence low,
    and cite no span saying so). "low" and "very low" claim nothing a missing
    grade could undercut, so they pass. grade_departure lifts the ceiling STOP
    only, as before: a missing grade is cured by citing the grade.
    """
    sent = row.get("sentence") or ""
    level = whu_level(sent)
    if not level:
        return []
    if level == "?":
        return [{"check": "B20", "verdict": "confidence level unreadable",
                 "why": "a 'Confidence ...' sentence whose level is none of %s"
                        % ", ".join(WHU_LEVELS)}]
    grades = [(g, sid) for sid, span in evidence_spans(row)
              for g in stated_grades(span)]
    if not grades:
        if WHU_LEVELS[level] <= GRADE_RANK["low"]:
            return []
        return [{"check": "B20", "verdict": "confidence stated without a cited grade",
                 "level": level,
                 "why": "states %r; no premise states a certainty grade, so nothing "
                        "the sentence cites bounds it. Cite the grade" % level}]
    top = max(GRADE_RANK[g] for g, _ in grades)
    if WHU_LEVELS[level] <= top:
        return []
    cited = ", ".join("%s (%s)" % (g, sid) for g, sid in grades)
    if (row.get("grade_departure") or "").strip():
        return []
    return [{"check": "B20", "verdict": "confidence above its cited grade",
             "level": level,
             "why": "states %r; the highest grade its evidence states is %s. "
                    "A departure needs grade_departure on the row" % (level, cited)}]


# B21. A sentence about OUR holdings -- what we hold, opened, obtained, searched
# -- is true or false according to the source store, not according to any
# document. Citing one makes it look as though a document supports it, and
# outside judges split on exactly these (14 of 80 judgements in the test
# issues). epistemic.py already adjudicates the class against the store.
#
# Subject, not phrase. "the reviews we hold agree on the direction" carries
# "we hold" and is a claim about the world; the sentences here make OUR
# holdings or actions the subject, or end on a clause saying we have not
# opened what the sentence names.
HOLDINGS = re.compile(
    r"^\W*(?:we\s+(?:hold|have\s+not\s+(?:yet\s+)?(?:opened|read|checked|obtained)"
    r"|did\s+not\s+(?:obtain|open|read|check)|could\s+not\s+(?:obtain|open|reach))\b"
    r"|our\s+search\b)"
    r"|,\s*which\s+we\s+have\s+not\s+(?:yet\s+)?(?:opened|read|checked|obtained)\b",
    re.I)


def is_holdings(sent: str, trigger: str = "") -> bool:
    """A sentence about what we hold or did. The subject phrasing above, or a
    row the scan marked as a process claim (PROCESS_CLAIM): the same check, one
    door, so the two cannot drift."""
    return bool(HOLDINGS.search(sent or "")) or trigger == PROCESS_TRIGGER


# PROTECTED SENTENCES (post-study fix 1, 2026-10-27). The page's restatement of
# its question, and its statements of what we held, read, searched or did not
# read, are not claims a source can support: no document records what WHU read.
# On WHU-S08 the conclusion judge and the audit read exactly these against the
# bound source and found them unsupported, and the ruling model, told to keep
# only what the source supports, narrowed the question to the stocktake's own
# subject and removed every statement of what was not read
# (docs/whu-omissions-investigation-2026-10.md, section 3). A protected
# sentence is never put to a source-support ruling; a person reads it, and
# protected.py stops the preflight if one left the page without a person's
# sign-off.
#
# The class is is_holdings (B21's detector, unchanged) widened by two narrow
# phrasings, plus a row marker for whatever the phrasing misses. HOLDINGS itself
# is not widened: B21 routes what it matches to the store, on every issue.
PROTECTED_KINDS = ("question", "reading")
QUESTION_RESTATEMENT = re.compile(
    r"^\W*(?:the|our|this)\s+question\s+(?:here\s+)?(?:is|was|we\s+(?:ask|asked|answer|answered))\b",
    re.I)
READING = re.compile(
    r"(?:^\W*|[;:,]\s*|\b(?:and|but)\s+)we\s+(?:"
    r"drew\s+on|searched|read\s+(?:it|them|this|these|only)\b"
    r"|did\s+not\s+(?:search|read|open|obtain|check|look\s+at)"
    r"|have\s+not\s+(?:yet\s+)?(?:read|opened|searched|checked|obtained))\b"
    r"|^\W*(?:of|from)\s+the\s+[^,;]{1,120},\s*we\s+(?:drew|read|cite|used|took)\b"
    # "behind paywalls we could not pass" (WHU-S07): wherever it stands, "we
    # could not" + an access verb reports what we were unable to do. Not
    # "find": "we could not find any trial showing X" is an absence-of-evidence
    # claim (the GAP-001 class) and stays subject to the checks.
    r"|\bwe\s+could\s+not\s+(?:pass|access|obtain|open|reach|read)\b",
    re.I)
# A sentence that also states a finding is never protected by its phrasing:
# "We searched PubMed and found no trials" reports a search AND a result, and
# the result must stay audited. A person may still protect it with the row
# marker (advisor's review of fix 1, 2026-10-27).
STATES_FINDING = re.compile(
    r"\b(?:found|no\s+evidence|no\s+stud(?:y|ies)|no\s+trials?|none\s+of|show(?:s|ed|n)?|demonstrated)\b",
    re.I)


def protected_kind(sent: str, row: dict | None = None) -> str | None:
    """"question", "reading", or None. A row's `protected` marker, when it names
    one of PROTECTED_KINDS, wins; otherwise the sentence's own phrasing, unless
    the sentence also states a finding (STATES_FINDING)."""
    mark = (row or {}).get("protected")
    if mark in PROTECTED_KINDS:
        return mark
    s = sent or ""
    if STATES_FINDING.search(s):
        return None
    if QUESTION_RESTATEMENT.search(s):
        return "question"
    if HOLDINGS.search(s) or READING.search(s):
        return "reading"
    return None


def support_ids(row: dict) -> list[str]:
    ids = [row.get("source_id")]
    ids += [x.get("source_id") for x in (row.get("also_rests_on") or [])]
    ids += [x.get("source_id") for x in (row.get("premises") or [])]
    return list(dict.fromkeys(i for i in ids if i))


def b21_holdings(row: dict, slug: str) -> list[dict]:
    """Route a holdings sentence to the store, and refuse a document as its support.

    `rests_on_store` lists the source ids whose STORE RECORD the sentence is
    about. It is the subject, not support: epistemic.declared_sources reads the
    ids off the row to know which record to ask.
    """
    sent = row.get("sentence") or ""
    declared = row.get("rests_on_store") or []
    # A ROW DECLARED A JUDGEMENT IS NOT ROUTED HERE BY ITS TAG. The scan's
    # process_claim tag is a word match ("we missed"), set before anyone has
    # read the sentence; a person who has declared the row a judgement, with
    # premises in held documents and a step, has answered the question the tag
    # asked. Routing it to the store anyway makes its premises a "holdings
    # sentence cites a document" BAD -- the declared bucket overruled by a
    # regex. The subject phrasing (HOLDINGS) still routes it: a judgement that
    # says "we hold" is about the store whatever its bucket. A process_claim
    # row NOT declared a judgement is routed exactly as before. 2026-10-18,
    # deskilling d03dd93f.
    trigger = "" if (row.get("bucket") or "") == "judgement" else (row.get("trigger") or "")
    # A process-claim row that the old subject phrasing would not have caught:
    # nobody has declared its subject yet, so the declaration findings below are
    # not its to raise. Its subject is the source-list entry it sits in, if any,
    # else whatever the text names; with neither, it is NOT EVALUATED (warn),
    # never "not in sources" -- "We check the sources on this page" is about no
    # one document.
    process_only = (trigger == PROCESS_TRIGGER
                    and not HOLDINGS.search(sent) and not declared)
    markup = row.get("store_subject_markup") or []
    if not is_holdings(sent, trigger):
        if declared:
            return [{"check": "B21", "verdict": "declared to the store, not a holdings sentence",
                     "why": "rests_on_store is set and the sentence is not about "
                            "what we hold; a person decides which is wrong"}]
        return []
    # A ROW RESTING ON WHU'S RECORDS (B24) has its support; with no store
    # subject declared or marked up, there is nothing for the store to answer
    # and nothing missing. It is still refused a document as support below if
    # it cites one, and a row with a store subject is still checked against it.
    if record_bound(row, slug) and not declared and not markup and not support_ids(row):
        return []
    out = []
    import epistemic as E
    cited = support_ids(row)
    try:
        known = {r.get("id") for r in E._sources(slug)}
    except (Exception, SystemExit):
        known = None
    unknown = [d for d in declared if known is not None and d not in known]
    if cited:
        out.append({"check": "B21", "verdict": "holdings sentence cites a document",
                    "why": "a sentence about what we hold is settled by the store, "
                           "and this one cites %s as support" % ", ".join(cited)})
    elif unknown:
        out.append({"check": "B21", "verdict": NOT_IN_SOURCES,
                    "why": "rests_on_store names %s, which has no entry; add one with "
                           "source_ledger.py add (state not_opened)" % ", ".join(unknown)})
    elif process_only or (markup and not declared):
        pass
    elif not declared:
        # Round 3: a holdings sentence that names no entry, and whose text names
        # none either, is about a document the store has never recorded -- T02
        # s46's meta-analysis, s61's feeding study, T04 s46's errata. The store
        # cannot answer for a document it has no row for: the cure is the row.
        #
        # But "names no entry" is not "has no entry". The first version stopped
        # on two published sentences whose documents ARE registered ("We could
        # not obtain PALMARES-2 itself" -- S011, S021; "We have not opened
        # Sparrow, Liu and Wegner's 2011 Science paper" -- S010), only because
        # their rows predate rests_on_store. So the text is asked first, with
        # epistemic's own resolver; a sentence that names a registered source is
        # undeclared, not unregistered.
        try:
            named = list(getattr(E, "resolve", lambda s_, g: [])(sent, slug))
        except (Exception, SystemExit):
            named = []
        if named:
            out.append({"check": "B21", "verdict": "holdings sentence not declared to the store",
                        "why": "the text names %s, which has an entry; declare it in "
                               "rests_on_store" % ", ".join(named)})
        else:
            out.append({"check": "B21", "verdict": NOT_IN_SOURCES,
                        "why": "neither the row nor the text names a source; if the "
                               "document has an entry, declare it in rests_on_store, "
                               "and if not, add one with source_ledger.py add (state "
                               "not_opened)"})
    try:
        verdicts = E.check_sentence(sent, slug, declared=list(declared) or list(markup) or None)
        if process_only:
            subj = list(declared) or list(markup) or list(E.resolve(sent, slug))
            verdicts += E.route_check(sent, subj, slug)
    except (Exception, SystemExit) as exc:
        verdicts = [{"verdict": E.NOT_EVALUATED, "why": "%s: %s" % (type(exc).__name__, exc)}]
    if not verdicts:
        out.append({"check": "B21", "verdict": "store check not evaluated",
                    "why": "epistemic.check_sentence reads no claim about our access "
                           "in this sentence; nothing has checked it against the store"})
    for v in verdicts:
        if v.get("class") == getattr(E, "UNCLASSIFIED", "unclassified"):
            out.append({"check": "B21", "verdict": "source unclassified",
                        "why": "%s carries document_class unclassified; set it to "
                               "document or record_about" % v.get("source")})
            continue
        if v["verdict"] == E.NOT_EVALUATED and unknown and v.get("source") in unknown:
            continue                       # already the STOP above
        if v["verdict"] == getattr(E, "WARN_VERDICT", "WARN"):
            out.append({"check": "B21", "verdict": "we hold its abstract — say so",
                        "why": "%s is abstract_held; the sentence says we have not "
                               "opened or obtained it" % v.get("source")})
            continue
        if v["verdict"] == E.FAIL:
            out.append({"check": "B21", "verdict": "store disagrees",
                        "why": "%s: asserts %s, store records %s"
                               % (v.get("source"), v.get("asserted"), v.get("recorded"))})
        elif v["verdict"] == E.NOT_EVALUATED:
            out.append({"check": "B21", "verdict": "store check not evaluated",
                        "why": v.get("why") or ""})
    return out


# ---------------------------------------------------------------------------
# B24 — a sentence resting on WHU's own committed records
# ---------------------------------------------------------------------------
#
# "We read it at the publisher", "a draft of this section said nothing false
# had been printed", "neither is what a reader takes from a review date" --
# claims about what WHU did or decided. Their evidence is not a document in the
# library but a record in the repository: a ruling under review/, an entry in
# corrections.md, a line in sources.json or watch.json. Batch 4 found eight such
# sentences supported and could bind none of them: rests_on_store takes a
# source id, and a ruling is not a source. 2026-10-18.
#
# So a row may carry `rests_on_record`: [{path, quote, sha}]. `path` is
# repo-relative and must be under docs/ or the issue's own case directory;
# `quote` must occur in the file AS COMMITTED AT HEAD (the working tree is not
# a record -- seventy uncommitted files sit in it as this is written), under
# spancheck's normalisation; `sha` is the file's git blob sha when the binding
# was made. A quote no longer in the committed file is BAD: the sentence rests
# on something that is not there. A file whose blob has moved on, with the
# quote still in it, is a WARN -- the record changed under the binding, and a
# person should look, but nothing is false yet.
RECORD_CHANGED = "record changed since binding"
RECORD_GONE = "record quote not in the committed file"
RECORD_REFUSED = "record path is not a WHU record"
RECORD_INCOMPLETE = "record binding incomplete"
_COMMITTED_CACHE: dict[str, tuple[str, str] | None] = {}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _committed(path: str) -> tuple[str, str] | None:
    """(blob sha, text) of `path` as committed at HEAD, or None if it is not
    committed. Read through git, never from the working tree."""
    if path in _COMMITTED_CACHE:
        return _COMMITTED_CACHE[path]
    import subprocess
    root = str(_repo_root())
    try:
        sha = subprocess.run(["git", "-C", root, "rev-parse", "HEAD:%s" % path],
                             capture_output=True, text=True, check=True).stdout.strip()
        text = subprocess.run(["git", "-C", root, "cat-file", "blob", sha],
                              capture_output=True, check=True).stdout.decode("utf-8", "replace")
        out = (sha, text)
    except (subprocess.CalledProcessError, OSError):
        out = None
    _COMMITTED_CACHE[path] = out
    return out


def _untagged(text: str) -> str:
    """A record's text with HTML tags removed, compared under spancheck's
    normalisation. corrections.md writes <q>Last reviewed 30 August 2026</q>
    inside its sentences; a quote of the sentence is a quote of its words, with
    or without the markup (2026-10-18)."""
    import spancheck as SC
    return SC._norm(_HTML_TAG.sub("", text or ""))


# A TAG, NOT A LESS-THAN SIGN. "<[^>]+>" over a whole sources.json deletes from
# "p<0.001" to the next ">" anywhere in the file -- the hazard CLAUDE.md records
# for text.normalise (62k of a page lost to one stray "<"). Only an element
# name, an optional attribute run with no angle bracket in it, and a close.
_HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]{0,200})?/?>")


_COMMIT_CACHE: dict[str, tuple[str, str] | None] = {}


def _commit_message(commit: str) -> tuple[str, str] | None:
    """(full sha, message) of a commit in main's history, or None. A commit that
    is not an ancestor of main -- an unmerged branch, a stash, a typo that
    resolves to nothing -- is not a record of this publication."""
    c = (commit or "").strip()
    if c in _COMMIT_CACHE:
        return _COMMIT_CACHE[c]
    import subprocess
    root = str(_repo_root())
    out = None
    try:
        full = subprocess.run(["git", "-C", root, "rev-parse", "--verify", "%s^{commit}" % c],
                              capture_output=True, text=True, check=True).stdout.strip()
        anc = subprocess.run(["git", "-C", root, "merge-base", "--is-ancestor", full, "main"],
                             capture_output=True)
        if anc.returncode == 0:
            msg = subprocess.run(["git", "-C", root, "show", "-s", "--format=%B", full],
                                 capture_output=True, check=True).stdout.decode("utf-8", "replace")
            out = (full, msg)
    except (subprocess.CalledProcessError, OSError):
        out = None
    _COMMIT_CACHE[c] = out
    return out


def commit_entry(commit: str, quote: str) -> dict:
    """The entry to write for a commit message: checked now. Raises ValueError
    rather than return an entry that would fail B24."""
    import spancheck as SC
    got = _commit_message(commit)
    if got is None:
        raise ValueError("%s: not a commit in main's history" % commit)
    if SC._norm(quote) not in SC._norm(got[1]):
        raise ValueError("%s: quote not in the commit message: %s" % (commit, quote[:60]))
    return {"commit": got[0], "quote": quote}


def record_path_ok(path: str, slug: str) -> bool:
    """Repo-relative, inside docs/ or this issue's case directory."""
    p = (path or "").strip()
    if not p or p.startswith("/") or ".." in Path(p).parts:
        return False
    if p.startswith("docs/"):
        return True
    try:
        case = store.case_dir(slug).resolve().relative_to(_repo_root().resolve()).as_posix()
    except (Exception, SystemExit):
        return False
    return p.startswith(case + "/")


def record_entry(path: str, quote: str, slug: str) -> dict:
    """The entry to write: checked now, with the blob sha it was checked at.
    Raises ValueError rather than return an entry that would fail B24."""
    import spancheck as SC
    if not record_path_ok(path, slug):
        raise ValueError("%s: not under docs/ or the issue's case directory" % path)
    got = _committed(path)
    if got is None:
        raise ValueError("%s: not committed at HEAD" % path)
    if _untagged(quote) not in _untagged(got[1]):
        raise ValueError("%s: quote not in the committed file: %s" % (path, quote[:60]))
    return {"path": path, "quote": quote, "sha": got[0]}


def b24_records(row: dict, slug: str) -> list[dict]:
    """Every record the row names, checked against HEAD."""
    import spancheck as SC
    out = []
    for e in row.get("rests_on_record") or []:
        if isinstance(e, dict) and (e.get("commit") or "").strip():
            # A COMMIT MESSAGE IS A RECORD TOO (2026-10-18): the drafting
            # commit 0ee52b8 is the only place it is written that lint_claims
            # forced the papers open. Immutable, so no sha: the quote must be
            # in the message of a commit in main's history.
            quote = (e.get("quote") or "").strip()
            got = _commit_message(e["commit"])
            if not quote:
                out.append({"check": "B24", "verdict": RECORD_INCOMPLETE,
                            "why": "a commit binding needs commit and quote: %r" % (e,)})
            elif got is None:
                out.append({"check": "B24", "verdict": RECORD_GONE,
                            "why": "%s is not a commit in main's history" % e["commit"][:12]})
            elif SC._norm(quote) not in SC._norm(got[1]):
                out.append({"check": "B24", "verdict": RECORD_GONE,
                            "why": "commit %s's message does not contain %r" % (got[0][:12], quote[:80])})
            continue
        path = (e.get("path") or "").strip() if isinstance(e, dict) else ""
        quote = (e.get("quote") or "").strip() if isinstance(e, dict) else ""
        if not path or not quote or not (e.get("sha") or "").strip():
            out.append({"check": "B24", "verdict": RECORD_INCOMPLETE,
                        "why": "a record binding needs path, quote and sha: %r" % (e,)})
            continue
        if not record_path_ok(path, slug):
            out.append({"check": "B24", "verdict": RECORD_REFUSED,
                        "why": "%s is not under docs/ or the issue's case directory" % path})
            continue
        got = _committed(path)
        if got is None or _untagged(quote) not in _untagged(got[1]):
            out.append({"check": "B24", "verdict": RECORD_GONE,
                        "why": "%s %s: %r" % (path, "is not committed at HEAD" if got is None
                                              else "no longer contains the quote", quote[:80])})
            continue
        if got[0] != e["sha"].strip():
            out.append({"check": "B24", "verdict": RECORD_CHANGED,
                        "why": "%s was %s at binding and is %s now; the quote is still there, "
                               "and a person should read what changed around it"
                               % (path, e["sha"][:12], got[0][:12])})
    return out


def record_bound(row: dict, slug: str) -> bool:
    """The row rests on records, and every one of them still says what it was
    bound to (a changed file with the quote intact still counts)."""
    if not row.get("rests_on_record"):
        return False
    return not any(CALIBRATION_SEVERITY.get(f["verdict"]) == BAD for f in b24_records(row, slug))


# ---------------------------------------------------------------------------
# B22 — a claim to a source's own words is checked against its words
# ---------------------------------------------------------------------------
#
# T01 s80: "The paper's own wording is that exercise appeared equally effective
# across comorbidities and baseline severity". The paper's words are "Exercise
# appeared equally effective for people with and without comorbidities and with
# different baseline levels of depression." The sentence has no quotation
# marks, so quotations.py never saw it, and no figure, so rule 1 never did. The
# paid gate found it (Phase B S5); nothing free could.
#
# A sentence that says it gives a source's own words makes a claim a string
# search can settle. Reported speech -- "states that", "writes that",
# "describes this as" -- claims only the sense, and is not this check's.
#
# "verbatim" and "word for word" are wording claims ONLY when what follows is
# the words: a colon or an opening quotation mark, whitespace aside. T04's
# "addresses this question almost word for word" describes a likeness and gives
# no words to check (ruled 2026-10-17).
WORDING_CLAIM = re.compile(
    r"\b(?:own\s+wording|own\s+words|in\s+(?:its|their)\s+(?:own\s+)?words)\b"
    r"|\b(?:verbatim|word\s+for\s+word)(?=\s*[:\"\u201c\u2018'])", re.I)
_WORDING_LEAD = re.compile(
    r"^[\s,:;—–-]*(?:(?:is|are|was|were|reads?|runs?)\b)?[\s,:]*"
    r"(?:that\b)?[\s,:]*")
_CLAUSE_END = re.compile(r"(?<!\d)[.;!?](?!\d)|\s[—–]\s")
MIN_CLAUSE_WORDS = 2


def wording_clause(sent: str) -> str:
    """The words a wording claim says are the source's, or "".

    What follows the phrase, after "is that" / "is:" / a comma; up to the
    closing quotation mark if it opens with one, else to the end of the
    clause."""
    m = WORDING_CLAIM.search(sent)
    if not m:
        return ""
    rest = sent[m.end():]
    rest = rest[_WORDING_LEAD.match(rest).end():]
    q = re.match(r"\s*([\"“‘'])", rest)
    if q:
        close = {"“": "”", "‘": "’"}.get(q.group(1), q.group(1))
        body = rest[q.end():]
        j = body.find(close)
        return (body[:j] if j >= 0 else body).strip()
    e = _CLAUSE_END.search(rest)
    return (rest[:e.start()] if e else rest).strip().rstrip(",:")


def _clause_prefixes(clause: str) -> list[str]:
    """The whole clause, and every comma-delimited prefix of it of at least
    MIN_CLAUSE_WORDS (two) words: "X, which is our gloss" is a claim about X.

    Two, not four. Melanoma's "in its own words, descriptive only , against a
    one-sided alpha of 0.10, ..." claims two words, which are in S007 verbatim
    ("(ie, are descriptive only)"); a four-word floor never tested them and
    reported a correct published sentence as a STOP (2026-10-17). Never one: a
    single word is in almost any document."""
    parts = clause.split(",")
    out = []
    for i in range(1, len(parts) + 1):
        p = ",".join(parts[:i]).strip()
        if len(p.split()) >= MIN_CLAUSE_WORDS and p not in out:
            out.append(p)
    whole = clause.strip()
    if whole and whole not in out:
        out.append(whole)
    return out


def _closest_sentence(clause: str, texts: list[str]) -> str:
    import difflib
    import spancheck as SC
    want = SC._norm(clause).lower()
    best, score = "", 0.0
    for t in texts:
        for s in re.split(r"(?<=[.!?])\s+", SC._norm(t)):
            if len(s) < 12:
                continue
            r = difflib.SequenceMatcher(None, want, s.lower()).ratio()
            if r > score:
                best, score = s, r
    return best


_QS, _QE = "\u2063", "\u2064"          # invisible markers for <q> and </q>
_MARKED_CACHE: dict = {}


def _marked_page(slug: str) -> str:
    """The page's text with each <q> element's boundaries kept as markers.
    Tags become spaces, as in the text the scan split into sentences, so a
    row's sentence ("... practice requires .") is found in it as written."""
    import html as _h
    key = (slug, id(_page_html))
    if key not in _MARKED_CACHE:
        try:
            raw = HEAD.sub(" ", _page_html(slug))
        except (Exception, SystemExit):
            raw = ""
        raw = re.sub(r"<q\b[^>]*>", " " + _QS, raw, flags=re.I)
        raw = re.sub(r"</q\s*>", _QE + " ", raw, flags=re.I)
        raw = re.sub(r"<[^>]+>", " ", raw)
        _MARKED_CACHE[key] = " ".join(_h.unescape(raw).split())
    return _MARKED_CACHE[key]


def quoted_parts(sent: str, slug: str) -> list[str] | None:
    """The words inside <q> elements WITHIN this sentence on the page: [] when
    the sentence carries none, None when the sentence cannot be found on the
    page (the caller then reads the sentence as it always has). A <q> that runs
    past the sentence's end -- the row is "... whereas Budzyń et al." and the
    quotation continues -- is cut at the sentence's end."""
    marked = _marked_page(slug)
    if not marked:
        return None
    plain, where = [], []
    for k, c in enumerate(marked):
        if c not in (_QS, _QE):
            plain.append(c); where.append(k)
    plain = "".join(plain)
    want = " ".join((sent or "").split())
    a = plain.find(want)
    if a < 0 or not want:
        return None
    lo, hi = where[a], where[a + len(want) - 1] + 1
    inside = marked[:lo].count(_QS) > marked[:lo].count(_QE)
    parts, cur = [], []
    for c in marked[lo:hi]:
        if c == _QS:
            inside = True; cur = []
        elif c == _QE:
            if inside and cur: parts.append("".join(cur))
            inside = False; cur = []
        elif inside:
            cur.append(c)
    if inside and cur:
        parts.append("".join(cur))
    return [p.strip(" ,;:") for p in (" ".join(x.split()) for x in parts)
            if len(p.strip(" ,;:").split()) >= MIN_CLAUSE_WORDS]


ACCENT_INFO = "wording claim matched ignoring accents"


def b22_wording_claim(row: dict, slug: str) -> list[dict]:
    """A sentence claiming a source's own words: those words, verbatim, in a span
    the row is bound to or in the held text of a source it cites. Absent: STOP,
    naming the clause and the nearest held sentence. Source not held:
    undetermined, never STOP.

    THE COMPARISON IS QUOTATIONS.PY'S (2026-10-18). Curly and straight, single
    and double quotation marks fold silently -- house style, not wording; a
    match that needed the accent fold ("Budzyń" / "Budzyn") passes with an INFO
    note saying so. And WHEN THE PAGE MARKS THE QUOTATION with <q>, only the
    words inside it are claimed: "In their words, trainees who rely on AI during
    the early formative years <q>may fail to develop …</q>" quotes the <q> and
    paraphrases the lead-in, and B22 had STOPped on the lead-in (24bdc717)."""
    import spancheck as SC
    import quotations as Q
    sent = row.get("sentence") or ""
    if not WORDING_CLAIM.search(sent):
        return []
    parts = quoted_parts(sent, slug) or []
    clause = parts[0] if parts else wording_clause(sent)
    if not clause:
        return [{"check": "B22", "verdict": "wording claim with nothing to check",
                 "why": "the sentence claims a source's own words and no clause "
                        "follows the claim"}]
    spans = [b for _, b in covering_spans(row)]
    held, defective = [], []
    for sid in support_ids(row):
        texts = [t for _, t in SC._texts(slug, sid)]
        if texts:
            held += texts
            if SC.defective_renditions(slug, sid)[0]:
                defective.append(sid)
    hay = [Q.norm(SC._norm(t)) for t in spans + held]
    strict_hay = [Q.norm(SC._norm(t), fold_accents=False) for t in spans + held]
    def found(p):
        want = Q.norm(SC._norm(p))
        if not want or not any(want in h for h in hay):
            return None
        return any(Q.norm(SC._norm(p), fold_accents=False) in h for h in strict_hay)
    if parts:
        # Every <q> in the sentence must be in the source; nothing outside them
        # is claimed as the source's words.
        res = [(p, found(p)) for p in parts]
        missing = [p for p, f in res if f is None]
        if not missing:
            if all(res_f for _p, res_f in res):
                return []
            return [{"check": "B22", "verdict": ACCENT_INFO,
                     "why": "%s: %s" % (Q.ACCENT_NOTE, ", ".join(Q.accent_folds(" ".join(parts)))
                                        or "the source's text carries accents the quotation does not")}]
        clause = missing[0]
    else:
        for p in _clause_prefixes(clause):
            f = found(p)
            if f is True:
                return []
            if f is False:
                return [{"check": "B22", "verdict": ACCENT_INFO,
                         "why": "%s: %s" % (Q.ACCENT_NOTE, ", ".join(Q.accent_folds(p))
                                            or "the source's text carries accents the sentence does not")}]
    if not held or defective:
        return [{"check": "B22", "verdict": "wording claim undetermined",
                 "why": "%r: not in the bound span(s), and %s"
                        % (clause[:160], "the source's held text has a defective layer"
                           if defective else "no source it cites is held")}]
    return [{"check": "B22", "verdict": "wording claim not in its source",
             "why": "claims the source's own words, %r, and they are in no bound span "
                    "and no held text of %s; nearest held sentence: %r"
                    % (clause[:200], ", ".join(support_ids(row)),
                       _closest_sentence(clause, spans + held)[:240])}]


# ---------------------------------------------------------------------------
# B23 — a point estimate shown without the interval its span gives (INFO)
# ---------------------------------------------------------------------------
#
# Most of Phase B's real minor findings (I2, I3, I7, I9, I10) were one thing: a
# sentence stating an effect size whose span gives it with a confidence
# interval, and leaving the interval out. Not wrong; less than the source says.
# A note for the writer, never a block.
_INTERVAL_NAME = (r"(?:CI|CrI|UI|confidence interval|credible interval|uncertainty interval)"
                  r"(?:\s*\[CI\])?")
_EST_CI = re.compile(
    r"(?<![\d.])(?P<est>-?\d+(?:\.\d+)?)\s*%?\s*"
    r"(?:(?P<named>[\(\[]\s*95\s?%\s*" + _INTERVAL_NAME + r"\s*[,:=]?\s*"
    r"|[,;]\s*95\s?%\s*" + _INTERVAL_NAME + r"\s*[,:=]?\s*"
    r"|[\(\[]\s*" + _INTERVAL_NAME + r"\s*[,:=]?\s*)"
    r"|(?P<bare>[\(\[]\s*))"
    r"(?P<lo>-?\d+(?:\.\d+)?)\s*%?\s*(?:to|-|,|;)\s*(?P<hi>-?\d+(?:\.\d+)?)", re.I)
_INTERVAL_WORDS = re.compile(r"\b(?:CI|CrI|confidence|credible|interval|range)\b", re.I)


def span_estimates(span: str) -> list[tuple[str, str, str]]:
    """(estimate, low, high) for each point estimate the span gives WITH an
    interval. A named interval ("95% CI") counts as written. An unnamed
    bracket counts only for a decimal estimate that lies between its bounds,
    so "aged 65 (60-70)" and "n = 120 (45-60)" are not read as intervals."""
    import spancheck as SC
    out = []
    for m in _EST_CI.finditer(SC._norm(span)):
        est, lo, hi = m.group("est"), m.group("lo"), m.group("hi")
        if m.group("bare") is not None:
            try:
                e, a, b = float(est), float(lo), float(hi)
            except ValueError:
                continue
            if "." not in est or not min(a, b) <= e <= max(a, b):
                continue
        out.append((est, lo, hi))
    return out


def b23_interval_omitted(row: dict) -> list[dict]:
    import spancheck as SC
    import modelbind as MB
    sent = row.get("sentence") or ""
    if _INTERVAL_WORDS.search(sent):
        return []
    figs = MB.figures(FT.comma_grouped(sent))
    out, seen = [], set()
    for _, span in covering_spans(row):
        for est, lo, hi in span_estimates(span):
            e = est.lstrip("-")
            if e in seen or e in {"0", "1"}:
                continue
            shown = [f for f in figs if f == e or FT.rounds_to(e, f)]
            if not shown:
                continue
            if lo.lstrip("-") in figs or hi.lstrip("-") in figs:
                continue
            seen.add(e)
            out.append({"check": "B23", "verdict": "interval omitted",
                        "why": "the span gives %s with the interval %s to %s; the "
                               "sentence states %s and no interval"
                               % (est, lo, hi, shown[0])})
    return out


NOT_IN_SOURCES = "document not in sources.json — add an entry (unread) for it"

# B25, GRADE CARRIED (post-study fix 2, step 5, 2026-10-27). A sentence ADDED
# for a finding the page left out (origin "omission_add", ruling.py omissions)
# carries every certainty or confidence term its span carries -- GRADE's
# "high-certainty evidence", the IPCC's "(high confidence)", "medium evidence,
# high agreement" -- and states none higher. Dropping one is a STOP: an added
# sentence is the source's finding, and a finding without its grade is a
# different claim (WHU-S01-C4 was reported with its percentages and without
# its grade). Stating a higher level is a WARN, as the design asks: B20 stops a
# "Confidence ..." sentence above its grade already.
OMISSION_ADD = "omission_add"
HEDGE_DROPPED_ADDED = "evidence hedge dropped from an added sentence"
GRADE_DROPPED = "grade dropped from an added sentence"
GRADE_RAISED = "grade raised in an added sentence"
_LEVEL = r"(very\s+low|low|moderate|medium|high|very\s+high)"
_GRADE_TERMS = (
    ("certainty", re.compile(_LEVEL + r"[\s-]+(?:certainty|quality)\b", re.I)),
    ("certainty", re.compile(r"\b(?:certainty|quality)\s+(?:of\s+(?:the\s+)?evidence\s+)?(?:was\s+|is\s+)?"
                             + _LEVEL, re.I)),
    ("confidence", re.compile(_LEVEL + r"\s+confidence\b", re.I)),
    ("evidence", re.compile(r"\b(limited|medium|robust)\s+evidence\b", re.I)),
    ("agreement", re.compile(_LEVEL + r"\s+agreement\b", re.I)),
)
_LEVEL_RANK = {"very low": 0, "low": 1, "limited": 1, "moderate": 2, "medium": 2, "high": 3, "robust": 3,
               "very high": 4}


def grade_terms(text: str) -> dict[str, list[str]]:
    """{family: [levels]} of every certainty or confidence term in TEXT."""
    out: dict[str, list[str]] = {}
    for fam, rx in _GRADE_TERMS:
        for m in rx.finditer(text or ""):
            lvl = " ".join(m.group(1).lower().split())
            if lvl not in out.setdefault(fam, []):
                out[fam].append(lvl)
    return out


def b25_grade_carried(row: dict) -> list[dict]:
    if (row.get("origin") or "") != OMISSION_ADD:
        return []
    sent = grade_terms(row.get("sentence") or "")
    out = []
    for sid, span in evidence_spans(row):
        for fam, levels in grade_terms(span).items():
            for lvl in levels:
                if lvl not in sent.get(fam, []):
                    out.append({"check": "B25", "verdict": GRADE_DROPPED,
                                "why": "the span (%s) says %s %s; the added sentence does not" % (sid, lvl, fam)})
            top = max(_LEVEL_RANK[l] for l in levels)
            higher = [l for l in sent.get(fam, []) if _LEVEL_RANK[l] > top]
            if higher:
                out.append({"check": "B25", "verdict": GRADE_RAISED,
                            "why": "the added sentence says %s %s; the span (%s) says at most %s"
                                   % (higher[0], fam, sid, max(levels, key=_LEVEL_RANK.get))})
    return out

CALIBRATION_SEVERITY = {
    NOT_IN_SOURCES: BAD,
    "source unclassified": WARN,
    "we hold its abstract — say so": WARN,
    "holdings sentence not declared to the store": WARN,
    "evidence hedge dropped": WARN,
    HEDGE_DROPPED_ADDED: BAD,
    GRADE_DROPPED: BAD,
    GRADE_RAISED: WARN,
    "evidence hedge disposed": INFO,
    "significance qualifier dropped": WARN,
    "confidence above its cited grade": BAD,
    "confidence stated without a cited grade": BAD,
    "confidence level unreadable": WARN,
    "holdings sentence cites a document": BAD,
    "store disagrees": BAD,
    "store check not evaluated": WARN,
    "declared to the store, not a holdings sentence": WARN,
    "wording claim not in its source": BAD,
    "wording claim undetermined": WARN,
    "wording claim with nothing to check": WARN,
    ACCENT_INFO: INFO,
    "interval omitted": INFO,
    RECORD_CHANGED: WARN,
    RECORD_GONE: BAD,
    RECORD_REFUSED: BAD,
    RECORD_INCOMPLETE: BAD,
}
CALIBRATION_CHECKS = {"B19", "B20", "B21", "B22", "B23", "B24", "B25"}


def calibration_findings(row: dict, slug: str) -> list[dict]:
    """B19-B23 over one row. Reads the row, the store for B21 and the held
    text for B22. Writes nothing: run_checks puts what it returns in
    check_flags."""
    return (b19_hedge_dropped(row) + b19_significance_dropped(row) + b20_confidence_ceiling(row)
            + b21_holdings(row, slug) + b22_wording_claim(row, slug)
            + b23_interval_omitted(row) + b24_records(row, slug) + b25_grade_carried(row))


def run_checks(slug: str, *, only: str = "") -> dict:
    """Run every span check against the source THE ROW NAMES.

    WHY THIS IS THE ONLY SANCTIONED WAY TO CALL THEM.

    On 2026-09-01 B12 was run against a document that happened to be in the
    library rather than the one the sentence cites, and reported two correct
    sentences on a live page as errors: "we print 0.510, the source says 0.51".
    The page cites the Journal of Clinical Oncology five-year paper, which
    prints 0.510. What prints 0.51 is a company press release the page does not
    cite. The check was right about the document it was given and the document
    it was given was the wrong one.

    Every span check takes a source id. Whoever supplies it can be wrong, and
    was. The binding row is the answer to "which document does this sentence
    rest on", recorded once, reviewable, and not re-decided at each call site.

    A caller reaching past this into b2_present or b12_precision directly is
    asserting provenance it has to be able to defend. The canary does, because
    it asks about a document rather than about a sentence. Preflight does not,
    and uses this.
    """
    import spancheck as SC
    doc = load(slug)
    rows = doc.get("bindings") or {}
    tally = {"checked": 0, "flags": 0, "undetermined": 0,
             "calibration_stop": 0, "calibration_warn": 0, "calibration_info": 0}
    for sha, row in rows.items():
        if only and sha != only:
            continue
        if not row.get("on_page"):
            continue
        # B19-B21 READ EVERY ROW, NOT ONLY THE BOUND ONES. A judgement carries
        # no span, so the loop below has always skipped it -- and the
        # judgements are where the over-certainty was found.
        calib = calibration_findings(row, slug)
        for f in calib:
            sev = CALIBRATION_SEVERITY.get(f["verdict"], WARN)
            tally[{BAD: "calibration_stop", INFO: "calibration_info"}
                  .get(sev, "calibration_warn")] += 1
        if not row.get("span") or not row.get("source_id"):
            row["check_flags"] = calib
            if calib:
                row["checked_on"] = date.today().isoformat()
            tally["flags"] += len(calib)
            continue
        sid, span, sent = row["source_id"], row["span"], row["sentence"]
        found = []
        tally["checked"] += 1
        # EVERY SPAN THE ROW RESTS ON, NOT THE FIRST ONE.
        #
        # B6 and B12 were handed row["span"] and row["source_id"] and nothing
        # else, so a row that named three documents was checked against one.
        # Both then reported, correctly about the document they were given and
        # wrongly about the sentence:
        #
        #   * B6 said "descriptive only" had no span carrying "only", on a row
        #     whose also_rests_on is the sentence 'These subsequent analyses are
        #     not intended for formal hypothesis testing (ie, are descriptive
        #     only).'
        #   * B12 said we had added a decimal to 0.053, on a row whose premises
        #     quote the Lancet printing 'two-sided p=0.053'.
        #
        # This is the same shape as b12_precision's own founding bug — a check
        # pointed at a document rather than at the claim — committed one layer
        # up, and it is the shape rule_rows already solved with covering(). The
        # checks are unchanged. They are given what the row says it rests on.
        cover = covering_spans(row)
        all_spans = " \u0000 ".join(b for _, b in cover)
        cover_sids = list(dict.fromkeys(a for a, _ in cover))

        present, why = SC.b2_present(span, slug, sid)
        if present is SC.UNDETERMINED:
            tally["undetermined"] += 1
            found.append({"check": "B2", "verdict": "undetermined", "why": why})
        elif present is not True:
            other, why2 = SC.b3_elsewhere(span, slug, sid)
            found.append({"check": "B2/B3", "verdict": "absent",
                          "why": "%s; %s" % (why, why2)})
        else:
            ok5, why5 = SC.b5_complete(span, slug, sid)
            if not ok5:
                found.append({"check": "B5", "verdict": "truncated", "why": why5})
            # A SCOPE WORD MAY BE DISPOSED OF, BY A PERSON, IN THE ROW.
            #
            # "Of the study it is actually announcing it says only that the
            # endpoints were met ... No hazard ratio, no interval, no p-value,
            # no percentage" is an absence claim about a WHOLE DOCUMENT. No span
            # can carry "only", so B6 is right that nothing maps and will be
            # right forever. Left alone it becomes the flag the operator learns
            # to scroll past, which is how a check stops working.
            #
            # So the row may carry a disposition: the word, why it is not a
            # claim the span is meant to bear, WHAT WOULD SHOW IT WRONG, and who
            # signed. Same discipline as b13's declared exclusions -- a
            # signature, not a filter. A disposition with no falsifier or no
            # signer does not count, and one whose word is no longer in the
            # sentence is itself a flag.
            disposed = {}
            for d in (row.get("scope_words") or []):
                if isinstance(d, dict) and d.get("word") and \
                        (d.get("falsifier") or "").strip() and \
                        (d.get("by") or "").strip():
                    disposed[d["word"]] = d
            by_field = field_negation(row, cover)
            by_count = enumeration_covered(sent, cover, slug)
            b14, why14 = bounded_figure_negative(row, cover, sent, slug)
            for w, why6 in SC.b6_scope(sent, all_spans):
                if w in disposed:
                    continue
                if by_field and w in NEGATION_WORDS:
                    continue
                if by_count and w in ENUMERATING:
                    continue
                if b14 == "clear" and w in NEGATION_WORDS:
                    continue
                found.append({"check": "B6", "verdict": "unmapped scope word",
                              "why": "%s — %s" % (w, why6)})
            if by_field:
                row["negation_read_from_field"] = by_field
            if by_count:
                row["enumeration_counted"] = by_count
            if b14 == "clear":
                row["bounded_negative_searched"] = why14
            elif b14 == "candidates":
                found.append({"check": "B14", "verdict": "bounded negative unsearched",
                              "why": why14})
            live_words = {w for w, _ in SC.b6_scope(sent, "")}
            for w, d in disposed.items():
                if w not in live_words:
                    found.append({
                        "check": "B6", "verdict": "stale disposition",
                        "why": "%r is disposed of in this row and is no longer a "
                               "scope word in the sentence; a disposition that "
                               "outlives its word is a filter" % w})
            import autobind as AB
            grouped = []
            for a in AB.anchors_of(FT.strip_citations(sent)):
                # Ask every source the row names. A figure printed as we print
                # it by ANY of them is not a precision we added; a source that
                # is not in the library answers nothing and clears nothing.
                verdicts = [SC.b12_precision(a, slug, x) for x in cover_sids]
                printed = [why for ok, why in verdicts if ok and "as printed" in why]
                if printed:
                    # INFO, on the row and never a flag: found only by reading
                    # "1, 222" as 1,222 (figure_text.split_grouped).
                    if all("INFO:" in why for why in printed):
                        grouped.append("%s: %s" % (a, printed[0].split("INFO: ", 1)[1]))
                    continue
                bad = [why for ok, why in verdicts if not ok]
                if bad:
                    where = ("" if len(cover_sids) == 1 else
                             " (asked %s)" % ", ".join(cover_sids))
                    found.append({"check": "B12", "verdict": "added precision",
                                  "why": bad[0] + where})
            if grouped:
                row["figures_read_across_grouping"] = grouped
            else:
                row.pop("figures_read_across_grouping", None)
        found += calib
        row["check_flags"] = found
        row["checked_on"] = date.today().isoformat()
        tally["flags"] += len(found)
    save(slug, doc)
    return tally


# ---------------------------------------------------------------------------
# B1
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# THE WRITING RULE
# ---------------------------------------------------------------------------
#
# Adopted 2026-09-02, by the editor, after two page-gate runs produced eleven
# findings that were right:
#
#   1. NO FACTUAL STATEMENT THAT IS NOT BASED ON A DOCUMENT WE HAVE AND HAVE
#      FULLY READ.
#   2. EVERY INFERENCE FLAGGED, WITH THE LOGIC AND THE FACTS THAT SUPPORT IT.
#
# Ten of the eleven would have been prevented by those two sentences. The
# eleventh -- a subheading contradicting the paragraph beneath it -- is a
# relation between two things we wrote, which no sourcing rule can reach; that
# is B16's contradiction question.
#
# WHY THIS IS IN CODE AND NOT IN A DOCUMENT
#
# Both rules were ALREADY in this repository. `bucket` has been a field on every
# binding row since the row was designed, and it is null on all eighty sentences
# of issue one. "Empirical sentences bound" has been a WARN reporting 20 of 80.
# The spec's deletion rule, the "write the correction from the source record"
# rule, and undefined_states were the same: written down, gating nothing, and
# each one was followed by the error it described.
#
# A rule that does not block is a rule that will be broken by whoever is tired.
#
# THERE IS NO GRANDFATHERING, AND THERE WAS FOR ABOUT AN HOUR
#
# The first version of this exempted every sentence already on the page, on the
# reasoning that blocking 318 sentences would stop three issues and teach the
# operator to waive the check. That reasoning is the reasoning behind every
# waiver ever granted, and the editor rejected it in one line: given the state
# of the drafting, every sentence in all three articles should be revalidated
# or rewritten.
#
# He is right, and the exemption had already proved him right before he said
# it. Drawn the obvious way -- "everything unbound today" -- it excused a
# sentence written that same afternoon, one of two the gate had never examined.
# Redrawn from git, it still excused sixty-four sentences whose only claim to
# exemption was that nobody had checked them yet. A rule whose scope is "not
# the things we already did" is not a rule.
#
# So the two rules apply to every empirical sentence on every page. The count
# of sentences that fail them is the real backlog, printed rather than
# absorbed, and the only way it falls is by binding or removing a sentence.

RULE_ADOPTED = "2026-09-02"


def bind_field(slug: str, sha: str, sid: str, path: str) -> tuple[bool, str]:
    """Bind a sentence to a STRUCTURED FIELD in a held registry record.

    WHY THIS IS NOT THE PROSE PATH
    ------------------------------
    modelbind rejects a field binding, and it is right to. Its guard asks
    whether the span shares subject matter with the sentence, because a span
    that shares only digits is a coincidence of numbers. But a registry field
    reads `"hasResults":false`, and the sentence reads "the registry carries no
    posted results" -- zero words in common, and the binding is nonetheless
    exactly right. Loosening the prose guard to let this through would loosen
    it for everything.

    So relevance is established differently here, and the record says which:
    the caller names the FIELD PATH, this walks the held JSON to it, and the
    span is that field as the document actually writes it. A path that does not
    resolve is refused. The claim being made is still only R1's -- this field,
    with this value, is in this document -- and not that the sentence is true.
    """
    text = _held_text(slug, sid)
    if text is None:
        return False, "%s is not in the library" % sid
    try:
        data = json.loads(text)
    except ValueError:
        return False, "%s is not JSON, so it has no fields to bind to" % sid
    node, walked = data, []
    for key in path.split("."):
        walked.append(key)
        if isinstance(node, list):
            try:
                node = node[int(key)]
            except (ValueError, IndexError):
                return False, "%s does not resolve in %s" % (".".join(walked), sid)
        elif isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return False, "%s does not resolve in %s" % (".".join(walked), sid)
    span = "%s:%s" % (json.dumps(path.split(".")[-1]), json.dumps(node))
    if span.replace(" ", "") not in text.replace(" ", ""):
        return False, ("%s resolves to %r but that is not how %s writes it"
                       % (path, node, sid))
    doc = load(slug)
    row = (doc.get("bindings") or {}).get(sha)
    if row is None:
        return False, "no binding row %s" % sha[:8]
    row.update(source_id=sid, span=span, locator="$." + path,
               locator_type="field", envelope=None,
               document_sha=(store.held(slug).get(sid) or {}).get("sha256"),
               proposed_by="bind_field", confirmed=False,
               proposed_on=date.today().isoformat(),
               why_bound="the field %s in %s carries this value; relevance is "
                         "the named field path, not prose overlap" % (path, sid))
    save(slug, doc)
    return True, "bound to $.%s in %s" % (path, sid)


def _held_text(slug: str, sid: str):
    import spancheck as SC
    return SC._text(slug, sid)


def _as_numbers(figs) -> set[float]:
    """Figures compared as NUMBERS, because 1.0 and 1 are the same number.

    The coverage check first compared figure strings, and reported that "an HR
    of 1.0" was unsupported by a source saying "if HR = 1". Same number, two
    spellings, and the check could not see it -- the same family as The
    Lancet's middle dot and the Greek alpha extracting as "a". A comparison
    that cannot see the thing it is comparing does not get to report an
    absence.

    Precision differences are B12's question, not this one. This check asks
    only whether the quantity appears at all.
    """
    out = set()
    for f in figs:
        try:
            out.add(float(f))
        except ValueError:
            continue
    return out


def _bare_integer_in(fig: str, covered: str) -> bool:
    """Does the span write this figure as a bare integer -- "4415" for the
    page's "4,415"?

    modelbind._NUM admits an integer only in up-to-three-digit or comma-grouped
    form, and deliberately: widen it to bare four-digit runs and every year in
    every document becomes a figure. So the page's "4,415" reaches this check
    as a claim figure, and a span writing "4415" (Scientific Reports) or
    "Of 9146 eligible patients" (ESMO Open) could never confirm it -- rule 1
    blocked cdk46 on two figures the documents plainly state, 12 September
    2026.

    This normalises the thousands separator on BOTH sides for ONE figure the
    page already claims, and admits no new token: it is asked only about a
    figure `_claim_figures` produced, so a year in a document is never read as
    a figure here, and a year on the page never enters `_claim_figures` in
    the first place (a bare four-digit run does not match _NUM). The document
    side is searched as a whole-number token, so 4415 does not match 44150 or
    4415.2.
    """
    digits = fig.replace(",", "")
    if not digits.isdigit() or len(digits) < 4:
        return False
    # Every separator a source groups thousands with, not only the comma: a
    # space, a no-break space, a thin space (spancheck.figure_pattern). Six
    # figures in the test issues were printed "14 170" in their own spans and
    # reported as in none (2026-10-17).
    return re.search(FT.figure_pattern(digits) + r"(?!\.\d)", covered) is not None


def _claim_figures(text: str, names: set[str] | None = None) -> set[str]:
    """The figures a sentence CLAIMS, which is not every digit string in it.
    A citation's volume/issue/pages are not among them (FT.strip_citations).

    "KEYNOTE-942" and "mRNA-4157" are names. The first run of the coverage
    check read 942 as a figure and reported it missing from the span the
    sentence was bound to, which is true and meaningless. A number inside a
    token that also carries letters is part of an identifier, not a
    measurement -- stated as a rule about token shape rather than as a list of
    the identifiers we happen to have met, because every allowlist built from
    met vocabulary in this repository has been wrong.
    """
    text = FT.strip_citations(text)
    import modelbind as MB
    named = set()
    for tok in re.split(r"\s+", text):
        if re.search(r"[A-Za-z]", tok) and re.search(r"\d", tok):
            named |= MB.figures(tok)
    # A NAME CAN HAVE A SPACE IN IT. "CheckMate 238" is two tokens, so the
    # token-shape rule above let 238 through and the check reported it as a
    # figure in no bound span. The names come from the source ledger's own
    # `also_called` lists -- what THIS issue's documents are called -- and not
    # from a list of the trials I happen to have met, which is the mistake this
    # repository has made four times.
    for name in (names or set()):
        if re.search(r"\b%s\b" % re.escape(name), text):
            named |= MB.figures(name)
    return {f for f in MB.figures(text) if f not in named}


# Source kinds that are somebody's account of a document rather than the
# document. Read from the ledger's own `type` field, not from a list of outlets
# we have met.
REPORTING = {"coverage", "trade"}


def figures_resting_only_on_reporting(slug: str) -> list[tuple[str, str]]:
    """Sentences carrying a figure whose every source is somebody's reporting.

    Issue one tells a reader "every number above traces to one of these" and
    lists its sources. On 3 September an outside reviewer showed the page then
    said "and none to a news report", which was false: its five-year landmark
    rates were credited to a trade article because the primary abstract had
    returned 403 to every fetch. The abstract was obtained by hand the same day
    and those two sentences moved onto it.

    That fixed the instance. This function is here so the claim cannot quietly
    become false again -- a figure may be bound to reporting on the way to
    finding the document, and this says so out loud while it is.

    It is deliberately narrow: it asks about SENTENCES CARRYING FIGURES, since
    a quotation from an outlet is properly sourced to that outlet and only a
    number is expected to come from the record.
    """
    import modelbind as MB
    kinds = {x["id"]: x.get("type") for x in store.sources(slug)}
    names = trial_names(store.sources(slug))
    doc = load(slug)
    out = []
    for k, v in (doc.get("bindings") or {}).items():
        if not v.get("on_page"):
            continue
        if not [f for f in _claim_figures(v["sentence"], names) if MB._weight(f)]:
            continue
        sids = ([v["source_id"]] if v.get("source_id") else []) + \
               [x.get("source_id") for x in (v.get("also_rests_on") or [])] + \
               [x.get("source_id") for x in (v.get("premises") or [])]
        seen = {kinds.get(s) for s in sids if s}
        if seen and seen <= REPORTING:
            out.append((k, v["sentence"]))
    return out


def _declared_exclusions(slug: str) -> list[dict]:
    """figure-exclusions.json, read without importing b13 (b13 imports this).

    Each entry names a figure, the sentence it belongs to, why it is not a claim
    about any document, who declared it and what would show it wrong. b13 owns
    the file and reports one that no longer matches a sentence as stale, so an
    entry cannot quietly outlive its sentence.
    """
    try:
        p = store.case_dir(slug) / "figure-exclusions.json"
        return json.loads(p.read_text(encoding="utf-8")).get("exclusions") or []
    except (Exception, SystemExit):
        # (Exception, SystemExit), not Exception and not BaseException:
        # store.case_dir() raises SystemExit for a
        # slug with no case directory, and SystemExit is not an Exception. This
        # guard was written as `except Exception` when the declared-exclusions
        # read was added on 2026-09-09 and therefore caught nothing that was
        # actually thrown -- it took 22 rules tests from green to red, because
        # they run against a synthetic slug. The same distinction is already
        # commented in publish.py's preflight loop. Bare BaseException would
        # also swallow KeyboardInterrupt and make a hung run uninterruptible
        # through this path; naming both catches what is actually thrown and
        # says so. The defect underneath is that a library function makes a
        # terminate-the-process decision at all -- see open-gaps.
        return []


def not_examined(slug: str) -> list[str]:
    """Body sentences neither rule looks at, because no row was ever made.

    `scan()` requires a detectable anchor before it creates a binding row. That
    is a reasonable way to find sentences worth binding and a bad way to define
    the population of a rule that claims to cover the page. This function is the
    difference between the two, so the number can be printed instead of implied.
    """
    doc = load(slug)
    rows = (doc.get("bindings") or {})
    rowed = {" ".join((v.get("sentence") or "").split())
             for v in (rows.values() if isinstance(rows, dict) else rows)
             if isinstance(v, dict) and v.get("on_page")}
    return [s for s in (" ".join(x.split()) for x in page_sentences(slug))
            if s not in rowed]


def rule_rows(slug: str) -> list[tuple[str, str, str]]:
    """The two rules, as blocking rows, over the sentences that have a binding row.

    SCOPE, CORRECTED 2026-09-10. This docstring said "Every sentence on the page,
    no exemptions." It does not do that and never did.

    The population is `bindings.json`'s on_page rows. `scan()` creates a row only
    where an anchor is detectable -- a figure, a quotation, a named trial, a
    registry identifier, a DOI -- and skips the rest (`if not must: continue`).
    So a sentence carrying a claim with no detectable anchor never enters, and is
    examined by neither rule.

    The gap is not small. On 2026-09-10: melanoma 131 rowed of 343 body
    sentences; cdk46 169 of 487; deskilling 112 of 426. A row reading "all 131
    sentence(s) name the words they rest on" means all 131 OF THE 131 THAT HAVE
    ROWS, and the sentence above it said "every sentence on the page".

    That is failure 15 -- a check whose scope is narrower than its name -- in the
    file that defines this publication's foundational rule, and it is also the
    unread-signature failure: a control described in words that nothing performs.
    A docstring overstating what a function examines is how the next person
    concludes that a green rule 1 means the page is bound.

    THE THIRD OUTCOME. Sentences with no detectable anchor are NOT EXAMINED --
    reported and counted, never absent. Same principle as the epistemic check:
    a check that cannot evaluate something says so rather than passing it
    silently. See `not_examined()` below and Appendix D.
    """
    import spancheck as SC
    import modelbind as MB
    doc = load(slug)
    rows = doc.get("bindings") or {}
    on_page = {k: v for k, v in rows.items() if v.get("on_page")}

    # WHAT RULE 1 ASKS OF A JUDGEMENT, AND WHY IT IS NOT A SPAN
    #
    # The editor's two rules divide the page: a FACTUAL STATEMENT rests on a
    # document we hold and read; an INFERENCE is flagged and shows the logic
    # and the facts behind it. The first version of this check demanded a span
    # from every sentence including the judgements, which would have pushed me
    # to point "0.0266 and 0.053 are the same result" at some passage it does
    # not rest on -- inventing a binding to satisfy a check, which is the
    # failure mode this whole file exists to prevent.
    #
    # So a judgement satisfies rule 1 through its PREMISES, each of which is a
    # span in a held document, checked by rule 2 below. This is not a softer
    # requirement: a judgement must carry premises AND a written-out step,
    # where a report needs only its span. Declaring a sentence a judgement to
    # escape rule 1 buys strictly more work, which is the property that keeps
    # the bucket honest.
    known_names = trial_names(store.sources(slug))
    # A figure the page WORKS OUT rather than reports -- the scorecard's
    # composite -- is verified by furniture.py against its own arithmetic, the
    # scores shown beside it and weights summing to 1. That is a stricter test
    # than a quotation, so a sentence may refer to it. Only from an element
    # that passes; a scorecard that does not add up donates nothing.
    try:
        import furniture
        worked_out = furniture.computed_figures(_page_html(slug))
    except Exception:
        worked_out = set()

    def covering(v):
        spans = []
        if v.get("span"):
            spans.append((v.get("source_id"), v["span"]))
        spans += [(x.get("source_id"), x.get("span") or "")
                  for x in (v.get("also_rests_on") or [])]
        if (v.get("bucket") or "") == "judgement":
            spans += [(x.get("source_id"), x.get("span") or "")
                      for x in (v.get("premises") or [])]
        return [(sid, sp) for sid, sp in spans if sid and sp]

    # AN ATTESTATION IS NOT A SPAN, AND SATISFIES RULE 1 ANYWAY.
    #
    # NCCN's licence forbids putting the guideline through any automated tool,
    # so no check has read it or ever may. Spec section 3 says so in the table:
    # for a figure-based sentence, "locatable" is NOT POSSIBLE. Section 7 routes
    # it to the operator, by recorded question and answer. A rule 1 that
    # demanded a span from those sentences would make the attested route
    # useless and push us toward pasting licence-bound text into a file to
    # satisfy a check -- the worst outcome available.
    #
    # So a `figure` row rests on its attestation, and rule 2 makes that cost a
    # named person, the record of their reading, and a locator. The count is
    # reported SEPARATELY below and never added to the verified ones, because
    # "a human says this is in a document nothing may read" and "this string is
    # in these bytes" are different claims and merging them is the oldest error
    # in this repository.
    attested = [k for k, v in on_page.items()
                if (v.get("bucket") or "") == "figure"
                and (v.get("attested_by") or "").strip()
                and (v.get("attested_in") or "").strip()
                and (v.get("locator") or "").strip()]
    # A HOLDINGS SENTENCE RESTS ON THE STORE, AND SATISFIES RULE 1 THAT WAY.
    # Same shape as the attestation above: not a span, never counted as a
    # verified one, reported on its own row. B21 is what asks the store.
    stored = [k for k, v in on_page.items()
              if (v.get("rests_on_store") or []) and is_holdings(v.get("sentence"))
              and not support_ids(v)]
    # A DECLARED FRAMING ROW IS SETTLED, NOT UNBOUND. A heading, signpost or
    # transition makes no claim about the world or about a source, so there is
    # no span for it to rest on; a person has said so in the row (bucket
    # context, `framing` {why, by}). Counting it as "rests on nothing yet" put
    # 23 deskilling rows in the backlog that nobody could ever clear -- the
    # pressure toward pointing a signpost at a passage it does not rest on.
    # Reported on its own row, never counted as bound or verified, and a row
    # with a blank why or by is not a declaration and stays unbound. 2026-10-18.
    framed = [k for k, v in on_page.items()
              if (v.get("bucket") or "") == "context" and not covering(v)
              and isinstance(v.get("framing"), dict)
              and (v["framing"].get("why") or "").strip()
              and (v["framing"].get("by") or "").strip()]
    # A SENTENCE RESTING ON WHU'S OWN COMMITTED RECORDS (B24) is bound: every
    # quote it names is in the file as committed. Reported on its own row and
    # never counted as a verified span of a document. A record quote that is no
    # longer there is `loose` below -- bound, and resting on nothing.
    rec_flags = {k: b24_records(v, slug) for k, v in on_page.items() if v.get("rests_on_record")}
    recorded = [k for k, fl in rec_flags.items()
                if not any(CALIBRATION_SEVERITY.get(f["verdict"]) == BAD for f in fl)]
    rec_gone = {k: fl for k, fl in rec_flags.items() if k not in set(recorded)}
    rec_changed = ["%s: %s" % (k[:8], f["why"][:120]) for k, fl in rec_flags.items()
                   for f in fl if f["verdict"] == RECORD_CHANGED]
    unbound = [k for k, v in on_page.items()
               if not covering(v) and k not in set(attested) and k not in set(stored)
               and k not in set(framed) and k not in set(recorded) and k not in rec_gone]

    # A SENTENCE IS NOT BOUND BECAUSE ONE OF ITS FIGURES IS.
    #
    # "the three-year paper says 80% power against a one-sided alpha of 0.10,
    # and the ASCO deck states the same threshold" rests on two documents. Bind
    # it to the paper and rule 1 goes green with half the sentence resting on
    # nothing -- a check applied where its premise holds, and nothing asking
    # the other question, which is the shape of every failure in this file's
    # history. So: every figure the sentence carries must appear in a span the
    # sentence is actually bound to.
    loose, loose_keys, unevaluable, rounded = [], set(), [], []
    split, dehyphenated, unwatermarked = [], [], []
    for k, v in on_page.items():
        if k in set(attested):
            continue          # nothing here may read the document it rests on
        spans = covering(v)
        if not spans:
            continue
        covered = ""
        for sid, span in spans:
            present, why = SC.b2_present(span, slug, sid)
            if present is SC.UNDETERMINED:
                # the checker cannot read this rendition (declared on the
                # record); the span is neither confirmed nor refuted, and the
                # figures it would cover count as covered on the binder's
                # word -- reported separately below, never as verified
                unevaluable.append("%s: %s" % (k[:8], why[:120]))
                covered += " " + SC._norm(span)
                continue
            if present is True and SC.DROPPED_HYPHEN_NOTE in why:
                dehyphenated.append("%s: in %s (%s)" % (k[:8], sid, v["sentence"][:40]))
            if present is True and SC.SSRN_NOTE in why:
                unwatermarked.append("%s: in %s (%s)" % (k[:8], sid, v["sentence"][:40]))
            if present is not True:
                loose.append("%s: a span it names is not in %s" % (k[:8], sid))
                loose_keys.add(k)
                continue
            covered += " " + SC._norm(span)
        # DECLARED EXCLUSIONS COUNT HERE TOO, AS THE `computed` MARK ALREADY DOES.
        # This check had one exemption channel and the repository has two. A
        # figure that is not a claim about any document -- the page's own
        # arithmetic, an HTTP status our own request came back with -- is
        # declared in figure-exclusions.json by a person, with a reason and a
        # falsifier, and b13 has honoured that since it was written. Rule 1 did
        # not, so a figure could be correctly declared there and still reported
        # here as resting on nothing, which pushes the author toward deleting a
        # true word to satisfy a check that has already been answered. The
        # signature is the control; reading only one of the two files was the
        # gap. Same shape as the b13/corrections_check split of 2026-09-09.
        declared = set()
        for r in _declared_exclusions(slug):
            ins = (r.get("in_sentence") or "").strip()
            if ins and SC._norm(ins) in SC._norm(v["sentence"]):
                declared |= _as_numbers([r.get("figure")])
        # Thousands separators are read on both sides: "14 170" in a span is
        # 14,170, and so is "14 170" in a sentence (spancheck.comma_grouped).
        span_figs = MB.figures(covered) | MB.figures(FT.comma_grouped(covered))
        held = _as_numbers(span_figs) | worked_out | declared
        missing = []
        for f in _claim_figures(FT.comma_grouped(v["sentence"]), known_names):
            if not MB._weight(f) or _as_numbers([f]) <= held \
                    or _bare_integer_in(f, covered):
                continue
            # A ROUNDING OF A SPAN FIGURE IS THAT FIGURE, AND IS SAID SO.
            # T01 s21 prints "-0.95" and "-0.4" for a span's -0.946 and -0.43
            # and was reported as resting on nothing. A figure that is a span
            # figure correctly rounded one decimal place shorter passes, with a
            # note naming both values; anything else -- -0.946 shown as -0.9 or
            # -0.94 -- is still a figure in no span. The rule is B12's
            # (spancheck.rounds_to), not a second copy of it.
            src = sorted(h for h in span_figs if FT.rounds_to(h, f))
            if src:
                rounded.append("%s: %s is %s rounded (%s)"
                               % (k[:8], f, src[0], v["sentence"][:40]))
                continue
            # "1, 222" in a span copied from extracted text is 1,222, read so
            # only where it is exactly this figure (figure_text.split_grouped).
            grouped = FT.split_grouped(f, covered)
            if grouped:
                split.append("%s: %s is printed %r in its span (%s)"
                             % (k[:8], f, grouped, v["sentence"][:40]))
                continue
            missing.append(f)
        if missing:
            loose.append("%s: %s in no span it is bound to (%s)"
                         % (k[:8], ", ".join(sorted(missing)[:4]),
                            v["sentence"][:40]))
            loose_keys.add(k)

    for k, fl in rec_gone.items():
        loose.append("%s: a record it rests on does not say it (%s)"
                     % (k[:8], "; ".join(f["why"][:100] for f in fl[:2])))
        loose_keys.add(k)

    out_extra = []
    if recorded:
        out_extra.append(("rule 1 — sentences resting on WHU's committed records", OK,
                          "INFO: %d of %d say what WHU did or decided, and every quote they "
                          "name is in the file as committed (B24); not a span of a "
                          "document and never counted as one" % (len(recorded), len(on_page))))
    if rec_changed:
        out_extra.append(("rule 1 — records changed since binding", WARN,
                          "%d record(s) a sentence rests on have changed since the binding "
                          "was made; the quote is still there, and a person should read "
                          "what changed around it: %s" % (len(rec_changed), " || ".join(rec_changed[:3]))))
    if rounded:
        # INFO, AND SO OK: nothing here is unsupported. The row exists so that
        # a rounding is never silent -- the reader of the page sees -0.95, the
        # span says -0.946, and the record says both.
        out_extra.append(("rule 1 — figures shown rounded from their span", OK,
                          "INFO: %d figure(s) are a span figure correctly rounded one "
                          "decimal place shorter, and pass as that figure: %s"
                          % (len(rounded), " || ".join(rounded))))
    if split:
        out_extra.append(("rule 1 — figures read across a comma-and-space grouping", OK,
                          "INFO: %d figure(s) are in their span only with a comma and "
                          "one space between thousands groups, and pass as that "
                          "figure: %s" % (len(split), " || ".join(split))))
    if dehyphenated:
        out_extra.append(("rule 1 — spans matched ignoring a dropped hyphen", OK,
                          "INFO: %d span(s) %s: %s"
                          % (len(dehyphenated), SC.DROPPED_HYPHEN_NOTE,
                             " || ".join(dehyphenated))))
    if unwatermarked:
        out_extra.append(("rule 1 — spans matched after removing SSRN's watermark", OK,
                          "INFO: %d span(s) %s: %s"
                          % (len(unwatermarked), SC.SSRN_NOTE, " || ".join(unwatermarked))))
    if unevaluable:
        out_extra.append(("spans this check cannot evaluate", WARN,
                          "%d span(s) name a source whose only held rendition has a "
                          "defective text layer, declared on its record; neither "
                          "confirmed nor refuted, and not counted as verified: %s"
                          % (len(unevaluable), " || ".join(unevaluable[:3]))))
    if stored:
        out_extra.append(("sentences resting on the source store", WARN,
                          "%d of %d say what we hold or did, and rest on the store's "
                          "record rather than on a document; B21 asks the store. "
                          "Not a verified span and never counted as one."
                          % (len(stored), len(on_page))))
    if framed:
        out_extra.append(("rule 1 — sentences declared framing", OK,
                          "INFO: %d of %d are headings, signposts or transitions a "
                          "person has declared make no claim (bucket context, with "
                          "`framing`); settled, not bound, and never counted as a "
                          "verified span" % (len(framed), len(on_page))))
    if attested:
        out_extra.append(("sentences resting on a human attestation", WARN,
                          "%d of %d rest on a document no check may read: a named "
                          "reader read it, the record of that reading is named, and "
                          "the place in the document is named. This is not a "
                          "verified span and is never counted as one."
                          % (len(attested), len(on_page))))

    # TWO STATEMENTS, TWO ROWS. Until 12 September 2026 rule 1 was one row
    # saying "135 of 169 rest on nothing, 7 carry a figure no bound span
    # contains", and the row blocked on either. Those are different claims:
    #
    #   `loose`   a sentence IS bound and its evidence is not there -- a span
    #             the row names is not in the document, or a figure the
    #             sentence carries is in no span it is bound to. Something is
    #             FALSE OR UNSUPPORTED, by name. Blocks.
    #   `unbound` a row exists (an anchor was detected) and nobody has bound
    #             it. NOTHING HAS CHECKED THIS. Printed, counted, WARN.
    #
    # The 11 September ruling: a check blocks only when it can name a specific
    # thing that is false or unsupported; a check that cannot evaluate
    # something says so and does not block; every demoted row stays printed
    # and counted. Not a demotion of rule 1 -- the blocking half keeps its
    # label -- but a split, so the block names the defect and the backlog is
    # the backlog.
    bound_n = (len(on_page) - len(unbound) - len(attested) - len(stored) - len(framed)
               - len(recorded))
    out = [("rule 1 — written from a document we hold",
            OK if not loose else BAD,
            "every figure in the %d bound sentence(s) is in a span the sentence "
            "is bound to, and every such span is in its document" % bound_n
            if not loose else
            "%d bound sentence(s) rest on something that is not there -- a "
            "figure no bound span contains, or a span not in its document: %s"
            % (len(loose), " || ".join(loose[:3]))),
           ("rule 1 — sentences not yet bound",
            OK if not unbound else WARN,
            "every one of the %d sentence(s) with a binding row is bound or "
            "declared framing" % len(on_page) if not unbound else
            "%d of %d rest on nothing yet: no span, no premises. Nothing has "
            "checked these -- not passed, not failed. %s"
            % (len(unbound), len(on_page),
               " || ".join(on_page[k]["sentence"][:50] for k in unbound[:2])))]

    # RULE 2, IN THE SPEC'S VOCABULARY AND NOT A NEW ONE
    #
    # The first draft of this check invented a bucket called "inference".
    # BUCKETS had been defined at the top of this file since the spec was
    # written -- deterministic, context, judgement, figure -- and used by
    # nothing. Section 3 already says an unclassified sentence is a defect;
    # section 7 already routes a licence-reserved source to the operator by
    # recorded question and answer. Both were written down and neither ran.
    # That is the fifth instance of this pattern in three days, so: no new
    # words. An inference is a `judgement` sentence, and the editor's demand
    # that it show its logic and its facts is the premises-and-step
    # requirement below.
    unbucketed = [k for k, v in on_page.items() if not v.get("bucket")]
    wrong = [k for k, v in on_page.items()
             if v.get("bucket") and v["bucket"] not in BUCKETS]
    bad = ["%s: bucket %r is not one of %s"
           % (k[:8], on_page[k]["bucket"], ", ".join(BUCKETS)) for k in wrong]

    for k, v in on_page.items():
        bucket = v.get("bucket") or ""
        if bucket == "judgement":
            # The editor's rule 2: flag the inference, show the logic and the
            # facts. Premises are checked against held bytes; the step is
            # written out so a reader can disagree with the reasoning rather
            # than only with the conclusion.
            prem = v.get("premises") or []
            if not prem:
                bad.append("%s: a judgement with no premises" % k[:8])
            for pr in prem:
                sid, span = pr.get("source_id"), pr.get("span") or ""
                if not sid or not span:
                    bad.append("%s: a premise with no source or no span" % k[:8])
                    continue
                present, why = SC.b2_present(span, slug, sid)
                if present is not True:
                    bad.append("%s: a premise whose span is not in %s"
                               % (k[:8], sid))
            if not (v.get("step") or "").strip():
                bad.append("%s: a judgement with no step written out" % k[:8])
        elif bucket == "figure":
            # Spec section 3: for a figure-based sentence "locatable" is NOT
            # POSSIBLE by machine, and section 7 routes anything a licence
            # reserves to a person to the operator, by recorded question and
            # answer. So the row must name the person, the record, and the
            # place in the document -- and this check must never report such a
            # span as verified, because it has not read the document.
            for field, what in (("attested_by", "who read it"),
                                ("attested_in", "the record of the reading"),
                                ("locator", "where in the document")):
                if not (v.get(field) or "").strip():
                    bad.append("%s: a figure-based sentence with no %s"
                               % (k[:8], what))

    # BLOCK ON A PROBLEM, WARN ON A BACKLOG. Until 12 September 2026 this row
    # blocked on "162 undeclared, 0 problem(s)" -- blocking while saying it
    # had found nothing. An undeclared bucket is nothing-has-checked-this; a
    # judgement with no premises, a premise whose span is not in its document,
    # a bucket outside the vocabulary, a figure-based sentence with no named
    # reader is a defect by name. So: problems > 0 blocks; problems == 0 warns
    # however many are undeclared, and the undeclared count stays in the
    # message. 11 September ruling; nothing here is exempted, only classified.
    out.append(("rule 2 — every sentence declares its kind, judgements show "
                "their work",
                OK if not (unbucketed or bad) else (BAD if bad else WARN),
                "all %d sentence(s) declare a bucket, and every judgement "
                "shows its premises and its step" % len(on_page)
                if not (unbucketed or bad) else
                "%d undeclared, %d problem(s): %s"
                % (len(unbucketed), len(bad),
                   " || ".join((bad + [on_page[k]["sentence"][:50]
                                       for k in unbucketed])[:3]))
                + ("" if bad else " -- the undeclared are unexamined, not wrong; "
                                  "nothing blocks until a declared sentence fails")))

    out.extend(out_extra)
    onlyreporting = figures_resting_only_on_reporting(slug)
    out.append(("figures resting only on somebody's reporting",
                OK if not onlyreporting else BAD,
                "no sentence carrying a figure rests only on coverage — every "
                "number on the page reaches a release, a paper or a registry "
                "record" if not onlyreporting else
                "%d sentence(s) carry a figure whose only source is reporting: %s"
                % (len(onlyreporting),
                   " || ".join(t[:60] for _, t in onlyreporting[:3]))))

    todo = set(unbound) | set(unbucketed) | set(wrong)
    todo |= {k for k, _ in onlyreporting}
    todo |= loose_keys
    if todo:
        out.append(("sentences still to revalidate", WARN,
                    "%d of %d. Adopted %s with no exemption for what was "
                    "already written: every sentence in the article is either "
                    "bound to the words it rests on, declared as an inference "
                    "and shown, or off the page."
                    % (len(todo), len(on_page), RULE_ADOPTED)))

    # THE THIRD OUTCOME. Everything above is computed over the rows in
    # bindings.json. This row is the rest of the page, and it exists because
    # "all 131 sentence(s) name the words they rest on" was true of the 131 and
    # was read as true of the page. A check that cannot evaluate something says
    # so; it never leaves it out. WARN and not BAD deliberately: an unexamined
    # sentence is not a failing sentence, and reporting it as one would push
    # somebody to delete prose to clear a number.
    # A page that cannot be read gives an UNKNOWN coverage, not a silent zero.
    # Omitting the row when the count fails would reintroduce exactly the
    # absence this row exists to remove -- and the first version of it did that,
    # because page_sentences() raises for a slug with no page.
    try:
        ne = not_examined(slug)
    except BaseException as exc:                            # SystemExit included
        out.append(("sentences neither rule examined", WARN,
                    "could not be counted: %s: %s. Unknown, not zero."
                    % (type(exc).__name__, exc)))
        ne = []
    if ne:
        total = len(on_page) + len(ne)
        out.append(("sentences neither rule examined", WARN,
                    "%d of %d body sentence(s). A binding row is created only "
                    "where an anchor is detectable — a figure, a quotation, a "
                    "named trial, a registry identifier — so a claim with none "
                    "of those never enters either rule. The rows above are "
                    "computed over the other %d. Not examined is not passed."
                    % (len(ne), total, len(on_page))))
    return out


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    try:
        doc = load(slug)
    except Exception as exc:
        return [("claim bindings", WARN, "could not read bindings.json: %s" % exc)]
    rows = doc.get("bindings") or {}
    if not rows:
        return [("claim bindings", WARN,
                 "no bindings recorded — run bindings.py %s scan. Until then no "
                 "sentence on this page names the words it rests on." % slug)]
    on_page = {k: v for k, v in rows.items() if v.get("on_page")}
    bound = [k for k, v in on_page.items() if v.get("span")]
    unbucketed = [k for k, v in on_page.items() if not v.get("bucket")]
    # VOCABULARY, RULED 2026-09-10. One word was doing three jobs.
    #
    #   BOUND     has a span in a held document.
    #   DECLARED  a judgement with stated premises and a step.
    #   ATTESTED  a figure a named person read in a document no check may read.
    #
    # Rule 1 is satisfied by any of the three. **"Bound" never means "satisfies
    # rule 1."** This row used to say "%d of %d are bound to a span; %d rest on
    # nothing this system can name" -- which called 34 correctly declared
    # judgements and 2 correctly attested figures "resting on nothing", while
    # rule 1 passed the same sentences two rows below. Two rows, one file,
    # opposite characterisations of the same 36 sentences, and the melanoma page
    # inherited the loose reading and printed it to readers.
    #
    # b13's two-notions-of-"used", one layer down.
    declared = [k for k, v in on_page.items()
                if not v.get("span") and (v.get("bucket") or "") == "judgement"]
    attested_n = [k for k, v in on_page.items()
                  if not v.get("span") and (v.get("bucket") or "") == "figure"
                  and (v.get("attested_by") or "").strip()]
    stored_n = [k for k, v in on_page.items()
                if not v.get("span") and (v.get("rests_on_store") or [])
                and k not in declared and k not in attested_n]
    other = (len(on_page) - len(bound) - len(declared) - len(attested_n)
             - len(stored_n))
    out = [("empirical sentences bound to a span",
            OK if not other else WARN,
            "%d of %d bound to a span, %d declared as judgements resting on stated "
            "premises, %d attested by a named reader, %d resting on the source "
            "store%s. Rule 1 below is satisfied by any of the four; BOUND means a "
            "span and nothing else."
            % (len(bound), len(on_page), len(declared), len(attested_n),
               len(stored_n), "" if not other else ", and %d by none of them" % other))]
    out.extend(rule_rows(slug))
    def _span_flags(v):
        return [f for f in (v.get("check_flags") or [])
                if f.get("check") not in CALIBRATION_CHECKS]
    flagged = [k for k, v in on_page.items() if _span_flags(v)]
    checked = [k for k, v in on_page.items()
               if v.get("checked_on") and v.get("span")]
    if checked:
        out.append(("bound sentences the span checks flagged",
                    OK if not flagged else BAD,
                    "none of the %d bound sentence(s) is flagged" % len(checked)
                    if not flagged else
                    "%d of %d bound sentence(s) carry a flag: %s"
                    % (len(flagged), len(checked),
                       " || ".join("%s %s" % (f["check"], f["verdict"])
                                   for k in flagged[:4]
                                   for f in _span_flags(on_page[k])[:1]))))
    calib = [(k, f) for k, v in on_page.items() for f in (v.get("check_flags") or [])
             if f.get("check") in CALIBRATION_CHECKS]
    if calib:
        stops = [(k, f) for k, f in calib
                 if CALIBRATION_SEVERITY.get(f["verdict"]) == BAD]
        infos = [(k, f) for k, f in calib
                 if CALIBRATION_SEVERITY.get(f["verdict"]) == INFO]
        warns = [x for x in calib if x not in stops and x not in infos]
        # An INFO note does not make the row warn: it is ok with the notes
        # counted, so a page with only notes is not a page with problems.
        out.append(("sentences surer than their sources (B19-B21)",
                    BAD if stops else (WARN if warns else OK),
                    "%d STOP, %d warn, %d info: %s"
                    % (len(stops), len(warns), len(infos),
                       " || ".join("%s %s" % (f["check"], f["verdict"])
                                   for k, f in (stops or warns or infos)[:4]))))
    if unbucketed:
        out.append(("sentences with no declared bucket", WARN,
                    "%d of %d — a sentence whose kind nobody declared cannot be "
                    "routed to the process that should check it"
                    % (len(unbucketed), len(on_page))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("scan", help="add a blank row for every unbound empirical sentence")
    u = sub.add_parser("unbound", help="print the sentences that rest on nothing named")
    u.add_argument("--limit", type=int, default=25)
    sub.add_parser("check", help="run the span checks from the bindings")
    sub.add_parser("status")
    args = ap.parse_args()

    if args.cmd == "check":
        t = run_checks(args.slug)
        print("\n  %d bound sentence(s) checked against the source each row "
              "names" % t["checked"])
        print("  %d flag(s), %d undetermined" % (t["flags"], t["undetermined"]))
        print("  calibration (B19-B23): %d STOP, %d warn, %d info\n"
              % (t["calibration_stop"], t["calibration_warn"], t["calibration_info"]))
        doc = load(args.slug)
        for sha, row in (doc.get("bindings") or {}).items():
            # ONLY WHAT IS STILL ON THE PAGE. A row whose sentence has been
            # edited keeps its old flags as history and is no longer a finding;
            # printing them made the header say "0 flags" above two flags.
            if not row.get("on_page"):
                continue
            for f in (row.get("check_flags") or []):
                mark = ""
                if f.get("check") in CALIBRATION_CHECKS:
                    mark = {BAD: " STOP", INFO: " info"}.get(
                        CALIBRATION_SEVERITY.get(f["verdict"]), " warn")
                print("  %-7s %-20s %s" % (f["check"] + mark, f["verdict"],
                                           row["sentence"][:78]))
                print("          [%s] %s" % (sha[:8], f["why"][:130]))
        print()
        # A STOP from B20 or B21 fails the command. The older checks keep
        # their old exit status; changing it is not this change's to make.
        return 1 if t["calibration_stop"] else 0

    if args.cmd == "scan":
        doc, unbound, stale = scan(args.slug)
        rows = doc["bindings"]
        on_page = sum(1 for v in rows.values() if v.get("on_page"))
        print("\n  %d empirical sentence(s) on the page" % on_page)
        print("  %d bound, %d unbound" % (on_page - len(unbound), len(unbound)))
        if stale:
            print("  %d row(s) for sentences no longer on the page, kept as record"
                  % len(stale))
        print("  written to %s\n" % path(args.slug))
        return 0

    if args.cmd == "unbound":
        doc = load(args.slug)
        rows = [v for v in (doc.get("bindings") or {}).values()
                if v.get("on_page") and not v.get("span")]
        print("\n  %d unbound empirical sentence(s)\n" % len(rows))
        for r in rows[:args.limit]:
            print("  [%s] %s" % (r["why_empirical"], r["sentence"][:150]))
        print()
        return 0

    print()
    for label, state, detail in preflight_rows(args.slug):
        print("  %-6s %-34s %s" % (state, label, detail))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
