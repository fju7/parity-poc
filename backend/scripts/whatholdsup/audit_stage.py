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
    audit_stage.py run SLUG --lean          lean WHU (lean.py; or WHU_LEAN=1)

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
import functools
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
import jsonio  # noqa: E402
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


def _frozen():
    """frozen.py: a changed frozen prompt is refused when read (protocol rev 38)."""
    return _load_frozen()


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


DOC_SEP = "\n[… text omitted …]\n"
MIN_CONTEXT = 1000               # characters either side of a bound passage, at the least
MAX_CONTEXT = 2 * WINDOW         # and at the most, before term windows get the rest


@functools.lru_cache(maxsize=8)
def _norm_index(text: str) -> tuple[str, tuple[int, ...]]:
    normed, offs = norm_map(text)
    return normed, tuple(offs)


def passages(text: str, must) -> list[tuple[int, int]]:
    """(start, end) in TEXT of each bound passage in MUST, found as the
    delivery check compares (norm()); a passage not in the text is left out
    here and is caught by check_delivery."""
    out, low = [], text.lower()
    for m in must or ():
        if not m:
            continue
        i = low.find(m.lower())
        if i >= 0:
            out.append((i, i + len(m)))
            continue
        nm = norm(m)
        normed, offs = _norm_index(text)
        k = normed.find(nm) if nm else -1
        if k >= 0:
            out.append((offs[k], offs[k + len(nm) - 1] + 1))
    return sorted(set(out))


def _merge(ws: list[tuple[int, int]]) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for a, b in sorted(ws):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def _size(ws: list[tuple[int, int]]) -> int:
    return sum(b - a for a, b in ws) + len(DOC_SEP) * max(0, len(ws) - 1)


def _around(ps: list[tuple[int, int]], c: int, n: int) -> list[tuple[int, int]]:
    return _merge([(max(0, a - c), min(n, b + c)) for a, b in ps])


def passages_fit(text: str, must) -> bool:
    """Whether every bound passage, each with MIN_CONTEXT either side, fits in
    MAX_DOC_CHARS. When it does not, the batch is split (fit_batches)."""
    if len(text) <= MAX_DOC_CHARS:
        return True
    return _size(_around(passages(text, must), MIN_CONTEXT, len(text))) <= MAX_DOC_CHARS


