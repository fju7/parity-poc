#!/usr/bin/env python3
"""The audit stage: every sentence a reader sees, read against what it rests on.

Design: docs/whu-audit-stage-design.md, approved 19 October 2026 with two
additions (a sentence still failing after three read-and-correct rounds is
cut, and the cut logged; the meta description and card text are read in the
same pass as the body).

Usage:
    audit_stage.py run SLUG [--cap USD] [--ledger-issue NAME]
    audit_stage.py run SLUG --dry-run --limit 20 --out DIR [--cap USD]
    audit_stage.py check SLUG

`run` writes issues/<case>/audit/<run-id>/: manifest.json, verdicts.jsonl,
rulings.jsonl, cuts.jsonl, second_reads.jsonl. `--dry-run` reads only the
first LIMIT units, writes only under DIR, and touches nothing in the issue's
records. `check` prints the preflight row.

WHAT IS FIXED, AND WHERE
  The reading prompt and the ruling prompt are files (audit_prompts/), each
  identified by sha256 on the manifest. The model is MODEL. Spend goes to the
  ledger through spend_ledger's metered client; before each call the worst
  case is checked against --cap (this run) and the day cap. Any failure stops
  the run: a call that errors, a reply that does not parse, a quotation that is
  still not verbatim after one re-read. The manifest says "failed" and why.

THE RULING MODEL SEES ONLY the finding, its sentence and the quoted source
text (ruling_payload). Not the binding, not the issue, not the run, and never
answer keys, the review a study question came from, other systems' answers,
judge outputs or study files: none of those is an input to this module, and
ruling_payload builds its payload from an allow-list, so nothing passed in by
mistake reaches the model either. The test inspects the payload.

ROUNDS. A finding the ruling model accepts or amends replaces the sentence's
text, and the new text is read again. A sentence still failing after
MAX_ROUNDS read-and-correct rounds is cut: its text must leave the page, and
cuts.jsonl says so with every round's finding.

SECOND READER. After the rounds, every judgement sentence (its binding has
premises) and a fixed-seed SECOND_SHARE of the other holds are read again by
an independent call. A disagreement is a finding and is ruled like any other.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
_spec = importlib.util.spec_from_file_location("spend_ledger", ROOT / "backend" / "scripts" / "spend_ledger.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

READ_PROMPT = HERE / "audit_prompts" / "read.md"
RULE_PROMPT = HERE / "audit_prompts" / "rule.md"
MODEL = "claude-opus-5-5"
READ_MAX_OUT = 12000
RULE_MAX_OUT = 1500
BATCH = 20
MAX_ROUNDS = 3
SECOND_SHARE = 0.10
SECOND_SEED = 20261019
MAX_DOC_CHARS = 120_000          # a longer held text is cut to windows around the batch's terms
WINDOW = 3000
QUOTE_AROUND = 600
ROW_LABEL = "audit complete"
BORROW = 0.45
ADOPTED = "2026-10-19T20:00:00+00:00"
PUBLISHED_ACTIONS = ("publish", "republish")
OK, BAD, WARN = "ok", "BLOCKED", "warn"

KINDS = ("Overstated a finding or a source's claim", "Misattributed or misdescribed",
         "Claimed more about our own process than our records show",
         "Rested on a document we do not hold", "A wrong date, count, figure or author",
         "Understated a source's standing", "Misquoted", "Understated a finding", "A copy defect")
VERDICTS = ("holds", "finding", "not_a_correction", "updated_by_source")
SETTLED = ("holds", "not_a_correction", "updated_by_source", "holds_by_ruling")
RULE_FIELDS = ("sentence", "kind", "reason", "proposed_text", "quoted_source_text")


class AuditFailure(RuntimeError):
    """The run stops. Nothing downstream may treat a partial run as complete."""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fingerprint(sentence: str) -> str:
    """bindings.py's key for a sentence: whitespace-normalised, sha256[:16]."""
    return hashlib.sha256(" ".join(sentence.split()).encode("utf-8")).hexdigest()[:16]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("−", "-"), (" ", " ")):
        s = s.replace(a, b)
    return " ".join(s.split()).lower()


