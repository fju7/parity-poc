#!/usr/bin/env python3
"""Check 5b, a mechanical figure check (validity plan §5b): "mechanical figure check, figure claims only; not a human
review". $0, no model in the loop.

    figure_check.py classify          every round-1 M1 item with a figure -> FIGURE_ABSENT / FIGURE_NEAR / AMBIGUOUS
                                      (reads sentences and held source text only, never a judge label)

Written, with backend/tests/test_whu_validity_figure_check.py, before any judge label was read for this check.

FIGURES (figures()): numbers in the drawn sentence, with or without a unit or %, after normalisation: Unicode minus
and dashes to "-", thousands separators removed ("1,234", "1 234", "1.234.567"), a decimal comma read as a point
("0,5"), "12 %" / "12 per cent" / "12 percent" the number 12, a range "1.2–3.4" or "1.2 to 3.4" two figures.
NOT FIGURES: citation markers ("[3]", "[3, 4]", "[3–5]", "[^1_2]") and the numbers inside them; years (a four-digit
whole number 1900-2099 with no decimal point, %, separator or sign, and not part of a range with a non-year).

SOURCE NUMBERS (numbers_in()): the same normaliser over the held text, plus number words zero-twenty and the tens.

CLASSES, for one item, over every cited source's held text joined:
  FIGURE_ABSENT   no claimed figure equals any source number, and none matches one by rounding or a %-conversion
  FIGURE_NEAR     every claimed figure equals a source number at some position where at least two distinct content
                  words of the sentence occur within WINDOW (300) characters on either side
  AMBIGUOUS       anything else: some figures found and some not; found but never near two content words; or matched
                  only by rounding (a source number that rounds to the claim at the claim's decimals) or a
                  %-conversion (x100 or /100)
CONTENT WORDS (content_words()): the sentence's words of three or more letters, lower-cased, minus STOPWORDS, number
words and citation markers; matched in the source as whole words, a trailing "s" ignored on both sides (words over
four letters). KNOWN LIMITS: derived figures (a difference, a ratio, a sum) look absent; a figure the source gives
only in a table that pdftotext scattered may look absent or not near; a number word above twenty is not read.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
WINDOW = 300
RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "quarterly" / "round1" / "m1"
OUT = HERE / "results" / "check5b_classes.json"
CLASSES = ("FIGURE_ABSENT", "FIGURE_NEAR", "AMBIGUOUS")

STOPWORDS = set("""
a about above across after again against all almost along also although always among an and another any are around
as at be because been before being below between both but by can could did do does done down during each either
else even ever every few for from further had has have having he her here hers him his how however i if in into is
it its itself just least less like made make many may might more most much must my near nearly neither no nor not
now of off often on once one only or other others our out over own per perhaps quite rather same she should since
so some such than that the their them then there these they this those though through thus to too under until up
upon us very was we were what when where whether which while who whom whose why will with within without would yet
you your
study studies review reviews trial trials evidence found finds showed shows reported reports report data analysis
participants people patients result results effect effects compared group groups among around approximately about
percent per cent percentage times year years number numbers total
""".split())
NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
                "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
                "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
                "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100}

CITATION = re.compile(r"\[\^?\d+(?:_\d+)?(?:\s*[,–—-]\s*\^?\d+(?:_\d+)?)*\]")
DASHES = str.maketrans({"−": "-", "–": "–", "—": "–", "‒": "–", " ": " ", " ": " ", "\xa0": " "})
# a number: optional sign, digits with optional thousands groups (comma, point or thin space), optional decimal part
NUM = re.compile(r"(?<![\w.,])(-)?(\d{1,3}(?:[,. ]\d{3})+|\d+)(?:([.,])(\d+))?(?![\w])")
RANGE_JOIN = re.compile(r"^\s*(?:–|-|to)\s*$")


def _value(sign: str | None, whole: str, sep: str | None, frac: str | None) -> tuple[float, int, bool]:
    """(value, decimals, had_grouping) from NUM's groups; a grouping separator is a ',', '.' or ' ' every 3 digits."""
    grouped = bool(re.search(r"[,. ]", whole))
    if grouped:
        seps = set(re.findall(r"[,. ]", whole))
        if len(seps) == 1 and sep and sep in seps:          # "1,234,5" style: not a number we can read
            return float("nan"), 0, True
        whole = re.sub(r"[,. ]", "", whole)
    dec = 0
    v = float(whole)
    if frac is not None:
        if sep == "," and len(frac) == 3 and not grouped:    # "1,234": a thousands separator, not a decimal comma
            v = float(whole + frac)
        else:
            v = float(whole + "." + frac)
            dec = len(frac)
    return (-v if sign else v), dec, grouped


