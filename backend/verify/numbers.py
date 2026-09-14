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
_DIGIT = re.compile(r"(?<![\w.])[−\-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:[.·]\d+)?(?![\w])")
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
        s = raw.replace(",", "").replace("·", ".").replace("−", "-")
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
        toks = [t for t in re.split(r"[\s\-]+", m.group(0)) if t]
        toks = [t for t in toks if t.lower() not in ("per", "cent", "percent")]
        if not toks:
            continue
        v = _words_value(toks)
        if v is not None:
            out.add(_canon(v))
    return out


def canonical_numbers(text: str) -> set[str]:
    """Every number in `text`, digits or words, as canonical strings."""
    text = text or ""
    return _digits(text) | _words(text)


def figures(assertion: str) -> set[str]:
    """The numbers an assertion commits to. Same extraction; named for intent."""
    return canonical_numbers(assertion)