def trim(text: str, wanted: list[str], must: list[str] | tuple = ()) -> tuple[str, bool]:
    """A held text over MAX_DOC_CHARS is cut to windows, joined in document
    order with DOC_SEP between them, so the reader sees where text is left out.

    EVERY BOUND PASSAGE GETS ITS OWN WINDOW (2026-10-21). The version before
    merged every window (passages and terms) into runs and, when one run was
    longer than the limit, cut it around a single centre: on WHU-P04, S005's
    passages at about 21,500 and 106,200 characters sat in one such run, and
    the cut kept one of them. Now each passage in MUST is windowed on its
    own; the space left is shared as context among those windows (the same
    on every side, up to MAX_CONTEXT); only then do windows around the key
    terms (WANTED) go in, while room is left. Windows that overlap are joined,
    never cut. If the passages with MIN_CONTEXT do not fit, the caller splits
    the batch (fit_batches); a passage is never dropped for size here.

    NEVER EMPTY FOR A NON-EMPTY TEXT (2026-10-20): with no passage and no
    term found, the text's opening MAX_DOC_CHARS is kept."""
    if len(text) <= MAX_DOC_CHARS:
        return text, False
    n = len(text)
    ps = passages(text, must)
    chosen: list[tuple[int, int]] = []
    if ps:
        lo, hi = 0, MAX_CONTEXT                    # the largest context that fits
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if _size(_around(ps, mid, n)) <= MAX_DOC_CHARS:
                lo = mid
            else:
                hi = mid - 1
        chosen = _around(ps, lo, n)
    low = text.lower()
    hits = []
    for w in {x.lower() for x in wanted if x}:
        for m in re.finditer(re.escape(w), low):
            hits.append((m.start(), m.end(), w))
    clusters: list[list] = []                       # [start, end, {terms}, [hit positions]]
    for a0, b0, w in sorted(hits):
        a, b = max(0, a0 - WINDOW), min(n, b0 + WINDOW)
        if clusters and a <= clusters[-1][1]:
            clusters[-1][1] = max(clusters[-1][1], b)
            clusters[-1][2].add(w); clusters[-1][3].append(a0)
        else:
            clusters.append([a, b, {w}, [a0]])
    for c in sorted(clusters, key=lambda c: (-len(c[2]), c[0])):
        room = MAX_DOC_CHARS - _size(chosen) - (len(DOC_SEP) if chosen else 0)
        if room <= 0:
            break
        a, b = c[0], c[1]
        if b - a > room:                            # centred on the cluster's middle hit
            mid = c[3][len(c[3]) // 2]
            a = max(c[0], min(mid - room // 2, c[1] - room))
            b = a + room
        trial = _merge(chosen + [(a, b)])
        if _size(trial) <= MAX_DOC_CHARS:
            chosen = trial
    if not chosen:
        return text[:MAX_DOC_CHARS], True
    return DOC_SEP.join(text[a:b] for a, b in chosen), True


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


class ReplyCutOff(AuditFailure):
    """The reply reached its max_tokens and was cut off. It carries what the
    call cost (`usage`), since it was paid for; `cut_off` lets a caller that
    loaded this module under another name recognise it (ruling.py)."""
    cut_off = True

    def __init__(self, msg: str, usage: dict | None = None):
        super().__init__(msg)
        self.usage = usage or {}


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
# delivery, not a finding about the sentence -- IF THE DELIVERY RECORD AGREES.
#
# THE DELIVERY RECORD DECIDES (2026-10-22). On WHU-S02 a reader wrote that "the
# source's claim Remote CBT was not shown", and the old pattern (a document
# word, then anything for 80 characters, then "was not shown") stopped the run
# as DOCUMENT_NOT_DELIVERED although every document of the batch had been
# delivered whole, with every bound passage in it. Now a reader's wording only
# stops the run when the batch's delivery record (delivery_report) shows a
# document delivered empty or a bound passage missing (delivery_fault). With a
# clean record the finding is an ordinary finding: it goes to the ruling model
# with its quoted passages as usual, and the ruling's log record carries the
# tag "reader_claimed_missing_but_delivered". (check_delivery already stops a
# batch whose record is not clean before the reader is called, so the stop
# here is the second line, not the first.)
#
# _SAYS_MISSING matches only a statement about the document or text itself,
# its subject next to the claim: "the document (provided) is empty", "the
# source text was not provided", "no text was provided", "the full text is
# unavailable", "the document could not be read", "could not open the paper".
# A document word followed some words later by "was not shown" is not one.
READER_CLAIMED_MISSING = "reader_claimed_missing_but_delivered"
_DOC = r"(?:document|text|source|paper|article|abstract|passage|pdf|file)s?"
_GONE = (r"(?:empty|blank|missing|unavailable|unreadable|illegible|"
         r"not\s+(?:provided|available|included|given|delivered|supplied|attached|present|readable))")
_SAYS_MISSING = re.compile(
    # the [adjective] document [provided] is/was/appears (to be) empty|not provided|...
    r"\b(?:the|this|that|its|any|a|an)\s+(?:[a-z-]+\s+)?" + _DOC
    + r"(?:\s+(?:provided|given|supplied|delivered|attached))?(?:\s+(?:for|from)\s+S\d+)?"
    r"\s+(?:itself\s+)?(?:is|was|were|are|appears?|seems?)(?:\s+to\s+be)?\s+" + _GONE + r"\b"
    # source text not provided / document unavailable (no verb)
    r"|\b(?:source|document|full)\s+" + _DOC + r"\s+(?:not\s+(?:provided|available|supplied|delivered)|unavailable)\b"
    # an empty document / a blank text
    r"|\b(?:an?|the)\s+(?:empty|blank)\s+" + _DOC + r"\b"
    # no (document|source|full) text (was) provided / no document text
    r"|\bno\s+(?:document\s+|source\s+|full\s+)?text\s+(?:was\s+|is\s+|has\s+been\s+)?"
    r"(?:provided|given|supplied|delivered|available|included)\b"
    r"|\bno\s+(?:document|source)\s+text\b"
    # the document could not be read / could not read the document
    r"|\b(?:the|this|that|its|any)\s+(?:[a-z-]+\s+)?" + _DOC
    + r"\s+(?:could|can)\s*not\s+be\s+(?:read|opened|accessed|loaded|seen)\b"
    r"|\b(?:could|can)\s*not\s+(?:see|read|access|open|load)\s+(?:the|any|this|that)\s+(?:[a-z-]+\s+)?"
    + _DOC + r"\b", re.I)


def says_document_missing(v: dict) -> bool:
    return bool(_SAYS_MISSING.search(" ".join(str(v.get(k) or "") for k in ("kind", "reason"))))


def delivery_fault(rep: list[dict]) -> str | None:
    """What the batch's delivery record shows went wrong (a document delivered
    empty, a bound passage missing), or None when it is clean."""
    for r in rep:
        if not r.get("delivered_chars"):
            return "%s delivered empty" % r.get("source")
        if not r.get("spans_inside", True):
            return "%s delivered without %d bound passage(s)" % (r.get("source"), len(r.get("missing_spans") or []))
    return None


def _claimed_missing(v: dict, u: dict, who: str, rep: list[dict]) -> dict:
    """A finding whose wording says its document was missing: DOCUMENT_NOT_DELIVERED
    if the batch's delivery record shows a fault, else the tag for its ruling's
    log record ({} for an ordinary finding)."""
    if not says_document_missing(v):
        return {}
    fault = delivery_fault(rep)
    if fault:
        raise DocumentNotDelivered("%s: the %s's finding says a document was empty or unavailable (%r) "
                                   "and the delivery record shows %s; not sent to the ruling model"
                                   % (u["id"], who, (v.get("reason") or "")[:160], fault))
    return {"tags": [READER_CLAIMED_MISSING]}


def doc_passages(slug: str, batch: list[dict], held: dict[str, str],
                 licensed: frozenset = frozenset()) -> dict[str, tuple[str, list[str]]]:
    """{source id: (held text, the batch's bound passages in it)} for every
    document the batch's sentences rest on that may be sent."""
    out: dict[str, tuple[str, list[str]]] = {}
    for u in batch:
        for sid in sources_of(u["row"] or {}):
            if sid in out or sid in licensed:
                continue
            text = held.get("%s:%s" % (slug, sid)) or held.get(sid)
            if text is None:
                continue
            must = [x.get("span") or "" for b in batch for x in
                    [b["row"] or {}] + ((b["row"] or {}).get("also_rests_on") or [])
                    + ((b["row"] or {}).get("premises") or [])
                    if x.get("source_id") == sid and x.get("span")]
            out[sid] = (text, must)
    return out


def batch_fits(slug: str, batch: list[dict], held: dict[str, str],
               licensed: frozenset = frozenset()) -> bool:
    if all(u["part"] in SUMMARY_PARTS for u in batch):
        return True
    return all(passages_fit(t, m) for t, m in doc_passages(slug, batch, held, licensed).values())


def fit_batches(slug: str, bs: list[list[dict]], held: dict[str, str],
                licensed: frozenset = frozenset(), splits: list | None = None) -> list[list[dict]]:
    """BS with every batch whose bound passages (each with MIN_CONTEXT) do not
    fit one document's MAX_DOC_CHARS split in halves until they do, or down to
    one sentence, which trim() delivers whole whatever its size. A run never
    fails on size alone (2026-10-21). Each split is noted in SPLITS."""
    out = []

    def go(b):
        if len(b) <= 1 or batch_fits(slug, b, held, licensed):
            out.append(b)
            return
        if splits is not None:
            splits.append({"units": [u["id"] for u in b], "into": 2,
                           "why": "bound passages with %d characters of context each exceed %d "
                                  "characters of one document" % (MIN_CONTEXT, MAX_DOC_CHARS)})
        h = len(b) // 2
        go(b[:h]); go(b[h:])
    for b in bs:
        go(b)
    return out


def batch_inputs(slug: str, batch: list[dict], held: dict[str, str],
                 licensed: frozenset = frozenset()) -> tuple[dict[str, str], dict[str, dict]]:
    """(documents {id: text}, records {id: {path, text}}) for one batch. A
    licensed source is never a document, whatever the held texts contain."""
    terms_ = sorted(terms([b["sentence"] for b in batch]))
    docs = {sid: trim(text, terms_, must)[0]
            for sid, (text, must) in doc_passages(slug, batch, held, licensed).items()}
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
    t = _frozen().read_text(SUMMARY_PROMPT)
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
    t = _frozen().read_text(READ_PROMPT)
    return t.replace("{documents}", "DOCUMENTS\n\n" + dtext).replace("{records}", "RECORDS\n\n" + rtext) \
            .replace("{sentences}", stext)


def parse_json(text: str) -> dict | list:
    s = jsonio.strip_code_fence(text)
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


_QUOTE_MARKS = "\"'«»‹›„‟"


def quote_body(q: str) -> str:
    """A quotation as matched: normalised as norm() normalises, with any
    quotation marks ENCLOSING it removed -- a reader or the source advocate
    often wraps what it quotes in quote marks the document does not carry.
    Only a pair at both ends is removed (repeatedly, for nested pairs); the
    interior must still match exactly. 2026-10-20: four of WHU-P02's advocate
    quotations were verbatim once their own enclosing quote marks were
    removed."""
    s = norm(q or "").strip()
    while len(s) >= 2 and s[0] in _QUOTE_MARKS and s[-1] in _QUOTE_MARKS:
        s = s[1:-1].strip()
    return s


def quoted_in(q: str, hay: str) -> bool:
    """Is quotation Q, word for word, in HAY (enclosing quote marks aside)?"""
    body = quote_body(q)
    return bool(body) and body in norm(hay or "")


def _norm_piece(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("–", "-"), ("—", "-"), ("−", "-"), (" ", " ")):
        s = s.replace(a, b)
    return s.lower()


def norm_map(s: str) -> tuple[str, list[int]]:
    """(norm(s), offsets): offsets[i] is the index in S of the character that
    produced norm(s)[i]. Normalised a base character with its combining marks
    at a time, so NFKC composes as it does on the whole string."""
    out, offs, i, n = [], [], 0, len(s or "")
    while i < n:
        j = i + 1
        while j < n and unicodedata.combining(s[j]):
            j += 1
        for ch in _norm_piece(s[i:j]):
            if ch.isspace():
                if out and out[-1] != " ":
                    out.append(" "); offs.append(i)
            else:
                out.append(ch); offs.append(i)
        i = j
    if out and out[-1] == " ":
        out.pop(); offs.pop()
    return "".join(out), offs


def locate(q: str, hay: str) -> tuple[int, int] | None:
    """Where quotation Q sits in HAY, as (start, end) offsets of HAY, found by
    the comparison quoted_in uses (norm(), enclosing quote marks aside) --
    never by an exact match on part of the quotation. None if it is not there."""
    body = quote_body(q)
    if not body or not hay:
        return None
    normed, offs = norm_map(hay)
    k = normed.find(body)
    if k < 0:
        return None
    return offs[k], offs[k + len(body) - 1] + 1


def in_context(q: str, hay: str, around: int) -> str:
    """The passage of HAY holding quotation Q with AROUND characters either
    side; Q alone when it is not in HAY."""
    at = locate(q, hay)
    if at is None:
        return q
    return hay[max(0, at[0] - around): at[1] + around]


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
        if not quoted_in(q, hay):
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
        around = in_context(q, hay or "", QUOTE_AROUND)
        quoted.append("Quotation %d: \"%s\"\nIn its document: ...%s..." % (n, q, " ".join(around.split())))
    payload = {"sentence": sentence, "kind": finding.get("kind") or "",
               "reason": finding.get("reason") or "", "proposed_text": finding.get("proposed_text") or "",
               "quoted_source_text": "\n\n".join(quoted)}
    assert tuple(payload) == RULE_FIELDS
    return payload


def build_rule_prompt(payload: dict) -> str:
    t = _frozen().read_text(RULE_PROMPT)
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

    model = MODEL                       # a Caller built without __init__ (tests) runs MODEL

    def __init__(self, *, cap: float, ledger_issue: str, ask=None, day_cap=None, model: str = MODEL):
        self.cap, self.issue, self.calls = cap, ledger_issue, []
        # The model this caller runs. MODEL unless lean WHU's tiering asks for
        # another (lean.model_for); every call record names it.
        self.model = model
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

    def __call__(self, prompt: str, max_tokens: int, role: str, cache_prefix: str | None = None) -> tuple[str, dict]:
        # CACHE_PREFIX (lean WHU only): the leading part of PROMPT to mark for
        # the prompt cache. The text sent is PROMPT either way.
        extra = {}
        if self.model != MODEL:
            extra["model"] = self.model
        if cache_prefix and prompt.startswith(cache_prefix):
            extra["cache_prefix_chars"] = len(cache_prefix)
        if self._ask is not None:
            if self._day_cap is not None:
                self._day_cap(0.0)
            text, usage = self._ask(prompt, max_tokens)
            stop = usage.pop("stop_reason", None) if isinstance(usage, dict) else None
            self.calls.append({"role": role, **extra, **usage})
            if stop == "max_tokens":
                raise ReplyCutOff("reply cut off at %d tokens (%s)" % (max_tokens, role), usage)
            return text, usage
        content = prompt
        if cache_prefix:
            import lean
            content = lean.cache_blocks(prompt, cache_prefix)
        n_in = self._raw.messages.count_tokens(model=self.model,
                                               messages=[{"role": "user", "content": content}]).input_tokens
        p = S.rates(self.model, n_in) if hasattr(S, "rates") else S.PRICES[self.model]
        # A cached prefix may be written at the cache-write price, the higher one.
        worst = (n_in * max(p["input"], p["cache_write"] if cache_prefix else 0) + max_tokens * p["output"]) / 1e6
        if self._spent() - self._start + worst > self.cap:
            raise AuditFailure("spend cap: this call could cost $%.3f; the run has spent $%.3f of $%.2f"
                               % (worst, self._spent() - self._start, self.cap))
        # The issue's cap as well as the day cap (protocol rev 27: a study issue is
        # capped at caps.json's study_per_issue). check_cap checks both.
        S.check_cap(self.issue, worst)
        t0 = time.time()
        r = self._client.messages.create(model=self.model, max_tokens=max_tokens,
                                         messages=[{"role": "user", "content": content}])
        if r.stop_reason == "refusal":
            raise AuditFailure("the model refused (%s)" % role)
        text = "".join(getattr(b, "text", "") for b in r.content)
        usd, counts = S.price(r.model, r.usage)
        usage = {"input": counts["input"], "output": counts["output"], "usd": usd or 0.0,
                 "seconds": round(time.time() - t0, 1)}
        if counts.get("cache_write") or counts.get("cache_read"):
            usage.update(cache_write=counts["cache_write"], cache_read=counts["cache_read"])
        self.calls.append({"role": role, **extra, **usage})
        if r.stop_reason == "max_tokens":
            # Paid for, so counted above; the caller decides what a cut-off
            # reply means (ruling.py retries once, 2026-10-22).
            raise ReplyCutOff("reply cut off at %d tokens (%s)" % (max_tokens, role), usage)
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
               deliveries: list | None = None, on_reject=None,
               inputs: tuple | None = None, cache_sid: str | None = None) -> tuple[list[dict], dict, dict]:
    """INPUTS (lean WHU): this batch's (docs, records), built by lean_audit;
    CACHE_SID: the source whose document block ends the prompt's cached prefix."""
    summary = all(u["part"] in SUMMARY_PARTS for u in batch)
    if summary:
        docs, records = {"PAGE": body}, {}
        build = lambda bs: build_summary_prompt(bs, body)
    else:
        docs, records = inputs if inputs is not None else batch_inputs(slug, batch, held, licensed)
        build = lambda bs: build_read_prompt(bs, docs, records, ctx, licensed)
        # FAIL CLOSED, BEFORE ANY CALL: every document delivered non-empty and
        # holding every span its sentences are bound to. Recorded either way.
        rep = delivery_report(slug, batch, held, docs, licensed)
        if deliveries is not None:
            deliveries.extend(dict(r, role=role) for r in rep)
        check_delivery(rep)
    def ask(prompt: str, r: str):
        if cache_sid and not summary:
            import lean_audit
            pre = lean_audit.cache_prefix(prompt, cache_sid)
            if pre:
                return call(prompt, READ_MAX_OUT, r, cache_prefix=pre)
        return call(prompt, READ_MAX_OUT, r)
    text, usage = ask(build(batch), role + ("-summary" if summary else ""))
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
        t2, _u2 = ask(p2, role + "-requote")
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
               "second_seed", "inputs", "lean_config")


def _ask_for(ask, model: str):
    """A test's fake ASK for one model: ask(prompt, max_tokens) as always, or
    ask(prompt, max_tokens, model) when it takes the model (lean tiering tests)."""
    if ask is None:
        return None
    import inspect
    try:
        n = len(inspect.signature(ask).parameters)
    except (TypeError, ValueError):
        n = 2
    return (lambda p, m: ask(p, m, model)) if n >= 3 else ask


def _snap(u: dict, **extra) -> dict:
    return {**{k: u[k] for k in UNIT_KEYS if k in u}, **extra}


def run(slug: str, *, out_dir: Path, limit: int | None = None, cap: float = 40.0,
        ledger_issue: str | None = None, ask=None, held: dict | None = None,
        unit_list: list[dict] | None = None, licensed: set | None = None,
        seed: int = SECOND_SEED, resume: bool = False, day_cap=None,
        prior_dir: Path | None = None) -> dict:
    """PRIOR_DIR (lean WHU only): the earlier complete run an incremental
    re-audit carries verdicts from (reaudit.prior_run)."""
    import lean
    LEAN = lean.enabled()
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
        # Batches split because their bound passages did not fit one document.
        "splits": [],
    }
    if LEAN:
        import passage_index as PI
        manifest["lean_config"] = {"models": {k: lean.model_for(k) for k in
                                              ("audit_first", "audit_escalate", "audit_rule", "audit_second")},
                                   "k": PI.K, "min_score": PI.MIN_SCORE, "min_terms": PI.MIN_TERMS,
                                   "passage_chars": PI.PASSAGE_CHARS}
        manifest["unit_list"] = [[u["id"], u["part"], u["sha"]] for u in us]
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
        manifest["splits"] = list(prior.get("splits") or [])
        manifest["resumed"] = (prior.get("resumed") or []) + [
            {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "after": prior.get("failure"), "usd_before": prior.get("usd") or 0.0}]
    prior_usd = float((prior or {}).get("usd") or 0.0)
    # The run's cap covers every day it runs on, not each resume afresh.
    # Lean WHU: one caller per model (lean.STAGE_MODELS); off, one caller for all.
    callers: dict[str, Caller] = {}

    def caller(stage: str) -> Caller:
        m = lean.model_for(stage) if LEAN else MODEL
        if m not in callers:
            callers[m] = Caller(cap=cap - prior_usd, ledger_issue=ledger_issue or slug,
                                ask=_ask_for(ask, m), day_cap=day_cap, model=m)
        return callers[m]
    call = caller("audit_first")
    big, rule_call, second_call = caller("audit_escalate"), caller("audit_rule"), caller("audit_second")
    kinds = ("verdicts", "rulings", "cuts", "second_reads", "quote_rejections") + (("retrieval",) if LEAN else ())
    files = {k: open(out_dir / ("%s.jsonl" % k), "a" if prior else "w", encoding="utf-8") for k in kinds}

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
            protected_kind = _B().protected_kind
            gen, carry = [], {}
            if LEAN:
                import lean_sentences as LS
                import reaudit as RA
                gen = LS.generated(slug)
                rp = RA.plan(slug, us, held, manifest, prior_dir)
                manifest["reaudit"] = {k: v for k, v in rp.items() if k != "carry"}
                manifest["reaudit"]["carried"] = len(rp["carry"])
                carry = rp["carry"]
            for u in us:
                g = LS.matches(u["sentence"], gen) if (gen and u["part"] == "page") else None
                if g:
                    # Lean WHU: a generated sentence, word for word what issue.json
                    # and sources.json generate now. Code's check replaces a
                    # person's read for it (lean_sentences.py).
                    state[u["sha"]] = LS.RECORD_CHECK
                    prog["done"][u["id"]] = _snap(u, status=LS.RECORD_CHECK)
                    log("verdicts", {"unit": u["id"], "part": u["part"], "sha": u["sha"], "round": 0,
                                     "sentence": u["sentence"], "verdict": LS.RECORD_CHECK,
                                     "generated": {"kind": g["kind"], "source": g["source"], "field": g["field"]},
                                     "reason": "generated from %s and checked against it by code" % g["field"]})
                    continue
                if u["id"] in carry:
                    # Lean WHU: unchanged since the prior run; its verdict carried by fingerprint.
                    state[u["sha"]] = carry[u["id"]]
                    prog["done"][u["id"]] = _snap(u, status=carry[u["id"]], carried_from=rp["from"])
                    log("verdicts", {"unit": u["id"], "part": u["part"], "sha": u["sha"], "round": 0,
                                     "sentence": u["sentence"], "verdict": "carried",
                                     "status": carry[u["id"]], "carried_from": rp["from"],
                                     "reason": "unchanged since audit run %s (incremental re-audit)" % rp["from"]})
                    continue
                kind = protected_kind(u["sentence"], u.get("row")) if u["part"] == "page" else None
                if kind:
                    # The question restatement, or what we held, read or did not
                    # read: no document records that, so a reader of documents
                    # can only find it unsupported and a ruling can only narrow
                    # or cut it (WHU-S08 u45, u46, u47, u14). A person reads it;
                    # it is never ruled, corrected or cut here.
                    state[u["sha"]] = HUMAN_READ_REQUIRED
                    prog["done"][u["id"]] = _snap(u, status=HUMAN_READ_REQUIRED)
                    log("verdicts", {"unit": u["id"], "part": u["part"], "sha": u["sha"], "round": 0,
                                     "sentence": u["sentence"], "verdict": HUMAN_READ_REQUIRED,
                                     "protected": kind,
                                     "reason": "protected sentence (%s): a person reads it; never "
                                               "ruled, corrected or cut by the audit" % kind})
                    continue
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
            bs = fit_batches(slug, batches([live(s) for s in prog["queue"]]), held, lic, manifest["splits"])
            if LEAN:
                import lean_audit as LA
                rlog: list = []
                gdocs = LA.group_documents(slug, bs, held, lic, log=rlog)
            for bi, batch in enumerate(bs):
                inputs = cache_sid = None
                if LEAN and not all(u["part"] in SUMMARY_PARTS for u in batch):
                    inputs = LA.batch_inputs(slug, batch, held, lic, group_docs=gdocs.get(bi), log=rlog)
                    cache_sid = next(iter(gdocs[bi])) if bi in gdocs else None
                    for r_ in rlog:
                        log("retrieval", dict(r_, batch=bi))
                    rlog.clear()
                vs, docs, records = read_batch(call, slug, batch, held, ctx, "read", lic, body,
                                               deliveries=manifest["deliveries"],
                                               on_reject=lambda r: log("quote_rejections", r),
                                               inputs=inputs, cache_sid=cache_sid)
                decided = {}
                if LEAN and big is not call:
                    esc = [u for u, v in zip(batch, vs) if LA.needs_escalation(u, v)]
                    if esc:
                        for u, v in zip(batch, vs):
                            if u in esc:
                                log("verdicts", {"unit": u["id"], "part": u["part"], "sha": u["sha"],
                                                 "round": u["round"], "sentence": u["sentence"],
                                                 **{k: v.get(k) for k in ("verdict", "kind", "evidence",
                                                                          "proposed_text", "reason")},
                                                 "model": call.model, "escalated": True})
                        v2, _d, _r = read_batch(big, slug, esc, held, ctx, "read-escalate", lic, body,
                                                deliveries=manifest["deliveries"],
                                                on_reject=lambda r: log("quote_rejections", r),
                                                inputs=(docs, records))
                        again = {u["id"]: v for u, v in zip(esc, v2)}
                        vs = [again.get(u["id"], v) for u, v in zip(batch, vs)]
                        decided = {i: big.model for i in again}
                for u, v in zip(batch, vs):
                    log("verdicts", {"unit": u["id"], "part": u["part"], "sha": u["sha"], "round": u["round"],
                                     "sentence": u["sentence"], **{k: v.get(k) for k in
                                     ("verdict", "kind", "evidence", "proposed_text", "reason")},
                                     **({"read_without_licensed_sources": u["licensed_excluded"]}
                                        if u.get("licensed_excluded") else {}),
                                     **({"decided_by": decided.get(u["id"], call.model)} if LEAN else {})})
                    if v["verdict"] != "finding":
                        state[u["sha"]] = v["verdict"]
                        prog["done"][u["id"]] = _snap(u, status=v["verdict"])
                        finish(u)
                        continue
                    tags = _claimed_missing(v, u, "reader", delivery_report(slug, batch, held, docs, lic))
                    payload = ruling_payload(v, u["sentence"], docs, records)
                    rtext, _ru = rule_call(build_rule_prompt(payload), RULE_MAX_OUT, "rule")
                    r = check_ruling(parse_json(rtext))
                    log("rulings", {"unit": u["id"], "sha": u["sha"], "round": u["round"],
                                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "by": "ruling model %s" % rule_call.model, "model": rule_call.model,
                                    "prompt_sha256": sha(RULE_PROMPT.read_text(encoding="utf-8")),
                                    "inputs": payload, "payload_sha256": sha(json.dumps(payload)),
                                    **r, **tags})
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
            # A verdict carried from an earlier run was sampled (or not) there.
            final = [prog["done"][u["id"]] for u in us
                     if prog["done"].get(u["id"], {}).get("status") in SETTLED
                     and not prog["done"][u["id"]].get("carried_from")]
            had_finding = [s["id"] for s in final if s["id"] in flagged]
            held_first = [s["id"] for s in final if s["id"] not in flagged]
            k = max(1, round(SECOND_SHARE * len(held_first))) if held_first else 0
            sampled = random.Random(seed).sample(held_first, k) if k else []
            prog["second"] = {"seed": seed, "flagged": had_finding, "holds_pool": len(held_first),
                              "sampled": sampled, "todo": had_finding + sampled}
        sec = prog["second"]
        for batch in fit_batches(slug, batches([live(prog["done"][i]) for i in sec["todo"]]), held, lic,
                                 manifest["splits"]):
            inputs = None
            if LEAN and not all(u["part"] in SUMMARY_PARTS for u in batch):
                import lean_audit as LA
                rl: list = []
                inputs = LA.batch_inputs(slug, batch, held, lic, log=rl)
                for r_ in rl:
                    log("retrieval", dict(r_, batch="second"))
            vs, docs, records = read_batch(second_call, slug, batch, held, ctx, "second-read", lic, body,
                                           deliveries=manifest["deliveries"],
                                           on_reject=lambda r: log("quote_rejections", r), inputs=inputs)
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
                    tags = _claimed_missing(v, u, "second reader",
                                            delivery_report(slug, batch, held, docs, lic))
                    payload = ruling_payload(v, u["sentence"], docs, records)
                    rtext, _ru = rule_call(build_rule_prompt(payload), RULE_MAX_OUT, "rule-second")
                    r = check_ruling(parse_json(rtext))
                    # A card or meta wording that is not a whole body sentence
                    # is recorded with apply: False and left for a person.
                    summary_bad = (u["part"] in SUMMARY_PARTS and r["ruling"] != "reject"
                                   and not body_sentence(r["text"] or "", us))
                    log("rulings", {"unit": u["id"], "sha": u["sha"], "round": "second",
                                    "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                    "by": "ruling model %s" % rule_call.model, "model": rule_call.model,
                                    "prompt_sha256": sha(RULE_PROMPT.read_text(encoding="utf-8")),
                                    "inputs": payload, "payload_sha256": sha(json.dumps(payload)), **r, **tags,
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
        manifest["calls"] = list((prior or {}).get("calls") or []) + [c for k in callers for c in callers[k].calls]
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


def is_withdrawn(run_dir: Path) -> dict | None:
    """The run's withdrawal record ({reason, on}) if its manifest has one."""
    try:
        w = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8")).get("withdrawn")
    except Exception:
        return None
    return w if isinstance(w, dict) and w.get("reason") else None


def withdraw(run_dir: Path, reason: str, on: str | None = None) -> dict:
    """Mark a run withdrawn in its manifest, with the reason and the date. Its
    rulings are then not expected on the page (applied_check) and it is never
    the run preflight reads (latest_run). Nothing else in the run changes.

    A LIST, NOT A FIELD (2026-10-20). Withdrawing a run again appends the new
    reason to "reasons", each with its date, oldest first; "reason" and "on"
    are the latest. Until then the second withdrawal overwrote the first:
    WHU-P02's 20261020T173234Z lost "documents delivered empty (GAP-015)" when
    it was withdrawn again for "made before ruling payloads carried context"."""
    mp = Path(run_dir) / "manifest.json"
    m = json.loads(mp.read_text(encoding="utf-8"))
    if not (reason or "").strip():
        raise ValueError("a withdrawal needs a reason")
    rec = {"reason": reason.strip(), "on": on or datetime.now(timezone.utc).date().isoformat()}
    old = m.get("withdrawn") if isinstance(m.get("withdrawn"), dict) else {}
    reasons = list(old.get("reasons") or ([{"reason": old["reason"], "on": old.get("on")}]
                                          if old.get("reason") else []))
    reasons.append(rec)
    m["withdrawn"] = dict(rec, reasons=reasons)
    mp.write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
    return m["withdrawn"]


def latest_run(slug: str) -> Path | None:
    root = audit_root(slug)
    if not root.exists():
        return None
    runs = sorted(p for p in root.iterdir() if (p / "manifest.json").exists() and not is_withdrawn(p))
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
            bits.append("%d sentence(s) need a person's read (resting only on a source no model may read, "
                        "a failed read, or a protected sentence) and have no recorded human read "
                        "(human_reads.jsonl; e.g. %r)" % (len(human), human[0]["sentence"][:80]))
        if unread:
            bits.append("%d sentence(s) have no audit verdict on their current wording (e.g. %r)"
                        % (len(unread), unread[0]["sentence"][:80]))
        if leave:
            bits.append("%d sentence(s) were corrected or cut by the audit and are still on the page (e.g. %r)"
                        % (len(leave), leave[0]["sentence"][:80]))
        return [(ROW_LABEL, BAD, "; ".join(bits) + ". Apply the rulings and re-run the audit.")]
    return [(ROW_LABEL, OK, "every one of %d sentences is settled in audit run %s" % (len(us), run_dir.name))]


def _stage_guard(issue: str, n_units: int) -> None:
    """Before the run's first paid call (stage_cap.py): refuse to start if the
    estimate from measured audit runs exceeds the cap left today or on the issue."""
    import stage_cap
    stage_cap.guard("audit", issue, n_units)


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
    w = sub.add_parser("withdraw", help="mark a run withdrawn: its rulings no longer apply")
    w.add_argument("slug"); w.add_argument("run_dir"); w.add_argument("--reason", required=True)
    import lean
    argv = lean.strip_flag(argv)          # --lean: lean WHU (lean.py); default off
    a = ap.parse_args(argv)
    if a.cmd == "withdraw":
        rd = Path(a.run_dir)
        if not rd.is_absolute():
            rd = audit_root(a.slug) / a.run_dir if not rd.exists() else rd
        print(json.dumps(withdraw(rd, a.reason), ensure_ascii=False))
        return 0
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
        done = len(((prior.get("progress") or {}).get("done")) or {})
        _stage_guard(a.ledger_issue or prior.get("ledger_issue") or a.slug,
                     max(0, (prior.get("units") or 0) - done))
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
    n = len(units(a.slug))
    _stage_guard(a.ledger_issue or a.slug, min(n, a.limit) if (a.dry_run and a.limit) else n)
    prior_dir = None
    if lean.enabled() and not a.dry_run:
        import reaudit
        prior_dir = reaudit.prior_run(a.slug)
    m = run(a.slug, out_dir=out, limit=a.limit if a.dry_run else None, cap=a.cap,
            ledger_issue=a.ledger_issue, prior_dir=prior_dir)
    print(json.dumps({k: m.get(k) for k in ("status", "failure", "units", "usd", "second_read")}, indent=1))
    return 0 if m["status"] == "complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())
