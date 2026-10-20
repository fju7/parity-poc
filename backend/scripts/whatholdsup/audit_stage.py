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

SECOND READER. After the rounds, every sentence that had a finding (at its
final wording) and a seeded SECOND_SHARE sample of the sentences that held on
their first read are read again by an independent call. The seed and the
sampled units are on the manifest. A disagreement is a finding and is ruled
like any other. (Budget ruling, protocol rev 26, 20 October 2026; until then
every judgement sentence was read again in place of the flagged ones.)

RESUME. A run stopped by a cap or a failure writes its progress to the
manifest: which units are finished, which are queued for the current round,
and where the second reader is. `run SLUG --resume RUN_DIR` carries on in the
same directory without reading a finished sentence again, and refuses if any
input -- page, bindings, held texts, prompts, model, seed -- has changed since
the stop. A unit whose read was logged but whose ruling was not is not
finished, and is read again.

A CARD OR META-DESCRIPTION WORDING is applied only if it is, word for word, a
whole sentence of the page body (body_sentence: typography and spacing folded,
nothing else). A summary may only repeat the page; a wording the ruling model
composed is a finding left for a person, logged in cuts.jsonl with
left_for_person, and never applied. A body wording the stage applies reaches
the page as a changed sentence, which preflight blocks until changecheck has
read it and the narrow gate has run.
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
SUMMARY_PROMPT = HERE / "audit_prompts" / "summary.md"
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
SUMMARY_PARTS = ("card", "meta_description")
SUMMARY_KIND = "Summary says what the body does not"
HUMAN_READ_REQUIRED = "HUMAN_READ_REQUIRED"
# A sentence whose reader quotation is still not word for word after its
# re-read (2026-10-20). Marked and the run continues; at the end of the run it
# becomes HUMAN_READ_REQUIRED. It used to stop the whole run.
FAILED_READ = "FAILED_READ"
ADOPTED = "2026-10-19T20:00:00+00:00"
PUBLISHED_ACTIONS = ("publish", "republish")
OK, BAD, WARN = "ok", "BLOCKED", "warn"

KINDS = ("Overstated a finding or a source's claim", "Misattributed or misdescribed",
         "Claimed more about our own process than our records show",
         "Rested on a document we do not hold", "A wrong date, count, figure or author",
         "Understated a source's standing", "Misquoted", "Understated a finding", "A copy defect")
VERDICTS = ("holds", "finding", "not_a_correction", "updated_by_source")
SUMMARY_VERDICTS = ("holds", "finding", "not_a_correction")
SETTLED = ("holds", "not_a_correction", "updated_by_source", "holds_by_ruling", "holds_by_human_read")
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
    return out


def _words(s: str) -> str:
    """Typography and spacing folded; case and every word kept."""
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("−", "-"), (" ", " ")):
        s = s.replace(a, b)
    return " ".join(s.split())


def body_sentence(text: str, us: list[dict]) -> bool:
    """Is `text` word for word a whole sentence of the page body?"""
    want = _words(text or "")
    return bool(want) and any(_words(u["sentence"]) == want for u in us if u["part"] == "page")


def page_body(us: list[dict]) -> str:
    """The page body as the audit reads it: its sentences, in order. A summary
    (card, meta description) is read against this, not against the sources
    (ruling of 19 October 2026: the body has already been read against them)."""
    return " ".join(u["sentence"] for u in us if u["part"] == "page")


def licensed_ids(slug: str) -> set[str]:
    """Sources whose licence forbids machine reading, from the issue's
    sources.json (source_store.LICENCE_KEY, on the source or on its access
    record). Read from the record every time, never hard-coded: NCCN on cdk46
    is S001 today, and an id is not a licence."""
    import source_store
    key = source_store.LICENCE_KEY
    p = source_store.case_dir(slug) / "sources.json"
    if not p.exists():
        return set()
    srcs = json.loads(p.read_text(encoding="utf-8")).get("sources") or []
    return {x["id"] for x in srcs if x.get(key) or (x.get("access") or {}).get(key)}


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
        if u["part"] in SUMMARY_PARTS:
            groups.setdefault(" summary", []).append(u)      # sorts first; read against the page
            continue
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


DOC_SEP = "\n[...]\n"


