#!/usr/bin/env python3
"""The ruling model, everywhere the study's protocol assigns it (rev 27).

    ruling.py gate SLUG [--cap USD]          rule every undecided gate finding
    ruling.py conclusions SLUG [--cap USD]   rule every undecided conclusion-judge flag
    ruling.py changecheck SLUG [--cap USD]   rule every undisposed changecheck finding
    ruling.py advocate SLUG [--cap USD]      rule every open source-advocate objection
    ruling.py dangling SLUG [--cap USD]      rule every reference an applied ruling left
                                             pointing at nothing (GAP-016)

WHY THIS EXISTS
---------------
WHU's published issues have a person rule on gate findings (`accept-gate`,
gate-findings.json) and decide every conclusion-judge flag (`decide --by`). The
study's frozen process ("The frozen WHU process", protocol rev 27) gives those
rulings to the same ruling model that rules on audit findings and second-reader
disagreements, so that no advisor session rules during the study. This module
is that, for the two kinds the audit stage does not already cover. It runs on a
STUDY issue only (issue.json "study": true); a published issue keeps its people.

WHAT THE MODEL SEES -- AN ALLOW-LIST
-----------------------------------
Exactly RULE_FIELDS: the sentence, the finding (kind, reason, proposed text) and
the quoted source text, each quotation labelled by position only ("Quotation
1"), so not even a source id travels. The quotations are the passages the
sentence's binding row rests on, with QUOTE_AROUND characters of their document
either side. Nothing else on a binding row, a gate report or a review entry --
the drafter's step, check flags, verdicts, earlier decisions, urls, source ids,
signers -- can reach the model; test_whatholdsup_ruling.py plants those and
asserts none arrives.

THE PROMPTS, BY SHA256
----------------------
Conclusion-judge flags use audit_prompts/rule.md, the audit stage's prompt,
unchanged. Gate findings use audit_prompts/rule_cite.md: rule.md word for word
plus one output field, "quotation", the number of the quotation the reason
cites. A gate finding is settled in gate-findings.json, where "accepted" and
"rejected" must name a source and a quotation that is in it (findings.py); the
model is never shown a source id, so it names the quotation's number and the id
is looked up here. Every ruling is logged with its time, model, prompt sha256
and its inputs, and is attributed "ruling model claude-opus-5-5".

ONE RULING PER SENTENCE (GAP-019, 2026-10-21). In every mode, the open
findings are grouped by the sentence they target, and each sentence is ruled
in one call that returns one decision and one text. A sentence with one finding
is ruled as before, with the prompt above; a sentence with several is ruled with
audit_prompts/rule_group.md (rule_group_cite.md for the gate: the same plus
"quotation"), whose payload is GROUP_FIELDS: the sentence, every finding (kind,
reason, proposed text, the numbers of the quotations it rests on) and every
quotation once, in context. Their sha256 are frozen in GROUP_PROMPT_SHA256.
Each log record's "covers" names the findings its ruling settles, and every
one of them is recorded with that one decision and text.

Changecheck findings and source-advocate objections (added 2026-10-20) use
rule.md too: their records need no source and quotation. An advocate's own
quotation of its document is shown as a quotation ONLY if it is in the held text
of that document, word for word; otherwise the reason says it is not.

HOW A RULING IS RECORDED
------------------------
  gate        reject -> "rejected"; accept/amend -> "accepted", carrying the
              ruling's text, which the drafting step applies to the page; no
              quotation cited -> "judgement".
  conclusion  reject -> "rejected"; accept/amend -> "accepted", with the
              ruling's text in the reason.
  changecheck a disposition in change-reviews.json, keyed by
              changecheck.finding_key: reject -> "reject"; accept/amend ->
              "accept", carrying the ruling's text (an accepted finding does not
              stay closed: the sentence must change).
  advocate    the item's MERIT / EFFECT / DID lines in the advocate
              adjudication file: reject -> "no" / "none"; accept/amend -> "yes"
              / "corrects", DID naming the text to apply. Questions about a
              source only a person may read are not ruled: they stay with a
              person (protocol rev 27, "Sentences that need a person").

A REPLY CUT OFF (2026-10-22). The output limit is MAX_OUT, 4,000 tokens (1,500
until a WHU-S01 ruling ran past it and stopped the step). A reply cut off at
the limit is asked once more with the identical prompt; each cut-off attempt is
logged in rulings/attempts.jsonl. Cut off again, a RULING_FAILED record there
names the findings, they stay open (a later run rules them), and the step goes
on to the next sentence; the mode exits 4 after its consistency sample.
Rulings a step made before it stopped, unsampled, are carried into the sample
of the run that resumes it (unsampled; each step line lists its ruling_ids).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jsonio  # noqa: E402

MODEL = "claude-opus-5-5"
BY = "ruling model %s" % MODEL
BY_PROTECTED = "code (ruling.py gate: protected sentence, left for a person)"
RULE_FIELDS = ("sentence", "kind", "reason", "proposed_text", "quoted_source_text")
QUOTE_AROUND = 600
# The ruling's output limit. 1,500 until 2026-10-22, when a WHU-S01 ruling
# reply ran past it, the caller raised, and the step stopped mid-way.
MAX_OUT = 4000
# A reply cut off at MAX_OUT is asked once more with the same prompt; both
# attempts are logged (attempts_log). Cut off again: RULING_FAILED.
ATTEMPTS = 2
RULING_FAILED = "RULING_FAILED"
# The consistency sample began with commit c625411 (2026-10-21 01:21 UTC):
# rulings before it were never sampled and are not carried into a sample.
SAMPLED_SINCE = "2026-10-21T01:21:28+00:00"
# Each mode's ruling_kind on its log records.
MODE_KIND = {"gate": "gate", "conclusions": "conclusion", "changecheck": "changecheck",
             "advocate": "advocate", "dangling": "dangling", "omissions": "omission",
             "judgements": "relevance"}
PROMPTS = {
    "audit": HERE / "audit_prompts" / "rule.md",
    "second-reader": HERE / "audit_prompts" / "rule.md",
    "conclusion": HERE / "audit_prompts" / "rule.md",
    "gate": HERE / "audit_prompts" / "rule_cite.md",
    "changecheck": HERE / "audit_prompts" / "rule.md",
    "advocate": HERE / "audit_prompts" / "rule.md",
    "dangling": HERE / "audit_prompts" / "rule.md",
    # Post-study fix 2 (2026-10-27): a finding the page left out. Not a frozen
    # study prompt; docs/whu-fix2-omission-rulings-design.md, section 2.
    "omission": HERE / "audit_prompts" / "rule_omission.md",
    # Post-study fix 3 (2026-10-27): does a held assessment judgement bear on
    # the question? docs/whu-fix3-evidence-standard.md, section 3.2.
    "relevance": HERE / "audit_prompts" / "rule_relevance.md",
}
# Several findings on one sentence, ruled in one call (GAP-019).
GROUP_FIELDS = ("sentence", "findings", "quoted_source_text")
GROUP_PROMPTS = {k: HERE / "audit_prompts" / ("rule_group_cite.md" if k == "gate" else "rule_group.md")
                 for k in PROMPTS if k not in ("omission", "relevance")}
# The omission ruling's payload (fix 2): an allow-list like RULE_FIELDS.
OMISSION_FIELDS = ("question", "scope", "reader", "finding", "anchor", "already_on_page")
RELEVANCE_FIELDS = ("question", "scope", "judgement")
# Frozen as the prompts are frozen: by sha256, on every ruling and here
# (test_whatholdsup_ruling_group.py checks the files against these).
GROUP_PROMPT_SHA256 = {
    "rule_group.md": "68a0fd068ff518820dfbaeab58eeba4a571fa7928e231b80dbf0112c01d39a62",
    "rule_group_cite.md": "82d440f6a68192763882744323b64eb83a95baebb2f9e8c0395193c98faeb84d",
}


class RulingError(Exception):
    pass


class RulingFailed(RulingError):
    """The reply was cut off at MAX_OUT on every attempt. The findings it
    covers are logged RULING_FAILED and left open; the step goes on."""



def _load_frozen():
    """frozen.py, by its path beside this file (callers load this module by path)."""
    import importlib.util as _u
    m = sys.modules.get("frozen")
    if m is None:
        sp = _u.spec_from_file_location("frozen", Path(__file__).resolve().parent / "frozen.py")
        m = _u.module_from_spec(sp)
        sys.modules["frozen"] = m
        sp.loader.exec_module(m)
    return m

def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_sha(kind: str, grouped: bool = False) -> str:
    return sha((GROUP_PROMPTS if grouped else PROMPTS)[kind].read_text(encoding="utf-8"))


def _rec_index(fid: str) -> int | None:
    """N of a recency finding id, f<draft sha>-rec-N or the older rec-N
    (findings.recency_id)."""
    m = re.match(r"^(?:f[0-9a-f]{8}-)?rec-(\d+)$", fid or "")
    return int(m.group(1)) if m else None


def _norm(s: str) -> str:
    return " ".join((s or "").split()).lower()


# ---------------------------------------------------------------------------
# the payload: an allow-list, nothing else
# ---------------------------------------------------------------------------

def quotations(row: dict, held: dict[str, str]) -> list[tuple[str, str]]:
    """(source id, quote) for every passage a binding row rests on: its span,
    also_rests_on, and premises. The source id stays here; it is never sent."""
    out = []
    if row.get("source_id") and row.get("span"):
        out.append((row["source_id"], row["span"]))
    for x in (row.get("also_rests_on") or []) + (row.get("premises") or []):
        if isinstance(x, dict) and x.get("source_id") and x.get("span"):
            out.append((x["source_id"], x["span"]))
    # The same passage can be a row's span AND one of its premises; it is shown once.
    seen, uniq = set(), []
    for q in out:
        if q not in seen:
            seen.add(q)
            uniq.append(q)
    return uniq


def payload(sentence: str, kind: str, reason: str, proposed_text: str,
            quotes: list[tuple[str, str]], held: dict[str, str]) -> dict:
    """Exactly RULE_FIELDS. Each quotation is shown with QUOTE_AROUND characters
    of its document either side, labelled by position only."""
    p = {"sentence": " ".join((sentence or "").split()), "kind": kind or "",
         "reason": reason or "", "proposed_text": proposed_text or "",
         "quoted_source_text": _shown(quotes, held)}
    assert tuple(p) == RULE_FIELDS
    return p


def _shown(quotes: list[tuple[str, str]], held: dict[str, str]) -> str:
    shown = []
    for n, (sid, q) in enumerate(quotes, 1):
        # Located as the audit compares a quotation (audit_stage.locate: norm(),
        # enclosing quote marks aside), then mapped back to the document's own
        # offsets. Until 2026-10-20 this was an exact find of the first 30
        # characters, which a line break or a curly quote defeated.
        import audit_stage as A
        around = A.in_context(q, held.get(sid) or "", QUOTE_AROUND)
        shown.append("Quotation %d: \"%s\"\nIn its document: ...%s..." % (n, q, " ".join(around.split())))
    return "\n\n".join(shown) or "(no source text is quoted for this sentence)"


def group_payload(sentence: str, findings: list[dict], held: dict[str, str]) -> tuple[dict, list]:
    """Exactly GROUP_FIELDS, for several findings on one sentence: each finding
    (kind, reason, proposed text, and the numbers of the quotations it rests
    on) and every quotation once, numbered across the group. Returns the
    payload and the numbered quotations."""
    quotes: list[tuple[str, str]] = []
    for f in findings:
        for q in f["quotes"]:
            if q not in quotes:
                quotes.append(q)
    parts = []
    for n, f in enumerate(findings, 1):
        nums = ", ".join(str(quotes.index(q) + 1) for q in f["quotes"]) or "none"
        parts.append("Finding %d\nKind: %s\nReader's reason: %s\nReader's proposed text: %s\n"
                     "Quotations it rests on: %s" % (n, f.get("kind") or "", f.get("reason") or "",
                                                     f.get("proposed") or "", nums))
    p = {"sentence": " ".join((sentence or "").split()), "findings": "\n\n".join(parts),
         "quoted_source_text": _shown(quotes, held)}
    assert tuple(p) == GROUP_FIELDS
    return p, quotes


def build_prompt(kind: str, p: dict, grouped: bool = False) -> str:
    frozen = _load_frozen()             # a changed frozen prompt is refused (protocol rev 38)
    t = frozen.read_text((GROUP_PROMPTS if grouped else PROMPTS)[kind])
    for k in (OMISSION_FIELDS if kind == "omission" else RELEVANCE_FIELDS if kind == "relevance"
              else GROUP_FIELDS if grouped else RULE_FIELDS):
        t = t.replace("{%s}" % k, p[k])
    return t


def parse(kind: str, text: str, n_quotes: int) -> dict:
    if kind == "omission":
        return parse_omission(text)
    if kind == "relevance":
        return parse_relevance(text)
    s = jsonio.strip_code_fence(text)
    m = re.search(r"\{.*\}", s, re.S)
    try:
        got = json.loads(m.group(0) if m else s)
    except Exception:
        raise RulingError("ruling reply is not JSON: %r" % s[:200])
    if not isinstance(got, dict) or got.get("ruling") not in ("accept", "amend", "reject"):
        raise RulingError("ruling reply not usable: %r" % (got,))
    if got["ruling"] in ("accept", "amend") and got.get("text") is None:
        raise RulingError("ruling %s with no text" % got["ruling"])
    if kind == "gate":
        q = got.get("quotation")
        if q is not None and not (isinstance(q, int) and 1 <= q <= n_quotes):
            raise RulingError("ruling cites quotation %r of %d" % (q, n_quotes))
    return got


def parse_omission(text: str) -> dict:
    """An omission ruling's reply, as {"ruling": add | out_of_scope |
    not_material, "text": the draft for ADD else None, ...}: the ruling/text
    shape every ruling record has, so the consistency sample compares it as it
    compares any other."""
    s = jsonio.strip_code_fence(text)
    m = re.search(r"\{.*\}", s, re.S)
    try:
        got = json.loads(m.group(0) if m else s)
    except Exception:
        raise RulingError("omission reply is not JSON: %r" % s[:200])
    if not isinstance(got, dict):
        raise RulingError("omission reply not usable: %r" % (got,))
    outcome = str(got.get("outcome") or "").strip().upper()
    if outcome not in ("ADD", "OUT_OF_SCOPE", "NOT_MATERIAL"):
        raise RulingError("omission outcome %r is not ADD, OUT_OF_SCOPE or NOT_MATERIAL" % got.get("outcome"))
    draft, span = (got.get("draft_text") or "").strip(), (got.get("span") or "").strip()
    element = (got.get("scope_element") or "").strip()
    if outcome == "ADD" and not (draft and span):
        raise RulingError("ADD with no draft_text or no span")
    if outcome == "OUT_OF_SCOPE" and not element:
        raise RulingError("OUT_OF_SCOPE naming no scope element")
    return {"ruling": outcome.lower(), "text": draft if outcome == "ADD" else None, "outcome": outcome,
            "scope_element": element, "span": span if outcome == "ADD" else "",
            "in_scope": got.get("in_scope"), "material": got.get("material"), "reason": got.get("reason") or "",
            "reason_for_reader": got.get("reason_for_reader") or ""}


def parse_relevance(text: str) -> dict:
    """{"ruling": relevant | not_relevant, "text": the question words or None, ...}."""
    s = jsonio.strip_code_fence(text)
    m = re.search(r"\{.*\}", s, re.S)
    try:
        got = json.loads(m.group(0) if m else s)
    except Exception:
        raise RulingError("relevance reply is not JSON: %r" % s[:200])
    if not isinstance(got, dict) or not isinstance(got.get("relevant"), bool):
        raise RulingError("relevance reply not usable: %r" % (got,))
    words = (got.get("question_words") or "").strip()
    return {"ruling": "relevant" if got["relevant"] else "not_relevant",
            "text": words if got["relevant"] else None, "relevant": got["relevant"],
            "question_words": words, "reason": got.get("reason") or ""}


def attempts_log(log: Path) -> Path:
    """Cut-off attempts and RULING_FAILED records, beside the ruling log and
    apart from it: nothing that reads rulings.jsonl (the consistency sample,
    applied_check, the stage cap's per-ruling cost) mistakes one for a ruling."""
    return log.parent / "attempts.jsonl"


def _append(path: Path, rec: dict) -> dict:
    rec["id"] = sha(json.dumps(rec, sort_keys=True, ensure_ascii=False))[:16]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def rule(kind: str, p: dict, n_quotes: int, call, log: Path, ref: dict, grouped: bool = False) -> dict:
    """One ruling: prompt, call, check, log. `call(prompt, max_tokens, role)`
    returns (text, usage) -- audit_stage.Caller, metered and capped, or a fake.

    A reply cut off at MAX_OUT (audit_stage.ReplyCutOff) is logged in
    attempts_log and asked once more with the identical prompt; a second
    cut-off is logged there too, with a RULING_FAILED record naming the
    findings, and raises RulingFailed for the caller to pass over."""
    prompt = build_prompt(kind, p, grouped)
    path = (GROUP_PROMPTS if grouped else PROMPTS)[kind]
    base = {"by": BY, "model": MODEL, "ruling_kind": kind, "prompt": str(path.relative_to(HERE)),
            "prompt_sha256": prompt_sha(kind, grouped), "inputs_sha256": sha(json.dumps(p))}
    cut = []
    for n in range(1, ATTEMPTS + 1):
        try:
            text, usage = call(prompt, MAX_OUT, "rule-%s" % kind + ("" if n == 1 else "-retry"))
            break
        except Exception as e:
            if not getattr(e, "cut_off", False):
                raise
            cut.append(_append(attempts_log(log), {
                "type": "cut_off", "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                **base, "inputs": p, **ref, "attempt": n, "of": ATTEMPTS, "max_tokens": MAX_OUT,
                "error": str(e), "usage": getattr(e, "usage", {}) or {}})["id"])
    else:
        failed = _append(attempts_log(log), {
            "type": RULING_FAILED, "status": RULING_FAILED,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **base, **ref,
            "attempts": cut, "why": "the reply was cut off at %d tokens on all %d attempts; the "
                                    "finding(s) stay open" % (MAX_OUT, ATTEMPTS)})
        raise RulingFailed("%s: cut off at %d tokens on all %d attempts (record %s)"
                           % (kind, MAX_OUT, ATTEMPTS, failed["id"]))
    got = parse(kind, text, n_quotes)
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "by": BY,
           "model": MODEL, "ruling_kind": kind, "prompt": str(path.relative_to(HERE)),
           "prompt_sha256": prompt_sha(kind, grouped), "inputs": p, "inputs_sha256": sha(json.dumps(p)),
           **ref, **got, "usage": usage}
    if cut:
        rec["after_cut_off"] = cut          # the attempt(s) cut off before this reply
    _append(log, rec)
    return got


