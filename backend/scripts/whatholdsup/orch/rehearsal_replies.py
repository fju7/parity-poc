"""The offline rehearsal's reply generators (orch/rehearsal.py). Each recognises one prompt by its own fixed words
and answers in the shape that prompt asks for, built from the prompt itself (its ids, passages, sentences) or, where
the base attempt recorded it, from that record (WHU_REHEARSE_BASE: the base case folder, read only). Synthetic,
never a model's reading: a rehearsal proves the plumbing, not the page."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

R = sys.modules["whu_rehearsal"]
HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


def _has(*words):
    return lambda prompt, step, what, provider: all(w in prompt for w in words)


def _base() -> Path | None:
    p = os.environ.get("WHU_REHEARSE_BASE")
    return Path(p) if p and Path(p).is_dir() else None


def _first_sentence(text: str) -> str:
    import source_ledger as L
    s = L.sentences(" ".join((text or "").split()))
    return s[0] if s else ""


JUNK = re.compile(r"Keywords|display-pdf|pmc-|Received |Accepted |Collection date|doi:|https?://|\bPMC\d|et al|colleagues|Table \d|Figure \d|\(\s*\d{4}\s*\)", re.I)


# Furniture a model would never state as a finding, found on 02w's newly held gap maps (P136): JATS converter
# metadata, author lists ("K. , Jeffries , D. ,"), and abbreviation lists (mostly capitalised short tokens).
FURNITURE = re.compile(r"version-number|cover-date|[Cc]onverter|\s,\s|\b[A-Z]\.\s*,")


def _prose(s: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z\u2010-]*", s)
    if len(words) < 8:
        return False
    caps = sum(1 for w in words if w.isupper() and len(w) > 1)
    return caps / len(words) < 0.2 and sum(1 for w in words if w.islower()) / len(words) > 0.5


def _clean_sentence(text: str) -> str:
    """The first sentence of TEXT that reads as prose (40-300 characters, no record furniture), else ""."""
    import source_ledger as L
    for s in L.sentences(" ".join((text or "").split())):
        if 40 <= len(s) <= 300 and not JUNK.search(s) and not FURNITURE.search(s) and s[0].isupper() \
                and s.rstrip().endswith(".") and _prose(s):
            return s
    return ""


def _after(prompt: str, label: str) -> str:
    i = prompt.find(label)
    return prompt[i + len(label):] if i >= 0 else ""


# ------------------------------------------------------------------ the orchestrator's own steps (orch/model_steps)

@R.generator("premise", _has("You prepare the entry gate for a fact-check"))
def premise(prompt, step, what):
    q = _after(prompt, "QUESTION:").strip()
    return json.dumps({
        "belief": "Inclusive education helps children with disabilities learn in ordinary schools.",
        "kill_condition": "The held systematic reviews find no improvement in any education outcome.",
        "reader_with_a_decision": "A programme officer choosing which education programme to fund.",
        "scope_covers": q[:200] or "the question as asked",
        "scope_out": [{"what": "programmes in high-income countries", "why": "outside the question's settings"}],
        "weighs": "measured and assessed",
        "measured": "outcomes measured in trials and evaluations",
        "assessed": "a review's certainty rating"})


@R.generator("discover", _has("Find the primary sources that best answer this question"))
def discover(prompt, step, what):
    """The base attempt's proposals, as recorded in its sources.json (found and unresolved)."""
    base = _base()
    rows = []
    if base and (base / "sources.json").exists():
        d = json.loads((base / "sources.json").read_text(encoding="utf-8"))
        for s in d.get("sources") or []:
            rows.append({"title": s.get("title"), "first_author": (s.get("authors") or s.get("first_author") or
                                                                  "Unknown").split(",")[0].split(" ")[0],
                         "year": s.get("year"), "container": s.get("container") or "",
                         "type": s.get("type") or "review", "url": s.get("url") or "",
                         "why": "recorded proposal (rehearsal)"})
        for u in d.get("unresolved_proposals") or []:
            p = u.get("proposal") or u
            if p.get("title"):
                rows.append({"title": p["title"], "first_author": p.get("first_author") or "Unknown",
                             "year": p.get("year"), "container": p.get("container") or "",
                             "type": p.get("type") or "review", "url": p.get("url") or "",
                             "why": "recorded proposal (rehearsal)"})
    return json.dumps({"sources": rows})


