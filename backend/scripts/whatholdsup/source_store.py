#!/usr/bin/env python3
"""The library: every source document we have ever held, kept and re-readable.

WHY THIS EXISTS
---------------
On 2026-09-01 the operator asked why we do not check every sentence against the
source. The ledger answered:

    24 sources
     3 opened by a person
     8 resting on nothing but "whatever the search tool returned for this URL"

We had never acquired the sources. Each role did its own retrieval, took a
fragment, used it and threw it away; the next role searched again. The same
paper had been "read" fifteen times and opened zero times.

A fragment cannot be re-examined, cannot be diffed against next year's version,
and cannot tell you what it did NOT contain -- which is exactly how the Shaaban
paper's own "29 blocks with block size of four" was deleted from the page as if
we had invented it.

A LIBRARY, NOT A PILE
---------------------
Documents are content-addressed: one copy per distinct set of bytes, ever, under
its own sha256. Two things follow, and both are the operator's reasons rather
than mine.

  A DOCUMENT CITED BY THREE ISSUES IS STORED ONCE and each issue points at it.
  The library is the corpus; an issue's manifest is an index into it.

  A DOCUMENT THAT CHANGES IS NOT OVERWRITTEN. A corrected paper, a new guideline
  version, a registry record updated after we published -- each is new bytes,
  so a new hash, and BOTH ARE KEPT. When a correction request or a changelog
  event arrives about a sentence, the question "what did this say when we read
  it" has an answer, and "what changed since" is a diff rather than an argument.

IDENTITY IS CONFIRMED, NOT ASSUMED
----------------------------------
The first version of this module rejected documents by a blocklist of wall
phrases -- "captcha", "subscribe to continue". Within the hour it stored two
PubMed cookie-consent pages as full text, because "cookies required" was not on
the list. A blocklist can only refuse what somebody has already been caught by.

So the test is now positive, which is the same correction this project has made
three times in other places: the bytes must contain something that IDENTIFIES
the document -- a distinctive run of its title, its DOI, its PMID, its NCT
number. A page that cannot show it is the document is not stored as one, whether
or not it looks like a wall.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "backend" / "data" / "whatholdsup" / "library"
CASES = ROOT / "issues"

OK, BAD, WARN = "ok", "BLOCKED", "warn"

EXT = {"application/pdf": ".pdf", "text/html": ".html", "application/json": ".json",
       "text/plain": ".txt", "application/xml": ".xml", "text/xml": ".xml"}

STOP = {"the", "a", "an", "of", "and", "or", "in", "for", "with", "on", "to", "as",
        "at", "by", "from", "is", "are", "was", "were", "not", "no", "vs", "versus"}


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob("WHU-*-%s" % slug))
    if not hits:
        raise SystemExit("no case directory for %r" % slug)
    return hits[0]


# ---------------------------------------------------------------------------
# the library
# ---------------------------------------------------------------------------

def docs_dir() -> Path:
    return LIB / "docs"


def index_path() -> Path:
    return LIB / "index.json"


def issue_index_path(slug: str) -> Path:
    return LIB / "issues" / ("%s.json" % slug)


def _load(p: Path, default: dict) -> dict:
    if not p.exists():
        return dict(default)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)


def load_index() -> dict:
    return _load(index_path(), {
        "what_this_is": (
            "Every source document this publication has ever held, one entry per "
            "distinct set of bytes. Content-addressed, so a document cited by several "
            "issues is stored once, and a document that changes is kept ALONGSIDE the "
            "version we read rather than replacing it. That is what makes 'what did "
            "this say when we wrote the sentence' answerable when a correction request "
            "arrives."),
        "docs": {}})


def load_issue_index(slug: str) -> dict:
    return _load(issue_index_path(slug), {
        "what_this_is": ("Which document in the library each of this issue's sources "
                         "points at. The library holds the bytes; this says what we "
                         "were reading when we wrote the page."),
        "issue": slug, "sources": {}})


def save_index(ix: dict) -> None:
    LIB.mkdir(parents=True, exist_ok=True)
    index_path().write_text(json.dumps(ix, indent=2, ensure_ascii=False), encoding="utf-8")


def save_issue_index(slug: str, ix: dict) -> None:
    issue_index_path(slug).parent.mkdir(parents=True, exist_ok=True)
    issue_index_path(slug).write_text(json.dumps(ix, indent=2, ensure_ascii=False),
                                      encoding="utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def doc_path(digest: str, ext: str) -> Path:
    return docs_dir() / digest[:2] / (digest + ext)


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------

def identifying_tokens(src: dict) -> list[str]:
    """Strings that would appear in the document if these bytes really are it."""
    out = []
    for m in re.finditer(r"NCT\d{8}", json.dumps(src), re.I):
        out.append(m.group(0))
    for m in re.finditer(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", src.get("url", "") + " "
                         + src.get("title", "")):
        out.append(m.group(0).rstrip(".,)"))
    for m in re.finditer(r"PMID[: ]*(\d{6,9})|PMC(\d{6,9})", json.dumps(src)):
        out.append(m.group(0))
    title = src.get("title", "")
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9'-]{3,}", title)
             if w.lower() not in STOP]
    out.extend(words[:12])
    seen, uniq = set(), []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower()); uniq.append(t)
    return uniq


def pdftotext_path() -> str | None:
    """Find pdftotext, including where PATH will not.

    launchd starts jobs with a minimal PATH that does not include
    /opt/homebrew/bin, so shutil.which() returns nothing on a Mac where poppler
    is installed and working. The acquisition job would then report "pdftotext
    is not installed", refuse every PDF it fetched, and be believed -- a tool
    reporting an absence it was not in a position to observe, which is the error
    this repository has now recorded five times.
    """
    import shutil as _sh
    found = _sh.which("pdftotext")
    if found:
        return found
    for p in ("/opt/homebrew/bin/pdftotext", "/usr/local/bin/pdftotext",
              "/usr/bin/pdftotext", "/opt/local/bin/pdftotext"):
        if Path(p).exists():
            return p
    return None


def text_of(data: bytes, content_type: str = "", pages: int = 8) -> tuple[str, str]:
    """The document's readable text, for the identity test.

    A PDF's text is compressed, so decoding its bytes as latin-1 finds almost
    nothing -- which is how the first version of this test REFUSED two genuine
    FDA prescribing-information PDFs, reporting 1 of 4 title words. Refusing a
    real document is the safer error and it is still an error: it would have
    sent a person to hunt for a file we already had.

    pdftotext is used where present, and where it is not the caller is told the
    difference rather than being handed a confident-looking failure.
    """
    if data[:5] != b"%PDF-":
        return data.decode("utf-8", "replace"), "text"
    import subprocess
    import tempfile
    exe = pdftotext_path()
    if exe:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(data); tmp = fh.name
        try:
            cmd = [exe, "-q"] + (["-l", str(pages)] if pages else []) + [tmp, "-"]
            out = subprocess.run(cmd, capture_output=True, timeout=120)
            if out.returncode == 0 and len(out.stdout) > 200:
                return out.stdout.decode("utf-8", "replace"), "pdftotext"
        except Exception:
            pass
        finally:
            try:
                Path(tmp).unlink()
            except Exception:
                pass
    # Nothing came out. The raw bytes are returned so a title in an uncompressed
    # stream can still match, but the CALLER IS TOLD the text was never
    # extracted -- so it can say "nobody here can read this" instead of "this is
    # the wrong document". Those are different statements and only one is true.
    return data.decode("latin-1", "replace"), "unextracted"


# ---------------------------------------------------------------------------
# is it the document, or a page about the document?
# ---------------------------------------------------------------------------

# Source types whose document is an ARTICLE, and so must show an article's
# substance. A registry record, a drug label or a guideline page is not an
# article and is not held to this.
# `conference` was in this set from the day it was written and should never
# have been. A conference abstract or presentation deck is a complete document
# of its own kind: it has no reference list, no discussion section, and no
# introduction in the sense the article test means. Asked about ASCO 2024's
# LBA9512 -- eleven pages carrying the three-year hazard ratio this page prints
# -- the test answered "cannot show it is the document" and refused it.
#
# Third instance of one error today: registry postings, drug labels, and now a
# conference deck, each judged by the furniture of a journal article they were
# never going to have. The set is what the article test APPLIES to, and it has
# to be earned rather than assumed.
# Every source type this publication uses, what it is, and — where the type
# settles it — what FORM of document it is. None means the type does not settle
# the form and the source must declare one; see the note below.
TYPES = {
    # journal articles
    "primary":       ("a study's own publication", "article"),
    "comparison":    ("a study comparing others", "article"),
    "methods":       ("a methodological paper", "article"),
    "review":        ("a review article", "article"),
    "synthesis":     ("a systematic review or meta-analysis", "article"),
    # short journal items
    "corrigendum":   ("a correction or erratum notice", "notice"),
    "editorial":     ("an editorial or retraction notice", "notice"),
    # structured records
    "registry":      ("a trial registry record", "record"),
    "label":         ("a regulator-published drug label", "record"),
    "guideline":     ("a clinical guideline", "record"),
    # pages
    "conference":    ("a conference abstract or presentation", "page"),
    "press_release": ("a company's announcement about its own study", "page"),
    "coverage":      ("journalism about a study", "page"),
    "carrier":       ("a piece that carried a claim onward", "page"),
    "secondary":     ("secondary coverage or commentary on a study", "page"),
    # the type names a ROLE and does not settle the form
    "critique":      ("a critique of a study, in any form", None),
    "prior_art":     ("earlier work the page cites for context, in any form", None),
}

# THE TYPE FIELD IS OVERLOADED, and this is the finding that mattered on
# 2026-09-01.
#
# It encodes the source's ROLE in the argument -- critique, prior art, carrier,
# coverage -- and not its FORM -- journal article, news piece, registry record,
# expert-reaction page. The article test needs form. B8's closeness ranking
# needs role. One field is carrying both, so it can answer neither reliably.
#
# Issue three proves it. Under `critique` sit an OSF preprint, an arXiv comment,
# an ACG review piece and a Science Media Centre expert-reaction page: two are
# papers with reference lists, two are not. Under `prior_art` sit a
# Gastroenterology editorial and an article in The Conversation. Declaring
# either type article-or-not is guessing, and this file guessed twice and was
# wrong twice within the hour.
#
# The fix is a second field: `form`, on the source, saying what kind of document
# it is. Until every ambiguous source carries one, a type marked None here
# reports as UNDETERMINED rather than being silently assigned -- which is the
# whole point of the coverage report it feeds.
# WHAT EACH FORM MEANS, and what test it earns.
#
#   article  a research paper, review or preprint: should carry a reference
#            list and a discussion, so the article test applies
#   notice   a short journal item -- erratum, editorial, comment, letter:
#            complete at a few hundred words, no article furniture expected
#   record   a structured record -- registry posting, drug label
#   page     a web page -- journalism, a press release, an expert-reaction
#            page, a newsletter
FORMS = {"article", "notice", "record", "page"}
FORM_FLOOR = {"notice": 600, "record": 2000, "page": 2000}


def form_of(src: dict) -> str | None:
    """The form declared on the source, or the one its type settles."""
    f = src.get("form")
    if f in FORMS:
        return f
    return TYPES.get(src.get("type", ""), (None, None))[1]

# DERIVED, NEVER WRITTEN TWICE.
#
# For one hour on 2026-09-01 the registry above and this set disagreed:
# synthesis, critique and secondary were declared journal articles in one place
# and omitted from the article test in the other. The coverage report caught it
# within a minute of existing, which is the argument for both.
ARTICLE_TYPES = {t for t, (_d, form) in TYPES.items() if form == "article"}

# A COMPANY STATEMENT ABOUT A STUDY IS NOT THE STUDY.
#
# Issue one types three Merck press releases as `primary`, the same type as a
# peer-reviewed publication. Two consequences, both wrong and both invisible
# until issue one was run through these checks on 2026-09-01. The article test
# was applied to them, so a 93,668-character press release was REFUSED
# acquisition for failing to look like a paper. And B8 ranks `primary` closest
# to a claim, so a company release would have been offered as a closer source
# than The Lancet for the same figure -- on a page whose own argument turns on
# the difference between a company figure and a journal one.
PRESS = "press_release"

# The NCCN guideline licence forbids putting the document through any AI tool.
# A source carrying this flag is never acquired, never classified, and never
# quoted except from an answer a person gave after reading it.
LICENCE_KEY = "licence_forbids_machine_reading"

_MARKS = ("abstract", "introduction", "methods", "results", "discussion",
          "conclusion", "references", "acknowledg", "funding", "supplementary")


def substance(data: bytes, content_type: str = "") -> tuple[str, str]:
    """(kind, why) — full_text, abstract, or landing.

    WHY THIS EXISTS, AND IT IS THE THIRD TIME IN ONE SESSION.

    Acquisition found a free repository copy of the MONALEESA-2 overall-survival
    paper, fetched it, and stored it as full_text_held. It was the University of
    Edinburgh RESEARCH EXPLORER LANDING PAGE: 34 KB, 5,559 characters, no
    sections, the paper's title and DOI and nothing else. The identity test
    passed it precisely BECAUSE a landing page carries the title and the DOI.

    A second one, for the MONALEESA-2 updated-results paper, was the repository
    ABSTRACT page -- structured abstract, no body, no references.

    Identity and substance are different questions. "Are these bytes about the
    right paper" is not "are these bytes the paper", and every version of this
    week's error is one of those two being answered when the other was asked.

    The discriminator, measured on what is actually in the library: a full text
    carries BOTH a reference list and a discussion or introduction, and cites
    heavily (et al x22, x11 for the two real ones); the abstract page has
    neither and cites three times; the landing page has nothing at all.
    """
    # The WHOLE pdf, not the first eight pages. The identity test reads eight
    # for speed; substance must see the end of the document, because the thing
    # that separates a paper from its abstract is the REFERENCE LIST, and that
    # is on the last pages. With the eight-page limit this classified the
    # Shaaban paper -- which we hold in full and have read -- as an abstract.
    raw, _how = text_of(data, content_type, pages=0)
    if data[:5] != b"%PDF-" and data[:1] not in (b"{", b"["):
        # And strip the markup. Measuring raw HTML counted navigation chrome as
        # prose and menu labels as sections: a landing page scored 26,946
        # "characters" and two "sections" it did not have.
        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
        raw = re.sub(r"<[^>]+>", " ", raw)
    t = " ".join(raw.split()).lower()
    hits = {m for m in _MARKS if m in t}
    if len(t) < 6000 or not hits:
        return "landing", ("%d characters and %d section markers — this is a page "
                           "ABOUT the document, not the document"
                           % (len(t), len(hits)))
    if "references" in hits and ({"discussion", "introduction"} & hits):
        return "full_text", ("%d characters, reference list and %s present"
                             % (len(t), "/".join(sorted(hits & {"discussion",
                                                                "introduction"}))))
    if "abstract" in hits:
        return "abstract", ("%d characters, abstract present but no reference list "
                            "or discussion — this is the abstract, not the paper"
                            % len(t))
    return "landing", ("%d characters, sections %s — cannot show it is the document"
                       % (len(t), ",".join(sorted(hits))))


def classify(slug: str, sid: str, data: bytes,
             content_type: str = "") -> tuple[str, str]:
    """(kind, why), asking the substance question ONLY where it is the question.

    substance() discriminates a paper from a page about a paper, using an
    article's furniture: a reference list, a discussion, an introduction. Run it
    over a drug label or a ClinicalTrials.gov results posting and it returns
    "landing" with full confidence -- which is how a first pass at this
    backfill labelled the KISQALI prescribing information, all four registry
    postings and the IBRANCE warnings section as pages ABOUT documents we hold
    in full. A 221,525-character results posting is not a landing page. It is a
    complete document of a kind that has no discussion section because its kind
    does not have one.

    A test applied outside the domain it was built for does not become silent.
    It answers, and it answers wrongly, and the answer looks exactly like the
    right one. So the type decides whether the question applies at all.
    """
    src = next((x for x in sources(slug) if x.get("id") == sid), {})
    stype = src.get("type", "")
    form = form_of(src)
    if form == "article":
        return substance(data, content_type)
    if form == "page":
        kind, why = substance_page(data, content_type)
        return ("document" if kind == "full_page" else "shell",
                "form 'page' — " + why)
    if form in FORM_FLOOR:
        text, _how = text_of(data, content_type, pages=0)
        if data[:5] != b"%PDF-" and data[:1] not in (b"{", b"["):
            text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text,
                          flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", " ", text)
        n = len(" ".join(text.split()))
        if n < FORM_FLOOR[form]:
            return "stub", ("form '%s', and only %d characters — too little to "
                            "be the document" % (form, n))
        return "document", ("form '%s' — %d characters held. The article test "
                            "does not apply to this form" % (form, n))
    if form is None and stype:
        return "undetermined", ("type '%s' does not settle whether this is a "
                                "journal article, and the source declares no "
                                "form — so no substance test applies and none "
                                "has run" % stype)
    if stype and stype not in ARTICLE_TYPES:
        # THE ARTICLE TEST DOES NOT APPLY — BUT ONE QUESTION STILL DOES.
        #
        # ARTICLE_TYPES is an allow-list, and issue three's vocabulary is not in
        # it: synthesis, critique, prior_art, carrier, secondary, editorial. So
        # eighteen of the nineteen documents held for a LIVE page skipped the
        # substance test entirely and were recorded as "a complete document of
        # its own kind" without anything looking at them. That is the same
        # anti-pattern this repository documented in errata.py the same evening
        # — an allow-list built from the nouns one issue happens to use — left
        # standing here.
        #
        # A proper fix decides by the document rather than by the type name, and
        # needs to know what furniture each kind should have. Until then, the
        # one question that applies to EVERY kind: is there enough here to be a
        # document at all, or is this a stub? A Time article, an EDUCAUSE essay
        # and a retraction notice are all complete at very different lengths,
        # but none of them is 800 characters.
        text, _how = text_of(data, content_type, pages=0)
        if data[:5] != b"%PDF-" and data[:1] not in (b"{", b"["):
            text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text,
                          flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", " ", text)
        n = len(" ".join(text.split()))
        # A corrigendum or a retraction notice is complete at a few hundred
        # words; the Budzyn correction is 1,492 characters and says everything
        # it has to say. A threshold that calls those stubs is a threshold that
        # gets waived.
        floor = 600 if stype in ("corrigendum", "editorial") else 2000
        if n < floor:
            return "stub", ("type '%s', and only %d characters — too little to "
                            "be the document, whatever kind it is" % (stype, n))
        return "document", ("type '%s' — a %s is a complete document of its own "
                            "kind; the article test (reference list, discussion) "
                            "does not apply to it. %d characters held, not "
                            "examined further" % (stype, stype, n))
    return substance(data, content_type)


def substance_page(data: bytes, content_type: str = "") -> tuple[str, str]:
    """Is this the page, or the shell of one? — the article test's analogue.

    A character floor is a weak test and it was standing in for a real one. Ten
    of issue three's seventeen held documents are pages -- journalism, an
    expert-reaction page, a newsletter -- and all a page had to do was exceed
    2,000 characters. A paywall teaser, a consent wall with boilerplate, or a
    cookie notice wrapped in navigation all clear that comfortably.

    What separates a page from its shell is PROSE: sentences of the length
    people write in. Navigation, menus, cookie text and teasers are short
    fragments and legal boilerplate; an article is paragraphs. Counted on what
    is actually in the library, a real news page carries dozens of sentences
    over sixty characters and a wall carries a handful.

    Positive, like every other test here: it looks for what a page has, not for
    phrases a wall has been caught using.
    """
    text, _how = text_of(data, content_type, pages=0)
    if data[:5] != b"%PDF-" and data[:1] not in (b"{", b"["):
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text,
                      flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", " ", text)
    t = " ".join(text.split())
    sents = [x for x in re.split(r"(?<=[.!?])\s+", t) if len(x) >= 60]
    words = len(t.split())
    if len(sents) >= 12 and words >= 400:
        return "full_page", ("%d prose sentence(s) over sixty characters, %d "
                             "words — this reads as the page itself"
                             % (len(sents), words))
    return "shell", ("only %d prose sentence(s) over sixty characters in %d "
                     "words — a teaser, a wall or navigation, not the page"
                     % (len(sents), words))


def identifies(data: bytes, src: dict, content_type: str = "") -> tuple[bool, str]:
    """Do these bytes show they ARE this document?

    Positive test, deliberately. The blocklist version of this stored two PubMed
    cookie-consent pages as full text within an hour of being written, because
    "cookies required" was not a phrase anyone had been caught by yet. A
    blocklist can only refuse what has already gone wrong once.
    """
    if len(data) < 2000:
        return False, "only %d bytes" % len(data)
    raw, how = text_of(data, content_type)
    hay = raw.lower()
    toks = identifying_tokens(src)
    hard = [t for t in toks if re.match(r"(NCT\d{8}|10\.\d{4,9}/|PMID|PMC\d)", t, re.I)]
    for t in hard:
        if t.lower() in hay:
            return True, "contains its identifier %s" % t
    words = [t for t in toks if t not in hard]
    hits = [w for w in words if w.lower() in hay]
    if len(words) >= 3 and len(hits) >= max(3, (len(words) + 1) // 2):
        return True, "contains %d of %d distinctive title words" % (len(hits), len(words))
    if how == "unextracted":
        # No text came out. That is not "this is the wrong document", it is
        # "nobody here can read this document", and saying the first when you
        # mean the second is the error this whole apparatus exists to stop.
        return False, ("no text could be extracted from this PDF (pdftotext %s), so "
                       "identity could not be checked either way — look at it yourself "
                       "and use --force if it is right"
                       % ("at %s failed on it" % pdftotext_path() if pdftotext_path()
                          else "was not found on this machine"))
    return False, ("nothing in these bytes identifies them as this document "
                   "(%d of %d title words, no DOI/PMID/NCT match)"
                   % (len(hits), len(words)))


# ---------------------------------------------------------------------------
# putting things in
# ---------------------------------------------------------------------------

def put(slug: str, sid: str, data: bytes, *, url: str, via: str,
        content_type: str = "", title: str = "", note: str = "") -> dict:
    digest = sha(data)
    ext = EXT.get((content_type or "").split(";")[0].strip()) or (
        ".pdf" if data[:5] == b"%PDF-" else
        ".json" if data[:1] in (b"{", b"[") else
        ".html" if b"<html" in data[:2000].lower() else ".bin")
    p = doc_path(digest, ext)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(data)

    ix = load_index()
    row = ix.setdefault("docs", {}).setdefault(digest, {
        "file": str(p.relative_to(LIB)), "bytes": len(data),
        "content_type": content_type, "first_held": date.today().isoformat(),
        "urls": [], "titles": [], "used_by": [], "note": note})
    if url and url not in row["urls"]:
        row["urls"].append(url)
    if title and title not in row["titles"]:
        row["titles"].append(title)
    tag = "%s:%s" % (slug, sid)
    if tag not in row["used_by"]:
        row["used_by"].append(tag)
    save_index(ix)

    # WHAT KIND OF DOCUMENT IS THIS, recorded at the moment of storing.
    #
    # substance() existed for three hours before this line did, and in that gap
    # the CLI "add" path -- the path a human uses, which is the path we told
    # ourselves was the trustworthy one -- stored three documents with no
    # substance classification at all. Identity was confirmed; substance was
    # never asked. That is the same split the landing-page incident was about,
    # reintroduced one function to the left. Every route into the library now
    # answers both questions.
    kind, kind_why = classify(slug, sid, data, content_type)

    iix = load_issue_index(slug)
    prior = (iix.get("sources") or {}).get(sid) or {}
    versions = list(prior.get("superseded") or [])
    alsos = list(prior.get("also_held") or [])
    if prior.get("sha256") and prior["sha256"] != digest:
        # SUPERSEDED AND ALSO_HELD ARE DIFFERENT THINGS, and conflating them
        # destroys the reason for keeping old bytes at all.
        #
        # The Shaaban paper arrived twice on 2026-09-01: as Europe PMC full-text
        # XML from acquisition, and as the published PDF the operator supplied.
        # The first version of this recorded the XML as "superseded" by the PDF.
        # They are the same paper in two representations. A later diff of one
        # against the other would report that everything changed, which would
        # make the version history worse than useless -- it would make it
        # misleading, on precisely the question it exists to answer.
        #
        # SUPERSEDED means the document itself changed: same representation,
        # different bytes -- a corrected paper, a new guideline version, a
        # registry record updated after we published. That is a real diff and a
        # real changelog event.
        #
        # ALSO_HELD means another form of the same thing.
        prior_ext = Path(prior.get("file", "")).suffix
        entry = {"sha256": prior["sha256"], "file": prior.get("file"),
                 "held": prior.get("held"), "url": prior.get("url"),
                 "recorded": date.today().isoformat()}
        if prior_ext and prior_ext != ext:
            alsos.append(entry)
        else:
            entry["replaced"] = date.today().isoformat()
            versions.append(entry)
    iix.setdefault("sources", {})[sid] = {
        "sha256": digest, "file": row["file"], "bytes": len(data), "url": url,
        "held": date.today().isoformat(), "via": via, "note": note,
        "kind": kind, "kind_why": kind_why,
        "superseded": versions, "also_held": alsos}
    save_issue_index(slug, iix)
    return {"sha256": digest, "file": row["file"], "bytes": len(data),
            "retrieved": date.today().isoformat(), "url": url,
            "kind": kind, "kind_why": kind_why}


def put_file(slug: str, sid: str, path: Path, *, url: str, via: str,
             title: str = "", note: str = "") -> dict:
    ct, _ = mimetypes.guess_type(str(path))
    return put(slug, sid, Path(path).read_bytes(), url=url, via=via,
               content_type=ct or "", title=title, note=note)


def held(slug: str) -> dict:
    return load_issue_index(slug).get("sources") or {}


def verify(slug: str) -> tuple[list[str], list[str]]:
    intact, broken = [], []
    for sid, row in sorted(held(slug).items()):
        f = LIB / row.get("file", "")
        if not f.exists():
            broken.append("%s: %s is not in the library" % (sid, row.get("file")))
        elif sha(f.read_bytes()) != row.get("sha256"):
            broken.append("%s: %s does not match its recorded hash" % (sid, row.get("file")))
        else:
            intact.append(sid)
    return intact, broken


def sources(slug: str) -> list[dict]:
    raw = json.loads((case_dir(slug) / "sources.json").read_text(encoding="utf-8"))
    return raw.get("sources", raw) if isinstance(raw, dict) else raw


GAPS_FILE = "documents-we-do-not-hold.md"


def gaps_markdown(slug: str) -> str:
    """The list of documents we do not hold, DERIVED rather than maintained.

    The hand-written version of this file listed S004 and S016 as documents we
    could not get, hours after both were in the library. A stale gap list is
    worse than none: it is a claim about what we cannot see, made by something
    that had stopped looking, and this project has now written that sentence
    about five different mechanisms. So the file is generated from sources.json
    and the library, and regenerating it is the only way to edit it.
    """
    h = held(slug)
    lines = ["# %s — documents we do not hold" % slug.upper(),
             "",
             "GENERATED by `source_store.py %s gaps --write`. Do not hand-edit:"
             " re-run it." % slug,
             "Generated %s." % date.today().isoformat(),
             ""]

    missing, partial, forbidden = [], [], []
    for src in sources(slug):
        sid = src.get("id")
        rec = h.get(sid)
        acc = src.get("access") or {}
        # The flag sits on the SOURCE, not inside access. Reading only one of
        # the two places listed the NCCN guideline as a document nobody had
        # got, when in fact a person had read it and answered ten questions
        # from it -- the licence is why it is not in the library, and saying so
        # is the whole purpose of this section.
        if src.get(LICENCE_KEY) or acc.get(LICENCE_KEY):
            forbidden.append((src, rec))
        elif not rec:
            missing.append((src, None))
        elif rec.get("kind") not in ("full_text", "document"):
            partial.append((src, rec))

    lines += ["We hold %d of %d. Not held: %d. Held but not the whole document: %d."
              % (len(h), len(sources(slug)), len(missing), len(partial)), ""]

    def block(title, why, rows, show_kind=False):
        if not rows:
            return []
        out = ["## %s" % title, "", why, ""]
        for src, rec in rows:
            out.append("### %s — %s" % (src.get("id"), src.get("title", "")))
            out.append("")
            out.append("    state  %s" % ((src.get("access") or {}).get("state", "?")))
            out.append("    url    %s" % src.get("url", ""))
            if show_kind and rec:
                out.append("    held   %s — %s" % (rec.get("kind"), rec.get("kind_why", "")))
            used = src.get("used_for")
            if used:
                out.append("    we use it for: %s" % (used if isinstance(used, str)
                                                      else "; ".join(used)))
            out.append("")
        return out

    lines += block(
        "Not in the library at all", 
        "Until each is in the library the ledger permits only the figures a "
        "retrieval literally returned, attributed to that retrieval, and NO "
        "characterisation of the document.",
        missing)
    lines += block(
        "In the library, but not the whole document",
        "These bytes identify themselves as the right document and are not it: "
        "an abstract, or a page about it. Everything the missing part would "
        "license -- the statistical analysis, the limitations, anything the "
        "abstract does not print -- is not licensed.",
        partial, show_kind=True)
    lines += block(
        "The licence forbids machine reading",
        "This document may not be put through any AI tool. Only a person may "
        "read it, and the page may say only what that person answered, in "
        "answers recorded as such.",
        forbidden)

    lines += ["## How to add one", "",
              "Open it with whatever access you have, save the file, then, from "
              "the `backend` directory:", "",
              "    venv/bin/python3 scripts/whatholdsup/source_store.py %s \\" % slug,
              "      add <SID> <path-to-the-file> --url <url> --via \"how you got it\"",
              "",
              "It refuses a file whose text does not identify it as that "
              "document, and refuses an article whose text shows it is a page "
              "ABOUT the article. Then re-run:", "",
              "    venv/bin/python3 scripts/whatholdsup/source_store.py %s gaps --write" % slug,
              ""]
    return "\n".join(lines)


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    try:
        srcs = sources(slug)
    except Exception as exc:
        return [("source library", WARN, "could not read sources.json: %s" % exc)]
    intact, broken = verify(slug)
    h = set(intact)
    rows = []
    lying = [s["id"] for s in srcs
             if ((s.get("access") or {}).get("state") == "full_text_held" and s["id"] not in h)]
    rows.append(("library matches the ledger", OK if not lying else BAD,
                 "every source claiming a held full text has one in the library"
                 if not lying else
                 "%d source(s) claim full_text_held with nothing in the library: %s — a "
                 "field asserting a read that did not happen"
                 % (len(lying), ", ".join(lying))))
    rows.append(("held documents intact", OK if not broken else BAD,
                 "%d document(s) in the library, every hash matches" % len(intact)
                 if not broken else
                 "%d held document(s) missing or altered: %s"
                 % (len(broken), " || ".join(broken[:3]))))
    unheld = [s["id"] for s in srcs if s["id"] not in h]
    rows.append(("sources we hold", OK if not unheld else WARN,
                 "all %d source documents are in the library" % len(srcs) if not unheld else
                 "%d of %d held — not held: %s" % (len(h), len(srcs), ", ".join(unheld[:8]))))
    # THE LEDGER CAN UNDERSTATE TOO, AND ONLY OVERSTATEMENT WAS CHECKED.
    #
    # "library matches the ledger" asks whether a source CLAIMING full text has
    # one. It does not ask the reverse: a document sitting in the library under
    # a state that says nobody opened it. On 2026-09-02 S010 was added to the
    # library from a saved copy and its access state stayed `blocked`, so a
    # quotation whose wording had just been matched against those very bytes
    # went on blocking the publish for want of a source nobody had opened.
    #
    # An overstatement licenses a claim that was never checked. An
    # understatement blocks one that was, and sends somebody to fetch a document
    # already on disk. Both are the ledger disagreeing with the shelf.
    silent = [s["id"] for s in srcs
              if s["id"] in h and (s.get("access") or {}).get("state") in
              ("blocked", "not_opened", "fragment_only")]
    rows.append(("the ledger knows what the library holds",
                 OK if not silent else BAD,
                 "no held document is recorded as unread"
                 if not silent else
                 "%d document(s) are IN the library under a state that says "
                 "nobody has them: %s — update the state or say why the bytes "
                 "do not count as a read"
                 % (len(silent), ", ".join(silent))))
    frag = [s["id"] for s in srcs if (s.get("access") or {}).get("state") == "fragment_only"]
    if frag:
        rows.append(("sources that are only a fragment", WARN,
                     "%d source(s) rest on what a retrieval returned and nobody holds: %s"
                     % (len(frag), ", ".join(frag))))
    return rows


def strong_identifiers(src: dict) -> list[str]:
    """The identifiers a document PRINTS ABOUT ITSELF, parsed from the URL we
    hold. A DOI, a PMID, a PMCID, an NCT number. Never a title, never a guess."""
    url = src.get("url") or ""
    out = []
    for pat in (r"(10\.\d{4,9}/[^\s?#]+)", r"/articles/(PMC\d+)",
                r"pubmed\.ncbi\.nlm\.nih\.gov/(\d{6,9})",
                r"(NCT\d{8})", r"/article/(S\d{4}-\d{4}\(\d{2}\)\d{5}-[\dX])"):
        m = re.search(pat, url, re.I)
        if m:
            out.append(m.group(1).rstrip(".,;)"))
    for extra in ("nct", "pmid", "doi"):
        v = src.get(extra)
        if v:
            out.append(str(v))
    return out


def _searchable(data: bytes) -> str:
    txt, _how = text_of(data, "application/pdf" if data[:5] == b"%PDF-" else "",
                        pages=0)
    return txt


def ingest_scan(slug: str, folder: Path, *, limit_mb: int = 40) -> list[dict]:
    """Which files in a folder ARE sources of this issue that we do not hold.

    WHY THIS EXISTS
    ---------------
    On 2026-09-01 the errata check reported that MONARCH 3's corrigendum and the
    correction to the colonoscopy deskilling study were not in the library. Both
    were true. Both documents were also sitting in the operator's Downloads
    folder -- the colonoscopy correction since 30 August, read on the day it was
    downloaded and accurately described on the published page.

    The gap was never knowledge. It was that a document read by a person and
    then closed leaves no trace, which is the entire reason the library exists,
    and the library had only ever been run against one issue. Two live pages
    rest on fifty source documents and the library holds none of them.

    So: point this at a folder and it tells you what is already on disk. It
    decides nothing by filename. Every candidate must pass the same positive
    identity test as any other acquisition -- the bytes must contain the
    document's own DOI, PMID, NCT number or enough of its title -- so a wrong
    file cannot be matched in by being hopefully named.
    """
    srcs = [s for s in sources(slug) if s.get("id") not in held(slug)]
    out = []
    rejected = []
    files = sorted([f for f in Path(folder).iterdir()
                    if f.is_file() and f.suffix.lower() in
                    (".pdf", ".html", ".htm", ".xml", ".json", ".txt")])
    for f in files:
        try:
            if f.stat().st_size > limit_mb * 1024 * 1024:
                continue
            data = f.read_bytes()
        except Exception:
            continue
        # STRONG IDENTIFIERS ONLY, and never a title-word match.
        #
        # identifies() accepts "contains 7 of 12 distinctive title words",
        # which is sound for a document fetched FROM A SOURCE'S OWN URL and
        # unsound for a file found lying in a folder. Run over Downloads it
        # matched this publication's own melanoma page, its issue-one email and
        # three gate reports as source documents, because a page that CITES a
        # paper contains that paper's title. A document about a source is not
        # the source; it is the same identity-versus-substance confusion this
        # module was written for, arriving from the other direction.
        # The multi-match test runs over ALL sources of the issue, not only the
        # unheld ones. Restricted to unheld sources it let our own published
        # page through: every other identifier on it belonged to a source we
        # already hold, so the page looked like a single-source match.
        about = []
        for src in sources(slug):
            for k in strong_identifiers(src):
                if k.lower() in _searchable(data).lower():
                    about.append(src["id"])
                    break
        if len(about) > 1:
            rejected.append({"file": str(f), "why":
                             "carries the identifiers of %d different sources "
                             "(%s) — a document about them, not one of them"
                             % (len(about), ", ".join(about[:6]))})
            continue
        hits = []
        for src in srcs:
            strong = strong_identifiers(src)
            if not strong:
                continue
            found = [k for k in strong if k.lower() in _searchable(data).lower()]
            if found:
                hits.append((src, found))
        if hits:
            src, found = hits[0]
            ct, _ = mimetypes.guess_type(str(f))
            kind, kwhy = classify(slug, src["id"], data, ct or "")
            out.append({"file": str(f), "source": src["id"],
                        "title": (src.get("title") or "")[:70],
                        "identity": "contains its own %s" % ", ".join(found),
                        "kind": kind, "kind_why": kwhy, "bytes": len(data)})
    ingest_scan.rejected = rejected
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("add", help="put a document you already have into the library")
    a.add_argument("sid"); a.add_argument("path")
    a.add_argument("--url", required=True)
    a.add_argument("--via", required=True, help="how it was obtained, and by whom")
    a.add_argument("--note", default="")
    a.add_argument("--force", action="store_true",
                   help="store even if the bytes do not identify themselves")
    g = sub.add_parser("gaps", help="regenerate the list of documents we do not hold")
    g.add_argument("--write", action="store_true",
                   help="write it into the issue directory instead of printing it")
    ing = sub.add_parser("ingest",
                         help="find documents we already have on disk somewhere")
    ing.add_argument("folder")
    ing.add_argument("--apply", action="store_true",
                     help="actually add the matches to the library")
    ing.add_argument("--via", default="",
                     help="how these were obtained, required with --apply")
    sub.add_parser("status")
    sub.add_parser("library", help="everything the library holds, across issues")
    args = ap.parse_args()

    if args.cmd == "add":
        src = next((s for s in sources(args.slug) if s.get("id") == args.sid), {})
        data = Path(args.path).read_bytes()
        ok, why = identifies(data, src)
        if not ok and not args.force:
            print("\n  REFUSED: %s\n  Use --force only if you have looked at the file "
                  "yourself.\n" % why)
            return 2
        ct, _ = mimetypes.guess_type(str(args.path))
        kind, kind_why = classify(args.slug, args.sid, data, ct or "")
        if kind == "landing" and src.get("type") in ARTICLE_TYPES and not args.force:
            print("\n  REFUSED: %s\n  It identifies itself as the right document, but it "
                  "is not the document.\n  Use --force only if you have opened the file "
                  "yourself and disagree.\n" % kind_why)
            return 2
        row = put_file(args.slug, args.sid, Path(args.path), url=args.url, via=args.via,
                       title=src.get("title", ""), note=args.note)
        print("\n  held %s -> %s  (%d bytes, sha %s)\n  identity:  %s\n  substance: %s — %s\n"
              % (args.sid, row["file"], row["bytes"], row["sha256"][:16],
                 why if ok else "stored with --force, identity NOT confirmed",
                 row["kind"], row["kind_why"]))
        if row["kind"] != "full_text" and src.get("type") in ARTICLE_TYPES:
            print("  The ledger state for %s is %s_held, NOT full_text_held.\n"
                  % (args.sid, row["kind"]))
        return 0

    if args.cmd == "ingest":
        hits = ingest_scan(args.slug, Path(args.folder).expanduser())
        rej = getattr(ingest_scan, "rejected", [])
        if rej:
            print("\n  %d file(s) refused as documents ABOUT our sources rather "
                  "than the sources themselves:" % len(rej))
            for r in rej[:6]:
                print("    %-42s %s" % (Path(r["file"]).name[:42], r["why"][:70]))
        if not hits:
            print("\n  nothing in %s matches a source of %s that we do not "
                  "already hold\n" % (args.folder, args.slug))
            return 0
        print("\n  %d file(s) in %s are sources of %s that the library does not "
              "hold:\n" % (len(hits), args.folder, args.slug))
        for h in hits:
            print("  %-6s %-10s %s" % (h["source"], h["kind"],
                                       Path(h["file"]).name[:60]))
            print("         %s | %s" % (h["identity"][:60], h["title"]))
        if not args.apply:
            print("\n  Nothing added. Re-run with --apply --via \"how you got "
                  "them\" to store them.\n")
            return 0
        if not args.via:
            print("\n  REFUSED: --apply needs --via. How a document was obtained "
                  "is part of what the library is for.\n")
            return 2
        for h in hits:
            src = next(x for x in sources(args.slug) if x["id"] == h["source"])
            row = put_file(args.slug, h["source"], Path(h["file"]),
                           url=src.get("url", ""), via=args.via,
                           title=src.get("title", ""))
            print("  held %s -> %s (%s)" % (h["source"], row["file"][:40],
                                            row["kind"]))
        print()
        return 0

    if args.cmd == "gaps":
        text = gaps_markdown(args.slug)
        if args.write:
            out = case_dir(args.slug) / GAPS_FILE
            out.write_text(text, encoding="utf-8")
            print("\n  wrote %s\n" % out)
        else:
            print(text)
        return 0

    if args.cmd == "library":
        ix = load_index()
        print("\n  %d document(s) in the library\n" % len(ix.get("docs", {})))
        for dg, r in sorted(ix.get("docs", {}).items(), key=lambda x: -x[1]["bytes"]):
            print("  %s  %9d B  %-28s %s" % (dg[:12], r["bytes"],
                                             ", ".join(r["used_by"])[:28],
                                             (r["titles"] or [""])[0][:44]))
        print()
        return 0

    print()
    for name, state, detail in preflight_rows(args.slug):
        print("  %-8s %-32s %s" % (state, name, detail))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