def _numbers(text: str, years_out: bool) -> list[dict]:
    t = CITATION.sub(lambda m: " " * len(m.group(0)), text.translate(DASHES))
    out = []
    for m in NUM.finditer(t):
        sign, whole, sep, frac = m.group(1), m.group(2), m.group(3), m.group(4)
        # a sign directly after a digit is a range dash ("1-3"), not a minus
        if sign and m.start() > 0 and t[m.start() - 1].isdigit():
            sign = None
        v, dec, grouped = _value(sign, whole, sep, frac)
        if math.isnan(v):
            continue
        after = t[m.end():m.end() + 12].lower()
        pct = bool(re.match(r"\s*(%|per\s*cent|percent)", after))
        year = (years_out and frac is None and not grouped and not sign and not pct and len(whole) == 4
                and 1900 <= int(whole) <= 2099)
        out.append({"value": v, "decimals": dec, "pct": pct, "at": m.start(), "end": m.end(), "year": year})
    return out


def figures(sentence: str) -> list[dict]:
    """The sentence's figures: numbers that are not citation numbers or years."""
    nums = _numbers(sentence, years_out=True)
    t = sentence.translate(DASHES)
    # a year joined to a non-year by a range dash ("1999–2.5") is not a year; a year-year range stays years
    for a, b in zip(nums, nums[1:]):
        if RANGE_JOIN.match(t[a["end"]:b["at"]]) and a["year"] != b["year"]:
            a["year"] = b["year"] = False
    return [n for n in nums if not n["year"]]


def numbers_in(text: str) -> list[dict]:
    nums = _numbers(text, years_out=False)
    for m in re.finditer(r"\b(%s)\b" % "|".join(NUMBER_WORDS), text, re.I):
        nums.append({"value": float(NUMBER_WORDS[m.group(1).lower()]), "decimals": 0, "pct": False,
                     "at": m.start(), "end": m.end(), "year": False})
    return nums


def _stem(w: str) -> str:
    return w[:-1] if len(w) > 4 and w.endswith("s") else w


def content_words(sentence: str) -> set[str]:
    t = CITATION.sub(" ", sentence)
    return {_stem(w) for w in re.findall(r"[a-z][a-z'-]{2,}", t.lower())
            if w not in STOPWORDS and w not in NUMBER_WORDS and _stem(w) not in STOPWORDS}


def _words_at(text_lower: str, lo: int, hi: int) -> set[str]:
    return {_stem(w) for w in re.findall(r"[a-z][a-z'-]{2,}", text_lower[max(0, lo):hi])}


def _rounds_to(y: float, x: dict) -> bool:
    return round(y, x["decimals"]) == x["value"]


def classify(sentence: str, source_text: str) -> dict:
    figs = figures(sentence)
    if not figs:
        return {"class": None, "why": "no figure"}
    src = numbers_in(source_text)
    low = source_text.lower()
    words = content_words(sentence)
    found, near, loose = [], [], []
    for f in figs:
        exact = [n for n in src if n["value"] == f["value"]]
        found.append(bool(exact))
        near.append(any(len(words & _words_at(low, n["at"] - WINDOW, n["end"] + WINDOW)) >= 2 for n in exact))
        loose.append(not exact and any(_rounds_to(n["value"], f) or n["value"] * 100 == f["value"]
                                       or n["value"] / 100 == f["value"] for n in src))
    detail = {"figures": [f["value"] for f in figs], "found": found, "near": near, "loose": loose,
              "content_words": len(words)}
    if not any(found) and not any(loose):
        return {"class": "FIGURE_ABSENT", **detail}
    if all(found) and all(near):
        return {"class": "FIGURE_NEAR", **detail}
    return {"class": "AMBIGUOUS", **detail}


def run() -> int:
    """Classify every round-1 M1 item with a figure. Reads items, uncited items, the source manifest and held texts;
    no reply folder is opened."""
    items = json.loads((RUN / "items.json").read_text())
    unc = json.loads((RUN / "uncited.json").read_text())
    km = json.loads((RUN / "key_map.json").read_text())
    man = {m["url"]: m for m in json.loads((RUN / "sources" / "manifest.json").read_text())}
    out = {}
    for it in items:
        if not figures(it["claim"]):
            continue
        texts, missing = [], []
        for c in it["citations"]:
            m = man.get(c.get("url") or "")
            if m and m["extent"] != "unreachable":
                texts.append((RUN / "sources" / (m["source_id"] + ".txt")).read_text(encoding="utf-8"))
            else:
                missing.append(c.get("label"))
        k = km[it["item"]]
        row = {"question": k["question"], "system": k["system"]}
        if not texts:
            out[it["item"]] = {**row, "class": None, "why": "no cited source held"}
            continue
        r = classify(it["claim"], "\n\n".join(texts))
        out[it["item"]] = {**row, **r, "some_source_not_held": bool(missing)}
    for it in unc:
        if figures(it["claim"]):
            k = km[it["item"]]
            out[it["item"]] = {"question": k["question"], "system": k["system"], "class": None, "why": "uncited"}
    tally = Counter((v["system"], v["class"] or v["why"]) for v in out.values())
    res = {"label": "mechanical figure check, figure claims only; not a human review",
           "rules": "next_phase/figure_check.py docstring", "window_chars": WINDOW,
           "counts": {"%s/%s" % k: n for k, n in sorted(tally.items())}, "items": out}
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(run() if sys.argv[1:2] == ["classify"] else (print(__doc__) or 2))
