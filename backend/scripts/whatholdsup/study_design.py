"""What Holds Up: the study-design characteriser.

WHY THIS EXISTS
---------------
DESIGN is one of the six fatal claim classes and, until now, one of three that
fatal_recall.py scored as MISSING rather than MISSED -- "no
design-characterisation check exists", written in its own source.

The failure it is built for already happened. From source_ledger.py:

    the page called MONALEESA-2's final overall-survival p-value "two-sided" in
    five places. Nobody had opened the paper's statistical section; the
    characterisation was produced by a model reasoning about what such a paper
    probably says, and three separate gate runs agreed with it, because a
    checker drawn from the same distribution as the writer re-derives the
    writer's guess and reads like corroboration.

That last sentence is the whole argument for this file having no model in it.
Asking a second model whether a trial was double-blind gets you the same guess
back, wearing the clothes of a check. Asking the registry gets you the answer.

WHAT MAKES THIS CLASS TRACTABLE
-------------------------------
Design facts are registered. ClinicalTrials.gov publishes, for every
interventional trial, its masking, allocation, phase, study type and
intervention model as structured fields. So:

    KEYNOTE-942  NCT03897881   masking NONE       -- it is OPEN-LABEL
    MONALEESA-2  NCT01958021   masking QUADRUPLE
    PALOMA-3     NCT01942135   masking TRIPLE, allocation RANDOMIZED, PHASE3

A page calling KEYNOTE-942 "the double-blind Phase 2b trial" is contradicted by
a field, not by an opinion. That is the kind of finding that does not drift,
does not need re-measuring, and cannot be argued with.

WHAT IT BLOCKS ON
-----------------
Direct contradiction only. A check that fires on defensible wording gets
switched off, and today's work has already produced two of those -- an identity
test that scored five correct trials as wrong documents, and a quotation
extractor that read CSS font stacks. Being right matters more than being
thorough, because a check nobody trusts protects nothing.

So: open-label against a masked trial, blinded against an unmasked one,
randomised against a non-randomised one, the wrong phase, interventional
described as observational, crossover against parallel. Everything else is
recorded and passes.

A characterisation of a trial with no NCT cannot be settled this way, and is
not waved through either: it must carry an attestation in the issue's
design.json naming what was read. An unverified design claim is not a verified
one -- the source ledger's rule, one level down again.
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

UA = {"User-Agent": "civicscale-design-check"}

# Each entry: the words a page uses, the registry field, and the values that
# CONTRADICT them. Absence of contradiction is not confirmation; it is silence,
# and silence passes.
MASKING_ORDER = ("NONE", "SINGLE", "DOUBLE", "TRIPLE", "QUADRUPLE")

CLAIMS = [
    # (label, regex over the page, checker name)
    ("open-label",      r"\bopen[-\s]?label\b",                       "masking_none"),
    ("blinded",         r"\b(double|triple|quadruple)[-\s]?blind(ed)?\b", "masking_blinded"),
    ("single-blind",    r"\bsingle[-\s]?blind(ed)?\b",                "masking_single"),
    ("randomised",      r"\brandomi[sz]ed\b",                          "randomised"),
    ("non-randomised",  r"\b(non[-\s]?randomi[sz]ed|single[-\s]?arm)\b", "not_randomised"),
    ("observational",   r"\b(observational|retrospective)\b",          "observational"),
    ("crossover",       r"\bcross[-\s]?over\b",                        "crossover"),
    ("phase",           r"\bphase\s?([1-4]|I{1,3}|IV)\s?([ab])?\b",    "phase"),
]

# A design word characterises a trial only inside the SAME SENTENCE as the
# trial's name.
#
# The first version used a 260-character window either side, on the reasoning
# that "In the double-blind Phase 2b trial," often refers back to a trial named
# in a previous clause. Tested against two sentences -- one about KEYNOTE-942
# and one about PALOMA-3 -- it reported PALOMA-3 as described "double-blind"
# and "Phase 2b", having reached backwards into the KEYNOTE-942 sentence and
# collected its words. It caught the real error and invented a second one
# beside it.
#
# A false positive here is worse than a missed characterisation: this check's
# whole value is that a registry contradiction cannot be argued with, and one
# invented contradiction destroys that. Sentence scope gives up cross-sentence
# references and keeps the property that when it fires, it is right.
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\u201c\"])")


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


def path(slug: str) -> Path:
    return case_dir(slug) / "design.json"


def load(slug: str) -> dict | None:
    p = path(slug)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def trials_for(slug: str) -> dict:
    """Trial name -> NCT id, from design.json and from sources.json."""
    out = {}
    d = load(slug) or {}
    for name, nct in (d.get("trials") or {}).items():
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
            if not m:
                continue
            # The trial's short name, when the title carries one: "PALOMA-3: ..."
            t = s.get("title") or ""
            nm = re.match(r"([A-Za-z][A-Za-z0-9]*[-\s]?\d+[a-z]?)\s*[:—-]", t)
            if nm:
                out.setdefault(nm.group(1).strip(), m.group(1).upper())
    return out


def registry(nct: str) -> dict | None:
    url = ("https://clinicaltrials.gov/api/v2/studies/" + urllib.parse.quote(nct)
           + "?fields=protocolSection.designModule")
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25).read()
        return json.loads(raw)["protocolSection"]["designModule"]
    except Exception:
        return None


def contradiction(check: str, dm: dict, matched: str) -> str | None:
    """The registry's own words, when they contradict ours. Else None."""
    di = dm.get("designInfo") or {}
    masking = ((di.get("maskingInfo") or {}).get("masking") or "").upper()
    alloc = (di.get("allocation") or "").upper()
    model = (di.get("interventionModel") or "").upper()
    stype = (dm.get("studyType") or "").upper()
    phases = [p.upper() for p in (dm.get("phases") or [])]

    if check == "masking_none" and masking and masking != "NONE":
        return f"the registry records masking {masking}, not open-label"
    if check == "masking_blinded" and masking in ("NONE", "SINGLE"):
        return f"the registry records masking {masking or 'unspecified'}, not blinded"
    if check == "masking_single" and masking and masking != "SINGLE":
        return f"the registry records masking {masking}"
    if check == "randomised" and alloc and alloc.startswith("NON"):
        return f"the registry records allocation {alloc}"
    if check == "not_randomised" and alloc == "RANDOMIZED":
        return "the registry records allocation RANDOMIZED"
    if check == "observational" and stype == "INTERVENTIONAL":
        return "the registry records an INTERVENTIONAL study"
    if check == "crossover" and model and model != "CROSSOVER":
        return f"the registry records intervention model {model}"
    if check == "phase" and phases:
        m = re.search(r"phase\s?([1-4]|I{1,3}|IV)", matched, re.I)
        if not m:
            return None
        roman = {"I": "1", "II": "2", "III": "3", "IV": "4"}
        n = roman.get(m.group(1).upper(), m.group(1))
        # PHASE1|PHASE2 covers a "phase 1/2"; 2b is inside PHASE2.
        if not any(p == f"PHASE{n}" for p in phases):
            return f"the registry records {'/'.join(phases)}"
    return None


