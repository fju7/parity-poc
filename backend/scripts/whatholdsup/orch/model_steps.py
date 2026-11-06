"""The orchestrator's model steps (docs/whu-orchestrator.md §2.1). Each builds its prompt from declared
inputs only, takes the reply through ASK (a function (prompt, max_tokens, role) -> text, which in a paid run
is a metered, guarded call and in tests a stub), validates it against a fixed schema, and returns data for
the step's code to write. A model never writes a file, runs a command or chooses the next step; a reply
outside the schema is a StepFailed, never repaired by hand.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


class StepFailed(RuntimeError):
    pass


def now() -> str:
    """The clock, read from the system (never estimated)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_json(text: str):
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = t.find(opener), t.rfind(closer)
        if i >= 0 and j > i:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                continue
    raise StepFailed("the reply is not JSON: %r" % (text or "")[:200])


def _str(d: dict, k: str, limit: int, required: bool = True) -> str:
    v = d.get(k)
    if v is None and not required:
        return ""
    if not isinstance(v, str) or (required and not v.strip()):
        raise StepFailed("field %r missing or not text" % k)
    v = " ".join(v.split())
    if len(v) > limit:
        raise StepFailed("field %r is over %d characters" % (k, limit))
    return v


# ---- 1. premise (before any source exists) ----------------------------------------------------------------

PREMISE_PROMPT = """You prepare the entry gate for a fact-check of one question. You have NOT seen any source and must not
cite one. From the question alone, write JSON only:
{{"belief": "<what a well-informed non-expert likely believes on this question, stated as they would state it>",
 "kill_condition": "<the finding in the primary sources that would mean there is no story>",
 "reader_with_a_decision": "<who would act on the answer, and what decision>",
 "scope_covers": "<what the question covers>",
 "scope_out": [{{"what": "<a neighbouring question this page will not answer>", "why": "<why>"}}],
 "weighs": "measured" | "assessed" | "measured and assessed",
 "measured": "<what counts as measured evidence here>",
 "assessed": "<what counts as an assessed judgement here (a review's or panel's certainty rating)>"}}

QUESTION:
{question}
"""

PREMISE_FIXED = ("belief", "kill_condition", "reader_with_a_decision", "scope", "evidence_standard")


def premise(question: str, ask, by: str) -> dict:
    """The rows fixed before any source (ruling C): belief, kill condition, reader, scope, evidence standard."""
    d = parse_json(ask(PREMISE_PROMPT.format(question=question), 1500, "premise"))
    if not isinstance(d, dict):
        raise StepFailed("the premise reply is not an object")
    weighs = _str(d, "weighs", 40)
    if weighs not in ("measured", "assessed", "measured and assessed"):
        raise StepFailed("weighs must be measured, assessed or both")
    outs = d.get("scope_out") or []
    if not isinstance(outs, list) or not all(isinstance(o, dict) for o in outs):
        raise StepFailed("scope_out must be a list of {what, why}")
    at = now()
    return {"belief": {"statement": _str(d, "belief", 600)},
            "kill_condition": _str(d, "kill_condition", 600),
            "reader_with_a_decision": _str(d, "reader_with_a_decision", 400),
            "scope": {"covers": _str(d, "scope_covers", 600),
                      "out": [{"what": _str(o, "what", 300), "why": _str(o, "why", 300)} for o in outs[:6]],
                      "by": by, "written_at": at},
            "evidence_standard": {"weighs": weighs, "measured": _str(d, "measured", 400),
                                  "assessed": _str(d, "assessed", 400), "when_they_differ": "state both",
                                  "by": by, "written_at": at}}


# ---- 2. discover (web search; proposals only) -------------------------------------------------------------

DISCOVER_PROMPT = """Find the primary sources that best answer this question: the most recent systematic reviews,
assessment reports, guidelines and pivotal trials. Propose at most {n}. For each, give only what identifies it;
never an identifier you have not seen. JSON only:
{{"sources": [{{"title": "<exact title>", "first_author": "<surname, or the issuing body>", "year": <year>,
  "container": "<journal or publisher>", "type": "<one of: {types}>",
  "url": "<the page where you found it>", "why": "<what it is for, at most 25 words>"}}]}}

QUESTION:
{question}
"""


def discover_prompt(question: str, n: int, types: list[str]) -> str:
    return DISCOVER_PROMPT.format(question=question, n=n, types=", ".join(types))


def discover_proposals(reply, types: set, n: int) -> list[dict]:
    """The validated proposals. There is no `form` field: form is derived by code from the type (E6)."""
    d = reply if isinstance(reply, dict) else parse_json(reply)
    rows = d.get("sources") if isinstance(d, dict) else None
    if not isinstance(rows, list):
        raise StepFailed("no sources list")
    out = []
    for r in rows[:n]:
        if not isinstance(r, dict):
            continue
        t = r.get("type")
        if t not in types:
            raise StepFailed("type %r is not one of source_store.TYPES" % t)
        if "form" in r:
            raise StepFailed("a proposal may not name a form: form is derived from the type")
        y = r.get("year")
        out.append({"title": _str(r, "title", 400), "first_author": _str(r, "first_author", 120),
                    "year": int(y) if isinstance(y, int) or (isinstance(y, str) and y.isdigit()) else None,
                    "container": _str(r, "container", 200, required=False), "type": t,
                    "url": _str(r, "url", 500, required=False), "why": _str(r, "why", 300, required=False)})
    return out


