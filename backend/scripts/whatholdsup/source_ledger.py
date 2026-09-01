#!/usr/bin/env python3
"""
What Holds Up: the source-access ledger.

WHY THIS EXISTS
---------------
On 2026-08-29 a reader found that issue two had criticised the NCCN breast
cancer guideline for a distinction the guideline itself draws, in the same
document, in a section we had never read. Six adverse characterisations of that
document were published by a pipeline in which nothing had opened it.

The information was not missing. It was written down, in prose, in the
`used_for` field of S001 in sources.json:

    "Read directly by a human on 2026-08-28: the licence forbids putting the
     document through an AI tool, so no automated check on this issue has seen
     it."

That is a disclosure. It is not a control. Nothing could act on it, because it
was a sentence rather than a state, and so the piece published six claims about
a document that no check in the pipeline was permitted to read.

The same week, and by the same mechanism, the page called MONALEESA-2's final
overall-survival p-value "two-sided" in five places. Nobody had opened the
paper's statistical section; the characterisation was produced by a model
reasoning about what such a paper probably says, and three separate gate runs
agreed with it, because a checker drawn from the same distribution as the
writer re-derives the writer's guess and reads like corroboration.

THE RULE
--------
The gate already holds that an unrun check is not a pass. This is the same
principle one level down:

    AN UNREAD SOURCE IS NOT A SOURCE THAT AGREES WITH US.

So every source carries a machine-readable access state, and the states that
mean "nobody opened this" block a publish that characterises it.

WHAT THIS DOES NOT DO
---------------------
It does not decide whether a claim is fair. It decides whether anyone was in a
position to know. Those are different questions and only the second one is
mechanical, which is exactly why this file has no model in it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "issues"

OK, BAD, WARN = "ok", "BLOCKED", "warn"

# ---------------------------------------------------------------------------
# the states
# ---------------------------------------------------------------------------
#
# Ordered by what they license. A claim needs a state at or above its bar.

# WHAT machine_read WAS, AND WHY IT IS GONE
# ------------------------------------------
# This file opens with "AN UNREAD SOURCE IS NOT A SOURCE THAT AGREES WITH US"
# and then defined a state called `machine_read` that meant, in practice:
#
#     "sections": ["whatever the search tool returned for this URL"]
#
# which is not a read. It records that a URL appeared in the citation list of a
# gate report. Nothing checked what came back, or whether anything did. And it
# sat in READ_STATES, licensing "figures, characterisation, and adverse claims"
# -- the most permissive grant in the file -- on the weakest possible evidence.
#
# On 2026-09-01 the ledger for issue two read: 24 sources, 3 opened by a person,
# 8 resting on nothing but that string. All three that had been opened were
# opened by the operator, and every one of the three produced a correction. The
# read rate and the error rate were the same number seen from two sides.
#
# Every incident that week happened inside that permission. Our own observation
# published under Tanguy's name for four days; the paper's own "29 blocks with
# block size of four" deleted from the page as if it were our arithmetic;
# PALMARES-2 described as behind a wall while the ledger called it read; a
# registry number belonging to another trial.
#
# The state that hid all of it is replaced by two that cannot:
#
#     FULL_TEXT_HELD   the document is IN THE STORE, hashed, quotable, and
#                      re-readable next year when a correction request arrives
#     FRAGMENT_ONLY    a retrieval returned something. NOT A READ STATE.
#
# A fragment cannot be re-examined, cannot be diffed, and cannot tell you what
# it did NOT contain -- which is exactly how a true sentence got deleted.

FULL_TEXT_HELD = "full_text_held"   # in the library, hashed; we can prove what it says
HUMAN_READ = "human_read"           # a person opened it. Required where a licence
                                    # forbids machine reading, as NCCN's does.
ABSTRACT_HELD = "abstract_held"     # we hold the ABSTRACT and not the paper.
FRAGMENT_ONLY = "fragment_only"     # a retrieval returned something. Not a read.
BLOCKED = "blocked"                 # we tried, by a named route, and could not get it
NOT_OPENED = "not_opened"           # nobody tried

# ABSTRACT_HELD exists because of what acquisition actually brought back on
# 2026-09-01. Free repository copies of two MONALEESA-2 papers were fetched and
# stored as full text. One was the University of Edinburgh landing page -- the
# title, the DOI, and nothing else. The other was the repository ABSTRACT page:
# structured abstract, no body, no references.
#
# Both passed the identity test, and they passed it BECAUSE a page about a paper
# carries the paper's title and DOI. Identity and substance are different
# questions, and every version of this week's error is one of them being
# answered when the other was asked.
#
# An abstract is worth holding: it is stable, quotable and re-readable, which a
# fragment is not. It is not the paper. A claim about what the STUDY found needs
# the paper; a claim about what the abstract says needs this.

STATES = (FULL_TEXT_HELD, HUMAN_READ, ABSTRACT_HELD, FRAGMENT_ONLY, BLOCKED,
          NOT_OPENED)

# What each state permits, as prose the board prints. The distinction that
# matters is between "somebody read this" and "somebody guessed".
PERMITS = {
    FULL_TEXT_HELD: "figures, characterisation, adverse claims, and quotation",
    ABSTRACT_HELD: ("what the ABSTRACT says, quoted and attributed to the abstract. "
                    "NOT what the study found, NOT its methods, and no adverse claim "
                    "about what the paper omits — we do not hold the paper"),
    HUMAN_READ: ("figures and characterisation; adverse claims and quotations need "
                 "the reader's own answer, recorded"),
    FRAGMENT_ONLY: ("ONLY the figures the retrieval literally returned, attributed to "
                    "that retrieval. NO characterisation of the document, because "
                    "nobody holds the document"),
    BLOCKED: "figures already extracted, disclosed as such; NO new characterisation",
    NOT_OPENED: "nothing. Cite it or get it.",
}

# FRAGMENT_ONLY IS DELIBERATELY NOT HERE. That is the whole change.
# ABSTRACT_HELD is a read state: somebody can open those bytes and check the
# sentence against them. What it licenses is narrower, and PERMITS says so.
# The states in which we hold the ENTIRE document, so that a claim on the page
# that some part of it could not be opened contradicts the ledger. ABSTRACT_HELD
# is deliberately absent: holding the abstract is compatible with -- is usually
# the reason for -- not having reached the methods.
HOLDS_WHOLE_DOCUMENT = (FULL_TEXT_HELD, HUMAN_READ)

READ_STATES = (FULL_TEXT_HELD, HUMAN_READ, ABSTRACT_HELD)

# Sources whose licence forbids putting the document through any automated tool.
# They can never reach FULL_TEXT_HELD, and HUMAN_READ is the ceiling: a person
# reads it and answers specific recorded questions, which is how issue two's
# NCCN claims were established (advocate/2026-08-29-adjudication.md).
LICENCE_FORBIDS_MACHINE_READING = "licence_forbids_machine_reading"


# ---------------------------------------------------------------------------
# adverse and characterising language
# ---------------------------------------------------------------------------
#
# These are recall-oriented, not precise. A false positive costs one line of
# reading on the board. A false negative is how issue two published. The list
# grows when something gets past it; every entry below is here because
# something did.

CHARACTERISING = re.compile(
    r"\b("
    r"states?|said|says|records?|reports?|describes?|defines?|grades?|assigns?|"
    r"lists?|notes?|acknowledges?|concedes?|claims?|asserts?|argues?|maintains?|"
    r"treats? \w+ as|calls?|labels?|characterises?|characterizes?"
    r")\b", re.I)

ADVERSE = re.compile(
    r"\b("
    r"fail(?:s|ed)? to|does not (?:say|state|report|address|establish|mention|disclose)|"
    r"did not (?:say|state|report|address|establish|mention|disclose)|"
    r"never (?:says|states|mentions|reports|discloses)|omits?|omitted|omission|"
    r"quietly|buried|misleading|misleads?|selective(?:ly)?|"
    r"unsupported|not supported|thin|overstates?|overstated|understates?|"
    r"without (?:saying|disclosing|acknowledging)|"
    r"we could not (?:establish|determine|verify|open)|"
    r"invites? the reader|performs? one on the reader|"
    r"is read as|read as a ranking|not a verdict|is not one"
    r")\b", re.I)

SENTENCE = re.compile(r"(?<=[.!?])\s+")


BREAK = "\x00"          # block boundary; cannot occur in page text

# THE CHANGE LOG IS NOT THE ARTICLE, AND FOUR MODULES HAVE NOW LEARNED IT
# SEPARATELY.
#
# The updates footer records what the page USED TO SAY and why it stopped.
# Every check that reads the page's CLAIMS and reads the footer too produces
# findings that are exactly inverted, because a withdrawal looks like an
# assertion:
#
#   b13          demanded a source for figures the log quotes as WRONG
#   quotations   demanded a source's wording for a sentence we had made up
#   lint         demanded a registry for "we could not establish X, so the
#                sentence no longer claims it"
#   advocate     spent 7 of 28 objections arguing against corrections we had
#                already made, including one it could not evaluate because the
#                sentence was a fragment of a correction
#
# In each case the only way to satisfy the check was to stop recording our own
# errors, which is the one thing this publication promises not to do.
#
# Checks that read the page's claims take body_only(). Checks that read the
# page's ACCOUNT OF ITSELF -- the dateline, self_description, the correction
# reconciliation -- take the whole document, because that is what they are
# about.
CHANGE_LOG = re.compile(r"<footer[^>]*id=[\"']updates[\"'][^>]*>.*?</footer>",
                        re.I | re.S)


def body_only(html_text: str) -> str:
    """The page without its change log. See CHANGE_LOG."""
    return CHANGE_LOG.sub(" ", html_text)


BLOCK = re.compile(
    r"</(?:h[1-6]|p|li|td|th|tr|blockquote|figcaption|caption|div|section|"
    r"article|dt|dd|option|label)\s*>|<br\s*/?>", re.I)


def plain(html_text: str) -> str:
    """Tag-stripped, entity-decoded page text, WITH BLOCK BOUNDARIES KEPT.

    Entities matter: the page writes &ldquo; and &mdash;, and a sentence
    splitter that sees them as words splits in the wrong places, which silently
    shortens the sentences this file matches against.

    SO DO BLOCK BOUNDARIES. Every tag used to become a space, and a heading has
    no full stop, so </h3><p> glued the heading to the sentence after it. The
    page's own sentences arrived as "What time did to the top two bars When
    KEYNOTE-942 first reported in 2023, ..." and "In this story - and this is
    the interesting part The April 2023 press release reported ...". Table rows
    and chart labels arrived as one sentence each, a whole trial table in one
    string.

    Four of the five flags on the first checked batch of model bindings were
    this: a scope word from a HEADING, reported as unmapped against a span that
    was never meant to carry it. The check was right that the words were not in
    the span. The words were not in the sentence either.

    A heading ends a sentence. So does a cell, a list item, and a line break.
    """
    import html as _h
    # A SENTINEL, NOT A NEWLINE.
    #
    # The first version substituted "\n" and had sentences() split on it -- so
    # every LINE BREAK IN THE SOURCE FILE became a sentence boundary. The body
    # paragraphs are single long lines and were unaffected; the change log is
    # hand-wrapped, and it shredded. The source advocate was handed "We had
    # called the announcement one that" and "We had skipped the three-year
    # readout, which is where the" as sentences and objected, correctly, that
    # it could not evaluate a fragment.
    #
    # A newline inside a paragraph is typesetting. A block boundary is
    # structure. Only the second ends a sentence, so only the second gets a
    # mark, and it is a character that cannot occur in page text.
    t = _h.unescape(re.sub(r"<[^>]+>", " ", BLOCK.sub(BREAK, html_text)))
    return t.replace("\r", " ").replace("\n", " ")


def sentences(text: str) -> list[str]:
    """Split on terminal punctuation AND on block boundaries (see plain())."""
    out: list[str] = []
    for chunk in re.split(r"[%s\n]" % BREAK, text):
        out += [s.strip() for s in SENTENCE.split(chunk) if s.strip()]
    return out


def identifiers(src: dict) -> list[str]:
    """Tokens that mean 'this sentence is about this source'.

    Taken from the title rather than guessed: trial names, journal names and
    organisations are what a page actually says when it refers to a study.
    """
    # An explicit alias list is authoritative. Titles are inferred from, and a
    # title like "KEYNOTE-942: a randomised, phase 2b study - The Lancet, 2024"
    # yields the trial name, which three separate sources on this page share.
    # Inference is a fallback for sources nobody has named; where somebody has
    # said how a document is referred to, that is the answer.
    explicit = [t for t in (src.get("also_called") or []) if str(t).strip()]
    if explicit:
        return sorted(set(explicit), key=len, reverse=True)

    out: list[str] = []
    title = src.get("title", "")
    # Trial and programme names: runs of capitals, often hyphenated with a digit.
    out += re.findall(r"\b[A-Z][A-Z0-9]{2,}(?:-[A-Z0-9]+)*\b", title)
    # Named organisations and journals the page refers to by name.
    for token in ("NCCN", "N Engl J Med", "NEJM", "J Clin Oncol", "Ann Oncol",
                  "Annals of Oncology", "Scientific Reports", "Cancers"):
        if token.lower() in title.lower():
            out.append(token)
    # A page refers to its sources the way prose does — "the guideline", "the
    # label", "the paper" — and almost never by the title in sources.json. The
    # first run of this audit found nothing adverse about the NCCN guideline
    # because not one of the offending sentences contained the string "NCCN".
    # So the role-nouns a page actually uses have to be declared per source, and
    # an undeclared reference is invisible here. That is the known limit of this
    # check and the reason `also_called` is not optional in practice.
    # (reached only when no explicit alias was given)
    # Deduplicate, longest first so "MONALEESA-2" beats "MONALEESA".
    seen, uniq = set(), []
    for t in sorted(set(out), key=len, reverse=True):
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return uniq


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# a wall is a property of the document; a failure is a property of our attempt
# ---------------------------------------------------------------------------

# Phrases in which the page says a source could not be opened. Deliberately
# narrow: these are the page's set formulas for it, not every sentence about
# access.
# A LIST OF PHRASINGS THIS CHECK HAS MET. It failed on 2026-09-01, on a
# sentence that had been on a live page for four days:
#
#   "the journal site blocks automated access, so we have verified the citation
#    but not read the full text ourselves"
#
# -- while the ledger recorded that source as full_text_held. Neither "blocks
# automated access" nor "not read the full text" was in the list, so the page
# claimed a document was unreachable that we hold, and the check built for
# exactly that said nothing. Found by the source advocate, arguing the paper's
# case, not by this.
#
# Allow-lists and blocklists built from vocabulary already met are always
# wrong; this is the fourth time that has been written down here. The entries
# below are broadened toward SHAPE rather than phrase -- a negated reading or
# access verb, a blocking verb near "access" -- but the honest statement is
# that this catches the phrasings somebody thought of.
INACCESSIBLE = re.compile(
    r"\b(behind a (?:pay)?wall|paywalled|"
    r"(?:could|can|did|do|does|have|has|had) ?n[o']?t (?:be |been )?"
    r"(?:fully |yet |ourselves )?(?:open|opened|reach|reached|read|access|"
    r"accessed|retrieve|retrieved|obtain|obtained)|"
    r"we (?:could|can) ?not open|not (?:publicly )?accessible|"
    r"(?:blocks?|blocked|refus\w+|denie[sd]|prevents?) [a-z ]{0,20}access|"
    r"not read the full text|"
    r"every route we tried returned a block)\b", re.I)


def undefined_states(srcs: list[dict]) -> dict[str, list[str]]:
    """Access states this module does not define, by state.

    WHY. On 2026-09-01 machine_read was abolished here: its only evidence was
    that a URL had appeared in a gate report's citation list, and it sat in
    READ_STATES licensing characterisation and adverse claims. Issue two's
    entries were rewritten to fragment_only, which licenses neither.

    Issues one and three were not. Forty-four sources on two LIVE pages went on
    carrying a state with no definition, no permit and no place in READ_STATES,
    and nothing noticed, because every check asks what a state permits and none
    asks whether the state exists.

    A vocabulary that drifts between issues is a ledger that contradicts itself
    in the same repository -- the same failure as a page contradicting its own
    source list, one level down.

    THE RAW STATE, NOT access_of(). This function asked access_of, which
    SANITISES an unknown state into NOT_OPENED before returning it -- so the
    value it tested was always one of STATES and this check could never report
    anything. It was written after forty-four undefined states reached two live
    pages, it has sat in the recall test scoring CAUGHT ever since, and on
    2026-09-01 three sources were entered with the state `not_held`, which is
    not a state, and it returned {}.

    A check that consumes a laundered value is not a check. This is the same
    shape as the canary passing because both sides of the comparison used the
    same broken normaliser, and as a preflight row printed under a mark the
    display had no key for: the control ran, and could not have failed.
    """
    out: dict[str, list[str]] = {}
    for s in srcs:
        a = s.get("access")
        st = a.get("state") if isinstance(a, dict) else None
        if st and st not in STATES:
            out.setdefault(st, []).append(s.get("id", "?"))
    return out


def undefined_state_rows(slug: str, srcs: list[dict]) -> list[tuple[str, str, str]]:
    """The preflight row. NOTHING CALLED undefined_states -- it existed, it was
    in the recall test, and no gate ran it, so the vocabulary could drift on a
    live page exactly as before."""
    bad = undefined_states(srcs)
    if not bad:
        return [("access states are defined",
                 "ok", "every source carries one of: %s" % ", ".join(STATES))]
    return [("access states are defined", "BLOCKED",
             "%d source(s) carry a state this ledger does not define, so nothing "
             "knows what they permit: %s"
             % (sum(len(v) for v in bad.values()),
                "; ".join("%s on %s" % (k, ", ".join(v)) for k, v in bad.items())))]


def inaccessibility_claims(page_text: str, srcs: list[dict]) -> list[tuple[str, dict, str]]:
    """(sentence, source, its access state) where the page says a source could
    not be opened and the ledger says somebody read it.

    WHY THIS EXISTS
    ---------------
    On 2026-08-31 the gate reported, as its most consequential finding, that
    this page says of PALMARES-2:

        "the paper itself is behind a wall we could not open"
        "We could not open PALMARES-2's declaration of interests. That is a
         statement about our access and not about its investigators, of whom we
         know nothing"

    and builds a fairness argument on it -- P-VERIFY's Pfizer funding is
    disclosed, PALMARES-2's is not, and the asymmetry is attributed to access
    rather than to a choice.

    S011's ledger entry says `machine_read`. The page contradicted its own
    ledger, in the same repository, and nothing compared them.

    THE DISTINCTION THIS CHECK IS ABOUT. "Behind a wall" is a claim about the
    DOCUMENT. "We could not open it" is a claim about OUR ATTEMPT. They are not
    the same sentence and only the second one is ours to make. Every version of
    today's recurring error is this confusion: a SOURCE role that could not
    reach a registry reporting the figure wrong; a fetch that received a
    truncated document reporting a string absent; a check reading an empty
    directory as an agent that never ran. Here it is in the page's own voice,
    in front of a reader, load-bearing for an argument about whose funding gets
    disclosed.

    WHAT IT DOES NOT DO. It does not decide whether the document is in fact
    open. It cannot: that needs a retrieval, and a retrieval that fails is
    exactly the evidence this check exists to distrust. It reports the tension
    and makes a person resolve it -- by correcting the page, or by downgrading
    a ledger entry that overstates what was read. Both are real answers and
    both should be made knowingly.
    """
    out = []
    for sent in sentences(plain(page_text)):
        if not INACCESSIBLE.search(sent):
            continue
        for src in srcs:
            names = identifiers(src)
            if not names:
                continue
            if not any(re.search(r"\b%s\b" % re.escape(n), sent, re.I) for n in names):
                continue
            state = (access_of(src) or {}).get("state")
            # WHOLE DOCUMENT, not READ_STATES.
            #
            # ABSTRACT_HELD is a read state -- the abstract was read -- and for
            # one day this check treated it as a contradiction of "we could not
            # open it". On 2026-09-01 it stopped the publish over three
            # sentences saying MONALEESA-2's updated-results paper had a
            # statistical section we could not open, while the ledger said
            # abstract_held. Those sentences and that ledger entry AGREE. A
            # source whose abstract we hold is precisely a source whose
            # statistical section we did not open.
            #
            # Only holding the whole document contradicts a claim that part of
            # it could not be reached. The check that fires where its premise
            # does not hold is the error this repository has now recorded in
            # five other places; here it was about to make a person edit a true
            # sentence to satisfy it.
            if state in HOLDS_WHOLE_DOCUMENT:
                out.append((" ".join(sent.split())[:190], src, state))
            break
    return out


def case_dir(slug: str) -> Path:
    """The directory holding this piece's case file.

    Leads resolve first. A candidate under issues/leads/<slug> has sources,
    and they need a ledger from the moment somebody starts reading -- the
    reading that decides whether to draft is the reading most likely to go
    unrecorded. Until 2026-08-29 this resolved only WHU-nnn-<slug>, so
    candidate-stage work had nowhere of its own to go and landed in a
    published issue's case file instead.
    """
    lead = CASES / "leads" / slug
    if lead.is_dir():
        return lead
    hits = sorted(CASES.glob(f"WHU-*-{slug}"))
    if not hits:
        raise SystemExit(f"no case directory for {slug!r} under {CASES}")
    return hits[0]


def sources_path(slug: str) -> Path:
    return case_dir(slug) / "sources.json"


def load(slug: str) -> dict:
    return json.loads(sources_path(slug).read_text(encoding="utf-8"))


def save(slug: str, doc: dict) -> None:
    sources_path(slug).write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def access_of(src: dict) -> dict:
    a = src.get("access")
    if not isinstance(a, dict):
        return {"state": NOT_OPENED}
    if a.get("state") not in STATES:
        return {"state": NOT_OPENED, "malformed": a.get("state")}
    return a


# ---------------------------------------------------------------------------
# the audit
# ---------------------------------------------------------------------------

def audit(slug: str, page_text: str,
          baseline_text: str | None = None) -> list[tuple[str, str, str]]:
    """Rows for the board: (label, status, detail).

    `baseline_text` is the version readers can already see. When it is given,
    only sentences that are NEW or CHANGED since then are held against the
    ledger.

    That scoping is deliberate and it is not a loophole. This gate exists to
    stop an unverified claim from being published; on a correction to a live
    page, holding the whole backlog hostage would block a correction behind
    work unrelated to it, and blocking a correction is worse than the error it
    corrects. New claims get the full bar. Old ones are reported as a backlog
    to work through, which is what they are.
    """
    doc = load(slug)
    srcs = doc.get("sources", [])
    rows: list[tuple[str, str, str]] = []

    missing = [s["id"] for s in srcs if access_of(s).get("state") == NOT_OPENED]
    rows.append((
        "source ledger complete",
        OK if not missing else BAD,
        f"{len(srcs)} source(s), each with an access record"
        if not missing else
        f"{len(missing)} source(s) with no record that anyone opened them: "
        + ", ".join(missing)))

    # A source this audit cannot recognise on the page is a source this audit
    # does not check -- and a check that matches nothing looks exactly like a
    # check that found nothing. That is the failure this whole file exists to
    # prevent, and on 2026-08-29 this file committed it: run against issue one,
    # every row came back clean because issue one's sources.json carries no
    # titles, so identifiers() returned an empty list for all ten sources and
    # not one sentence was ever compared. It reported "no claim says what an
    # unopened source says" about a page it had not read a word of.
    mute = [s["id"] for s in srcs if not identifiers(s)]
    rows.append((
        "sources are identifiable on the page",
        OK if not mute else BAD,
        "every source has a name or an alias this audit can find in the prose"
        if not mute else
        f"{len(mute)} source(s) with nothing to match on — no title, no "
        f"also_called. Every check below silently skips them and reports clean: "
        + ", ".join(mute)))

    # A row in sources.json is not thereby a source. Issue one's was built by
    # sweeping the page's links, which collected the font CDN and the
    # stylesheet host; they are still S001, S002 and S003, typed "press", with
    # an empty used_for. The ledger will faithfully record an access state for
    # a webfont, because it checks whether anyone opened a thing, not whether
    # the thing is a source.
    ASSET_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com", "cdnjs.",
                   "cdn.jsdelivr.net", "code.jquery.com")
    junk = [s["id"] for s in srcs
            if any(h in (s.get("url") or "") for h in ASSET_HOSTS)
            or not (s.get("used_for") or "").strip()]
    rows.append((
        "every source is a source",
        OK if not junk else BAD,
        "no asset hosts or empty entries in the source list"
        if not junk else
        f"{len(junk)} entr(y/ies) that cite nothing or point at an asset host — "
        f"build the list from the page's own sources section, not from a link "
        f"sweep: " + ", ".join(junk)))

    # Sources that descend from one upstream document are one source.
    #
    # Issue two said no randomised head-to-head trial existed, and the COVERAGE
    # role found agreement everywhere. Every agreeing document was downstream of
    # the same claim: NCCN summaries repeating the guideline, and P-VERIFY,
    # which the page itself quotes as describing its purpose as working "in the
    # absence of randomised trials that directly compare the three" -- and the
    # page cited that as confirmation. Counting agreeing documents is not
    # counting evidence. There is no way for a machine to detect an echo it has
    # not been told about, so this reports the derivation structure the issue
    # has declared and says plainly how much of it is independent.
    derived = [(s["id"], s.get("derives_from"))
               for s in srcs if s.get("derives_from")]
    independent = len(srcs) - len(derived)
    if derived:
        rows.append((
            "independent sources", WARN,
            "%d of %d source(s) declare an upstream: %s. Agreement between these "
            "is an echo, not corroboration."
            % (len(derived), len(srcs),
               "; ".join("%s <- %s" % (i, d if isinstance(d, str) else ", ".join(d))
                         for i, d in derived[:4]))))
    else:
        rows.append((
            "independent sources", OK,
            "no source declares an upstream. That is either true or unexamined — "
            "`derives_from` is only as good as the reading behind it."))

    read_ids = {s["id"] for s in srcs if access_of(s).get("state") in READ_STATES}

    sents = sentences(page_text)
    old_sents = set(sentences(baseline_text)) if baseline_text is not None else None

    unread_chars: list[str] = []
    backlog: list[str] = []
    adverse_unanswered: list[str] = []

    for s in srcs:
        state = access_of(s).get("state")
        ids = identifiers(s)
        if not ids:
            continue
        # A claim ABOUT one source can be sourced TO another -- the page takes
        # MONALEESA-7's test direction from the ASCO abstract of the same
        # analysis, and says so in the sentence. Declared support counts.
        supported = set(s.get("characterisation_supported_by") or []) & read_ids
        for sent in sents:
            if not any(i.lower() in sent.lower() for i in ids):
                continue
            is_new = old_sents is None or sent not in old_sents
            if state in (NOT_OPENED, BLOCKED) and CHARACTERISING.search(sent):
                if supported:
                    continue
                (unread_chars if is_new else backlog).append(
                    f"{s['id']}: {sent[:110]}")
            elif state == HUMAN_READ and ADVERSE.search(sent) and is_new:
                adverse_unanswered.append(f"{s['id']}: {sent[:110]}")

    rows.append((
        "new claims about unread sources",
        OK if not unread_chars else BAD,
        "no claim added since the live version says what an unopened source says"
        if not unread_chars else
        f"{len(unread_chars)} NEW sentence(s) say what an unopened source says. "
        "This is the class that published 'two-sided' about a paywalled "
        "statistical section: " + " | ".join(unread_chars[:4])))

    if backlog:
        rows.append((
            "unread-source backlog", WARN,
            f"{len(backlog)} sentence(s) already live say what an unopened source "
            f"says. Not blocking this correction, and not fine either: "
            + " | ".join(backlog[:3])))

    # A wall is a property of the document; a failure is a property of our
    # attempt. See inaccessibility_claims.
    walls = inaccessibility_claims(page_text, srcs)
    rows.append((
        "claims a source could not be opened",
        OK if not walls else BAD,
        "no sentence says a source is unreachable that the ledger records as read"
        if not walls else
        "%d sentence(s) tell a reader a source could not be opened, and the ledger "
        "says it WAS read. One of the two is wrong and only a person can say which: "
        "correct the page, or downgrade a ledger entry that overstates what was "
        "read. %s"
        % (len(walls),
           " | ".join("%s (%s, ledger: %s)" % (s, src["id"], state)
                      for s, src, state in walls[:3]))))

    rows.append((
        "adverse claims needing the human reader",
        OK if not adverse_unanswered else WARN,
        "none" if not adverse_unanswered else
        f"{len(adverse_unanswered)} adverse sentence(s) about a source only a "
        "person has read — the advocate cannot check these, so the reader must: "
        + " | ".join(adverse_unanswered[:3])))

    return rows


def brief(slug: str) -> str:
    doc = load(slug)
    out = [f"source ledger — {slug}", ""]
    for s in doc.get("sources", []):
        a = access_of(s)
        st = a.get("state")
        line = f"  {s['id']:5} {st:13} {s.get('title','')[:64]}"
        out.append(line)
        who = a.get("by") or "?"
        when = a.get("on") or "?"
        if st in READ_STATES:
            out.append(f"        read by {who} on {when}")
            if a.get("not_read"):
                out.append(f"        NOT read: {'; '.join(a['not_read'])}")
        elif st == BLOCKED:
            out.append(f"        blocked by {a.get('blocked_by') or 'unstated'}"
                       f" — tried {when}")
        else:
            out.append("        nobody has opened this")
        out.append(f"        permits: {PERMITS[st]}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_status(args) -> int:
    print()
    print(brief(args.slug))
    print()
    return 0


def cmd_set(args) -> int:
    doc = load(args.slug)
    for s in doc.get("sources", []):
        if s["id"] != args.id:
            continue
        a = {"state": args.state,
             "by": args.by,
             "on": args.on or date.today().isoformat()}
        if args.sections:
            a["sections"] = args.sections
        if args.not_read:
            a["not_read"] = args.not_read
        if args.blocked_by:
            a["blocked_by"] = args.blocked_by
        if args.note:
            a["note"] = args.note
        s["access"] = a
        save(args.slug, doc)
        print(f"  {args.id}: {args.state} (by {a['by']} on {a['on']})")
        print(f"  permits: {PERMITS[args.state]}")
        return 0
    print(f"no source {args.id!r} in {sources_path(args.slug)}", file=sys.stderr)
    return 1


def cmd_audit(args) -> int:
    page = ROOT / args.page
    text = plain(page.read_text(encoding="utf-8"))
    rows = audit(args.slug, text)
    print()
    for label, st, detail in rows:
        mark = {OK: "  ok ", BAD: " STOP", WARN: " warn"}[st]
        print(f"{mark:>7}  {label:38} {detail}")
    print()
    return 0 if not any(st == BAD for _l, st, _d in rows) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    sub = ap.add_subparsers(dest="cmd", required=True)

    st = sub.add_parser("status", help="what has been opened, and by whom")
    st.add_argument("slug")
    st.set_defaults(fn=cmd_status)

    se = sub.add_parser("set", help="record that a source was opened, or could not be")
    se.add_argument("slug")
    se.add_argument("id")
    se.add_argument("--state", choices=STATES, required=True)
    se.add_argument("--by", required=True, help="who opened it — a name, not a role")
    se.add_argument("--on", help="ISO date; defaults to today")
    se.add_argument("--sections", nargs="*", help="what parts were read")
    se.add_argument("--not-read", nargs="*", dest="not_read",
                    help="parts NOT read, named so the gap is a fact and not a silence")
    se.add_argument("--blocked-by", choices=("paywall", "licence", "captcha", "dead-link"))
    se.add_argument("--note")
    se.set_defaults(fn=cmd_set)

    au = sub.add_parser("audit", help="check the page's claims against the ledger")
    au.add_argument("slug")
    au.add_argument("--page", required=True, help="repo-relative path to the page")
    au.set_defaults(fn=cmd_audit)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
