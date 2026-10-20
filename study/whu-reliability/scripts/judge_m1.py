#!/usr/bin/env python3
"""Run the M1 (citation support) judge prompt with a Claude and a ChatGPT judge.

Usage:
    judge_m1.py RUN_DIR [--cap USD] [--only P01,P03] [--judges claude,openai]
                [--tag SUFFIX] [--ledger-issue NAME]
                [--consistency-share 0.2] [--seed N]

RUN_DIR holds items.json (claim, context, reference label, the URLs the
sentence cites) and sources/ (from snapshot.py: one snapshot per source, with
manifest.json). Replies go to RUN_DIR/replies<tag>/<judge>/<item>.json.

WHAT THE RUNNER DECIDES, AND THE PROMPT DOES NOT (rulings of 19 October 2026,
protocol "Rulings from prep round 1"):

  Refusal. A refused call is retried once, unchanged. Refused again, the
  judge's label is REFUSED, the item is flagged for a person, and the other
  judge's label stands alone. The input is never reworded.

  Abstract only. If a cited snapshot is abstract-only (the manifest's
  abstract_only flag, decided by snapshot.py from the stored text) and the
  judge says Absent, the recorded label is NOT_VERIFIABLE_ABSTRACT: excluded
  from the rate like Unreachable, and reported.

  Length. Each snapshot is counted in tokens (Anthropic's count_tokens, free).
  Up to MAX_SOURCE_TOKENS it goes whole. Above that, chunk() keeps every
  section containing the claim's key terms, and the item is marked CHUNKED.

  Several sources. Every cited snapshot is given, in the order the sentence
  cites them. If any work the sentence cites has no snapshot (no URL in the
  answer, or unreachable), the item is INCOMPLETE_SOURCES: no judge is called,
  and it goes to a person. A sentence is never judged on part of its sources.
  Items list every cited work under "citations" ({label, url}); "urls" is the
  older field and is read as citations with no labels.
  --allow-incomplete judges such an item on the snapshots that exist; it is for
  tests of the judges themselves (the authorship bias test), never for labels.

ONE READ, AND A SEEDED SAMPLE READ TWICE (budget ruling, protocol rev 26,
20 October 2026). Each judge reads each item once. A seeded random
--consistency-share (default 20%) of the items is read a second time by each
judge, into RUN_DIR/replies<tag>_repeat/, for the run-to-run consistency
report. The pool is the items that will be judged (not INCOMPLETE_SOURCES, at
least one reachable source), decided from the manifest before any call, so
the sample is drawn and written to RUN_DIR/replies<tag>/consistency_sample.json
(seed, share, pool, items) before the first call; an invocation that would
draw a different sample stops instead. A sampled item's second read follows
its first straight away, while the source block is still in each API's cache.

CACHING. The documents come first in the prompt so the source block can be
cached: on Claude with an explicit cache_control breakpoint at the end of the
documents, on OpenAI by its automatic prefix caching with a prompt_cache_key
naming the documents. Two runs of one item, or two sentences citing the same
source, then pay full input price once.

SPEND. Every call lands in backend/data/spend/ledger.jsonl under
--ledger-issue. Before each call the worst case (all input at the cache-write
price, plus the output ceiling) is added to what that issue has spent, and the
runner stops if it would pass --cap.
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

import httpx

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
# By file path: putting backend/scripts on sys.path would shadow the standard
# library's `signal` with backend/scripts/signal/, which breaks httpx's imports.
_spec = importlib.util.spec_from_file_location("spend_ledger", ROOT / "backend" / "scripts" / "spend_ledger.py")
S = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S)

PROMPT = STUDY / "prompts" / "m1_citation_support.md"
LABELS = ["Supported", "Overstates", "Understates", "Absent", "Wrong source",
          "Contradicted", "Unreachable"]
REFUSED = "REFUSED"
INCOMPLETE_SOURCES = "INCOMPLETE_SOURCES"
NOT_VERIFIABLE_ABSTRACT = "NOT_VERIFIABLE_ABSTRACT"
SCRIPT = "study/whu-reliability/judge_m1.py"
CONTEXT_CHARS = 400
MAX_SOURCE_TOKENS = 150_000
CONSISTENCY_SHARE = 0.20
CONSISTENCY_SEED = 20261020
REPEAT_SUFFIX = "_repeat"

CLAUDE_MODEL = "claude-opus-5-5"
CLAUDE_MAX_OUT = 1024
OPENAI_MODEL = "gpt-6-astra"
OPENAI_MAX_OUT = 6000           # reasoning tokens count as output
# Standard tier, checked 2026-10-19 at developers.openai.com/api/docs/pricing.
OPENAI_PRICE = {"input": 10.00, "cached_input": 1.00, "output": 50.00}

STOP = set("""a an the and or of in on at to for from by with without as is are was were be been being
this that these those it its their there which who whom whose what when where how than then also not no
but if so such into over under after before between about among per vs versus more most less least very
""".split())


def env_keys() -> dict:
    out = {}
    for line in (ROOT / "backend" / ".env").read_text().splitlines():
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m:
            out[m.group(1)] = m.group(2).strip().strip("'\"")
    return out


def spent(issue: str) -> float:
    return sum(float(e.get("usd") or 0) for e in S.entries() if e.get("issue") == issue)


# --------------------------------------------------------------------------
# Long sources
# --------------------------------------------------------------------------

def key_terms(claim: str) -> tuple[set[str], set[str]]:
    """(numbers, words) the claim turns on. Numbers are kept as written (with
    decimals and %); words are capitalised names and content words of seven or
    more letters, lowercased. Deterministic, so a chunked item can be rebuilt."""
    nums = {n.rstrip(".,") for n in re.findall(r"\d[\d.,]*%?", claim) if len(n.rstrip(".,")) >= 2}
    words = set()
    for w in re.findall(r"[A-Za-z][A-Za-z'-]+", claim):
        lw = w.lower()
        if lw in STOP:
            continue
        if (w[0].isupper() and len(w) >= 3) or len(w) >= 7:
            words.add(lw)
    return nums, words


def _fit(s: str, centre: int, limit: int, count) -> str:
    """The longest slice of S around CENTRE whose token count is within LIMIT."""
    if count(s) <= limit:
        return s
    n = max(1, int(len(s) * limit / max(1, count(s))))
    while True:
        a = max(0, min(centre - n // 2, len(s) - n))
        cut = s[a:a + n]
        if count(cut) <= limit or n <= 1:
            return cut
        n = max(1, int(n * 0.9))


def chunk(text: str, claim: str, limit: int, count, spans: list[str] | None = None) -> tuple[str, dict]:
    """The sections of TEXT the claim turns on, in order, within LIMIT tokens.

    A section is a block between blank lines. It is kept if it contains a
    cited span, any of the claim's numbers, or at least two of its words.
    Sections with a cited span are ranked first, then by matches. If what is
    kept is above LIMIT, sections are dropped from the weakest up -- but never
    the last one. `count` is a token counter (text -> int), passed in so the
    test can use a fake one.

    NEVER EMPTY FOR A NON-EMPTY SOURCE (2026-10-20, as audit_stage.trim()).
    This used to return "" when no section matched, and when the one matching
    section was over the limit (it was dropped until nothing was left). Now a
    single section over the limit is cut to the limit, centred on the cited
    span (else on the claim's terms), and with no matching section the opening
    of the source is kept, up to the limit."""
    nums, words = key_terms(claim)
    norm = lambda s: " ".join((s or "").split()).lower()
    spans_n = [norm(s) for s in (spans or []) if s]
    secs = [s for s in re.split(r"\n\s*\n", text) if s.strip()]
    scored = []
    for i, s in enumerate(secs):
        low, ns = s.lower(), norm(s)
        sp = sum(1 for x in spans_n if x in ns)
        n = sum(1 for x in nums if x in s)
        w = sum(1 for x in words if x in low)
        if sp or n or w >= 2:
            scored.append((sp * 100 + n * 3 + w, i))
    info = {"sections_total": len(secs), "key_numbers": sorted(nums), "key_words": sorted(words),
            "dropped_for_length": 0, "cut_to_limit": False, "opening_kept": False}
    if not scored:
        # Nothing matched: the opening of the source, up to the limit.
        out = _fit(text, 0, limit, count)
        info.update(sections_kept=0, opening_kept=True, cut_to_limit=len(out) < len(text))
        return out, info
    keep = sorted(i for _sc, i in scored)
    out = "\n\n[...]\n\n".join(secs[i] for i in keep)
    while len(keep) > 1 and count(out) > limit:
        worst = min((sc, i) for sc, i in scored if i in keep)
        keep.remove(worst[1]); info["dropped_for_length"] += 1
        out = "\n\n[...]\n\n".join(secs[i] for i in keep)
    if count(out) > limit:
        # One section left and it is over the limit: cut it, centred on the
        # cited span, else on the claim's terms.
        s = secs[keep[0]]
        low = s.lower()
        at = [low.find(x[:40]) for x in spans_n if low.find(x[:40]) >= 0]
        if not at:
            at = sorted(p for p in [s.find(x) for x in nums] + [low.find(x) for x in words] if p >= 0)
        centre = (at[len(at) // 2] if at else 0) + 20
        out = _fit(s, centre, limit, count)
        info["cut_to_limit"] = True
    info["sections_kept"] = len(keep)
    return out, info


def delivery_problems(full: str, delivered: str, claim: str, spans: list[str] | None = None) -> list[str]:
    """What the judge would NOT receive that its source holds (fail closed,
    2026-10-20). chunk() can return nothing -- no section with the claim's key
    terms, or one such section longer than the limit, dropped until none is
    left -- which is the audit stage's empty-document defect in this runner.
    Every key term of the claim and every cited span that is in the held text
    must be in what is delivered; a term the source does not contain at all is
    not a delivery problem (that is for the judge to find)."""
    out = []
    if full.strip() and not delivered.strip():
        out.append("delivered empty (%d characters held)" % len(full))
        return out
    nums, words = key_terms(claim)
    low_full, low_del = full.lower(), delivered.lower()
    for n in sorted(nums):
        if n in full and n not in delivered:
            out.append("key number %r is in the source but not in what the judge receives" % n)
    for w in sorted(words):
        if w in low_full and w not in low_del:
            out.append("key word %r is in the source but not in what the judge receives" % w)
    norm = lambda s: " ".join((s or "").split()).lower()
    for s in spans or []:
        if s and norm(s) in norm(full) and norm(s) not in norm(delivered):
            out.append("cited span %r is in the source but not in what the judge receives" % s[:80])
    return out


# --------------------------------------------------------------------------
# The prompt
# --------------------------------------------------------------------------

def documents_block(docs: list[dict]) -> str:
    parts = []
    for i, d in enumerate(docs, 1):
        parts.append("<<<DOCUMENT %d (readable extent: %s%s)\n%s\nDOCUMENT %d>>>"
                     % (i, d["extent"], "; long document, only the sections containing the "
                        "sentence's key terms are shown" if d.get("chunked") else "", d["text"], i))
    return "\n\n".join(parts)


def build(item: dict, docs: list[dict]) -> tuple[str, str]:
    """(cacheable prefix, rest). The prefix is everything up to and including
    the documents, so it is identical for any two calls on the same sources."""
    ctx = item.get("context") or ""
    if len(ctx) > CONTEXT_CHARS:
        ctx = "…" + ctx[-CONTEXT_CHARS:].lstrip()
    t = PROMPT.read_text(encoding="utf-8")
    head, tail = t.split("{documents}", 1)
    prefix = head + documents_block(docs)
    rest = tail.replace("{claim}", item["claim"]).replace("{context}", ctx)
    return prefix, rest


def parse(text: str) -> tuple[dict | None, list[str]]:
    """The reply as JSON, and every way it departs from the required form."""
    problems = []
    s = text.strip()
    if s.startswith("```"):
        problems.append("code fence")
        s = re.sub(r"^```(json)?\s*|\s*```$", "", s)
    try:
        obj = json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            return None, problems + ["not JSON"]
        problems.append("text around the JSON")
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return None, problems + ["not JSON"]
    if set(obj) != {"label", "span", "reason"}:
        problems.append("keys %s" % sorted(obj))
    if obj.get("label") not in LABELS:
        problems.append("label %r not in the label set" % obj.get("label"))
    return obj, problems


def norm(s: str) -> str:
    # NFKC first: PDF text keeps ligatures ("Eﬀects") that a judge quoting it
    # types as two letters; the quote is still verbatim.
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("−", "-").replace("·", ".")
    return " ".join(s.split()).lower()


def final_label(judge_label: str | None, refused: bool, docs: list[dict]) -> str | None:
    """The label recorded for the study, after the runner's rules."""
    if refused:
        return REFUSED
    if judge_label == "Absent" and any(d.get("abstract_only") for d in docs):
        return NOT_VERIFIABLE_ABSTRACT
    return judge_label


# --------------------------------------------------------------------------
# The two APIs
# --------------------------------------------------------------------------

def call_claude(client, prefix: str, rest: str, model: str) -> tuple[str, dict, float, bool]:
    r = client.messages.create(
        model=model, max_tokens=CLAUDE_MAX_OUT,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": rest}]}])
    text = "".join(getattr(b, "text", "") for b in r.content)
    usd, counts = S.price(getattr(r, "model", model), r.usage)
    return text, {**counts, "model": r.model, "stop": r.stop_reason}, usd or 0.0, r.stop_reason == "refusal"


def call_openai(key: str, prefix: str, rest: str, issue: str) -> tuple[str, dict, float, bool]:
    resp = httpx.post("https://api.openai.com/v1/responses", timeout=600,
                      headers={"Authorization": "Bearer " + key},
                      json={"model": OPENAI_MODEL, "input": prefix + rest,
                            "max_output_tokens": OPENAI_MAX_OUT,
                            "prompt_cache_key": "m1-" + hashlib.sha256(prefix.encode()).hexdigest()[:40]})
    resp.raise_for_status()
    d = resp.json()
    refused = False
    texts = []
    for o in d.get("output", []):
        if o.get("type") != "message":
            continue
        for c in o.get("content", []):
            if c.get("type") == "refusal":
                refused = True
            elif c.get("type") in ("output_text", "text"):
                texts.append(c.get("text", ""))
    text = d.get("output_text") or "".join(texts)
    u = d.get("usage") or {}
    cached = int((u.get("input_tokens_details") or {}).get("cached_tokens") or 0)
    inp, out = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
    usd = ((inp - cached) * OPENAI_PRICE["input"] + cached * OPENAI_PRICE["cached_input"]
           + out * OPENAI_PRICE["output"]) / 1e6
    counts = {"input": inp, "cache_read": cached, "output": out,
              "reasoning": int((u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0),
              "model": d.get("model"), "stop": d.get("status"),
              "incomplete": d.get("incomplete_details")}
    S.record(script=SCRIPT, role="m1-judge-openai", issue=issue, usd=usd,
             input_tokens=inp, output_tokens=out,
             note="%s; cached_input=%d" % (d.get("model") or OPENAI_MODEL, cached))
    return text, counts, usd, refused


# --------------------------------------------------------------------------

def consistency_sample(judged: list[str], share: float, seed: int) -> list[str]:
    """The items read a second time: a seeded share of those judged, drawn
    from them in sorted order so the draw depends on the seed and the pool
    only, never on the order items were judged in."""
    pool = sorted(set(judged))
    k = max(1, round(share * len(pool))) if pool and share > 0 else 0
    return sorted(random.Random(seed).sample(pool, k)) if k else []


def judgeable(it: dict, manifest: dict, allow_incomplete: bool = False) -> bool:
    """Will the main loop call a judge on this item? The same tests, from the
    manifest alone: at least one reachable snapshot, and no cited work missing
    unless --allow-incomplete."""
    cites = it.get("citations") or [{"label": "", "url": u} for u in it["urls"]]
    missing = [c for c in cites if not c.get("url") or manifest[c["url"]]["extent"] == "unreachable"]
    reachable = [c for c in cites if c.get("url") and manifest[c["url"]]["extent"] != "unreachable"]
    return bool(reachable) and (not missing or allow_incomplete)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--cap", type=float, default=25.0)
    ap.add_argument("--only")
    ap.add_argument("--judges", default="claude,openai")
    ap.add_argument("--tag", default="")
    ap.add_argument("--ledger-issue", default="whu-reliability-prep2")
    ap.add_argument("--allow-incomplete", action="store_true")
    ap.add_argument("--author-line", default="",
                    help="bias test: a line placed after the documents and before the claim")
    ap.add_argument("--consistency-share", type=float, default=CONSISTENCY_SHARE,
                    help="share of judged items each judge reads a second time (0 for none)")
    ap.add_argument("--seed", type=int, default=CONSISTENCY_SEED,
                    help="seed for the consistency sample; logged with the sample")
    a = ap.parse_args()
    run = Path(a.run_dir)
    items = json.loads((run / "items.json").read_text())
    manifest = {r["url"]: r for r in json.loads((run / "sources" / "manifest.json").read_text())}
    if a.only:
        keep = set(a.only.split(","))
        items = [i for i in items if i["item"] in keep]
    keys = env_keys()
    import anthropic
    raw = anthropic.Anthropic(api_key=keys["ANTHROPIC_API_KEY"])
    client = S.metered(raw, script=SCRIPT, issue=a.ledger_issue, role="m1-judge-claude")
    prompt_sha = hashlib.sha256(PROMPT.read_bytes()).hexdigest()

    def count(text: str) -> int:
        return raw.messages.count_tokens(model=CLAUDE_MODEL, messages=[{"role": "user", "content": text}]).input_tokens

    tok_file = run / "sources" / "tokens.json"
    tokens = json.loads(tok_file.read_text()) if tok_file.exists() else {}
    skipped = []

    def judge_items(todo: list[dict], tag: str, judged: list[str]) -> int:
        for it in todo:
            docs, unreachable, undelivered = [], [], []
            cites = it.get("citations") or [{"label": "", "url": u} for u in it["urls"]]
            for c in cites:
                if not c.get("url"):
                    unreachable.append({"label": c.get("label"), "url": None,
                                        "why": c.get("note") or "no URL in the answer"})
            for u in [c["url"] for c in cites if c.get("url")]:
                m = manifest[u]
                if m["extent"] == "unreachable":
                    unreachable.append({"url": u, "why": m["extent_why"]})
                    continue
                text = (run / "sources" / (m["source_id"] + ".txt")).read_text(encoding="utf-8")
                if m["source_id"] not in tokens:
                    tokens[m["source_id"]] = count(text)
                    tok_file.write_text(json.dumps(tokens, indent=1))
                d = {"source_id": m["source_id"], "url": u, "extent": m["extent"],
                     "abstract_only": bool(m.get("abstract_only")), "tokens": tokens[m["source_id"]],
                     "text_sha256": m["text_sha256"], "chunked": False, "text": text}
                spans = [s for s in [it.get("span")] + list(it.get("spans") or []) if s]
                if d["tokens"] > MAX_SOURCE_TOKENS:
                    d["text"], d["chunk"] = chunk(text, it["claim"], MAX_SOURCE_TOKENS, count, spans)
                    d["chunked"] = True
                bad = delivery_problems(text, d["text"], it["claim"], spans)
                if bad:
                    undelivered.append({"url": u, "source_id": m["source_id"], "why": "; ".join(bad)})
                docs.append(d)
            if not docs:
                skipped.append((it["item"], "; ".join(x["why"] for x in unreachable)))
                continue
            # A source the judge would receive incompletely (undelivered) is never
            # judged, whatever --allow-incomplete says: that flag is about sources
            # nobody could fetch, not about text this runner failed to pass on.
            if (unreachable and not a.allow_incomplete) or undelivered:
                for judge in a.judges.split(","):
                    out = run / ("replies" + tag) / judge / (it["item"] + ".json")
                    if out.exists():
                        continue
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(json.dumps({
                        "item": it["item"], "judge": judge, "prompt_version": "v3",
                        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "label": INCOMPLETE_SOURCES, "judge_label": None, "attempts": [], "usd": 0.0,
                        "sources": [{k: v for k, v in d.items() if k != "text"} for d in docs],
                        "unreachable_sources": unreachable, "undelivered_sources": undelivered,
                        "human_review": True,
                        "form_problems": [], "parsed": None, "reference": it["reference"]},
                        indent=1, ensure_ascii=False), encoding="utf-8")
                    print("%-5s %-7s %-24s ref %-11s not judged: %s" % (
                        it["item"], judge, INCOMPLETE_SOURCES, it["reference"],
                        "; ".join("%s (%s)" % (x.get("label") or x.get("url"), x["why"])
                                  for x in unreachable + undelivered)[:120]))
                continue
            judged.append(it["item"])
            prefix, rest = build(it, docs)
            if a.author_line:
                # After the documents, before the claim: the cached block is unchanged.
                rest = "\n\n" + a.author_line.strip() + rest
            n_in = count(prefix + rest)
            for judge in a.judges.split(","):
                out = run / ("replies" + tag) / judge / (it["item"] + ".json")
                if out.exists():
                    continue
                attempts = []
                for attempt in (1, 2):              # the second only after a refusal
                    if judge == "claude":
                        p = S.PRICES[CLAUDE_MODEL]
                        worst = (n_in * p["cache_write"] + CLAUDE_MAX_OUT * p["output"]) / 1e6
                    else:
                        worst = (n_in * OPENAI_PRICE["input"] + OPENAI_MAX_OUT * OPENAI_PRICE["output"]) / 1e6
                    so_far = spent(a.ledger_issue)
                    if so_far + worst > a.cap:
                        print("STOP: %s on %s could cost up to $%.3f; %s has spent $%.3f of $%.2f"
                              % (judge, it["item"], worst, a.ledger_issue, so_far, a.cap))
                        return 3
                    t0 = time.time()
                    for net in range(3):
                        try:
                            if judge == "claude":
                                text, usage, usd, refused = call_claude(client, prefix, rest, CLAUDE_MODEL)
                            else:
                                text, usage, usd, refused = call_openai(keys["OPENAI_API_KEY"], prefix, rest, a.ledger_issue)
                            break
                        except Exception as e:
                            if net == 2:
                                raise
                            print("  network retry %s %s: %s" % (judge, it["item"], str(e)[:160]))
                            time.sleep(10)
                    attempts.append({"attempt": attempt, "seconds": round(time.time() - t0, 1),
                                     "usage": usage, "usd": round(usd, 6), "refused": refused, "raw": text})
                    if not refused:
                        break
                last = attempts[-1]
                refused = last["refused"]
                obj, problems = (None, []) if refused else parse(last["raw"])
                span = (obj or {}).get("span") or ""
                span_ok = bool(span) and any(norm(span) in norm(d["text"]) for d in docs)
                label = final_label((obj or {}).get("label"), refused, docs)
                rec = {"item": it["item"], "judge": judge, "model": last["usage"].get("model"),
                       "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "prompt_sha256": prompt_sha, "prompt_version": "v3", "author_line": a.author_line or None,
                       "allow_incomplete": bool(a.allow_incomplete and unreachable),
                       "sources": [{k: v for k, v in d.items() if k != "text"} for d in docs],
                       "unreachable_sources": unreachable,
                       "chunked": any(d["chunked"] for d in docs),
                       "input_tokens_counted": n_in, "attempts": attempts,
                       "usd": round(sum(x["usd"] for x in attempts), 6),
                       "judge_label": (obj or {}).get("label"), "label": label,
                       "parsed": obj, "form_problems": problems,
                       "span_verbatim_in_documents": span_ok,
                       "human_review": label == REFUSED, "reference": it["reference"]}
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
                u = last["usage"]
                print("%-5s %-7s %-24s ref %-11s $%.4f  in %6d cached %6d write %6d out %5d  %s%s%s" % (
                    it["item"], judge, label, it["reference"], rec["usd"], u.get("input", 0),
                    u.get("cache_read", 0), u.get("cache_write", 0), u.get("output", 0),
                    "span ok" if span_ok else ("-" if refused else "SPAN NOT VERBATIM"),
                    ("  FORM: " + "; ".join(problems)) if problems else "",
                    ("  REFUSED x%d" % len(attempts)) if refused else ""))
        return 0

    pool = sorted(it["item"] for it in items if judgeable(it, manifest, a.allow_incomplete))
    sample = consistency_sample(pool, a.consistency_share, a.seed)
    if sample:
        rec = {"seed": a.seed, "share": a.consistency_share, "pool": pool, "items": sample,
               "judges": a.judges.split(","), "repeat_dir": "replies" + a.tag + REPEAT_SUFFIX}
        sf = run / ("replies" + a.tag) / "consistency_sample.json"
        if sf.exists():
            old = json.loads(sf.read_text())
            if {k: old.get(k) for k in ("seed", "share", "pool", "items")} != \
                    {k: rec[k] for k in ("seed", "share", "pool", "items")}:
                print("STOP: %s records a different consistency sample (seed %s, %d items); "
                      "this invocation would draw seed %s, %d items" % (sf, old.get("seed"), len(old.get("items") or []),
                                                                       a.seed, len(sample)))
                return 4
        else:
            sf.parent.mkdir(parents=True, exist_ok=True)
            sf.write_text(json.dumps({**rec, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                                     indent=1))
        print("consistency sample (seed %d, %d of %d): %s" % (a.seed, len(sample), len(pool), ", ".join(sample)))
    judged: list[str] = []
    for it in items:
        rc = judge_items([it], a.tag, judged)
        if not rc and it["item"] in sample:
            rc = judge_items([it], a.tag + REPEAT_SUFFIX, [])
        if rc:
            return rc
    if sorted(judged) != pool:
        print("STOP: the items judged (%d) are not the pool the sample was drawn from (%d)" % (len(judged), len(pool)))
        return 5
    for s in skipped:
        print("skipped (no reachable source): %s  %s" % s)
    print("%s spent: $%.4f" % (a.ledger_issue, spent(a.ledger_issue)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
