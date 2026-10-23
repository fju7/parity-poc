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
from datetime import date, datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MODEL = "claude-opus-5-5"
BY = "ruling model %s" % MODEL
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
             "advocate": "advocate", "dangling": "dangling"}
PROMPTS = {
    "audit": HERE / "audit_prompts" / "rule.md",
    "second-reader": HERE / "audit_prompts" / "rule.md",
    "conclusion": HERE / "audit_prompts" / "rule.md",
    "gate": HERE / "audit_prompts" / "rule_cite.md",
    "changecheck": HERE / "audit_prompts" / "rule.md",
    "advocate": HERE / "audit_prompts" / "rule.md",
    "dangling": HERE / "audit_prompts" / "rule.md",
}
# Several findings on one sentence, ruled in one call (GAP-019).
GROUP_FIELDS = ("sentence", "findings", "quoted_source_text")
GROUP_PROMPTS = {k: HERE / "audit_prompts" / ("rule_group_cite.md" if k == "gate" else "rule_group.md")
                 for k in PROMPTS}
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
    for k in (GROUP_FIELDS if grouped else RULE_FIELDS):
        t = t.replace("{%s}" % k, p[k])
    return t


def parse(kind: str, text: str, n_quotes: int) -> dict:
    s = (text or "").strip()
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
    for group in by_sentence(_gate_items(rows, report, doc, held, slug)):
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
                      "ruled": "ruling.py gate, prompt %s" % psha[:12], "on": date.today().isoformat()}
                if together:
                    sr["ruled_together"] = together
                f.setdefault("sentence_rulings", []).append(sr)
                recency[f.get("id")] = (f, it["study"])
                continue
            f.update({"decision": decision, "source_id": sid, "quote": quote,
                      "why": got.get("reason") or "", "by": BY, "on": date.today().isoformat(),
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
    srs = f.get("sentence_rulings") or []
    if not keys or set(keys) - {x["row"] for x in srs}:
        return False                         # a sentence still to rule (RULING_FAILED)
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
              "by": BY, "on": date.today().isoformat(),
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
    for group in by_sentence(_conclusion_items(review, rows, held)):
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
    for group in by_sentence(items):
        r = _try_sentence("changecheck", group, held, call, log_path(slug), failed)
        if r is None:
            continue
        got, _q, psha = r
        together = _together(group, lambda it: it["finding_key"])
        for it in group:
            f = it["finding"]
            d = {"key": it["finding_key"], "kind": f.get("kind"), "sentence": f["sentence"],
                 "decision": "reject" if got["ruling"] == "reject" else "accept",
                 "by": BY, "on": date.today().isoformat(), "reason": got.get("reason") or "",
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
                if c is None or SA._closed(c, "objections"):
                    continue
                out.append({"file": adj, "head": head, "source": b["source"], "objection": o})
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
    out = []
    for it in advocate_items(slug, case):
        o = it["objection"]
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
    for group in by_sentence(_advocate_items(slug, rows, held, case)):
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
    for group in by_sentence(_dangling_items(case, page_html, rows, held)):
        r = _try_sentence("dangling", group, held, call, case / "rulings" / "rulings.jsonl", failed)
        if r is None:
            continue
        got, _q, _s = r
        for it in group:
            done.append({"term": it["term"], **got})
    return done


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
    else:
        raise ValueError(mode)
    return len(by_sentence(items))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gate", "conclusions", "changecheck", "advocate", "dangling"):
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
    stage_cap.guard("rulings", a.slug, n + CS.sample_size(n + len(carried)))
    import audit_stage as A
    call = A.Caller(cap=a.cap, ledger_issue=a.slug)
    fn = {"gate": rule_gate, "conclusions": rule_conclusions,
          "changecheck": rule_changecheck, "advocate": rule_advocate,
          "dangling": rule_dangling}[a.cmd]
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