def blocks(page_text: str) -> list[str]:
    """The page's block-level text units: paragraphs, list items, headings."""
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", page_text, flags=re.I | re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    parts = re.split(r"</(?:p|li|h[1-6]|td|div|blockquote|figcaption)\s*>", t, flags=re.I)
    out = []
    for part in parts:
        txt = norm(html.unescape(re.sub(r"<[^>]+>", " ", part)))
        if txt:
            out.append(txt)
    return out


def findings(slug: str, page_text: str) -> list[dict]:
    """Every design characterisation on the page, tied to a trial.

    SCOPE IS THE THING THIS CHECK GETS RIGHT OR WRONG.

    A 260-character window either side of a trial name reached into the
    neighbouring sentence and reported PALOMA-3 as "double-blind" by collecting
    words written about KEYNOTE-942 -- a real error found, and a second one
    invented beside it.

    Sentence scope fixed that and covered almost nothing: on issue two the
    trials are named 14 to 21 times each and the design vocabulary lives in
    different sentences entirely, so it tied zero claims to zero trials and
    reported the page clean.

    What actually made the window unsafe was AMBIGUITY, not distance. So the
    rule is: inside a block that names exactly ONE trial, a design word
    characterises that trial, however many sentences away it sits. In a block
    naming two or more, fall back to the sentence, because there the reader
    cannot tell either.
    """
    trials = sorted(trials_for(slug).items(), key=lambda x: -len(x[0]))
    out = []
    for block in blocks(page_text):
        named = [(n, i) for n, i in trials if re.search(re.escape(n), block, re.I)]
        # Distinct trials, not distinct spellings: MONARCH 2 and MONARCH-2 are
        # one trial and must not make the block look ambiguous.
        distinct = {i for _n, i in named}
        scopes = [(block, named)] if len(distinct) == 1 else [
            (sent, [(n, i) for n, i in trials if re.search(re.escape(n), sent, re.I)])
            for sent in _SENT.split(block)]
        for scope, present in scopes:
            for name, nct in present:
                for label, pat, check in CLAIMS:
                    hit = re.search(pat, scope, re.I)
                    if not hit:
                        continue
                    out.append({"trial": name, "nct": nct, "label": label, "check": check,
                                "matched": hit.group(0), "context": norm(scope)[:220]})
    # One row per (trial, label) — the same characterisation repeated is one
    # claim, not five. MONALEESA-2's p-value was wrong in five places and that
    # was one error.
    seen, uniq = set(), []
    for f in out:
        k = (f["trial"], f["label"])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


