#!/usr/bin/env python3
"""
What Holds Up: publication control.

WHY THIS EXISTS
---------------
Until now the only way to know what had been published was to open the site and
read it. The pieces existed — a gate, a broadcast sender, a git remote that
Vercel watches — and nothing joined them or wrote down what happened. On
2026-08-27 the live melanoma page had been wrong for hours in a way that had
been fixed in the repo, and nothing anywhere said so.

This is the join. It answers three questions:

    what have we published, and is it still what we meant?   -> status
    is this issue safe to publish right now?                 -> check
    publish it, and write down that we did                   -> publish / announce
    a new study appeared and two paragraphs changed          -> update
    a nav link changed on a page nobody is republishing      -> record-live

THE PREFLIGHT IS THE POINT
--------------------------
Every check below exists because something got past its absence:

  gate report present, passed, and matching the file
      An email went to subscribers carrying none of the corrections made to the
      page that afternoon. require_gate in send_broadcast.py closed that for the
      send; this closes it for the site too.

  every figure in the email appears on the page
      "Met both of its endpoints" was right on the page and wrong in the email,
      because the email was written from the page and compressed it. Nothing
      compared the two. Recorded as ENDPOINT_ROLE_CONFLATED, caught_by: nothing.

  html and text versions carry the same figures
      They have already drifted once in a single editing pass.

  no orphaned adjudications
      A decision whose sentence no longer exists is dead weight, and its absence
      means a finding that reads as settled is not.

  the live page matches the repo
      The failure this file was written after.

Usage:
    cd backend && source venv/bin/activate

    python scripts/whatholdsup/publish.py status
    python scripts/whatholdsup/publish.py check melanoma
    python scripts/whatholdsup/publish.py publish melanoma          # site
    python scripts/whatholdsup/publish.py announce melanoma         # email
    python scripts/whatholdsup/publish.py log

Nothing irreversible happens without --yes.
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import os
import importlib.util
import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # repo root
GATE = ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py"
RECORD = ROOT / "backend" / "data" / "whatholdsup" / "published.json"
REVIEWS = ROOT / "backend" / "data" / "whatholdsup" / "reviews.json"
CASES = ROOT / "issues"
REGISTER = ROOT / "issue-register.csv"

_spec = importlib.util.spec_from_file_location("factcheck_draft", GATE)
fc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fc)


def _sibling(name):
    """Load a module that lives beside this one.

    These four were written after the 29 August corrections, each because
    something in that round got past the checks that existed:

      source_ledger       six adverse claims about a guideline nobody in the
                          pipeline was permitted to read
      lint_claims         a universal quantifier and a stale count, both
                          syntax, both passed by eighteen model runs
      source_advocate     no role had ever been asked what the source would
                          say back
      premise             the piece's premise was fitted to what we had found,
                          and nothing checks a premise -- checks run against one
      corrections_intake  the site promised a 48-hour acknowledgement in writing
                          and nothing anywhere kept a clock
    """
    path = Path(__file__).resolve().parent / (name + ".py")
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


ledger = _sibling("source_ledger")
lint = _sibling("lint_claims")
advocate = _sibling("source_advocate")
premise = _sibling("premise")
intake = _sibling("corrections_intake")

# Added 2026-08-29 after a second post-publication review found two randomised
# head-to-head trials behind a sentence the piece printed four times.
#
#   counterexample     the lint had already listed "no randomised trial has
#                      compared any of the three" as an unbounded universal.
#                      That list was a checklist nobody had to act on, which is
#                      documentation and not a control. This makes it an input:
#                      one adversarial call per universal negative, registries
#                      required. Run against the published page it broke all
#                      four in a single call.
#   inherited_claims   verifying that a source SAYS X is not verifying X. NCCN's
#                      sentence was true and scoped to one setting; ours was
#                      unscoped and false, and every step in between was done
#                      correctly.
counterexample = _sibling("counterexample")
watch = _sibling("watch")
inherited = _sibling("inherited_claims")

# Added 2026-08-31. QUOTATION was one of three fatal classes that fatal_recall.py
# scored as MISSING rather than MISSED -- "no quotation matcher exists", written
# in its own source. Unlike the modules above, this one is not a response to an
# incident: the class is known, an altered quotation costs a reader all trust in
# every other sentence, and waiting for the failure before building the control
# is the habit being broken.
quotations = _sibling("quotations")

# Added 2026-08-31 with the quotation matcher, and for the failure named in
# source_ledger.py: the page called MONALEESA-2's final OS p-value "two-sided"
# in five places, nobody had opened the statistical section, and three gate
# runs agreed with the guess because a model checker re-derives the writer's
# guess and it reads like corroboration. Design facts are registered, so this
# one asks ClinicalTrials.gov instead of asking a model.
study_design = _sibling("study_design")

# Added 2026-08-31. The gate reports "<- differs" when the page is not the
# draft it judged, and then computes its state from the findings it has, which
# say nothing about text added since. Issue two's board read "state ok, every
# one of its 7 findings resolved" while the live page carried 28 sentences of
# figures, trial names and registry ids introduced by the 30 August correction
# -- the gate report does not contain the word Shaaban. Corrections are the
# least-checked text on a page and the likeliest place for a second error.
unjudged = _sibling("unjudged")
registry_figures = _sibling("registry_figures")

# Added 2026-08-31, an hour after registry_figures, because registry_figures
# only sees decimals. Three of the eight open findings on issue two were a
# trial's STATUS, its START DATE and its ENROLMENT -- all structured registry
# fields, all reported NOT_FOUND by a role that searches the web, and none of
# them reachable by a checker that looks for hazard ratios. Enumerating the
# claim classes is only half the work; the other half is noticing that a class
# you thought was covered is covered for one data type and silent for the rest.
registry_facts = _sibling("registry_facts")

# The document store. Added 2026-09-01, when the ledger for issue two read: 24
# sources, 3 opened by a person, 8 resting on nothing but "whatever the search
# tool returned for this URL". We had never acquired the sources -- every role
# did its own retrieval, took a fragment, and threw it away. This asks the only
# question that makes a sentence checkable a year from now: do we HOLD the
# document it was written from.
source_store = _sibling("source_store")

# B10 and B1 of the claim-bindings spec (docs/whatholdsup-claim-bindings-spec.md).
#
# errata: an erratum is the ONE class of secondary document that can silently
# falsify a figure already published, and it is free to look for. Two were found
# by hand on 2026-09-01 in metadata nobody had read -- one nine months old, one
# seven years -- and a third turned up on the LIVE issue-three page within
# minutes of this running for the first time.
#
# bindings: which words in which document support each sentence. Reports how
# much of the page rests on nothing this system can name. It reports presence
# and absence and never truth.
errata = _sibling("errata")
bindings = _sibling("bindings")
# B9 starts from the PAGE rather than the source list, which is the only way to
# see a source nobody wrote down. B8 asks whether a closer document says the
# same thing.
page_ledger = _sibling("reconcile")
# What each check did NOT examine, as a number beside what it found. Built after
# the substance test was found not to be running on eighteen of the nineteen
# documents held for a live issue, and saying so in no way at all.
coverage = _sibling("coverage")
# Whether the span checks can read each held document at all. A figure taken out
# of a document must be findable in it written the way the page writes it. Built
# after B2 said "not there" three times about a figure held since morning,
# because The Lancet writes its decimals with a middle dot.
canary = _sibling("canary")
# B13: does this figure appear in ANY document we hold? The one check that does
# not need a binding, a citation or a judgement -- and the one that would have
# stopped three figures reaching a live page, written between two and six days
# before the paper that settles them was held. See b13.preflight_rows.
b13 = _sibling("b13")
# B14: what a correction TOOK OUT. Every other check asks whether a claim on the
# page is supported; none asked whether a REMOVAL was, and 35% of the recorded
# errors on issue two came in with an earlier correction. See deletions.py.
deletions = _sibling("deletions")
# B15: a finding is settled by a DOCUMENT, never by the finding. Closes MEL-11 --
# a correction notice that asserted more than the check which prompted it, on a
# live page. See findings.py.
findings = _sibling("findings")

# The spend ledger. Fourteen of the fifteen scripts in this repo that make
# priced model calls record nothing about what they cost, and the one that does
# writes it into a report the next run overwrites -- which is why "what has this
# issue cost" had no answer, and why an agreed cap of "two gate runs" could be
# renegotiated twice without anyone seeing the running total. A cap you cannot
# measure against is an intention.
def _load_spend():
    """Load spend_ledger by PATH, never by adding backend/scripts to sys.path.

    backend/scripts/signal/ is a package literally named `signal`. Putting
    backend/scripts on sys.path makes it importable as top-level `signal` and
    it shadows the standard library -- so anyio's `from signal import Signals`
    resolves to our package and every import of anthropic dies. That is what
    the first wiring of this ledger did, and it broke the gate outright:

        ImportError: cannot import name 'Signals' from 'signal'
        (backend/scripts/signal/__init__.py)

    The rest of this repo loads siblings with spec_from_file_location for
    exactly this reason. So does this.
    """
    import importlib.util
    p = Path(__file__).resolve().parents[1] / "spend_ledger.py"
    if not p.exists():
        return None
    try:
        sp = importlib.util.spec_from_file_location("spend_ledger", p)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        return m
    except Exception:
        return None


spend = _load_spend()

# The registry lives in code rather than in the served directory: a JSON file
# under site/ is deployed and fetchable, and this names files, not content.
ISSUES = {
    "melanoma": {
        "number": 1,
        "title": "The Melanoma Result",
        "page": "site/whatholdsup/melanoma.html",
        "url": "https://whatholdsup.org/melanoma",
        "email_html": "site/whatholdsup/email/issue1-melanoma.html",
        "email_txt": "site/whatholdsup/email/issue1-melanoma.txt",
        "audience": "bae12ea6-cbad-4b91-b250-81991bf6b4b5",
        "email_subject": "The Melanoma Result — a Phase 3 success with no numbers",
    },
    "deskilling": {
        "number": 3,
        "title": "What Happens to the Experts First",
        # NOT under site/ until it publishes. On 2026-08-30 this file sat at
        # site/whatholdsup/deskilling.html for six commits, and every push put an
        # ungated, unreviewed draft on the public web under a masthead reading
        # "Published 30 August 2026". The pre-push guard did not catch it: the
        # guard compares a published page against its publication record, and a
        # page that has never been published has no record to differ from. It
        # protected the two live issues and was blind to a third appearing.
        # Moved under site/ on 2026-08-30, at publication and not before. The
        # note above is why: for six commits this file sat here unpublished and
        # every push served an ungated draft under a masthead that said it was
        # published. Promotion is the last step, taken once the preflight is
        # clean, and it is deliberately manual.
        "page": "site/whatholdsup/deskilling.html",
        "url": "https://whatholdsup.org/deskilling",
        "email_html": "site/whatholdsup/email/issue3-deskilling.html",
        "email_txt": "site/whatholdsup/email/issue3-deskilling.txt",
        "audience": "bae12ea6-cbad-4b91-b250-81991bf6b4b5",
        "email_subject": "What Happens to the Experts First \u2014 what AI does to people who are already good at something",
    },
    "cdk46": {
        "number": 2,
        "title": "The Category Difference",
        "page": "site/whatholdsup/cdk46.html",
        "url": "https://whatholdsup.org/cdk46",
        "email_html": "site/whatholdsup/email/issue2-cdk46.html",
        "email_txt": "site/whatholdsup/email/issue2-cdk46.txt",
        "audience": "bae12ea6-cbad-4b91-b250-81991bf6b4b5",
        "email_subject": "The Category Difference \u2014 what separates a category 1 from a category 2A",
    },
}

SENDER = ROOT / "site" / "whatholdsup" / "email" / "send_broadcast.py"

NUM = re.compile(r"\d+\.\d+|\d+(?:,\d{3})+|\d+%|\bn=\d+\b")
OK, BAD, WARN = "ok", "BLOCKED", "warn"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def figures(text: str) -> set[str]:
    return set(NUM.findall(text))


# ---------------------------------------------------------------------------
# gate analysis
#
# A gate verdict means nothing on its own. It is a statement about one exact
# version of one file, made by an instrument with recorded defects. Reading
# `passed` alone gets it wrong in both directions: it blocks a draft whose
# findings were fixed an hour ago, and it clears a draft that changed after the
# run. On 2026-08-28 the board sent us back to re-run a gate on five findings
# that had already been fixed, and the report it was reading had never been
# opened past its `passed` flag. Two of the seven claim verdicts underneath it
# were live errors nobody had seen.
#
# So this reads four things and keeps them apart:
#
#   what the run found        objections, inferences AND claim verdicts, which
#                             are where fact errors actually live
#   whether it still applies  the report's sha against the file's sha now
#   whether it still bites    is each finding's quote still in the text
#   whether it is the tool    findings matching a recorded instrument defect
#
# Nothing here can turn a failed run on the CURRENT text into a pass. The most
# it can do is say that a stale run's findings are all gone from the text, and
# that is a question put to a human, not a default. Answering it is `accept-gate`,
# which writes the answer down.
# ---------------------------------------------------------------------------

RECORDS_ONLY = {"CALIBRATION"}          # recorded and published, never blocks

# Which role owns each part of a report, so a finding can be looked up in the
# decisions file. This mapping is the whole reason the board can stop asking
# about things already settled: draft_decisions.json is keyed on (role, quote),
# and until now nothing on the board consulted it. Sixteen recorded judgments
# about this one page sat there while the board demanded they be made again.
ROLE_OF = {"objections": "ADVOCATE", "inferences": "INFERENCE", "verdict": "SOURCE"}


def decided_by_figure(f: dict, decisions: dict) -> dict | None:
    """Match a SOURCE verdict to a recorded decision on figure, not wording.

    A claim quote is the extractor's paraphrase of a sentence, not the sentence.
    It is rewritten on every run, so a decision keyed on last run's phrasing
    reads as NEW this run, and a judgment made once has to be made again. This
    is the same reason carry_verdicts keys on (figure, attributed_to), and the
    same key is used here.

    Both the figure and, when the claim names one, the source have to appear in
    the recorded quote. A figure alone is too weak: "19 August" appears in four
    unrelated sentences on this page.
    """
    fig = fc._norm(f.get("figure") or "")
    if len(fig) < 5:
        return None
    src = fc._norm(f.get("source") or "")
    for (role, quote), dec in decisions.items():
        if role != "SOURCE" or fig not in quote:
            continue
        if src and len(src) >= 5 and src not in quote:
            continue
        return dec
    return None
VERDICT_OK = {"VERIFIED", "INTERNAL"}   # INTERNAL = the piece citing itself

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_SUBS = {"–": "-", "—": "-", "−": "-", "‘": "'",
         "’": "'", "“": '"', "”": '"', " ": " "}
_MISSING = ("not appear", "could not be", "cannot be found", "not be located",
            "no entity called", "not found", "could not find", "unreachable",
            "does not exist")


def flatten(s: str) -> str:
    """Draft text and gate quotes reduced to something comparable.

    `&ndash;` on a page and an en dash in a quote are the same character to a
    reader and different bytes to `in`. An earlier version of this comparison
    missed exactly that and retired a decision that was still live.
    """
    s = _html.unescape(s or "")
    s = _TAG.sub(" ", s)
    for a, b in _SUBS.items():
        s = s.replace(a, b)
    return _WS.sub(" ", s).strip().casefold()


def slug_for(target: Path) -> str | None:
    rel = str(target.relative_to(ROOT)) if str(target).startswith(str(ROOT)) else str(target)
    for slug, cfg in ISSUES.items():
        if rel in (cfg.get("page"), cfg.get("email_html")):
            return slug
    return None


def coverage_sources(r: dict) -> list[tuple[str, str]]:
    """(outlet, url) pairs the COVERAGE role reported in this same run."""
    out = []
    for c in ((r.get("coverage") or {}).get("best_coverage") or []):
        if isinstance(c, dict):
            name = (c.get("outlet") or c.get("name") or "").strip()
            url = (c.get("url") or "").strip()
            if name and url:
                out.append((name, url))
    return out


def gate_findings(r: dict) -> list[dict]:
    """Every blocking-capable thing the run produced, in one shape.

    Objections and inferences carry a class. Claim verdicts do not — they are
    the SOURCE role's per-figure result, and NOT_FOUND or WRONG_VALUE there is
    a fact finding whatever the objections say. Leaving them out is how a run
    with three wrong figures reads as four phrasing notes.
    """
    out = []
    for section, prob, pfx in (("objections", "why", "o"), ("inferences", "problem", "i")):
        n = 0
        for f in (r.get(section) or []):
            if not isinstance(f, dict):
                continue
            n += 1
            cls = (f.get("class") or "").strip().upper() or "UNCLASSIFIED"
            out.append({
                "id": "%s%d" % (pfx, n), "kind": section, "class": cls,
                "severity": (f.get("severity") or "").upper(),
                "quote": f.get("quote") or "",
                "figure": "", "why": f.get(prob) or f.get("objection") or "",
                "fix": f.get("fix") or "",
                # unclassified fails closed: an unlabelled finding is not a
                # calibration note until somebody says it is.
                "blocking": cls not in RECORDS_ONLY,
            })
    claims = {c.get("id"): c for c in (r.get("claims") or []) if isinstance(c, dict)}
    for cid, v in (r.get("verdicts") or {}).items():
        if not isinstance(v, dict):
            continue
        verdict = (v.get("verdict") or "").upper()
        if verdict in VERDICT_OK:
            continue
        c = claims.get(cid, {})
        out.append({
            "id": cid, "kind": "verdict", "class": verdict,
            "severity": "SERIOUS" if verdict == "WRONG_VALUE" else "",
            "quote": c.get("claim") or "",
            "figure": c.get("figure") or "",
            "source": c.get("attributed_to") or "",
            "why": v.get("note") or "",
            "fix": v.get("found_value") or "",
            "blocking": True,
        })
    return out


def still_in_text(f: dict, body: str) -> str:
    """present / partial / gone / unknown — and unknown never reads as gone.

    Claim text is a paraphrase: the extractor rewrites the sentence, so a
    containment test on it fails on drafts that never changed. Figures do not
    get paraphrased, which is why carry-forward keys on them, and why this does.
    """
    fig = [x.strip() for x in re.split(r"[,;]", f.get("figure") or "") if x.strip()]
    if fig:
        hit = [x for x in fig if flatten(x) in body]
        if len(hit) == len(fig):
            return "figure"
        return "partial" if hit else "gone"
    q = flatten(f.get("quote") or "")
    if not q:
        return "unknown"
    if q in body:
        return "present"
    if len(q) > 90 and (q[:80] in body or q[-80:] in body):
        return "partial"
    if f["kind"] == "verdict":
        return "unknown"        # a paraphrase that does not match proves nothing
    return "gone"


# What each answer means in words, because "still in the text" said of a
# paraphrase we could not find is a claim we have not earned.
WHERE = {
    "present": "still in the text",
    "figure":  "its figures are still in the text",
    "partial": "partly still in the text",
    "unknown": "could not be located — the claim is the extractor's paraphrase, "
               "so absence of a match proves nothing either way",
    "gone":    "no longer in the text",
}


def instrument_flags(f: dict, sources: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Recorded defects this finding looks like. A flag, never a dismissal.

    Both patterns below cost us real time before they were named, and both are
    invisible from inside a single role: they are contradictions between roles,
    or between a role and the calendar.
    """
    flags = []
    blob = flatten(" ".join(str(f.get(k) or "") for k in ("why", "quote", "fix")))
    if any(m in blob for m in _MISSING):
        for name, url in sources:
            n = flatten(name)
            if len(n) >= 6 and n in blob:
                flags.append(("SOURCE_FALSE_NEGATIVE",
                              "COVERAGE cites %s with a URL in this same run: %s" % (name, url)))
                break
    if f["class"] == "NOT_FOUND" and any(w in blob for w in (
            "internal editorial", "internal disclosure", "publication's own",
            "not verifiable against any external", "cannot be verified against a primary",
            "cannot be verified against any external", "editorial claim")):
        flags.append(("INTERNAL_MISCLASSED_AS_NOT_FOUND",
                      "the role has an INTERNAL verdict for claims about ourselves and "
                      "returned NOT_FOUND instead; absence of an external source is the "
                      "expected result, not a finding"))
    if f["class"] in ("WRONG_VALUE", "FACT"):
        phrase = any(w in blob for w in ("primary analysis", "three-year", "3-year",
                                         "interim", "earlier readout", "first readout"))
        years = [int(y) for y in re.findall(r"\b(20[12]\d)\b", blob)]
        stale = years and min(years) <= datetime.now().year - 2
        if phrase or stale:
            flags.append(("WRONG_READOUT_COMPARISON",
                          "the figures it offers are sourced to %s — check it describes the "
                          "same data cut before believing it"
                          % ("an earlier readout" if phrase else str(min(years)))))
    return flags


