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


def page_sentences(slug: str) -> list[str]:
    html = ledger.page_text(slug) if hasattr(ledger, "page_text") else None
    if html is None:
        html = _page_html(slug)
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
            stale.append(sha)
    save(slug, doc)
    return doc, unbound, stale


# ---------------------------------------------------------------------------
# B1
# ---------------------------------------------------------------------------

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
    sub.add_parser("status")
    args = ap.parse_args()

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