# --------------------------------------------------------------------------
# What is read: every sentence a reader sees
# --------------------------------------------------------------------------

def _B():
    import bindings as B
    return B


def _ledger():
    import source_ledger as L
    return L


def meta_description(page_html: str) -> list[str]:
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', page_html, re.I)
    if not m:
        return []
    import html as H
    return [" ".join(s.split()) for s in _ledger().sentences(H.unescape(m.group(1))) if s.strip()]


def card_sentences(slug: str) -> list[str]:
    """The homepage card's prose for this issue: its subject line and summary.
    The provenance line under it is derived from the record, not written."""
    idx = ROOT / "site" / "whatholdsup" / "index.html"
    if not idx.exists():
        return []
    m = re.search(r'<a class="issue" href="/%s">(.*?)</a>' % re.escape(slug), idx.read_text(encoding="utf-8"), re.S)
    if not m:
        return []
    block = re.sub(r'<span class="(prov|more|no)">.*?</span>', " ", m.group(1), flags=re.S)
    block = re.sub(r"<h3>.*?</h3>", " ", block, flags=re.S)
    L = _ledger()
    return [" ".join(s.split()) for s in L.sentences(L.plain(block)) if s.strip()]


def units(slug: str) -> list[dict]:
    """Every sentence a reader sees, in reading order: the card, the meta
    description, the page (standfirst, body, source notes), the change history.
    Each carries its binding row, if it has one."""
    B = _B()
    rows = B.load(slug)["bindings"]
    page_html = B._page_html(slug)
    parts = [("card", card_sentences(slug)), ("meta_description", meta_description(page_html)),
             ("page", B.page_sentences(slug)), ("footer", B.footer_sentences(slug))]
    out, seen = [], set()
    for part, sents in parts:
        for s in sents:
            fp = fingerprint(s)
            if (part, fp) in seen:
                continue
            seen.add((part, fp))
            out.append({"id": "u%d" % (len(out) + 1), "part": part, "sentence": s,
                        "sha": fp, "row": rows.get(fp)})
    # The card and the meta description restate the page; a sentence there with
    # no row of its own is read against the binding of the page sentence it
    # restates (word overlap >= BORROW), and says which one it borrowed.
    page_rows = [(set(_words(u["sentence"])), u) for u in out if u["part"] == "page" and u["row"]]
    for u in out:
        if u["row"] or u["part"] not in ("card", "meta_description"):
            continue
        w = set(_words(u["sentence"]))
        best = max(page_rows, key=lambda pr: len(w & pr[0]) / max(len(w | pr[0]), 1), default=None)
        if best and len(w & best[0]) / max(len(w | best[0]), 1) >= BORROW:
            u["row"] = dict(best[1]["row"], borrowed_from=best[1]["sha"])
    return out