def acceptance_file(slug: str | None) -> Path | None:
    case = case_dir(slug) if slug else None
    return (case / "gate-acceptances.json") if case else None


def acceptance_for(slug: str | None, target: Path, digest: str) -> dict | None:
    """A recorded human decision to proceed on a stale gate, bound to this sha.

    Bound, so it dies the moment the file changes again. An acceptance that
    outlived its content would be worse than no acceptance at all: it would
    read as a check.
    """
    fp = acceptance_file(slug)
    if not fp or not fp.exists():
        return None
    try:
        rows = json.loads(fp.read_text()).get("acceptances", [])
    except Exception:
        return None
    for a in reversed(rows):
        if a.get("file") == target.name and a.get("sha") == digest:
            return a
    return None


def registry_overturns(slug: str, target: Path) -> set[str]:
    """Numbers the trial registry confirms, so a model verdict cannot outrank it.

    THE REASON THIS IS CODE AND NOT A BETTER PROMPT.

    SOURCE_SYSTEM already forbids what happened on 2026-08-31, in its own
    words, having been taught by three earlier incidents:

        NOT_FOUND ... This is a statement about what you could reach, NOT
        about whether the thing exists.

        If you cannot establish that, the verdict is NOT_FOUND -- you could
        not reach the right source -- and not WRONG_VALUE.

    The role returned WRONG_VALUE on PALOMA-2's HR 0.921 (0.755-1.124),
    asserting that no source gives it. ClinicalTrials.gov posts it under
    "Overall Survival (OS): Final Analysis". The instruction was explicit, the
    reasoning behind it was in the prompt, and the role broke it anyway.

    A rule a model is told is not a control. So where a deterministic check and
    a model verdict disagree, the deterministic one wins and the disagreement is
    recorded. That is the whole architecture, applied to the one place it was
    still missing: the check that decides whether a figure is real.
    """
    try:
        confirmed = {f["norm"] for f in registry_figures.findings(
            slug, target.read_text(encoding="utf-8")) if f["in_registry"]}
    except Exception as exc:
        # NOT a silent return. The first version swallowed the exception and
        # returned an empty set, so the reconciliation reported "0 overturned"
        # and looked like a considered answer rather than a crash. A check that
        # fails quietly is indistinguishable from a check that found nothing,
        # which is the whole reason this file exists.
        print("  [WARN] registry reconciliation failed, so no model verdict was "
              "checked against the registry: %s: %s" % (type(exc).__name__, exc))
        return set()
    return confirmed


def registry_fact_overturns(slug: str, target: Path) -> dict:
    """Trial status, dates and enrolment the registry confirms.

    Same argument as registry_overturns one field-type over, and the same
    refusal to fail quietly: an exception here is printed, not swallowed, so
    "nothing overturned" can never be a crash wearing the clothes of a verdict.
    """
    try:
        return registry_facts.confirmed_keys(
            slug, target.read_text(encoding="utf-8"))
    except Exception as exc:
        print("  [WARN] registry fact reconciliation failed, so no model verdict "
              "about a trial's status, dates or enrolment was checked against the "
              "registry: %s: %s" % (type(exc).__name__, exc))
        return {}


def _figures_all_confirmed(figure: str, confirmed: set[str]) -> bool:
    """True only if EVERY number in the finding's figure is posted by the registry.

    Every one, not any: overturning "HR 0.921 (0.755-1.124)" because the
    registry happens to post 0.921 somewhere, while the interval is a different
    analysis, would be the same over-reach in the opposite direction.
    """
    nums = re.findall(r"\d+\.\d+", figure or "")
    if not nums:
        return False
    return all(("%g" % float(n)) in confirmed for n in nums)


def gate_state(target: Path, slug: str | None = None) -> dict:
    """Everything knowable about this file's gate without spending a run."""
    slug = slug or slug_for(target)
    rp = target.with_suffix(target.suffix + ".gate.json")
    d = {"report": rp, "target": target, "exists": rp.exists(), "fresh": False,
         "findings": [], "blocking": [], "outstanding": [], "resolved": [],
         "suspect": [], "unlocatable": [], "settled": [], "overturned": [],
         "calibration": 0, "accepted": None,
         "state": BAD, "detail": "", "notes": []}
    if not rp.exists():
        d["detail"] = "never gated — there is no %s" % rp.name
        return d
    try:
        r = json.loads(rp.read_text())
    except Exception as exc:
        d["detail"] = "%s is unreadable: %s" % (rp.name, exc)
        return d

    d["checked_at"] = r.get("checked_at", "?")
    d["recorded_sha"] = r.get("sha256") or ""
    d["current_sha"] = sha(target)
    d["fresh"] = d["recorded_sha"] == d["current_sha"]
    d["passed_flag"] = r.get("passed")

    body = flatten(target.read_text(encoding="utf-8"))
    sources = coverage_sources(r)
    confirmed_by_registry = registry_overturns(slug, target)
    facts_by_registry = registry_fact_overturns(slug, target)
    decisions = fc.load_decisions(fc.DECISIONS, target.name)
    for f in gate_findings(r):
        f["where"] = still_in_text(f, body)
        f["flags"] = instrument_flags(f, sources)
        # A decision on a SOURCE finding is keyed on the VERDICT -- NOT_FOUND,
        # WRONG_VALUE, WRONG_SOURCE -- because that is what factcheck_draft.py
        # passes to classify() when it writes one (see its line "classify(
        # 'SOURCE', c.get('claim'), v.get('verdict'), ...)"). gate_findings
        # translates the verdict into a severity WORD for display, and passing
        # that word here instead made every SOURCE decision come back STALE:
        # found by quote, rejected on a severity the recorder never wrote.
        # STALE blocks, so the effect was that adjudicating a source finding
        # made the board worse. Thirty-one decisions were silently unmatched
        # this way before anyone noticed. The key must be the same string on
        # both sides.
        # A verdict the registry refutes stops blocking, and says who overruled
        # it. Only SOURCE verdicts: the advocate and inference roles are not
        # making a claim about what a document contains.
        if (f["kind"] == "verdict" and f["class"] in ("WRONG_VALUE", "NOT_FOUND")
                and (_figures_all_confirmed(f.get("figure", ""), confirmed_by_registry)
                     or registry_facts.quote_fully_confirmed(
                         f.get("quote", ""), facts_by_registry))):
            f["blocking"] = False
            f["overturned"] = True
            d["overturned"].append(f)
            _by = ("figure" if _figures_all_confirmed(
                       f.get("figure", ""), confirmed_by_registry) else "fact")
            f["why"] = ("the trial registry posts every %s in this claim (%s); the role "
                        "reported %s having searched the web, which does not reach "
                        "ClinicalTrials.gov's structured results. Deterministic check wins. "
                        "Original note: %s"
                        % (_by,
                           "hazard ratios, bounds and p-values" if _by == "figure"
                           else "status, dates and enrolment",
                           f["class"], (f.get("why") or "")[:160]))

        _key = f["class"] if f["kind"] == "verdict" else f["severity"]
        f["decided"], dec, _how = fc.classify(ROLE_OF.get(f["kind"], ""), f["quote"],
                                              _key, decisions)
        if f["decided"] == "NEW" and f["kind"] == "verdict":
            byfig = decided_by_figure(f, decisions)
            if byfig:
                f["decided"], dec = "ADJUDICATED", byfig
        f["decision"] = (dec or {}).get("decision", "")
        f["reason"] = (dec or {}).get("reason", "")
        d["findings"].append(f)
        if not f["blocking"]:
            d["calibration"] += 1
            continue
        d["blocking"].append(f)
        if f["flags"]:
            d["suspect"].append(f)
        if f["where"] == "gone":
            d["resolved"].append(f)
        elif f["decided"] in ("ADJUDICATED", "OVERLAP"):
            # Read, judged, and written down with a reason. Asking again is not
            # rigour, it is the board failing to read its own record.
            d["settled"].append(f)
        else:
            d["outstanding"].append(f)
            if f["where"] == "unknown":
                d["unlocatable"].append(f)

    if d["overturned"]:
        d["notes"].append(
            "%d SOURCE verdict(s) overturned by ClinicalTrials.gov — the role reported a "
            "figure or a trial fact missing or wrong having searched the web, which does "
            "not reach the registry's structured results, and the registry posts every "
            "checkable part of the claim: %s. A deterministic check outranks a model "
            "verdict, and the disagreement is recorded rather than dropped."
            % (len(d["overturned"]), ", ".join(f["id"] for f in d["overturned"])))

    d["accepted"] = acceptance_for(slug, target, d["current_sha"])
    nb, no_, nr = len(d["blocking"]), len(d["outstanding"]), len(d["resolved"])
    ns = len(d["settled"])
    settled_note = (", %d already decided" % ns) if ns else ""
    kinds = ", ".join(sorted({f["class"] for f in d["outstanding"]})) or "none"

    if d["passed_flag"] is True and nb:
        d["notes"].append("the report says passed=True and carries %d blocking finding(s); "
                          "believe the findings" % nb)

    if d["fresh"]:
        if no_ == 0 and d["passed_flag"] is True:
            d["state"] = OK
            d["detail"] = "gated %s on this exact text, clean%s" % (
                d["checked_at"],
                " — %d calibration note(s)" % d["calibration"] if d["calibration"] else "")
        elif nb == 0:
            d["state"] = WARN
            d["detail"] = ("gated %s on this exact text; no blocking findings, but the run "
                           "recorded passed=%r" % (d["checked_at"], d["passed_flag"]))
        else:
            d["state"] = BAD
            d["detail"] = ("%d unresolved on this exact text%s — %s"
                           % (no_, settled_note, kinds))
        return d

    old = (d["recorded_sha"] or "?")[:8]

    # WHAT THE RECONCILIATION BELOW CANNOT SEE, and did not, for ten days.
    #
    # The reasoning underneath it is sound about the findings the run RAISED:
    # every one is gone from the text or decided on the record, so the check
    # was performed. It is silent about text the run never saw, because a
    # sentence written after the run generates no finding to reconcile, and no
    # finding reads as nothing wrong.
    #
    # Issue two: gated 28 August, then nine commits of edits. On 30 August the
    # commit "issue two said no head-to-head trial existed, and two do" added
    # the Shaaban trial and HARMONIA — 116 patients, 58.6% clinical benefit in
    # both arms, 13.67 against 12.69 months, NCT05207709. The report does not
    # contain the word Shaaban. The board said ok every time it was asked.
    #
    # An absence of findings about a sentence is not a verdict about it.
    d["unjudged"] = []
    if not d["fresh"]:
        try:
            # ANY blocking row, not just the one about new figures. The first
            # wiring filtered on the name "empirical sentences never judged"
            # and so dropped the other blocking case -- a comparison that could
            # not be made at all, because the judged draft recovered from git
            # was identical to the current page. Issue three hit exactly that
            # and kept reading "ok" while the filter looked past it. Narrowing
            # a check to the failure you have in mind is how the other one gets
            # through.
            for _n, _st, _detail in unjudged.preflight_rows(slug, target):
                if _st == BAD:
                    d["unjudged"].append(_detail)
        except Exception as exc:                       # never let this hide the board
            d["notes"].append("could not tell which sentences were judged: %s" % exc)

    if d["unjudged"]:
        d["state"] = BAD
        d["detail"] = ("gated %s on an earlier draft (%s) and the page has changed since: %s"
                       % (d["checked_at"], old, d["unjudged"][0]))
        return d

    # A run that judged an earlier draft, every finding of which is now either
    # gone from the text or decided on the record, is a check that has been
    # performed. Requiring a signature on it asks a person to attest to a
    # reconciliation only whoever made the edits could perform — the same defect
    # the outside-review step had, one row up, and it took being told twice.
    #
    # What a signature genuinely buys is a decision to proceed past something
    # still open. That case still stops, and it makes you name each one.
    if no_ == 0:
        d["state"] = OK
        if nb == 0:
            d["detail"] = ("gated %s on an earlier draft (%s); it raised nothing that "
                           "blocks%s" % (d["checked_at"], old, settled_note))
        else:
            d["detail"] = ("gated %s on an earlier draft (%s); every one of its %d "
                           "finding(s) is resolved — %d gone from the text, %d decided "
                           "in draft_decisions.json"
                           % (d["checked_at"], old, nb, nr, ns))
        if d["accepted"]:
            d["detail"] += " (also signed off %s by %s)" % (
                d["accepted"].get("at", "?")[:10], d["accepted"].get("by", "?"))
        return d

    nu = len(d["unlocatable"])
    d["state"] = BAD
    d["detail"] = ("gated %s on an earlier draft (%s); %d of %d open — %d still in the "
                   "text, %d unlocatable, %d gone%s"
                   % (d["checked_at"], old, no_, nb, no_ - nu, nu, nr, settled_note))
    if d["accepted"]:
        d["state"] = WARN
        d["detail"] += " — proceeding past them was signed off %s by %s" % (
            d["accepted"].get("at", "?")[:10], d["accepted"].get("by", "?"))
    return d


def gate_report(target: Path) -> tuple[str, str]:
    """(state, detail) — the two-value view the preflight and the board use."""
    d = gate_state(target)
    return d["state"], d["detail"]

MONTHS = ("January February March April May June July August September "
          "October November December").split()
DATELINE = re.compile(r"\b(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})\b")


def header_date(raw: str) -> str:
    """The date the article says it is, from its own masthead.

    The first date in the kicker row is the one a reader takes as "when this
    was written". Everything else on the page — an event date, a source's
    publication date — is about the world, not about us.
    """
    m = re.search(r'<span class="meta">(.*?)</span>', raw, re.S)
    if not m:
        return ""
    txt = _html.unescape(_TAG.sub(" ", m.group(1)))
    # "Published X - Updated Y": Y is the one that has to be today. A masthead
    # that keeps the original date is the point of the convention; what must not
    # go stale is the statement of when it last moved.
    up = re.search(r"Updated\s+(" + DATELINE.pattern + ")", txt)
    if up:
        return up.group(1)
    d = DATELINE.search(txt)
    return d.group(0) if d else ""


def as_of_date(raw: str) -> str:
    m = re.search(r"As of\s+([^<.]{4,40})", _html.unescape(_TAG.sub(" ", raw)))
    if not m:
        return ""
    d = DATELINE.search(m.group(1))
    return d.group(0) if d else ""


def pretty(d) -> str:
    return "%d %s %d" % (d.day, MONTHS[d.month - 1], d.year)


def corrections_text(slug: str) -> str:
    case = case_dir(slug)
    fp = (case / "corrections.md") if case else None
    return fp.read_text(encoding="utf-8") if fp and fp.exists() else ""


def live_body(url: str, timeout: int = 20) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "whatholdsup-publish"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def load_record() -> list[dict]:
    if not RECORD.exists():
        return []
    try:
        return json.loads(RECORD.read_text()).get("published", [])
    except Exception:
        return []


def append_record(entry: dict) -> None:
    rows = load_record()
    rows.append(entry)
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps({
        "what_this_is": "Every publication and every send, appended. This is the "
                        "answer to 'what have we published', and it is in the repo "
                        "so it is versioned and diffable rather than only true on "
                        "a server somewhere.",
        "published": rows,
    }, indent=2), encoding="utf-8")



JOBS = ROOT / "backend" / "data" / "jobs"
JOB_STALE_MINUTES = 20


def queued_jobs_rows() -> list[tuple[str, str, str]]:
    """Is the unattended runner actually running the work we handed it?

    WHY THIS EXISTS
    ---------------
    On 2026-08-31 two gate runs were queued for the launchd runner, whose
    StartInterval is 30 seconds. Ninety seconds later the queue was untouched
    and backend/data/jobs/logs/ was empty, so this function was written -- and
    its first version said, in the operator's face, "the runner has never
    executed anything".

    THAT WAS WRONG, and so was the correction. Nine minutes later a job was
    claimed and run, and this docstring was rewritten to say the runner "had
    been firing all along". It may not have been: the operator had just been
    given the command to run the queue by hand, and the timing fits that as
    well as it fits a launchd tick. Thirty minutes later a canary job sat
    unclaimed, which is not what a 30-second StartInterval looks like.

    So the honest state is: WE DO NOT KNOW WHETHER LAUNCHD HAS EVER FIRED THIS.
    What is established is narrower and still worth having -- logs/ holds one
    file PER CLAIMED JOB, so an empty logs/ means no job was ever claimed, and
    it does not distinguish an agent that never ran from an agent that never
    had work. Reading it as the first was the error: an absence observed by
    something that could not have seen the thing is not an absence. That is the
    same error as a retrieval that could not reach a page reporting the figure
    absent, written into a check built to catch it, an hour after writing it --
    and then a second time, in the fix, by asserting a cause the evidence did
    not carry.

    So the block below states the wait, which is a fact, and offers the two
    readings of an empty logs/ without choosing between them.

    The reason to keep the check is unchanged and is not about the runner. A
    job sitting in the queue forever looks exactly like a job about to start,
    and the board that blocks on "the gate has not read these sentences" will
    go on saying so while the run meant to read them sits unstarted on disk.
    An unstarted job is not a job in progress, and a board that cannot tell the
    difference is telling someone to wait for nothing.
    """
    q = JOBS / "queue"
    if not q.exists():
        return []
    jobs = sorted(q.glob("*.json"))
    if not jobs:
        return []
    now = time.time()
    oldest = min(f.stat().st_mtime for f in jobs)
    waited = int((now - oldest) / 60)
    log_dir = JOBS / "logs"
    ran_ever = any(log_dir.glob("*")) if log_dir.exists() else False
    names = ", ".join(f.stem for f in jobs[:4])
    if waited < JOB_STALE_MINUTES:
        return [("queued jobs", OK,
                 "%d job(s) waiting for the runner, oldest %d min: %s"
                 % (len(jobs), waited, names))]
    return [("queued jobs", BAD,
             "%d job(s) have been in the queue %d minutes and nothing has run them: %s. "
             "%s Check the runner: `launchctl list org.whatholdsup.jobrunner` on the Mac, "
             "and `bash backend/scripts/whatholdsup/schedule/runner.sh` runs the queue "
             "in the foreground. A job nobody started is not a job in progress, and a "
             "board that cannot tell the difference is telling you to wait for nothing."
             % (len(jobs), waited, names,
                "backend/data/jobs/logs/ holds no job log, which means no job has ever "
                "been CLAIMED -- either the runner has never run, or it has never had "
                "one to take. Those are different problems and this cannot tell them "
                "apart; runner.out and runner.err, if launchd wrote them, can."
                if not ran_ever else
                "The runner has claimed a job before, so it is not the install."))]