def _passages(prompt):
    body = _after(prompt, "PASSAGES:")
    return re.findall(r"^\[([^\]]+)\] (.+)$", body, re.M)


@R.generator("draft", _has("Write a What Holds Up page answering the question below"))
def draft(prompt, step, what):
    ps = [(pid, _clean_sentence(t)) for pid, t in _passages(prompt)]
    ps = [(pid, s) for pid, s in ps if s][:9]
    def sents(chunk):
        return [{"text": s, "passages": [pid]} for pid, s in chunk]
    return json.dumps({"title": "What the reviews find",
                       "sections": [{"id": "answer", "heading": "The short answer",
                                     "blocks": [{"sentences": sents(ps[:2])}]},
                                    {"id": "findings", "heading": "What the sources report",
                                     "blocks": [{"h3": "Findings"}, {"sentences": sents(ps[2:7])}]},
                                    {"id": "verdict", "heading": "What holds up",
                                     "blocks": [{"sentences": sents(ps[7:9] or ps[:1])}]}]})


_COVERAGE_SEEN = {"n": 0}


@R.generator("coverage", _has("Its sources contain the finding below"))
def coverage(prompt, step, what):
    """Most findings stated (in the finding's own first sentence), one in four not material: a real reply's mix,
    inside the declarations budget."""
    _COVERAGE_SEEN["n"] += 1
    s = _clean_sentence(_after(prompt, "FINDING:"))
    if s and _COVERAGE_SEEN["n"] % 4:
        return json.dumps({"decision": "state", "why": "rehearsal: the page should say it", "element": "",
                           "sentence": s})
    return json.dumps({"decision": "not_material", "why": "rehearsal: not material to the question",
                       "element": "", "sentence": ""})


@R.generator("judgement", _has("must state the assessment below, from its source"))
def judgement(prompt, step, what):
    # the first sentence that reads as prose (P136: on 02w's newly held gap maps the first "sentence" of an assessment
    # was an abbreviation list or a reference fragment, which no model would write and the page check refused)
    a = _after(prompt, "ASSESSMENT (verbatim from the source):")
    return json.dumps({"sentence": _clean_sentence(a) or
                       "The review states its conclusion in its abstract, in its own words (rehearsal)."})


# ------------------------------------------------------------------ ruling prompts (audit_prompts/*.md)

def _block(prompt: str, name: str) -> str:
    m = re.search(r"<<<%s\n(.*?)\n%s>>>" % (name, name), prompt, re.S)
    return m.group(1) if m else ""


@R.generator("rule-relevance", _has("You decide only whether that judgement bears on the question"))
def rule_relevance(prompt, step, what):
    q = _block(prompt, "QUESTION")
    words = "low- and middle-income countries" if "low- and middle-income countries" in q else " ".join(q.split()[:3])
    if not _clean_sentence(_block(prompt, "JUDGEMENT")):
        # a "judgement" with no prose sentence in it (a gap map's abbreviation or author list, P136) is not one a
        # model would rule relevant: no question words in it
        return json.dumps({"relevant": False, "question_words": "",
                           "reason": "The passage states no assessment (rehearsal)."})
    return json.dumps({"relevant": True, "question_words": words,
                       "reason": "It bears on whether the programmes work (rehearsal)."})


# ------------------------------------------------------------------ the gate (factcheck_draft)

@R.generator("recency", _has("You check whether a draft is out of date"))
def recency(prompt, step, what):
    srcs = re.findall(r"^\s*\[(\d+)\] ([^\n]+)$", _after(prompt, "\n Sources\n"), re.M)
    studies = [{"name": t.split(". ")[1] if ". " in t else t[:120], "draft_uses": "the review as cited",
                "latest_known": "the cited version (rehearsal)", "status": "CURRENT",
                "url": "https://europepmc.org/", "what_changed": ""} for _n, t in srcs]
    return json.dumps({"studies": studies})


