#!/usr/bin/env python3
"""Check an AI answer, v4: lean WHU's passage retrieval (plan doc "WHU next phase", Part B item 1).

v1, v2 and v3 are imported unchanged; everything v3 does (copies, walls, licences, abstracts, ranked
claims, passages shown, reasons) v4 does the same way. One step differs: what the judge reads. v3
sends judge_m1 each cited source whole (judge_m1.chunk past MAX_SOURCE_TOKENS); v4 sends the
passages of that source most relevant to the claim:

  * the TOP_K passages BM25 finds for the claim (backend/scripts/whatholdsup/passage_index.py,
    the module lean WHU's audit uses), in document order, with "[… text omitted …]" between;
  * TOPPED UP so judge_m1.delivery_problems still holds: for every key term of the claim
    (judge_m1.key_terms) that the source contains but those passages do not, the best passage
    containing it is added;
  * when retrieval finds nothing above its threshold, the claim is COULDN'T CHECK ("no relevant
    passage"), logged with the source -- never judged on the whole source. A claim has no bound
    passage here, so there is nothing else to fall back to.

The judge's prompt, model, first-read rule and labels are judge_m1's, through v1's judge; the
passage shown to a reader (§10.1) is located in the source's full held text, as v3 does.
Not wired into the preview: routers/whu_check.py stays on v2.
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pipeline as V1
import pipeline_v3 as V3
from pipeline import BACKED, COULDNT, LABELS, NO_SOURCE, NOT_BACKED, Stop  # noqa: F401

J = V1.J
_WHU = Path(__file__).resolve().parents[3] / "backend" / "scripts" / "whatholdsup"
if str(_WHU) not in sys.path:
    sys.path.insert(0, str(_WHU))
import passage_index as PI  # noqa: E402

VERSION = 4
TOP_K = 6
R_NO_PASSAGE = "no relevant passage"


def passages_for(text: str, claim: str, k: int = TOP_K) -> tuple[str, dict]:
    """(what the judge reads, the retrieval record) for one claim against one held text."""
    ix = PI.index_of(text)
    got = ix.top(claim, k)
    ranges = [(p.start, p.end) for p, _s in got]
    rec = {"retrieved": [[p.start, p.end, round(s, 3)] for p, s in got], "below_threshold": not got,
           "topped_up": []}
    if not got:
        return "", rec
    nums, words = J.key_terms(claim)
    have = PI.deliver(text, ranges)
    low_text = text.lower()
    for term in sorted(nums) + sorted(words):
        hay_full, hay = (text, have) if term in nums else (low_text, have.lower())
        if term not in hay_full or term in hay:
            continue
        cands = [p for p in ix.passages if term in (text[p.start:p.end] if term in nums
                                                   else text[p.start:p.end].lower())]
        if not cands:
            continue
        best = max(cands, key=lambda p: ix.score(p.idx, PI.tokens(claim))[0])
        ranges.append((best.start, best.end))
        rec["topped_up"].append({"term": term, "at": [best.start, best.end]})
        have = PI.deliver(text, ranges)
    return have, rec


def _docs_v4(c: dict, man: dict, work: Path, count) -> tuple[list[dict], list[dict], list[str], list[dict]]:
    """(docs the judge reads, the same docs with full text, reasons it cannot be judged, retrieval log)."""
    docs, full, why, log = [], [], [], []
    for ct in c["citations"]:
        u = ct.get("url")
        if not u:
            why.append("%s: %s" % (ct["label"], ct.get("note") or "no address in the answer"))
            continue
        m = man[u]
        if m["extent"] == "unreachable":
            why.append("%s %s: %s" % (ct["label"], u, m.get("extent_why")))
            continue
        text = (work / "sources" / (m["source_id"] + ".txt")).read_text(encoding="utf-8")
        sent, rec = passages_for(text, c["claim"])
        log.append({"idx": c.get("idx"), "url": u, "source_id": m["source_id"], **rec})
        if not sent:
            why.append("%s %s: %s (retrieval found nothing above its threshold; the whole source is "
                       "never sent)" % (ct["label"], u, R_NO_PASSAGE))
            continue
        base = {"source_id": m["source_id"], "url": u, "extent": m["extent"],
                "abstract_only": bool(m.get("abstract_only")), "chunked": False}
        d = dict(base, text=sent, tokens=count(sent), passages=True)
        bad = J.delivery_problems(text, sent, c["claim"], [])
        if bad:
            why.append("%s %s: %s" % (ct["label"], u, "; ".join(bad)))
        docs.append(d)
        full.append(dict(base, text=text))
    return docs, full, why, log


def plan_v4(claims: list[dict], man: dict, work: Path, count, workers: int = 8) -> tuple[list[dict], list[dict]]:
    """v1's plan with v4's documents: (planned rows, retrieval log)."""
    def one(c):
        if not c["citations"]:
            return {**c, "label": NO_SOURCE, "reason": "no citation", "study_label": "UNCITED"}, []
        docs, full, why, log = _docs_v4(c, man, work, count)
        if why:
            return {**c, "label": COULDNT, "reason": "; ".join(why), "study_label": None,
                    "sources": [ct.get("url") for ct in c["citations"]]}, log
        prefix, rest = J.build(c, docs)
        n_in = count(prefix + rest)
        return {**c, "label": None, "docs": docs, "full_docs": full, "prefix": prefix, "rest": rest,
                "n_in": n_in, "worst": V1.worst_cost(n_in)}, log
    with ThreadPoolExecutor(max_workers=workers) as ex:
        got = list(ex.map(one, claims))
    return [p for p, _l in got], [r for _p, l in got for r in l]


def judge_v4(planned: list[dict], man: dict, work: Path, client, before_call=None, workers: int = 8) -> list[dict]:
    """v3's judge (v1's, one claim per thread); the passage shown is found in the full held text."""
    full_of = {id(p): p.get("full_docs") or p.get("docs") or [] for p in planned}
    rows = [{k: v for k, v in p.items() if k != "full_docs"} for p in planned]
    results = V3.judge_v3(rows, man, work, client, before_call, workers)
    out = []
    for p, r in zip(planned, results):
        if r.get("label") == COULDNT and r.get("verdict_withheld") and full_of[id(p)]:
            # v3 looked for the span in what was judged; the passages are part of the full text
            r = V3.finish({**r, "label": r["verdict_withheld"]}, full_of[id(p)], man)
        elif r.get("passage") is None and r.get("label") in (BACKED, NOT_BACKED):
            r = V3.finish(r, full_of[id(p)], man)
        if r.get("label") == COULDNT and R_NO_PASSAGE in (r.get("reason") or ""):
            r["reason_kind"] = R_NO_PASSAGE                     # v4's one new reason (§10.9's list + this)
        out.append(r)
    return out


def prepare(text: str, work: Path, fmt: str | None = None, count=None, system: str = "answer",
            net: dict | None = None, selected: list[int] | None = None, max_claims: int = V1.MAX_CLAIMS) -> dict:
    """v3's preparation with v4's plan: adapt, sentences, ranked claims, copies, passages (no model call)."""
    n = {**V3.NET, **(net or {})}
    md, cited, fmt = V3.adapt_answer(text, fmt)
    rows, refs = V1.sentences(md, cited, work, system)
    claims, beyond, found = V3.claims_v3(rows, refs, selected, max_claims)
    man = V3.snapshots_v3(claims, work, V3.V2.titles_from(text), n)
    planned, log = plan_v4(claims, man, work, count)
    return {"format": fmt, "rows": rows, "refs": refs, "claims": claims, "beyond_limit": beyond, "found": found,
            "manifest": man, "planned": planned, "retrieval": log, "version": VERSION,
            "below_threshold": sum(1 for r in log if r["below_threshold"]),
            "worst_usd": round(sum(p.get("worst") or 0 for p in planned), 4),
            "calls": sum(1 for p in planned if p["label"] is None)}


def check(text: str, work: Path, client, count, fmt: str | None = None, system: str = "answer",
          net: dict | None = None, selected: list[int] | None = None, before_call=None) -> dict:
    t0 = time.time()
    prep = prepare(text, work, fmt, count, system, net, selected)
    results = judge_v4(prep["planned"], prep["manifest"], work, client, before_call)
    return {**{k: v for k, v in prep.items() if k != "planned"}, "results": results,
            "summary": V3.summary(results, prep["found"]), "seconds": round(time.time() - t0, 1)}


public = V3.public