def outside_review(page: Path, slug: str) -> tuple[str, str]:
    """Has an independent reviewer read THIS version of the assessment?

    The gate is five roles that share an instrument and therefore share its
    blind spots — measured, not assumed: the recall fixture has a class no role
    finds. The outside review of issue one raised the direction-versus-magnitude
    defect that none of the six phases had, and that became rule 8. It is the
    only check that can find what the others are constitutionally unable to see,
    so it is a STOP and not a warning.

    A review is bound to the content hash it read. If the piece changed
    afterwards the review is not void — the changes were probably the ones it
    asked for — but a human has to say so, which is the point.
    """
    if not REVIEWS.exists():
        return BAD, "no outside review has ever been recorded"
    try:
        rows = json.loads(REVIEWS.read_text()).get("reviews", [])
    except Exception as exc:
        return BAD, f"reviews.json is unreadable: {exc}"
    mine = [r for r in rows if r.get("issue") == slug]
    if not mine:
        return BAD, f"no outside review recorded for {slug}"
    latest = mine[-1]
    if latest.get("sha") == sha(page):
        return OK, (f"reviewed {latest.get('at', '?')[:10]} by "
                    f"{latest.get('reviewer', 'unnamed')}, "
                    f"{latest.get('findings', '?')} finding(s), all adjudicated")
    # A review of an earlier draft is not a review of this one, and pretending
    # otherwise is the failure this function exists to prevent. But the changes
    # after a review are usually the ones it asked for, and re-running the whole
    # review to say so is not proportionate. So: a confirmation, bound to BOTH
    # hashes — the version reviewed and the version now — naming who looked at
    # the difference. It reads as a confirmation on the board, never as a review.
    try:
        confs = json.loads(REVIEWS.read_text()).get("confirmations", [])
    except Exception:
        confs = []
    now = sha(page)
    for c in reversed(confs):
        if (c.get("issue") == slug and c.get("reviewed_sha") == latest.get("sha")
                and c.get("now_sha") == now):
            return OK, (f"reviewed {latest.get('at', '?')[:10]} by "
                        f"{latest.get('reviewer', 'unnamed')}; changes since confirmed "
                        f"{c.get('at', '?')[:10]} by {c.get('by', '?')}")

    # No human is asked whether the changes match the adjudication. Only the
    # person who made them could answer that, and asking anyone else produces a
    # signature instead of a check. The reconciliation is the check: every
    # change traced to a recorded decision that resolves to something readable.
    ok, bad, _stale = reconcile(slug)
    if ok and not bad:
        cites = ", ".join(sorted({r.get("because", "?") for _k, _w, _n, r in ok}))
        return OK, (f"reviewed {latest.get('at', '?')[:10]} by "
                    f"{latest.get('reviewer', 'unnamed')}; {len(ok)} change(s) since, "
                    f"each traced to a recorded decision ({cites})")
    if bad:
        return BAD, (f"{len(bad)} change(s) since the review of "
                     f"{str(latest.get('sha'))[:8]} have no decision behind them")
    return WARN, (f"the last review read a different version "
                  f"({latest.get('at', '?')[:10]}, sha {str(latest.get('sha'))[:8]}), "
                  f"and no change to the prose was recorded")


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def fc_parity_provenance(page_text: str, email_text: str) -> list[str]:
    """Sourcing claims the email makes that the page does not.

    Figure parity would never have caught this: the figures matched exactly.
    What differed was the sentence saying what the figures ARE.
    """
    ep = _sibling("email_parity")
    return ep.provenance_parity(page_text, email_text)


# Rows an UPDATE to a living issue does not have to re-earn, and why.
#
# An update is judged on what it ADDS. Re-running the whole first-publication
# battery for a two-paragraph change is how a living issue stops being updated
# at all -- and an issue that is never updated while displaying a changelog is
# worse than one that never promised.
#
# The list is a whitelist, not a blacklist, and that is deliberate: anything
# NOT named here blocks an update, INCLUDING checks added after this list was
# written. A list of exemptions will be forgotten; a list of exemptions that
# fails closed is forgotten safely.
UPDATE_SOFTENS = {
    "page gate": "the fact-check gate was run on this piece; a change is judged "
                 "by the checks below, and a substantive rewrite should go "
                 "through `publish` instead",
    "email gate": "the email is not what is changing",
    "email figures on page": "the email is not what is changing",
    "email sourcing claims match the page": "the email is not what is changing",
    "html/text parity": "the email is not what is changing",
    "email adjudications": "the email is not what is changing",
    "outside review": "the piece was reviewed once; if THIS change needs "
                      "reviewing, that is a judgement, not a gate",
    "belief stated": "the premise is about how the piece was conceived, not "
                     "about what it now says",
    "belief shown to be held": "as above",
    "what the sources show": "as above",
    "direction recorded": "as above",
    "reader with a decision": "as above",
    "carried in general coverage?": "as above",
    "our contribution named": "as above",
    "kill condition written": "superseded for a living issue by the watch list",
    "kill condition tested": "superseded for a living issue by the watch list",
}


def preflight(slug: str, *, for_email: bool,
              for_update: bool = False) -> list[tuple[str, str, str]]:
    cfg = ISSUES[slug]
    page = ROOT / cfg["page"]
    ehtml = ROOT / cfg["email_html"]
    etxt = ROOT / cfg["email_txt"]
    out: list[tuple[str, str, str]] = []

    for label, f in (("page file", page), ("email html", ehtml), ("email text", etxt)):
        out.append((label, OK if f.exists() else BAD,
                    str(f.relative_to(ROOT)) if f.exists() else f"missing: {f}"))
    if not (page.exists() and ehtml.exists() and etxt.exists()):
        return out

    st, detail = gate_report(page)
    out.append(("page gate", st, detail))
    st, detail = gate_report(ehtml)
    out.append(("email gate", st, detail))

    ptext, etext, ttext = fc.read_draft(page), fc.read_draft(ehtml), etxt.read_text(encoding="utf-8")

    stray = figures(etext) - figures(ptext)
    out.append(("email figures on page", OK if not stray else BAD,
                "every figure in the email appears on the page" if not stray
                else f"in the email and not on the page: {', '.join(sorted(stray))}"))

    # B14 -- against what readers can actually see. A removal is only checkable
    # against the published version, so this row is silent when the live page
    # cannot be fetched, and says so rather than passing.
    try:
        _live_for_del = live_body(cfg["url"])
        if _live_for_del:
            out.extend(deletions.check(slug, _live_for_del,
                                       page.read_text(encoding="utf-8")))
        else:
            out.append(("figures a correction removed", WARN,
                        "the live page could not be fetched, so nothing here "
                        "knows what a correction took out"))
    except BaseException as exc:
        out.append(("figures a correction removed", WARN,
                    "did not run: %s: %s" % (type(exc).__name__, exc)))

    try:
        out.extend(findings.preflight_rows(
            slug, page.with_suffix(page.suffix + ".gate.json")))
    except BaseException as exc:
        out.append(("gate findings settled", WARN,
                    "did not run: %s: %s" % (type(exc).__name__, exc)))

    _pp = fc_parity_provenance(ptext, etext)
    out.append(("email sourcing claims match the page", OK if not _pp else BAD,
                "the email describes where its figures come from the way the page does"
                if not _pp else
                "%d sourcing claim(s) in the email that the page does not make. The "
                "email said every figure came from a trial publication or a drug "
                "label while quoting two observational studies: %s"
                % (len(_pp), " || ".join(x[:120] for x in _pp[:2]))))

    drift = figures(etext) ^ figures(ttext)
    out.append(("html/text parity", OK if not drift else BAD,
                "same figures in both" if not drift
                else f"differ: {', '.join(sorted(drift))}"))

    for label, f, text in (("page", page, ptext), ("email", ehtml, etext)):
        dec = fc.load_decisions(fc.DECISIONS, f.name)
        orph = fc.orphaned(dec, text)
        out.append((f"{label} adjudications", OK if not orph else WARN,
                    f"{len(dec)} decisions, none orphaned" if not orph
                    else f"{len(orph)} quote a sentence that is gone: "
                         + "; ".join(q[:44] for _r, q in orph)))

    st, detail = outside_review(page, slug)
    out.append(("outside review", st, detail))

    _cap = (spend.caps().get("per_issue") or {}).get(slug, spend.caps().get("default_per_issue"))
    _so_far = spend.spent(issue=slug)
    out.append(("spend on this issue",
                OK if not _cap or _so_far < 0.8 * float(_cap) else WARN,
                "$%.2f recorded%s. This is a floor: only factcheck_draft.py reports its "
                "cost DIRECTLY -- but every script that reaches the model now goes "
                "through factcheck_draft.call, which refuses to spend until a "
                "caller declares an issue, so advocate and counterexample runs "
                "land here too. Signal scripts still do not."
                % (_so_far, (" of a $%.0f cap" % float(_cap)) if _cap else "")))

    # The four checks added after the 29 August corrections. Order is
    # deliberate: the cheap deterministic ones first, so that a page failing on
    # a stale count is not first made to wait on a model call.
    # THE BODY, NOT THE CHANGE LOG, for the checks that read the page's claims.
    # counterexample was given the whole document and spent three of eight
    # attacks on our own correction entries. See source_ledger.body_only.
    _ptext = ledger.plain(ledger.body_only(page.read_text(encoding="utf-8")))
    out.extend(lint.lint(page.read_text(encoding="utf-8"), slug))
    out.extend(counterexample.preflight_rows(slug, _ptext))
    out.extend(inherited.preflight_rows(slug, _ptext))
    # Reads the page's own markup, not the flattened text: the extractor strips
    # tags itself and needs the quotation marks as the page sets them.
    out.extend(quotations.preflight_rows(slug, page.read_text(encoding="utf-8"), page))
    try:
        out.extend(study_design.preflight_rows(slug, page.read_text(encoding="utf-8")))
    except SystemExit as e:
        out.append(("study-design characterisations", BAD, str(e)))
    out.extend(unjudged.preflight_rows(slug, page))
    # Ask the registry before the SOURCE role does. On 2026-08-31 that role
    # reported four figures NOT_FOUND -- twice escalating to WRONG_VALUE --
    # because ClinicalTrials.gov's structured results are not reliably
    # reachable by web search. Its own notes said so: "only a stub page was
    # returned". The API returns them in under a second. Acting on that report
    # would have replaced a correct HR 0.921 with 0.956.
    try:
        out.extend(registry_figures.preflight_rows(slug, page.read_text(encoding="utf-8")))
        out.extend(registry_facts.preflight_rows(slug, page.read_text(encoding="utf-8")))
    except SystemExit as e:
        out.append(("registry figures", BAD, str(e)))
    try:
        _live = live_body(cfg["url"])
        out.extend(ledger.audit(
            slug, ledger.plain(page.read_text(encoding="utf-8")),
            ledger.plain(_live) if _live else None))
    except SystemExit as e:
        out.append(("source ledger", BAD, str(e)))
    # NOTHING RAN undefined_states. It was written after 44 undefined states
    # reached two live pages, it sits in the recall test scoring CAUGHT, and no
    # gate called it -- so on 2026-09-01 three sources were entered with the
    # state `not_held`, which is not a state, and nothing said so.
    try:
        out.extend(ledger.undefined_state_rows(slug, source_store.sources(slug)))
    except BaseException as exc:
        out.append(("access states are defined", WARN,
                    "did not run: %s: %s" % (type(exc).__name__, exc)))
    out.extend(advocate.preflight_rows(slug))
    out.extend(premise.preflight_rows(
        slug, already_published=any(r["issue"] == slug and r["action"] == "publish"
                                    for r in load_record())))
    out.extend(intake.preflight_rows(slug))
    out.extend(queued_jobs_rows())
    try:
        out.extend(source_store.preflight_rows(slug))
    except Exception as exc:
        out.append(("source store", WARN, "the store check did not run: %s: %s"
                    % (type(exc).__name__, exc)))
    try:
        out.extend(page_ledger.preflight_rows(
            slug, page.read_text(encoding="utf-8")))
    except BaseException as exc:
        out.append(("page to ledger", WARN, "did not run: %s: %s"
                    % (type(exc).__name__, exc)))
    for _mod, _name in ((errata, "errata check"), (bindings, "claim bindings"),
                        (coverage, "check coverage"),
                        (b13, "figures in held documents"),
                        (canary, "checks can read the documents")):
        try:
            out.extend(_mod.preflight_rows(slug))
        except BaseException as exc:   # SystemExit is not an Exception
            out.append((_name, WARN, "did not run: %s: %s"
                        % (type(exc).__name__, exc)))
    # A LIVING issue promises a reader it is current. That promise is only
    # honest if somebody has actually looked, and the page has to display the
    # date of the last CHECK rather than the last change. These rows are empty
    # for an ordinary issue: silence is not a living issue, and nothing here
    # may invent one.
    out.extend(watch.preflight_rows(slug, page.read_text(encoding="utf-8")))

    if for_email:
        # Presence only. The value is never read into any output, here or
        # anywhere else in this file.
        out.append(("sender credentials", OK if has_sender_key() else BAD,
                    "%s is available to the sender" % SENDER_KEY if has_sender_key()
                    else "%s is not set and not in %s — the send will fail"
                         % (SENDER_KEY, ENVFILE.relative_to(ROOT))))

    # The page's own date, against the day it is actually going out. An
    # assessment published on the 28th whose masthead says the 26th is the
    # error this publication exists to point at, printed on itself.
    # datetime.now() is the clock of whoever runs this, and that is deliberate:
    # the masthead should say the day the piece went out where it went out from.
    # But it means two machines in different zones disagree for part of every
    # day. On 2026-08-29 this check passed at 02:15 UTC and failed on the
    # publisher's Mac at 19:15 Pacific the evening before, on the same file,
    # because the date had been typed from the wrong side of midnight. Whoever
    # sets it should not be typing it at all -- see the `dateline` command --
    # and when it is off by exactly one day the message says why rather than
    # leaving somebody to work it out.
    today = pretty(datetime.now().date())
    hd = header_date(ptext if False else page.read_text(encoding="utf-8"))
    detail = f"says {hd or 'nothing'}, and today is {today}"
    if hd != today:
        detail += " — a reader reads that as when it was written"
        try:
            d1 = datetime.strptime(hd, "%d %B %Y").date() if hd else None
            if d1 and abs((d1 - datetime.now().date()).days) == 1:
                tz = datetime.now().astimezone().tzname() or "local time"
                detail += (". Exactly one day out, which is what a dateline set from a "
                           "machine in another time zone looks like — this one is on %s. "
                           "Set it from the machine that publishes: publish.py dateline %s"
                           % (tz, slug))
        except Exception:
            pass
    # Whether a stale dateline blocks depends on whether anything is actually
    # being published. This check exists because an assessment went out on the
    # 28th with a masthead saying the 26th. It does NOT exist to make a page
    # that is already live, and identical to the repo, re-date itself every
    # morning. On 2026-08-29 it blocked issue one for saying 28 August, which
    # is the day issue one was last changed and therefore the correct date.
    # `live_body` is fetched below for the live-page check; do it once, here,
    # so the two checks agree about what is being published.
    _live_now = live_body(cfg["url"])
    _nothing_to_publish = (
        _live_now is not None
        and hashlib.sha256(_live_now.encode()).hexdigest() == sha(page))
    if hd != today and _nothing_to_publish:
        out.append(("page dateline", OK,
                    f"says {hd}, and the live page is identical to the repo — "
                    f"nothing is being published, so that is the day it last changed"))
    else:
        out.append(("page dateline", OK if hd == today else BAD, detail))
    ao = as_of_date(page.read_text(encoding="utf-8"))
    if ao:
        out.append(("evidence 'as of'",
                    OK if (ao == today or _nothing_to_publish) else WARN,
                    f"says {ao}" + ("" if ao == today else
                                    (", and nothing is being published"
                                     if _nothing_to_publish
                                     else f", and today is {today}"))))

    body = _live_now
    if body is None:
        out.append(("live page", WARN, f"could not reach {cfg['url']}"))
    else:
        same = hashlib.sha256(body.encode()).hexdigest() == sha(page)
        out.append(("live page", OK if same else WARN,
                    "matches the repo" if same
                    else "DIFFERS from the repo — the site is behind"))
        # If readers can already see a different version, this publish is an
        # edit to something published, and the site promises in writing that
        # every such change is recorded with its date and what moved. Nothing
        # checked that until an article went out with a masthead two days stale
        # and ten changed sentences behind it.
        if not same:
            changed = len(changes_since(body, page.read_text(encoding="utf-8")))
            logged = today in corrections_text(slug)
            out.append(("correction recorded", OK if logged else BAD,
                        f"{changed} sentence(s) differ from what readers see now"
                        + (f", and corrections.md carries a {today} entry" if logged
                           else f", and corrections.md has no {today} entry — "
                                "who-pays-for-this promises every change is recorded")))

    if for_update:
        softened = []
        for i, (label, st, detail) in enumerate(out):
            if st == BAD and label in UPDATE_SOFTENS:
                out[i] = (label, WARN, detail + "  [not re-earned for an update: %s]"
                          % UPDATE_SOFTENS[label])
                softened.append(label)
        if softened:
            out.append(("softened for this update", WARN,
                        "%d check(s) downgraded because an update is judged on what "
                        "it adds: %s. Anything not on that list still blocks."
                        % (len(softened), ", ".join(softened))))
    return out


# Rows a --waive cannot cover when an email is being SENT.
#
# On 2026-08-29 issue two was announced with the publication record reading
# "gate reconciled rather than re-run: gated 2026-08-28 on an earlier draft".
# One --waive string covered every STOP, including a stale email gate. The
# email that went out said "Every figure above comes from a trial publication
# or a drug label" while quoting, four paragraphs earlier, a US real-world
# cohort of 9,146 patients and an Italian study of 1,982. The check that
# compares the email's sourcing claims to the page's would have caught it. It
# was waived along with everything else.
#
# The asymmetry is the whole reason this list exists: A PAGE CAN BE CORRECTED
# AFTER PUBLICATION AND AN EMAIL CANNOT BE RECALLED. So on the announce path,
# the rows standing between a false claim and somebody's inbox are not
# waivable at all. Everything else still is, with a reason and a name.
UNWAIVABLE_ON_SEND = {
    "email gate": "the email is what is being sent; a gate on an earlier draft "
                  "is a gate on a different email",
    "page gate": "the email links to the page and vouches for it",
    "email sourcing claims match the page": "this is the exact check that would "
                                            "have stopped the 29 August send",
    "email figures on page": "a figure in an inbox that is not on the page cannot "
                             "be corrected by editing the page",
    "html/text parity": "half the recipients would get a different issue",
    "live page": "subscribers follow the link",
}


def show(rows: list[tuple[str, str, str]], waive: str | None = None,
         unwaivable: dict | None = None) -> bool:
    """Print the preflight and say whether it passes.

    `unwaivable` names rows a --waive must not cover. See UNWAIVABLE_ON_SEND.
    """
    unwaivable = unwaivable or {}
    mark = {OK: "  ok ", BAD: " STOP", WARN: " warn"}
    # A ROW UNDER A MARK THIS DISPLAY DOES NOT KNOW IS A SILENT PASS.
    # b13 was wired in returning "bad" where every other check module returns
    # "BLOCKED". It ran, it found the three figures, and its row printed under
    # no mark at all -- indistinguishable, in a screen of forty rows, from a
    # check that had nothing to say. Any state this display cannot render is
    # promoted to a STOP naming the module, because a check whose verdict
    # cannot be read has not been run.
    rows = [(l, st if st in mark else BAD,
             d if st in mark else
             "this check returned the state %r, which is not one of %s -- its "
             "verdict could not be displayed and is treated as a STOP: %s"
             % (st, sorted(mark), d))
            for l, st, d in rows]
    hard = [l for l, st, _d in rows if st == BAD and l in unwaivable]
    for label, st, detail in rows:
        if st == BAD and label in unwaivable:
            m = " STOP"
        elif waive and st == BAD:
            m = " WAIVED"
        else:
            m = mark[st]
        print(f"{m:>7}  {label:24} {detail}")
    blocked = [l for l, st, _d in rows if st == BAD]
    if hard:
        print()
        print("  NOT WAIVABLE: %s" % ", ".join(hard))
        for l in hard:
            print("    %-38s %s" % (l, unwaivable[l]))
        print()
        print("  A page can be corrected after publication. An email cannot be")
        print("  recalled. On 29 August a stale gate was waived and an email went")
        print("  out saying every figure came from a trial publication or a drug")
        print("  label, over figures from two real-world cohorts. Fix these, or")
        print("  do not send.")
        return False
    if blocked and waive:
        print()
        print(f"  WAIVED: {', '.join(blocked)}")
        print(f"  Reason: {waive}")
        print("  This goes into the publication record. It is not a pass; it is a")
        print("  decision to publish without one, on the record, with a name on it.")
        return True
    return not blocked


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_status(_args) -> int:
    rec = load_record()
    print()
    print(f"{'issue':12} {'page':10} {'live':10} {'email':10} {'last sent':12}")
    print("-" * 60)
    for slug, cfg in ISSUES.items():
        page, ehtml = ROOT / cfg["page"], ROOT / cfg["email_html"]
        pg = gate_report(page)[0] if page.exists() else BAD
        eg = gate_report(ehtml)[0] if ehtml.exists() else BAD
        body = live_body(cfg["url"])
        if body is None:
            live = "unreachable"
        elif hashlib.sha256(body.encode()).hexdigest() == sha(page):
            live = "current"
        else:
            live = "BEHIND"
        sent = [r for r in rec if r["issue"] == slug and r["action"] == "announce"]
        print(f"{slug:12} {('gated' if pg == OK else 'ungated'):10} "
              f"{live:10} {('gated' if eg == OK else 'ungated'):10} "
              f"{(sent[-1]['at'][:10] if sent else 'never'):12}")
    print()
    if not rec:
        print("Nothing has been recorded as published yet.")
    return 0


