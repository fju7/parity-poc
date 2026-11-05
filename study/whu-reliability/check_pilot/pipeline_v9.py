#!/usr/bin/env python3
"""Check an AI answer, v9: v8, then an overstatement second read on every BACKED verdict, and a document the user
supplies for a source v8 could not reach (docs/whu-check-an-answer-pilot.md §17).
v8 is imported unchanged and decides every claim exactly as before. v9 adds:
  * second_read: one short call to the OpenAI judge's model per BACKED verdict, given only the claim and the passage
    v8 showed. A yes shows "BACKED, but may overstate" with the model's one-line reason; v8's label, passage and
    reason are kept. A read that fails twice shows "BACKED (overstatement check not done)".
  * score_label: §17.3's table, decided before any v9 call ("may overstate" is NOT BACKED for agreement; a failed
    read is COULDN'T CHECK everywhere).
  * supply_source / recheck_with_supplied: verify.supplied's identity check, unchanged, with store=False (nothing is
    written to Signal's corpus); an admitted file is served to v8's own fetch for its one URL, and only the claims
    citing it are re-checked, marked "checked against a document you supplied". The user supplies the document,
    never the conclusion.
Not wired into the preview: routers/whu_check.py stays on v2.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote

import pipeline_v8 as P8
from pipeline import BACKED, COULDNT, NO_SOURCE, NOT_BACKED, Stop  # noqa: F401

J, S = P8.J, P8.S
VERSION = 9
BACKEND = Path(__file__).resolve().parents[3] / "backend"

MAY_OVERSTATE = "BACKED, but may overstate"
NOT_DONE = "BACKED (overstatement check not done)"
SUPPLIED_NOTE = "checked against a document you supplied"
HOW = ("overstates", "generalises", "more_certain", "none")
REASON_WORDS = 25
SECOND_READ_MODEL = J.OPENAI_MODEL           # §17.2: the OpenAI judge's model (a point for the ruling, §17.4.1)
SECOND_READ_MAX_OUT = 2000                   # reasoning counts as output
SECOND_READ_ROLE = "check-v9-second-read"
SECOND_READ_TRIES = 2                        # one retry (§17.2)

SECOND_READ_PROMPT = """You compare one claim with one passage. The passage is all you are given; judge only it.

Does the claim say more than the passage does? Answer yes if the claim does any of these:
- overstates: gives a larger effect, a stronger finding or a firmer conclusion than the passage reports;
- generalises: extends the finding to people, places, times or conditions the passage does not cover;
- more_certain: states as established what the passage hedges, qualifies or reports as uncertain or low-certainty.
Answer no if the passage says at least what the claim says. Do not judge whether the claim is true, and do not use
anything you know beyond the passage.

Reply with one JSON object and nothing else:
{"may_overstate": true or false, "how": "overstates" | "generalises" | "more_certain" | "none", "reason": "<one line, at most 25 words>"}
"how" is "none" exactly when "may_overstate" is false.
"""
PROMPT_SHA256 = hashlib.sha256(SECOND_READ_PROMPT.encode()).hexdigest()


def second_read_input(claim: str, passage: str) -> str:
    """The text after the fixed prompt: the claim and the passage, nothing else (§17.2)."""
    return "%s\nCLAIM:\n%s\n\nPASSAGE:\n%s\n" % (SECOND_READ_PROMPT, claim.strip(), passage.strip())


def parse_reply(text: str) -> tuple[dict | None, str | None]:
    """(reply, None) if the text is §17.2's JSON form exactly; else (None, why)."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None, "no JSON object"
    try:
        obj = json.loads(m.group(0))
    except ValueError:
        return None, "not valid JSON"
    if not isinstance(obj, dict) or set(obj) != {"may_overstate", "how", "reason"}:
        return None, "keys are not may_overstate, how, reason"
    mo, how, reason = obj["may_overstate"], obj["how"], obj["reason"]
    if not isinstance(mo, bool) or how not in HOW or not isinstance(reason, str) or not reason.strip():
        return None, "a field has the wrong type or value"
    if (how == "none") == mo:
        return None, "how is 'none' but may_overstate is true, or the reverse"
    if len(reason.split()) > REASON_WORDS or "\n" in reason.strip():
        return None, "reason is not one line of at most %d words" % REASON_WORDS
    return {"may_overstate": mo, "how": how, "reason": reason.strip()}, None