def _words(s: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'%.-]*", s) if len(w) > 2]


def sources_of(row: dict | None) -> list[str]:
    if not row:
        return []
    ids = [row.get("source_id")] + [x.get("source_id") for x in row.get("also_rests_on") or []]
    ids += [x.get("source_id") for x in row.get("premises") or []]
    out = []
    for i in ids:
        if i and i not in out:
            out.append(i)
    return out


def batches(us: list[dict], size: int = BATCH) -> list[list[dict]]:
    """Grouped by the source the sentence rests on first (one reader holding
    one source reads everything that cites it), then process sentences, then
    the rest; at most SIZE to a batch."""
    groups: dict[str, list[dict]] = {}
    for u in us:
        row = u["row"] or {}
        key = (sources_of(row) or [None])[0] or ("records" if row.get("rests_on_record") else "unbound")
        groups.setdefault(key, []).append(u)
    out = []
    for key in sorted(groups, key=lambda k: (k in ("records", "unbound"), k)):
        g = groups[key]
        out += [g[i:i + size] for i in range(0, len(g), size)]
    return out


# --------------------------------------------------------------------------
# The reading prompt
# --------------------------------------------------------------------------

def terms(texts: list[str]) -> set[str]:
    out = set()
    for t in texts:
        out |= {n for n in re.findall(r"\d[\d.,]*%?", t) if len(n) >= 2}
        out |= {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'-]{6,}", t)}
    return out


def trim(text: str, wanted: list[str]) -> tuple[str, bool]:
    """A held text over MAX_DOC_CHARS is cut to windows around every place a
    span or key term occurs; the reader is told it is seeing windows."""
    if len(text) <= MAX_DOC_CHARS:
        return text, False
    low = text.lower()
    hits = []
    for w in wanted:
        for m in re.finditer(re.escape(w.lower()), low):
            hits.append(m.start())
    hits.sort()
    spans, cur = [], None
    for h in hits:
        a, b = max(0, h - WINDOW), min(len(text), h + WINDOW)
        if cur and a <= cur[1]:
            cur[1] = b
        else:
            if cur:
                spans.append(cur)
            cur = [a, b]
    if cur:
        spans.append(cur)
    out, total = [], 0
    for a, b in spans:
        if total + (b - a) > MAX_DOC_CHARS:
            break
        out.append(text[a:b]); total += b - a
    return "\n[...]\n".join(out), True


def batch_inputs(slug: str, batch: list[dict], held: dict[str, str]) -> tuple[dict[str, str], dict[str, dict]]:
    """(documents {id: text}, records {id: {path, text}}) for one batch."""
    docs: dict[str, str] = {}
    for u in batch:
        row = u["row"] or {}
        for sid in sources_of(row):
            if sid in docs:
                continue
            text = held.get("%s:%s" % (slug, sid)) or held.get(sid)
            if text is None:
                continue
            wanted = [x.get("span") or "" for x in [row] + (row.get("also_rests_on") or []) + (row.get("premises") or [])]
            wanted = [w[:60] for w in wanted if w] + sorted(terms([b["sentence"] for b in batch]))
            docs[sid] = trim(text, wanted)[0]
    records: dict[str, dict] = {}
    B = _B()
    for u in batch:
        for e in (u["row"] or {}).get("rests_on_record") or []:
            path = e.get("path") or ""
            if not path or any(r["path"] == path and r["quote"] == e.get("quote") for r in records.values()):
                continue
            got = B._committed(path)
            text = got[1] if got else ""
            q = e.get("quote") or ""
            i = norm(text).find(norm(q)[:80]) if q else -1
            # The committed record around its quotation: enough to read it in place.
            window = text if len(text) <= 2 * QUOTE_AROUND * 4 else ""
            if not window:
                raw_i = text.find(q[:40]) if q else -1
                a = max(0, (raw_i if raw_i >= 0 else 0) - QUOTE_AROUND * 2)
                window = text[a:a + QUOTE_AROUND * 6]
            records["R%d" % (len(records) + 1)] = {"path": path, "quote": q, "text": window,
                                                    "found": i >= 0}
    return docs, records


def binding_line(row: dict | None) -> str:
    if not row:
        return "none: this sentence has no binding row"
    bits = []
    if row.get("source_id"):
        bits.append("rests on %s%s" % (row["source_id"], (": \"%s\"" % row["span"][:300]) if row.get("span") else ""))
    for x in row.get("also_rests_on") or []:
        bits.append("also %s: \"%s\"" % (x.get("source_id"), (x.get("span") or "")[:300]))
    for x in row.get("premises") or []:
        bits.append("premise %s: \"%s\"" % (x.get("source_id"), (x.get("span") or "")[:300]))
    for x in row.get("rests_on_record") or []:
        bits.append("record %s: \"%s\"" % (x.get("path"), (x.get("quote") or "")[:200]))
    if row.get("framing"):
        bits.append("declared framing")
    return "; ".join(bits) or "a row with nothing bound"


def build_read_prompt(batch: list[dict], docs: dict[str, str], records: dict[str, dict],
                      context: dict[str, tuple[str, str]]) -> str:
    dtext = "\n\n".join("<<<DOCUMENT %s\n%s\nDOCUMENT %s>>>" % (k, v, k) for k, v in docs.items()) \
        or "(no held document for this batch)"
    rtext = "\n\n".join("<<<RECORD %s (%s)\n%s\nRECORD %s>>>" % (k, r["path"], r["text"], k) for k, r in records.items()) \
        or "(no records for this batch)"
    stext = "\n\n".join(
        "[%s] (%s)\nSENTENCE: %s\nBEFORE: %s\nAFTER: %s\nBINDING: %s"
        % (u["id"], u["part"].replace("_", " "), u["sentence"], context.get(u["id"], ("", ""))[0] or "-",
           context.get(u["id"], ("", ""))[1] or "-", binding_line(u["row"]))
        for u in batch)
    t = READ_PROMPT.read_text(encoding="utf-8")
    return t.replace("{documents}", "DOCUMENTS\n\n" + dtext).replace("{records}", "RECORDS\n\n" + rtext) \
            .replace("{sentences}", stext)


def parse_json(text: str) -> dict | list:
    s = text.strip()
    s = re.sub(r"^```(json)?\s*|\s*```$", "", s)
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"[\[{].*[\]}]", s, re.S)
        if not m:
            raise AuditFailure("reply is not JSON: %r" % text[:200])
        try:
            return json.loads(m.group(0))
        except Exception as e:
            raise AuditFailure("reply is not JSON: %s" % e)


def check_verdicts(batch: list[dict], got: dict) -> list[dict]:
    vs = got.get("verdicts") if isinstance(got, dict) else None
    if not isinstance(vs, list):
        raise AuditFailure("reply has no verdicts list")
    by = {v.get("id"): v for v in vs if isinstance(v, dict)}
    missing = [u["id"] for u in batch if u["id"] not in by]
    if missing:
        raise AuditFailure("no verdict for %s" % ", ".join(missing))
    out = []
    for u in batch:
        v = by[u["id"]]
        if v.get("verdict") not in VERDICTS:
            raise AuditFailure("%s: verdict %r not allowed" % (u["id"], v.get("verdict")))
        if v["verdict"] == "finding" and v.get("kind") not in KINDS:
            raise AuditFailure("%s: finding kind %r not allowed" % (u["id"], v.get("kind")))
        out.append(v)
    return out


def bad_quotes(verdict: dict, docs: dict[str, str], records: dict[str, dict], row: dict | None) -> list[dict]:
    """Every evidence quotation that is NOT verbatim in the document or record it
    names. A quote naming a document not shown is bad; a quote naming BINDING
    must occur in the sentence's own binding."""
    bad = []
    for e in verdict.get("evidence") or []:
        src, q = (e.get("source") or "").strip(), e.get("quote") or ""
        if not q.strip():
            bad.append(e); continue
        if src == "BINDING":
            hay = json.dumps(row or {}, ensure_ascii=False)
        elif src in docs:
            hay = docs[src]
        elif src in records:
            hay = records[src]["text"]
        else:
            bad.append(e); continue
        if norm(q) not in norm(hay):
            bad.append(e)
    unheld = verdict.get("kind") == "Rested on a document we do not hold"
    if verdict.get("verdict") in ("holds", "finding") and not (verdict.get("evidence") or []) and not unheld:
        bad.append({"source": "", "quote": "", "why": "no evidence given"})
    return bad


# --------------------------------------------------------------------------
# The ruling prompt: an allow-list, nothing else
# --------------------------------------------------------------------------

def ruling_payload(finding: dict, sentence: str, docs: dict[str, str], records: dict[str, dict]) -> dict:
    """Exactly RULE_FIELDS. The quoted source text is each evidence quotation in
    its document, with QUOTE_AROUND characters either side, labelled by
    position only ("Quotation 1"), so not even a source id travels."""
    quoted = []
    for n, e in enumerate(finding.get("evidence") or [], 1):
        src, q = e.get("source") or "", e.get("quote") or ""
        hay = docs.get(src) if src in docs else (records.get(src) or {}).get("text", "")
        around = q
        if hay:
            i = norm(hay).find(norm(q))
            if i >= 0:
                # norm() collapses whitespace; find the raw position by the quote's first words
                raw_i = hay.find(q[:30]) if hay.find(q[:30]) >= 0 else 0
                around = hay[max(0, raw_i - QUOTE_AROUND): raw_i + len(q) + QUOTE_AROUND]
        quoted.append("Quotation %d: \"%s\"\nIn its document: ...%s..." % (n, q, " ".join(around.split())))
    payload = {"sentence": sentence, "kind": finding.get("kind") or "",
               "reason": finding.get("reason") or "", "proposed_text": finding.get("proposed_text") or "",
               "quoted_source_text": "\n\n".join(quoted)}
    assert tuple(payload) == RULE_FIELDS
    return payload


def build_rule_prompt(payload: dict) -> str:
    t = RULE_PROMPT.read_text(encoding="utf-8")
    for k in RULE_FIELDS:
        t = t.replace("{%s}" % k, payload[k])
    return t


def check_ruling(got) -> dict:
    if not isinstance(got, dict) or got.get("ruling") not in ("accept", "amend", "reject"):
        raise AuditFailure("ruling reply not usable: %r" % (got,))
    if got["ruling"] in ("accept", "amend") and got.get("text") is None:
        raise AuditFailure("ruling %s with no text" % got["ruling"])
    return got


# --------------------------------------------------------------------------
# Calls, caps and the run
# --------------------------------------------------------------------------

class Caller:
    """One model, metered, capped. `ask` may be replaced (tests): it takes
    (prompt, max_tokens) and returns (text, usage dict)."""

    def __init__(self, *, cap: float, ledger_issue: str, ask=None):
        self.cap, self.issue, self.calls = cap, ledger_issue, []
        self._ask = ask
        self._start = self._spent()
        if ask is None:
            import anthropic
            key = None
            for line in (ROOT / "backend" / ".env").read_text().splitlines():
                m = re.match(r"^ANTHROPIC_API_KEY=(.*)$", line.strip())
                if m:
                    key = m.group(1).strip().strip("'\"")
            if not key:
                raise AuditFailure("no ANTHROPIC_API_KEY")
            self._raw = anthropic.Anthropic(api_key=key)
            self._client = S.metered(self._raw, script="audit_stage.py", issue=ledger_issue, role="audit")

    def _spent(self) -> float:
        return sum(float(e.get("usd") or 0) for e in S.entries() if e.get("issue") == self.issue)

    def __call__(self, prompt: str, max_tokens: int, role: str) -> tuple[str, dict]:
        if self._ask is not None:
            text, usage = self._ask(prompt, max_tokens)
            self.calls.append({"role": role, **usage})
            return text, usage
        n_in = self._raw.messages.count_tokens(model=MODEL, messages=[{"role": "user", "content": prompt}]).input_tokens
        p = S.PRICES[MODEL]
        worst = (n_in * p["input"] + max_tokens * p["output"]) / 1e6
        if self._spent() - self._start + worst > self.cap:
            raise AuditFailure("spend cap: this call could cost $%.3f; the run has spent $%.3f of $%.2f"
                               % (worst, self._spent() - self._start, self.cap))
        S.check_day_cap(worst)
        t0 = time.time()
        r = self._client.messages.create(model=MODEL, max_tokens=max_tokens,
                                         messages=[{"role": "user", "content": prompt}])
        if r.stop_reason == "refusal":
            raise AuditFailure("the model refused (%s)" % role)
        if r.stop_reason == "max_tokens":
            raise AuditFailure("reply cut off at %d tokens (%s)" % (max_tokens, role))
        text = "".join(getattr(b, "text", "") for b in r.content)
        usd, counts = S.price(r.model, r.usage)
        usage = {"input": counts["input"], "output": counts["output"], "usd": usd or 0.0,
                 "seconds": round(time.time() - t0, 1)}
        self.calls.append({"role": role, **usage})
        return text, usage


def context_map(us: list[dict]) -> dict[str, tuple[str, str]]:
    out = {}
    for i, u in enumerate(us):
        before = us[i - 1]["sentence"] if i and us[i - 1]["part"] == u["part"] else ""
        after = us[i + 1]["sentence"] if i + 1 < len(us) and us[i + 1]["part"] == u["part"] else ""
        out[u["id"]] = (before, after)
    return out


def read_batch(call: Caller, slug: str, batch: list[dict], held: dict, ctx: dict, role: str) -> tuple[list[dict], dict, dict]:
    docs, records = batch_inputs(slug, batch, held)
    prompt = build_read_prompt(batch, docs, records, ctx)
    text, usage = call(prompt, READ_MAX_OUT, role)
    vs = check_verdicts(batch, parse_json(text))
    # Quotations not verbatim go back to the reader once, for those sentences only.
    retry = [u for u, v in zip(batch, vs) if bad_quotes(v, docs, records, u["row"])]
    if retry:
        p2 = build_read_prompt(retry, docs, records, ctx) + (
            "\n\nYOUR PREVIOUS REPLY QUOTED TEXT THAT IS NOT IN THE DOCUMENTS for these sentences: %s. "
            "Quote only text that appears character for character in the document you name."
            % ", ".join(u["id"] for u in retry))
        t2, _u2 = call(p2, READ_MAX_OUT, role + "-requote")
        v2 = {v["id"]: v for v in check_verdicts(retry, parse_json(t2))}
        for i, (u, v) in enumerate(zip(batch, vs)):
            if u["id"] in v2:
                vs[i] = v2[u["id"]]
                if bad_quotes(vs[i], docs, records, u["row"]):
                    raise AuditFailure("%s: quotation still not verbatim after a re-read" % u["id"])
    return vs, docs, records


def run(slug: str, *, out_dir: Path, limit: int | None = None, cap: float = 40.0,
        ledger_issue: str | None = None, ask=None, held: dict | None = None,
        unit_list: list[dict] | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    call = Caller(cap=cap, ledger_issue=ledger_issue or slug, ask=ask)
    us = unit_list if unit_list is not None else units(slug)
    if limit:
        us = us[:limit]
    if held is None:
        import reachability
        held = reachability.held_text(slug, cache=False)
    B = _B() if unit_list is None else None
    manifest = {
        "slug": slug, "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL, "read_prompt_sha256": sha(READ_PROMPT.read_text(encoding="utf-8")),
        "rule_prompt_sha256": sha(RULE_PROMPT.read_text(encoding="utf-8")),
        "cap_usd": cap, "ledger_issue": ledger_issue or slug, "units": len(us), "limit": limit,
        "max_rounds": MAX_ROUNDS, "second_share": SECOND_SHARE, "second_seed": SECOND_SEED,
        "inputs": {"held_texts": {k: sha(v) for k, v in sorted(held.items())}},
        "status": "running",
    }
    if B is not None:
        page = B._page_html(slug)
        manifest["inputs"]["page_sha256"] = sha(page)
        manifest["inputs"]["bindings_sha256"] = sha(B.path(slug).read_text(encoding="utf-8"))
    files = {k: open(out_dir / ("%s.jsonl" % k), "w", encoding="utf-8")
             for k in ("verdicts", "rulings", "cuts", "second_reads")}

    def log(kind: str, rec: dict) -> None:
        files[kind].write(json.dumps(rec, ensure_ascii=False) + "\n"); files[kind].flush()

    state: dict[str, str] = {}          # sentence sha -> settled status or "must_leave_page"
    try:
        ctx = context_map(us)
        current = {u["id"]: dict(u, round=1, history=[]) for u in us}
        pending = list(current.values())
        while pending:
            nxt = []
            for batch in batches(pending):
                vs, docs, records = read_batch(call, slug, batch, held, ctx, "read")
                for u, v in zip(batch, vs):
                    log("verdicts", {"unit": u["id"], "part": u["part"], "sha": u["sha"], "round": u["round"],
                                     "sentence": u["sentence"], **{k: v.get(k) for k in
                                     ("verdict", "kind", "evidence", "proposed_text", "reason")}})
                    if v["verdict"] != "finding":
                        state[u["sha"]] = v["verdict"]
                        continue
                    payload = ruling_payload(v, u["sentence"], docs, records)
                    rtext, _ru = call(build_rule_prompt(payload), RULE_MAX_OUT, "rule")
                    r = check_ruling(parse_json(rtext))
                    log("rulings", {"unit": u["id"], "sha": u["sha"], "round": u["round"],
                                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "by": "ruling model %s" % MODEL, "payload_sha256": sha(json.dumps(payload)),
                                    **r})
                    if r["ruling"] == "reject":
                        state[u["sha"]] = "holds_by_ruling"
                        continue
                    state[u["sha"]] = "must_leave_page"
                    hist = u["history"] + [{"round": u["round"], "kind": v.get("kind"), "reason": v.get("reason"),
                                            "ruling": r["ruling"], "text": r["text"]}]
                    new = (r["text"] or "").strip()
                    if not new or u["round"] >= MAX_ROUNDS:
                        log("cuts", {"unit": u["id"], "part": u["part"], "original_sha": us_sha(us, u["id"]),
                                     "last_text": u["sentence"], "rounds": hist,
                                     "why": "ruling cut the sentence" if not new else
                                     "still failing after %d read-and-correct rounds" % MAX_ROUNDS})
                        continue
                    nxt.append(dict(u, sentence=new, sha=fingerprint(new), round=u["round"] + 1, history=hist))
            pending = nxt
        # Second reader: every judgement sentence and a fixed-seed share of the rest that hold.
        settled = [u for u in us if state.get(u["sha"]) in SETTLED]
        rng = random.Random(SECOND_SEED)
        judgement = [u for u in settled if (u["row"] or {}).get("premises")]
        others = [u for u in settled if u not in judgement]
        k = max(1, round(SECOND_SHARE * len(others))) if others else 0
        sample = judgement + (rng.sample(others, k) if k else [])
        for batch in batches(sample):
            vs, docs, records = read_batch(call, slug, batch, held, ctx, "second-read")
            for u, v in zip(batch, vs):
                agree = (v["verdict"] != "finding")
                log("second_reads", {"unit": u["id"], "sha": u["sha"], "verdict": v["verdict"],
                                     "kind": v.get("kind"), "reason": v.get("reason"), "agrees": agree})
                if agree:
                    continue
                payload = ruling_payload(v, u["sentence"], docs, records)
                rtext, _ru = call(build_rule_prompt(payload), RULE_MAX_OUT, "rule-second")
                r = check_ruling(parse_json(rtext))
                log("rulings", {"unit": u["id"], "sha": u["sha"], "round": "second",
                                "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                "by": "ruling model %s" % MODEL, "payload_sha256": sha(json.dumps(payload)), **r})
                if r["ruling"] != "reject":
                    # Accepted on the second read: the sentence must change. It is
                    # not re-read here; the next run reads the corrected text.
                    state[u["sha"]] = "must_leave_page"
        manifest["second_read"] = {"read": len(sample), "judgement_rows": len(judgement)}
        manifest["status"] = "complete"
    except AuditFailure as e:
        manifest["status"] = "failed"; manifest["failure"] = str(e)
    except Exception as e:                      # any failure stops the run
        manifest["status"] = "failed"; manifest["failure"] = "%s: %s" % (type(e).__name__, e)
    finally:
        for f in files.values():
            f.close()
        manifest["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest["state"] = state
        manifest["calls"] = call.calls
        manifest["usd"] = round(sum(c.get("usd") or 0 for c in call.calls), 6)
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    return manifest


def us_sha(us: list[dict], uid: str) -> str:
    return next((u["sha"] for u in us if u["id"] == uid), "")


# --------------------------------------------------------------------------
# The preflight row
# --------------------------------------------------------------------------

def audit_root(slug: str) -> Path:
    import source_store
    return source_store.case_dir(slug) / "audit"


def latest_run(slug: str) -> Path | None:
    root = audit_root(slug)
    if not root.exists():
        return None
    runs = sorted(p for p in root.iterdir() if (p / "manifest.json").exists())
    return runs[-1] if runs else None


def published_before_adoption(slug: str, record_rows: list[dict]) -> str:
    first = [r for r in record_rows if r.get("issue") == slug and r.get("action") in PUBLISHED_ACTIONS]
    return first[0]["at"] if first and first[0]["at"] < ADOPTED else ""


def preflight_rows(slug: str, record_rows: list[dict] | None = None, *, current: list[dict] | None = None,
                   run_dir: Path | None = None) -> list[tuple[str, str, str]]:
    """One row, fail closed: BLOCKED unless the latest audit run is complete and
    every sentence a reader will see, at its current wording, is settled in it.
    An issue first published before ADOPTED is SKIPPED (ok, with the word and
    the reason), as conclusion_judge does for issues that predate it."""
    first = published_before_adoption(slug, record_rows or [])
    if first:
        return [(ROW_LABEL, OK, "SKIPPED — first published %s, before the audit stage was adopted (%s)"
                 % (first[:10], ADOPTED[:10]))]
    run_dir = run_dir or latest_run(slug)
    if run_dir is None:
        return [(ROW_LABEL, BAD, "no audit run for this issue. Run: python3 backend/scripts/whatholdsup/"
                 "audit_stage.py run %s" % slug)]
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if m.get("status") != "complete":
        return [(ROW_LABEL, BAD, "the latest audit run (%s) is %s: %s"
                 % (run_dir.name, m.get("status"), m.get("failure") or "not finished"))]
    if m.get("limit"):
        return [(ROW_LABEL, BAD, "the latest audit run (%s) read only the first %d units -- a dry run, not an audit"
                 % (run_dir.name, m["limit"]))]
    state = m.get("state") or {}
    us = current if current is not None else units(slug)
    unread = [u for u in us if u["sha"] not in state]
    leave = [u for u in us if state.get(u["sha"]) == "must_leave_page"]
    if unread or leave:
        bits = []
        if unread:
            bits.append("%d sentence(s) have no audit verdict on their current wording (e.g. %r)"
                        % (len(unread), unread[0]["sentence"][:80]))
        if leave:
            bits.append("%d sentence(s) were corrected or cut by the audit and are still on the page (e.g. %r)"
                        % (len(leave), leave[0]["sentence"][:80]))
        return [(ROW_LABEL, BAD, "; ".join(bits) + ". Apply the rulings and re-run the audit.")]
    return [(ROW_LABEL, OK, "every one of %d sentences is settled in audit run %s" % (len(us), run_dir.name))]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("slug")
    r.add_argument("--cap", type=float, default=40.0)
    r.add_argument("--ledger-issue")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--limit", type=int)
    r.add_argument("--out")
    c = sub.add_parser("check"); c.add_argument("slug")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        import publish
        for row in preflight_rows(a.slug, publish.load_record()):
            print("  %-6s %-16s %s" % (row[1], row[0], row[2]))
        return 0
    if a.dry_run:
        if not (a.out and a.limit):
            raise SystemExit("--dry-run needs --out DIR and --limit N: it writes nowhere in the issue")
        out = Path(a.out)
        if str(out.resolve()).startswith(str((ROOT / "issues").resolve())):
            raise SystemExit("--dry-run --out must be outside issues/")
    else:
        out = audit_root(a.slug) / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    m = run(a.slug, out_dir=out, limit=a.limit if a.dry_run else None, cap=a.cap,
            ledger_issue=a.ledger_issue)
    print(json.dumps({k: m.get(k) for k in ("status", "failure", "units", "usd", "second_read")}, indent=1))
    return 0 if m["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