def cmd_check(args) -> int:
    print(f"\nPreflight: {args.slug}\n")
    ok = show(preflight(args.slug, for_email=False), args.waive)
    print()
    print("Ready." if ok else "BLOCKED — fix every STOP above.")
    return 0 if ok else 1


def cmd_log(_args) -> int:
    rec = load_record()
    if not rec:
        print("\nNo publications recorded.\n")
        return 0
    print()
    for r in rec:
        print(f"  {r['at'][:19]}  {r['action']:9} {r['issue']:12} {r.get('note', '')}")
        print(f"{'':21}  content {r.get('sha', '?')[:16]}  commit {r.get('commit', '-')[:9]}")
    print()
    return 0


def git(*args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def cmd_publish(args) -> int:
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    print(f"\nPreflight: {args.slug}\n")
    if not show(preflight(args.slug, for_email=False), args.waive):
        print("\nBLOCKED — nothing published.")
        return 1
    if not args.yes:
        print("\nPreflight passed. Re-run with --yes to commit, push and wait for the deploy.")
        return 0

    code, out = git("status", "--porcelain")
    if code != 0:
        print(f"\ngit status failed: {out}")
        return 2
    if out.strip():
        for f in ("page", "email_html", "email_txt"):
            git("add", cfg[f])
        git("add", "site/whatholdsup")
        code, out = git("commit", "-m",
                        f"whatholdsup: publish {args.slug} (issue {cfg['number']})")
        # git says "nothing to commit" when the tree is clean and "no changes
        # added to commit" when other files are dirty but none of OURS are.
        # The guard knew the first phrase and not the second, so a second
        # publish attempt -- or any attempt where the site files were already
        # committed and unrelated work was outstanding -- aborted with "commit
        # failed" and a wall of git status, having in fact succeeded earlier.
        # Both phrases mean the same thing here: there is nothing of ours left
        # to commit, which is not a failure.
        nothing_new = ("nothing to commit" in out
                       or "no changes added to commit" in out
                       or "nothing added to commit" in out)
        if code != 0 and not nothing_new:
            print(f"\ncommit failed: {out}")
            return 2
        if code != 0:
            print("  nothing new to commit — the site files are already committed.")
    # A push to a branch nobody deploys is a push that will never go live, and
    # the only symptom is ten minutes of polling followed by "the live page
    # still differs". On 2026-08-28 that is exactly what happened: the whole
    # issue was committed and pushed to a feature branch while the host deploys
    # the default one. Say so before spending the ten minutes.
    _c, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    _c, default = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    default = (default or "origin/main").split("/", 1)[-1].strip()
    branch = (branch or "").strip()
    if branch and default and branch != default:
        print()
        print("  STOP. You are on %s, and the host deploys %s." % (branch, default))
        print("  Pushing here will not put anything in front of a reader. Merge to")
        print("  %s first, then publish from there." % default)
        print()
        print("    git checkout %s && git merge --no-ff %s && git push origin %s"
              % (default, branch, default))
        print()
        print("  Then re-run this command. Nothing has been recorded.")
        print()
        return 2

    # The pre-push guard refuses any push that would change a published
    # page without a record. This push is the one that creates the record,
    # so it would block itself. Say who is knocking.
    os.environ["WHATHOLDSUP_PUBLISHING"] = "1"
    try:
        code, out = git("push", "origin", "HEAD")
    finally:
        os.environ.pop("WHATHOLDSUP_PUBLISHING", None)
    if code != 0:
        print(f"\npush failed: {out}")
        return 2
    print("  pushed. waiting for the deploy to serve it...")

    want = sha(page)
    for attempt in range(40):
        body = live_body(cfg["url"])
        if body and hashlib.sha256(body.encode()).hexdigest() == want:
            print(f"  live matches the repo after {attempt * 15}s")
            break
        time.sleep(15)
    else:
        print("  the live page still differs after 10 minutes. Not recorded as published.")
        return 3

    _c, commit = git("rev-parse", "HEAD")
    append_record({
        "issue": args.slug, "action": "publish",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha": want, "commit": commit, "url": cfg["url"],
        "note": f"issue {cfg['number']} — {cfg['title']}",
        "waived": args.waive or None,
    })
    print(f"\nPublished and recorded. {cfg['url']}")
    return 0


ENVFILE = ROOT / "backend" / ".env"
SENDER_KEY = "RESEND_WHATHOLDSUP_KEY"


def sender_python() -> tuple[str | None, str]:
    """An interpreter that can actually run the sender, and how we found it.

    The sender was launched with sys.executable -- whichever python happened to
    be running this file. On 2026-08-28 that was the system python3, which does
    not have `resend`, while the repo's own venv does. The send failed at the
    last step of a process that had passed every check before it, on a
    dependency that was installed six inches away.

    This is the same fault as --verify reading os.environ while the run read
    backend/.env: a tool that depends on which shell you happened to be in,
    rather than looking for what it needs. Look for it.

    Order: the repo's venv, then whatever is running us. A path is only
    returned if it can actually import the package, because a venv that exists
    and cannot send is not an answer.
    """
    import subprocess as _sp

    def can_send(exe: str) -> bool:
        try:
            r = _sp.run([exe, "-c", "import resend"], capture_output=True, timeout=20)
            return r.returncode == 0
        except Exception:
            return False

    tried = []
    for cand in (ROOT / "backend" / "venv" / "bin" / "python",
                 ROOT / "backend" / "venv" / "bin" / "python3",
                 ROOT / "venv" / "bin" / "python",
                 ROOT / ".venv" / "bin" / "python"):
        if cand.exists():
            tried.append(str(cand))
            if can_send(str(cand)):
                return str(cand), "the repo venv at %s" % cand.parent.parent.relative_to(ROOT)
    tried.append(sys.executable)
    if can_send(sys.executable):
        return sys.executable, "the interpreter running this script"
    return None, "\n".join("    %s" % t for t in dict.fromkeys(tried))


def sender_env(wanted: tuple[str, ...] = ()) -> dict:
    """The environment the sender needs, filled in from backend/.env.

    send_broadcast.py reads its key straight from os.environ and loads no
    dotenv; its docstring tells you to `export` it first. That is fine for a
    person at a terminal and wrong for a button, which inherits whatever
    environment the board happened to start with. On 2026-08-28 the first real
    send failed on exactly that.

    Values already in the environment win, so an exported key still overrides
    the file. Nothing here is printed, logged or recorded — only handed to the
    subprocess.
    """
    wanted = set(wanted or (SENDER_KEY,))
    env = dict(os.environ)
    if not ENVFILE.exists():
        return env
    try:
        lines = ENVFILE.read_text(encoding="utf-8").splitlines()
    except Exception:
        return env
    # Only the variable the sender actually needs. The file holds two dozen
    # secrets for other parts of this repo and none of them are the mailer's
    # business; handing a subprocess everything because it was convenient is
    # how a credential ends up somewhere nobody expected it.
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        if k not in wanted or k in env:
            continue
        env[k] = v.strip().strip('"').strip("'")
    return env


def has_sender_key() -> bool:
    return bool(sender_env().get(SENDER_KEY))


def cmd_record_live(args) -> int:
    """Sign off a change to an already-published page without a full publish.

    The hole this fills. On 2026-08-29 a wrong first author was fixed on
    issue two and pushed in an ordinary commit; the deploy served it and
    published.json still described the version from half an hour before.
    The pre-push guard now refuses that push. But the guard would also
    refuse the change that put a link to issue two in issue one's nav bar
    -- a change nobody could object to -- and the full publish path will
    not take it either, because issue one now fails four checks that did
    not exist when it was published. A guard whose only escape is
    --no-verify is a guard that will be bypassed, and a bypass records
    nothing at all.

    So: this records that a person read the diff and stands behind it. It
    is weaker than a publish and says so in the record. It refuses
    anything large enough to deserve the front door.
    """
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    rec = [r for r in load_record() if r["issue"] == args.slug
           and r["action"] in ("publish", "republish")]
    if not rec:
        print("\n%s has never been published. Use `publish`, not this.\n" % args.slug)
        return 2

    last, now = rec[-1], sha(page)
    if last.get("sha") == now:
        print("\nNothing to record — %s is byte-identical to what was signed off "
              "on %s.\n" % (cfg["page"], last["at"][:19]))
        return 0

    # Find the commit whose blob matches the recorded sha, so we can show a
    # real diff rather than asking someone to trust a hash comparison.
    base = None
    _c, log = git("log", "--format=%H", "--", cfg["page"])
    for commit in [x for x in log.split() if x]:
        blob = subprocess.run(["git", "show", "%s:%s" % (commit, cfg["page"])],
                              cwd=ROOT, capture_output=True)
        if blob.returncode == 0 and hashlib.sha256(blob.stdout).hexdigest() == last["sha"]:
            base = commit
            break

    if base is None:
        print("\nCannot show you what changed: no commit in this history holds the "
              "content\nthat was published on %s. That is itself worth knowing. "
              "Use the full\npublish path so the new content is checked on its own "
              "merits.\n" % last["at"][:19])
        return 2

    _c, diff = git("diff", base, "--", cfg["page"])
    changed = [l for l in diff.splitlines()
               if (l.startswith("+") or l.startswith("-"))
               and not l.startswith(("+++", "---"))]
    prose = [l for l in changed if re.search(r">[^<>]{60,}", l)]

    print("\nWhat changed in %s since it was signed off on %s:\n"
          % (cfg["page"], last["at"][:19]))
    for l in changed[:60]:
        print("   " + l[:160])
    if len(changed) > 60:
        print("   ... and %d more" % (len(changed) - 60))
    print()

    LIMIT = 24
    if len(changed) > LIMIT or prose:
        why = ("%d changed lines, more than the %d this path will take"
               % (len(changed), LIMIT)) if len(changed) > LIMIT else \
              ("%d of them rewrite a sentence a reader will read" % len(prose))
        print("REFUSED — %s.\n" % why)
        print("  This is a change to what the piece SAYS, and it belongs in front of")
        print("  the checks, not beside them:\n")
        print("      python3 scripts/whatholdsup/publish.py publish %s --yes\n"
              % args.slug)
        print("  If that path is blocked by checks written after this issue was")
        print("  published, that is the right argument to have. Have it there.\n")
        return 1

    if not args.reason:
        print("Small enough to record here. Say what it is and why it is not a")
        print("change to the argument, and run again:\n")
        print('      python3 scripts/whatholdsup/publish.py record-live %s \\\n'
              '          --reason "..."\n' % args.slug)
        return 1

    if not args.yes:
        print("Reason: %s\n" % args.reason)
        print("Re-run with --yes to record it.\n")
        return 0

    _c, commit = git("rev-parse", "HEAD")
    append_record({
        "issue": args.slug,
        "action": "republish",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha": now,
        "commit": commit.strip(),
        "url": cfg["url"],
        "note": args.reason,
        "basis": "NOT a preflight. A person read the diff below and signed it as "
                 "not touching the argument. %d changed line(s)." % len(changed),
        "diff": changed,
        "supersedes": last["sha"],
        "waived": None,
    })
    print("Recorded. %s is now signed off at %s.\n" % (cfg["page"], now[:16]))
    print("Commit backend/data/whatholdsup/published.json and push.\n")
    return 0


def cmd_update(args) -> int:
    """The third mode: a substantive change to a LIVING issue.

    `publish` is for a first publication and for a rewrite. `record-live` is
    for a change too small to touch the argument -- it refuses anything that
    rewrites a sentence. Neither fits the ordinary event in a living issue's
    life, which is that a new study appeared and two paragraphs changed.

    Without this, that event has only bad options: run the whole
    first-publication battery for a paragraph, which nobody will keep doing;
    or push past the guard with --no-verify, which records nothing. An issue
    that displays a changelog and is never updated is worse than one that
    never promised.

    What an update must still earn is everything about what it ADDS: the claim
    lint, the source ledger on any new source, a counterexample run on any new
    universal negative, inherited-claims attribution, and the living-issue rows
    -- including that the page's 'Last reviewed' date matches a check that
    actually ran. See UPDATE_SOFTENS for what it does not have to re-earn, and
    why each one is on that list.
    """
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    w = _sibling("watch")

    if w.load(args.slug) is None:
        print("\n  %s is not a living issue — no watch.json." % args.slug)
        print("  Use `publish` for a rewrite, or `record-live` for a change too")
        print("  small to touch the argument. `update` exists for the event in")
        print("  between, and only a living issue has those.\n")
        return 2

    rec = [r for r in load_record() if r["issue"] == args.slug
           and r["action"] in ("publish", "republish", "update")]
    if not rec:
        print("\n  %s has never been published.\n" % args.slug)
        return 2
    if rec[-1].get("sha") == sha(page):
        print("\n  Nothing to update — the page is byte-identical to what was "
              "signed off on %s.\n" % rec[-1]["at"][:19])
        return 0

    print("\nPreflight (update): %s\n" % args.slug)
    if not show(preflight(args.slug, for_email=False, for_update=True), args.waive):
        print("\nBLOCKED — nothing updated.")
        return 1

    if not (args.what and args.changed):
        print("\n  An update needs --what (what appeared in the world) and")
        print("  --changed (what changed on the page). These are the changelog")
        print("  entry a reader will see, and the update is not recorded without")
        print("  them. 'The evidence moved' is the whole distinction between this")
        print("  and a correction.\n")
        return 1

    if not args.yes:
        print("\nPreflight passed. Re-run with --yes to commit, push, wait for the")
        print("deploy, record the update and write the changelog entry.\n")
        return 0

    for f in ("page", "email_html", "email_txt"):
        git("add", cfg[f])
    git("add", "site/whatholdsup")
    git("add", str((ledger.case_dir(args.slug) / "watch.json").relative_to(ROOT)))
    git("add", str((ledger.case_dir(args.slug) / "changelog.md").relative_to(ROOT)))
    code, out = git("commit", "-m", "whatholdsup: update %s — %s"
                    % (args.slug, args.what[:60]))
    if code != 0 and not any(x in out for x in
                             ("nothing to commit", "no changes added to commit",
                              "nothing added to commit")):
        print("\ncommit failed: %s" % out)
        return 2

    os.environ["WHATHOLDSUP_PUBLISHING"] = "1"
    try:
        code, out = git("push", "origin", "HEAD")
    finally:
        os.environ.pop("WHATHOLDSUP_PUBLISHING", None)
    if code != 0:
        print("\npush failed: %s" % out)
        return 2
    print("  pushed. waiting for the deploy to serve it...")

    want = sha(page)
    for attempt in range(40):
        body = live_body(cfg["url"])
        if body and hashlib.sha256(body.encode()).hexdigest() == want:
            print("  live matches the repo after %ds" % (attempt * 15))
            break
        time.sleep(15)
    else:
        print("  the live page still differs after 10 minutes. Not recorded.")
        return 3

    _c, commit = git("rev-parse", "HEAD")
    append_record({
        "issue": args.slug, "action": "update",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha": want, "commit": commit.strip(), "url": cfg["url"],
        "note": args.what,
        "changed": args.changed,
        "source": args.source,
        "basis": "living issue update — judged on what it adds. Softened checks "
                 "are listed in the preflight output above and in UPDATE_SOFTENS.",
        "waived": args.waive,
    })
    doc = w.load(args.slug)
    doc.setdefault("changelog", []).append({
        "on": datetime.now(timezone.utc).date().isoformat(),
        "by": "publish.py update",
        "what": args.what, "changed": args.changed, "source": args.source,
        "page_sha": want,
    })
    w.save(args.slug, doc)
    print("\n  Recorded, and a changelog entry written against sha %s." % want[:16])
    print("  Now write the reader-facing version into %s and commit it.\n"
          % (ledger.case_dir(args.slug) / "changelog.md").relative_to(ROOT))
    return 0


def cmd_announce(args) -> int:
    cfg = ISSUES[args.slug]
    ehtml = ROOT / cfg["email_html"]
    print(f"\nPreflight: {args.slug}\n")
    rows = preflight(args.slug, for_email=True)
    if not show(rows, args.waive, UNWAIVABLE_ON_SEND):
        print("\nBLOCKED — nothing sent.")
        return 1
    live = [d for l, _s, d in rows if l == "live page"]
    if live and "DIFFERS" in live[0]:
        print("\nBLOCKED — the site is behind the repo. Publish before announcing, or "
              "subscribers will follow a link to something older than the email.")
        return 1
    if not args.yes:
        print("\nPreflight passed. Re-run with --yes to send.")
        return 0

    subject = (getattr(args, "subject", None) or cfg.get("email_subject") or "").strip()
    audience = cfg.get("audience")
    if not subject:
        print("\nBLOCKED — no subject line. Nothing sent.")
        return 1
    if not audience:
        print("\nBLOCKED — no audience configured for %s. Nothing sent." % args.slug)
        return 1
    if not SENDER.exists():
        print("\nBLOCKED — %s is missing. Nothing sent." % SENDER)
        return 1
    if not has_sender_key():
        print("\nBLOCKED — %s is not set and is not in %s. Nothing sent."
              % (SENDER_KEY, ENVFILE.relative_to(ROOT)))
        print("Add it to that file as %s=... (the value never appears in any" % SENDER_KEY)
        print("output, record or log), or export it in the shell that runs the board.")
        return 1

    # The send happens HERE, and the record is written only if it succeeds.
    #
    # The first version of this function wrote the record and then printed "now
    # run send_broadcast.py to perform the send." Run from a terminal that is a
    # readable instruction. Run from a button it is invisible, and on
    # 2026-08-28 the publication record carried a broadcast that had never been
    # transmitted. A record written before the act it records is not a record.
    # send_broadcast.py has its own gate guard, and it is a good one: it refuses
    # content whose gate report says FAILED or whose sha does not match what was
    # checked. It knows nothing about reconciliation, so a file whose findings
    # are all resolved but which has been edited since still reads to it as
    # unchecked — which is the correct default and the wrong answer here.
    #
    # So: our own gate_state decides, and what it decides is passed through as
    # the sender's waiver reason, where it prints in the output and lands in the
    # publication record. If our check does NOT pass, nothing is passed through
    # and the sender blocks, which is what should happen.
    g = gate_state(ehtml, args.slug)
    basis = args.waive
    if not basis and g["state"] in (OK, WARN) and not g["fresh"]:
        basis = "gate reconciled rather than re-run: %s" % g["detail"]
    exe, how = sender_python()
    if exe is None:
        print()
        print("  No interpreter available here can import `resend`, so the send")
        print("  cannot run. Tried:")
        print(how)
        print()
        print("  Install it where the sender will look first:")
        print("    %s/backend/venv/bin/pip install resend" % ROOT)
        print()
        print("  Nothing has been sent and nothing recorded.")
        print()
        return 2
    print("  sender: %s" % how)
    cmd = [exe, str(SENDER),
           "--segment", audience,
           "--subject", subject,
           "--html", str(ROOT / cfg["email_html"]),
           "--text", str(ROOT / cfg["email_txt"]),
           "--gate-report", str(ehtml) + ".gate.json",
           "--send"]
    if basis:
        cmd += ["--gate-waived", basis]
    if getattr(args, "dry_run", False):
        # Rehearsal: every check the sender runs, no API call, no record. There
        # was no way to try this path without mailing a list, which is why the
        # first thing it ever did in anger was record a send that never happened.
        cmd.remove("--send")
        cmd += ["--dry-run"]
    print("\nSending: %s" % " ".join(cmd[1:]))
    print()
    proc = subprocess.run(cmd, cwd=str(SENDER.parent), capture_output=True,
                          text=True, env=sender_env())
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out.strip())
    if proc.returncode != 0:
        print("\nSEND FAILED — exit %d. Nothing has been recorded." % proc.returncode)
        return 1
    if getattr(args, "dry_run", False):
        print("\nRehearsal only. Nothing sent, nothing recorded.")
        return 0
    if "SENT" not in out:
        print("\nThe sender exited 0 but did not report a send. Nothing recorded — "
              "check the Resend dashboard before trying again, so nobody gets it twice.")
        return 1

    bid = ""
    # Permissive on purpose: the id is written into the record so a send can be
    # traced in the Resend dashboard, and a pattern that only matched hex UUIDs
    # would drop any other format silently — recording a send with no way back
    # to it, which is half of the failure this function already had once.
    mb = re.search(r"broadcast\s+([A-Za-z0-9_-]{4,})", out)
    if mb:
        bid = mb.group(1)
    append_record({
        "issue": args.slug, "action": "announce",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha": sha(ehtml), "commit": git("rev-parse", "HEAD")[1],
        "note": "sent to segment %s%s" % (audience, (", broadcast " + bid) if bid else ""),
        "gate_basis": basis or "gate report passed on these exact bytes",
        "subject": subject,
        "waived": args.waive or None,
    })
    print("\nSent, and recorded.")
    return 0




