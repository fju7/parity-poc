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
MAX_OUT = 1500
PROMPTS = {
    "audit": HERE / "audit_prompts" / "rule.md",
    "second-reader": HERE / "audit_prompts" / "rule.md",
    "conclusion": HERE / "audit_prompts" / "rule.md",
    "gate": HERE / "audit_prompts" / "rule_cite.md",
    "changecheck": HERE / "audit_prompts" / "rule.md",
    "advocate": HERE / "audit_prompts" / "rule.md",
    "dangling": HERE / "audit_prompts" / "rule.md",
}


class RulingError(Exception):
    pass


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prompt_sha(kind: str) -> str:
    return sha(PROMPTS[kind].read_text(encoding="utf-8"))


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
    shown = []
    for n, (sid, q) in enumerate(quotes, 1):
        # Located as the audit compares a quotation (audit_stage.locate: norm(),
        # enclosing quote marks aside), then mapped back to the document's own
        # offsets. Until 2026-10-20 this was an exact find of the first 30
        # characters, which a line break or a curly quote defeated.
        import audit_stage as A
        around = A.in_context(q, held.get(sid) or "", QUOTE_AROUND)
        shown.append("Quotation %d: \"%s\"\nIn its document: ...%s..." % (n, q, " ".join(around.split())))
    p = {"sentence": " ".join((sentence or "").split()), "kind": kind or "",
         "reason": reason or "", "proposed_text": proposed_text or "",
         "quoted_source_text": "\n\n".join(shown) or "(no source text is quoted for this sentence)"}
    assert tuple(p) == RULE_FIELDS
    return p


def build_prompt(kind: str, p: dict) -> str:
    t = PROMPTS[kind].read_text(encoding="utf-8")
    for k in RULE_FIELDS:
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


def rule(kind: str, p: dict, n_quotes: int, call, log: Path, ref: dict) -> dict:
    """One ruling: prompt, call, check, log. `call(prompt, max_tokens, role)`
    returns (text, usage) -- audit_stage.Caller, metered and capped, or a fake."""
    prompt = build_prompt(kind, p)
    text, usage = call(prompt, MAX_OUT, "rule-%s" % kind)
    got = parse(kind, text, n_quotes)
    rec = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "by": BY,
           "model": MODEL, "ruling_kind": kind, "prompt": str(PROMPTS[kind].relative_to(HERE)),
           "prompt_sha256": prompt_sha(kind), "inputs": p, "inputs_sha256": sha(json.dumps(p)),
           **ref, **got, "usage": usage}
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return got


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
        elif fid.startswith("rec-") and fid[4:].isdigit() and int(fid[4:]) <= len(rec):
            # A recency study that is not CURRENT (GAP-014): the sentence is the
            # one that relies on that readout, found by the study's name or by
            # the readout the gate says the draft uses.
            s = rec[int(fid[4:]) - 1]
            text = s.get("name") or ""
            out.append({"finding": f, "text": text, "fix": "", "alt": s.get("draft_uses") or ""})
            continue
        out.append({"finding": f, "text": text, "fix": fix})
    return out


def rule_gate(slug: str, call, *, P=None, report: dict | None = None, rows: dict | None = None,
              held: dict | None = None) -> list[dict]:
    """Rule every undecided gate finding and record each in gate-findings.json."""
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
    for it in gate_items(report, doc):
        f = it["finding"]
        hit = _row_for(rows, it["text"]) or (_row_for(rows, it["alt"]) if it.get("alt") else None)
        sentence = hit[1]["sentence"] if hit else it["text"]
        quotes = quotations(hit[1], held) if hit else []
        p = payload(sentence, "gate %s finding (%s)" % (f.get("kind"), f.get("gate_verdict")),
                    f.get("gate_said") or "", it["fix"], quotes, held)
        got = rule("gate", p, len(quotes), call, log_path(slug),
                   {"finding_id": f.get("id"), "row": hit[0] if hit else None,
                    "sentence_found": bool(hit)})
        q = got.get("quotation")
        sid, quote = (quotes[q - 1] if q else ("", ""))
        if not q:
            decision = "judgement"
        else:
            decision = "rejected" if got["ruling"] == "reject" else "accepted"
        f.update({"decision": decision, "source_id": sid, "quote": quote,
                  "why": got.get("reason") or "", "by": BY, "on": date.today().isoformat(),
                  "ruling": got["ruling"], "ruling_text": got.get("text"),
                  "ruled": "ruling.py gate, prompt %s" % prompt_sha("gate")[:12]})
        f.pop("_fill_in", None)
        done.append(f)
    F.save(slug, doc)
    return done


