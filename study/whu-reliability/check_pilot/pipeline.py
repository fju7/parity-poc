#!/usr/bin/env python3
"""Check an AI answer: the reliability study's M1 pipeline on one pasted answer.

Design: docs/whu-check-an-answer-pilot.md (fixed before this code). Every step is
the study's own code, imported by path; nothing here restates a prompt or a rule:

  adapt      blinding/adapt.py (the capture formats the study handled)
  sentences  blinding/blind.py from_markdown / blind / sentence_rows
  claims     blinding/identifiability.claim_like
  licence    backend/scripts/whatholdsup/find_access.py (Europe PMC, Unpaywall)
  snapshot   scripts/retrieve_sources.retrieve, routes (a) to (c)
  judge      scripts/judge_m1.py: M1 v3 prompt (sha256 checked), build, chunk,
             delivery_problems, call_claude, parse, final_label; Claude only, first read only

Per claim: BACKED / NOT BACKED / NO SOURCE / COULDN'T CHECK, with the reason.
Network and model access are passed in (licence_fn, retrieve_fn, client, count), so the
offline tests run on recorded sources and a recorded reply.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
ROOT = STUDY.parents[1]
for p in (STUDY / "blinding", STUDY / "scripts", ROOT / "backend" / "scripts" / "whatholdsup"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def _load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


import adapt  # noqa: E402
import blind  # noqa: E402

IDENT = _load("identifiability_check", STUDY / "blinding" / "identifiability.py")
J = _load("judge_m1_check", STUDY / "scripts" / "judge_m1.py")
S = J.S  # spend_ledger, as judge_m1 loaded it

BACKED, NOT_BACKED, NO_SOURCE, COULDNT = "BACKED", "NOT BACKED", "NO SOURCE", "COULDN'T CHECK"
LABELS = (BACKED, NOT_BACKED, NO_SOURCE, COULDNT)
# The study's own sets (analyse.py M1_PASS / M1_FAIL; measures.py cited_not_supported).
STUDY_PASS = {"Supported"}
STUDY_CITED_FAIL = {"Overstates", "Understates", "Absent", "Wrong source", "Contradicted"}
MAX_CLAIMS = 40
MARK = re.compile(r"\[(\d+)\]")
FORMATS = ("gemini_html", "chatgpt_lenticular", "chatgpt_bracketed", "perplexity_sources",
           "gemini_works_cited", "claude_sources", "report_section")


class Stop(RuntimeError):
    """A cap or a precondition stops the run before a call."""


def study_label_to_check(label: str | None) -> str:
    """The study's M1 label (or UNCITED) as one of the four check labels."""
    if label == "UNCITED":
        return NO_SOURCE
    if label in STUDY_PASS:
        return BACKED
    if label in STUDY_CITED_FAIL:
        return NOT_BACKED
    return COULDNT


# --------------------------------------------------------------------------
# 1-3. Adapt, sentences, claims
# --------------------------------------------------------------------------

def detect_format(text: str) -> str:
    head = text.lstrip()[:200].lower()
    if head.startswith("<!doctype html") or head.startswith("<html"):
        return "gemini_html"
    if adapt.LENTICULAR.search(text):
        return "chatgpt_lenticular"
    if adapt.BRACKETED.search(text):
        return "chatgpt_bracketed"
    if adapt.PPLX_MARK.search(text) and re.search(r"(?m)^#{1,6}\s*References\s*$", text):
        return "perplexity_sources"
    if re.search(r"(?m)^#{1,6}\s*\**Works cited\**\s*$", text):
        return "gemini_works_cited"
    if re.search(r"(?m)^#{1,6}\s*Sources\s*$", text):
        return "claude_sources"
    return "report_section"