# ---- 4. draft ----------------------------------------------------------------------------------------------

DRAFT_PROMPT = """Write a What Holds Up page answering the question below from the passages given, and from nothing
else. Every sentence must rest on the passages it names; say what the sources say, with their own certainty
words; never generalise beyond them. JSON only:
{{"title": "<page title>",
 "sections": [{{"id": "answer", "heading": "The short answer", "blocks": [...]}},
              {{"id": "findings", "heading": "<heading>", "blocks": [...]}},
              {{"id": "verdict", "heading": "What holds up", "blocks": [...]}}]}}
where each block is {{"h3": "<subheading>"}} or {{"sentences": [{{"text": "<one sentence>", "passages": ["<id>", ...]}}]}}.
A sentence that draws only on the page's own earlier sentences gives "passages": []. Do not write citation
numbers; code adds them.

QUESTION:
{question}

PASSAGES:
{passages}
"""

SECTION_IDS = ("answer", "findings", "verdict")


def draft_prompt(question: str, passages: dict) -> str:
    body = "\n\n".join("[%s] %s" % (pid, " ".join(p["text"].split())) for pid, p in passages.items())
    return DRAFT_PROMPT.format(question=question, passages=body)


def draft_page(reply, passages: dict) -> dict:
    """{"title", "sections": [{"id", "heading", "blocks"}]} with every passage id one that was sent."""
    d = reply if isinstance(reply, dict) else parse_json(reply)
    if not isinstance(d, dict) or not isinstance(d.get("sections"), list):
        raise StepFailed("no sections")
    title = _str(d, "title", 200)
    secs = []
    for s in d["sections"]:
        if not isinstance(s, dict) or s.get("id") not in SECTION_IDS:
            raise StepFailed("section id must be one of %s" % (SECTION_IDS,))
        blocks = []
        for b in s.get("blocks") or []:
            if isinstance(b, dict) and isinstance(b.get("h3"), str):
                blocks.append({"h3": " ".join(b["h3"].split())[:200]})
                continue
            sents = (b or {}).get("sentences") if isinstance(b, dict) else None
            if not isinstance(sents, list):
                raise StepFailed("a block is neither h3 nor sentences")
            row = []
            for x in sents:
                text = re.sub(r"\s*\[\d+(?:[,–-]\s*\d+)*\]", "", _str(x, "text", 900))
                pids = x.get("passages") or []
                bad = [p for p in pids if p not in passages]
                if bad:
                    raise StepFailed("passage id(s) not sent: %s" % bad[:3])
                row.append({"text": text, "passages": list(dict.fromkeys(pids))})
            blocks.append({"sentences": row})
        secs.append({"id": s["id"], "heading": _str(s, "heading", 120), "blocks": blocks})
    if [s["id"] for s in secs] != list(SECTION_IDS):
        raise StepFailed("the sections must be answer, findings, verdict, in that order")
    return {"title": title, "sections": secs}


# ---- 6. coverage decisions -----------------------------------------------------------------------------------

COVERAGE_PROMPT = """A fact-check page answers the question below. Its sources contain the finding below, which the
page does not use. Decide, JSON only:
{{"decision": "out_of_scope" | "not_material" | "state", "why": "<at most 30 words>",
 "sentence": "<if state: one sentence saying what the finding says, with its own certainty words; else empty>"}}

QUESTION:
{question}

SCOPE:
{scope}

FINDING:
{unit}
"""


def coverage_decision(question: str, scope: str, unit: str, ask) -> dict:
    d = parse_json(ask(COVERAGE_PROMPT.format(question=question, scope=scope, unit=unit), 600, "coverage"))
    if not isinstance(d, dict) or d.get("decision") not in ("out_of_scope", "not_material", "state"):
        raise StepFailed("decision must be out_of_scope, not_material or state")
    out = {"decision": d["decision"], "why": _str(d, "why", 300)}
    if d["decision"] == "state":
        out["sentence"] = _str(d, "sentence", 900)
    return out


# ---- 7. judgement sentences ----------------------------------------------------------------------------------

JUDGEMENT_PROMPT = """A fact-check page must state the assessment below, from its source, with the source's own
certainty or confidence words. Write one sentence, JSON only:
{{"sentence": "<the sentence>"}}

ASSESSMENT (verbatim from the source):
{text}
"""


def judgement_sentence(text: str, ask) -> str:
    d = parse_json(ask(JUDGEMENT_PROMPT.format(text=text), 500, "judgement_sentence"))
    if not isinstance(d, dict):
        raise StepFailed("not an object")
    return _str(d, "sentence", 900)
