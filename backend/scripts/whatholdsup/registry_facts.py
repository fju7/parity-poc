"""What Holds Up: check a trial's STATUS, DATES and ENROLMENT against the registry.

WHY THIS EXISTS
---------------
registry_figures.py settles hazard ratios, confidence bounds and p-values. It
sees decimals and nothing else. So a page can state four things about a trial
and have exactly one of them checkable:

    "HARMONIA (NCT05207709) is a phase III, randomised, open-label trial;
     it opened in March 2022 and terminated with 61 patients enrolled."

    phase III, randomised, open-label   <- study_design.py checks these
    opened in March 2022                <- NOTHING CHECKED THIS
    terminated                          <- NOTHING CHECKED THIS
    61 patients enrolled                <- NOTHING CHECKED THIS

The 2026-08-31 re-gate reported all three as NOT_FOUND:

    HARMONIA opened on 28 March 2022.
      "The date 28 March 2022 does not appear in any source I could reach."
    HARMONIA terminated with 61 patients enrolled.
      "No source I could reach confirms that HARMONIA was terminated or that
       61 patients were enrolled at termination."
    PALMARES-2's record (NCT06805812) shows it is still recruiting toward an
    estimated 3,500 patients.
      "The live ClinicalTrials.gov record for NCT06805812 was not returned by
       any search result."

Every one of them is a structured field, returned by the API in under a second:

    NCT05207709  overallStatus TERMINATED
                 startDate     2022-03-28  (ACTUAL)
                 enrollment    61          (ACTUAL)
    NCT06805812  overallStatus RECRUITING
                 enrollment    3500        (ESTIMATED)

This is the same lesson as registry_figures, one field-type over: the SOURCE
role searches the web, the web does not reach the registry's structured record,
and "I could not look" comes back dressed as "it is not there". A model saying
NOT_FOUND about a field that an API posts is not a finding, it is a gap in
retrieval, and the fix is retrieval and not a better prompt.

CONFIRMATION ONLY. THIS CHECK NEVER CONTRADICTS.
------------------------------------------------
Three checkers written this week had to be narrowed after over-reaching, and
one of them -- the 260-character design window -- invented a finding. So this
one is deliberately built to be incapable of that class of error.

It says a claim is CONFIRMED when the registry posts that exact value for that
field, and says NOTHING otherwise. It never says a claim is wrong. The reason
is not timidity, it is that contradiction here is genuinely unsafe: a page
saying "58 patients per arm" against a registry enrolment of 116 is right, and
a checker that reads a per-arm number as a total would report a false error on
a true sentence. Confirming is sound; contradicting would need to understand
the sentence, and understanding the sentence is the thing we are trying not to
delegate to a model.

The purpose is to overturn NOT_FOUND, and overturning NOT_FOUND needs only
confirmation.

SCOPE
-----
The trial must be unambiguous, by the rule the other two checkers arrived at
the hard way: a claim is attributed to a trial only inside a text scope naming
exactly ONE registry number. Two scopes are read, both requiring that:

    - the whole block, when the block is short (a source entry);
    - the sentence carrying the NCT, in any block.

The second is new here and is what makes the check reach body prose: on this
page the HARMONIA facts sit in a 1,400-character paragraph that the block rule
skips, but they are in the same sentence as the NCT.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "issues"
OK, BAD, WARN = "ok", "BLOCKED", "warn"

MAX_BLOCK = 700
UA = {"User-Agent": "civicscale-registry-check"}
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(“\"])")

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def norm(t: str) -> str:
    return " ".join(t.split())


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob(f"WHU-*-{slug}"))
    if not hits:
        raise SystemExit(f"no case directory for {slug!r}")
    return hits[0]


# ---------------------------------------------------------------------------
# the registry side
# ---------------------------------------------------------------------------

_CACHE: dict = {}


def record(nct: str) -> dict | None:
    """The protocol section. Cached; one call per trial per run."""
    if nct in _CACHE:
        return _CACHE[nct]
    url = ("https://clinicaltrials.gov/api/v2/studies/" + urllib.parse.quote(nct)
           + "?fields=protocolSection.statusModule,protocolSection.designModule")
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers=UA), timeout=30).read()
        out = json.loads(raw)["protocolSection"]
    except Exception:
        out = None
    _CACHE[nct] = out
    return out


def posted_facts(nct: str) -> dict:
    """{field: value} the registry posts, in the forms this file compares."""
    p = record(nct)
    if not p:
        return {}
    st = p.get("statusModule") or {}
    dm = p.get("designModule") or {}
    out = {}
    if st.get("overallStatus"):
        out["status"] = st["overallStatus"].upper()
    for key, field in (("startDateStruct", "start_date"),
                       ("completionDateStruct", "completion_date"),
                       ("primaryCompletionDateStruct", "primary_completion_date")):
        d = (st.get(key) or {}).get("date")
        if d:
            out[field] = d
            out[field + "_type"] = ((st.get(key) or {}).get("type") or "").upper()
    ei = dm.get("enrollmentInfo") or {}
    if ei.get("count") is not None:
        out["enrolment"] = int(ei["count"])
        out["enrolment_type"] = (ei.get("type") or "").upper()
    return out


# ---------------------------------------------------------------------------
# the page side
# ---------------------------------------------------------------------------

# A status word only counts when the page is describing the trial's state, so
# each pattern carries its own context. "completed" alone is far too common a
# word in prose about medicine to read as a registry status.
STATUS = [
    (r"\bterminated\b", "TERMINATED"),
    (r"\bwithdrawn\b", "WITHDRAWN"),
    (r"\bsuspended\b", "SUSPENDED"),
    (r"\b(?:still |now )?recruiting\b(?!\s+(?:was|is)\b)", "RECRUITING"),
    (r"\bnot yet recruiting\b", "NOT_YET_RECRUITING"),
    (r"\bactive,? not recruiting\b", "ACTIVE_NOT_RECRUITING"),
    (r"\benrolling by invitation\b", "ENROLLING_BY_INVITATION"),
]

# "opened in March 2022", "opened on 28 March 2022", "began in March 2022".
OPENED = re.compile(
    r"\b(?:opened|began|started|commenced|first enrolled)\b[^.;]{0,40}?"
    r"(?:on|in)?\s*"
    r"(?:(\d{1,2})\s+)?(" + "|".join(MONTHS) + r")\s+(\d{4})", re.I)

CLOSED = re.compile(
    r"\b(?:completed|closed|terminated|ended|stopped)\b[^.;]{0,40}?"
    r"(?:on|in)\s*"
    r"(?:(\d{1,2})\s+)?(" + "|".join(MONTHS) + r")\s+(\d{4})", re.I)

# A count next to "patients" or "participants", in an enrolment context.
ENROL = re.compile(
    r"(?:\b(?:enrolled|enrolment|enrollment|randomised|randomized|recruited|"
    r"recruiting toward|toward)\b[^.;]{0,40}?)?"
    r"\b([\d][\d,]{1,6})\s+(?:patients|participants|women|people)\b"
    r"(?:[^.;]{0,30}?\b(?:enrolled|were enrolled|randomised|randomized|recruited)\b)?",
    re.I)


def _iso(day: str | None, month: str, year: str) -> str:
    mm = "%02d" % (MONTHS.index(month.lower()) + 1)
    return "%s-%s-%02d" % (year, mm, int(day)) if day else "%s-%s" % (year, mm)


def date_agrees(page: str, posted: str) -> bool:
    """A page date agrees with a registry date when it is no more specific and
    matches as far as it goes. "March 2022" agrees with 2022-03-28;
    "28 March 2022" agrees with 2022-03-28 but not with 2022-03-26."""
    if not page or not posted:
        return False
    return posted.startswith(page) if len(page) <= len(posted) else False


def blocks(page_text: str) -> list[str]:
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", page_text, flags=re.I | re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    parts = re.split(r"</(?:p|li|h[1-6]|td|div|blockquote|figcaption|section)\s*>",
                     t, flags=re.I)
    return [norm(html.unescape(re.sub(r"<[^>]+>", " ", x))) for x in parts if norm(x)]


def scopes(page_text: str) -> list[str]:
    """Text units in which a trial may be unambiguous. See the module docstring."""
    out = []
    for block in blocks(page_text):
        if len(block) <= MAX_BLOCK:
            out.append(block)
        out.extend(s for s in _SENT.split(block) if "NCT" in s.upper())
    return out


def claims_in(text: str) -> list[tuple[str, object, str]]:
    """(field, value, the words matched) — every checkable assertion in `text`."""
    out = []
    for pat, val in STATUS:
        m = re.search(pat, text, re.I)
        if m:
            out.append(("status", val, m.group(0)))
    for rx, field in ((OPENED, "start_date"), (CLOSED, "completion_date")):
        for m in rx.finditer(text):
            out.append((field, _iso(m.group(1), m.group(2), m.group(3)), m.group(0)))
    for m in ENROL.finditer(text):
        raw = m.group(1)
        # A bare number beside "patients" is not an enrolment claim unless the
        # sentence says so. Without this, "1,982 patients" from a different
        # study in the same paragraph enters as an enrolment assertion.
        if not re.search(r"enroll?ed|enrol?ment|randomi[sz]ed|recruit", m.group(0), re.I):
            continue
        try:
            out.append(("enrolment", int(raw.replace(",", "")), m.group(0)))
        except ValueError:
            pass
    return out


def findings(slug: str, page_text: str) -> list[dict]:
    """Every trial fact on the page that the registry confirms.

    Silent about everything else, by construction — see the docstring.
    """
    out, seen = [], set()
    for scope in scopes(page_text):
        ncts = {n.upper() for n in re.findall(r"NCT\d{8}", scope, re.I)}
        if len(ncts) != 1:
            continue
        nct = ncts.pop()
        facts = posted_facts(nct)
        if not facts:
            continue
        for field, value, matched in claims_in(scope):
            posted = facts.get(field)
            if posted is None:
                continue
            if field.endswith("_date"):
                agrees = date_agrees(str(value), str(posted))
            else:
                agrees = value == posted
            if not agrees:
                continue                       # silent: never a contradiction
            key = (nct, field, str(value))
            if key in seen:
                continue
            seen.add(key)
            out.append({"nct": nct, "field": field, "value": value,
                        "posted": posted, "type": facts.get(field + "_type", ""),
                        "matched": matched, "scope": norm(scope)[:200]})
    return out


def confirmed_keys(slug: str, page_text: str) -> dict[str, set]:
    """{field: {what the REGISTRY posts}} for every fact it confirms.

    The registry's value, not the page's. The first version stored the page's,
    and then a gate finding quoting "opened on 28 March 2022" failed to overturn
    against a page that said only "March 2022" — even though 2022-03-28 is the
    posted date and the quote was exactly right. Storing the page's own wording
    makes the check able to confirm only the sentence it already read, which is
    not a check, it is an echo.
    """
    out: dict[str, set] = {}
    for f in findings(slug, page_text):
        out.setdefault(f["field"], set()).add(f["posted"])
    return out


def quote_fully_confirmed(quote: str, confirmed: dict[str, set]) -> bool:
    """True only when the quote makes at least one checkable assertion and the
    registry confirms EVERY one — the same all-not-any rule registry_figures
    applies to decimals, and for the same reason. A date agrees when it is no
    more specific than the posted one and matches as far as it goes."""
    cs = claims_in(quote or "")
    if not cs:
        return False
    for field, value, _m in cs:
        posted = confirmed.get(field) or set()
        if field.endswith("_date"):
            if not any(date_agrees(str(value), str(p)) for p in posted):
                return False
        elif value not in posted:
            return False
    return True


def preflight_rows(slug: str, page_text: str) -> list[tuple[str, str, str]]:
    try:
        fs = findings(slug, page_text)
    except Exception as exc:
        return [("registry facts", WARN,
                 "the check did not run: %s: %s" % (type(exc).__name__, exc))]
    if not fs:
        return [("registry facts", OK,
                 "no status, date or enrolment claim on the page is tied to a "
                 "single trial registry number")]
    return [("registry facts", OK,
             "%d trial fact(s) confirmed against ClinicalTrials.gov: %s"
             % (len(fs), " || ".join("%s %s=%s" % (f["nct"], f["field"], f["value"])
                                     for f in fs[:6])))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", required=True)
    args = ap.parse_args()
    text = Path(args.page).read_text(encoding="utf-8")
    fs = findings(args.slug, text)
    print()
    if not fs:
        print("  nothing on this page ties a status, date or enrolment claim to a "
              "single registry number.")
    for f in fs:
        print("  CONFIRMED  %s  %s = %s  (registry: %s %s)"
              % (f["nct"], f["field"], f["value"], f["posted"], f["type"]))
        print("             page: %s" % f["matched"])
    print()
    for name, state, detail in preflight_rows(args.slug, text):
        print("  %-8s %-30s %s" % (state, name, detail))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