# ---------------------------------------------------------------------------
# one ruling per sentence (GAP-019)
# ---------------------------------------------------------------------------
#
# Until 2026-10-21 every finding was ruled in its own call. On WHU-P02 two
# advocate objections on one sentence (S005-11 and S005-12) were ruled
# separately and could come back with two different texts for the same
# sentence, of which only one can be on the page. Now the findings of a run are
# grouped by the sentence they target -- its binding row, or, with no row, the
# sentence's text -- and each sentence is ruled once: one finding with the
# prompt it always had (rule.md / rule_cite.md, unchanged), several with
# rule_group.md / rule_group_cite.md, which list every finding and ask for one
# decision and one text that settles all of them. Every log record names the
# findings its ruling covers ("covers"), so applied_check expects one text per
# sentence.

def sentence_key(hit, sentence: str) -> tuple:
    return ("row", hit[0]) if hit else ("text", _norm(sentence))


def by_sentence(items: list[dict]) -> list[list[dict]]:
    """Items grouped by their "key", in the order each sentence first appears."""
    groups: dict = {}
    for it in items:
        groups.setdefault(it["key"], []).append(it)
    return list(groups.values())


def rule_sentence(kind: str, group: list[dict], held: dict, call, log: Path,
                  extra: dict | None = None) -> tuple[dict, list, str]:
    """Rule every finding in GROUP (all on one sentence) in one call. Each item
    carries sentence, kind, reason, proposed, quotes, ref. Returns (ruling,
    the numbered quotations it may cite, the prompt's sha256)."""
    if len(group) == 1:
        it = group[0]
        p = payload(it["sentence"], it["kind"], it["reason"], it["proposed"], it["quotes"], held)
        got = rule(kind, p, len(it["quotes"]), call, log,
                   dict(it["ref"], covers=[it["ref"]], **(extra or {})))
        return got, it["quotes"], prompt_sha(kind)
    p, quotes = group_payload(group[0]["sentence"], group, held)
    got = rule(kind, p, len(quotes), call, log,
               dict(covers=[it["ref"] for it in group], **(extra or {})), grouped=True)
    return got, quotes, prompt_sha(kind, True)


