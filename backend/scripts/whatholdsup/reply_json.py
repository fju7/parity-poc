"""One JSON value in a model's reply: the shared reply rule (advisor's ruling 1 on the 04h fork, 2026-11-27).

A reply is valid if it holds exactly ONE top-level JSON value of the required type (object or array), preceded at
most by a short non-JSON lead-in, with NOTHING after it, and the value parses whole as given -- no repair. A
second JSON value, trailing text, or a value that does not parse (cut off, broken) is invalid; the caller then
re-asks once, and a second invalid reply fails.

This narrows the rule ruled after attempt 17 ("exactly one JSON object, the whole reply") in one direction only:
a short lead-in before the value is allowed, because it hides nothing -- there is one unambiguous value and code
never guesses which. Everything after the value stays forbidden.

  - Before a bare value: a short lead-in, at most LEAD_MAX characters, holding no "{"; a "[" in it only as a
    citation marker ("[1]", "[2, 4]"; the advisor's condition of 2026-11-23), never as a JSON value.
  - A value in a code fence: prose before the fence keeps the rule ruled after attempt 14 (no JSON value in it,
    citation markers allowed, any length -- web-search final blocks summarise before their fenced answer, e.g.
    attempt 14's two recorded replies, 1,589 and 1,628 characters); the fence holds the one value; nothing after.
"""
from __future__ import annotations

import json
import re

LEAD_MAX = 600
CITATION = re.compile(r"\[\d{1,3}(?:\s*,\s*\d{1,3})*\]")
FENCED = re.compile(r"(?s)\A(.*?)```(?:json)?[ \t]*\n?(.*?)\n?[ \t]*```\s*\Z", re.IGNORECASE)


class Invalid(ValueError):
    """The reply is not one JSON value under the rule; the message says why."""


def _start(text: str) -> int:
    if text[:1] in "{[":
        return 0                                        # no lead-in: the value starts the reply
    masked = CITATION.sub(lambda m: " " * len(m.group(0)), text)
    hits = [i for i in (masked.find("{"), masked.find("[")) if i >= 0]
    return min(hits) if hits else -1


def value(text: str, kind: str = "object"):
    """The reply's one JSON value of KIND ("object" or "array"), or raise Invalid."""
    return parts(text, kind)[0]


def parts(text: str, kind: str = "object"):
    """(the value, the lead-in before it), or raise Invalid. The lead-in is logged by callers, never parsed."""
    want = list if kind == "array" else dict
    t = (text or "").strip()
    m = FENCED.match(t)
    if m:
        lead, body = m.group(1), m.group(2).strip()
        if "```" in body:
            raise Invalid("more than one code fence")
        i = 0 if body[:1] in "{[" else -1
    else:
        i = _start(t)
        lead, body = (t[:i] if i >= 0 else t), t
    if i < 0:
        raise Invalid("no JSON value")
    if not m and len(lead.strip()) > LEAD_MAX:
        raise Invalid("the text before the value is longer than a short lead-in (%d > %d characters)"
                      % (len(lead.strip()), LEAD_MAX))
    if "{" in lead or "[" in CITATION.sub("", lead):
        raise Invalid("JSON before the value")
    try:
        v, end = json.JSONDecoder().raw_decode(body, i)
    except ValueError as e:
        raise Invalid("the value does not parse whole as given (%s)" % e)
    rest = body[end:].strip()
    if rest:
        raise Invalid("text or a second value after the value: %r" % rest[:80])
    if not isinstance(v, want):
        raise Invalid("the value is not a JSON %s" % kind)
    return v, lead.strip()


def ok(text: str, kind: str = "object") -> bool:
    try:
        value(text, kind)
        return True
    except Invalid:
        return False