def case_dir(slug: str) -> Path | None:
    for d in sorted(CASES.glob("*/issue.json")):
        try:
            if json.loads(d.read_text()).get("slug") == slug:
                return d.parent
        except Exception:
            continue
    return None


def cmd_send_for_review(args) -> int:
    """Snapshot exactly what the reviewer is about to read, then hand it over.

    reviews.json stores the hash, which proves a later version differed. Only
    the bytes say what it actually said. Six months on, deciding whether a
    reviewer was objecting to sentence A or to the sentence that replaced it
    is not a question a hash can answer.
    """
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    case = case_dir(args.slug)
    if case is None:
        print(f"No case file for {args.slug} under {CASES}/ — create issue.json first.")
        return 2
    digest = sha(page)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snap = case / "review" / f"{day}-sent.html"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_bytes(page.read_bytes())

    adj = case / "review" / f"{day}-adjudication.md"
    if not adj.exists():
        adj.write_text(f"""# {args.slug} — adjudication of the outside review, {day}

Reviewed content: `{snap.name}`, sha256 `{digest[:16]}`
Standard: version {json.loads((case / 'issue.json').read_text()).get('standards_version', '?')}

The review itself is in `{day}-review.md` and is never edited after the fact,
including by us. This file sits beside it and is where our decisions go.

One block per finding. Every REJECT also goes into `draft_decisions.json` with
a `what_would_change_it`, so a rejection is a judgment on the record rather
than a thing we chose not to do.

---

## OR-001

**Finding**

> _paste the reviewer's finding_

**Disposition** — ACCEPT / ACCEPT-IN-PART / REJECT

**Reason**

**Change** — the exact edit, or "none"

**Sources considered** — S00x, S00y
""", encoding="utf-8")

    print(f"\nSnapshot: {snap.relative_to(ROOT)}")
    print(f"sha256   : {digest}")
    print(f"Adjudication template: {adj.relative_to(ROOT)}")
    print(f"\nSend the reviewer {cfg['page']} and the prompt at")
    print("docs/whatholdsup-outside-review-prompt.md. Not the email, and not the")
    print("gate report — a reader shown our findings anchors on them.")
    print("Save their report verbatim as", (case / 'review' / f'{day}-review.md').relative_to(ROOT))
    return 0


def cmd_review(args) -> int:
    """Record that an outside review happened and was adjudicated."""
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    if not page.exists():
        print(f"missing: {page}")
        return 2
    rows = []
    if REVIEWS.exists():
        try:
            rows = json.loads(REVIEWS.read_text()).get("reviews", [])
        except Exception:
            rows = []
    case = case_dir(args.slug)
    snaps = sorted((case / "review").glob("*-sent.html")) if case else []
    match = [f for f in snaps if hashlib.sha256(f.read_bytes()).hexdigest() == sha(page)]

    # A review that produced accepted findings necessarily changed the page, so
    # requiring the snapshot to match the CURRENT text made every useful review
    # unrecordable. The old message told you to "record the review against that
    # version, not this one" and then gave you no way to do it. --reviewed does.
    #
    # Both hashes go on the record: the one the reviewer read, and the one the
    # page reached after we acted. A review is a statement about the first, and
    # the second is what says how far the page has travelled since.
    if not match and getattr(args, "reviewed", None):
        want = getattr(args, "reviewed", None)
        named = [f for f in snaps if f.name == want or str(f) == want]
        if not named:
            print("\nNo snapshot called %s under %s/review/."
                  % (getattr(args, "reviewed", None), case.name))
            for f in snaps:
                print(f"  have: {f.name}  sha {hashlib.sha256(f.read_bytes()).hexdigest()[:16]}")
            return 2
        match = named
    if not match:
        print("\nNo snapshot matches the current page.")
        print("If the page has changed since the review — which it will have, if you")
        print("acted on anything the reviewer found — name the snapshot they read:")
        print("    --reviewed <name>-sent.html")
        for f in snaps:
            print(f"  have: {f.name}  sha {hashlib.sha256(f.read_bytes()).hexdigest()[:16]}")
        return 2

    rows.append({
        "issue": args.slug,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha": hashlib.sha256(match[-1].read_bytes()).hexdigest(),
        "sha_after_adjudication": sha(page),
        "reviewed_file": str(match[-1].relative_to(ROOT)),
        "standards_version": json.loads((case / "issue.json").read_text()).get("standards_version"),
        "reviewer": args.reviewer,
        "findings": args.findings,
        "accepted": args.accepted,
        "note": args.note or "",
    })
    REVIEWS.parent.mkdir(parents=True, exist_ok=True)
    REVIEWS.write_text(json.dumps({
        "what_this_is": "Outside reviews of full assessments, and what we did with "
                        "them. Bound to the content hash the reviewer actually read, "
                        "because a review of an earlier draft is not a review of this "
                        "one. Findings we rejected belong in draft_decisions.json with "
                        "a reason, like every other finding we reject.",
        "reviews": rows,
    }, indent=2), encoding="utf-8")
    rej = args.findings - args.accepted
    print(f"\nRecorded: {args.findings} finding(s), {args.accepted} accepted, {rej} rejected.")
    if rej:
        print(f"Those {rej} rejected finding(s) belong in draft_decisions.json with a")
        print("reason and a what_would_change_it, or this record is the only trace")
        print("that somebody decided to publish anyway.")
    return 0



# ---------------------------------------------------------------------------
# what changed since the reviewer read it
#
# The board used to ask "confirm the only changes since were the ones it asked
# for". Nobody could answer that honestly: the reviewed snapshot and the
# current file are both on disk, and the person being asked had read neither
# side by side. A confirmation that rests on knowledge the confirmer does not
# have is worse than no confirmation, because it produces a signature and no
# check. So the board shows the difference, sentence by sentence, and the
# signature is on something seen.
# ---------------------------------------------------------------------------

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“(])")


def sentences(raw: str) -> list[str]:
    """Visible prose, one sentence per entry, tags and entities resolved.

    Diffing the markup instead would report a changed href as a changed
    argument. What a reviewer read is the prose.
    """
    t = _html.unescape(_TAG.sub(" ", raw))
    for a, b in _SUBS.items():
        t = t.replace(a, b)
    t = _WS.sub(" ", t)
    return [x.strip() for x in _SENT.split(t) if len(x.strip()) > 3]


def changes_since(old_raw: str, new_raw: str, context: int = 0) -> list[tuple[str, str, str]]:
    """[(kind, was, now)] — kind is changed, removed or added."""
    import difflib
    a, b = sentences(old_raw), sentences(new_raw)
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            # Pair them up so a reworded sentence reads as one change rather
            # than a deletion next to an unrelated insertion.
            for k in range(max(i2 - i1, j2 - j1)):
                was = a[i1 + k] if i1 + k < i2 else ""
                now = b[j1 + k] if j1 + k < j2 else ""
                out.append(("changed" if was and now else ("removed" if was else "added"),
                            was, now))
        elif tag == "delete":
            for x in a[i1:i2]:
                out.append(("removed", x, ""))
        elif tag == "insert":
            for x in b[j1:j2]:
                out.append(("added", "", x))
    return out


def recorded_changes(slug: str) -> list[dict]:
    case = case_dir(slug)
    fp = (case / "changes.json") if case else None
    if not fp or not fp.exists():
        return []
    try:
        return json.loads(fp.read_text()).get("changes", [])
    except Exception:
        return []


def explain(kind: str, was: str, now: str, recorded: list[dict]) -> dict | None:
    """Find the recorded decision this change came from.

    Matched on the prose, both sides. A recorded change whose "was" no longer
    matches anything in the diff has been superseded; a diff entry with no
    recorded change went in without a decision, and that is the only thing here
    worth a human's attention.
    """
    w, n = flatten(was), flatten(now)
    for r in recorded:
        rw, rn = flatten(r.get("was") or ""), flatten(r.get("now") or "")
        if rw == w and rn == n:
            return r
    for r in recorded:                       # tolerate light re-editing since
        rw, rn = flatten(r.get("was") or ""), flatten(r.get("now") or "")
        if w and rw and (w in rw or rw in w) and (not n or not rn or n in rn or rn in n):
            return r
    return None


def decision_labels(slug: str) -> set[str]:
    """Every label a recorded change is allowed to cite.

    Section headings in the adjudication, plus the decisions file. Without this
    check `because` is a free-text field, and a reconciliation that passes on
    free text is a reconciliation that passes on anything. With it, an
    automatic pass means every change traces to something a person can open and
    read.
    """
    out = set()
    case = case_dir(slug)
    if case:
        # Both directories: review/ holds what an outside reader found, advocate/
        # holds what a source's own counsel argued and how we answered. A change
        # made because the NCCN panel's advocate asked a question, and the
        # operator went and read the guideline, has a decision behind it in
        # exactly the sense this check means -- it just does not live in review/.
        adjs = list((case / "review").glob("*-adjudication.md"))
        adjs += [f for f in (case / "advocate").glob("*-adjudication.md")
                 if "TEST" not in f.name]
        # And counterexample/. A hunt adjudication is a decision a person wrote
        # down and can be made to read -- which is the entire test this function
        # applies. Leaving it out meant a sentence rewritten BECAUSE a hunt broke
        # it could not cite the hunt that broke it, so the most directly evidenced
        # changes on the page were the ones that read as unexplained.
        adjs += [f for f in (case / "counterexample").glob("*-adjudication.md")
                 if "TEST" not in f.name]
        for adj in adjs:
            for line in adj.read_text(encoding="utf-8").splitlines():
                # "### S001-05" is a per-question decision and is citable on its
                # own; "## S001 — ..." is the source it belongs to.
                if line.startswith("### "):
                    out.add(line[4:].strip())
                    out.add(re.split(r"\s+[\u2014-]\s+", line[4:].strip())[0].strip())
                if line.startswith("## "):
                    head = line[3:].strip()
                    # "GATE-c34 / c35 — ACCEPT" cites as GATE-c34/c35 or GATE-c34
                    out.add(head)
                    first = re.split(r"\s+[\u2014-]\s+|\s+\(", head)[0].strip()
                    out.add(first)
                    out.add(first.replace(" / ", "/").replace(" /", "/").replace("/ ", "/"))
                    # "GATE-c28 / c29" names two findings, and the second one
                    # carries no prefix of its own. Expanding it is the whole
                    # difference between a label that resolves and one that
                    # silently does not.
                    m = re.match(r"([A-Z]+)-(.+)", first)
                    if m:
                        for part in re.findall(r"c?\d+", m.group(2)):
                            out.add("%s-%s" % (m.group(1), part))
    cfg = ISSUES.get(slug, {})
    for f in (cfg.get("page"), cfg.get("email_html")):
        if not f:
            continue
        for d in fc.load_decisions(fc.DECISIONS, Path(f).name).values():
            for key in ("id", "decision"):
                if d.get(key):
                    out.add(str(d[key]))
    out.add("AD-HOC")
    return {x for x in out if x}


def reconcile(slug: str) -> tuple[list[tuple], list[tuple], list[dict]]:
    """(explained, unexplained, unused recorded entries).

    A change counts as explained only if a recorded entry matches its prose AND
    that entry cites a label that resolves. Both halves matter: the first says
    somebody wrote down why, the second says the why points somewhere real.
    """
    cfg = ISSUES[slug]
    page = ROOT / cfg["page"]
    case = case_dir(slug)
    try:
        rows = json.loads(REVIEWS.read_text()).get("reviews", [])
    except Exception:
        rows = []
    mine = [r for r in rows if r.get("issue") == slug]
    if not mine or not case:
        return [], [], []
    latest = mine[-1]
    snaps = [f for f in sorted((case / "review").glob("*-sent.html"))
             if hashlib.sha256(f.read_bytes()).hexdigest() == latest.get("sha")]
    if not snaps:
        return [], [], []
    recorded = recorded_changes(slug)
    diff = changes_since(snaps[-1].read_text(encoding="utf-8"),
                         page.read_text(encoding="utf-8"))
    labels = decision_labels(slug)
    ok, bad, used = [], [], []
    for kind, was, now in diff:
        r = explain(kind, was, now, recorded)
        if r and r.get("because") not in labels:
            r = dict(r)
            r["unresolved"] = True
            bad.append((kind, was, now, r))
        elif r:
            ok.append((kind, was, now, r))
            used.append(id(r))
        else:
            bad.append((kind, was, now, None))
    return ok, bad, [r for r in recorded if id(r) not in used]


def review_diff_text(slug: str) -> tuple[bool, str]:
    """The reviewed snapshot against the file as it stands, in words."""
    cfg = ISSUES[slug]
    page = ROOT / cfg["page"]
    case = case_dir(slug)
    if not case:
        return False, "no case directory for %s" % slug
    try:
        rows = json.loads(REVIEWS.read_text()).get("reviews", [])
    except Exception:
        rows = []
    mine = [r for r in rows if r.get("issue") == slug]
    if not mine:
        return False, "no outside review recorded for %s" % slug
    latest = mine[-1]
    snaps = sorted((case / "review").glob("*-sent.html"))
    match = [f for f in snaps
             if hashlib.sha256(f.read_bytes()).hexdigest() == latest.get("sha")]
    if not match:
        return False, ("the snapshot the reviewer read is not on disk; "
                       "nothing can be compared against it")
    snap = match[-1]
    now = sha(page)
    if latest.get("sha") == now:
        return True, "The reviewed file and the current file are the same. Nothing changed."

    ok, bad, stale = reconcile(slug)
    total = len(ok) + len(bad)
    lines = ["The reviewer read  %s  (%s)" % (snap.name, str(latest.get("sha"))[:12]),
             "The file now is    %s  (%s)" % (page.name, now[:12]),
             "",
             "%d change(s) to the prose since. %d accounted for, %d not."
             % (total, len(ok), len(bad)),
             ""]
    if bad:
        lines.append("NOT ACCOUNTED FOR — these went in without a recorded decision:")
        lines.append("")
        for i, (kind, was, nowtxt, _r) in enumerate(bad, 1):
            lines.append(" !! %d. %s" % (i, kind.upper()))
            if was:
                lines.append("       was:  %s" % was)
            if nowtxt:
                lines.append("       now:  %s" % nowtxt)
            lines.append("")
        lines.append("Each needs a decision before this can be confirmed. Nothing here "
                     "is for a reader of this board to attest to — it is work that has "
                     "not been done.")
        lines.append("")
    lines.append("Accounted for:")
    lines.append("")
    for i, (kind, was, nowtxt, r) in enumerate(ok, 1):
        lines.append("%2d. %-14s %s" % (i, r.get("because", "?"), r.get("note", "")))
        if was:
            lines.append("    was:  %s" % was[:150])
        if nowtxt:
            lines.append("    now:  %s" % nowtxt[:150])
        lines.append("")
    if stale:
        lines.append("Recorded but no longer visible in the diff (superseded or reverted):")
        for r in stale:
            lines.append("    %s — %s" % (r.get("because", "?"), (r.get("was") or "")[:90]))
        lines.append("")
    adj = sorted((case / "review").glob("*-adjudication.md"))
    if adj:
        lines.append("Each label above is a section of %s or a decision in "
                     "draft_decisions.json." % adj[-1].name)
    return not bad, "\n".join(lines)


def cmd_review_changes(args) -> int:
    ok, text = review_diff_text(args.slug)
    print()
    print(text)
    print()
    return 0 if ok else 2


def cmd_explain_change(args) -> int:
    """Record why a change was made that nothing on file explains.

    This is the only part of the review step a person is asked for, and the
    only part they are in a position to give. Which change corresponds to which
    decision, and whether that decision exists, the tool works out itself.
    """
    case = case_dir(args.slug)
    if not case:
        print("\n  no case directory for %s\n" % args.slug)
        return 2
    note = (args.note or "").strip()
    if len(note) < 8:
        print("\n  Say why the change was made. One line, in terms someone could")
        print("  disagree with.\n")
        return 2
    fp = case / "changes.json"
    try:
        data = json.loads(fp.read_text()) if fp.exists() else {"changes": []}
    except Exception:
        data = {"changes": []}
    data.setdefault("changes", []).append({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "by": args.by,
        "kind": "changed" if (args.was and args.now) else ("removed" if args.was else "added"),
        "was": args.was or "",
        "now": args.now or "",
        "because": args.because or "AD-HOC",
        "note": note,
    })
    fp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    ok, bad, _s = reconcile(args.slug)
    print("\n  Recorded. %d change(s) accounted for, %d still not.\n" % (len(ok), len(bad)))
    return 0


def cmd_confirm_review(args) -> int:
    """Record that the changes made after a review were the ones it asked for."""
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    try:
        data = json.loads(REVIEWS.read_text())
    except Exception:
        print("\n  no reviews recorded for anything yet\n")
        return 2
    mine = [r for r in data.get("reviews", []) if r.get("issue") == args.slug]
    if not mine:
        print("\n  no outside review recorded for %s — there is nothing to carry\n" % args.slug)
        return 2
    latest = mine[-1]
    now = sha(page)
    if latest.get("sha") == now:
        print("\n  the review already covers this exact text; nothing to confirm\n")
        return 2
    ok, bad, _stale = reconcile(args.slug)
    if bad:
        print("\n  %d change(s) since the review have no recorded decision behind them."
              % len(bad))
        print("  That is not something to confirm; it is something to decide. Run")
        print("  review-changes to see them.\n")
        return 2
    # Every change traced to a decision. Asking a person to attest to that
    # reconciliation was asking them to sign for a check only the person who
    # made the changes could perform. The reconciliation is the check, and it
    # is written down; the signature just says a human saw the result.
    auto = ("all %d change(s) since the review reconcile to a recorded decision: %s"
            % (len(ok), ", ".join(sorted({r.get("because", "?") for _k, _w, _n, r in ok}))))
    reason = (args.reason or "").strip() or auto
    data.setdefault("confirmations", []).append({
        "issue": args.slug,
        "reviewed_sha": latest.get("sha"),
        "now_sha": now,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "by": args.by,
        "reason": reason,
        "reconciled": [{"because": r.get("because"), "was": w[:200], "now": n[:200]}
                       for _k, w, n, r in ok],
    })
    REVIEWS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n  Confirmed: the review of %s still applies to %s."
          % (str(latest.get("sha"))[:12], now[:12]))
    print("  Any further edit voids this and asks again.\n")
    return 0