FOR_PERSON = "for_person.jsonl"


def split_protected(items: list[dict], rows: dict) -> tuple[list[dict], list[dict]]:
    """(items to rule, items on a protected sentence). A protected sentence
    (bindings.protected_kind: the question restatement, what we held, read or
    did not read) is never rewritten or cut by the ruling model, in any mode:
    no source can support it, so a source-support ruling can only narrow or
    remove it (WHU-S08: advocate ruling 8ae1718065708594 began the rewriting of
    the stocktake sentence). Its findings stay open for a person."""
    import bindings as B
    keep, person = [], []
    for it in items:
        k = it["key"][1] if it.get("key") and it["key"][0] == "row" else None
        kind = B.protected_kind(it.get("sentence") or "", rows.get(k) if k else None)
        (person if kind else keep).append(dict(it, protected=kind) if kind else it)
    return keep, person


def route_to_person(mode: str, items: list[dict], log: Path) -> None:
    """Record each protected item as left for a person, beside the rulings
    log (never committed on a study issue), and say so."""
    for it in items:
        print("  left for a person (protected sentence, %s): %s -- %r"
              % (it["protected"], mode, (it.get("sentence") or "")[:80]))
        _append(log.with_name(FOR_PERSON), {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "mode": mode,
            "protected": it["protected"], "sentence": it.get("sentence"), "kind": it.get("kind"),
            "ref": it.get("ref"),
            "why": "a protected sentence is never rewritten or cut by the ruling model; a person decides"})


def _rulable(mode: str, items: list[dict], rows: dict, log: Path) -> list[dict]:
    keep, person = split_protected(items, rows)
    route_to_person(mode, person, log)
    return keep


def _together(group: list[dict], name) -> list:
    """What the other findings ruled in the same call are called, for the record."""
    return [name(it) for it in group] if len(group) > 1 else []


def _try_sentence(kind: str, group: list[dict], held: dict, call, log: Path, failed: list | None,
                  extra: dict | None = None):
    """rule_sentence, or None if the ruling failed (RulingFailed): the failure
    is logged in attempts_log, its findings stay open, it is added to FAILED,
    and the step goes on to the next sentence."""
    try:
        return rule_sentence(kind, group, held, call, log, extra)
    except RulingFailed as e:
        print("  %s: %s -- left open" % (RULING_FAILED, e))
        if failed is not None:
            failed.append({"kind": kind, "refs": [it["ref"] for it in group], "why": str(e)})
        return None


# ---------------------------------------------------------------------------
# the study issue
# ---------------------------------------------------------------------------

def held_texts(slug: str) -> dict[str, str]:
    """{source id: text}, extracted as the binding checks extract it (reading
    order; audit_stage.held_for_audit, via spancheck._text), keyed by the bare
    source id that binding rows and briefs use.

    Until 2026-10-20 this module read reachability.held_text, which (a) ran
    `pdftotext -layout`, splicing margin text into sentences, and (b) keys its
    texts "<issue>:<source id>". Every lookup here is by bare id, so the
    surrounding context of a quotation was never found, and the advocate's
    verbatim check below never found any quotation: every advocate quotation
    was reported to the model as not in the held text."""
    import audit_stage as A
    return A.held_for_audit(slug)


def _in_held(quote: str, text: str) -> bool:
    """The advocate's quotation is in the held text: compared as the audit
    stage compares a reader's quotation (audit_stage.quoted_in: norm(), and
    enclosing quote marks removed), no looser."""
    import audit_stage as A
    return A.quoted_in(quote, text)


def _publish():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pub_ruling", str(HERE / "publish.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def require_study(slug: str, P=None) -> None:
    P = P or _publish()
    if not P.is_study(slug):
        raise SystemExit("%s is not a study issue (issue.json \"study\": true). On a published "
                         "issue these rulings are a person's, not the ruling model's." % slug)


def log_path(slug: str) -> Path:
    import source_store as store
    return store.case_dir(slug) / "rulings" / "rulings.jsonl"


def _row_for(rows: dict, text: str) -> tuple[str, dict] | None:
    """The on-page binding row whose sentence contains `text`, or (for a gate
    claim, which restates rather than quotes) shares most of its words."""
    t = _norm(text)
    if not t:
        return None
    on = [(k, r) for k, r in rows.items() if r.get("on_page")]
    for k, r in on:
        if t in _norm(r.get("sentence")):
            return k, r
    words = set(re.findall(r"[a-z0-9.%]+", t))
    best, score = None, 0.0
    for k, r in on:
        w = set(re.findall(r"[a-z0-9.%]+", _norm(r.get("sentence"))))
        s = len(words & w) / max(1, len(words))
        if s > score:
            best, score = (k, r), s
    return best if score >= 0.6 else None


def gate_items(report: dict, findings_doc: dict) -> list[dict]:
    """Every undecided gate finding with the page text it is about and the
    gate's own proposed fix, if it gave one."""
    claims = {c.get("id"): c for c in (report.get("claims") or [])}
    objs = report.get("objections") or []
    infs = report.get("inferences") or []
    cov = (report.get("coverage") or {}).get("contradictions") or []
    rec = (report.get("recency") or {}).get("studies") or []
    out = []
    for f in findings_doc.get("findings") or []:
        if (f.get("decision") or "").strip():
            continue
        fid = f.get("id") or ""
        text, fix = "", ""
        if fid.startswith("obj-") and fid[4:].isdigit() and int(fid[4:]) <= len(objs):
            o = objs[int(fid[4:]) - 1]; text, fix = o.get("quote") or "", o.get("fix") or ""
        elif fid.startswith("inf-") and fid[4:].isdigit() and int(fid[4:]) <= len(infs):
            o = infs[int(fid[4:]) - 1]; text, fix = o.get("quote") or "", o.get("fix") or ""
        elif fid.startswith("cov-") and fid[4:].isdigit() and int(fid[4:]) <= len(cov):
            o = cov[int(fid[4:]) - 1]; text, fix = o.get("quote") or "", o.get("fix") or ""
        elif fid in claims:
            text = claims[fid].get("claim") or ""
        elif (_rec_index(fid) or 0) and _rec_index(fid) <= len(rec):
            # A recency study that is not CURRENT (GAP-014): the sentence is the
            # one that relies on that readout, found by the study's name or by
            # the readout the gate says the draft uses. Its id is f<draft
            # sha>-rec-N, or rec-N if recorded before 2026-10-22.
            s = rec[_rec_index(fid) - 1]
            text = s.get("name") or ""
            out.append({"finding": f, "text": text, "fix": "", "alt": s.get("draft_uses") or "",
                        "recency": True, "study": text})
            continue
        out.append({"finding": f, "text": text, "fix": fix})
    return out


