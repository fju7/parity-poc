#!/usr/bin/env python3
"""Omissions: what code decides about a finding the page left out.

Post-study fix 2, step 3 (2026-10-27). docs/whu-fix2-omission-rulings-design.md,
sections 2 and 2.4.

An omission objection (source_advocate type LEAVES_OUT) or an unaccounted
headline conclusion (coverage_check.py) goes to the omission ruling. Before any
model is asked, code decides three things here, and the model never decides
them:

  1. IS THE FINDING IN THE HELD SOURCE. The quotation is located in the held
     text (audit_stage.locate, the comparison every quotation check uses). Not
     found is NOT_IN_SOURCE, decided here, and no model is called. Found, its
     offsets and the held text's sha256 are recorded, and every later step
     quotes from the offsets, never from the advocate's words.
  2. ONE FINDING, ONE RULING. Findings from the same source whose offsets
     overlap are merged before ruling.
  3. A SCOPE ELEMENT IS REAL. An OUT_OF_SCOPE outcome must name words of the
     issue.json question or one of the premise's scope.out entries
     (premise.scope_of). An element that is in neither is refused, and the
     finding goes to a person.

THE RECORDS
-----------
issues/<case>/omissions.json (committed): one entry per decided finding --
source id, held-text sha256, offsets, the quotation's sha256, outcome, the
scope element, the reason in WHU's own words, who decided, the ruling id. NO
SOURCE TEXT: the repository is public and source quotations are never
committed (RUN.md ruling 3). The quoted text goes to rulings/omissions.jsonl,
which is ignored and archived privately.

THE BUDGETS
-----------
At most min(8, 15% of body sentences) ADD sentences, and at most min(10, 20% of
body sentences) declarations shown to readers (OUT_OF_SCOPE and NOT_MATERIAL,
fix 2 ruling 3 of 27 October 2026). Anything past a budget goes to a person,
never off the record.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

ADD, OUT_OF_SCOPE, NOT_MATERIAL, NOT_IN_SOURCE = "ADD", "OUT_OF_SCOPE", "NOT_MATERIAL", "NOT_IN_SOURCE"
OUTCOMES = (ADD, OUT_OF_SCOPE, NOT_MATERIAL, NOT_IN_SOURCE)
TO_PERSON = "TO_PERSON"
RECORD = "omissions.json"
PRIVATE = "omissions.jsonl"          # under rulings/, never committed
ADD_CAP, ADD_SHARE = 8, 0.15
DECLARE_CAP, DECLARE_SHARE = 10, 0.20
MIN_ELEMENT_WORDS = 2


def sha(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def _A():
    import audit_stage as A
    return A


# ---------------------------------------------------------------- 1. in the held source

def locate(quote: str, held_text: str) -> tuple[int, int] | None:
    """(start, end) of QUOTE in HELD_TEXT, by audit_stage.locate; None if absent."""
    if not (quote or "").strip() or not held_text:
        return None
    return _A().locate(quote, held_text)


def precheck(finding: dict, held: dict[str, str]) -> dict:
    """Code's decision on one finding {source, quote, ...}: either an outcome
    NOT_IN_SOURCE, or the finding with its verified offsets ("at") added.
    HELD maps a bare source id to its held text (ruling.held_texts)."""
    text = held.get(finding.get("source") or "") or ""
    if not text:
        return dict(finding, outcome=NOT_IN_SOURCE, why="no held text for %s" % finding.get("source"))
    at = locate(finding.get("quote") or "", text)
    if at is None:
        return dict(finding, outcome=NOT_IN_SOURCE,
                    why="the quotation is not in the held text of %s" % finding.get("source"))
    return dict(finding, at=list(at), held_sha256=sha(text), quote_sha256=sha(text[at[0]:at[1]]),
                held_quote=text[at[0]:at[1]])


# ---------------------------------------------------------------- 2. one finding, one ruling

def merge(findings: list[dict]) -> list[dict]:
    """Located findings from the same source whose offsets overlap become one,
    carrying every origin it merges ("origins") and the widest offsets."""
    out: list[dict] = []
    for f in sorted([f for f in findings if f.get("at")], key=lambda f: (f["source"], f["at"][0])):
        last = out[-1] if out else None
        if last and last["source"] == f["source"] and f["at"][0] < last["at"][1]:
            last["origins"].extend(f.get("origins") or [f.get("origin")])
            last["at"] = [last["at"][0], max(last["at"][1], f["at"][1])]
            continue
        out.append(dict(f, origins=list(f.get("origins") or [f.get("origin")])))
    return out + [f for f in findings if not f.get("at")]


def fill_quotes(findings: list[dict], held: dict[str, str]) -> list[dict]:
    """After merge(): the held quotation and its sha256 from the final offsets."""
    for f in findings:
        if f.get("at"):
            t = held[f["source"]]
            f["held_quote"] = t[f["at"][0]:f["at"][1]]
            f["quote_sha256"] = sha(f["held_quote"])
    return findings


# ---------------------------------------------------------------- 3. a scope element is real

def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[‘’“”\"'.,;:()–—-]", " ", s)
    return " ".join(s.split())


def scope_element_ok(element: str, scope: dict) -> tuple[bool, str]:
    """Is ELEMENT words of the question or of a scope.out entry? SCOPE is
    premise.scope_of(slug). At least MIN_ELEMENT_WORDS words, matched with case,
    punctuation and spacing folded; an ellipsis splits it into parts that must
    each match, in order, in the same place."""
    parts = [p for p in (_fold(x) for x in re.split(r"…|\.\.\.", element or "")) if p]
    if sum(len(p.split()) for p in parts) < MIN_ELEMENT_WORDS:
        return False, "the scope element names fewer than %d words" % MIN_ELEMENT_WORDS
    places = [("the question", scope.get("question") or "")] + \
             [("scope.out: %s" % o.get("what"), "%s %s" % (o.get("what") or "", o.get("why") or ""))
              for o in scope.get("out") or []]
    for name, text in places:
        hay, i = _fold(text), 0
        for p in parts:
            j = hay.find(p, i)
            if j < 0:
                break
            i = j + len(p)
        else:
            return True, "in %s" % name
    return False, "%r is in neither the question nor a scope.out entry" % (element or "")


# ---------------------------------------------------------------- the budgets

def add_budget(n_body: int) -> int:
    return min(ADD_CAP, int(ADD_SHARE * n_body))


def declaration_budget(n_body: int) -> int:
    return min(DECLARE_CAP, int(DECLARE_SHARE * n_body))


# ---------------------------------------------------------------- the records

def record_path(case: Path) -> Path:
    return case / RECORD


def private_path(case: Path) -> Path:
    return case / "rulings" / PRIVATE


def load(case: Path) -> dict:
    p = record_path(case)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"omissions": []}


PUBLIC_FIELDS = ("key", "source", "held_sha256", "at", "quote_sha256", "outcome", "element", "reason",
                 "by", "ruling", "origins", "on_page", "after", "decided_at")


def entry_key(f: dict) -> str:
    return "%s@%s-%s" % (f.get("source"), (f.get("at") or ["", ""])[0], (f.get("at") or ["", ""])[1])


def record(case: Path, f: dict, *, outcome: str, reason: str, by: str, element: str = "",
           ruling: str | None = None, on_page: str | None = None, after: str | None = None) -> dict:
    """Write one decision: the public entry (no source text) to omissions.json,
    the quotation itself to rulings/omissions.jsonl. Returns the public entry."""
    if outcome not in OUTCOMES + (TO_PERSON,):
        raise ValueError("outcome must be one of %s" % ", ".join(OUTCOMES + (TO_PERSON,)))
    e = {"key": entry_key(f), "source": f.get("source"), "held_sha256": f.get("held_sha256"),
         "at": f.get("at"), "quote_sha256": f.get("quote_sha256"), "outcome": outcome,
         "element": element, "reason": reason, "by": by, "ruling": ruling,
         "origins": f.get("origins") or [f.get("origin")], "on_page": on_page, "after": after,
         "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    doc = load(case)
    doc["omissions"] = [x for x in doc.get("omissions") or [] if x.get("key") != e["key"]] + [e]
    record_path(case).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    pp = private_path(case)
    pp.parent.mkdir(parents=True, exist_ok=True)
    with open(pp, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"key": e["key"], "quote": f.get("held_quote") or f.get("quote"),
                             "outcome": outcome, "at": e["decided_at"]}, ensure_ascii=False) + "\n")
    return e


# ---------------------------------------------------------------- the preflight (fix 2, step 9)

ROW = "omission objections ruled"
ADOPTED = "2026-10-27T20:00:00+00:00"
PUBLISHED_ACTIONS = ("publish", "republish")


def published_before_adoption(slug: str, record_rows: list[dict]) -> str:
    first = [r for r in record_rows if r.get("issue") == slug and r.get("action") in PUBLISHED_ACTIONS]
    return first[0]["at"] if first and first[0]["at"] < ADOPTED else ""


def skipped(slug: str, record_rows: list[dict] | None, label: str) -> list[tuple[str, str, str]]:
    first = published_before_adoption(slug, record_rows or [])
    return [(label, "ok", "SKIPPED — first published %s, before fix 2 was adopted (%s)"
             % (first[:10], ADOPTED[:10]))] if first else []


def preflight_rows(slug: str, record_rows: list[dict] | None = None, *, case: Path | None = None,
                   held: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    """BLOCKED while any LEAVES_OUT advocate objection is open (not yet ruled by
    ruling.py omissions, or sent to a person who has not closed it), or while
    omissions.json holds any run of source text."""
    s = skipped(slug, record_rows, ROW)
    if s:
        return s
    import ruling as R
    import source_store as store
    case = case or store.case_dir(slug)
    held = held if held is not None else R.held_texts(slug)
    open_ = [it["head"] for it in R._leaves_out(slug, case)]
    leaks = leaks_source_text(case, held)
    done = load(case).get("omissions") or []
    counts = {}
    for e in done:
        counts[e.get("outcome")] = counts.get(e.get("outcome"), 0) + 1
    if open_ or leaks:
        bits = []
        if open_:
            bits.append("%d LEAVES_OUT objection(s) open (e.g. %s): run ruling.py omissions %s, or a person "
                        "closes each with OMISSION/DID" % (len(open_), ", ".join(open_[:3]), slug))
        if leaks:
            bits.append("omissions.json holds source text (%s); it must hold offsets and hashes only"
                        % leaks[0][:80])
        return [(ROW, "BLOCKED", "; ".join(bits))]
    return [(ROW, "ok", "%d omission decision(s): %s" % (
        len(done), ", ".join("%d %s" % (n, k) for k, n in sorted(counts.items())) or "none needed"))]


def leaks_source_text(case: Path, held: dict[str, str], min_words: int = 6) -> list[str]:
    """Every run of MIN_WORDS words of any held text that appears in
    omissions.json: the committed record must hold none (a test helper and a
    preflight guard)."""
    pub = _fold(record_path(case).read_text(encoding="utf-8")) if record_path(case).exists() else ""
    out = []
    for sid, text in held.items():
        w = _fold(text).split()
        for i in range(0, max(0, len(w) - min_words + 1)):
            run = " ".join(w[i:i + min_words])
            if run in pub:
                out.append("%s: %r" % (sid, run))
                break
    return out
