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
    """Whitespace and dash normalisation only. Nothing that changes a number."""
    s = s.replace("–", "-").replace("—", "-").replace("−", "-")
    s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    return " ".join(s.split())


# --- B2 ---------------------------------------------------------------------

def b2_present(span: str, slug: str, sid: str) -> tuple[bool, str]:
    """Is this span in the document the sentence cites?"""
    doc = _text(slug, sid)
    if doc is None:
        return False, "%s is not in the library, so the span cannot be checked" % sid
    return (_norm(span).lower() in _norm(doc).lower(),
            "searched the held bytes of %s" % sid)


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


def b6_scope(sentence: str, span: str) -> list[tuple[str, str]]:
    """(word, why) for every quantifier or hedge with nothing under it.

    "its registry record labels EVERY log-rank p-value 1-sided" against a span
    that annotates three of fifteen. "RESTRICTED to the HER2-enriched subtype"
    against "HER2-E OR Basal-like". "What PALOMA-2 ESTABLISHED" against "OS was
    not significantly improved".
    """
    sp = set(re.findall(r"[a-z]+", _norm(span).lower()))
    out = []
    for w in re.findall(r"[a-z]+", _norm(sentence).lower()):
        if w not in SCOPE_WORDS:
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
    """Does the source carry the precision we print?

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
    for keep in range(len(frac) - 1, 0, -1):
        shorter = "%s.%s" % (whole, frac[:keep])
        # a bare prefix match would find 0.51 inside 0.519; require a boundary
        if re.search(r"(?<![0-9.])%s(?![0-9])" % re.escape(shorter), d):
            return False, ("the source prints %s, not %s — we show %d decimal "
                           "place(s) the source does not"
                           % (shorter, f, len(frac) - keep))
    return True, "no shorter rounding of this figure is in the source either"