def _recency_items(slug: str, it: dict, rows: dict, held: dict) -> list[dict]:
    """One item per body sentence a recency finding is about
    (findings.recency_targets: every on-page row whose binding rests on the
    study's source; never the source-list line), each with the recency result
    as its reason and the sentence's own bound passages. A sentence already
    ruled for this finding (sentence_rulings) is not ruled again. With no such
    sentence (findings.RECENCY_UNMATCHED), none: a finding with no target is
    not ruled on the study's name; the preflight STOPs on it instead."""
    import findings as F
    f = it["finding"]
    _sids, keys = F.recency_targets(slug, it["study"], rows)
    done = {x.get("row") for x in f.get("sentence_rulings") or []}
    base = {"finding": f, "kind": "gate %s finding (%s)" % (f.get("kind"), f.get("gate_verdict")),
            "reason": f.get("gate_said") or "", "proposed": "", "recency": True, "study": it["study"]}
    if not keys:
        return []          # RECENCY_UNMATCHED: not ruled; the preflight STOPs on it
    return [dict(base, key=("row", k), sentence=rows[k]["sentence"], quotes=quotations(rows[k], held),
                 ref={"finding_id": f.get("id"), "row": k, "sentence_found": True})
            for k in keys if k not in done]


def _gate_items(rows: dict, report: dict, doc: dict, held: dict, slug: str | None = None) -> list[dict]:
    out = []
    for it in gate_items(report, doc):
        f = it["finding"]
        if it.get("recency") and slug:
            out += _recency_items(slug, it, rows, held)
            continue
        hit = _row_for(rows, it["text"]) or (_row_for(rows, it["alt"]) if it.get("alt") else None)
        sentence = hit[1]["sentence"] if hit else it["text"]
        out.append({"key": sentence_key(hit, sentence), "sentence": sentence, "finding": f,
                    "kind": "gate %s finding (%s)" % (f.get("kind"), f.get("gate_verdict")),
                    "reason": f.get("gate_said") or "", "proposed": it["fix"],
                    "quotes": quotations(hit[1], held) if hit else [],
                    "ref": {"finding_id": f.get("id"), "row": hit[0] if hit else None,
                            "sentence_found": bool(hit)}})
    return out


def rule_gate(slug: str, call, *, P=None, report: dict | None = None, rows: dict | None = None,
              held: dict | None = None, failed: list | None = None) -> list[dict]:
    """Rule every undecided gate finding, one call per sentence, and record each
    in gate-findings.json."""
    import findings as F
    P = P or _publish()
    require_study(slug, P)
    if report is None:
        page = P.ROOT / P.issue_cfg(slug)["page"]
        report = json.loads(page.with_suffix(page.suffix + ".gate.json").read_text(encoding="utf-8"))
    if rows is None:
        import bindings as B
        rows = B.load(slug).get("bindings") or {}
    if held is None:
        held = held_texts(slug)
    doc = F.load(slug)
    done = []
    recency: dict = {}
    keep, person = split_protected(_gate_items(rows, report, doc, held, slug), rows)
    route_to_person("gate", person, log_path(slug))
    # A GATE FINDING ON A PROTECTED SENTENCE (post-study, mid-rerun tool fix,
    # 2026-10-28) is recorded not_ruled_protected, as an advocate or omission
    # item is closed (fix 7), so it can settle: findings.check accepts it only
    # while every target it names is protected. A recency finding's other
    # sentences are still ruled, one each; it settles when all have an answer.
    on = datetime.now(timezone.utc).date().isoformat()
    for it in person:
        f = it["finding"]
        why = ("the sentence is protected (%s); a protected sentence is never ruled by the model; "
               "left for a person" % it["protected"])
        if it.get("recency") and it["ref"].get("row"):
            f.setdefault("sentence_rulings", []).append({
                "row": it["ref"]["row"], "sentence": it["sentence"], "decision": F.NOT_RULED_PROTECTED,
                "protected": it["protected"], "source_id": "", "quote": "", "why": why,
                "ruling": None, "ruled": "ruling.py gate, not ruled: protected sentence", "on": on})
            recency[f.get("id")] = (f, it["study"])
            continue
        f.update({"decision": F.NOT_RULED_PROTECTED, "protected_targets": [it["sentence"]],
                  "source_id": "", "quote": "", "why": why, "by": BY_PROTECTED, "on": on})
        f.pop("_fill_in", None)
        done.append(f)
    for group in by_sentence(keep):
        r = _try_sentence("gate", group, held, call, log_path(slug), failed)
        if r is None:
            continue
        got, quotes, psha = r
        q = got.get("quotation")
        sid, quote = (quotes[q - 1] if q else ("", ""))
        if not q:
            decision = "judgement"
        else:
            decision = "rejected" if got["ruling"] == "reject" else "accepted"
        together = _together(group, lambda it: it["finding"].get("id"))
        for it in group:
            f = it["finding"]
            if it.get("recency") and it["ref"].get("row"):
                # one ruling per body sentence; the finding is settled below,
                # when every sentence it is about has one
                sr = {"row": it["ref"]["row"], "sentence": it["sentence"], "decision": decision,
                      "source_id": sid, "quote": quote, "why": got.get("reason") or "",
                      "ruling": got["ruling"], "ruling_text": got.get("text"),
                      "ruled": "ruling.py gate, prompt %s" % psha[:12], "on": datetime.now(timezone.utc).date().isoformat()}
                if together:
                    sr["ruled_together"] = together
                f.setdefault("sentence_rulings", []).append(sr)
                recency[f.get("id")] = (f, it["study"])
                continue
            f.update({"decision": decision, "source_id": sid, "quote": quote,
                      "why": got.get("reason") or "", "by": BY, "on": datetime.now(timezone.utc).date().isoformat(),
                      "ruling": got["ruling"], "ruling_text": got.get("text"),
                      "ruled": "ruling.py gate, prompt %s" % psha[:12]})
            if together:
                f["ruled_together"] = together
            f.pop("_fill_in", None)
            done.append(f)
    for f, study in recency.values():
        if _settle_recency(slug, f, rows, study):
            done.append(f)
    F.save(slug, doc)
    return done


def _settle_recency(slug: str, f: dict, rows: dict, study: str) -> bool:
    """Decide a recency finding once every body sentence it is about has a
    ruling: accepted if any sentence's ruling accepts or amends (citing a
    quotation), rejected if all reject (citing one), judgement where none
    cites a quotation. The texts to apply are the sentences' own
    (sentence_rulings, and each ruling's log record)."""
    import findings as F
    _sids, keys = F.recency_targets(slug, study, rows)
    srs_all = f.get("sentence_rulings") or []
    if not keys or set(keys) - {x["row"] for x in srs_all}:
        return False                         # a sentence still to rule (RULING_FAILED)
    # a protected sentence's answer is not_ruled_protected (rule_gate); the
    # decision is the other sentences', or not_ruled_protected if all are
    protected = [x for x in srs_all if x["decision"] == F.NOT_RULED_PROTECTED]
    srs = [x for x in srs_all if x["decision"] != F.NOT_RULED_PROTECTED]
    if protected:
        f["protected_targets"] = [x["sentence"] for x in protected]
    if not srs:
        f.update({"decision": F.NOT_RULED_PROTECTED, "source_id": "", "quote": "",
                  "why": "; ".join("%s: %s" % (x["row"], x["why"]) for x in protected),
                  "by": BY_PROTECTED, "on": datetime.now(timezone.utc).date().isoformat(),
                  "ruled": "ruling.py gate, every body sentence protected (sentence_rulings)"})
        f.pop("_fill_in", None)
        return True
    changed = [x for x in srs if x["ruling"] in ("accept", "amend")]
    pool = changed or srs
    cited = next((x for x in pool if x["decision"] != "judgement"), None)
    if changed:
        decision = "accepted" if cited else "judgement"
    else:
        decision = "rejected" if cited else "judgement"
    f.update({"decision": decision, "source_id": cited["source_id"] if cited else "",
              "quote": cited["quote"] if cited else "",
              "why": "; ".join("%s: %s" % (x["row"], x["why"]) for x in srs),
              "by": BY, "on": datetime.now(timezone.utc).date().isoformat(),
              "ruling": "accept" if changed else "reject",
              "ruling_text": None, "ruled": "ruling.py gate, one ruling per body sentence "
                                            "(sentence_rulings)"})
    f.pop("_fill_in", None)
    return True