# ------------------------------------------------------------------ the source advocate

@R.generator("advocate", _has("A publication called What Holds Up is about to publish an assessment"))
def advocate(prompt, step, what):
    return "[]"


# ------------------------------------------------------------------ the audit reader (audit_prompts/read.md)

def _documents(prompt: str) -> dict:
    return {m.group(1): m.group(2) for m in re.finditer(r"<<<DOCUMENT (\S+)\n(.*?)\nDOCUMENT \1>>>", prompt, re.S)}


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKC", s or "").replace("‐", "-").replace("‑", "-")
    return " ".join(s.split()).lower()


MARK = re.compile(r"\s*\[\d+(?:,\s*\d+)*\]")


@R.generator("audit-read", _has("THE SENTENCES TO READ", "Reply with ONE JSON object"))
def audit_read(prompt, step, what):
    docs = _documents(prompt)
    out = []
    for m in re.finditer(r"^\[(u\d+)\] \(([^)]*)\)\nSENTENCE: (.*?)\n(?:.*?\n)*?BINDING: (.*?)$", prompt, re.M):
        uid, _part, sentence, binding = m.groups()
        bare = MARK.sub("", sentence).strip()
        src = re.match(r"rests on (\S+?):", binding)
        doc = docs.get(src.group(1)) if src else None
        quote = bare[:300].rstrip()
        if doc is not None and _norm(quote) in _norm(doc):
            out.append({"id": uid, "verdict": "holds", "kind": None,
                        "evidence": [{"source": src.group(1), "quote": quote}], "proposed_text": None,
                        "reason": "The sentence is the document's own words (rehearsal)."})
        else:
            out.append({"id": uid, "verdict": "not_a_correction", "kind": None, "evidence": [],
                        "proposed_text": None, "reason": "No claim checked against a document (rehearsal)."})
    return json.dumps({"verdicts": out})


# ------------------------------------------------------------------ Google (orch/google.py)

@R.generator("google-preflight", _has("Reply with the single word: ok"))
def google_preflight(prompt, step, what):
    return "ok"


@R.generator("overstatement", _has("You compare one sentence with the passage it cites"))
def overstatement(prompt, step, what):
    return json.dumps({"overstates": "no", "how": "none", "why": "The sentence is the passage's own words (rehearsal)."})


# ------------------------------------------------------------------ the premise rows after reading (orch/premise_reading)

@R.generator("belief-outlet", _has("Find up to", "that state the belief below"))
def belief_outlet(prompt, step, what):
    """One page code must refuse (too few of the belief's key words) and one it can verify (recorded live once)."""
    return json.dumps({"outlets": [
        {"outlet": "World Health Organization", "url": "https://www.who.int/news-room/fact-sheets/detail/disability-and-health",
         "sentence": "rehearsal"},
        {"outlet": "UNICEF", "url": "https://www.unicef.org/education/inclusive-education", "sentence": "rehearsal"}]})


@R.generator("premise-reading", _has("answer three things about the", "KILL CONDITION:", "PASSAGES:"))
def premise_reading(prompt, step, what):
    q, sid = "", ""
    for m in re.finditer(r"^\[(S\d+)\] (.+)$", _after(prompt, "PASSAGES:"), re.M):
        s = _clean_sentence(m.group(2))
        if s:
            q, sid = s[:290], m.group(1)
            break
    quote = {"source": sid, "quote": q}
    return json.dumps({"sources_show": "The held review reports %s (rehearsal)." % "improved outcomes for some programmes",
                       "sources_show_quote": quote, "direction": "narrows", "direction_quote": quote,
                       "direction_why": "The held review finds effects for some programmes only (rehearsal).",
                       "kill_result": "survived", "kill_quote": quote,
                       "kill_note": "The held review does report improved outcomes (rehearsal)."})