def cmd_register(_args) -> int:
    """Regenerate issue-register.csv from the case files.

    Generated, never hand-edited. A register somebody updates by hand is wrong
    by the fifth issue and nobody notices which row — and the whole value of a
    register is that you can trust it without opening anything else.
    """
    import csv
    rows = []
    for d in sorted(CASES.glob("*/issue.json")):
        try:
            m = json.loads(d.read_text())
        except Exception as exc:
            print(f"[WARN] {d} unreadable: {exc}")
            continue
        dates, rev = m.get("dates", {}), m.get("review", {})
        rows.append({
            "id": m.get("id", ""), "slug": m.get("slug", ""),
            "title": m.get("title", ""), "topic": m.get("topic", ""),
            "status": m.get("status", ""),
            "standards": m.get("standards_version", ""),
            "drafted": dates.get("draft_started") or "",
            "reviewed": dates.get("outside_review") or "",
            "published": dates.get("published") or "",
            "findings": rev.get("findings") if rev.get("findings") is not None else "",
            "accepted": rev.get("accepted") if rev.get("accepted") is not None else "",
            "rejected": rev.get("rejected") if rev.get("rejected") is not None else "",
            "corrections": (m.get("corrections") or {}).get("count", ""),
            "url": m.get("url", ""),
        })
    if not rows:
        print(f"No issue.json found under {CASES}/")
        return 1
    with REGISTER.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\n{REGISTER.name}: {len(rows)} issue(s)")
    for r in rows:
        print(f"  {r['id']:8} {r['status']:10} {r['slug']:22} {r['title']}")
    return 0



# The steps are gates, and a gate that passes should hand straight to the next
# one. Until now each was a separate command a human had to remember, in order,
# which is how the outside review got skipped: not by a decision, but by nobody
# reaching that line. `next` says what the single next action is. `run` performs
# every step that is reversible and stops at the first thing that is not.

GATE = ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py"


def next_action(slug: str) -> tuple[str, str]:
    """(what to do next, the command that does it)."""
    cfg = ISSUES[slug]
    page, ehtml = ROOT / cfg["page"], ROOT / cfg["email_html"]

    for label, f in (("assessment", page), ("email", ehtml)):
        g = gate_state(f, slug)
        if g["state"] == BAD:
            rel = f.relative_to(ROOT)
            since = (" --since ../%s.gate.json" % rel
                     if f.with_suffix(f.suffix + ".gate.json").exists() else "")
            # A run is not always the answer. Read what the last one found
            # first: on 2026-08-28 six of its twelve findings were already
            # fixed, two were the instrument, and a re-run would have cost
            # money to rediscover that.
            if g["outstanding"]:
                return ("decide the %s gate — %s" % (label, g["detail"]),
                        'python scripts/whatholdsup/publish.py accept-gate %s --file %s '
                        '--despite %s --reason "..."'
                        % (slug, "assessment" if label == "assessment" else "email",
                           ",".join(sorted(x["id"] for x in g["outstanding"]))))
            hint = ("\n        read them first: publish.py gate-status %s" % slug
                    if g["exists"] else "")
            return ("gate the %s — %s%s" % (label, g["detail"], hint),
                    "python scripts/signal/factcheck_draft.py ../%s%s --report ../%s.gate.json"
                    % (rel, since, rel))

    st, detail = outside_review(page, slug)
    if st == BAD:
        return ("outside review — the only check that finds what our own roles cannot "
                "see, and it has never run",
                "python scripts/whatholdsup/publish.py send-for-review %s" % slug)
    if st == WARN:
        return ("confirm the outside review still applies — %s" % detail,
                'python scripts/whatholdsup/publish.py confirm-review %s --reason "..."' % slug)

    blocked = [l for l, s_, _d in preflight(slug, for_email=False) if s_ == BAD]
    if blocked:
        return ("resolve: %s" % ", ".join(blocked),
                "python scripts/whatholdsup/publish.py check %s" % slug)

    rec = [r for r in load_record() if r["issue"] == slug]
    pub = [r for r in rec if r["action"] == "publish"]
    # Published is about content, not history. A record from an hour ago says
    # nothing about the file as it stands, and this line said ANNOUNCE while
    # the board next to it said the repo had moved past what readers can see.
    if not pub:
        return ("PUBLISH — everything upstream is clear. This one is yours.",
                "python scripts/whatholdsup/publish.py publish %s --yes" % slug)
    if pub[-1].get("sha") != sha(page):
        return ("REPUBLISH — the page has changed since it was last published. "
                "Readers are on %s, the repo is on %s."
                % (str(pub[-1].get("sha"))[:8], sha(page)[:8]),
                "python scripts/whatholdsup/publish.py publish %s --yes" % slug)
    if not any(r["action"] == "announce" for r in rec):
        return ("ANNOUNCE — the site is live and recorded. This one is yours, and it "
                "cannot be taken back.",
                "python scripts/whatholdsup/publish.py announce %s --yes" % slug)
    return ("nothing — published and announced. The next thing this issue could "
            "need is a changelog entry, and the sweep that would find one does not "
            "exist yet.", "")


def cmd_next(args) -> int:
    what, how = next_action(args.slug)
    print()
    print("  next: %s" % what)
    if how:
        print()
        print("      %s" % how)
        print()
    return 0


def cmd_run(args) -> int:
    """Walk the chain, doing everything reversible, stopping before anything not.

    The two irreversible acts — pushing the site live and sending to a list —
    are never performed here however clear the path looks. They cannot be taken
    back, so they stay something a human types.
    """
    for _ in range(6):
        what, how = next_action(args.slug)
        if what.startswith(("PUBLISH", "ANNOUNCE", "nothing")):
            print()
            print("  stopping here: %s" % what)
            if how:
                print()
                print("      %s" % how)
                print()
            return 0
        if not how.startswith("python scripts/signal/factcheck_draft.py"):
            print()
            print("  stopping here: %s" % what)
            print()
            print("      %s" % how)
            print()
            return 1
        if not args.yes:
            print()
            print("  next step spends API calls: %s" % what)
            print()
            print("      %s" % how)
            print()
            print("  Re-run with --yes to let it work through the gates.")
            print()
            return 0
        print()
        print(">>> %s" % what)
        if subprocess.run(how.split(), cwd=ROOT / "backend").returncode != 0:
            print()
            print("  the gate blocked. Read it, fix or record, then run again.")
            print()
            return 1
    print()
    print("  six steps without reaching a decision point — stopping rather than looping.")
    return 1


DASH_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>What Holds Up &mdash; publication board</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bitter:wght@400;600&family=Karla:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{--paper:#F1F2F0;--card:#FBFBFA;--card-2:#E7E9E6;--ink:#15181A;--ink-2:#4C545A;
--ink-3:#7C858B;--rule:#CFD3CE;--rule-soft:#E0E3DF;--accent:#2C4A63;--accent-bg:#E3E9EE;
--holds:#2E6E52;--partly:#9A6C1C;--nope:#9B3B32;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--paper:#14171A;--card:#1B1F23;--card-2:#23282D;--ink:#E9ECEA;--ink-2:#AFB8BD;
--ink-3:#7B858C;--rule:#333A40;--rule-soft:#262C31;--accent:#8FB4D0;--accent-bg:#1C2A36;
--holds:#6CB795;--partly:#D2A15A;--nope:#D9827A;}}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);margin:0;padding:0 1.25rem 4rem;
font:400 16px/1.6 Karla,system-ui,-apple-system,sans-serif}
.wrap{max-width:50rem;margin:0 auto}
header.top{padding:3rem 0 1.5rem;border-bottom:1px solid var(--rule)}
h1{font:600 2rem/1.15 Bitter,Georgia,serif;margin:0 0 .5rem;letter-spacing:-.015em}
.mono{font:400 .82rem/1.5 "IBM Plex Mono",ui-monospace,monospace;color:var(--ink-3)}
.eyebrow{font:500 .7rem/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.12em;
text-transform:uppercase;color:var(--ink-3)}
.issue{margin-top:2.75rem}
.issue>header{display:flex;justify-content:space-between;align-items:flex-end;gap:1rem;
border-bottom:1px solid var(--rule);padding-bottom:.6rem}
.issue h2{font:600 1.3rem/1.2 Bitter,Georgia,serif;margin:.3rem 0 0}
.count{font:500 .85rem/1 "IBM Plex Mono",ui-monospace,monospace;color:var(--ink-3);
font-variant-numeric:tabular-nums;white-space:nowrap}
.nextup{background:var(--accent-bg);border:1px solid var(--rule-soft);border-radius:3px;
padding:1rem 1.2rem;margin:1.1rem 0 .8rem}
.nextup .kicker{font:500 .68rem/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.14em;
text-transform:uppercase;color:var(--accent);display:block;margin-bottom:.5rem}
.nextup p{margin:0 0 .7rem;font-weight:500}
.nextup p:last-child{margin-bottom:0}
code{display:block;font:400 .78rem/1.5 "IBM Plex Mono",ui-monospace,monospace;
background:var(--card-2);color:var(--ink-2);padding:.5rem .7rem;border-radius:2px;
margin-top:.5rem;white-space:pre-wrap;overflow-wrap:anywhere}
.cmd{position:relative}
.cmd button{position:absolute;top:.35rem;right:.35rem;font:500 .62rem/1 "IBM Plex Mono",
ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;cursor:pointer;
padding:.28rem .5rem;border:1px solid var(--rule);border-radius:2px;
background:var(--card);color:var(--ink-3)}
.cmd button:hover{color:var(--ink);border-color:var(--ink-3)}
button.go{display:inline-block;margin-top:.7rem;font:600 .78rem/1 Karla,system-ui,sans-serif;
cursor:pointer;padding:.55rem .95rem;border-radius:3px;border:1px solid var(--accent);
background:var(--accent);color:var(--paper)}
button.go:hover{filter:brightness(1.12)}
button.go.danger{border-color:var(--nope);background:var(--nope)}
button.go[disabled]{opacity:.5;cursor:default;filter:none}
pre.out{margin:.7rem 0 0;padding:.7rem .8rem;border-radius:2px;background:var(--card-2);
color:var(--ink-2);font:400 .78rem/1.5 "IBM Plex Mono",ui-monospace,monospace;
white-space:pre-wrap;overflow-wrap:anywhere}
pre.out.bad{border-left:2px solid var(--nope)}
pre.out.ok{border-left:2px solid var(--holds)}
form.ask{margin-top:.7rem;display:grid;gap:.6rem;padding:.85rem;border-radius:3px;
border:1px solid var(--rule);background:var(--card)}
form.ask label{display:grid;gap:.3rem}
form.ask label span{font:400 .82rem/1.4 Karla,system-ui,sans-serif;color:var(--ink-2)}
form.ask input{font:400 .85rem/1.4 Karla,system-ui,sans-serif;padding:.45rem .55rem;
border:1px solid var(--rule);border-radius:2px;background:var(--paper);color:var(--ink)}
form.ask input:focus{outline:2px solid var(--accent);outline-offset:-1px}
.askrow{display:flex;gap:.5rem;flex-wrap:wrap}
.askrow button{font:600 .78rem/1 Karla,system-ui,sans-serif;cursor:pointer;
padding:.5rem .95rem;border-radius:3px;border:1px solid var(--accent);
background:var(--accent);color:var(--paper)}
.askrow button.cancel{background:transparent;color:var(--ink-3);border-color:var(--rule)}
.livestate{font:400 .85rem/1.5 "IBM Plex Mono",ui-monospace,monospace;margin:0 0 1.2rem}
.livestate.done{color:var(--holds)}.livestate.warn{color:var(--partly)}
.livestate.blocked{color:var(--nope)}
ol.steps{list-style:none;margin:0;padding:0;display:grid;gap:.35rem}
li.step{display:grid;grid-template-columns:auto 1fr;gap:.85rem;align-items:start;
padding:.7rem .9rem;background:var(--card);border:1px solid var(--rule-soft);border-radius:3px}
li.step .dot{width:.7rem;height:.7rem;border-radius:50%%;margin-top:.42rem;
background:var(--card-2);border:1.5px solid var(--ink-3)}
li.step.done .dot{background:var(--holds);border-color:var(--holds)}
li.step.blocked .dot{background:var(--nope);border-color:var(--nope)}
li.step.warn .dot{background:var(--partly);border-color:var(--partly)}
li.step.done{background:transparent;border-color:transparent}
li.step.done b{color:var(--ink-3)}
li.step b{display:block;font-weight:600}
.detail{display:block;font:400 .85rem/1.5 "IBM Plex Mono",ui-monospace,monospace;
color:var(--ink-2);margin-top:.15rem;overflow-wrap:anywhere}
.why{display:block;font-size:.87rem;color:var(--ink-3);margin-top:.2rem}
ul.finds{list-style:none;margin:.6rem 0 0;padding:0;display:grid;gap:.3rem}
li.f{font:400 .84rem/1.45 Karla,system-ui,sans-serif;padding:.45rem .6rem;
border-left:2px solid var(--rule);background:var(--card-2);border-radius:2px}
li.f b{display:block;font:500 .7rem/1.4 "IBM Plex Mono",ui-monospace,monospace;
letter-spacing:.06em;text-transform:uppercase;margin-bottom:.15rem}
li.f span{color:var(--ink-2);overflow-wrap:anywhere}
li.f.settled{border-left-color:var(--accent);opacity:.72}
li.f.settled b{color:var(--accent)}
details.more{margin-top:.5rem}
details.more summary{cursor:pointer;font:500 .68rem/1 "IBM Plex Mono",ui-monospace,monospace;
letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);padding:.2rem 0}
details.more[open] summary{margin-bottom:.4rem}
li.f.bad{border-left-color:var(--nope)}li.f.bad b{color:var(--nope)}
li.f.gone{border-left-color:var(--holds)}li.f.gone b{color:var(--holds)}
li.f.tool{border-left-color:var(--partly)}li.f.tool b{color:var(--partly)}
li.f.note b{color:var(--ink-3)}
.issue.complete{margin-top:1.6rem;opacity:.82}
.issue.complete>header{padding-bottom:.4rem}
.issue.complete h2{font-size:1.05rem}
.issue.complete .count{color:var(--holds);letter-spacing:.08em;text-transform:uppercase;
font-size:.66rem}
.issue.complete .livestate{margin:.6rem 0 .3rem}
.chip{display:inline-block;margin-left:.6rem;padding:.16rem .45rem;border-radius:2px;
font:500 .62rem/1.3 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.08em;
text-transform:uppercase;vertical-align:middle;
background:var(--accent-bg);color:var(--holds);border:1px solid var(--holds)}
footer{margin-top:3rem;padding-top:1.2rem;border-top:1px solid var(--rule);
font-size:.87rem;color:var(--ink-3)}
</style></head><body><div class="wrap">
<header class="top">
<span class="eyebrow">What Holds Up &middot; internal</span>
<h1>Publication board</h1>
<p class="mono">Generated %(when)s from live state &mdash; gate reports, the publication
record, the review archive, and the site itself. A snapshot: it is baked into the
route at generation time, so regenerate it after anything below changes.</p>
</header>
%(issues)s
<section class="issue"><header><div><span class="eyebrow">not yet built</span>
<h2>Subscriptions</h2></div></header>
<p class="why" style="margin-top:1rem">Counts, growth, unsubscribes and the changelog's
last run belong here. Deliberately absent until the changelog delivers something:
a number on a board is not a working product, and a board full of numbers about a
thing that has never run would be worse than an empty section.</p></section>
<script>
document.addEventListener("click", function (e) {
  var b = e.target.closest("button.copy");
  if (!b) return;
  var c = b.parentNode.querySelector("code");
  if (!c || !navigator.clipboard) return;
  navigator.clipboard.writeText(c.textContent).then(function () {
    b.textContent = "copied";
    setTimeout(function () { b.textContent = "copy"; }, 1200);
  });
});
</script>
<footer>Regenerate with <code style="display:inline;padding:.15rem .35rem">python
scripts/whatholdsup/publish.py dashboard</code>. It reads state, never changes it.</footer>
</div></body></html>"""


# The publication process as a board rather than a sequence of commands to
# remember. Generated fresh on every run from the same functions the CLI uses,
# so it cannot drift from what `check` and `next` say — there is one source of
# truth and this is a rendering of it.
#
# Written to backend/data/, never to site/. It will carry subscriber counts, and
# a page at /admin on a static host protects nothing. The rule from the day
# send_broadcast.py was found being served at a public URL: a directory is not
# an access policy.

DASHBOARD = ROOT / "backend" / "data" / "whatholdsup" / "dashboard.html"

STEPS = [
    ("Draft", "The assessment and the email exist."),
    ("Gate the assessment", "Five adversarial roles. Blocks on fact, contradiction and unevidenced claims about third parties; records phrasing."),
    ("Gate the email", "The same, on the summary that reaches inboxes. It cannot be recalled once sent."),
    ("Outside review", "An independent reader, given the assessment and the standards, and neither our findings nor our adjudication."),
    ("Adjudicate", "We read the review together and decide. Every rejection goes on the record with a reason."),
    ("Publish the site", "Commits, pushes, and waits for the deploy to actually serve it before recording anything."),
    ("Announce", "The broadcast. Refuses if the site is behind the repo, so nobody follows a link to something older than their email."),
]


def _step_states(slug: str) -> list[dict]:
    cfg = ISSUES[slug]
    page, ehtml = ROOT / cfg["page"], ROOT / cfg["email_html"]
    rec = [r for r in load_record() if r["issue"] == slug]
    out = []

    def add(name, why, state, detail, cmd="", finds=None, action=None, chip=""):
        out.append({"name": name, "why": why, "state": state, "detail": detail,
                    "cmd": cmd, "finds": finds or [], "fold": "", "action": action,
                    "chip": chip})

    add(*STEPS[0], "done" if page.exists() and ehtml.exists() else "blocked",
        "assessment and email present" if page.exists() and ehtml.exists() else "missing")

    for (name, why), f, rel, which in ((STEPS[1], page, cfg["page"], "assessment"),
                                       (STEPS[2], ehtml, cfg["email_html"], "email")):
        g = gate_state(f, slug)
        since = (" --since ../%s.gate.json" % rel
                 if f.with_suffix(f.suffix + ".gate.json").exists() else "")
        # A stale run whose findings are all gone has already answered the
        # question. Sending someone to re-run it is the expensive answer, and
        # it is the one this board used to give.
        # ...unless the page has text the run never saw. A signature can settle
        # a finding somebody read and decided about. It cannot settle a
        # sentence nobody has read, and offering accept-gate here would let one
        # bless the 28 unjudged claims on issue two -- turning the new check
        # into a speed bump with a documented way round it.
        if g["exists"] and not g["fresh"] and not g["outstanding"] and not g.get("unjudged"):
            cmd = ('python scripts/whatholdsup/publish.py accept-gate %s --file %s '
                   '--reason "..."' % (slug, which))
        else:
            cmd = ("python scripts/signal/factcheck_draft.py ../%s%s --report ../%s.gate.json"
                   % (rel, since, rel))
        st = out.__len__()
        act, chip = None, ""
        if g["outstanding"] and not g["accepted"]:
            # The only thing here still worth a signature: a decision to proceed
            # past a finding that is genuinely open. It names each one.
            act = {"action": "accept-gate", "slug": slug, "file": which,
                   "label": "Proceed past %d open finding(s)" % len(g["outstanding"]),
                   "ask": "reason", "prefill": "",
                   "despite": ",".join(sorted(x["id"] for x in g["outstanding"]))}
        # A signed gate has passed. It passed by a recorded human decision
        # rather than by a clean run against this exact text, and that
        # difference belongs in the words, not in the colour: amber reads as
        # "something is wrong here", and nothing is.
        state = {OK: "done", WARN: "warn", BAD: "blocked"}[g["state"]]
        if g["state"] == OK and not g["fresh"]:
            chip = "reconciled"
        if g["accepted"] and g["outstanding"]:
            state, chip = "done", "signed off"
        add(name, why, state, g["detail"], cmd,
            finds=_finding_rows(g), action=act, chip=chip)
        srows = _settled_rows(g)
        out[st]["fold"] = _fold(srows, "%d already dealt with" % len(srows)) if srows else ""

    st, detail = outside_review(page, slug)
    rfinds, ract = [], None
    rcmd = "python scripts/whatholdsup/publish.py review-changes %s" % slug
    if st == BAD:
        # Every unaccounted-for change shown in full, and a form for the first.
        # Nothing here asks whether the reconciliation is right. It asks the one
        # question the tool cannot answer: why a sentence changed.
        _ok, _bad, _s = reconcile(slug)
        for kind, was, now_, _r in _bad:
            rfinds.append({"tone": "bad",
                           "head": "%s — no decision on file" % kind.upper(),
                           "text": ("was: %s    now: %s" % (was[:200], now_[:200])).strip()})
        if _bad:
            _k0, w0, n0, _r0 = _bad[0]
            ract = {"action": "explain-change", "slug": slug, "was": w0, "now": n0,
                    "ask": "explain",
                    "label": "Why was this changed? (1 of %d)" % len(_bad)}
    elif st == WARN:
        rcmd = "python scripts/whatholdsup/publish.py send-for-review %s" % slug
        ract = {"action": "send-for-review", "slug": slug, "label": "Snapshot for review"}
    add(*STEPS[3], {OK: "done", WARN: "warn", BAD: "blocked"}[st], detail, rcmd,
        finds=rfinds, action=ract)

    case = case_dir(slug)
    adj = sorted((case / "review").glob("*-adjudication.md")) if case else []
    add(*STEPS[4], "done" if st == OK else "pending",
        ("%s on file" % adj[-1].name) if adj else "no adjudication recorded",
        "python scripts/whatholdsup/publish.py review %s --reviewer NAME --findings N --accepted M" % slug,
        action={"action": "review", "slug": slug, "label": "Record a review",
                "ask": "review"} if st != OK else None)

    # "Published" is a statement about content, not about history. A record
    # from an hour ago says nothing about the file as it stands now, and a
    # board that reads green while the repo has moved past what readers can
    # see is the exact failure this whole thing was built to stop.
    pub = [r for r in rec if r["action"] == "publish"]
    current = bool(pub) and pub[-1].get("sha") == sha(page)
    if not pub:
        pdetail, pstate = "not published", "pending"
    elif current:
        pdetail, pstate = "published %s, and this is that version" % pub[-1]["at"][:10], "done"
    else:
        pdetail = ("last published %s, but the page has changed since — readers are on "
                   "%s, the repo is on %s"
                   % (pub[-1]["at"][:10], str(pub[-1].get("sha"))[:8], sha(page)[:8]))
        pstate = "blocked"
    add(*STEPS[5], pstate, pdetail,
        "python scripts/whatholdsup/publish.py publish %s --yes" % slug,
        action=None if current else {"action": "publish", "slug": slug,
                                     "label": "Publish" if not pub else "Republish",
                                     "ask": "confirm", "danger": 1})

    # A send is a statement about the content that went out, and it stops being
    # true the moment that content changes. This is the same rule the gate
    # acceptances and the publish record already follow -- a verdict unbound
    # from the sha it judged is meaningless -- and it was missing here.
    #
    # Until 2026-08-29 this read `action=None if ann else ...`, so an issue that
    # had ever been announced could never be announced again. Issue two was
    # announced at 02:26 carrying a claim about the NCCN guideline that was
    # corrected the same day; the corrected email was rewritten, re-gated and
    # committed, and the board offered no way to send it, while reporting the
    # step "done" on the strength of a send of different text hours earlier.
    ann = [r for r in rec if r["action"] == "announce"]
    void = [r for r in rec if r["action"] == "announce_void"]
    esha = sha(ehtml) if ehtml.exists() else None
    sent_this = bool(ann) and ann[-1].get("sha") == esha

    if not ann and void:
        astate = "pending"
        adetail = ("not sent — a %s row recorded a send that never happened and has been "
                   "voided" % void[-1]["at"][:10])
    elif not ann:
        astate, adetail = "pending", "not sent"
    elif sent_this:
        astate = "done"
        adetail = "sent %s, and this is that email" % ann[-1]["at"][:10]
    else:
        astate = "warn"
        adetail = ("sent %s — but that send carried a different email. Subscribers have "
                   "%s; the repo has %s. The earlier send cannot be recalled."
                   % (ann[-1]["at"][:10], str(ann[-1].get("sha"))[:8], str(esha)[:8]))

    add(*STEPS[6], astate, adetail,
        "python scripts/whatholdsup/publish.py announce %s --yes" % slug,
        action=None if sent_this else {
            "action": "announce", "slug": slug,
            "label": "Announce" if not ann else "Send the corrected email",
            "ask": "announce", "danger": 1,
            "subject": ISSUES[slug].get("email_subject", "")})
    return out


def _esc(t) -> str:
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _fold(rows: list[dict], label: str) -> str:
    if not rows:
        return ""
    return ('<details class="more"><summary>%s</summary><ul class="finds">%s</ul></details>'
            % (_esc(label),
               "".join('<li class="f %s"><b>%s</b><span>%s</span></li>'
                       % (_esc(x["tone"]), _esc(x["head"]), _esc(x["text"])) for x in rows)))


def _finding_rows(g: dict) -> list[dict]:
    """What the run found, in the order a person needs it.

    Outstanding first, because that is the only part that stops anything.
    Resolved next, because it is the evidence that a stale report is stale.
    Instrument flags recolour a row rather than adding one: the finding and the
    reason to doubt it belong in the same place, or the doubt gets lost.
    """
    """Open items in full; everything already dealt with behind one fold.

    A board that shows twelve findings when five need a decision is a board that
    gets skimmed. The seven that are gone or already judged are evidence, not
    work, and evidence belongs one click away.
    """
    rows = []
    for f in (g.get("outstanding") or []):
        head = "%s%s \u2014 %s" % (f["class"], (" " + f["id"]) if f["id"] else "",
                                   WHERE.get(f["where"], ""))
        body = (f["why"] or f["quote"] or "").strip()
        for cls, why in f["flags"]:
            body += "   [recorded defect %s: %s]" % (cls, why)
        rows.append({"tone": "tool" if f["flags"] else "bad", "head": head,
                     "text": body[:420]})
    for n in g.get("notes") or []:
        rows.append({"tone": "bad", "head": "report inconsistency", "text": n})
    return rows


def _settled_rows(g: dict) -> list[dict]:
    rows = []
    for f in (g.get("settled") or []):
        rows.append({"tone": "settled",
                     "head": "%s %s \u2014 decided" % (f["class"], f["id"]),
                     "text": (f["decision"] or "recorded in draft_decisions.json")})
    for f in (g.get("resolved") or []):
        rows.append({"tone": "gone", "head": "%s %s \u2014 gone from the text" % (f["class"], f["id"]),
                     "text": (f["quote"] or f["why"] or "")[:160]})
    if g.get("calibration"):
        rows.append({"tone": "note", "head": "%d calibration note(s)" % g["calibration"],
                     "text": "Phrasing and framing. Recorded, published, never blocking."})
    return rows


def _cmd(c: str) -> str:
    return ('<div class="cmd"><code>%s</code><button class="copy">copy</button></div>'
            % _esc(c)) if c else ""


INTERACTIVE = False


def _act(a: dict | None) -> str:
    """A button, only on a board that can actually run it.

    The static copy and the one at /api/admin render nothing here. A button
    that does nothing when clicked is worse than no button: it tells you the
    thing is possible from where you are standing, and it is not.
    """
    if not a or not INTERACTIVE:
        return ""
    return ('<button class="go%s" data-act="%s">%s</button>'
            % (" danger" if a.get("danger") else "", _esc(json.dumps(a)), _esc(a["label"])))


def _row(s: dict) -> str:
    finds = "".join('<li class="f %s"><b>%s</b><span>%s</span></li>'
                    % (_esc(x["tone"]), _esc(x["head"]), _esc(x["text"]))
                    for x in (s.get("finds") or []))
    return ('<li class="step %s"><div class="dot"></div><div>'
            '<b>%s%s</b><span class="detail">%s</span><span class="why">%s</span>%s%s%s'
            '</div></li>'
            % (s["state"], _esc(s["name"]),
               ('<span class="chip">%s</span>' % _esc(s["chip"])) if s.get("chip") else "",
               _esc(s["detail"]), _esc(s["why"]),
               ('<ul class="finds">%s</ul>' % finds) if finds else "",
               s.get("fold", ""),
               (_act(s.get("action"))
                + (_cmd(s["cmd"]) if s["state"] != "done" and s["cmd"] else ""))))



ADMIN_ROUTE = ROOT / "site" / "whatholdsup" / "api" / "admin.js"

ADMIN_JS = """// The publication board, behind a password.
//
// WHY THE BOARD IS EMBEDDED IN THE FUNCTION
// -----------------------------------------
// A static file under site/ is served at its own URL whether or not anything
// links to it, so putting the board there and guarding a different route would
// guard nothing. Files under api/ are functions, not static assets. Generating
// this file with the board inlined means there is exactly one path to the
// content and it runs through the check below.
//
// Regenerate with:  python scripts/whatholdsup/publish.py dashboard --web
// It is a snapshot at generation time, which is honest: the board reads gate
// reports and a publication record that live in the repo, and a serverless
// function cannot see those.
//
// WHY BASIC AUTH AND NOT A LOGIN PAGE
// -----------------------------------
// One operator, one secret, no session to store and nothing to get wrong.
// Comparison is constant-time. If ADMIN_PASSWORD is unset the route serves
// nothing at all rather than defaulting open — the failure mode of a guard
// that quietly stops guarding is worse than one that is plainly broken.