def _conclusion_items(review: dict, rows: dict, held: dict) -> list[dict]:
    import conclusion_judge as CJ
    out = []
    for k, e in sorted((review.get("sentences") or {}).items()):
        if not e.get("flagged") or CJ.decided(e):
            continue
        out.append({"key": ("row", k), "sentence": e.get("sentence") or "", "entry": e,
                    "kind": "conclusion judge: %s" % e.get("label"), "reason": e.get("reason") or "",
                    "proposed": "", "quotes": quotations(rows.get(k) or {}, held),
                    "ref": {"review_key": k, "sentence_sha": e.get("sentence_sha")}})
    return out


def rule_conclusions(slug: str, call, *, P=None, rows: dict | None = None,
                     held: dict | None = None, failed: list | None = None) -> list[dict]:
    """Rule every flagged, undecided conclusion-judge entry and record it with
    conclusion_judge.decide. The review holds one entry per sentence, so each
    sentence is one call already; it goes through the same grouping."""
    import conclusion_judge as CJ
    P = P or _publish()
    require_study(slug, P)
    if rows is None:
        import bindings as B
        rows = B.load(slug).get("bindings") or {}
    if held is None:
        held = held_texts(slug)
    review = CJ.load_review(slug)
    done = []
    # A protected sentence is a person's, never the ruling model's: a review
    # written before judged_rows excluded it must not rewrite it either
    # (WHU-S08, ruling b6caee39a4c1249d narrowed the question this way).
    for group in by_sentence(_rulable("conclusions", _conclusion_items(review, rows, held), rows,
                                      log_path(slug))):
        r = _try_sentence("conclusion", group, held, call, log_path(slug), failed)
        if r is None:
            continue
        got, _q, _s = r
        decision = "rejected" if got["ruling"] == "reject" else "accepted"
        why = got.get("reason") or ""
        if decision == "accepted":
            why += " New text: %s" % json.dumps(got.get("text"), ensure_ascii=False)
        for it in group:
            done.append(CJ.decide(slug, it["entry"]["sentence_sha"], decision, BY, why))
    return done


def _changecheck_items(slug: str, rows: dict, held: dict, page_html: str):
    import changecheck as C
    doc = C.load_reviews(slug)
    mine = [r for r in doc.get("reviews") or [] if r.get("sha") == C.page_sha(page_html)]
    if not mine:
        return doc, None
    have = {d.get("key") for d in doc.get("dispositions") or []}
    out, seen = [], set()
    for f in mine[-1].get("findings") or []:
        key = C.finding_key(f)
        if key in have or key in seen or not (f.get("sentence") or "").strip():
            continue                         # decided already, or UNRUN (nothing to rule on)
        seen.add(key)
        hit = _row_for(rows, f["sentence"])
        reason = f.get("why") or ""
        if (f.get("other") or "").strip():
            reason += " Against: %s" % " ".join(f["other"].split())
        out.append({"key": sentence_key(hit, f["sentence"]), "sentence": f["sentence"], "finding": f,
                    "finding_key": key, "kind": "changecheck: %s" % f.get("kind"), "reason": reason,
                    "proposed": "", "quotes": quotations(hit[1], held) if hit else [],
                    "ref": {"finding_key": key, "row": hit[0] if hit else None}})
    return doc, out


def rule_changecheck(slug: str, call, *, P=None, rows: dict | None = None,
                     held: dict | None = None, page_html: str | None = None,
                     failed: list | None = None) -> list[dict]:
    """Rule every finding of the latest changecheck review of the current page
    that has no disposition, one call per sentence, and record each as a
    disposition."""
    import changecheck as C
    P = P or _publish()
    require_study(slug, P)
    if page_html is None:
        page_html = (P.ROOT / P.issue_cfg(slug)["page"]).read_text(encoding="utf-8")
    if rows is None:
        import bindings as B
        rows = B.load(slug).get("bindings") or {}
    if held is None:
        held = held_texts(slug)
    doc, items = _changecheck_items(slug, rows, held, page_html)
    if items is None:
        raise SystemExit("no changecheck review of the current page; run changecheck.py first")
    done = []
    for group in by_sentence(_rulable("changecheck", items, rows, log_path(slug))):
        r = _try_sentence("changecheck", group, held, call, log_path(slug), failed)
        if r is None:
            continue
        got, _q, psha = r
        together = _together(group, lambda it: it["finding_key"])
        for it in group:
            f = it["finding"]
            d = {"key": it["finding_key"], "kind": f.get("kind"), "sentence": f["sentence"],
                 "decision": "reject" if got["ruling"] == "reject" else "accept",
                 "by": BY, "on": datetime.now(timezone.utc).date().isoformat(), "reason": got.get("reason") or "",
                 "ruling": got["ruling"], "ruling_text": got.get("text"),
                 "ruled": "ruling.py changecheck, prompt %s" % psha[:12]}
            if together:
                d["ruled_together"] = together
            doc.setdefault("dispositions", []).append(d)
            done.append(d)
    C.record_path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
    return done


def advocate_items(slug: str, case: Path | None = None) -> list[dict]:
    """Every OBJECTION in the advocate's briefs whose adjudication item is still
    open, with its heading, as source_advocate numbers them."""
    import source_advocate as SA
    import source_store as store
    d = (case or store.case_dir(slug)) / "advocate"
    out = []
    is_protected = SA.protected_check(slug)
    for bf in sorted(d.glob("*-briefs.json")) if d.exists() else []:
        if "TEST" in bf.name:
            continue
        adj = bf.with_name(bf.name[:-len("-briefs.json")] + "-adjudication.md")
        if not adj.exists():
            continue
        chunks = {c.splitlines()[0][4:].split(" ")[0]: c
                  for c in re.split(r"(?=^### )", adj.read_text(encoding="utf-8"), flags=re.M)[1:]}
        n = 0
        for b in json.loads(bf.read_text(encoding="utf-8")):
            for o in b.get("objections") or []:
                n += 1
                head = "%s-%02d" % (b["source"], n)
                if b.get("mode", "objections") != "objections":
                    continue
                c = chunks.get(head)
                if c is None or SA._closed(c, "objections", is_protected):
                    continue
                out.append({"file": adj, "head": head, "source": b["source"], "objection": o,
                            "principal": b.get("principal")})
    return out


