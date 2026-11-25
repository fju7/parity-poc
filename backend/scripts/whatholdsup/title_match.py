"""Identity matching for a proposed source against a registry record (advisor's ruling 1 after the P091 build,
2026-11-24): the rules proven in backend/verify/search.py, ported, because WHU's modules do not import the shared
verify package (backend/tests/verify/test_units.py, design doc §8).

Ported verbatim in behaviour from:
  verify/text.py    LITERATURE_BOILERPLATE, normalise, content_tokens, agreement
  verify/search.py  MATCH_RATIO, MATCH_MIN, _title_matches, surname_tokens, _author_ok, _year_ok

THE MATCH RULE (verify/search.py): a candidate's title agrees when one normalised title contains the other (with at
least two distinctive words on each side), or when the shared distinctive words are at least MATCH_RATIO of the
smaller set AND number at least MATCH_MIN. A first author agrees by family-name tokens (compound and particled
surnames: 'Di Pietrantonj', 'van der Linden', 'Ben-Shlomo'); a year agrees within one (epub vs print). Either is
skipped, never refused, when one side has none.

It replaces find_access.titles_agree's three-shared-words test for identity (orch/resolve.py), which on
2026-11-24 let a Crossref "Correction: KV3.1 channel modulation: a systematic review of pharmacological intervention
strategies" through for "Inclusive Strategies for Children With Developmental Disabilities in Mainstream Classrooms
in Africa: A systematic review" on "strategies", "systematic", "review". Under this rule those share one distinctive
word ("systematic" and "review" are boilerplate): ratio 1/7, refused. backend/tests/test_whu_title_match.py holds the
golden cases of tests/verify/golden_search.json and that one, and checks this port against verify itself.
"""
from __future__ import annotations

import re
import unicodedata

MATCH_RATIO = 0.6
MATCH_MIN = 3

# verify/text.py LITERATURE_BOILERPLATE, copied (the port test checks it is identical)
LITERATURE_BOILERPLATE = {
    "a", "an", "the", "of", "in", "for", "with", "and", "or", "to", "on", "at", "by", "from",
    "vs", "versus", "plus", "study", "trial", "phase", "randomized", "randomised",
    "double", "blind", "blinded", "placebo", "controlled", "multicenter", "multicentre",
    "open", "label", "active", "evaluate", "evaluation", "test", "investigational",
    "patients", "participants", "adults", "subjects", "efficacy", "safety", "comparing",
    "compared", "comparison", "treatment", "therapy", "first", "second", "line", "i", "ii",
    "iii", "iv", "1", "2", "3", "4", "who", "have", "as", "after", "before", "using", "use",
    "assessment", "analysis", "effect", "effects", "outcomes", "results", "review",
    "systematic", "final", "overall", "update", "updated", "years", "year",
    "advanced", "cancer", "cancers", "disease", "metastatic", "carcinoma", "early", "stage",
}


def normalise(s: str | None) -> str:
    """verify.text.normalise: for SHORT strings (titles); strips <tags>."""
    s = unicodedata.normalize("NFKD", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def content_tokens(s: str, boilerplate: set[str] = LITERATURE_BOILERPLATE) -> set[str]:
    return {w for w in normalise(s).split() if w not in boilerplate and len(w) > 2 and not w.isdigit()}


def agreement(ours: str, theirs: str, boilerplate: set[str] = LITERATURE_BOILERPLATE) -> tuple[float, set[str]]:
    """verify.text.agreement: (ratio, shared); containment of one normalised string in the other is 1.0."""
    a = normalise(ours)
    ta = content_tokens(ours, boilerplate)
    best, best_shared = 0.0, set()
    for cand in (theirs or "").split(" || "):
        b = normalise(cand)
        if not b:
            continue
        if a and b and (a in b or b in a or a.replace(" ", "") in b.replace(" ", "")
                        or b.replace(" ", "") in a.replace(" ", "")):
            return 1.0, ta or {a}
        tb = content_tokens(cand, boilerplate)
        if ta and tb:
            shared = ta & tb
            r = len(shared) / min(len(ta), len(tb))
            if r > best:
                best, best_shared = r, shared
    return round(best, 3), best_shared


def title_matches(proposed: str, candidate: str) -> tuple[bool, float, set]:
    """verify.search._title_matches."""
    ratio, shared = agreement(proposed, candidate)
    ours = len(content_tokens(proposed))
    theirs = len(content_tokens(candidate))
    if ratio == 1.0 and shared and min(ours, theirs) >= 2:
        return True, ratio, shared                       # containment
    return (ratio >= MATCH_RATIO and len(shared) >= MATCH_MIN), ratio, shared


_INITIALS = re.compile(r"^(?:[A-Z]\.?){1,3}$")


def surname_tokens(name: str) -> list[str]:
    """verify.search.surname_tokens: 'Di Pietrantonj C' -> ['di', 'pietrantonj']; 'A. Hviid' -> ['hviid']."""
    head = (name or "").split(",")[0].strip()
    head = unicodedata.normalize("NFKD", head).encode("ascii", "ignore").decode()
    raw = [t for t in re.split(r"[\s\-'’.]+", head) if t]
    while raw and _INITIALS.match(raw[0]):
        raw.pop(0)
    while raw and _INITIALS.match(raw[-1]):
        raw.pop()
    return [re.sub(r"[^a-z]", "", t.lower()) for t in raw if re.sub(r"[^a-z]", "", t.lower())]


def author_ok(proposed: str | None, found: str | None) -> bool:
    """verify.search._author_ok: FOUND is the registry's FIRST author, whole ('Di Pietrantonj C')."""
    if not proposed or not found:
        return True
    p, f = surname_tokens(proposed), surname_tokens(found)
    if not p or not f:
        return True
    if p == f:
        return True
    pj, fj = "".join(p), "".join(f)
    if pj == fj or (len(pj) >= 4 and (pj in fj or fj in pj)):
        return True
    n = len(p)
    return any(f[i:i + n] == p for i in range(len(f) - n + 1)) or \
        any(p[i:i + len(f)] == f for i in range(n - len(f) + 1))


def year_ok(proposed, found) -> bool:
    """verify.search._year_ok: within one year when both are given."""
    try:
        p = int(proposed) if proposed not in (None, "") else None
        f = int(found) if found not in (None, "") else None
    except (TypeError, ValueError):
        return True
    if not p or not f:
        return True
    return abs(p - f) <= 1


def first_author(author_string: str | None) -> str | None:
    """The registry's first author, whole: the part of an 'A, B, C' author string before the first comma."""
    return (author_string or "").split(",")[0].strip() or None


def check(proposed_title: str, proposed_author: str | None, proposed_year, record: dict) -> tuple[bool, str]:
    """(agrees, why) for a registry RECORD in Europe PMC's field names (title, authorString, pubYear)."""
    ok, ratio, shared = title_matches(proposed_title, record.get("title") or "")
    if not ok:
        return False, "title does not agree: ratio %.3f on %d shared distinctive word(s) (needs containment, or " \
                      "%.1f on %d)" % (ratio, len(shared), MATCH_RATIO, MATCH_MIN)
    fa = first_author(record.get("authorString"))
    if not author_ok(proposed_author, fa):
        return False, "first author %r does not agree with the record's first author %r" % (proposed_author, fa)
    if not year_ok(proposed_year, record.get("pubYear")):
        return False, "year %s does not match the record's %s" % (proposed_year, record.get("pubYear"))
    return True, "title ratio %.3f on %d shared; first author and year agree where given" % (ratio, len(shared))