def adapt_answer(text: str, fmt: str | None = None) -> tuple[str, list[str] | None, str]:
    """(Markdown blind.py reads, the answer's own reference list or None, format)."""
    fmt = fmt or detect_format(text)
    if fmt not in FORMATS:
        raise adapt.AdaptError("unknown format %r" % fmt)
    if fmt == "gemini_html":
        return adapt.gemini_html(text), None, fmt
    md = text if any(adapt.REPORT_START.match(l) for l in text.splitlines()) else "## Report\n\n" + text
    if fmt == "chatgpt_lenticular":
        return adapt.chatgpt_lenticular(md), None, fmt
    if fmt == "chatgpt_bracketed":
        return adapt.chatgpt_bracketed(md), None, fmt
    if fmt == "perplexity_sources":
        body, cited = adapt.perplexity_sources(md)
        return body, cited, fmt
    if fmt == "gemini_works_cited":
        return adapt.report_section(md), adapt.works_cited(md), fmt
    if fmt == "claude_sources":
        body, cited = adapt.claude_sources(md)
        return body, cited, fmt
    return adapt.report_section(md), None, fmt


def sentences(md: str, cited: list[str] | None, work: Path, system: str = "answer") -> tuple[list[dict], list[str]]:
    """(sentence rows, reference URLs), as prepare_scoring.blind_one makes them."""
    work.mkdir(parents=True, exist_ok=True)
    src = work / ("%s.adapted.md" % system.lower())
    src.write_text(md, encoding="utf-8")
    _body, refs = blind.from_markdown(md)
    if cited is not None:
        if refs:
            raise adapt.AdaptError("links in the body as well as its own reference list")
        refs = list(cited)
    return blind.sentence_rows(src, system), refs


def claims_of(rows: list[dict], refs: list[str], max_claims: int = MAX_CLAIMS) -> tuple[list[dict], list[dict]]:
    """(claims to check, claim-like sentences beyond the limit). Citations as
    prepare_scoring.do_sample builds them."""
    pool = sorted((r for r in rows if IDENT.claim_like(r)), key=lambda r: r["idx"])
    out = []
    for r in pool:
        cites, seen = [], set()
        for n in (int(x) for x in MARK.findall(r["text"])):
            u = refs[n - 1] if 1 <= n <= len(refs) else None
            u = adapt.fragment_free(u) if u else None
            if (n, u) in seen:
                continue
            seen.add((n, u))
            cites.append({"label": "[%d]" % n, "url": u} if u else
                         {"label": "[%d]" % n, "url": None, "note": "marker outside the reference list"})
        out.append({"idx": r["idx"], "claim": r["text"], "context": r["context"], "citations": cites,
                    "reference": ""})
    return out[:max_claims], out[max_claims:]


# --------------------------------------------------------------------------
# 4-5. Licence, then snapshot
# --------------------------------------------------------------------------

def is_open(licence: str | None) -> bool:
    return bool(licence) and licence.strip().lower().startswith("cc")


def licence_of(url: str) -> dict:
    """The cited work's licence, read before anything is fetched: Europe PMC's license
    field by an identifier in the address, else an Unpaywall location whose licence is CC."""
    import find_access as FA
    ids = FA.ids_from_url(url)
    rec = None
    for field, key in (("PMCID", "pmcid"), ("EXT_ID", "pmid"), ("DOI", "doi")):
        if key in ids:
            rec = FA.epmc(ids[key], field)
            time.sleep(1)
            if rec:
                break
    if rec and is_open(rec.get("license")):
        return {"licence": rec["license"], "by": "Europe PMC license field (%s)" % (rec.get("pmcid") or rec.get("pmid")),
                "ids": ids}
    doi = ids.get("doi") or (rec or {}).get("doi")
    if doi:
        up = FA.unpaywall(doi)
        time.sleep(1)
        for loc in (up or {}).get("oa_locations") or []:
            if is_open(loc.get("license")):
                return {"licence": loc["license"], "by": "Unpaywall location %s" % loc.get("host_type"), "ids": ids}
    why = ("no identifier in the address" if not ids else
           "no Creative Commons licence in Europe PMC or Unpaywall for %s" % json.dumps(ids))
    return {"licence": None, "by": why, "ids": ids}