def _close_item(path: Path, head: str, merit: str, effect: str, did: str) -> None:
    """Fill the template's empty MERIT / EFFECT / DID lines of ONE item."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?=^### )", text, flags=re.M)
    for i, c in enumerate(parts):
        if c.startswith("### %s " % head) or c.startswith("### %s\n" % head):
            lines = c.split("\n")
            for j, l in enumerate(lines):
                if l.rstrip() == "MERIT:":
                    lines[j] = "MERIT:  " + merit
                elif l.rstrip() == "EFFECT:":
                    lines[j] = "EFFECT: " + effect
                elif l.rstrip() == "DID:":
                    lines[j] = "DID:    " + did
            parts[i] = "\n".join(lines)
            break
    else:
        raise RulingError("no item %s in %s" % (head, path))
    path.write_text("".join(parts), encoding="utf-8")


def _advocate_items(slug: str, rows: dict, held: dict, case: Path | None = None) -> list[dict]:
    """MISSTATES objections only: a LEAVES_OUT objection (declared, or
    suspected from its wording) is an omission, ruled by rule_omissions (fix 2),
    never by asking whether the source supports the sentence it is pinned to."""
    import source_advocate as SA
    out = []
    for it in advocate_items(slug, case):
        o = it["objection"]
        if SA.omission_kind(o)[0] == SA.LEAVES_OUT:
            continue
        claim = o.get("claim_quoted") or ""
        hit = _row_for(rows, claim)
        sentence = hit[1]["sentence"] if hit else claim
        quotes = quotations(hit[1], held) if hit else []
        reason = o.get("objection") or ""
        if (o.get("why") or "").strip():
            reason += " Why it matters: %s" % o["why"].strip()
        says = (o.get("source_says") or "").strip()
        if says:
            if _in_held(says, held.get(it["source"]) or ""):
                if (it["source"], says) not in quotes:
                    quotes.append((it["source"], says))
            else:
                reason += (" The objection quotes its document, but that quotation is not in "
                           "the held text of the document.")
        out.append({"key": sentence_key(hit, sentence), "sentence": sentence, "item": it,
                    "kind": "source advocate objection (%s)" % (o.get("severity") or "?"),
                    "reason": reason, "proposed": "", "quotes": quotes,
                    "ref": {"advocate_item": it["head"], "file": it["file"].name,
                            "row": hit[0] if hit else None}})
    return out


def rule_advocate(slug: str, call, *, P=None, rows: dict | None = None,
                  held: dict | None = None, case: Path | None = None,
                  failed: list | None = None) -> list[dict]:
    """Rule every open source-advocate objection, one call per sentence, and
    close its item."""
    P = P or _publish()
    require_study(slug, P)
    if rows is None:
        import bindings as B
        rows = B.load(slug).get("bindings") or {}
    if held is None:
        held = held_texts(slug)
    done = []
    for group in by_sentence(_rulable("advocate", _advocate_items(slug, rows, held, case), rows,
                                      log_path(slug))):
        r = _try_sentence("advocate", group, held, call, log_path(slug), failed)
        if r is None:
            continue
        got, _q, psha = r
        tag = "ruled by %s, prompt %s" % (BY, psha[:12])
        together = _together(group, lambda it: it["item"]["head"])
        if together:
            tag += ", together with every finding on this sentence (%s)" % ", ".join(together)
        for it in group:
            if got["ruling"] == "reject":
                _close_item(it["item"]["file"], it["item"]["head"], "no — %s" % (got.get("reason") or ""),
                            "none", "nothing; %s" % tag)
            else:
                text = got.get("text") or ""
                _close_item(it["item"]["file"], it["item"]["head"], "yes — %s" % (got.get("reason") or ""),
                            "corrects",
                            ("the sentence is to be replaced word for word with: %s; %s"
                             % (json.dumps(text, ensure_ascii=False), tag)) if text else
                            "the sentence is to be cut; %s" % tag)
            done.append({"item": it["item"]["head"], **got})
    return done


def _dangling_ruled(lp: Path) -> set:
    """(term, sentence) pairs already ruled: one per record, or one per finding
    a grouped record covers."""
    out = set()
    for line in (lp.read_text(encoding="utf-8").splitlines() if lp.exists() else []):
        r = json.loads(line) if line.strip() else {}
        if r.get("ruling_kind") != "dangling":
            continue
        s = (r.get("inputs") or {}).get("sentence")
        for c in r.get("covers") or [{"term": r.get("term")}]:
            out.add((c.get("term"), s))
    return out


def _dangling_items(case: Path, page_html: str, rows: dict, held: dict) -> list[dict]:
    import applied_check as AC
    before = _dangling_ruled(case / "rulings" / "rulings.jsonl")
    out = []
    for f in AC.dangling(case, page_html):
        if (f["term"], f["later_sentence"]) in before:
            continue
        hit = _row_for(rows, f["later_sentence"])
        reason = ("It uses %r, which no earlier sentence on the page now introduces: a ruling "
                  "changed the sentence that did, which now reads: %s"
                  % (f["term"], json.dumps(f["applied_sentence"], ensure_ascii=False)))
        out.append({"key": sentence_key(hit, f["later_sentence"]), "sentence": f["later_sentence"],
                    "kind": "dangling reference", "reason": reason, "proposed": "",
                    "quotes": quotations(hit[1], held) if hit else [], "term": f["term"],
                    "ref": {"term": f["term"], "after_ruling": f["log"], "row": hit[0] if hit else None}})
    return out


def rule_dangling(slug: str, call, *, P=None, rows: dict | None = None, held: dict | None = None,
                  page_html: str | None = None, case: Path | None = None,
                  failed: list | None = None) -> list[dict]:
    """Rule every term an applied ruling removed that a later sentence still
    uses while no earlier sentence now introduces it (applied_check.dangling).
    The model gets the later sentence, the finding (both sentences: the later
    one, and the applied text that no longer introduces the term) and the
    later sentence's bound passages; several terms on one later sentence are
    one call. A (term, sentence) already ruled is not ruled again."""
    import source_store as store
    P = P or _publish()
    require_study(slug, P)
    case = case or store.case_dir(slug)
    if page_html is None:
        page_html = (P.ROOT / P.issue_cfg(slug)["page"]).read_text(encoding="utf-8")
    if rows is None:
        import bindings as B
        rows = B.load(slug).get("bindings") or {}
    if held is None:
        held = held_texts(slug)
    done = []
    for group in by_sentence(_rulable("dangling", _dangling_items(case, page_html, rows, held), rows,
                                      case / "rulings" / "rulings.jsonl")):
        r = _try_sentence("dangling", group, held, call, case / "rulings" / "rulings.jsonl", failed)
        if r is None:
            continue
        got, _q, _s = r
        for it in group:
            done.append({"term": it["term"], **got})
    return done


# ---------------------------------------------------------------------------
# omissions (post-study fix 2, step 4)
# ---------------------------------------------------------------------------
#
# A LEAVES_OUT objection is not ruled by asking whether the source supports the
# sentence it is pinned to (that is how WHU-S07's S003-13 was rejected, at
# rulings.jsonl:12). Code decides first (omissions.py): is the finding in the
# held text (else NOT_IN_SOURCE, no call), and one finding is ruled once. The
# model then decides scope and materiality and drafts an ADD; code checks
# what it can: the scope element is real, the span is inside the finding, the
# anchor is not a protected sentence, and the budgets. Anything code refuses
# goes to a person, never off the record. docs/whu-fix2-omission-rulings-design.md.

OMISSION_CLOSE = {"ADD": ("yes", "sharpens"), "OUT_OF_SCOPE": ("no", "none"),
                  "NOT_MATERIAL": ("no", "none"), "NOT_IN_SOURCE": ("no", "none")}


def _leaves_out(slug: str, case: Path | None = None) -> list[dict]:
    import source_advocate as SA
    return [it for it in advocate_items(slug, case) if SA.omission_kind(it["objection"])[0] == SA.LEAVES_OUT]


def _close_omission(path: Path, head: str, outcome: str, did: str) -> None:
    """Close one item with the omission outcome: its OMISSION/DID lines, or,
    on an item written before fix 2, MERIT/EFFECT/DID saying the same."""
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?=^### )", text, flags=re.M)
    for i, c in enumerate(parts):
        if not (c.startswith("### %s " % head) or c.startswith("### %s\n" % head)):
            continue
        if re.search(r"^OMISSION:", c, re.M):
            lines = c.split("\n")
            for j, l in enumerate(lines):
                if l.rstrip() == "OMISSION:":
                    lines[j] = "OMISSION: " + outcome.lower()
                elif l.rstrip() == "DID:":
                    lines[j] = "DID:      " + did
            parts[i] = "\n".join(lines)
            path.write_text("".join(parts), encoding="utf-8")
            return
        merit, effect = OMISSION_CLOSE[outcome]
        _close_item(path, head, "%s — omission ruling: %s" % (merit, outcome.lower()), effect, did)
        return
    raise RulingError("no item %s in %s" % (head, path))


def _anchor_index(anchor: str, sents: list[str]) -> int | None:
    a = _norm(anchor)
    if not a:
        return None
    for i, s in enumerate(sents):
        if a in _norm(s):
            return i
    return None


def _placement(anchor: str, sents: list[str], rows: dict) -> tuple[str | None, str]:
    """(the page sentence an ADD goes after, how). After the anchor; if the
    anchor is protected (fix 1), after the nearest unprotected sentence before
    it, never inside or in place of a protected one. None: a person places it."""
    import bindings as B
    i = _anchor_index(anchor, sents)
    if i is None:
        return None, "the anchor is not on the page"
    for j in range(i, -1, -1):
        s = sents[j]
        if B.protected_kind(s, rows.get(B.fingerprint(s))) is None:
            return s, "after the anchor" if j == i else "after the nearest unprotected sentence before a protected anchor"
    return None, "no unprotected sentence at or before the anchor"


def omission_payload(question: str, scope: dict, reader: str, finding: str, context: str,
                     anchor_window: list[str], already: list[str]) -> dict:
    sc = "Covers: %s\nOut of scope:\n%s" % (
        scope.get("covers") or "(not stated)",
        "\n".join("- %s (%s)" % (o.get("what"), o.get("why") or "") for o in scope.get("out") or []) or "(none declared)")
    p = {"question": question or "", "scope": sc, "reader": reader or "(not named)",
         "finding": "Quotation: \"%s\"\nIn its document: ...%s..." % (finding, " ".join((context or "").split())),
         "anchor": "\n".join(anchor_window) or "(no anchor on the page)",
         "already_on_page": "\n".join("- %s" % s for s in already[:30]) or "(nothing)"}
    assert tuple(p) == OMISSION_FIELDS
    return p


def rule_omissions(slug: str, call, *, P=None, rows: dict | None = None, held: dict | None = None,
                   case: Path | None = None, page_sentences: list[str] | None = None,
                   scope: dict | None = None, reader: str | None = None, licensed: set | None = None,
                   reask=None, failed: list | None = None) -> list[dict]:
    """Rule every open LEAVES_OUT advocate objection. Returns one decision per
    finding: {"outcome", "origins", ...}; for ADD also "text", "span",
    "insert_after". `reask(system, user)` answers source_advocate's one-time
    re-ask for an omission quoting what the page already uses (default: a
    metered call, under fc.enter_issue)."""
    import audit_stage as A
    import bindings as B
    import omissions as O
    import premise as PM
    import source_advocate as SA
    import source_store as store
    P = P or _publish()
    require_study(slug, P)
    case = case or store.case_dir(slug)
    if rows is None:
        rows = B.load(slug).get("bindings") or {}
    if held is None:
        held = held_texts(slug)
    if page_sentences is None:
        page_sentences = B.page_sentences(slug)
    scope = scope if scope is not None else PM.scope_of(slug)
    if reader is None:
        reader = str(((PM.load(slug) or {}).get("reader_with_a_decision")) or "")
    lic = set(licensed) if licensed is not None else A.licensed_ids(slug)
    log = case / "rulings" / "rulings.jsonl"

    def bound_spans(sid: str) -> list[str]:
        return [q for r in rows.values() if r.get("on_page") for s_, q in quotations(r, held) if s_ == sid]

    def already(sid: str) -> list[str]:
        return [r["sentence"] for r in rows.values()
                if r.get("on_page") and sid in A.sources_of(r) and r.get("sentence")]

    items, found = {}, []
    for it in _leaves_out(slug, case):
        o, sid = it["objection"], it["source"]
        items[it["head"]] = it
        if sid in lic:
            route_to_person("omissions", [{"protected": "licensed source", "sentence": o.get("claim_quoted"),
                                           "kind": "omission", "ref": {"advocate_item": it["head"]}}], log)
            continue
        if SA.needs_reask(o, held.get(sid) or "", bound_spans(sid)):
            o = SA.reask_omission({"source": sid, "principal": it.get("principal")}, o, held.get(sid) or "",
                                  bound_spans(sid), ask=reask)
            it["objection"] = o
        found.append(O.precheck({"source": sid, "quote": o.get("source_says") or "", "origin": it["head"]}, held))

    done = []
    counts = {"ADD": 0, "DECLARED": 0}
    for e in O.load(case).get("omissions") or []:
        if e.get("outcome") == O.ADD:
            counts["ADD"] += 1
        elif e.get("outcome") in (O.OUT_OF_SCOPE, O.NOT_MATERIAL):
            counts["DECLARED"] += 1
    n_body = len(page_sentences)

    def close(f: dict, outcome: str, did: str, **extra) -> None:
        for h in f.get("origins") or [f.get("origin")]:
            _close_omission(items[h]["file"], h, outcome, did)
        done.append(dict({"outcome": outcome, "origins": f.get("origins") or [f.get("origin")],
                          "source": f.get("source")}, **extra))

    def to_person(f: dict, why: str) -> None:
        O.record(case, f, held_text=held.get(f.get("source")), outcome=O.TO_PERSON, reason=why,
                 by="code (ruling.py omissions)")
        route_to_person("omissions", [{"protected": "omission: " + why, "sentence": f.get("anchor") or "",
                                       "kind": "omission", "ref": {"origins": f.get("origins")}}], log)
        done.append({"outcome": O.TO_PERSON, "origins": f.get("origins"), "why": why})

    for f in [f for f in found if f.get("outcome") == O.NOT_IN_SOURCE]:
        f["origins"] = [f["origin"]]
        O.record(case, f, held_text=held.get(f.get("source")), outcome=O.NOT_IN_SOURCE, reason=f["why"],
                 by="code (omissions.precheck)")
        close(f, O.NOT_IN_SOURCE, "nothing added: %s" % f["why"])

    for f in O.fill_quotes(O.merge([f for f in found if f.get("at")]), held):
        heads = f["origins"]
        anchor = items[heads[0]]["objection"].get("claim_quoted") or ""
        f["anchor"] = anchor
        i = _anchor_index(anchor, page_sentences)
        window = page_sentences[max(0, i - 1):i + 2] if i is not None else []
        context = A.in_context(f["held_quote"], held[f["source"]], QUOTE_AROUND)
        p = omission_payload(scope.get("question"), scope, reader, f["held_quote"], context, window,
                             already(f["source"]))
        try:
            got = rule("omission", p, 0, call, log, {"covers": [{"advocate_item": h} for h in heads],
                                                    "source": f["source"], "offsets": f["at"]})
        except RulingFailed as e:
            print("  %s: %s -- left open" % (RULING_FAILED, e))
            if failed is not None:
                failed.append({"kind": "omission", "refs": heads, "why": str(e)})
            continue
        except RulingError as e:
            to_person(f, "the ruling reply was not usable (%s)" % e)
            continue
        outcome, rid = got["outcome"], None
        rid = _last_id(log)
        if outcome == "OUT_OF_SCOPE":
            ok, why = O.scope_element_ok(got["scope_element"], scope)
            if not ok:
                to_person(f, "OUT_OF_SCOPE refused by code: %s" % why)
                continue
            if counts["DECLARED"] >= O.declaration_budget(n_body):
                to_person(f, "over the declarations budget (%d)" % O.declaration_budget(n_body))
                continue
            counts["DECLARED"] += 1
            O.record(case, f, held_text=held.get(f.get("source")), outcome=O.OUT_OF_SCOPE, reason=got["reason"], by=BY,
                     reason_for_reader=got.get("reason_for_reader") or "",
                     element=got["scope_element"], ruling=rid)
            close(f, O.OUT_OF_SCOPE, "nothing added; out of scope (%s); listed for readers"
                  % got["scope_element"], element=got["scope_element"])
        elif outcome == "NOT_MATERIAL":
            sev = [items[h]["objection"] for h in heads]
            if any((o.get("severity") or "").upper() == "SERIOUS"
                   and (o.get("changes_conclusion") or "").upper() == "CHANGES" for o in sev):
                to_person(f, "NOT_MATERIAL on a SERIOUS objection that CHANGES the conclusion")
                continue
            if counts["DECLARED"] >= O.declaration_budget(n_body):
                to_person(f, "over the declarations budget (%d)" % O.declaration_budget(n_body))
                continue
            counts["DECLARED"] += 1
            O.record(case, f, held_text=held.get(f.get("source")), outcome=O.NOT_MATERIAL, reason=got["reason"],
                     by=BY, ruling=rid, reason_for_reader=got.get("reason_for_reader") or "")
            close(f, O.NOT_MATERIAL, "nothing added; not material; listed for readers")
        else:
            if O.locate(got["span"], f["held_quote"]) is None:
                to_person(f, "the ADD's span is not in the finding")
                continue
            after, how = _placement(anchor, page_sentences, rows)
            if after is None:
                to_person(f, "no place for the ADD: %s" % how)
                continue
            if counts["ADD"] >= O.add_budget(n_body):
                to_person(f, "over the ADD budget (%d)" % O.add_budget(n_body))
                continue
            counts["ADD"] += 1
            O.record(case, f, held_text=held.get(f.get("source")), outcome=O.ADD, reason=got["reason"], by=BY, ruling=rid,
                     on_page=B.fingerprint(got["text"]), after=B.fingerprint(after))
            close(f, O.ADD, "to be inserted word for word after %s: %s"
                  % (json.dumps(after, ensure_ascii=False), json.dumps(got["text"], ensure_ascii=False)),
                  text=got["text"], span=got["span"], insert_after=after, placement=how, at=f["at"])
    return done


def _last_id(log: Path) -> str | None:
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return json.loads(lines[-1]).get("id") if lines else None


# ---------------------------------------------------------------------------
# assessment judgements: relevance (post-study fix 3, step 2)
# ---------------------------------------------------------------------------

def relevance_payload(question: str, scope: dict, judgement: str) -> dict:
    sc = "Covers: %s\nOut of scope:\n%s" % (
        scope.get("covers") or "(not stated)",
        "\n".join("- %s (%s)" % (o.get("what"), o.get("why") or "") for o in scope.get("out") or []) or "(none declared)")
    p = {"question": question or "", "scope": sc, "judgement": " ".join((judgement or "").split())}
    assert tuple(p) == RELEVANCE_FIELDS
    return p


def rule_judgements(slug: str, call, *, P=None, held: dict | None = None, scope: dict | None = None,
                    case: Path | None = None, failed: list | None = None) -> list[dict]:
    """Rule relevance for every held assessment judgement with no decision on
    its current text (judgements.candidates), one call each. A 'relevant'
    answer is recorded only when code finds its question words in the
    question or the premise scope; otherwise the candidate goes to a person."""
    import judgements as J
    import premise as PM
    import source_store as store
    P = P or _publish()
    require_study(slug, P)
    case = case or store.case_dir(slug)
    held = held if held is not None else held_texts(slug)
    scope = scope if scope is not None else PM.scope_of(slug)
    log = case / "rulings" / "rulings.jsonl"
    to_rule, _person = J.undecided(J.candidates(held), J.load(case), held)
    done = []
    for c in to_rule:
        text = held[c["source"]][c["at"][0]:c["at"][1]]
        p = relevance_payload(scope.get("question"), scope, text)
        try:
            got = rule("relevance", p, 0, call, log, {"candidate": c["key"], "source": c["source"],
                                                    "offsets": c["at"]})
        except RulingFailed as e:
            print("  %s: %s -- left open" % (RULING_FAILED, e))
            if failed is not None:
                failed.append({"kind": "relevance", "refs": [c["key"]], "why": str(e)})
            continue
        except RulingError as e:
            J.record(case, c, held[c["source"]], relevant=None, words="", by="code (ruling.py judgements)",
                     reason="the ruling reply was not usable (%s)" % e, to_person=True)
            route_to_person("judgements", [{"protected": "relevance unusable", "sentence": c["key"],
                                            "kind": "relevance", "ref": {"candidate": c["key"]}}], log)
            done.append({"key": c["key"], "relevant": None, "to_person": True})
            continue
        rid = _last_id(log)
        if got["relevant"]:
            ok, why = J.verify_words(got["question_words"], scope)
            if not ok:
                J.record(case, c, held[c["source"]], relevant=None, words=got["question_words"],
                         by="code (ruling.py judgements)", reason="relevance refused by code: %s" % why,
                         ruling=rid, to_person=True)
                route_to_person("judgements", [{"protected": "relevance words unverified", "sentence": c["key"],
                                                "kind": "relevance", "ref": {"candidate": c["key"]}}], log)
                done.append({"key": c["key"], "relevant": None, "to_person": True, "why": why})
                continue
        J.record(case, c, held[c["source"]], relevant=got["relevant"], words=got["question_words"],
                 reason=got["reason"], by=BY, ruling=rid)
        done.append({"key": c["key"], "relevant": got["relevant"], "section": c["section"]})
    return done


REASK_UNITS = 2      # a one-time omission re-ask (~$0.05) against an omission ruling (~$0.03)


def omission_units(slug: str, rulings: int, case: Path | None = None, held: dict | None = None,
                   rows: dict | None = None) -> int:
    """The stage cap's units for `ruling.py omissions`: the rulings, plus
    REASK_UNITS for each LEAVES_OUT objection that will be re-asked
    (source_advocate.needs_reask), counted as rule_omissions decides it."""
    import bindings as B
    import source_advocate as SA
    held = held if held is not None else held_texts(slug)
    rows = rows if rows is not None else (B.load(slug).get("bindings") or {})
    reasks = 0
    for it in _leaves_out(slug, case):
        sid = it["source"]
        bound = [q for r in rows.values() if r.get("on_page") for s_, q in quotations(r, held) if s_ == sid]
        if SA.needs_reask(it["objection"], held.get(sid) or "", bound):
            reasks += 1
    return rulings + REASK_UNITS * reasks


def pending(mode: str, slug: str, P=None) -> int:
    """How many calls MODE would make now -- one per sentence with findings --
    the units of the stage cap check, selected and grouped as each rule_*
    function selects and groups them, without a call."""
    import source_store as store
    P = P or _publish()
    case = store.case_dir(slug)
    import bindings as B
    rows = B.load(slug).get("bindings") or {}
    if mode == "gate":
        import findings as F
        page = P.ROOT / P.issue_cfg(slug)["page"]
        report = json.loads(page.with_suffix(page.suffix + ".gate.json").read_text(encoding="utf-8"))
        items = _gate_items(rows, report, F.load(slug), {}, slug)
    elif mode == "conclusions":
        import conclusion_judge as CJ
        items = _conclusion_items(CJ.load_review(slug), rows, {})
    elif mode == "changecheck":
        html = (P.ROOT / P.issue_cfg(slug)["page"]).read_text(encoding="utf-8")
        items = _changecheck_items(slug, rows, {}, html)[1] or []
    elif mode == "advocate":
        items = _advocate_items(slug, rows, {})
    elif mode == "dangling":
        html = (P.ROOT / P.issue_cfg(slug)["page"]).read_text(encoding="utf-8")
        items = _dangling_items(case, html, rows, {})
    elif mode == "judgements":
        import judgements as J
        held = held_texts(slug)
        return len(J.undecided(J.candidates(held), J.load(case), held)[0])
    elif mode == "omissions":
        # One call per merged, located finding: code's precheck is free.
        import omissions as O
        held = held_texts(slug)
        found = [O.precheck({"source": it["source"], "quote": it["objection"].get("source_says") or ""}, held)
                 for it in _leaves_out(slug, case)]
        return len([f for f in O.merge(found) if f.get("at")])
    else:
        raise ValueError(mode)
    # A protected sentence is a person's, never a call (split_protected).
    return len(by_sentence(split_protected(items, rows)[0]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gate", "conclusions", "changecheck", "advocate", "dangling", "omissions", "judgements"):
        s = sub.add_parser(name)
        s.add_argument("slug")
        s.add_argument("--cap", type=float, default=50.0,
                       help="this run's own ceiling; the issue cap and the day cap also apply")
        s.add_argument("--seed", type=int,
                       help="the consistency sample's seed (default: derived from the step id; logged)")
    a = ap.parse_args(argv)
    require_study(a.slug)
    import consistency as CS
    import stage_cap
    kind = MODE_KIND[a.cmd]
    n = pending(a.cmd, a.slug)
    # Rulings of this kind that no completed step sampled: a step that
    # stopped before its sample (a crash, a cap stop) is sampled by the run
    # that resumes it, together with this run's own rulings.
    carried = unsampled(log_path(a.slug), log_path(a.slug).parent / "consistency.jsonl", kind)
    # before the first paid call; the units include the consistency sample
    units = n + CS.sample_size(n + len(carried))
    if a.cmd == "omissions":
        stage_cap.guard("omissions", a.slug, omission_units(a.slug, units))
    elif a.cmd == "judgements":
        stage_cap.guard("judgements", a.slug, units)
    else:
        stage_cap.guard("rulings", a.slug, units)
    import audit_stage as A
    call = A.Caller(cap=a.cap, ledger_issue=a.slug)
    fn = {"gate": rule_gate, "conclusions": rule_conclusions,
          "changecheck": rule_changecheck, "advocate": rule_advocate,
          "dangling": rule_dangling, "omissions": rule_omissions, "judgements": rule_judgements}[a.cmd]
    if a.cmd == "omissions":
        import source_advocate as SA
        SA.fc.enter_issue(a.slug)        # the one-time re-asks are metered against the issue
    step = "%s-%s" % (a.cmd, datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    before = _log_lines(log_path(a.slug))
    if carried:
        print("  %d ruling(s) from a step that stopped before its consistency sample are "
              "carried into this step's sample" % len(carried))
    failed: list = []
    done = fn(a.slug, call, failed=failed)
    print("  %d ruling(s) recorded; log: %s" % (len(done), log_path(a.slug)))
    consistency_sample(a.slug, step, log_path(a.slug), before, call, seed=a.seed, kind=kind,
                       carried=carried)
    print("  usd this run: %.4f" % sum((c.get("usd") or 0) for c in call.calls))
    if failed:
        print("  %s: %d sentence(s), their findings left open (%s); run this step again"
              % (RULING_FAILED, len(failed), attempts_log(log_path(a.slug))))
        return 4
    return 0


def _log_lines(log: Path) -> int:
    return len(log.read_text(encoding="utf-8").splitlines()) if log.exists() else 0


def unsampled(log: Path, cons: Path, kind: str) -> list[dict]:
    """Rulings of KIND in LOG that no completed step sampled: made since the
    sample began (SAMPLED_SINCE), named by no step line's ruling_ids, and
    later than the last step line of KIND that predates ruling_ids (a step's
    rulings are all logged before its step line)."""
    import consistency as CS
    steps = [s for s in CS.load(cons) if s.get("type") == "step" and s.get("kind") == kind]
    covered = {i for s in steps for i in (s.get("ruling_ids") or [])}
    legacy = max((s.get("at") or "" for s in steps if "ruling_ids" not in s), default="")
    return [r for r in CS.load(log)
            if r.get("ruling_kind") == kind and r.get("id") and r["id"] not in covered
            and (r.get("at") or "") >= SAMPLED_SINCE and (r.get("at") or "") > legacy]


def consistency_sample(slug: str, step: str, log: Path, before: int, call, seed=None,
                       kind: str | None = None, carried: list | None = None) -> dict | None:
    """The ruling-model consistency sample (consistency.py) over the rulings
    this step appended to LOG after line BEFORE, and any CARRIED from a step of
    the same kind that stopped before its sample (unsampled): a seeded 20%, at
    least 1, re-run with the identical payload, logged, never applied."""
    import consistency as CS
    lines = log.read_text(encoding="utf-8").splitlines()[before:] if log.exists() else []
    recs = [json.loads(l) for l in lines if l.strip()]
    if kind is not None:
        recs = [r for r in recs if r.get("ruling_kind") == kind]
    new_ids = {r.get("id") for r in recs}
    carried = [r for r in (carried or []) if r.get("id") not in new_ids]
    recs = carried + recs
    if not recs:
        return None
    kind = recs[0].get("ruling_kind")
    line = CS.sample_step(step, slug, kind, recs, CS.ruling_reask(call), log.parent / "consistency.jsonl",
                          seed=seed, carried=[r.get("id") for r in carried])
    print("  consistency: re-ran %d of %d ruling(s) (seed %d): %d of %d usable pair(s) agree "
          "on decision and text; never applied" % (line["sampled"], line["rulings"], line["seed"],
                                                   line["agree"], line["usable"]))
    return line


if __name__ == "__main__":
    raise SystemExit(main())
