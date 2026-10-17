#!/usr/bin/env python3
"""The conclusion judge — a publish stage. A model reads each conclusion against
the passages the writer recorded for it, and a person decides every one it flags.

WHAT IT IS FOR
--------------
B19 and B20 are word-level. They see a dropped "may" and a "high" above a cited
"moderate"; they cannot see a conclusion whose claim simply goes further than its
premises -- T03 s56, "the evidence says the calorie deficit, not the clock, does
most of the work", where no premise says anything about mechanism. This asks a
reader that question, from the store only.

WHAT IT IS NOT
--------------
It is not a filter on B19 or B20, and nothing here may be used to clear one. In
validation round 1 the judge called SUPPORTED every one of the four sentences
whose dropped hedge B19 reports, quoting the evidence with the hedge already
removed, and in both rounds it passed T04 s60 -- "high" against a passage it
quoted as "moderate certainty" -- which B20 stops. A flag here is a question for
a person; an absence of a flag is not an answer to anything.
docs/whatholdsup-conclusion-judge.md has the validation record.

WHAT THE JUDGE SEES, AND WHAT IT DOES NOT
-----------------------------------------
For every on-page binding row whose bucket is `judgement`, except holdings
sentences (bindings.is_holdings, the detector B21 routes to the store): the
sentence, about 400 characters of the page around it, and each premise as
(source id, access state, the recorded passage). NOT the writer's step: in
validation round 1, with the step shown, the judge adopted the writer's framing
on three of the known-error sentences and passed them. NOT check_flags, gate
findings, earlier verdicts or decisions: a flag must be the judge's own reading.

    claude-sonnet-4-6, one call per sentence, temperature 0 (fixed in call()),
    through factcheck_draft.call(search=False) under the issue's spend cap.

RUN, DECIDE, CHECK
------------------
    python3 conclusion_judge.py <slug>                    judge; writes the review
    python3 conclusion_judge.py <slug> decide <sentence_sha> <accepted|rejected|judgement> \\
        --by "<name>" --why "<reason>"                   record a decision
    python3 conclusion_judge.py <slug> status            the preflight row, no spend

The review is issues/<case>/conclusion-review.json. Re-running judges only
sentences that are new or whose text changed; a decision on an unchanged
sentence is kept, and a decision on a sentence whose text changed is marked
stale and must be made again.
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]

OK, BAD, WARN = "ok", "BLOCKED", "warn"   # publish.py's vocabulary

ROW_LABEL = "conclusion review settled"
REVIEW_FILE = "conclusion-review.json"
JUDGE_MODEL = "claude-sonnet-4-6"
ROLE = "conclusion_judge"
DECISIONS = ("accepted", "rejected", "judgement")
LABELS = ("SUPPORTED", "OVERSTATES", "UNDERSTATES", "NOT_IN_EVIDENCE", "CONTRADICTED")
UNPARSEABLE = "UNPARSEABLE"
CONTEXT_EACH_SIDE = 200

# THE STAGE IS ADOPTED HERE, AND IT IS NOT RETROACTIVE FOR WHAT IS ALREADY LIVE.
# An issue with a publish or republish row in published.json from before this
# instant was published without the stage existing; blocking its next
# corrections on a review nobody could have run would block corrections, which
# is worse than the errors they correct. It is SKIPPED, by name and with the
# reason, never passed silently. Every issue first published after this instant
# needs the review.
ADOPTED = "2026-10-17T16:00:00+00:00"
PUBLISHED_ACTIONS = ("publish", "republish")

# The judge prompt, exactly as it ran in validation round 2, mode A (spans, no
# step). Sent as two parts because call() takes a system prompt and a user
# message; the two joined by a blank line are the validated text.
SYSTEM = (
    "You are checking one conclusion from a research summary against the evidence "
    "it was built on. You see only the passages the writer actually read. Judge "
    "whether those passages support the conclusion as worded. Do not use outside "
    "knowledge about the topic; do not judge whether the conclusion is true in the "
    "world.")
USER_TEMPLATE = (
    "Conclusion: {sentence}\n"
    "Surrounding text: {context}\n"
    "Evidence (source id, how much of the source was read, passage):\n"
    "{premises}\n"
    "\n"
    "Pick exactly one label:\n"
    "- SUPPORTED: the passages support the conclusion as worded, including its "
    "strength, scope, certainty and any causal language.\n"
    "- OVERSTATES: the passages support something weaker: a hedge or uncertainty "
    "dropped, association stated as cause, a subgroup generalised, a smaller or less "
    "certain effect stated as larger or firmer.\n"
    "- UNDERSTATES: the passages support something stronger than the conclusion "
    "says: a hedge added that the evidence does not call for, a clear effect "
    "described as uncertain or absent, scope narrowed without reason.\n"
    "- NOT_IN_EVIDENCE: the conclusion asserts something the passages do not "
    "address at all.\n"
    "- CONTRADICTED: the passages say the opposite.\n"
    "\n"
    "Note: if a source was read as an abstract only, judge only what the abstract "
    "says.\n"
    "\n"
    'Reply with JSON only: {"label": "...", "reason": "one or two sentences naming '
    'the exact words in the conclusion and in the evidence that decide it"}')


# ---------------------------------------------------------------------------
# which sentences, and what the judge is shown
# ---------------------------------------------------------------------------

def fingerprint(sentence: str) -> str:
    """bindings.fingerprint, restated so this module imports nothing to compute
    it; test_whatholdsup_conclusion_judge holds the two equal."""
    return hashlib.sha256(" ".join((sentence or "").split()).encode("utf-8")).hexdigest()[:16]


def _is_holdings(sentence: str) -> bool:
    import bindings as B
    return B.is_holdings(sentence)


def judged_rows(bindings_doc: dict) -> list[tuple[str, dict]]:
    """(row id, row) for every on-page judgement row that is not a holdings
    sentence. A holdings sentence is settled by the store (B21), not by a
    reader of passages."""
    rows = bindings_doc.get("bindings") or {}
    return [(k, r) for k, r in rows.items()
            if r.get("on_page") and (r.get("bucket") or "") == "judgement"
            and not _is_holdings(r.get("sentence") or "")]


def plain(page_html: str) -> str:
    t = re.sub(r"<(script|style|head)\b.*?</\1>", " ", page_html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return " ".join(_html.unescape(t).split())


def context_of(sentence: str, text: str, each: int = CONTEXT_EACH_SIDE) -> str:
    """About `each` characters either side of the sentence, cut at word
    boundaries, the sentence itself left out. "" when it cannot be found."""
    s = " ".join(sentence.split())
    i = text.find(s)
    if i < 0:
        return ""
    before = text[max(0, i - each):i]
    after = text[i + len(s):i + len(s) + each]
    if i - each > 0 and " " in before:
        before = before.split(" ", 1)[1]
    if i + len(s) + each < len(text) and " " in after:
        after = after.rsplit(" ", 1)[0]
    return ("%s … %s" % (before.strip(), after.strip())).strip()


def build_user(row: dict, context: str, states: dict) -> str:
    """The user message. Reads exactly the sentence and the premises (source_id,
    span), plus each premise source's access state. Nothing else on the row --
    not the step, not check_flags, not a verdict -- can reach the judge."""
    prem = "\n".join('(%s, %s, "%s")' % (p.get("source_id") or "?",
                                         states.get(p.get("source_id"), "(no entry)"),
                                         " ".join((p.get("span") or "").split()))
                     for p in row.get("premises") or [])
    return (USER_TEMPLATE
            .replace("{sentence}", " ".join((row.get("sentence") or "").split()))
            .replace("{context}", context)
            .replace("{premises}", prem))


def parse_verdict(reply) -> dict:
    """call() returns parsed JSON or None. Anything that is not an object with a
    known label and a reason is UNPARSEABLE, which is a flag."""
    if not isinstance(reply, dict):
        return {"label": UNPARSEABLE, "reason": "",
                "raw": None if reply is None else json.dumps(reply)[:500]}
    label = str(reply.get("label", "")).strip().upper()
    reason = reply.get("reason")
    if label not in LABELS or not isinstance(reason, str) or not reason.strip():
        return {"label": UNPARSEABLE, "reason": str(reason or ""),
                "raw": json.dumps(reply)[:500]}
    return {"label": label, "reason": reason.strip()}


def is_flagged(label: str) -> bool:
    return label != "SUPPORTED"


def empty_decision() -> dict:
    return {"decision": None, "by": None, "on": None, "why": None}


def decided(entry: dict) -> bool:
    d = entry.get("decision") or {}
    return (d.get("decision") in DECISIONS and not d.get("stale")
            and all((d.get(k) or "").strip() for k in ("by", "on", "why")))


# ---------------------------------------------------------------------------
# the review file
# ---------------------------------------------------------------------------

def review_path(slug: str) -> Path:
    import source_store as store
    return store.case_dir(slug) / REVIEW_FILE


def load_review(slug: str) -> dict:
    p = review_path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"_what_this_is":
                "One verdict per conclusion sentence from the conclusion judge, and "
                "a person's decision on every one it flagged. A flag is a question, "
                "not a finding; an unflagged sentence is not thereby verified. See "
                "docs/whatholdsup-conclusion-judge.md.",
            "sentences": {}}


def save_review(slug: str, doc: dict) -> None:
    review_path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")


def plan(review: dict, rows: list[tuple[str, dict]]) -> tuple[list, list]:
    """(to_judge, keep) against the review as it stands.

    keep: entries whose row's sentence is unchanged -- verdict and decision stay.
    to_judge: (row id, row, previous entry or None) for rows with no entry, or
    whose text no longer matches the entry. A changed sentence's old decision is
    carried as `previous`, marked stale; it cannot settle the new text.
    """
    have = review.get("sentences") or {}
    by_sha = {e.get("sentence_sha"): k for k, e in have.items()}
    to_judge, keep = [], []
    for k, row in rows:
        sha = fingerprint(row.get("sentence") or "")
        e = have.get(k)
        if e is None and sha in by_sha:          # same sentence, row re-keyed
            e, k_old = have[by_sha[sha]], by_sha[sha]
            if k_old != k:
                have[k] = e
                del have[k_old]
        if e is not None and e.get("sentence_sha") == sha:
            keep.append(k)
        else:
            to_judge.append((k, row, e))
    return to_judge, keep


def record(review: dict, k: str, row: dict, verdict: dict, previous: dict | None,
           today: str) -> dict:
    entry = {"sentence_sha": fingerprint(row.get("sentence") or ""),
             "sentence": " ".join((row.get("sentence") or "").split()),
             "label": verdict["label"], "reason": verdict.get("reason", ""),
             "model": JUDGE_MODEL, "run_on": today,
             "flagged": is_flagged(verdict["label"])}
    if verdict.get("raw") is not None:
        entry["raw"] = verdict["raw"]
    if entry["flagged"]:
        entry["decision"] = empty_decision()
    if previous is not None:
        old = dict(previous)
        if old.get("decision"):
            old["decision"] = dict(old["decision"], stale=True)
        entry["previous"] = (previous.get("previous") or []) + [
            {k2: v for k2, v in old.items() if k2 != "previous"}]
    review.setdefault("sentences", {})[k] = entry
    return entry


# ---------------------------------------------------------------------------
# the store and the page
# ---------------------------------------------------------------------------

def _bindings_doc(slug: str) -> dict:
    import bindings as B
    return B.load(slug)


def access_states(slug: str) -> dict:
    import source_store as store
    import source_ledger as ledger
    return {s.get("id"): ledger.access_of(s).get("state") for s in store.sources(slug)}


def page_text(slug: str) -> str:
    """The page the issue will publish: publish.py's ISSUES entry if it has one,
    otherwise the single draft page in the case directory."""
    import bindings as B
    try:
        return plain(B._page_html(slug))
    except (KeyError, SystemExit, FileNotFoundError):
        import source_store as store
        pages = sorted((store.case_dir(slug) / "draft").glob("*.html"))
        if len(pages) != 1:
            raise SystemExit("%s: no ISSUES page and %d draft page(s); cannot find "
                             "the text around each sentence" % (slug, len(pages)))
        return plain(pages[0].read_text(encoding="utf-8"))


def _factcheck():
    """factcheck_draft, loaded by path and only when judging. Pinned to the
    judge model through SIGNAL_MODEL, the override call() already reads."""
    want = os.environ.get("SIGNAL_MODEL", "").strip()
    if want and want != JUDGE_MODEL:
        raise SystemExit("SIGNAL_MODEL is %r; the conclusion judge runs %s only"
                         % (want, JUDGE_MODEL))
    os.environ["SIGNAL_MODEL"] = JUDGE_MODEL
    import importlib.util
    p = ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py"
    spec = importlib.util.spec_from_file_location("factcheck_draft", p)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(p.parent))
    spec.loader.exec_module(m)
    if m.SIGNAL_MODEL != JUDGE_MODEL:
        raise SystemExit("factcheck_draft resolved model %r, not %s"
                         % (m.SIGNAL_MODEL, JUDGE_MODEL))
    return m


def judge(slug: str, *, ask=None, today: str | None = None) -> dict:
    """Judge every new or changed conclusion and write the review.

    `ask(system, user) -> reply` is the model call; by default
    factcheck_draft.call(search=False) under the issue's cap. Tests pass a stub.
    """
    if ask is None:
        fc = _factcheck()
        fc.enter_issue(slug)

        def ask(system, user):
            return fc.call(system, user, search=False, max_tokens=600,
                           label="%s/%s" % (ROLE, JUDGE_MODEL))
    today = today or date.today().isoformat()
    review = load_review(slug)
    rows = judged_rows(_bindings_doc(slug))
    to_judge, keep = plan(review, rows)
    if to_judge:
        states = access_states(slug)
        text = page_text(slug)
        for k, row, previous in to_judge:
            user = build_user(row, context_of(row.get("sentence") or "", text), states)
            record(review, k, row, parse_verdict(ask(SYSTEM, user)), previous, today)
            save_review(slug, review)          # after every call: a crash keeps what was paid for
    save_review(slug, review)
    return {"judged": len(to_judge), "kept": len(keep),
            "flagged": sum(1 for k, _r in rows
                           if (review["sentences"].get(k) or {}).get("flagged"))}


def decide(slug: str, sha: str, decision: str, by: str, why: str,
           today: str | None = None) -> dict:
    """Record a person's decision on one flagged sentence, found by its
    sentence_sha (a unique prefix of at least 8 characters is enough)."""
    if decision not in DECISIONS:
        raise ValueError("decision must be one of %s" % ", ".join(DECISIONS))
    if not (by or "").strip() or not (why or "").strip():
        raise ValueError("a decision needs a named person (--by) and a reason (--why)")
    if len(sha) < 8:
        raise ValueError("give at least 8 characters of the sentence_sha")
    review = load_review(slug)
    hits = [(k, e) for k, e in (review.get("sentences") or {}).items()
            if (e.get("sentence_sha") or "").startswith(sha)]
    if len(hits) != 1:
        raise ValueError("%d review entries match sentence_sha %r" % (len(hits), sha))
    k, e = hits[0]
    if not e.get("flagged"):
        raise ValueError("%s was judged %s and is not flagged; there is nothing to "
                         "decide" % (sha, e.get("label")))
    e["decision"] = {"decision": decision, "by": by.strip(),
                     "on": today or date.today().isoformat(), "why": why.strip()}
    save_review(slug, review)
    return e


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

def published_before_adoption(slug: str, record_rows: list[dict]) -> str:
    """The first publish/republish instant before ADOPTED, or ""."""
    times = sorted(r.get("at") or "" for r in record_rows or []
                   if r.get("issue") == slug and r.get("action") in PUBLISHED_ACTIONS)
    return times[0] if times and times[0] < ADOPTED else ""


def preflight_rows(slug: str, record_rows: list[dict] | None = None) -> list[tuple[str, str, str]]:
    """One row. BLOCKED until every current conclusion has a verdict on its
    current text and every flagged one has a current decision.

    `record_rows` is publish.load_record(). An issue first published before
    ADOPTED is SKIPPED -- reported as ok with the word SKIPPED and the reason,
    because publish.show() treats any state but ok/BLOCKED/warn as a STOP.
    """
    first = published_before_adoption(slug, record_rows or [])
    if first:
        return [(ROW_LABEL, OK,
                 "SKIPPED — first published %s, before the conclusion judge was "
                 "adopted (%s); republishing it does not require a review"
                 % (first[:10], ADOPTED[:10]))]
    p = review_path(slug)
    if not p.exists():
        return [(ROW_LABEL, BAD,
                 "no %s for this issue. Run: python3 backend/scripts/whatholdsup/"
                 "conclusion_judge.py %s" % (REVIEW_FILE, slug))]
    review = json.loads(p.read_text(encoding="utf-8"))
    have = review.get("sentences") or {}
    shas = {e.get("sentence_sha"): e for e in have.values()}
    rows = judged_rows(_bindings_doc(slug))
    missing, undecided, stale, flagged, done = [], [], [], 0, 0
    for k, row in rows:
        sha = fingerprint(row.get("sentence") or "")
        e = have.get(k) if (have.get(k) or {}).get("sentence_sha") == sha else shas.get(sha)
        if e is None:
            missing.append(k)
            continue
        if not e.get("flagged"):
            continue
        flagged += 1
        if (e.get("decision") or {}).get("stale"):
            stale.append(sha)
        elif decided(e):
            done += 1
        else:
            undecided.append(sha)
    if missing:
        return [(ROW_LABEL, BAD,
                 "%d of %d conclusion(s) have no verdict on their current text -- the "
                 "draft changed since the judge ran. Re-run: python3 backend/scripts/"
                 "whatholdsup/conclusion_judge.py %s" % (len(missing), len(rows), slug))]
    if undecided or stale:
        bits = []
        if undecided:
            bits.append("%d flagged conclusion(s) have no decision: %s"
                        % (len(undecided), ", ".join(s[:8] for s in undecided[:5])))
        if stale:
            bits.append("%d decision(s) are stale -- the sentence changed since it "
                        "was decided: %s" % (len(stale), ", ".join(s[:8] for s in stale[:5])))
        return [(ROW_LABEL, BAD,
                 "; ".join(bits) + ". Record each with: python3 backend/scripts/"
                 "whatholdsup/conclusion_judge.py %s decide <sentence_sha> "
                 "<accepted|rejected|judgement> --by NAME --why TEXT" % slug)]
    return [(ROW_LABEL, OK,
             "%d conclusion(s) judged, %d flagged, %d decided"
             % (len(rows), flagged, done))]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("decide", help="record a decision on one flagged conclusion")
    d.add_argument("sentence_sha")
    d.add_argument("decision", choices=DECISIONS)
    d.add_argument("--by", required=True, help="who decided -- a name, not a role")
    d.add_argument("--why", required=True)
    sub.add_parser("status", help="print the preflight row; no model call")
    a = ap.parse_args(argv)
    if a.cmd == "decide":
        try:
            e = decide(a.slug, a.sentence_sha, a.decision, a.by, a.why)
        except ValueError as exc:
            print("  REFUSED: %s" % exc, file=sys.stderr)
            return 1
        print("  %s: %s by %s on %s" % (e["sentence_sha"], e["decision"]["decision"],
                                        e["decision"]["by"], e["decision"]["on"]))
        return 0
    if a.cmd == "status":
        # publish.py loads the paid-call module at import; read its record
        # directly instead, by the same path it uses (publish.RECORD).
        rec = ROOT / "backend" / "data" / "whatholdsup" / "published.json"
        rows = (json.loads(rec.read_text(encoding="utf-8")).get("published", [])
                if rec.exists() else [])
        for label, st, detail in preflight_rows(a.slug, rows):
            print("  %-7s %-28s %s" % ({OK: "ok", BAD: "STOP", WARN: "warn"}[st], label, detail))
        return 0
    t = judge(a.slug)
    print("  %s: %d judged, %d kept from the last run, %d flagged; review at %s"
          % (a.slug, t["judged"], t["kept"], t["flagged"], review_path(a.slug)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