def retrieve_url(url: str, work: Path) -> dict:
    """retrieve_sources.retrieve on one address, its files written under WORK/sources."""
    import retrieve_sources as RN
    import snapshot as SN
    RN.RUN = work
    (work / "sources").mkdir(parents=True, exist_ok=True)
    row = {"url": url, "source_id": SN.source_id(url), "extent": "unreachable"}
    return RN.retrieve(row)


def snapshots(claims: list[dict], work: Path, licence_fn=licence_of, retrieve_fn=retrieve_url) -> dict:
    """{url: manifest row}: licence first; only an openly licensed work is fetched."""
    man = {}
    for c in claims:
        for ct in c["citations"]:
            u = ct.get("url")
            if not u or u in man:
                continue
            lic = licence_fn(u)
            if not is_open(lic["licence"]):
                man[u] = {"url": u, "extent": "unreachable", "extent_why": "no open-licence copy: " + lic["by"],
                          "licence": None, "licence_by": lic["by"], "why_kind": "no open licence"}
                continue
            row = retrieve_fn(u, work)
            row.update(licence=lic["licence"], licence_by=lic["by"])
            if row.get("extent") == "unreachable":
                row["why_kind"] = "not retrieved"
            man[u] = row
    (work / "sources").mkdir(parents=True, exist_ok=True)
    (work / "sources" / "manifest.json").write_text(json.dumps(list(man.values()), indent=1, default=str))
    return man


# --------------------------------------------------------------------------
# 6-7. Judge and label
# --------------------------------------------------------------------------

def prompt_ok() -> None:
    got = hashlib.sha256(J.PROMPT.read_bytes()).hexdigest()
    if got != J.PROMPT_SHA256:
        raise Stop("%s has sha256 %s, not the frozen M1 %s" % (J.PROMPT, got, J.PROMPT_VERSION))


def _docs(c: dict, man: dict, work: Path, count) -> tuple[list[dict], list[str]]:
    """judge_m1's documents for one claim, or the reasons it cannot be judged."""
    docs, why = [], []
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
        tokens = m.get("tokens") or count(text)
        m["tokens"] = tokens
        d = {"source_id": m["source_id"], "url": u, "extent": m["extent"],
             "abstract_only": bool(m.get("abstract_only")), "tokens": tokens, "chunked": False, "text": text}
        if tokens > J.MAX_SOURCE_TOKENS:
            d["text"], d["chunk"] = J.chunk(text, c["claim"], J.MAX_SOURCE_TOKENS, count, [])
            d["chunked"] = True
        bad = J.delivery_problems(text, d["text"], c["claim"], [])
        if bad:
            why.append("%s %s: %s" % (ct["label"], u, "; ".join(bad)))
        docs.append(d)
    return docs, why


def worst_cost(n_in: int) -> float:
    p = S.PRICES[J.CLAUDE_MODEL]
    return (n_in * p["cache_write"] + J.CLAUDE_MAX_OUT * p["output"]) / 1e6


def plan(claims: list[dict], man: dict, work: Path, count) -> list[dict]:
    """Per claim: either a label already (NO SOURCE / COULDN'T CHECK) or the prompt
    and its worst-case cost. Free: count_tokens only."""
    out = []
    for c in claims:
        if not c["citations"]:
            out.append({**c, "label": NO_SOURCE, "reason": "no citation", "study_label": "UNCITED"})
            continue
        docs, why = _docs(c, man, work, count)
        if why:
            out.append({**c, "label": COULDNT, "reason": "; ".join(why), "study_label": None,
                        "sources": [ct.get("url") for ct in c["citations"]]})
            continue
        prefix, rest = J.build(c, docs)
        n_in = count(prefix + rest)
        out.append({**c, "label": None, "docs": docs, "prefix": prefix, "rest": rest, "n_in": n_in,
                    "worst": worst_cost(n_in)})
    return out