def rule_conclusions(slug: str, call, *, P=None, rows: dict | None = None,
                     held: dict | None = None) -> list[dict]:
    """Rule every flagged, undecided conclusion-judge entry and record it with
    conclusion_judge.decide."""
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
    for k, e in sorted((review.get("sentences") or {}).items()):
        if not e.get("flagged") or CJ.decided(e):
            continue
        row = rows.get(k) or {}
        quotes = quotations(row, held)
        p = payload(e.get("sentence") or "", "conclusion judge: %s" % e.get("label"),
                    e.get("reason") or "", "", quotes, held)
        got = rule("conclusion", p, len(quotes), call, log_path(slug),
                   {"review_key": k, "sentence_sha": e.get("sentence_sha")})
        decision = "rejected" if got["ruling"] == "reject" else "accepted"
        why = got.get("reason") or ""
        if decision == "accepted":
            why += " New text: %s" % json.dumps(got.get("text"), ensure_ascii=False)
        done.append(CJ.decide(slug, e["sentence_sha"], decision, BY, why))
    return done


def rule_changecheck(slug: str, call, *, P=None, rows: dict | None = None,
                     held: dict | None = None, page_html: str | None = None) -> list[dict]:
    """Rule every finding of the latest changecheck review of the current page
    that has no disposition, and record each as a disposition."""
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
    doc = C.load_reviews(slug)
    mine = [r for r in doc.get("reviews") or [] if r.get("sha") == C.page_sha(page_html)]
    if not mine:
        raise SystemExit("no changecheck review of the current page; run changecheck.py first")
    have = {d.get("key") for d in doc.get("dispositions") or []}
    done = []
    for f in mine[-1].get("findings") or []:
        key = C.finding_key(f)
        if key in have or not (f.get("sentence") or "").strip():
            continue                         # decided already, or UNRUN (nothing to rule on)
        hit = _row_for(rows, f["sentence"])
        quotes = quotations(hit[1], held) if hit else []
        reason = f.get("why") or ""
        if (f.get("other") or "").strip():
            reason += " Against: %s" % " ".join(f["other"].split())
        p = payload(f["sentence"], "changecheck: %s" % f.get("kind"), reason, "", quotes, held)
        got = rule("changecheck", p, len(quotes), call, log_path(slug),
                   {"finding_key": key, "row": hit[0] if hit else None})
        d = {"key": key, "kind": f.get("kind"), "sentence": f["sentence"],
             "decision": "reject" if got["ruling"] == "reject" else "accept",
             "by": BY, "on": date.today().isoformat(), "reason": got.get("reason") or "",
             "ruling": got["ruling"], "ruling_text": got.get("text"),
             "ruled": "ruling.py changecheck, prompt %s" % prompt_sha("changecheck")[:12]}
        doc.setdefault("dispositions", []).append(d)
        have.add(key)
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
        adj = d / ("%s-adjudication.md" % bf.name[:10])
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


def rule_advocate(slug: str, call, *, P=None, rows: dict | None = None,
                  held: dict | None = None, case: Path | None = None) -> list[dict]:
    """Rule every open source-advocate objection and close its item."""
    P = P or _publish()
    require_study(slug, P)
    if rows is None:
        import bindings as B
        rows = B.load(slug).get("bindings") or {}
    if held is None:
        held = held_texts(slug)
    done = []
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
        p = payload(sentence, "source advocate objection (%s)" % (o.get("severity") or "?"),
                    reason, "", quotes, held)
        got = rule("advocate", p, len(quotes), call, log_path(slug),
                   {"advocate_item": it["head"], "file": it["file"].name,
                    "row": hit[0] if hit else None})
        tag = "ruled by %s, prompt %s" % (BY, prompt_sha("advocate")[:12])
        if got["ruling"] == "reject":
            _close_item(it["file"], it["head"], "no — %s" % (got.get("reason") or ""), "none",
                        "nothing; %s" % tag)
        else:
            text = got.get("text") or ""
            _close_item(it["file"], it["head"], "yes — %s" % (got.get("reason") or ""), "corrects",
                        ("the sentence is to be replaced word for word with: %s; %s"
                         % (json.dumps(text, ensure_ascii=False), tag)) if text else
                        "the sentence is to be cut; %s" % tag)
        done.append({"item": it["head"], **got})
    return done