def openai_call(key: str, issue: str, script: str = "study/whu-reliability/check_pilot/pipeline_v9.py"):
    """The default call: judge_m1.post_openai (rate-limit waits, OutOfCredit), metered on its own role and issue.
    Returns call(text) -> (reply text, usage, usd, refused or incomplete)."""
    def call(text: str):
        d = J.post_openai({"model": SECOND_READ_MODEL, "input": text, "max_output_tokens": SECOND_READ_MAX_OUT},
                          key).json()
        out_text, refused = [], False
        for o in d.get("output", []):
            for c in o.get("content", []) if o.get("type") == "message" else []:
                if c.get("type") == "refusal":
                    refused = True
                elif c.get("type") in ("output_text", "text"):
                    out_text.append(c.get("text", ""))
        u = d.get("usage") or {}
        cached = int((u.get("input_tokens_details") or {}).get("cached_tokens") or 0)
        inp, out = int(u.get("input_tokens") or 0), int(u.get("output_tokens") or 0)
        pr = J.OPENAI_PRICE
        usd = ((inp - cached) * pr["input"] + cached * pr["cached_input"] + out * pr["output"]) / 1e6
        S.record(script=script, role=SECOND_READ_ROLE, issue=issue, usd=usd, input_tokens=inp, output_tokens=out,
                 note="%s; cached_input=%d" % (d.get("model") or SECOND_READ_MODEL, cached))
        return (d.get("output_text") or "".join(out_text), {"input": inp, "cache_read": cached, "output": out,
                                                             "status": d.get("status")},
                usd, refused or d.get("status") == "incomplete")
    return call


def second_read(claim: str, passage: str, call) -> dict:
    """One BACKED verdict's second read: up to SECOND_READ_TRIES calls; a form failure, refusal, incomplete reply
    or error on the last try leaves it not done."""
    attempts = []
    for n in range(1, SECOND_READ_TRIES + 1):
        try:
            text, usage, usd, bad = call(second_read_input(claim, passage))
        except J.OutOfCredit:
            raise
        except Exception as e:                                      # an API error is a failed attempt, not a verdict
            attempts.append({"attempt": n, "usd": 0.0, "error": "%s: %s" % (type(e).__name__, e)})
            continue
        reply, why = (None, "refused or incomplete") if bad else parse_reply(text)
        attempts.append({"attempt": n, "usd": round(usd, 6), "usage": usage, "raw": text, "form_problem": why})
        if reply:
            return {"done": True, **reply, "attempts": attempts, "prompt_sha256": PROMPT_SHA256,
                    "model": SECOND_READ_MODEL, "usd": round(sum(a["usd"] for a in attempts), 6)}
    return {"done": False, "why": attempts[-1].get("form_problem") or attempts[-1].get("error"), "attempts": attempts,
            "prompt_sha256": PROMPT_SHA256, "model": SECOND_READ_MODEL,
            "usd": round(sum(a["usd"] for a in attempts), 6)}


def shown(row: dict) -> str:
    """What the user sees for a row."""
    sr = row.get("second_read")
    if row.get("label") != BACKED or sr is None:
        return row.get("label")
    if not sr["done"]:
        return NOT_DONE
    return MAY_OVERSTATE if sr["may_overstate"] else BACKED


def score_label(row: dict) -> str:
    """§17.3, decided before any v9 call: the label a row counts as for agreement and coverage."""
    s = shown(row)
    if s == MAY_OVERSTATE:
        return NOT_BACKED
    if s == NOT_DONE:
        return COULDNT
    return s


def apply_second_read(results: list[dict], call, only=None) -> list[dict]:
    """Every BACKED row (or those whose idx is in `only`) gets its second read; v8's fields are left as they were."""
    for r in results:
        if r.get("label") != BACKED or (only is not None and r["idx"] not in only):
            continue
        r["second_read"] = second_read(r["claim"], (r.get("passage") or {}).get("quote") or "", call)
        r["shown"] = shown(r)
        if r["shown"] == MAY_OVERSTATE:
            r["shown_reason"] = r["second_read"]["reason"]
    return results


def summary(results: list[dict]) -> dict:
    out: dict[str, int] = {}
    for r in results:
        out[shown(r)] = out.get(shown(r), 0) + 1
    return out


def check(text: str, work: Path, client, call, **kw) -> dict:
    """v8's check, unchanged, then the second read on every BACKED verdict (§17.2)."""
    t0 = time.time()
    res = P8.check(text, work, client, **kw)
    apply_second_read(res["results"], call)
    res.update(version=VERSION, v8_version=res.get("version"), summary_v9=summary(res["results"]),
               second_read_prompt_sha256=PROMPT_SHA256, seconds_second_read=round(time.time() - t0 - res["seconds"], 1))
    return res


# -- the user-supplied source (§17.6) --------------------------------------------------------------------------------

_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>]+)", re.I)


def _clean_doi(d: str) -> str:
    d = unquote(d).rstrip(".,;)]")
    return re.sub(r"(/(full|abstract|pdf|epdf|html))+$", "", d, flags=re.I)


