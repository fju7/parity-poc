#!/usr/bin/env python3
"""The claim definition for future rounds (validity plan §6, check 6). Free: no model is called.

A drawn M1 sentence (identifiability.claim_like) is a CLAIM unless code puts it in one of four kinds, the same
rules for every system:

  process       the system's own statement of what it searched, held, read or could not read, or how it worked
                (WHU: a binding row marked protected "reading"; any system: a first-person or self-referring
                subject in the first four words with a process verb from PROCESS_VERB), unless it also states a
                finding (FINDING: the words of bindings.STATES_FINDING, so "We found no trial ..." stays a claim,
                as WHU's own protection refuses it)
  question      the question restated (bindings.QUESTION_RESTATEMENT's words; WHU: protected "question")
  out_of_scope  a line declaring findings outside the answer's scope (bindings.DECLARATION_LEAD's leads, WHU's
                readers' list), or a line under a heading in OUT_OF_SCOPE_HEADING (the last heading in the ~400
                characters before it)
  furniture     a heading, caption or reference-list entry (FURNITURE)

The patterns are copied here, not imported, so this definition cannot move when WHU's code does; the copies are
checked against bindings.py by backend/tests/test_whu_validity_claims.py while they are meant to agree.

    claims.py SENTENCES.jsonl [--protected BINDINGS.json]   print each row's kind
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

KINDS = ("claim", "process", "question", "out_of_scope", "furniture")

FINDING = re.compile(
    r"\b(?:found|no\s+evidence|no\s+stud(?:y|ies)|no\s+trials?|none\s+of|show(?:s|ed|n)?|demonstrated)\b", re.I)
QUESTION = re.compile(
    r"^\W*(?:the|our|this|your)\s+question\s+(?:here\s+)?(?:is|was|we\s+(?:ask|asked|answer|answered))\b", re.I)
DECLARATION = re.compile(
    r"^\W*(?:Outside this question:|Judged not material to this question:|Not added:"
    r"|Findings in our sources we judged outside this question\b)", re.I)
SELF = r"(?:i|we|my|our|this\s+(?:answer|report|response|review|summary|search)|the\s+(?:search|sources?\s+(?:i|we)))"
PROCESS_VERB = re.compile(
    r"\b(?:searched|search(?:ing)?\s+(?:of|for|across)|looked\s+(?:at|for)|reviewed|read|consulted|drew\s+on"
    r"|relied\s+(?:on|mainly\s+on)|obtained|accessed|retrieved|held|focus(?:ed|es)\s+on|limited\s+(?:to|ourselves)"
    r"|could\s+not\s+(?:access|open|obtain|read|retrieve|verify)|(?:was|were)\s+unable\s+to\s+(?:access|open|obtain|read)"
    r"|did\s+not\s+(?:search|read|open|obtain|check|look\s+at)|have\s+not\s+(?:yet\s+)?(?:read|opened|searched))\b",
    re.I)
OUT_OF_SCOPE_HEADING = re.compile(
    r"\b(?:further\s+reading|related\s+(?:topics|questions)|beyond\s+(?:the|this)\s+(?:scope|question)"
    r"|outside\s+(?:the|this)\s+(?:scope|question)|not\s+covered|out\s+of\s+scope|excluded)\b", re.I)
FURNITURE = re.compile(r"^\W*(?:#{1,6}\s|figure\s+\d|fig\.\s*\d|table\s+\d|source:|references?\b|\[\d+\]\s+\S)", re.I)
HEADING_LINE = re.compile(r"^\s*(?:#{1,6}\s+(.+)|\*\*([^*]+)\*\*\s*)$")


def last_heading(context: str) -> str:
    for line in reversed((context or "").splitlines()):
        m = HEADING_LINE.match(line)
        if m:
            return (m.group(1) or m.group(2) or "").strip()
    return ""


def kind(text: str, context: str = "", protected: str | None = None) -> str:
    """One of KINDS for a drawn sentence. PROTECTED is WHU's binding-row marker for it, if any."""
    t = (text or "").strip()
    if protected == "question" or QUESTION.search(t):
        return "question"
    if protected == "scope" or DECLARATION.search(t) or OUT_OF_SCOPE_HEADING.search(last_heading(context)):
        return "out_of_scope"
    if FURNITURE.search(t):
        return "furniture"
    if protected == "reading":
        return "process"
    head = " ".join(t.split()[:4])
    if re.search(r"^\W*%s\b" % SELF, head, re.I) and PROCESS_VERB.search(t) and not FINDING.search(t):
        return "process"
    return "claim"


def _norm(t: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", re.sub(r"\[\d+(?:[,–-]\s*\d+)*\]", " ", t or "").lower()))


def protected_map(bindings_json: Path) -> dict[str, str]:
    """{normalised sentence: protected kind} from a WHU page's bindings.json."""
    b = json.loads(bindings_json.read_text(encoding="utf-8"))["bindings"]
    return {_norm(r["sentence"]): r["protected"] for r in b.values() if r.get("protected")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sentences", type=Path)
    ap.add_argument("--protected", type=Path)
    a = ap.parse_args()
    prot = protected_map(a.protected) if a.protected else {}
    for line in a.sentences.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        print(r["idx"], kind(r["text"], r.get("context") or "", prot.get(_norm(r["text"]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
