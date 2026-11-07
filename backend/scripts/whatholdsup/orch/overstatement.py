"""The cross-company overstatement check in WHU's own sentence gate (docs/whu-orchestrator.md §3).

For each page sentence bound to a passage, one call to gemini-4-argon with ONLY the sentence and
its passage. "yes" makes the sentence leave the page under the lean fail-safe (recorded, never
dismissed); on a required line the fail-safe's STOP keeps the line and the page is Not Ready.
A reply that is not valid JSON, or a refusal, is asked once more; a second bad reply is treated
as "yes". A transport error stops the step (no reply is not a verdict).

Records: rulings/overstatement.jsonl, one row per (sentence, passage) checked. A pair already
checked with the same inputs is not sent again.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

LOG = "rulings/overstatement.jsonl"
PATH = "overstatement"                 # the fail-safe's path name for this check
PASSAGE_MAX = 2400
PROMPT = (
    "You compare one sentence with the passage it cites. Answer whether the SENTENCE overstates the PASSAGE: "
    "states more than the passage says, generalises beyond what the passage covers, or states something more "
    "certainly than the passage does. Reply with JSON only:\n"
    '{"overstates": "yes" or "no", "how": "more" | "generalises" | "more_certain" | "none", '
    '"why": "<at most 30 words>"}\n\n'
    "PASSAGE:\n%s\n\nSENTENCE:\n%s\n")
PROMPT_SHA = hashlib.sha256(PROMPT.encode("utf-8")).hexdigest()
HOWS = ("more", "generalises", "more_certain", "none")
TREATED_AS_YES = "no valid reply after a second request; treated as yes (a finding code cannot verify)"


def _sha(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def norm(s: str) -> str:
    return " ".join((s or "").split())


_SENT_END = re.compile(r"[.!?][\"”’)\]]*\s")


def passage_around(text: str, start: int, end: int, limit: int = PASSAGE_MAX) -> tuple[int, int]:
    """The bound span [start, end) widened to whole sentences, at most LIMIT characters (the span itself is never
    cut: a span longer than LIMIT is sent whole)."""
    if end - start >= limit:
        return start, end
    lo = start
    for m in _SENT_END.finditer(text, max(0, start - limit), start):
        lo = m.end()
    if lo == start and start > 0:            # no sentence end before it within reach
        lo = max(0, start - (limit - (end - start)) // 2)
    m = _SENT_END.search(text, max(start, end - 1))      # a span that ends its sentence is not extended
    hi = m.end() if m else len(text)
    if hi - lo > limit:
        hi = min(hi, lo + limit) if lo + limit >= end else end
    return lo, max(hi, end)


def pairs(rows: dict, held: dict, locate) -> list[dict]:
    """Every (sentence, passage) to check: on-page rows with a span in a held text, plus also_rests_on spans."""
    out = []
    for sha, r in sorted(rows.items()):
        if not r.get("on_page") or r.get("protected"):
            continue
        spans = []
        if r.get("span") and r.get("source_id"):
            spans.append((r["source_id"], r["span"], r.get("offsets")))
        for extra in r.get("also_rests_on") or []:
            if isinstance(extra, dict) and extra.get("span") and extra.get("source_id"):
                spans.append((extra["source_id"], extra["span"], extra.get("offsets")))
        for sid, span, offs in spans:
            text = held.get(sid) or ""
            at = tuple(offs) if offs and text[offs[0]:offs[1]] == span else locate(span, text)
            if not at:
                out.append({"sentence": r.get("sentence") or "", "sentence_sha": sha, "source_id": sid,
                            "span": span, "passage": None, "why_none": "the bound span is not in the held text"})
                continue
            lo, hi = passage_around(text, at[0], at[1])
            out.append({"sentence": r.get("sentence") or "", "sentence_sha": sha, "source_id": sid, "span": span,
                        "offsets": [lo, hi], "passage": text[lo:hi]})
    return out


def parse(reply: str) -> dict | None:
    """{"overstates": "yes"|"no", "how", "why"} or None when the reply is not the schema."""
    t = (reply or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    v = str(d.get("overstates", "")).strip().lower()
    if v not in ("yes", "no"):
        return None
    how = str(d.get("how", "")).strip()
    return {"overstates": v, "how": how if how in HOWS else "unstated", "why": str(d.get("why", ""))[:400]}


def key_of(p: dict) -> str:
    return _sha("\n".join([PROMPT_SHA, norm(p["sentence"]), p["source_id"], _sha(p["passage"] or "")]))


def load(case: Path) -> list[dict]:
    f = case / LOG
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def _append(case: Path, row: dict) -> None:
    f = case / LOG
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def check_one(gw, p: dict) -> dict:
    """Ask, and once more on a bad reply. Returns the verdict row (not yet written)."""
    text = PROMPT % (p["passage"], norm(p["sentence"]))
    replies = []
    verdict = None
    for _attempt in range(2):
        got = gw.call(text, "overstatement")
        replies.append({"text": got["text"], "model": got["model"], "usd": got["usd"],
                        "refused": got["refused"], "finish": got["finish"]})
        verdict = None if got["refused"] else parse(got["text"])
        if verdict:
            break
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "key": key_of(p),
           "sentence": norm(p["sentence"]), "sentence_sha": p["sentence_sha"], "source_id": p["source_id"],
           "offsets": p.get("offsets"), "passage_sha": _sha(p["passage"]), "prompt_sha": PROMPT_SHA,
           "replies": replies, "usd": round(sum(r["usd"] for r in replies), 6)}
    if verdict:
        row.update(verdict=verdict["overstates"], how=verdict["how"], why=verdict["why"])
    else:
        row.update(verdict="yes", how="unstated", why=TREATED_AS_YES)
    return row


def run(case: Path, rows: dict, held: dict, locate, gw, removal) -> dict:
    """Check every pair not already checked. REMOVAL(it) records the fail-safe (lean_failsafe.record).
    Returns counts."""
    have = {r["key"]: r for r in load(case)}
    counts = {"pairs": 0, "checked": 0, "carried": 0, "yes": 0, "no": 0, "no_passage": 0, "usd": 0.0}
    for p in pairs(rows, held, locate):
        counts["pairs"] += 1
        if p.get("passage") is None:
            counts["no_passage"] += 1
            continue
        k = key_of(p)
        row = have.get(k)
        if row:
            counts["carried"] += 1
        else:
            row = check_one(gw, p)
            _append(case, row)
            have[k] = row
            counts["checked"] += 1
            counts["usd"] += row["usd"]
        counts[row["verdict"]] += 1
        if row["verdict"] == "yes":
            removal({"kind": "overstatement", "sentence": row["sentence"], "ref": {"finding_key": k},
                     "protected": None})
    counts["usd"] = round(counts["usd"], 6)
    return counts


def preflight_row(case: Path, page_sentences: list[str], rows: dict, held: dict, locate) -> tuple[str, str, str]:
    """("overstatement check complete", ok|BLOCKED, detail)."""
    have = {r["key"]: r for r in load(case)}
    on_page = {norm(s) for s in page_sentences}
    missing, still = [], []
    for p in pairs(rows, held, locate):
        if norm(p["sentence"]) not in on_page:
            continue
        if p.get("passage") is None:
            missing.append(p["sentence"])
            continue
        r = have.get(key_of(p))
        if not r:
            missing.append(p["sentence"])
        elif r["verdict"] == "yes":
            still.append(p["sentence"])
    if missing or still:
        return ("overstatement check complete", "BLOCKED",
                "%d bound sentence(s) on the page have no verdict for their current text and passage; %d judged "
                "to overstate their passage are still on the page%s"
                % (len(missing), len(still), (": %r" % (still or missing)[0][:100])))
    return ("overstatement check complete", "ok", "every bound sentence on the page has a 'no' verdict (%s)"
            % "gemini-4-argon")