const crypto = require("crypto");

const BOARD = %(board)s;

function ok(header, expected) {
  if (!header || !header.startsWith("Basic ")) return false;
  let decoded = "";
  try {
    decoded = Buffer.from(header.slice(6), "base64").toString("utf8");
  } catch { return false; }
  const given = decoded.slice(decoded.indexOf(":") + 1);
  const a = Buffer.from(given);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  return crypto.timingSafeEqual(a, b);
}

module.exports = function handler(req, res) {
  const expected = process.env.ADMIN_PASSWORD;
  if (!expected) {
    console.error("ADMIN_PASSWORD is not set; refusing to serve the board.");
    res.status(500).send("Not configured.");
    return;
  }
  if (!ok(req.headers.authorization, expected)) {
    res.setHeader("WWW-Authenticate", 'Basic realm="What Holds Up", charset="UTF-8"');
    res.status(401).send("Authentication required.");
    return;
  }
  res.setHeader("Content-Type", "text/html; charset=utf-8");
  // Never cached anywhere but the reader's own tab: this is operational state,
  // and a CDN copy of it would outlive the password check.
  res.setHeader("Cache-Control", "no-store, private");
  res.setHeader("X-Robots-Tag", "noindex, nofollow");
  res.status(200).send(BOARD);
};
"""

SERVER_STARTED = ""


def _dashboard_html(interactive: bool = False) -> str:
    global INTERACTIVE
    INTERACTIVE = interactive
    parts = []
    for slug in sorted(ISSUES):
        cfg = ISSUES[slug]
        steps = _step_states(slug)
        what, how = next_action(slug)
        done = sum(1 for s in steps if s["state"] == "done")
        body = live_body(cfg["url"])
        page = ROOT / cfg["page"]
        if body is None:
            live = ("warn", "could not reach the site")
        elif hashlib.sha256(body.encode()).hexdigest() == sha(page):
            live = ("done", "live matches the repo")
        else:
            live = ("blocked", "live is behind the repo")

        rows = "".join(_row(s) for s in steps)

        # An issue with nothing left to do should stop occupying a screen. The
        # steps are still there — they are the evidence that it went through
        # them — but folded, because what a finished issue owes the board is one
        # line saying it is finished and when.
        if done == len(steps):
            rec2 = [r for r in load_record() if r["issue"] == slug]
            pub = [r for r in rec2 if r["action"] == "publish"]
            ann = [r for r in rec2 if r["action"] == "announce"]
            line = " &middot; ".join(filter(None, [
                ("published %s" % pub[-1]["at"][:10]) if pub else "",
                ("announced %s" % ann[-1]["at"][:10]) if ann else "",
                _esc(live[1])]))
            parts.append(
                '<section class="issue complete"><header><div>'
                '<span class="eyebrow">%s &middot; %s</span><h2>%s</h2></div>'
                '<span class="count">complete</span></header>'
                '<p class="livestate %s">%s</p>'
                '<p class="why">Nothing to do. It stays here, folded, until the '
                'changelog sweep finds something in this issue worth telling '
                'subscribers about &mdash; which is not built yet.</p>'
                '<details class="more allsteps"><summary>%d steps, all complete</summary>'
                '<ol class="steps">%s</ol></details></section>'
                % (_esc(slug), _esc(cfg.get("number", "")), _esc(cfg["title"]),
                   live[0], line, len(steps), rows))
            continue

        parts.append(
            '<section class="issue"><header><div>'
            '<span class="eyebrow">%s &middot; %s</span><h2>%s</h2></div>'
            '<span class="count">%d / %d</span></header>'
            '<div class="nextup"><span class="kicker">Next</span><p>%s</p>%s</div>'
            '<p class="livestate %s">%s</p>'
            '<ol class="steps">%s</ol></section>'
            % (_esc(slug), _esc(cfg.get("number", "")), _esc(cfg["title"]),
               done, len(steps), _esc(what),
               _cmd(how) if how else "",
               live[0], _esc(live[1]), rows))

    html = DASH_TEMPLATE % {
        "when": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "issues": "".join(parts),
    }
    if interactive:
        html = html.replace("</body>", ACTION_JS + "</body>")
        if SERVER_STARTED:
            # The page is rebuilt on every request, so its timestamp is always
            # now even when the process serving it is hours old and running
            # code from before the last change. This is the honest line.
            html = html.replace(
                "</header>",
                '<p class="mono">Server started %s &mdash; restart it to pick up '
                'changes to publish.py.</p></header>' % _esc(SERVER_STARTED))
    INTERACTIVE = False
    return html


ACTION_JS = """<script>
// Every prompt() here used to be a browser dialog. Chrome suppresses those
// after one dismissal, and the handler returned silently when it did, which is
// indistinguishable from a dead button. Forms are in the page, cannot be
// suppressed, can be cancelled visibly, and show what they are going to send.
(function () {
  var FIELDS = {
    reason: [{ k: "reason",
               label: "This is what will be recorded. Edit it if you disagree with "
                      + "it. It is bound to the file's hash, so the next edit voids it.",
               ph: "" }],
    explain: [{ k: "note",
                label: "Why was this change made? One line, on the record. Every "
                       + "other change matched a decision already written down; "
                       + "this one matched none." }],
    review: [{ k: "reviewer", label: "Who or what reviewed it?" },
             { k: "findings", label: "How many findings did it return?" },
             { k: "accepted", label: "How many did we act on?" },
             { k: "note", label: "One line on what it changed (optional)" }]
  };

  function confirmFields(action) {
    return [{ k: "confirm",
              label: "This cannot be taken back. Type " + action.toUpperCase()
                     + " to go ahead.",
              ph: action.toUpperCase() }];
  }

  // A subject line is editorial and nobody but the sender can write it, so it
  // is asked for. Everything else about the send the tool already knows.
  function announceFields(subject) {
    return [{ k: "subject", label: "Subject line, as it will appear in the inbox.",
              value: subject || "" },
            { k: "confirm",
              label: "This goes to the list and cannot be recalled. Type ANNOUNCE.",
              ph: "ANNOUNCE" }];
  }

  function box(host) {
    var el = host.querySelector("pre.out");
    if (!el) {
      el = document.createElement("pre");
      el.className = "out";
      host.appendChild(el);
    }
    return el;
  }

  function post(payload, out, btn, then) {
    btn.disabled = true;
    out.className = "out";
    out.textContent = "working...";
    fetch("/do", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (r) { return r.json(); }).then(function (j) {
      out.className = "out " + (j.ok ? "ok" : "bad");
      out.textContent = j.output || (j.ok ? "done" : "failed");
      btn.disabled = false;
      then(j);
    }).catch(function (err) {
      out.className = "out bad";
      out.textContent = "could not reach the board: " + err
        + "\\n\\nIs it still running in the terminal you started it from?";
      btn.disabled = false;
    });
  }

  function form(host, fields, submitLabel, onSubmit) {
    var old = host.querySelector("form.ask");
    if (old) old.parentNode.removeChild(old);
    var f = document.createElement("form");
    f.className = "ask";
    fields.forEach(function (fd) {
      var l = document.createElement("label");
      var t = document.createElement("span");
      t.textContent = fd.label;
      var i = document.createElement("input");
      i.type = "text";
      i.name = fd.k;
      i.autocomplete = "off";
      if (fd.ph) i.placeholder = fd.ph;
      if (fd.value) i.value = fd.value;
      l.appendChild(t);
      l.appendChild(i);
      f.appendChild(l);
    });
    var row = document.createElement("div");
    row.className = "askrow";
    var go = document.createElement("button");
    go.type = "submit";
    go.textContent = submitLabel;
    var no = document.createElement("button");
    no.type = "button";
    no.className = "cancel";
    no.textContent = "Cancel";
    no.addEventListener("click", function () { f.parentNode.removeChild(f); });
    row.appendChild(go);
    row.appendChild(no);
    f.appendChild(row);
    f.addEventListener("submit", function (e) {
      e.preventDefault();
      var vals = {};
      fields.forEach(function (fd) { vals[fd.k] = f.elements[fd.k].value; });
      onSubmit(vals, f);
    });
    host.appendChild(f);
    var first = f.querySelector("input");
    if (first) first.focus();
  }

  function reload() { setTimeout(function () { location.reload(); }, 1400); }

  document.addEventListener("click", function (e) {
    var b = e.target.closest("button.go");
    if (!b || b.closest("form.ask")) return;
    var a;
    try { a = JSON.parse(b.dataset.act); } catch (err) { return; }
    var host = b.parentNode;
    var out = box(host);

    // Show the difference, then ask. The signature is on something seen.
    if (a.ask === "diff") {
      post({ action: "review-changes", slug: a.slug }, out, b, function (j) {
        // Not ok means at least one change has no decision behind it. That is
        // not something to confirm past, so no confirm button is offered.
        if (!j.ok) return;
        form(host, [], "Every change is accounted for \\u2014 confirm", function () {
          post({ action: "confirm-review", slug: a.slug }, out, b,
               function (k) { if (k.ok) reload(); });
        });
      });
      return;
    }

    var fields = a.ask === "announce" ? announceFields(a.subject)
               : a.ask === "confirm" ? confirmFields(a.action)
               : (FIELDS[a.ask] || []);
    if (a.prefill && fields.length === 1) {
      fields = [{ k: fields[0].k, label: fields[0].label, value: a.prefill }];
    }
    if (!fields.length) {
      post(a, out, b, function (j) { if (j.ok) reload(); });
      return;
    }
    form(host, fields, a.label, function (v) {
      var payload = {};
      for (var k in a) { if (a.hasOwnProperty(k)) payload[k] = a[k]; }
      for (var k2 in v) { if (v.hasOwnProperty(k2)) payload[k2] = v[k2]; }
      post(payload, out, b, function (j) { if (j.ok) reload(); });
    });
  });
})();
</script>
"""


def cmd_dashboard(args) -> int:
    html = _dashboard_html(interactive=False)
    DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(html, encoding="utf-8")

    if args.web:
        ADMIN_ROUTE.parent.mkdir(parents=True, exist_ok=True)
        ADMIN_ROUTE.write_text(ADMIN_JS % {"board": json.dumps(html)}, encoding="utf-8")
        print()
        print("  %s" % ADMIN_ROUTE.relative_to(ROOT))
        print("  -> https://whatholdsup.org/api/admin, behind ADMIN_PASSWORD")
    print()
    print("  %s" % DASHBOARD)
    print()
    print("  Regenerate any time; it reads live state. The copy under backend/data")
    print("  is local. The copy at /api/admin is served, behind ADMIN_PASSWORD, and")
    print("  is a snapshot — it is only as current as the last --web run.")
    print()
    return 0


def cmd_dateline(args) -> int:
    """Set the masthead date from this machine's clock.

    A date somebody types is a date somebody can type wrong, and on 2026-08-29
    it was: set to 29 August from a UTC machine while the publisher's own clock
    said the 28th, seven hours and one midnight behind. The preflight caught it,
    which is the system working, but the fix for a field nobody should be typing
    is to stop typing it.

    Run this on the machine that will publish, which is the machine whose day
    the masthead is claiming.
    """
    cfg = ISSUES[args.slug]
    page = ROOT / cfg["page"]
    if not page.exists():
        print("missing: %s" % page)
        return 2
    text = page.read_text(encoding="utf-8")
    was = header_date(text)
    today = pretty(datetime.now().date())
    if was == today:
        print("\n  Already %s. Nothing to change.\n" % today)
        return 0
    if not was:
        print("\n  No dateline found in the masthead to replace. The header needs a")
        print("  <span class=\"meta\"> carrying a date before this can set one.\n")
        return 2
    page.write_text(text.replace(was, today, 1), encoding="utf-8")
    print("\n  %s  ->  %s" % (was, today))
    print("  Set from this machine's clock (%s)."
          % (datetime.now().astimezone().tzname() or "local time"))
    print("  This edit voids any gate acceptance bound to the old bytes, which is")
    print("  correct: re-accept before publishing.\n")
    return 0


def cmd_gate_status(args) -> int:
    """Everything the last gate run says, without spending another one.

    The runs cost money and stopped buying findings some time ago. What they
    already produced had never been read past a boolean. This reads it.
    """
    cfg = ISSUES[args.slug]
    for label, f in (("assessment", ROOT / cfg["page"]), ("email", ROOT / cfg["email_html"])):
        g = gate_state(f, args.slug)
        print()
        print("  %s  %s" % (label.upper(), f.name))
        print("  %s" % ("-" * (len(label) + len(f.name) + 2)))
        print("    state      %s" % {OK: "ok", WARN: "warn", BAD: "STOP"}[g["state"]])
        print("    %s" % g["detail"])
        if g["exists"]:
            print("    report sha %s" % (g.get("recorded_sha") or "?")[:16])
            print("    file sha   %s%s" % (g.get("current_sha", "?")[:16],
                                           "" if g["fresh"] else "   <- differs"))
        for tone, group in (("open", g["outstanding"]), ("done", g["resolved"])):
            for x in group:
                print()
                print("    [%s] %s %s -- %s"
                      % (tone, x["class"], x["id"], WHERE.get(x["where"], x["where"])))
                q = (x["quote"] or "").strip().replace("\n", " ")
                if q:
                    print("      quote  %s" % q[:150])
                if x["why"]:
                    print("      why    %s" % x["why"].strip()[:220])
                for cls, why in x["flags"]:
                    print("      DEFECT %s -- %s" % (cls, why[:150]))
        if g["calibration"]:
            print()
            print("    %d calibration note(s) -- recorded, published, never blocking"
                  % g["calibration"])
        for n in g["notes"]:
            print("    !! %s" % n)
    print()
    return 0


def cmd_accept_gate(args) -> int:
    """Record a decision to proceed on a stale gate whose findings are all gone.

    Not a pass and not a waiver. A waiver publishes past a check that failed;
    this is the narrower case where the check failed against text that no longer
    exists and every finding it raised has been verified out of the file. It is
    bound to the sha, so the next edit voids it, and it carries a name and a
    reason because an acceptance nobody signed is just a default with paperwork.
    """
    cfg = ISSUES[args.slug]
    f = ROOT / (cfg["page"] if args.file == "assessment" else cfg["email_html"])
    g = gate_state(f, args.slug)
    if not g["exists"]:
        print("\n  %s has never been gated. Accepting nothing is not a decision.\n" % f.name)
        return 2
    if g["fresh"]:
        print("\n  The report already describes this exact text. Nothing to accept:")
        print("  %s\n" % g["detail"])
        return 2
    # A signature settles a finding somebody read. It cannot settle a sentence
    # nobody has read. Issue two's stale run had every finding resolved AND 28
    # unjudged claims added afterwards; accepting it would have recorded a
    # human decision about text no human or role had seen, which is worse than
    # no record at all because it looks like diligence.
    if g.get("unjudged"):
        print("\n  This page carries text the gate never saw, so there is nothing here")
        print("  a signature can settle:")
        for u in g["unjudged"]:
            print("    %s" % u[:300])
        print("\n  Re-gate it. accept-gate is for findings that were read and decided,")
        print("  not for sentences nobody has read.\n")
        return 2

    named = {t.strip() for t in (args.despite or "").split(",") if t.strip()}
    open_ids = {x["id"] for x in g["outstanding"]}
    unnamed = open_ids - named
    if unnamed:
        print("\n  %d finding(s) from that run are not resolved in the current text."
              % len(g["outstanding"]))
        print("  Fix them, re-run the gate, or name each one you are accepting past")
        print("  with --despite. Naming them is the point: a blanket override records")
        print("  a decision without recording what was decided.\n")
        for x in g["outstanding"]:
            mark = "named" if x["id"] in named else "     "
            print("    [%s] %-4s %-14s %s -- %s"
                  % (mark, x["id"], x["class"], WHERE.get(x["where"], ""),
                     (x["why"] or x["quote"] or "")[:100]))
        print()
        print("    --despite %s" % ",".join(sorted(open_ids)))
        print()
        return 2
    stray = named - open_ids
    if stray:
        print("\n  --despite names %s, which is not open on this run. Check the ids"
              % ", ".join(sorted(stray)))
        print("  with gate-status before accepting past anything.\n")
        return 2
    # What is being accepted is a fact about the run, and the tool knows it.
    # Making a person compose that sentence was making them attest to a
    # reconciliation only the tool had performed. They can still overwrite it.
    auto = ("%d finding(s) from the %s run: %d verified gone from the text, "
            "%d already decided in draft_decisions.json%s"
            % (len(g["blocking"]), g.get("checked_at", "?"), len(g["resolved"]),
               len(g["settled"]),
               "; " + ", ".join(sorted(named)) + " accepted past" if named else ""))
    reason = (args.reason or "").strip() or auto
    fp = acceptance_file(args.slug)
    if fp is None:
        print("\n  no case directory for %s\n" % args.slug)
        return 2
    rows = []
    if fp.exists():
        try:
            rows = json.loads(fp.read_text()).get("acceptances", [])
        except Exception:
            rows = []
    rows.append({
        "file": f.name,
        "sha": g["current_sha"],
        "gate_report_sha": g.get("recorded_sha", ""),
        "gate_checked_at": g.get("checked_at", ""),
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "by": args.by,
        "reason": reason,
        "findings_in_that_run": len(g["blocking"]),
        "verified_gone": len(g["resolved"]),
        "accepted_despite": sorted(named),
    })
    fp.write_text(json.dumps({
        "what_this_is": "Decisions to proceed on a gate run that judged an earlier "
                        "version of the file, taken only where every blocking finding "
                        "from that run was verified absent from the current text. Bound "
                        "to the content hash, so the next edit voids the acceptance.",
        "acceptances": rows,
    }, indent=2), encoding="utf-8")
    print("\n  Accepted: %s, %d finding(s) from the %s run, %d verified gone%s."
          % (f.name, len(g["blocking"]), g.get("checked_at", "?"), len(g["resolved"]),
             ", %d accepted past: %s" % (len(named), ", ".join(sorted(named))) if named else ""))
    print("  Bound to sha %s. Any edit to the file voids it.\n" % g["current_sha"][:16])
    return 0


# ---------------------------------------------------------------------------
# the board, served from this machine, with the buttons wired up
#
# The copy at /api/admin is a function in Vercel's cloud. It has no repo, no
# git and no python, so a button there cannot accept a gate or publish an
# issue — it can only show what was true when it was generated. That is worth
# having for reading from a phone, and it is the wrong place to work.
#
# This runs where the work already is. Every button calls the same function
# the CLI calls, the page is regenerated on every request rather than baked in,
# and it binds to the loopback address only: no port is open to the network,
# and nothing but this machine can reach it.
# ---------------------------------------------------------------------------

def _run_action(payload: dict) -> tuple[bool, str]:
    """Call the same command function the CLI would, and capture what it says.

    One map, one place. If a button and a command could diverge, they would,
    and the first anyone would know is a board reporting something that did not
    happen.
    """
    import contextlib
    import io
    from argparse import Namespace

    kind = payload.get("action")
    slug = payload.get("slug")
    if slug not in ISSUES:
        return False, "unknown issue: %r" % slug

    if kind == "accept-gate":
        args = Namespace(slug=slug, file=payload.get("file"),
                         reason=(payload.get("reason") or "").strip(),
                         by=payload.get("by") or os.environ.get("USER") or "operator",
                         despite=payload.get("despite"))
        fn = cmd_accept_gate
    elif kind == "send-for-review":
        args, fn = Namespace(slug=slug), cmd_send_for_review
    elif kind == "explain-change":
        args = Namespace(slug=slug, was=payload.get("was") or "",
                         now=payload.get("now") or "",
                         because=payload.get("because") or "AD-HOC",
                         note=payload.get("note") or "",
                         by=payload.get("by") or os.environ.get("USER") or "operator")
        fn = cmd_explain_change
    elif kind == "review-changes":
        args, fn = Namespace(slug=slug), cmd_review_changes
    elif kind == "confirm-review":
        reason = (payload.get("reason") or "").strip()
        args = Namespace(slug=slug, reason=reason,
                         by=payload.get("by") or os.environ.get("USER") or "operator")
        fn = cmd_confirm_review
    elif kind == "review":
        try:
            findings = int(payload.get("findings"))
            accepted = int(payload.get("accepted"))
        except (TypeError, ValueError):
            return False, "findings and accepted must both be numbers"
        args = Namespace(slug=slug, reviewer=(payload.get("reviewer") or "").strip(),
                         findings=findings, accepted=accepted,
                         note=payload.get("note") or "",
                         reviewed=(payload.get("reviewed") or "").strip() or None)
        if not args.reviewer:
            return False, "who reviewed it?"
        fn = cmd_review
    elif kind in ("publish", "announce"):
        if kind == "announce" and not (payload.get("subject") or "").strip():
            return False, "a subject line is required"
        # Irreversible. The CLI makes you type --yes; this makes you type the
        # word. Neither is a real safeguard against a determined mistake, and
        # both are enough to stop an absent-minded click.
        if (payload.get("confirm") or "").strip().upper() != kind.upper():
            return False, "not confirmed"
        args = Namespace(slug=slug, yes=True, waive=payload.get("waive") or None,
                         subject=payload.get("subject"))
        fn = cmd_publish if kind == "publish" else cmd_announce
    elif kind == "gate-status":
        args, fn = Namespace(slug=slug), cmd_gate_status
    elif kind == "check":
        args, fn = Namespace(slug=slug, yes=False, waive=None), cmd_check
    else:
        return False, "unknown action: %r" % kind

    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = fn(args)
    except Exception as exc:                    # a traceback in a browser is
        return False, "%s\n\n%s: %s" % (buf.getvalue(), type(exc).__name__, exc)
    return code == 0, buf.getvalue().strip() or "done"


def cmd_board(args) -> int:
    import http.server
    import socketserver
    import webbrowser

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def _send(self, code, body, ctype):
            b = body if isinstance(body, bytes) else body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path.split("?")[0] not in ("/", "/index.html"):
                self._send(404, "no", "text/plain; charset=utf-8")
                return
            # Regenerated per request. The served copy is a snapshot because a
            # serverless function cannot read the repo; this one can, so it is
            # never stale and never needs regenerating by hand.
            self._send(200, _dashboard_html(interactive=True), "text/html; charset=utf-8")

        def do_POST(self):
            if self.path != "/do":
                self._send(404, "no", "text/plain; charset=utf-8")
                return
            n = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(n) or b"{}")
            except Exception as exc:
                self._send(400, json.dumps({"ok": False, "output": str(exc)}),
                           "application/json")
                return
            ok, out = _run_action(payload)
            self._send(200, json.dumps({"ok": ok, "output": out}), "application/json")

    socketserver.TCPServer.allow_reuse_address = True
    # Walk up until something is free. Handing back an error and a port number
    # to type is the tool making its problem into the operator's problem, and
    # the whole point of the board is to stop doing that.
    srv, port, last = None, args.port, None
    for port in range(args.port, args.port + 25):
        try:
            srv = socketserver.TCPServer(("127.0.0.1", port), Handler)
            break
        except OSError as exc:
            last = exc
    if srv is None:
        print("\n  no free port between %d and %d — %s\n"
              % (args.port, args.port + 24, last))
        return 2
    if port != args.port:
        print()
        print("  %d was busy — using %d instead." % (args.port, port))
        print("  If a board is already running there, this is a second one.")
    global SERVER_STARTED
    SERVER_STARTED = datetime.now().strftime("%Y-%m-%d %H:%M")
    url = "http://127.0.0.1:%d/" % port
    print()
    print("  Publication board: %s" % url)
    print("  Loopback only — nothing outside this machine can reach it.")
    print("  Every button runs the same function the CLI runs.")
    print("  Ctrl-C to stop.")
    print()
    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped\n")
    finally:
        srv.server_close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="what is published, and is it still what we meant").set_defaults(fn=cmd_status)
    sub.add_parser("log", help="every publication and send, in order").set_defaults(fn=cmd_log)
    sub.add_parser("register", help="regenerate issue-register.csv from the case files").set_defaults(fn=cmd_register)
    db = sub.add_parser("dashboard", help="write the publication board")
    db.add_argument("--web", action="store_true",
                    help="also regenerate the password-protected route at /api/admin")
    db.set_defaults(fn=cmd_dashboard)
    nx = sub.add_parser("next", help="what is the single next action for this issue")
    nx.add_argument("slug", choices=sorted(ISSUES))
    nx.set_defaults(fn=cmd_next)
    rn = sub.add_parser("run", help="walk the chain, stopping before anything irreversible")
    rn.add_argument("slug", choices=sorted(ISSUES))
    rn.add_argument("--yes", action="store_true", help="let it spend API calls on gate runs")
    rn.set_defaults(fn=cmd_run)
    rn.set_defaults(fn=cmd_run)
    sfr = sub.add_parser("send-for-review",
                         help="snapshot the assessment and prepare the adjudication file")
    sfr.add_argument("slug", choices=sorted(ISSUES))
    sfr.set_defaults(fn=cmd_send_for_review)

    r = sub.add_parser("review", help="record an outside review and its adjudication")
    r.add_argument("slug", choices=sorted(ISSUES))
    r.add_argument("--reviewer", required=True, help="who or what reviewed it")
    r.add_argument("--findings", type=int, required=True, help="how many findings it returned")
    r.add_argument("--accepted", type=int, required=True, help="how many we acted on")
    r.add_argument("--note", help="one line on what the review changed")
    r.add_argument("--reviewed", metavar="SNAPSHOT",
                   help="the -sent.html the reviewer actually read, when the page has "
                        "changed since — which it will have if you acted on anything "
                        "they found. Both hashes are recorded.")
    r.set_defaults(fn=cmd_review)

    for name, fn, helptext in (("check", cmd_check, "run the preflight and stop"),
                               ("publish", cmd_publish, "preflight, push, wait for live, record"),
                               ("announce", cmd_announce, "preflight the email and record the send")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("slug", choices=sorted(ISSUES))
        p.add_argument("--yes", action="store_true", help="actually do it")
        if name == "announce":
            p.add_argument("--subject",
                           help="subject line; defaults to the issue's configured one")
            p.add_argument("--dry-run", action="store_true",
                           help="run every check the sender runs and stop; sends nothing")
        p.add_argument("--waive", metavar="REASON",
                       help="Publish despite blocking preflight items. Requires a reason, "
                            "which is written into the publication record beside what was "
                            "waived. Use it when a check has stopped buying anything, not "
                            "when it is inconvenient.")
        p.set_defaults(fn=fn)
    up = sub.add_parser("update",
                        help="record a substantive change to a LIVING issue")
    up.add_argument("slug", choices=sorted(ISSUES))
    up.add_argument("--what", help="what appeared in the world")
    up.add_argument("--changed", help="what changed on the page")
    up.add_argument("--source", help="the new source's id in sources.json")
    up.add_argument("--yes", action="store_true", help="actually do it")
    up.add_argument("--waive", metavar="REASON",
                    help="update despite a blocking item. Recorded, with the reason.")
    up.set_defaults(fn=cmd_update)
    rl = sub.add_parser("record-live",
                        help="sign off a small change to an already-published page")
    rl.add_argument("slug", choices=sorted(ISSUES))
    rl.add_argument("--reason", help="what changed and why it is not a change to the argument")
    rl.add_argument("--yes", action="store_true", help="actually record it")
    rl.set_defaults(fn=cmd_record_live)
    bd = sub.add_parser("board",
                        help="serve the board on this machine with the buttons live")
    bd.add_argument("--port", type=int, default=8787)
    bd.add_argument("--no-open", action="store_true", help="do not open a browser")
    bd.set_defaults(fn=cmd_board)

    rc = sub.add_parser("review-changes",
                        help="show what changed in the prose since the reviewer read it")
    rc.add_argument("slug", choices=sorted(ISSUES))
    rc.set_defaults(fn=cmd_review_changes)

    ec = sub.add_parser("explain-change",
                        help="record why a change was made that nothing on file explains")
    ec.add_argument("slug", choices=sorted(ISSUES))
    ec.add_argument("--was", default="")
    ec.add_argument("--now", default="")
    ec.add_argument("--because", default="AD-HOC")
    ec.add_argument("--note", required=True)
    ec.add_argument("--by", default=os.environ.get("USER") or "operator")
    ec.set_defaults(fn=cmd_explain_change)

    cr = sub.add_parser("confirm-review",
                        help="record that the changes since a review were the ones it asked for")
    cr.add_argument("slug", choices=sorted(ISSUES))
    cr.add_argument("--reason", help="optional; the reconciliation is recorded either way")
    cr.add_argument("--by", default=os.environ.get("USER") or "operator")
    cr.set_defaults(fn=cmd_confirm_review)

    dl = sub.add_parser("dateline",
                        help="set the masthead date from this machine's clock")
    dl.add_argument("slug", choices=sorted(ISSUES))
    dl.set_defaults(fn=cmd_dateline)

    gs = sub.add_parser("gate-status",
                        help="read what the last gate run found, without running one")
    gs.add_argument("slug", choices=sorted(ISSUES))
    gs.set_defaults(fn=cmd_gate_status)

    ag = sub.add_parser("accept-gate",
                        help="record a decision to proceed on a stale gate whose "
                             "findings are all verified gone from the current text")
    ag.add_argument("slug", choices=sorted(ISSUES))
    ag.add_argument("--file", choices=("assessment", "email"), required=True)
    ag.add_argument("--reason",
                    help="optional; defaults to what the run actually found")
    ag.add_argument("--by", default=os.environ.get("USER") or "operator",
                    help="who is deciding")
    ag.add_argument("--despite", metavar="IDS",
                    help="comma-separated finding ids being accepted past, from "
                         "gate-status. Each must be dispositioned somewhere a reader "
                         "can find it: the adjudication file, or draft_decisions.json.")
    ag.set_defaults(fn=cmd_accept_gate)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
