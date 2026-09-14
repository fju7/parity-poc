"""FIGURE normalisation: the numbers a text contains, as canonical values.

Design doc §4a. A gate that compares strings refuses "thirty days" against a
statute that says "30 days" and admits nothing it should refuse in exchange.
So both the assertion and the document reduce to the SET OF NUMBERS they
contain, digits or words, and a figure is found when its value is in the set.
Units are not compared (see the doc for why).

Forms handled, each with a test:
  digits      30 · 1,961 · 0.561 · 0·561 (Lancet middle dot) · 18% · 18 per cent ·
              0.72–0.90 (en dash range → both bounds) · −0.5 / -0.5 (unicode minus) ·
              P<0.001 · 30-day · 45-day · (30)
  words       thirty · thirty-nine · forty five · one hundred · two hundred and ten ·
              eighteen per cent · eighteen percent · two and a half · thirty (30)
A form not handled is a false refusal — the safe direction — and gets added.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
         "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
         "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
         "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
        "eighty": 80, "ninety": 90}
SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000}
FRACTIONS = {"half": Decimal("0.5"), "quarter": Decimal("0.25"), "third": Decimal("0.3333")}
_WORD = set(UNITS) | set(TENS) | set(SCALES) | {"and", "a"}

# digits: optional sign, thousands groups or plain, decimal point OR middle dot
# Thousands groups may be separated by a comma, a thin space (U+2009), a
# narrow no-break space (U+202F) or a plain space: Annals writes "657 461
# children" and "5 025 754 person-years". A space-separated group counts only
# when every following group is exactly three digits.
_SEP = r"[,\u2009\u202f ]"
_DIGIT = re.compile(r"(?<![\w.])[−\-]?(?:\d{1,3}(?:" + _SEP + r"\d{3})+|\d+)(?:[.·]\d+)?(?![\w])")
_WORDS = re.compile(r"\b(?:" + "|".join(sorted(_WORD | {"per", "cent", "percent"}, key=len, reverse=True))
                    + r")(?:[\s\-]+(?:" + "|".join(sorted(_WORD | {"half", "quarter", "third"}, key=len, reverse=True))
                    + r"))*\b", re.I)


def _canon(d: Decimal) -> str:
    d = d.normalize()
    return format(d, "f") if d == d.to_integral() else format(d, "f").rstrip("0").rstrip(".")


def _digits(text: str) -> set[str]:
    out = set()
    for m in _DIGIT.finditer(text):
        raw = m.group(0)
        # "23 million": the digits belong to the composed figure (_digit_scales),
        # not to a figure of 23 on their own.
        if re.match(r"\s*(hundred|thousand|million|billion)\b", text[m.end():], re.I):
            continue
        s = re.sub(_SEP, "", raw).replace("·", ".").replace("−", "-")
        try:
            v = Decimal(s)
        except InvalidOperation:
            continue
        out.add(_canon(v))
        # An ASCII hyphen before a number is usually a dash, not a sign: the
        # CMS manual writes modifier "-25", a code range "99221-99238". Keep
        # the unsigned value too. A unicode minus (−0.5) is a sign and stays.
        if raw.startswith("-"):
            out.add(_canon(-v))
    return out


def _words_value(tokens: list[str]) -> Decimal | None:
    """Value of a run of number words, or None if it is not one.
    'two hundred and ten' -> 210; 'thirty-nine' -> 39; 'two and a half' -> 2.5."""
    total = Decimal(0); current = Decimal(0); seen = False; frac = None
    for t in tokens:
        t = t.lower()
        if t in UNITS:
            current += UNITS[t]; seen = True
        elif t in TENS:
            current += TENS[t]; seen = True
        elif t == "hundred":
            current = (current or Decimal(1)) * 100; seen = True
        elif t in SCALES:
            total += (current or Decimal(1)) * SCALES[t]; current = Decimal(0); seen = True
        elif t in FRACTIONS:
            frac = FRACTIONS[t]
        elif t in ("and", "a"):
            continue
        else:
            return None
    if not seen and frac is None:
        return None
    v = total + current
    if frac is not None:
        v += frac
    return v


# "two-sided", "one-tailed", "three-fold": adjectives, not figures the
# assertion commits to. Digit forms ("2-sided") still count; a document that
# says "2-sided" contains the 2 either way.
_ADJECTIVE_TAIL = re.compile(r"[\s\-]+(sided|tailed|fold|way|arm|thirds|fifths)\b", re.I)


def _words(text: str) -> set[str]:
    out = set()
    for m in _WORDS.finditer(text):
        if _ADJECTIVE_TAIL.match(text, m.end()):
            continue
        # "23 million": the scale word belongs to the digits before it
        # (_digit_scales); alone it is not a figure of one million.
        if re.match(r"(hundred|thousand|million|billion)\b", m.group(0), re.I) and re.search(r"\d\s*$", text[:m.start()]):
            continue
        toks = [t for t in re.split(r"[\s\-]+", m.group(0)) if t]
        toks = [t for t in toks if t.lower() not in ("per", "cent", "percent")]
        if not toks:
            continue
        v = _words_value(toks)
        if v is not None:
            out.add(_canon(v))
    return out


_DIGIT_SCALE = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*(hundred|thousand|million|billion)\b", re.I)


def _digit_scales(text: str) -> set[str]:
    """'23 million' -> 23000000; '1.2 billion' -> 1200000000. The digits alone
    are still emitted by _digits (a document that says '23 million' contains 23)."""
    out = set()
    for m in _DIGIT_SCALE.finditer(text):
        try:
            out.add(_canon(Decimal(re.sub(_SEP, "", m.group(1))) * SCALES[m.group(2).lower()]))
        except InvalidOperation:
            pass
    return out


def canonical_numbers(text: str) -> set[str]:
    """Every number in `text`, digits or words, as canonical strings."""
    text = text or ""
    return _digits(text) | _words(text) | _digit_scales(text)


def figures(assertion: str) -> set[str]:
    """The numbers an assertion commits to. Same extraction; named for intent."""
    return canonical_numbers(assertion)


# ---------------------------------------------------------------------------
# FIGURES AT STATED PRECISION (added 2026-09-14). "23 million" against a
# document that says 23,480,668 is not a false claim; it is the same figure
# at the precision the sentence chose. 26% of the claims withheld on the first
# mmr freeze were of this shape. So a figure carries the precision it was
# stated at, and a qualifier if it had one, and binds when a document figure
# ROUNDS to it (or clears it, for "over" / "under"):
#   "23 million"       vs 23,480,668  -> binds    (rounds to 23 at the million)
#   "24 million"       vs 23,480,668  -> refuses
#   "over 20 million"  vs 23,480,668  -> binds    (floor cleared)
#   "650,000"          vs 657,461     -> refuses  (rounds to 660,000 at the 10,000)
#   "0.93"             vs 0.926       -> binds
#   "12 children"      vs 13          -> refuses  (an unqualified integer is exact)
# Deterministic; no model.
# ---------------------------------------------------------------------------
_QUAL_FLOOR = {"over", "more than", "at least", "exceeding", "exceeds", "above", "greater than", "in excess of", "upwards of"}
_QUAL_CEIL = {"under", "fewer than", "less than", "below", "at most", "up to", "no more than"}
_QUAL_ABOUT = {"about", "approximately", "roughly", "nearly", "almost", "around", "some", "an estimated", "estimated", "~", "circa"}
_QUALS = sorted(_QUAL_FLOOR | _QUAL_CEIL | _QUAL_ABOUT, key=len, reverse=True)
_FIG = re.compile(
    r"(?P<q>(?:" + "|".join(re.escape(q) for q in _QUALS) + r")\s+)?"
    r"(?P<num>(?<![\w.])[−\-]?(?:\d{1,3}(?:" + _SEP + r"\d{3})+|\d+)(?:[.·]\d+)?)"
    r"(?:\s*(?P<scale>hundred|thousand|million|billion)\b)?"
    r"(?P<pct>\s*(?:%|per\s?cent|percent))?", re.I)


def _precision_of(numtxt: str, scale: str | None) -> Decimal:
    """The unit the figure was stated in: 10^-decimals; the scale word; or, for a
    large round integer, its trailing zeros (650,000 -> 10,000). An unqualified
    small integer is exact."""
    s = re.sub(_SEP, "", numtxt).replace("·", ".").replace("−", "-").lstrip("-")
    if scale:
        base = Decimal(SCALES[scale.lower()])
        if "." in s:
            return base / (Decimal(10) ** len(s.split(".")[1]))
        return base
    if "." in s:
        return Decimal(1) / (Decimal(10) ** len(s.split(".")[1]))
    stripped = s.rstrip("0")
    zeros = len(s) - len(stripped)
    if zeros >= 2 and Decimal(s) >= 10_000:
        return Decimal(10) ** zeros
    return Decimal(1)


def stated_figures(text: str) -> list[dict]:
    """Every digit-form figure in an assertion with its value, stated precision and
    qualifier. Word-form figures ('thirty days') keep exact matching via figures()."""
    out = []
    for m in _FIG.finditer(text or ""):
        raw = m.group("num")
        if _ADJECTIVE_TAIL.match(text, m.end("num")):
            continue
        try:
            v = Decimal(re.sub(_SEP, "", raw).replace("·", ".").replace("−", "-"))
        except InvalidOperation:
            continue
        scale = m.group("scale")
        if scale:
            v = v * SCALES[scale.lower()]
        q = (m.group("q") or "").strip().lower()
        kind = "floor" if q in _QUAL_FLOOR else "ceiling" if q in _QUAL_CEIL else "about" if q in _QUAL_ABOUT else "exact"
        out.append({"value": v, "precision": _precision_of(raw, scale), "qualifier": kind, "text": m.group(0).strip()})
    return out


def figure_matches(stated: dict, doc_values: set[str]) -> str | None:
    """The document value that satisfies a stated figure, or None."""
    v, p, q = stated["value"], stated["precision"], stated["qualifier"]
    canon_v = _canon(v)
    if canon_v in doc_values:
        return canon_v
    for dv in doc_values:
        try:
            d = Decimal(dv)
        except InvalidOperation:
            continue
        if q == "floor" and d >= v and d < v * 10:
            return dv
        if q == "ceiling" and d <= v and d > v / 10:
            return dv
        if p != 1 or q == "about":
            unit = p if p != 1 else Decimal(1)
            if (d / unit).quantize(Decimal(1), rounding="ROUND_HALF_UP") * unit == v:
                return dv
    return None
