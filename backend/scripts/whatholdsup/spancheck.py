#!/usr/bin/env python3
"""B2, B3, B5, B6 — the four span checks, as functions over real bytes.

Spec: docs/whatholdsup-claim-bindings-spec.md, section 4.

Each is a pure function of (what the sentence says, what span it claims, what
the document actually contains). None calls a model. None asserts that a
sentence is true: R1 governs this file. B2 says a string is or is not in a
document. B5 says a span stops mid-thought. B6 says a word in the sentence has
nothing under it in the span. What that MEANS is a person's to decide.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store  # noqa: E402


def _text(slug: str, sid: str) -> str | None:
    rec = (store.held(slug) or {}).get(sid)
    if not rec:
        return None
    f = store.LIB / rec.get("file", "")
    if not f.exists():
        return None
    ct = {".pdf": "application/pdf", ".json": "application/json",
          ".html": "text/html", ".xml": "application/xml"}.get(f.suffix, "")
    txt, _how = store.text_of(f.read_bytes(), ct, pages=0)
    if ct in ("text/html", "application/xml"):
        # SCRIPT AND STYLE CONTENTS ARE NOT THE DOCUMENT. Autobind's first run
        # on issue one bound "the overall survival interval runs 0.165 to 1.345"
        # to a span of CSS and JSON-LD from a press release's page furniture,
        # because the numbers occur inside a <script> block. A span drawn from
        # markup is worse than no span: it looks like evidence.
        txt = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", txt,
                     flags=re.S | re.I)
        txt = re.sub(r"<[^>]+>", " ", txt)
    return " ".join(txt.split())


def _norm(s: str) -> str:
    """Whitespace, dash and DECIMAL-SEPARATOR normalisation. Nothing that
    changes a number's value.

    THE LANCET WRITES ITS DECIMALS WITH A MIDDLE DOT: 0·561, 0·309-1·017,
    two-sided p=0·053. Every check in this file searched for "0.053" with a
    full stop, so on 2026-09-01 B2 reported three times that a figure was in no
    document we held while it sat in an abstract we had held all day, and sent
    the operator looking for a paywalled PDF he did not need.

    An absence reported by something that could not have seen the thing is not
    an absence -- recorded here for the eighth time, and the first time it was
    caused by a character.

    Only BETWEEN DIGITS, so a middle dot used as anything else is left alone.
    """
    s = re.sub(r"(?<=\d)[·•](?=\d)", ".", s)
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    return " ".join(s.split())


# --- B2 ---------------------------------------------------------------------

UNDETERMINED = "undetermined"


def b2_present(span: str, slug: str, sid: str,
               *, trust_canary: bool = True) -> tuple[bool | str, str]:
    """Is this span in the document the sentence cites?

    THREE ANSWERS, NOT TWO. True, False, or UNDETERMINED.

    On 2026-09-01 this function said False three times about a figure sitting in
    a document held since morning, because the publisher writes decimals with a
    middle dot and the normaliser could not read them. It said False in exactly
    the words it uses when it is right, and an operator went looking for a
    paywalled PDF on the strength of it.

    A document that fails the canary round trip is not one this function can
    report absences about. It returns UNDETERMINED, which callers must not treat
    as False -- "we could not tell" and "it is not there" are different states
    and merging them is the oldest error recorded in this repository.
    """
    doc = _text(slug, sid)
    if doc is None:
        return UNDETERMINED, ("%s is not in the library, so the span cannot be "
                              "checked either way" % sid)
    if _norm(span).lower() in _norm(doc).lower():
        return True, "searched the held bytes of %s" % sid
    if trust_canary:
        try:
            import canary as _canary
            if sid in _canary.unreadable(slug):
                return UNDETERMINED, (
                    "%s fails the canary round trip — figures taken out of it "
                    "cannot be found in it, so this pipeline cannot read this "
                    "document and its absences mean nothing" % sid)
        except BaseException:
            # case_dir raises SystemExit, which is not an Exception. Third time
            # in one day that this distinction has broken something here.
            pass
    return False, "searched the held bytes of %s" % sid


# --- B3 ---------------------------------------------------------------------

def b3_elsewhere(span: str, slug: str, exclude: str) -> tuple[str | None, str]:
    """When B2 fails, WHICH document does say this? A failure that names the
    right source repairs the sentence instead of merely refusing it."""
    for sid in sorted(store.held(slug) or {}):
        if sid == exclude:
            continue
        doc = _text(slug, sid)
        if doc and _norm(span).lower() in _norm(doc).lower():
            return sid, "the span is in %s, not %s" % (sid, exclude)
    return None, "no held document contains this span"


# --- B5 ---------------------------------------------------------------------

# What a span must not stop in front of. A range continues; a conjunction
# continues; a clause that carries the other half of the schedule continues.
CONTINUES = re.compile(
    r"^\s*(?:to\b|and\b|or\b|-\s*\d|–\s*\d|,\s*(?:and|or|at|to)\b|"
    r"at the beginning\b|every\b|monthly\b|then\b)", re.I)


def b5_complete(span: str, slug: str, sid: str) -> tuple[bool, str]:
    """Does the span stop mid-thought?

    The commonest way a true span becomes a false sentence. "Grade 3 diarrhea
    occurred in 8%" is in the label; the label says "8% to 20%". "Monitor LFTs
    every 2 weeks for the first 2 cycles" is in the label; the label continues
    "at the beginning of each subsequent 4 cycles".
    """
    doc = _text(slug, sid)
    if doc is None:
        return False, "%s is not in the library" % sid
    d, s = _norm(doc), _norm(span)
    i = d.lower().find(s.lower())
    if i < 0:
        return False, "the span is not in %s at all (B2)" % sid
    tail = d[i + len(s):]
    m = CONTINUES.match(tail)
    if m:
        return False, ("the span stops immediately before %r — the document "
                       "continues: %r" % (m.group(0).strip(),
                                          (s + tail[:70]).strip()))
    return True, "the span ends where the document's own thought ends"


# --- B6 ---------------------------------------------------------------------

QUANTIFIERS = {"every", "all", "each", "none", "no", "any", "never", "always",
               "entire", "whole", "universally", "invariably"}

SCOPE_WORDS = {
    "every", "all", "each", "none", "no", "never", "always", "only", "any",
    "restricted", "limited", "solely", "exclusively", "established",
    "confirmed", "demonstrated", "proved", "proven", "shows", "showed",
    "entire", "whole", "universally", "invariably",
}
# A scope word is satisfied by its own appearance in the span, or by a token
# that carries the same force. Deliberately generous: this check exists to find
# a word with NOTHING under it, not to police synonyms.
EQUIVALENT = {
    "every": {"every", "all", "each"},
    "all": {"all", "every", "each"},
    "each": {"each", "every", "all"},
    "none": {"none", "no", "not", "neither"},
    "no": {"no", "none", "not", "neither"},
    "never": {"never", "not", "no"},
    "only": {"only", "solely", "exclusively"},
    "restricted": {"restricted", "limited", "confined", "only", "solely"},
    "established": {"established", "demonstrated", "proved", "proven", "shown"},
    "confirmed": {"confirmed", "verified", "established"},
}


# A scope word only matters where the sentence is making a claim ABOUT WHAT THE
# SOURCE SAYS. Run without this, B6 flagged "no" in the chart label "0.5 1.0 —
# no effect 1.5", "any" in "before any of these trials had mature survival
# data", and "whole" in an aside — none of which quantifies over a document's
# contents. Five false flags in six teaches a reader to skip the sixth, which
# was the real one: "labels EVERY log-rank p-value on the study".
REPORTS = re.compile(
    r"\b(?:say|says|said|state|states|stated|label|labels|labelled|list|lists|"
    r"post|posts|posted|print|prints|printed|record|records|recorded|report|"
    r"reports|reported|show|shows|showed|give|gives|given|carr(?:y|ies|ied)|"
    r"describe|describes|described|annotat\w+|contain|contains|contained)\b",
    re.I)


def b6_scope(sentence: str, span: str) -> list[tuple[str, str]]:
    """(word, why) for every quantifier or hedge with nothing under it.

    "its registry record labels EVERY log-rank p-value 1-sided" against a span
    that annotates three of fifteen. "RESTRICTED to the HER2-enriched subtype"
    against "HER2-E OR Basal-like". "What PALOMA-2 ESTABLISHED" against "OS was
    not significantly improved".
    """
    # TWO KINDS OF SCOPE WORD, and only one needs the reporting guard.
    #
    # QUANTIFIERS — every, all, none, any — are the ones that produced the false
    # flags: "no effect" on a chart axis, "any of these trials". They only make
    # a claim about a document's contents when the sentence says the document
    # says something, so they are guarded by REPORTS.
    #
    # EPISTEMIC words — established, confirmed, demonstrated, restricted, only —
    # are claims about what the source SUPPORTS, and need no reporting verb.
    # "What PALOMA-2 established" and "HARMONIA was restricted to the
    # HER2-enriched subtype" carry no reporting verb and are both errors this
    # check exists to catch. Guarding them cost two true positives for five
    # false ones, which is a worse trade than the one it replaced.
    reports = bool(REPORTS.search(sentence))
    sp = set(re.findall(r"[a-z]+", _norm(span).lower()))
    out = []
    for w in re.findall(r"[a-z]+", _norm(sentence).lower()):
        if w not in SCOPE_WORDS:
            continue
        if w in QUANTIFIERS and not reports:
            continue
        ok = EQUIVALENT.get(w, {w}) & sp
        if not ok:
            out.append((w, "the sentence says %r and the span contains no word "
                           "carrying that force" % w))
    # de-duplicate, keep order
    seen, uniq = set(), []
    for w, why in out:
        if w not in seen:
            seen.add(w)
            uniq.append((w, why))
    return uniq


# --- B12 --------------------------------------------------------------------

def b12_precision(figure: str, slug: str, sid: str) -> tuple[bool, str]:
    """Does the source carry the precision we print? ASK IT OF THE CITED SOURCE.

    THIS CHECK IS ONLY MEANINGFUL AGAINST THE DOCUMENT THE SENTENCE CITES.

    On 2026-09-01 it was run against whatever document happened to be in the
    library and reported that issue one's "HR 0.510" was an added decimal,
    because the Merck press release prints HR=0.51. The page does not cite the
    press release. It cites the Journal of Clinical Oncology five-year paper,
    which prints 0.510 exactly as we do -- and which nobody held until an hour
    later. A correct sentence was reported to the operator as an error because
    the check was pointed at a document we had rather than the document the
    claim rests on.

    That is the failure this whole layer exists to prevent, committed inside the
    layer. It is also the argument for bindings: a check without a binding has
    to be told which source to look at, and whoever tells it can be wrong.

    Issue one prints "HR 0.510 (0.294-0.887)". The Merck release it cites says
    "HR=0.51". The interval limits match to three decimals and the point
    estimate does not, because the source never gave three. It prints
    "HR 0.561" for the Lancet paper; the digits we hold are "0.56", and they
    are in a company press release rather than in the paper.

    A reader seeing 0.510 infers the source reported three significant figures.
    It reported two. This is not a rounding quibble: added precision is a claim
    about how finely the underlying result was measured, and it is ours rather
    than theirs.

    Deterministic and cheap: if the figure is absent but a SHORTER rounding of
    it is present, say so.
    """
    doc = _text(slug, sid)
    if doc is None:
        return True, "%s is not in the library" % sid
    d = _norm(doc)
    f = _norm(figure)
    if f.lower() in d.lower():
        return True, "the source carries this figure as printed"
    if "." not in f:
        return True, "not a decimal figure"
    whole, frac = f.split(".", 1)
    # ONE DECIMAL PLACE AT A TIME, and never down to a single digit.
    #
    # The first version walked all the way down, so asked about 0.561 it found
    # "0.5" somewhere in a paper and reported that the source prints 0.5. A bare
    # 0.5 in a document is not a statement of the same quantity; it is a digit.
    # Only a rounding one place shorter is evidence that the source reported the
    # figure less precisely than we do.
    for keep in range(len(frac) - 1, max(0, len(frac) - 2), -1):
        if keep < 2:
            break
        shorter = "%s.%s" % (whole, frac[:keep])
        # a bare prefix match would find 0.51 inside 0.519; require a boundary
        # AND IT MUST BE THE CORRECT ROUNDING. Truncating 0.008 gives "0.00",
        # which is not what a source reporting that figure less precisely would
        # print — it would print 0.01. Run over a registry posting, the
        # truncating version announced that "the source prints 0.00, not 0.008".
        try:
            rounded = ("%%.%df" % keep) % float(f)
        except ValueError:
            break
        if rounded != shorter:
            continue
        if re.search(r"(?<![0-9.])%s(?![0-9])" % re.escape(shorter), d):
            return False, ("the source prints %s, not %s — we show %d decimal "
                           "place(s) the source does not"
                           % (shorter, f, len(frac) - keep))
    return True, "no shorter rounding of this figure is in the source either"