def loose_characterisations(page_text: str) -> list[str]:
    """Sentences that characterise a study design, whether or not we can tell
    WHICH study.

    Two uses, and they measure different things. In the gate this is the
    residual gap: a design word the check could not attach to a trial is a
    claim nobody verified, and saying so is better than silence. In
    fatal_recall.py it is the control's INPUT -- the same standard applied to
    COUNTEREXAMPLE and QUOTATION, where surfacing the sentence is scored
    separately from settling it, because a defect that never reaches a control
    is not a defect the control missed.
    """
    text = plain(page_text)
    out = []
    for sent in _SENT.split(text):
        for _label, pat, _check in CLAIMS:
            if re.search(pat, sent, re.I):
                out.append(norm(sent))
                break
    return out


def preflight_rows(slug: str, page_text: str, online: bool = True) -> list[tuple[str, str, str]]:
    fs = findings(slug, page_text)

    # The untied ones are computed FIRST and reported on every path. The early
    # return used to skip them, so a page whose design language named no
    # recognisable trial -- the worst case, where nothing could be verified --
    # reported "no design claim on the page" and read as clean. A check that
    # goes quiet exactly when its coverage is zero is worse than no check.
    tied = {norm(f["context"]) for f in fs}
    loose = [c for c in loose_characterisations(page_text) if c not in tied]
    loose_row = [("design claims tied to no trial", WARN,
                  "%d sentence(s) characterise a study design without naming a trial this "
                  "check can identify, so nothing verified them: %s"
                  % (len(loose), " || ".join(c[:90] for c in loose[:2])))] if loose else []

    if not fs:
        return [("study-design characterisations", OK,
                 "no design claim on the page is tied to a trial we can identify")] + loose_row

    d = load(slug) or {}
    attested = {(a.get("trial"), a.get("label")): a
                for a in (d.get("attested") or []) if isinstance(a, dict)}

    rows = [("study-design characterisations", OK,
             "%d characterisation(s) across %d trial(s)"
             % (len(fs), len({f["trial"] for f in fs})))]

    if not online:
        return rows + loose_row

    wrong, unchecked = [], []
    for f in fs:
        dm = registry(f["nct"])
        if dm is None:
            a = attested.get((f["trial"], f["label"]))
            if not a or not str(a.get("basis", "")).strip():
                unchecked.append("%s %s — %s did not resolve and nothing records what was read"
                                 % (f["trial"], f["label"], f["nct"]))
            continue
        c = contradiction(f["check"], dm, f["matched"])
        if c:
            wrong.append("%s is described as %s; %s (%s)"
                         % (f["trial"], f["label"], c, f["nct"]))

    rows.append(("design claims match the registry",
                 OK if not wrong else BAD,
                 "every design characterisation agrees with the trial registry"
                 if not wrong else
                 "%d contradicted by the registry: %s"
                 % (len(wrong), " || ".join(wrong[:3]))))
    if unchecked:
        rows.append(("design claims nobody could check", BAD,
                     "%d: %s" % (len(unchecked), " || ".join(unchecked[:2]))))

    # The residual gap, stated rather than hidden. It does not block -- much of
    # it is ordinary prose about study types in general -- but a check that
    # reports only what it can settle gives a false picture of its own coverage.
    return rows + loose_row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", required=True)
    ap.add_argument("--offline", action="store_true", help="extract only; no registry calls")
    args = ap.parse_args()
    page = ROOT / args.page
    if not page.exists():
        sys.exit(f"no such page: {page}")
    bad = 0
    for name, state, detail in preflight_rows(args.slug, page.read_text(encoding="utf-8"),
                                              online=not args.offline):
        print(f"  {state:8s} {name}\n           {detail}")
        bad += state == BAD
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