def trim(text: str, wanted: list[str], must: list[str] | tuple = ()) -> tuple[str, bool]:
    """A held text over MAX_DOC_CHARS is cut to windows around every place a
    bound span (`must`) or a key term (`wanted`) occurs; the reader is told it
    is seeing windows.

    NEVER EMPTY FOR A NON-EMPTY TEXT (2026-10-20). The first version added
    merged windows in document order and stopped at the first that did not
    fit, so when every hit merged into one window longer than the limit -- a
    159,009-character paper on the WHU-P02 practice run -- it returned "" and
    the reader was shown an empty document. Now: an oversized window is cut to
    the limit, centred on its bound span (else on the middle of its hits);
    windows holding a bound span are kept first, then those covering the most
    distinct terms; the kept windows are joined in document order; with no hit
    at all the text's opening MAX_DOC_CHARS is kept."""
    if len(text) <= MAX_DOC_CHARS:
        return text, False
    low = text.lower()
    must_l = {m.lower() for m in must if m}
    hits = []                                     # (position, is_bound_span, length, term)
    for w in {x.lower() for x in wanted if x} | must_l:
        for m in re.finditer(re.escape(w), low):
            hits.append((m.start(), w in must_l, len(w), w))
    if not hits:
        return text[:MAX_DOC_CHARS], True
    hits.sort()
    spans = []                                    # [start, end, hits]
    for h in hits:
        a, b = max(0, h[0] - WINDOW), min(len(text), h[0] + h[2] + WINDOW)
        if spans and a <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], b)
            spans[-1][2].append(h)
        else:
            spans.append([a, b, [h]])
    for s in spans:
        if s[1] - s[0] > MAX_DOC_CHARS:
            pts = sorted(h[0] for h in s[2] if h[1]) or sorted(h[0] for h in s[2])
            c = pts[len(pts) // 2]
            a = max(s[0], min(c - MAX_DOC_CHARS // 2, s[1] - MAX_DOC_CHARS))
            s[0], s[1] = a, a + MAX_DOC_CHARS
            s[2] = [h for h in s[2] if a <= h[0] and h[0] + h[2] <= s[1]]
    ranked = sorted(spans, key=lambda s: (-sum(1 for h in s[2] if h[1]),
                                          -len({h[3] for h in s[2]}), s[0]))
    chosen, total = [], 0
    for s in ranked:
        need = (s[1] - s[0]) + (len(DOC_SEP) if chosen else 0)
        if total + need <= MAX_DOC_CHARS:
            chosen.append(s)
            total += need
    chosen.sort(key=lambda s: s[0])
    return DOC_SEP.join(text[a:b] for a, b, _h in chosen), True


def held_for_audit(slug: str) -> dict[str, str]:
    """{source id: text} for every document held for this issue, extracted the
    way the binding checks extract it (spancheck._text: source_store.text_of,
    reading order, entities unescaped), so the reader is shown the text the
    bound spans were checked against.

    WHY NOT reachability.held_text (2026-10-20, WHU-P02 practice run). That
    runs `pdftotext -layout`, which keeps the page's physical line order: S008's
    margin lines ("Boston, MA", "Received 13 October 2022 and accepted ...") came
    out spliced into the middle of abstract sentences, and line-end hyphens
    stayed split ("haz- ard"). The reader quoted the sentence as the paper reads
    it, the quotation was not a run of the -layout text, and the quotation was
    rejected; none of the three spans u23 and u41 are bound to occurred in the
    -layout text at all. Matching is unchanged; only what the reader is shown."""
    import spancheck as SC
    import source_store as store
    out = {}
    for sid in sorted((store.held(slug) or {})):
        try:
            t = SC._text(slug, sid)
        except Exception:
            t = None
        if t is not None:
            out[sid] = t
    return out


class DocumentNotDelivered(AuditFailure):
    """A held document reached the reader empty, or without a span its batch's
    sentences are bound to. Never sent on; the run stops (fail closed)."""

    def __init__(self, msg: str):
        super().__init__("DOCUMENT_NOT_DELIVERED: " + msg)


def delivery_report(slug: str, batch: list[dict], held: dict[str, str], docs: dict[str, str],
                    licensed: frozenset = frozenset()) -> list[dict]:
    """Per document the batch rests on: held characters, delivered characters,
    and whether every bound span of the batch's sentences is in what was
    delivered (spancheck's normalisation)."""
    out = []
    for sid, delivered in docs.items():
        text = held.get("%s:%s" % (slug, sid)) or held.get(sid) or ""
        spans = []
        for u in batch:
            row = u["row"] or {}
            for x in [row] + (row.get("also_rests_on") or []) + (row.get("premises") or []):
                if x.get("source_id") == sid and x.get("span"):
                    spans.append(x["span"])
        # Every bound span must be in what was delivered. A span not even in the
        # held text means the reader is shown a different text from the one the
        # binding was checked against: that fails closed too (2026-10-20).
        missing = [s for s in spans if norm(s) not in norm(delivered)]
        out.append({"source": sid, "units": [u["id"] for u in batch], "held_chars": len(text),
                    "delivered_chars": len(delivered), "bound_spans": len(spans),
                    "spans_inside": not missing, "missing_spans": [m[:120] for m in missing]})
    return out


def check_delivery(report: list[dict]) -> None:
    for r in report:
        if not r["delivered_chars"]:                 # empty, whether or not the held text was
            raise DocumentNotDelivered("%s held %d characters and %d were delivered (units %s)"
                                       % (r["source"], r["held_chars"], r["delivered_chars"],
                                          ", ".join(r["units"])))
        if not r["spans_inside"]:
            raise DocumentNotDelivered("%s: %d bound span(s) not in the %d characters delivered of %d "
                                       "held (units %s): %r" % (r["source"], len(r["missing_spans"]),
                                       r["delivered_chars"], r["held_chars"], ", ".join(r["units"]),
                                       r["missing_spans"][0]))


# A finding that says the reader was given nothing to read is a fault in the
# delivery, not a finding about the sentence. It never reaches the ruling model
# (which would cut a sentence for the stage's own defect): the run stops.
_SAYS_MISSING = re.compile(
    r"\b(?:document|source|text|paper|article|abstract|passage)s?\b[^.]{0,80}?\b(?:is|was|were|are|appears?|"
    r"seems?)\s+(?:empty|blank|missing|unavailable|not (?:provided|shown|available|included|present|given))"
    r"|\b(?:empty|blank)\s+(?:document|source|text)\b|\bno (?:document|source) text\b"
    r"|\bcould not (?:see|read|access|open) (?:the|any|this) (?:document|source|text|paper)\b", re.I)


def says_document_missing(v: dict) -> bool:
    return bool(_SAYS_MISSING.search(" ".join(str(v.get(k) or "") for k in ("kind", "reason"))))


def batch_inputs(slug: str, batch: list[dict], held: dict[str, str],
                 licensed: frozenset = frozenset()) -> tuple[dict[str, str], dict[str, dict]]:
    """(documents {id: text}, records {id: {path, text}}) for one batch. A
    licensed source is never a document, whatever the held texts contain."""
    docs: dict[str, str] = {}
    for u in batch:
        row = u["row"] or {}
        for sid in sources_of(row):
            if sid in docs or sid in licensed:
                continue
            text = held.get("%s:%s" % (slug, sid)) or held.get(sid)
            if text is None:
                continue
            must = [x.get("span") or "" for b in batch for x in
                    [b["row"] or {}] + ((b["row"] or {}).get("also_rests_on") or [])
                    + ((b["row"] or {}).get("premises") or [])
                    if x.get("source_id") == sid and x.get("span")]
            wanted = [w[:60] for w in must] + sorted(terms([b["sentence"] for b in batch]))
            docs[sid] = trim(text, wanted, [w[:60] for w in must])[0]
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


def binding_line(row: dict | None, licensed: frozenset = frozenset()) -> str:
    """The binding as the reader sees it. A span from a licensed source is the
    licensed text itself, so it is withheld: the reader is told the source
    exists and that it is not shown."""
    if not row:
        return "none: this sentence has no binding row"
    bits = []

    def one(label, sid, span):
        if sid in licensed:
            return "%s %s (its licence forbids machine reading: not shown, read against the other sources only)" % (label, sid)
        return "%s %s: \"%s\"" % (label, sid, (span or "")[:300]) if span else "%s %s" % (label, sid)
    if row.get("source_id"):
        bits.append(one("rests on", row["source_id"], row.get("span")))
    for x in row.get("also_rests_on") or []:
        bits.append(one("also", x.get("source_id"), x.get("span")))
    for x in row.get("premises") or []:
        bits.append(one("premise", x.get("source_id"), x.get("span")))
    for x in row.get("rests_on_record") or []:
        bits.append("record %s: \"%s\"" % (x.get("path"), (x.get("quote") or "")[:200]))
    if row.get("framing"):
        bits.append("declared framing")
    return "; ".join(bits) or "a row with nothing bound"


def build_summary_prompt(batch: list[dict], body: str) -> str:
    stext = "\n\n".join("[%s] (%s)\nSENTENCE: %s" % (u["id"], u["part"].replace("_", " "), u["sentence"])
                         for u in batch)
    t = SUMMARY_PROMPT.read_text(encoding="utf-8")
    return t.replace("{documents}", "<<<DOCUMENT PAGE\n%s\nDOCUMENT PAGE>>>" % body).replace("{sentences}", stext)


def build_read_prompt(batch: list[dict], docs: dict[str, str], records: dict[str, dict],
                      context: dict[str, tuple[str, str]], licensed: frozenset = frozenset()) -> str:
    dtext = "\n\n".join("<<<DOCUMENT %s\n%s\nDOCUMENT %s>>>" % (k, v, k) for k, v in docs.items()) \
        or "(no held document for this batch)"
    rtext = "\n\n".join("<<<RECORD %s (%s)\n%s\nRECORD %s>>>" % (k, r["path"], r["text"], k) for k, r in records.items()) \
        or "(no records for this batch)"
    stext = "\n\n".join(
        "[%s] (%s)\nSENTENCE: %s\nBEFORE: %s\nAFTER: %s\nBINDING: %s"
        % (u["id"], u["part"].replace("_", " "), u["sentence"], context.get(u["id"], ("", ""))[0] or "-",
           context.get(u["id"], ("", ""))[1] or "-", binding_line(u["row"], licensed))
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


def check_verdicts(batch: list[dict], got: dict, summary: bool = False) -> list[dict]:
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
        if v.get("verdict") not in (SUMMARY_VERDICTS if summary else VERDICTS):
            raise AuditFailure("%s: verdict %r not allowed" % (u["id"], v.get("verdict")))
        if v["verdict"] == "finding" and v.get("kind") not in ((SUMMARY_KIND,) if summary else KINDS):
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

    def __init__(self, *, cap: float, ledger_issue: str, ask=None, day_cap=None):
        self.cap, self.issue, self.calls = cap, ledger_issue, []
        self._ask = ask
        # The day cap is spend_ledger's on every real call. A test with a fake
        # `ask` may pass its own, to stop a run as the day cap would.
        self._day_cap = day_cap
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
            if self._day_cap is not None:
                self._day_cap(0.0)
            text, usage = self._ask(prompt, max_tokens)
            self.calls.append({"role": role, **usage})
            return text, usage
        n_in = self._raw.messages.count_tokens(model=MODEL, messages=[{"role": "user", "content": prompt}]).input_tokens
        p = S.PRICES[MODEL]
        worst = (n_in * p["input"] + max_tokens * p["output"]) / 1e6
        if self._spent() - self._start + worst > self.cap:
            raise AuditFailure("spend cap: this call could cost $%.3f; the run has spent $%.3f of $%.2f"
                               % (worst, self._spent() - self._start, self.cap))
        # The issue's cap as well as the day cap (protocol rev 27: a study issue is
        # capped at caps.json's study_per_issue). check_cap checks both.
        S.check_cap(self.issue, worst)
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


def read_batch(call: Caller, slug: str, batch: list[dict], held: dict, ctx: dict, role: str,
               licensed: frozenset = frozenset(), body: str = "",
               deliveries: list | None = None, on_reject=None) -> tuple[list[dict], dict, dict]:
    summary = all(u["part"] in SUMMARY_PARTS for u in batch)
    if summary:
        docs, records = {"PAGE": body}, {}
        build = lambda bs: build_summary_prompt(bs, body)
    else:
        docs, records = batch_inputs(slug, batch, held, licensed)
        build = lambda bs: build_read_prompt(bs, docs, records, ctx, licensed)
        # FAIL CLOSED, BEFORE ANY CALL: every document delivered non-empty and
        # holding every span its sentences are bound to. Recorded either way.
        rep = delivery_report(slug, batch, held, docs, licensed)
        if deliveries is not None:
            deliveries.extend(dict(r, role=role) for r in rep)
        check_delivery(rep)
    text, usage = call(build(batch), READ_MAX_OUT, role + ("-summary" if summary else ""))
    vs = check_verdicts(batch, parse_json(text), summary)
    # Every rejected quotation, raw, to the run's private log (on_reject): the
    # sentence, the document it named and the reader's own words, so a failure
    # can be read against the held text afterwards.
    def rejected(u: dict, bad: list[dict], attempt: str) -> None:
        if on_reject is None:
            return
        for e in bad:
            on_reject({"unit": u["id"], "sha": u["sha"], "role": role, "attempt": attempt,
                       "source": e.get("source"), "quote": e.get("quote"),
                       **({"why": e["why"]} if e.get("why") else {})})

    # Quotations not verbatim go back to the reader once, for those sentences only.
    retry = []
    for u, v in zip(batch, vs):
        bad = bad_quotes(v, docs, records, u["row"])
        if bad:
            rejected(u, bad, "first read")
            retry.append(u)
    if retry:
        p2 = build(retry) + (
            "\n\nYOUR PREVIOUS REPLY QUOTED TEXT THAT IS NOT IN THE DOCUMENTS for these sentences: %s. "
            "Quote only text that appears character for character in the document you name."
            % ", ".join(u["id"] for u in retry))
        t2, _u2 = call(p2, READ_MAX_OUT, role + "-requote")
        v2 = {v["id"]: v for v in check_verdicts(retry, parse_json(t2), summary)}
        for i, (u, v) in enumerate(zip(batch, vs)):
            if u["id"] in v2:
                vs[i] = v2[u["id"]]
                bad = bad_quotes(vs[i], docs, records, u["row"])
                if bad:
                    rejected(u, bad, "re-read")
                    # FAILED_READ, not a stopped run: this sentence goes to a
                    # person at the end; the others are read as usual.
                    vs[i] = {"id": u["id"], "verdict": FAILED_READ, "kind": None,
                             "evidence": vs[i].get("evidence") or [], "proposed_text": None,
                             "reason": "quotation still not word for word after a re-read"}
    return vs, docs, records


UNIT_KEYS = ("id", "sentence", "sha", "round", "history", "licensed_excluded")
RESUME_SAME = ("slug", "model", "read_prompt_sha256", "rule_prompt_sha256", "summary_prompt_sha256",
               "licensed_sources_never_sent", "units", "limit", "max_rounds", "second_share",
               "second_seed", "inputs")


def _snap(u: dict, **extra) -> dict:
    return {**{k: u[k] for k in UNIT_KEYS if k in u}, **extra}


def run(slug: str, *, out_dir: Path, limit: int | None = None, cap: float = 40.0,
        ledger_issue: str | None = None, ask=None, held: dict | None = None,
        unit_list: list[dict] | None = None, licensed: set | None = None,
        seed: int = SECOND_SEED, resume: bool = False, day_cap=None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    us = unit_list if unit_list is not None else units(slug)
    if limit:
        us = us[:limit]
    if held is None:
        held = held_for_audit(slug)
    lic = frozenset(licensed if licensed is not None else licensed_ids(slug))
    # A licensed source's text is dropped from what this run holds before
    # anything is built, so no code path below can put it in a prompt.
    held = {k: v for k, v in held.items() if k.split(":")[-1] not in lic}
    body = page_body(us)
    B = _B() if unit_list is None else None
    manifest = {
        "slug": slug, "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": MODEL, "read_prompt_sha256": sha(READ_PROMPT.read_text(encoding="utf-8")),
        "rule_prompt_sha256": sha(RULE_PROMPT.read_text(encoding="utf-8")),
        "summary_prompt_sha256": sha(SUMMARY_PROMPT.read_text(encoding="utf-8")),
        "licensed_sources_never_sent": sorted(lic),
        "cap_usd": cap, "ledger_issue": ledger_issue or slug, "units": len(us), "limit": limit,
        "max_rounds": MAX_ROUNDS, "second_share": SECOND_SHARE, "second_seed": seed,
        "inputs": {"held_texts": {k: sha(v) for k, v in sorted(held.items())},
                   "units_sha256": sha(json.dumps([[u["id"], u["sha"]] for u in us]))},
        "status": "running",
        # Per document, per batch: held and delivered characters, and whether
        # every bound span was delivered (fail closed: check_delivery).
        "deliveries": [],
    }
    if B is not None:
        page = B._page_html(slug)
        manifest["inputs"]["page_sha256"] = sha(page)
        manifest["inputs"]["bindings_sha256"] = sha(B.path(slug).read_text(encoding="utf-8"))
    prior = None
    if resume:
        mp = out_dir / "manifest.json"
        if not mp.exists():
            raise AuditFailure("cannot resume: %s has no manifest" % out_dir)
        prior = json.loads(mp.read_text(encoding="utf-8"))
        if prior.get("status") != "failed" or not isinstance(prior.get("progress"), dict):
            raise AuditFailure("cannot resume: the run in %s is %s, not a stopped run with its progress"
                               % (out_dir, prior.get("status")))
        changed = [k for k in RESUME_SAME if prior.get(k) != manifest.get(k)]
        if changed:
            raise AuditFailure("cannot resume: %s changed since the run stopped; start a new run"
                               % ", ".join(changed))
        manifest["started"] = prior["started"]
        manifest["deliveries"] = list(prior.get("deliveries") or [])
        manifest["resumed"] = (prior.get("resumed") or []) + [
            {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "after": prior.get("failure"), "usd_before": prior.get("usd") or 0.0}]
    prior_usd = float((prior or {}).get("usd") or 0.0)
    # The run's cap covers every day it runs on, not each resume afresh.
    call = Caller(cap=cap - prior_usd, ledger_issue=ledger_issue or slug, ask=ask, day_cap=day_cap)
    files = {k: open(out_dir / ("%s.jsonl" % k), "a" if prior else "w", encoding="utf-8")
             for k in ("verdicts", "rulings", "cuts", "second_reads", "quote_rejections")}

    def log(kind: str, rec: dict) -> None:
        files[kind].write(json.dumps(rec, ensure_ascii=False) + "\n"); files[kind].flush()

    by_id = {u["id"]: u for u in us}

    def live(s: dict) -> dict:
        return {**by_id[s["id"]], **s}

    # sentence sha -> settled status or "must_leave_page"
    state: dict[str, str] = dict(prior["state"]) if prior else {}
    # done: unit id -> its final wording and status. queue: this round's units
    # not yet finished. next: the next round's. second: the second reader's
    # sample and what of it is still to read.
    prog = prior["progress"] if prior else {"done": {}, "flagged": [], "queue": None, "next": [], "second": None}
    try:
        ctx = context_map(us)
        if prog["queue"] is None:
            queue = []
            for u in us:
                srcs = sources_of(u["row"])
                if srcs and all(x in lic for x in srcs):
                    # Bound only to a source no model may read: a person reads it.
                    state[u["sha"]] = HUMAN_READ_REQUIRED
                    prog["done"][u["id"]] = _snap(u, status=HUMAN_READ_REQUIRED)
                    log("verdicts", {"unit": u["id"], "part": u["part"], "sha": u["sha"], "round": 0,
                                     "sentence": u["sentence"], "verdict": HUMAN_READ_REQUIRED,
                                     "licensed_sources": srcs,
                                     "reason": "bound only to source(s) whose licence forbids machine reading"})
                    continue
                extra = {"licensed_excluded": [x for x in srcs if x in lic]} if any(x in lic for x in srcs) else {}
                queue.append(_snap(u, round=1, history=[], **extra))
            prog["queue"] = queue
        flagged = prog["flagged"]

        def finish(u: dict) -> None:
            prog["queue"] = [s for s in prog["queue"] if s["id"] != u["id"]]

        while True:
            if not prog["queue"]:
                if not prog["next"]:
                    break
                prog["queue"], prog["next"] = prog["next"], []
            for batch in batches([live(s) for s in prog["queue"]]):
                vs, docs, records = read_batch(call, slug, batch, held, ctx, "read", lic, body,
                                               deliveries=manifest["deliveries"],
                                               on_reject=lambda r: log("quote_rejections", r))
                for u, v in zip(batch, vs):
                    log("verdicts", {"unit": u["id"], "part": u["part"], "sha": u["sha"], "round": u["round"],
                                     "sentence": u["sentence"], **{k: v.get(k) for k in
                                     ("verdict", "kind", "evidence", "proposed_text", "reason")},
                                     **({"read_without_licensed_sources": u["licensed_excluded"]}
                                        if u.get("licensed_excluded") else {})})
                    if v["verdict"] != "finding":
                        state[u["sha"]] = v["verdict"]
                        prog["done"][u["id"]] = _snap(u, status=v["verdict"])
                        finish(u)
                        continue
                    if says_document_missing(v):
                        raise DocumentNotDelivered("%s: the reader's finding says a document was empty or "
                                                   "unavailable (%r); not sent to the ruling model"
                                                   % (u["id"], (v.get("reason") or "")[:160]))
                    payload = ruling_payload(v, u["sentence"], docs, records)
                    rtext, _ru = call(build_rule_prompt(payload), RULE_MAX_OUT, "rule")
                    r = check_ruling(parse_json(rtext))
                    log("rulings", {"unit": u["id"], "sha": u["sha"], "round": u["round"],
                                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "by": "ruling model %s" % MODEL, "model": MODEL,
                                    "prompt_sha256": sha(RULE_PROMPT.read_text(encoding="utf-8")),
                                    "inputs": payload, "payload_sha256": sha(json.dumps(payload)),
                                    **r})
                    if u["id"] not in flagged:
                        flagged.append(u["id"])
                    if r["ruling"] == "reject":
                        state[u["sha"]] = "holds_by_ruling"
                        prog["done"][u["id"]] = _snap(u, status="holds_by_ruling")
                        finish(u)
                        continue
                    state[u["sha"]] = "must_leave_page"
                    hist = u["history"] + [{"round": u["round"], "kind": v.get("kind"), "reason": v.get("reason"),
                                            "ruling": r["ruling"], "text": r["text"]}]
                    new = (r["text"] or "").strip()
                    if new and u["part"] in SUMMARY_PARTS and not body_sentence(new, us):
                        log("cuts", {"unit": u["id"], "part": u["part"], "original_sha": us_sha(us, u["id"]),
                                     "last_text": u["sentence"], "rounds": hist, "left_for_person": True,
                                     "not_applied": new,
                                     "why": "a card or meta-description wording must be a whole sentence of the "
                                            "page body, word for word; the proposed wording is not, so it is "
                                            "left for a person and not applied"})
                        prog["done"][u["id"]] = _snap(u, status="left_for_person")
                        finish(u)
                        continue
                    if not new or u["round"] >= MAX_ROUNDS:
                        log("cuts", {"unit": u["id"], "part": u["part"], "original_sha": us_sha(us, u["id"]),
                                     "last_text": u["sentence"], "rounds": hist,
                                     "why": "ruling cut the sentence" if not new else
                                     "still failing after %d read-and-correct rounds" % MAX_ROUNDS})
                        prog["done"][u["id"]] = _snap(u, status="cut")
                        finish(u)
                        continue
                    prog["next"].append(_snap(dict(u, sentence=new, sha=fingerprint(new),
                                                   round=u["round"] + 1, history=hist)))
                    finish(u)
        # Second reader: every sentence that had a finding, at its final
        # wording, and a seeded SECOND_SHARE of those that held on first read.
        if prog["second"] is None:
            final = [prog["done"][u["id"]] for u in us
                     if prog["done"].get(u["id"], {}).get("status") in SETTLED]
            had_finding = [s["id"] for s in final if s["id"] in flagged]
            held_first = [s["id"] for s in final if s["id"] not in flagged]
            k = max(1, round(SECOND_SHARE * len(held_first))) if held_first else 0
            sampled = random.Random(seed).sample(held_first, k) if k else []
            prog["second"] = {"seed": seed, "flagged": had_finding, "holds_pool": len(held_first),
                              "sampled": sampled, "todo": had_finding + sampled}
        sec = prog["second"]
        for batch in batches([live(prog["done"][i]) for i in sec["todo"]]):
            vs, docs, records = read_batch(call, slug, batch, held, ctx, "second-read", lic, body,
                                           deliveries=manifest["deliveries"],
                                           on_reject=lambda r: log("quote_rejections", r))
            for u, v in zip(batch, vs):
                if v["verdict"] == FAILED_READ:
                    # Not an agreement: the second reader could not quote its
                    # document. The sentence goes to a person.
                    state[u["sha"]] = FAILED_READ
                    log("second_reads", {"unit": u["id"], "sha": u["sha"], "verdict": FAILED_READ,
                                         "reason": v.get("reason"), "agrees": None})
                    sec["todo"] = [i for i in sec["todo"] if i != u["id"]]
                    continue
                agree = (v["verdict"] != "finding")
                log("second_reads", {"unit": u["id"], "sha": u["sha"], "verdict": v["verdict"],
                                     "kind": v.get("kind"), "reason": v.get("reason"), "agrees": agree,
                                     "why_read": "had a finding" if u["id"] in sec["flagged"] else
                                                 "seeded sample (seed %d)" % seed})
                if not agree:
                    if says_document_missing(v):
                        raise DocumentNotDelivered("%s: the second reader's finding says a document was "
                                                   "empty or unavailable (%r); not sent to the ruling model"
                                                   % (u["id"], (v.get("reason") or "")[:160]))
                    payload = ruling_payload(v, u["sentence"], docs, records)
                    rtext, _ru = call(build_rule_prompt(payload), RULE_MAX_OUT, "rule-second")
                    r = check_ruling(parse_json(rtext))
                    # A card or meta wording that is not a whole body sentence
                    # is recorded with apply: False and left for a person.
                    summary_bad = (u["part"] in SUMMARY_PARTS and r["ruling"] != "reject"
                                   and not body_sentence(r["text"] or "", us))
                    log("rulings", {"unit": u["id"], "sha": u["sha"], "round": "second",
                                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "by": "ruling model %s" % MODEL, "model": MODEL,
                                    "prompt_sha256": sha(RULE_PROMPT.read_text(encoding="utf-8")),
                                    "inputs": payload, "payload_sha256": sha(json.dumps(payload)), **r,
                                    **({"apply": False, "left_for_person": True} if summary_bad else {})})
                    if r["ruling"] != "reject":
                        # Accepted on the second read: the sentence must change. It is
                        # not re-read here; the next run reads the corrected text.
                        state[u["sha"]] = "must_leave_page"
                sec["todo"] = [i for i in sec["todo"] if i != u["id"]]
        manifest["second_read"] = {"read": len(sec["flagged"]) + len(sec["sampled"]), "seed": seed,
                                   "had_finding": len(sec["flagged"]), "sampled": len(sec["sampled"]),
                                   "holds_pool": sec["holds_pool"], "sampled_units": sec["sampled"]}
        # FAILED_READ sentences end as HUMAN_READ_REQUIRED: a person reads them
        # (preflight blocks until human_reads.jsonl records it).
        failed = sorted(h for h, st in state.items() if st == FAILED_READ)
        for h in failed:
            state[h] = HUMAN_READ_REQUIRED
        manifest["failed_read"] = [{"unit": u["id"], "sha": u["sha"]} for u in us if u["sha"] in failed]
        manifest["status"] = "complete"
    except AuditFailure as e:
        manifest["status"] = "failed"; manifest["failure"] = str(e)
    except Exception as e:                      # any failure stops the run
        manifest["status"] = "failed"; manifest["failure"] = "%s: %s" % (type(e).__name__, e)
        if isinstance(e, S.OverCap):
            manifest["stopped_by"] = "issue cap" if isinstance(e, getattr(S, "OverIssueCap", ())) else "day cap"
    finally:
        for f in files.values():
            f.close()
        manifest["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest["state"] = state
        manifest["progress"] = prog
        manifest["calls"] = list((prior or {}).get("calls") or []) + call.calls
        manifest["usd"] = round(sum(c.get("usd") or 0 for c in manifest["calls"]), 6)
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
    state = dict(m.get("state") or {})
    # A sentence only a person may read is settled by a person's recorded read.
    hr = run_dir / "human_reads.jsonl"
    if hr.exists():
        for line in hr.read_text(encoding="utf-8").splitlines():
            r = json.loads(line) if line.strip() else {}
            if state.get(r.get("sha")) == HUMAN_READ_REQUIRED and r.get("verdict") == "holds" and r.get("by") and r.get("at"):
                state[r["sha"]] = "holds_by_human_read"
    us = current if current is not None else units(slug)
    unread = [u for u in us if u["sha"] not in state]
    human = [u for u in us if state.get(u["sha"]) == HUMAN_READ_REQUIRED]
    leave = [u for u in us if state.get(u["sha"]) == "must_leave_page"]
    if unread or leave or human:
        bits = []
        if human:
            bits.append("%d sentence(s) rest only on a source no model may read and have no recorded human read "
                        "(human_reads.jsonl; e.g. %r)" % (len(human), human[0]["sentence"][:80]))
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
    r.add_argument("--resume", metavar="RUN_DIR",
                   help="carry on a stopped run in its own directory; refuses if any input changed")
    c = sub.add_parser("check"); c.add_argument("slug")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        import publish
        for row in preflight_rows(a.slug, publish.load_record()):
            print("  %-6s %-16s %s" % (row[1], row[0], row[2]))
        return 0
    if a.resume:
        if a.dry_run or a.out or a.limit:
            raise SystemExit("--resume takes the stopped run's settings from its manifest; "
                             "give no --dry-run, --out or --limit")
        out = Path(a.resume)
        prior = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        m = run(a.slug, out_dir=out, limit=prior.get("limit"), cap=a.cap,
                ledger_issue=a.ledger_issue or prior.get("ledger_issue"), resume=True)
        print(json.dumps({k: m.get(k) for k in ("status", "failure", "units", "usd", "second_read", "resumed")},
                         indent=1))
        return 0 if m["status"] == "complete" else 2
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