def judge(planned: list[dict], client, before_call=None) -> list[dict]:
    """Claude judge, first read; a refusal retried once unchanged (judge_m1's rule)."""
    prompt_ok()
    out = []
    for p in planned:
        if p["label"] is not None:
            out.append({k: v for k, v in p.items() if k not in ("docs", "prefix", "rest")})
            continue
        attempts = []
        for attempt in (1, 2):
            if before_call:
                before_call(p["worst"])
            text, usage, usd, refused = J.call_claude(client, p["prefix"], p["rest"], J.CLAUDE_MODEL)
            attempts.append({"attempt": attempt, "usd": round(usd, 6), "refused": refused, "raw": text,
                             "usage": usage})
            if not refused:
                break
        last = attempts[-1]
        obj, problems = (None, []) if last["refused"] else J.parse(last["raw"])
        m1 = J.final_label((obj or {}).get("label"), last["refused"], p["docs"])
        span = (obj or {}).get("span") or ""
        span_ok = bool(span) and any(J.norm(span) in J.norm(d["text"]) for d in p["docs"])
        if m1 in STUDY_PASS:
            label = BACKED
        elif m1 in STUDY_CITED_FAIL:
            label = NOT_BACKED
        else:
            label = COULDNT
        if obj is None and not last["refused"]:
            reason = "the judge's reply did not parse: " + "; ".join(problems)
        elif m1 == J.REFUSED:
            reason = "the judge refused twice"
        elif m1 == J.NOT_VERIFIABLE_ABSTRACT:
            reason = "only the abstract could be read, and it does not state this"
        else:
            reason = "%s: %s" % (m1, (obj or {}).get("reason") or "")
        out.append({**{k: v for k, v in p.items() if k not in ("docs", "prefix", "rest")},
                    "label": label, "reason": reason, "study_label": m1, "span": span, "span_verbatim": span_ok,
                    "form_problems": problems, "usd": round(sum(a["usd"] for a in attempts), 6),
                    "sources": [d["url"] for d in p["docs"]], "attempts": attempts})
    return out


def totals(results: list[dict]) -> dict:
    t = {k: 0 for k in LABELS}
    for r in results:
        t[r["label"]] += 1
    t["usd"] = round(sum(r.get("usd") or 0 for r in results), 6)
    t["claims"] = len(results)
    return t


def prepare(text: str, work: Path, fmt: str | None = None, max_claims: int = MAX_CLAIMS,
            licence_fn=licence_of, retrieve_fn=retrieve_url, count=None, system: str = "answer") -> dict:
    """Steps 1-5 and the free planning pass: everything before the first model call."""
    md, cited, fmt = adapt_answer(text, fmt)
    rows, refs = sentences(md, cited, work, system)
    claims, beyond = claims_of(rows, refs, max_claims)
    man = snapshots(claims, work, licence_fn, retrieve_fn)
    planned = plan(claims, man, work, count)
    return {"format": fmt, "rows": rows, "refs": refs, "claims": claims, "beyond_limit": beyond,
            "manifest": man, "planned": planned,
            "worst_usd": round(sum(p.get("worst") or 0 for p in planned), 4),
            "calls": sum(1 for p in planned if p["label"] is None)}


def public(results: list[dict], man: dict) -> list[dict]:
    """What a reader is shown per claim: the label, the reason, the source links."""
    out = []
    for r in results:
        links = [ct.get("url") for ct in r["citations"] if ct.get("url")]
        out.append({"idx": r["idx"], "claim": r["claim"], "label": r["label"], "reason": r["reason"],
                    "sources": [{"url": u, "licence": (man.get(u) or {}).get("licence")} for u in links]})
    return out


def count_tokens_fn(raw_client):
    def count(text: str) -> int:
        return raw_client.messages.count_tokens(model=J.CLAUDE_MODEL,
                                                messages=[{"role": "user", "content": text}]).input_tokens
    return count


def scratch() -> Path:
    return Path(tempfile.mkdtemp(prefix="whu-check-"))
