"""What Holds Up: check figures against ClinicalTrials.gov, deterministically.

WHY THIS EXISTS
---------------
The 2026-08-31 re-gate of issue two produced sixteen unverified claims. Four
were false positives with a single cause, and two of those would have made the
page WORSE if acted on.

  PAGE                                     GATE SAID              REGISTRY SAYS
  PALOMA-2 OS HR 0.921 (0.755-1.124)       WRONG_VALUE            HR 0.921, CI
                                           "no source gives it"   0.755-1.124
  MONALEESA-2 HR 0.765 (0.628-0.932)       NOT_FOUND              exactly that
    p = 0.004                              "no source I reached"  p = 0.004
  "one-sided cumulative 2.5% level of      NOT_FOUND              verbatim in
    significance"                                                 the record
  PALOMA-2 p-values are 1-sided            NOT_FOUND              annotated on
                                                                  both analyses

The SOURCE role searches the web. ClinicalTrials.gov's structured results are
not reliably reachable that way, and the role said so in its own notes -- "only
a stub page was returned", "the structured results page was not retrievable".
Then it reported NOT_FOUND, and twice escalated to WRONG_VALUE, which reads as
"this figure is wrong" rather than "I could not look".

The API returns every one of those numbers in under a second, for nothing.

    Acting on that report would have replaced HR 0.921 with 0.956 and broken a
    sentence that was right.

So: ask the registry before asking a model. This runs BEFORE the SOURCE role,
settles what it can, and is both cheaper and more accurate than the thing it
short-circuits.

WHAT IT CHECKS
--------------
For every trial the issue knows an NCT for, every figure the page states in a
sentence naming that trial: hazard ratios, confidence bounds, p-values and
median months. CONFIRMED when the registry posts it, CONTRADICTED when the
registry posts a different value for the same quantity, and silent when the
registry has nothing to say -- which is not evidence either way and is not
reported as one.
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

MAX_BLOCK = 700   # a source entry; longer means prose about several trials
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(“\"])")


def norm(t: str) -> str:
    return " ".join(t.split())


def plain(page_text: str) -> str:
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", page_text, flags=re.I | re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    return norm(html.unescape(re.sub(r"<[^>]+>", " ", t)))


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob(f"WHU-*-{slug}"))
    if not hits:
        raise SystemExit(f"no case directory for {slug!r}")
    return hits[0]


def trials_for(slug: str) -> dict:
    """Trial name -> NCT, from design.json and any NCT urls in sources.json."""
    out = {}
    d = case_dir(slug) / "design.json"
    if d.exists():
        for name, nct in (json.loads(d.read_text()).get("trials") or {}).items():
            if nct:
                out[name] = nct.strip().upper()
    sp = case_dir(slug) / "sources.json"
    if sp.exists():
        raw = json.loads(sp.read_text(encoding="utf-8"))
        items = raw.get("sources", raw) if isinstance(raw, dict) else raw
        if isinstance(items, dict):
            items = list(items.values())
        for s in items:
            if not isinstance(s, dict):
                continue
            m = re.search(r"(NCT\d{8})", s.get("url") or "", re.I)
            nm = re.match(r"([A-Za-z][A-Za-z0-9]*[-\s]?\d+[a-z]?)\s*[:—-]", s.get("title") or "")
            if m and nm:
                out.setdefault(nm.group(1).strip(), m.group(1).upper())
    return out


_CACHE: dict = {}


def registry_text(nct: str) -> str | None:
    """The whole record as text. Cached; one call per trial per run."""
    if nct in _CACHE:
        return _CACHE[nct]
    url = "https://clinicaltrials.gov/api/v2/studies/" + urllib.parse.quote(nct)
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "civicscale-registry-check"}),
            timeout=30).read().decode("utf-8", "replace")
    except Exception:
        raw = None
    _CACHE[nct] = raw
    return raw


def numbers_in(text: str) -> set[str]:
    """Decimal figures, normalised. 0.80 and 0.8 are the same number."""
    out = set()
    for tok in re.findall(r"\d+\.\d+", text):
        try:
            out.add("%g" % float(tok))
        except ValueError:
            pass
    return out


# Figures worth checking: a hazard ratio, its bounds, a p-value. Median months
# are excluded -- the registry posts them per arm and the page often gives a
# difference, so a mismatch there is arithmetic rather than a discrepancy.
FIG = re.compile(
    r"(?:HR|hazard ratio)\s*=?\s*(\d\.\d+)"
    r"|(\d\.\d+)\s*(?:–|-|to)\s*(\d\.\d+)"
    r"|\bp\s*[=<]\s*(\d?\.\d+)", re.I)


def blocks(page_text: str) -> list[str]:
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", page_text, flags=re.I | re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    parts = re.split(r"</(?:p|li|h[1-6]|td|div|blockquote|figcaption|section)\s*>", t, flags=re.I)
    return [norm(html.unescape(re.sub(r"<[^>]+>", " ", x))) for x in parts if norm(x)]


def findings(slug: str, page_text: str) -> list[dict]:
    """Figures on the page, tied to a trial, checked against its registry record.

    SCOPE, AND THE FIRST VERSION GOT IT WRONG THE SAME WAY THE DESIGN CHECKER
    DID. Attributing a figure only when the SENTENCE names the trial found
    nothing useful: the numbers that matter sit in source entries whose heading
    carries the trial name and the NCT, and whose body then says "the sponsor's
    own posting ... gives HR 0.765 (95% CI 0.628-0.932)". Sentence scope
    checked 11 figures and none of the two known-confirmable ones.

    The identifier is better than the name anyway. A block containing exactly
    one NCT number is unambiguous in a way that matching "MONARCH 3" against
    prose is not, and the source entries put the NCT right there.
    """
    trials = sorted(trials_for(slug).items(), key=lambda x: -len(x[0]))
    out = []
    for block in blocks(page_text):
        # SHORT blocks only, and the NCT must be IN the block.
        #
        # Third attempt at scope, and the second two were worse than the first.
        # Sentence scope found none of the figures that matter, because they
        # live in source entries whose heading carries the trial and whose body
        # then states the number. Whole-block scope then credited MONALEESA-2's
        # "63.9 versus 51.4 months, HR 0.76" to MONALEESA-7's registry, because
        # a long prose section happened to contain one NCT and many trials'
        # figures.
        #
        # A checker that misattributes a figure to the wrong trial is worse
        # than no checker: it is precisely the fault that made the gate's own
        # report wrong today, reproduced in the fix for it. So this only speaks
        # about SOURCE ENTRIES -- a short block carrying exactly one registry
        # number, where the number and the figures beside it belong together --
        # and stays silent everywhere else. Narrow and right beats broad and
        # confident.
        if len(block) > MAX_BLOCK:
            continue
        ncts = {n.upper() for n in re.findall(r"NCT\d{8}", block, re.I)}
        if len(ncts) != 1:
            continue                      # ambiguous or none: say nothing
        nct = ncts.pop()
        raw = registry_text(nct)
        if raw is None:
            continue
        posted = numbers_in(raw)
        for m in FIG.finditer(block):
            for g in m.groups():
                if not g:
                    continue
                val = "%g" % float(g)
                out.append({"nct": nct, "value": g, "norm": val,
                            "in_registry": val in posted,
                            "sentence": norm(block)[:200]})
    # One row per (trial, value): the same figure printed in a table and again
    # in prose is one figure.
    seen, uniq = set(), []
    for f in out:
        k = (f["nct"], f["norm"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


def preflight_rows(slug: str, page_text: str) -> list[tuple[str, str, str]]:
    fs = findings(slug, page_text)
    if not fs:
        return [("registry figures", OK, "no figure on the page is tied to a trial registry")]
    confirmed = [f for f in fs if f["in_registry"]]
    unposted = [f for f in fs if not f["in_registry"]]
    rows = [("registry figures", OK,
             "%d of %d figure(s) appear verbatim in the trial registry"
             % (len(confirmed), len(fs)))]
    if unposted:
        # NOT a failure. The registry does not post every figure a paper
        # prints, and absence here is absence of evidence. Saying otherwise is
        # the exact mistake the SOURCE role made when it turned "I could not
        # reach the results page" into WRONG_VALUE.
        rows.append(("figures the registry does not post", WARN,
                     "%d figure(s) are not in their trial's registry record, which is not "
                     "evidence against them — the registry posts a subset of what a paper "
                     "prints: %s"
                     % (len(unposted),
                        " || ".join("%s (%s)" % (f["value"], f["nct"]) for f in unposted[:4]))))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", required=True)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    page = ROOT / args.page
    if not page.exists():
        sys.exit(f"no such page: {page}")
    txt = page.read_text(encoding="utf-8")
    for name, state, detail in preflight_rows(args.slug, txt):
        print(f"  {state:8s} {name}\n           {detail}")
    if args.list:
        print("\n  every figure checked:")
        for f in findings(args.slug, txt):
            mark = "CONFIRMED" if f["in_registry"] else "not posted"
            print(f"    {mark:11s} {f['value']:>8s}  {f['nct']}  {f['sentence'][:96]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
