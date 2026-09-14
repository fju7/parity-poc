"""No legal citation leaves in a letter unless the system put it there.

WHY THIS EXISTS
---------------
On 2026-09-14 ten appeal letters were generated through the provider
appeal prompt and every legal citation in them was checked against the
primary source -- codes.ohio.gov, the eCFR, the CMS manuals. Nineteen
distinct provisions were cited; twelve did not say what the letter claimed.
"Ohio Administrative Code 3901-1-54" (cited in seven letters as the state's
health-claims settlement standard) is the rule for property and casualty
claims. "Ohio Revised Code 3902.11" (cited as requiring insurers to disclose
their clinical criteria) is the definitions section for coordination of
benefits. "42 CFR 410.32(a)" (cited as the federal medical-necessity
standard) is the rule that diagnostic tests must be ordered by the treating
physician. Six of the twelve were hardcoded in the prompt itself; the other
six the model produced on its own. Every one carried the tone of counsel.

This is the same failure as the Signal DOIs: a plausible identifier, an
authoritative register, and nothing checking that the identifier names the
thing the sentence says it does. The prompt now instructs the model to cite
no section numbers at all. An instruction is not a control. This is the
control.

THE GATE
--------
Three steps, of which this module is the first and the one that makes the
other two safe to skip:

    extract   every string in the letter shaped like a citation to primary
              law -- statute, code, CFR, USC, administrative rule, manual
              chapter/section, section symbol. Deterministic, no model.
    refuse    if any is found, the letter is not returned. The caller may
              regenerate once with the violations named; if the second
              attempt also cites, no letter is returned at all. Fail closed
              to NO citation, never to an unverified one.
    (Phase 2) resolve -> fetch -> bind: an allow-list of provisions the
              system has retrieved from the primary source and matched to
              the obligation the letter asserts. Only a provision that passed
              all three may appear, quoted.

SINCE PHASE 2 THIS IS AN ALLOW-LIST, with the same fail-closed default. A
citation is refused unless it is on the list handed to check_letter(), and
the list is empty until something has been resolved, fetched and bound
(verify/allowlist.py, from the curated candidate table -- reviewed rows
only). On the list, a citation must still earn its sentence: every number in
the sentence that cites it must FIGURE-bind to the provision's fetched text.
With an empty list -- today, and for any state without reviewed rows -- the
behaviour is exactly the blocklist's: every citation is a violation. The
refusal is what holds when the list is empty; the list is an optimisation on
top of it, never a replacement.

WHAT COUNTS AS A CITATION
-------------------------
Anything a reader could look up and find to be wrong: a section symbol; a
title-and-section CFR or USC reference; a state code section ("Ohio Revised
Code 3901.38", "R.C. 3901.38", "Cal. Ins. Code 10123.13"); an administrative
rule ("OAC 3901-1-54", "Rule 3901-1-54"); a CMS manual by publication number
or chapter-and-section; the NCCI manual by chapter or section; a numbered
LCD/NCD. NOT counted: "applicable state prompt-pay requirements", "the
plan's medical-necessity standard", "external review" -- true statements
with no checkable number, which is the register the prompt asks for.

False positives are cheap here (a regeneration); false negatives are a wrong
law in a letter to a payer. So the patterns lean wide, and "Section 3" of
the letter's own outline is excluded by requiring a dotted or long number.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Each pattern is one family. Order does not matter; overlaps are de-duplicated
# by span.
_FAMILIES = {
    "section_symbol":   r"§+\s*[\dA-Za-z][\w.\-()]*",
    "cfr":              r"\b\d{1,2}\s*C\.?\s?F\.?\s?R\.?\s*(?:§+\s*)?(?:Part\s*)?\d[\w.\-()]*",
    "usc":              r"\b\d{1,2}\s*U\.?\s?S\.?\s?C\.?(?:A\.?)?\s*(?:§+\s*)?\d[\w.\-()]*",
    "state_code":       r"\b(?:Revised\s+Code|Rev\.?\s+Code|R\.C\.|Gen\.?\s+Laws?|Gen\.?\s+Stat\.?|Ann\.?\s+Stat\.?|Comp\.?\s+Stat\.?|"
                        r"Ins\.?\s+Code|Insurance\s+Code|Health\s+&\s+Safety\s+Code|Stat\.?|Statutes?\s+(?:Ann\.?|Annotated))"
                        r"\s*(?:§+|[Ss]ec(?:tion|\.)|[Cc]h(?:apter|\.))?\s*\d[\d.\-:]*\w*",
    "admin_code":       r"\b(?:Administrative\s+Code|Admin\.?\s+Code|O\.?A\.?C\.?|C\.?C\.?R\.?|N\.?Y\.?C\.?R\.?R\.?|Tex\.?\s+Admin\.?\s+Code)"
                        r"\s*(?:§+|[Rr]ule|[Tt]it(?:le|\.))?\s*\d[\d.\-:()]*\w*",
    "rule":             r"\b[Rr]ule\s+\d{2,}[\d.\-:]*",
    "cms_publication":  r"\b(?:Pub(?:lication|\.)?\s*)?100-0\d\b(?:[^.\n]{0,40}?\b[Cc]hapter\s+\d+)?(?:[^.\n]{0,20}?\b[Ss]ection\s+[\d.]+)?",
    "manual_section":   r"\b(?:IOM|NCCI|Policy\s+Manual|Processing\s+Manual|Benefit\s+Policy\s+Manual|Program\s+Integrity\s+Manual)\b[^.\n]{0,60}?\b[Cc]hapter\s+\d+(?:[^.\n]{0,20}?\b[Ss]ection\s+[\w.]+)?",
    "chapter_section":  r"\b[Cc]hapter\s+\d+,\s*[Ss]ection\s+[\dA-Z][\w.]*",
    "dotted_section":   r"\b[Ss]ec(?:tion|\.)\s+\d+\.\d+[\w.]*",
    "coverage_det":     r"\b(?:LCD|NCD)\s*(?:#|No\.?|L|)\s*\d{3,}",
}
_RX = {k: re.compile(v) for k, v in _FAMILIES.items()}


@dataclass(frozen=True)
class Citation:
    family: str
    text: str
    start: int
    end: int


def find_citations(text: str) -> list[Citation]:
    """Every citation-shaped string in `text`, de-duplicated by span, in order."""
    raw: list[Citation] = []
    for fam, rx in _RX.items():
        for m in rx.finditer(text or ""):
            raw.append(Citation(fam, " ".join(m.group(0).split()), m.start(), m.end()))
    # A match inside a longer match is the same citation seen twice
    # ("§ 424.5(a)(6)" inside "42 CFR § 424.5(a)(6)"): keep the longer one.
    keep = [c for c in raw if not any(o is not c and o.start <= c.start and c.end <= o.end
                                      and (o.end - o.start) > (c.end - c.start) for o in raw)]
    seen, out = set(), []
    for c in sorted(keep, key=lambda c: (c.start, -c.end)):
        if (c.start, c.end) not in seen:
            seen.add((c.start, c.end)); out.append(c)
    return out


_SENTENCE_END = re.compile(r"(?<=[.;:])\s+|\n+")


def _sentence_around(text: str, start: int, end: int) -> str:
    """The sentence (or line) that contains [start, end)."""
    left = max((m.end() for m in _SENTENCE_END.finditer(text, 0, start)), default=0)
    m = _SENTENCE_END.search(text, end)
    return text[left: m.start() if m else len(text)]


def check_letter(letter_text: str, allowed=None) -> list[Citation]:
    """The citations that make this letter unsendable. Empty means it may go.

    `allowed`: the verify.allowlist.Allowed entries for this letter, or None /
    empty. A citation is a violation unless it resolves to an allowed
    provision AND every number in its sentence is in that provision's text.
    """
    found = find_citations(letter_text)
    if not allowed:
        return found
    from verify import law
    from verify.bind import bind_figure
    by_ident = {(a.identifier.system, a.identifier.value): a for a in allowed}
    out = []
    for c in found:
        ident = law.identify(c.text)
        a = by_ident.get((ident.system, ident.value)) if ident else None
        if a is None:
            out.append(c); continue
        sentence = _sentence_around(letter_text, c.start, c.end)
        fig = bind_figure(sentence, a.document)
        if not fig.ok:
            out.append(Citation(c.family, f"{c.text} [{fig.reason}]", c.start, c.end))
    return out


def violations_note(cites: list[Citation]) -> str:
    """The message handed back to the model on the one permitted regeneration."""
    seen, out = set(), []
    for c in cites:
        if c.text not in seen:
            seen.add(c.text)
            out.append(c.text)
    return ("The previous draft cited the following, which is not permitted. Rewrite "
            "the letter with NO statute, code, CFR, USC, rule, manual chapter/section, "
            "or section number of any kind; state each obligation in plain words "
            "instead:\n  - " + "\n  - ".join(out))