def rule_dangling(slug: str, call, *, P=None, rows: dict | None = None, held: dict | None = None,
                  page_html: str | None = None, case: Path | None = None) -> list[dict]:
    """Rule every term an applied ruling removed that a later sentence still
    uses while no earlier sentence now introduces it (applied_check.dangling).
    The model gets the later sentence, the finding (both sentences: the later
    one, and the applied text that no longer introduces the term) and the
    later sentence's bound passages. A (term, sentence) already ruled is not
    ruled again."""
    import applied_check as AC
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
    done_before = set()
    lp = case / "rulings" / "rulings.jsonl"
    if lp.exists():
        for line in lp.read_text(encoding="utf-8").splitlines():
            r = json.loads(line) if line.strip() else {}
            if r.get("ruling_kind") == "dangling":
                done_before.add((r.get("term"), (r.get("inputs") or {}).get("sentence")))
    done = []
    for f in AC.dangling(case, page_html):
        if (f["term"], f["later_sentence"]) in done_before:
            continue
        hit = _row_for(rows, f["later_sentence"])
        quotes = quotations(hit[1], held) if hit else []
        reason = ("It uses %r, which no earlier sentence on the page now introduces: a ruling "
                  "changed the sentence that did, which now reads: %s"
                  % (f["term"], json.dumps(f["applied_sentence"], ensure_ascii=False)))
        p = payload(f["later_sentence"], "dangling reference", reason, "", quotes, held)
        got = rule("dangling", p, len(quotes), call, lp,
                   {"term": f["term"], "after_ruling": f["log"], "row": hit[0] if hit else None})
        done.append({"term": f["term"], **got})
    return done


def pending(mode: str, slug: str, P=None) -> int:
    """How many items MODE would rule now: the units of the stage cap check,
    counted as each rule_* function selects them, without a call."""
    import source_store as store
    P = P or _publish()
    case = store.case_dir(slug)
    if mode == "gate":
        import findings as F
        page = P.ROOT / P.issue_cfg(slug)["page"]
        report = json.loads(page.with_suffix(page.suffix + ".gate.json").read_text(encoding="utf-8"))
        return len(gate_items(report, F.load(slug)))
    if mode == "conclusions":
        import conclusion_judge as CJ
        return sum(1 for e in (CJ.load_review(slug).get("sentences") or {}).values()
                   if e.get("flagged") and not CJ.decided(e))
    if mode == "changecheck":
        import changecheck as C
        html = (P.ROOT / P.issue_cfg(slug)["page"]).read_text(encoding="utf-8")
        doc = C.load_reviews(slug)
        mine = [r for r in doc.get("reviews") or [] if r.get("sha") == C.page_sha(html)]
        have = {d.get("key") for d in doc.get("dispositions") or []}
        return sum(1 for f in ((mine[-1].get("findings") or []) if mine else [])
                   if C.finding_key(f) not in have and (f.get("sentence") or "").strip())
    if mode == "advocate":
        return len(advocate_items(slug))
    if mode == "dangling":
        import applied_check as AC
        html = (P.ROOT / P.issue_cfg(slug)["page"]).read_text(encoding="utf-8")
        before = set()
        lp = case / "rulings" / "rulings.jsonl"
        for line in (lp.read_text(encoding="utf-8").splitlines() if lp.exists() else []):
            r = json.loads(line) if line.strip() else {}
            if r.get("ruling_kind") == "dangling":
                before.add((r.get("term"), (r.get("inputs") or {}).get("sentence")))
        return sum(1 for f in AC.dangling(case, html) if (f["term"], f["later_sentence"]) not in before)
    raise ValueError(mode)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("gate", "conclusions", "changecheck", "advocate", "dangling"):
        s = sub.add_parser(name)
        s.add_argument("slug")
        s.add_argument("--cap", type=float, default=50.0,
                       help="this run's own ceiling; the issue cap and the day cap also apply")
    a = ap.parse_args(argv)
    require_study(a.slug)
    import stage_cap
    stage_cap.guard("rulings", a.slug, pending(a.cmd, a.slug))   # before the first paid call
    import audit_stage as A
    call = A.Caller(cap=a.cap, ledger_issue=a.slug)
    fn = {"gate": rule_gate, "conclusions": rule_conclusions,
          "changecheck": rule_changecheck, "advocate": rule_advocate,
          "dangling": rule_dangling}[a.cmd]
    done = fn(a.slug, call)
    print("  %d ruling(s) recorded; log: %s" % (len(done), log_path(a.slug)))
    print("  usd this run: %.4f" % sum((c.get("usd") or 0) for c in call.calls))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
