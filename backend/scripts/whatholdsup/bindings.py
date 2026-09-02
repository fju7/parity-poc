#!/usr/bin/env python3
"""The binding store — which words in which document support this sentence.

WHY
---
Every control in this repository is about a DOCUMENT: is it held, what kind is
it, was it read, does the ledger overstate it. None is about a SENTENCE. So
nothing anywhere records the only thing that would make verification complete,
deterministic, cheap and repeatable:

    this sentence rests on this source, at this locator, supported by
    these exact words.

Spec: docs/whatholdsup-claim-bindings-spec.md. This module is step 2 of its
build order — the store, and B1, the check that every empirical sentence has a
row. The span checks (B2, B3, B5, B6) come next and all of them need this.

WHAT B1 ALONE IS WORTH
----------------------
On 2026-09-01 the published page carried eight figures from a reconstructed
patient-data comparison that had its own entry in the visible source list and
NO entry in sources.json. No id, no access record, nothing in the library, no
row in the twenty-five sources we publish as our count. It was invisible to the
ledger, the quotation check, the gap list and preflight, because every one of
those starts from the source list and it was not in the source list.

B1 starts from the PAGE. A sentence carrying a figure, a trial name, a registry
id or a quotation, with no binding row, is a defect — whether or not anybody
remembered to write the source down.

R1 FROM THE SPEC, RESTATED HERE BECAUSE IT GOVERNS THIS FILE
-----------------------------------------------------------
This layer may assert only the presence or absence of a span. It may never
assert that a sentence is true. It reports what it can observe and hands the
resolution to a person: a block is a question, not a verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store      # noqa: E402
import source_ledger as ledger    # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

BUCKETS = ("deterministic", "context", "judgement", "figure")
QUESTIONS = ("locatable", "faithful", "warranted")


# ---------------------------------------------------------------------------
# which sentences must be bound
# ---------------------------------------------------------------------------

FIGURE = re.compile(r"\b\d+\.\d+\b|\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s?%")
NCT = re.compile(r"\bNCT\d{8}\b")
DOI = re.compile(r"\b10\.\d{4,9}/\S+")
QUOTED = re.compile(r"[“\"][^”\"]{25,}[”\"]")


def trial_names(srcs: list[dict]) -> set[str]:
    names = set()
    for s in srcs:
        for n in (s.get("also_called") or []):
            if len(n) > 3:
                names.add(n)
    return names


def is_empirical(sent: str, names: set[str]) -> tuple[bool, str]:
    """(must_be_bound, why). The why is printed, so a person can disagree with
    the classifier rather than guess at it."""
    if NCT.search(sent):
        return True, "registry identifier"
    if DOI.search(sent):
        return True, "DOI"
    if QUOTED.search(sent):
        return True, "quoted passage"
    if FIGURE.search(sent):
        return True, "figure"
    hit = next((n for n in names if re.search(r"\b%s\b" % re.escape(n), sent)), None)
    if hit:
        return True, "names %s" % hit
    return False, ""


# Page furniture is not a claim.
#
# The pages carry no <main> or <article>, so sentence extraction was taking the
# whole document — and the first "empirical sentence" needing a binding was the
# site navigation: "The Category Difference — What Holds Up What Holds Up What
# this is Issue one Issue two Who pays for this". It contains digits and proper
# nouns, so it looked empirical to a check counting digits and proper nouns.
#
# Every denominator this file has reported was inflated by it. Removing the nav,
# header and footer is not cosmetic: it changes what "141 sentences rest on
# nothing" means, and a number that is wrong in our favour is worse than one
# that is merely large.
FURNITURE = re.compile(r"<(nav|header|footer|aside)\b[^>]*>.*?</\1>",
                       re.S | re.I)


def page_sentences(slug: str) -> list[str]:
    html = ledger.page_text(slug) if hasattr(ledger, "page_text") else None
    if html is None:
        html = _page_html(slug)
    html = FURNITURE.sub(" ", html)
    return [" ".join(s.split()) for s in ledger.sentences(ledger.plain(html))]


def _page_html(slug: str) -> str:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pub", str(Path(__file__).resolve().parent / "publish.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    cfg = m.ISSUES[slug]
    return (m.ROOT / cfg["page"]).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# the store
# ---------------------------------------------------------------------------

def fingerprint(sent: str) -> str:
    return hashlib.sha256(" ".join(sent.split()).encode("utf-8")).hexdigest()[:16]


def path(slug: str) -> Path:
    return store.case_dir(slug) / "bindings.json"


def load(slug: str) -> dict:
    p = path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "_what_this_is":
            "One row per empirical sentence on the page: the source it rests "
            "on, the exact words in that source that support it, and who "
            "signed for each of the three questions. Spec: "
            "docs/whatholdsup-claim-bindings-spec.md.",
        "_r1":
            "This file records the presence or absence of a span. It does not "
            "record that a sentence is true. A row with every verdict signed "
            "means the sentence is WARRANTED by named evidence and named "
            "signers -- which is not the same claim and must never be printed "
            "as though it were.",
        "bindings": {},
    }


def save(slug: str, doc: dict) -> None:
    path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def blank_row(sent: str, why: str) -> dict:
    return {
        "sentence": sent[:600],
        "sentence_sha": fingerprint(sent),
        "why_empirical": why,
        "bucket": None,          # declared by whoever writes the sentence
        "source_id": None,
        "document_sha": None,
        "locator_type": None,    # prose | table | field | figure | none
        "locator": None,
        "span": None,
        "envelope": None,
        "scope_words": [],
        "falsifier": None,       # what would show this sentence wrong
        "verdicts": {q: None for q in QUESTIONS},
        "first_seen": date.today().isoformat(),
    }


def scan(slug: str) -> tuple[dict, list[str], list[str]]:
    """(doc, unbound, stale). Adds a blank row for every empirical sentence
    that has none; never deletes, because a sentence that has left the page is
    evidence about a correction and belongs in the record."""
    doc = load(slug)
    rows = doc.setdefault("bindings", {})
    names = trial_names(store.sources(slug))
    live, unbound = set(), []
    for sent in page_sentences(slug):
        must, why = is_empirical(sent, names)
        if not must:
            continue
        sha = fingerprint(sent)
        live.add(sha)
        if sha not in rows:
            rows[sha] = blank_row(sent, why)
        rows[sha]["on_page"] = True
        if not rows[sha].get("span"):
            unbound.append(sha)
    stale = []
    for sha, row in rows.items():
        if sha not in live:
            row["on_page"] = False
            row["left_page"] = row.get("left_page") or date.today().isoformat()
            stale.append(sha)
    save(slug, doc)
    return doc, unbound, stale


# ---------------------------------------------------------------------------
# running the checks FROM the binding, never from a caller's choice
# ---------------------------------------------------------------------------

def run_checks(slug: str, *, only: str = "") -> dict:
    """Run every span check against the source THE ROW NAMES.

    WHY THIS IS THE ONLY SANCTIONED WAY TO CALL THEM.

    On 2026-09-01 B12 was run against a document that happened to be in the
    library rather than the one the sentence cites, and reported two correct
    sentences on a live page as errors: "we print 0.510, the source says 0.51".
    The page cites the Journal of Clinical Oncology five-year paper, which
    prints 0.510. What prints 0.51 is a company press release the page does not
    cite. The check was right about the document it was given and the document
    it was given was the wrong one.

    Every span check takes a source id. Whoever supplies it can be wrong, and
    was. The binding row is the answer to "which document does this sentence
    rest on", recorded once, reviewable, and not re-decided at each call site.

    A caller reaching past this into b2_present or b12_precision directly is
    asserting provenance it has to be able to defend. The canary does, because
    it asks about a document rather than about a sentence. Preflight does not,
    and uses this.
    """
    import spancheck as SC
    doc = load(slug)
    rows = doc.get("bindings") or {}
    tally = {"checked": 0, "flags": 0, "undetermined": 0}
    for sha, row in rows.items():
        if only and sha != only:
            continue
        if not row.get("on_page") or not row.get("span") or not row.get("source_id"):
            continue
        sid, span, sent = row["source_id"], row["span"], row["sentence"]
        found = []
        tally["checked"] += 1

        present, why = SC.b2_present(span, slug, sid)
        if present is SC.UNDETERMINED:
            tally["undetermined"] += 1
            found.append({"check": "B2", "verdict": "undetermined", "why": why})
        elif present is not True:
            other, why2 = SC.b3_elsewhere(span, slug, sid)
            found.append({"check": "B2/B3", "verdict": "absent",
                          "why": "%s; %s" % (why, why2)})
        else:
            ok5, why5 = SC.b5_complete(span, slug, sid)
            if not ok5:
                found.append({"check": "B5", "verdict": "truncated", "why": why5})
            # A SCOPE WORD MAY BE DISPOSED OF, BY A PERSON, IN THE ROW.
            #
            # "Of the study it is actually announcing it says only that the
            # endpoints were met ... No hazard ratio, no interval, no p-value,
            # no percentage" is an absence claim about a WHOLE DOCUMENT. No span
            # can carry "only", so B6 is right that nothing maps and will be
            # right forever. Left alone it becomes the flag the operator learns
            # to scroll past, which is how a check stops working.
            #
            # So the row may carry a disposition: the word, why it is not a
            # claim the span is meant to bear, WHAT WOULD SHOW IT WRONG, and who
            # signed. Same discipline as b13's declared exclusions -- a
            # signature, not a filter. A disposition with no falsifier or no
            # signer does not count, and one whose word is no longer in the
            # sentence is itself a flag.
            disposed = {}
            for d in (row.get("scope_words") or []):
                if isinstance(d, dict) and d.get("word") and \
                        (d.get("falsifier") or "").strip() and \
                        (d.get("by") or "").strip():
                    disposed[d["word"]] = d
            for w, why6 in SC.b6_scope(sent, span):
                if w in disposed:
                    continue
                found.append({"check": "B6", "verdict": "unmapped scope word",
                              "why": "%s — %s" % (w, why6)})
            live_words = {w for w, _ in SC.b6_scope(sent, "")}
            for w, d in disposed.items():
                if w not in live_words:
                    found.append({
                        "check": "B6", "verdict": "stale disposition",
                        "why": "%r is disposed of in this row and is no longer a "
                               "scope word in the sentence; a disposition that "
                               "outlives its word is a filter" % w})
            import autobind as AB
            for a in AB.anchors_of(sent):
                ok12, why12 = SC.b12_precision(a, slug, sid)
                if not ok12:
                    found.append({"check": "B12", "verdict": "added precision",
                                  "why": why12})
        row["check_flags"] = found
        row["checked_on"] = date.today().isoformat()
        tally["flags"] += len(found)
    save(slug, doc)
    return tally


# ---------------------------------------------------------------------------
# B1
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# THE WRITING RULE
# ---------------------------------------------------------------------------
#
# Adopted 2026-09-02, by the editor, after two page-gate runs produced eleven
# findings that were right:
#
#   1. NO FACTUAL STATEMENT THAT IS NOT BASED ON A DOCUMENT WE HAVE AND HAVE
#      FULLY READ.
#   2. EVERY INFERENCE FLAGGED, WITH THE LOGIC AND THE FACTS THAT SUPPORT IT.
#
# Ten of the eleven would have been prevented by those two sentences. The
# eleventh -- a subheading contradicting the paragraph beneath it -- is a
# relation between two things we wrote, which no sourcing rule can reach; that
# is B16's contradiction question.
#
# WHY THIS IS IN CODE AND NOT IN A DOCUMENT
#
# Both rules were ALREADY in this repository. `bucket` has been a field on every
# binding row since the row was designed, and it is null on all eighty sentences
# of issue one. "Empirical sentences bound" has been a WARN reporting 20 of 80.
# The spec's deletion rule, the "write the correction from the source record"
# rule, and undefined_states were the same: written down, gating nothing, and
# each one was followed by the error it described.
#
# A rule that does not block is a rule that will be broken by whoever is tired.
#
# GRANDFATHERING, AND WHY IT IS A LIST AND NOT A DATE
#
# Sixty sentences on issue one predate the rule. Blocking them all today would
# stop the issue and teach the operator to waive the check, which is how a
# control dies. They are marked, once, by `predates_the_rule`. The mark cannot
# be earned by a new sentence -- a date could be, by a row written with an old
# first_seen -- and the count only ever shrinks, printed on every run so the
# debt is visible rather than absorbed.

RULE_ADOPTED = "2026-09-02"


def mark_grandfathered(slug: str, ref: str) -> int:
    """Mark the sentences that were on the page before the rule was adopted.

    NOT "everything unbound today". The first version of this function marked
    every on-page row, and it excused a sentence written that same afternoon --
    one of the two the gate had never examined. A waiver drawn to fit whatever
    is in front of it is not a waiver, it is an off switch.

    So the mark is drawn from evidence outside this file: `ref` is a git
    revision of the page from before RULE_ADOPTED, and a sentence is
    grandfathered if and only if its exact text was on that page. A sentence
    rewritten today is new writing and is held to the rule, which is the point
    -- sentences written while correcting other sentences are where this
    project's errors have actually come from.

    Once only. The recorded ref is the guard: a second pass would draw a new
    line around whatever had since been written.
    """
    doc = load(slug)
    if doc.get("_grandfathered_from"):
        raise RuntimeError(
            "%s was grandfathered on %s from %s already. Running this again "
            "would excuse every sentence written since. Bind or bucket the new "
            "sentence instead." % (slug, RULE_ADOPTED,
                                   doc["_grandfathered_from"]))
    before = _sentences_at(slug, ref)
    n = 0
    for row in (doc.get("bindings") or {}).values():
        if row.get("on_page") and fingerprint(row["sentence"]) in before:
            row["predates_the_rule"] = RULE_ADOPTED
            n += 1
    doc["_grandfathered_from"] = ref
    doc["_grandfathered_note"] = (
        "%d sentence(s) on the page at %s are not held to the two writing "
        "rules adopted %s. Every sentence written or rewritten since is."
        % (n, ref, RULE_ADOPTED))
    save(slug, doc)
    return n


def _sentences_at(slug: str, ref: str) -> set[str]:
    """Fingerprints of every sentence on the page as of a git revision."""
    import subprocess
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pub", str(Path(__file__).resolve().parent / "publish.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    rel = m.ISSUES[slug]["page"]
    html = subprocess.run(["git", "show", "%s:%s" % (ref, rel)],
                          cwd=str(m.ROOT), capture_output=True, text=True,
                          check=True).stdout
    html = FURNITURE.sub(" ", html)
    return {fingerprint(" ".join(s.split()))
            for s in ledger.sentences(ledger.plain(html))}


def rule_rows(slug: str) -> list[tuple[str, str, str]]:
    """The two rules, as blocking rows."""
    import spancheck as SC
    doc = load(slug)
    rows = doc.get("bindings") or {}
    on_page = {k: v for k, v in rows.items() if v.get("on_page")}
    old = {k for k, v in on_page.items() if v.get("predates_the_rule")}
    new = {k: v for k, v in on_page.items() if k not in old}

    unbound = [k for k, v in new.items() if not v.get("span")]
    out = [("rule 1 — written from a document we hold",
            OK if not unbound else BAD,
            "every sentence written since %s names the words it rests on"
            % RULE_ADOPTED if not unbound else
            "%d sentence(s) written since %s rest on nothing: %s"
            % (len(unbound), RULE_ADOPTED,
               " || ".join(on_page[k]["sentence"][:60] for k in unbound[:3])))]

    unbucketed = [k for k, v in new.items() if not v.get("bucket")]
    bad_inf = []
    for k, v in new.items():
        if (v.get("bucket") or "") != "inference":
            continue
        prem = v.get("premises") or []
        if not prem:
            bad_inf.append("%s: an inference with no premises" % k[:8])
            continue
        for pr in prem:
            sid, span = pr.get("source_id"), pr.get("span") or ""
            if not sid or not span:
                bad_inf.append("%s: a premise with no source or no span" % k[:8])
                continue
            present, why = SC.b2_present(span, slug, sid)
            if present is not True:
                bad_inf.append("%s: a premise whose span is not in %s"
                               % (k[:8], sid))
        if not (v.get("step") or "").strip():
            bad_inf.append("%s: an inference with no step written out" % k[:8])
    out.append(("rule 2 — inferences flagged and shown",
                OK if not (unbucketed or bad_inf) else BAD,
                "every sentence written since %s declares its kind, and every "
                "inference shows its premises" % RULE_ADOPTED
                if not (unbucketed or bad_inf) else
                "%d undeclared, %d inference problem(s): %s"
                % (len(unbucketed), len(bad_inf),
                   " || ".join((bad_inf + [on_page[k]["sentence"][:50]
                                           for k in unbucketed])[:3]))))
    debt = [k for k in old
            if not on_page[k].get("span") or not on_page[k].get("bucket")]
    if debt:
        out.append(("sentences that predate the rule", WARN,
                    "%d of %d sentence(s) written before %s would fail one of "
                    "the two rules and are not held to them. This number can "
                    "only go down: binding or bucketing one removes it, and "
                    "nothing written from now on can enter it."
                    % (len(debt), len(on_page), RULE_ADOPTED)))
    return out


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    try:
        doc = load(slug)
    except Exception as exc:
        return [("claim bindings", WARN, "could not read bindings.json: %s" % exc)]
    rows = doc.get("bindings") or {}
    if not rows:
        return [("claim bindings", WARN,
                 "no bindings recorded — run bindings.py %s scan. Until then no "
                 "sentence on this page names the words it rests on." % slug)]
    on_page = {k: v for k, v in rows.items() if v.get("on_page")}
    bound = [k for k, v in on_page.items() if v.get("span")]
    unbucketed = [k for k, v in on_page.items() if not v.get("bucket")]
    out = [("empirical sentences bound",
            OK if len(bound) == len(on_page) else WARN,
            "all %d empirical sentence(s) name the words they rest on"
            % len(on_page) if len(bound) == len(on_page) else
            "%d of %d empirical sentence(s) are bound to a span; %d rest on "
            "nothing this system can name"
            % (len(bound), len(on_page), len(on_page) - len(bound)))]
    out.extend(rule_rows(slug))
    flagged = [k for k, v in on_page.items() if v.get("check_flags")]
    checked = [k for k, v in on_page.items() if v.get("checked_on")]
    if checked:
        out.append(("bound sentences the span checks flagged",
                    OK if not flagged else BAD,
                    "none of the %d bound sentence(s) is flagged" % len(checked)
                    if not flagged else
                    "%d of %d bound sentence(s) carry a flag: %s"
                    % (len(flagged), len(checked),
                       " || ".join("%s %s" % (f["check"], f["verdict"])
                                   for k in flagged[:4]
                                   for f in on_page[k]["check_flags"][:1]))))
    if unbucketed:
        out.append(("sentences with no declared bucket", WARN,
                    "%d of %d — a sentence whose kind nobody declared cannot be "
                    "routed to the process that should check it"
                    % (len(unbucketed), len(on_page))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("scan", help="add a blank row for every unbound empirical sentence")
    u = sub.add_parser("unbound", help="print the sentences that rest on nothing named")
    u.add_argument("--limit", type=int, default=25)
    sub.add_parser("check", help="run the span checks from the bindings")
    sub.add_parser("status")
    args = ap.parse_args()

    if args.cmd == "check":
        t = run_checks(args.slug)
        print("\n  %d bound sentence(s) checked against the source each row "
              "names" % t["checked"])
        print("  %d flag(s), %d undetermined\n" % (t["flags"], t["undetermined"]))
        doc = load(args.slug)
        for sha, row in (doc.get("bindings") or {}).items():
            # ONLY WHAT IS STILL ON THE PAGE. A row whose sentence has been
            # edited keeps its old flags as history and is no longer a finding;
            # printing them made the header say "0 flags" above two flags.
            if not row.get("on_page"):
                continue
            for f in (row.get("check_flags") or []):
                print("  %-7s %-20s %s" % (f["check"], f["verdict"],
                                           row["sentence"][:78]))
                print("          %s" % f["why"][:130])
        print()
        return 0

    if args.cmd == "scan":
        doc, unbound, stale = scan(args.slug)
        rows = doc["bindings"]
        on_page = sum(1 for v in rows.values() if v.get("on_page"))
        print("\n  %d empirical sentence(s) on the page" % on_page)
        print("  %d bound, %d unbound" % (on_page - len(unbound), len(unbound)))
        if stale:
            print("  %d row(s) for sentences no longer on the page, kept as record"
                  % len(stale))
        print("  written to %s\n" % path(args.slug))
        return 0

    if args.cmd == "unbound":
        doc = load(args.slug)
        rows = [v for v in (doc.get("bindings") or {}).values()
                if v.get("on_page") and not v.get("span")]
        print("\n  %d unbound empirical sentence(s)\n" % len(rows))
        for r in rows[:args.limit]:
            print("  [%s] %s" % (r["why_empirical"], r["sentence"][:150]))
        print()
        return 0

    print()
    for label, state, detail in preflight_rows(args.slug):
        print("  %-6s %-34s %s" % (state, label, detail))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