def identifier_for(url: str, reference: str = "") -> tuple[str | None, str]:
    """(identifier, where it came from): the cited URL first (DOI, PubMed id, PMCID, NCT), then the answer's own
    reference entry for that citation (DOI or PMID), else (None, 'none')."""
    for where, s in (("url", url or ""), ("reference", reference or "")):
        m = _DOI.search(unquote(s))
        if m:
            return _clean_doi(m.group(1)), where
        m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", s) or (re.search(r"\bPMID:?\s*(\d{5,9})\b", s)
                                                                  if where == "reference" else None)
        if m:
            return "PMID:" + m.group(1), where
        m = re.search(r"\b(PMC\d{4,9})\b", s)
        if m:
            return m.group(1), where
        m = re.search(r"\b(NCT\d{8})\b", s)
        if m:
            return m.group(1), where
    return None, "none"


def _supplied_module():
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    from verify import supplied
    return supplied


def supply_source(path: str | Path, url: str, reference: str, supplied_by: str, run_dir: Path, supply=None) -> dict:
    """The user's file for an unreachable source, through verify.supplied.supply with store=False. The record (never
    the text) goes in run_dir/supplied/<sha256>.json; Signal's corpus is never written."""
    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    ident, where = identifier_for(url, reference)
    rec = {"url": url, "sha256": sha, "bytes": len(data), "supplied_by": supplied_by, "identifier": ident,
           "identifier_from": where, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if ident is None:
        rec.update(status="REFUSED_NO_IDENTIFIER", admitted=False,
                   reason="no registry identifier: this document cannot be checked against a registry, so it is "
                          "not used")
    else:
        sup = (supply or _supplied_module().supply)(path, url, supplied_by, ident, store=False)
        rec.update(status=sup.status, admitted=bool(sup.admitted), reason=sup.reason,
                   registry=(sup.record or {}).get("registry"), registry_heading=(sup.record or {}).get(
                       "registry_heading"), heading=(sup.record or {}).get("heading"),
                   content_type=getattr(sup.document, "content_type", None) if sup.document else None)
    out = run_dir / "supplied"
    out.mkdir(parents=True, exist_ok=True)
    (out / (sha + ".json")).write_text(json.dumps(rec, indent=1))
    rec["path"] = str(path)
    return rec


def supplied_net(net: dict | None, admitted: dict[str, dict]) -> dict:
    """v8's net with get() serving each admitted file, as fetched bytes, for its own URL only."""
    base = dict(net or P8.V4.V3.NET)
    get0 = base["get"]

    def get(url, *a, **k):
        rec = admitted.get(url)
        if rec is None:
            return get0(url, *a, **k)
        body = Path(rec["path"]).read_bytes()
        ctype = rec.get("content_type") or ("application/pdf" if body[:5] == b"%PDF-" else "text/html")
        return {"status": 200, "final_url": url, "content_type": ctype, "body": body}

    base["get"] = get
    return base


def recheck_with_supplied(text: str, work: Path, client, call, prev: dict, records: list[dict], **kw) -> dict:
    """Re-check only the claims citing an admitted file's URL, through v8 with the file served for that URL, then
    the second read; their rows replace the old ones and are marked SUPPLIED_NOTE. Every other row is kept."""
    admitted = {r["url"]: r for r in records if r.get("admitted")}
    idxs = sorted({r["idx"] for r in prev["results"] if any(c.get("url") in admitted for c in r.get("citations")
                                                               or [])})
    if not idxs:
        return {**prev, "supplied": records}
    sub = work / "supplied_recheck"
    sub.mkdir(parents=True, exist_ok=True)
    net = kw.get("net")
    kw = {k: v for k, v in kw.items() if k not in ("net", "selected")}
    again = P8.check(text, sub, client, net=supplied_net(net, admitted), selected=idxs, **kw)
    apply_second_read(again["results"], call)
    new = {r["idx"]: r for r in again["results"]}
    rows = []
    for r in prev["results"]:
        n = new.get(r["idx"])
        if n is None:
            rows.append(r)
            continue
        used = [c["url"] for c in n.get("citations") or [] if c.get("url") in admitted
                and (again["manifest"].get(c["url"]) or {}).get("extent") != "unreachable"]
        if used:
            n["supplied"] = [{"url": u, "sha256": admitted[u]["sha256"], "identifier": admitted[u]["identifier"],
                              "supplied_by": admitted[u]["supplied_by"]} for u in used]
            n["note"] = SUPPLIED_NOTE
        rows.append(n)
    return {**prev, "results": rows, "supplied": records, "summary_v9": summary(rows),
            "recheck": {"claims": idxs, "seconds": again["seconds"]}}
