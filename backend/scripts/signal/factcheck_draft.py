"""
Pre-publication fact-check gate for What Holds Up drafts.

WHY THIS EXISTS
---------------
On 2026-08-26 the melanoma draft was fact-checked by hand before publication.
Six things were wrong:

  1. STALE      three-year trial figures, superseded by a five-year readout
                published 1 June 2026 — two and a half months before the draft.
  2. ATTRIBUTED a one-sided p-value credited to The Lancet. It came from a
                company press release. The Lancet published a different,
                two-sided value.
  3. PHANTOM    a p-value of 0.0075 that appears in no source we can find.
  4. DROPPED    an earlier draft removed a figure as "unverifiable" that was
                sitting in the abstract of a paper the draft itself cited.
  5. SELECTIVE  one endpoint reported as strengthening; a second endpoint that
                had weakened went unmentioned, as did a toxicity difference.
  6. UNSUPPORTED an accusation about how other outlets had behaved, asserted
                without checking a single one. All of them had behaved.

Every one of those was caught, and the piece published with the list attached.
But the check was DISCRETIONARY — it happened because the writer chose to run
it. A process where the writer decides whether to be checked is not a process.

This makes it a gate. Non-zero exit blocks publication.

WHAT MAKES IT WORK
------------------
Two design rules, both learned the hard way:

* The checker is never given the draft's own source list as authority. It
  re-derives every figure from primary sources it finds itself. Four of the six
  errors above were INSIDE the draft's bibliography — a checker that verifies a
  draft against its own references confirms them.

* Unverified is a FAILURE, not a warning. This is the same lesson golden_set.py
  learned: an `api failed` that only printed a warning let a run report success
  while completely blind. Warnings get waved through on a Friday afternoon.

FIVE ROLES, NOT ONE
-------------------
A single "check the facts" pass catches classes 1-4 and misses 5 and 6, which
are the ones that make a piece unfair rather than merely wrong.

  SOURCE   Does the named source actually contain this figure, at this value?
           Grouped by source, because that is how a human checks: open the
           paper once, verify everything attributed to it.
  RECENCY  Has a newer readout superseded any study cited? One pass over the
           whole draft.
  INFER    Is the conclusion drawn from a figure warranted by it? A hazard
           ratio converted into lives, a design criticism imported across
           designs, a missing number reported as missing evidence.
  ADVOCATE What would the subject's head of communications object to as unfair
           or selective? One pass, reading the draft whole. This is the only
           role that can see an omission, because omissions are invisible when
           you check claims one at a time.
  COVERAGE Who else covered this story carefully, and what did they get right?
           Runs against the best of the coverage rather than the average, so a
           claim that "reporting missed X" has to survive someone having said
           X. Also reports what this piece can add that careful coverage does
           not — which is a stronger footing than a failure nobody committed.

Costs roughly (one call per distinct source) + 2, plus web searches. For a
piece citing four sources that is about six calls. Run once per issue.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/factcheck_draft.py --verify           # credentials only
    python scripts/signal/factcheck_draft.py path/to/draft.html
    python scripts/signal/factcheck_draft.py draft.html --report out.json
    python scripts/signal/factcheck_draft.py draft.html --known-errors

Exit codes:
    0  every claim VERIFIED and no SERIOUS objection
    1  something is unverified, wrong, stale, or seriously unfair
    2  the check could not run (credentials, unreadable draft, API failure)
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from signal_model import MODEL as SIGNAL_MODEL, warn_if_unpinned

# Server-side web search. Available on the standard API with no beta header.
# If the org has web search disabled in Console settings, calls fail and this
# script exits 2 rather than passing a draft it could not check.
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search"}
MAX_SEARCHES_PER_CALL = 12

BACKOFF_DELAYS = [5, 15, 40]
JSON_RETRIES = 2

KNOWN_ERRORS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "factcheck_known_errors.json"

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("[ERROR] ANTHROPIC_API_KEY is not set.")
            sys.exit(2)
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ---------------------------------------------------------------------------
# draft reading
# ---------------------------------------------------------------------------

def read_draft(path: Path) -> str:
    """Return the visible prose of a draft, HTML or plain text."""
    if not path.exists():
        print(f"[ERROR] Draft not found: {path}")
        sys.exit(2)
    raw = path.read_text(encoding="utf-8")
    if "<" not in raw:
        return raw
    body = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", raw)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    body = html.unescape(body)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n\s*\n\s*\n+", "\n\n", body)
    text = body.strip()
    if len(text) < 200:
        print(f"[ERROR] Draft yielded only {len(text)} characters of prose. Wrong file?")
        sys.exit(2)
    return text


# ---------------------------------------------------------------------------
# API plumbing
# ---------------------------------------------------------------------------

def _response_text(response) -> str:
    """Concatenate text blocks, skipping server-tool result blocks."""
    parts = []
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", "") or "")
    return "\n".join(parts).strip()


def _first_json_value(text: str) -> str | None:
    """Salvage the first complete JSON object or array from prose."""
    start = None
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            break
    if start is None:
        return None
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def call(system: str, user: str, *, search: bool, max_tokens: int = 8000, label: str = ""):
    """One model call, optionally with web search. Returns parsed JSON or None."""
    client = _get_client()
    kwargs = {}
    if search:
        kwargs["tools"] = [dict(WEB_SEARCH_TOOL, max_uses=MAX_SEARCHES_PER_CALL)]

    for json_attempt in range(JSON_RETRIES + 1):
        response = None
        for attempt in range(len(BACKOFF_DELAYS) + 1):
            try:
                response = client.messages.create(
                    model=SIGNAL_MODEL,
                    max_tokens=max_tokens,
                    temperature=0,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    **kwargs,
                )
                break
            except Exception as exc:
                err = str(exc)
                if "529" in err and attempt < len(BACKOFF_DELAYS):
                    delay = BACKOFF_DELAYS[attempt]
                    print(f"  [RETRY] overloaded, {attempt + 1}/{len(BACKOFF_DELAYS)} in {delay}s...")
                    time.sleep(delay)
                    continue
                print(f"  [ERROR] {label or 'call'}: {exc}")
                return None
        if response is None:
            return None

        text = _response_text(response)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            salvaged = _first_json_value(text)
            if salvaged:
                try:
                    return json.loads(salvaged)
                except json.JSONDecodeError:
                    pass
            if json_attempt < JSON_RETRIES:
                print(f"  [RETRY] {label}: response was not JSON, {json_attempt + 1}/{JSON_RETRIES}...")
                time.sleep(1)
                continue
            print(f"  [ERROR] {label}: no JSON after {JSON_RETRIES + 1} attempts. Tail: {text[-200:]!r}")
            return None
    return None


# ---------------------------------------------------------------------------
# phase 1 — extract claims
# ---------------------------------------------------------------------------

EXTRACT_SYSTEM = """You extract checkable claims from a draft article for fact-checking.

Return ONLY a JSON array. No prose, no markdown fence.

Each element:
{
  "id": "c1",
  "figure": "the exact number, statistic or quoted value as printed",
  "claim": "one sentence stating what the draft asserts",
  "attributed_to": "the source the draft credits, verbatim; null if it credits none",
  "kind": "figure" | "attribution" | "characterisation",
  "scope": "external" | "internal"
}

SCOPE is the most important field and the easiest to get wrong.

  external  A claim about the world, checkable against a source someone else
            published: a trial figure, a date, what a company released, what
            another outlet did or did not report.
  internal  A claim about the publication itself, checkable only from its own
            records: its scoring rubric and the arithmetic on it, its
            corrections policy and response times, its own editorial history
            ("we cut this", "we read seventeen articles", "six things were
            wrong"), and its own byline dates.

Only external claims can be verified against sources. Marking an internal
claim external produces a NOT_FOUND that means nothing and trains the reader
of this report to ignore it. Marking an external claim internal hides a real
failure — when genuinely unsure, choose external.

A claim about the publication's OWN CONDUCT toward third parties is external:
"every outlet we could reach attributed them correctly" is a claim about
outlets, not about us, and must be checked.

Extract EVERY:
  - number, percentage, ratio, interval, p-value, sample size, date
  - claim about what a named source says or contains
  - claim about what a third party (a company, an outlet, a regulator) did,
    said, omitted or failed to do

That last category matters most and is the easiest to miss. "No outlet
reported X", "the release contains no Y", "the coverage failed to Z" are
claims about the world that can be checked and are frequently wrong.

Do NOT extract: opinions, predictions, definitions, or explanations of
general concepts that carry no specific figure.

A number that appears in the draft with no source credited still gets
extracted, with attributed_to set to null. Those are the dangerous ones."""


def extract_claims(draft: str) -> list[dict] | None:
    print("[1/6] Extracting checkable claims...")
    out = call(
        EXTRACT_SYSTEM,
        f"Draft follows.\n\n---\n{draft}\n---",
        search=False, label="extract",
    )
    if out is None:
        return None
    if isinstance(out, dict):
        for key in ("claims", "items", "results"):
            if isinstance(out.get(key), list):
                out = out[key]
                break
    if not isinstance(out, list) or not out:
        print("[ERROR] Extraction returned no claims.")
        return None
    for i, c in enumerate(out):
        c.setdefault("id", f"c{i + 1}")
    print(f"      {len(out)} claims extracted")
    return out


# ---------------------------------------------------------------------------
# phase 2 — SOURCE audit, grouped by attributed source
# ---------------------------------------------------------------------------

SOURCE_SYSTEM = """You verify figures against primary sources. You are adversarial: your job is
to find what is wrong, not to confirm what is written.

CRITICAL RULE. The draft's own bibliography is NOT evidence. Find the source
yourself with web search and read what it actually says. If the draft says a
figure comes from a particular paper, your job is to check whether that paper
contains that figure — not to assume it does because the draft says so.

Prefer, in order: the peer-reviewed publication, the regulatory filing, the
company's own release, then anything else. A trade-press article is not a
primary source and never verifies a figure on its own.

Return ONLY a JSON array, one element per claim given to you:
{
  "id": "c1",
  "verdict": "VERIFIED" | "WRONG_VALUE" | "WRONG_SOURCE" | "NOT_FOUND",
  "found_value": "what the source actually says, or null",
  "actual_source": "where this figure really comes from, if not as attributed",
  "url": "the URL you verified against, or null",
  "note": "one sentence; required unless VERIFIED"
}

VERIFIED     the named source contains this figure at this value.
WRONG_VALUE  the source has this figure but a different value.
WRONG_SOURCE the figure is real but comes from somewhere else. Say where.
NOT_FOUND    you could not find this figure in any source you could reach.

NOT_FOUND is the correct verdict when you cannot reach the source. Do not
guess, and do not mark something VERIFIED because it sounds right or because
you remember it. If you could not open the document, say NOT_FOUND and explain
in the note. An unverifiable claim is a failure, not a pass."""


def audit_sources(claims: list[dict], draft_title: str) -> dict[str, dict]:
    external = [c for c in claims if c.get("scope", "external") != "internal"]
    internal = [c for c in claims if c.get("scope") == "internal"]
    if internal:
        print(f"      {len(internal)} internal claim(s) recorded, not source-checked")

    groups: dict[str, list[dict]] = {}
    for c in external:
        groups.setdefault(c.get("attributed_to") or "__UNATTRIBUTED__", []).append(c)

    print(f"[2/6] Source audit across {len(groups)} attributed source(s)...")
    verdicts: dict[str, dict] = {}
    for src, items in groups.items():
        shown = "no source credited in the draft" if src == "__UNATTRIBUTED__" else src
        print(f"      checking {len(items):>2} claim(s) against: {shown[:70]}")
        payload = {
            "subject": draft_title,
            "attributed_source": None if src == "__UNATTRIBUTED__" else src,
            "claims": [{"id": c["id"], "figure": c.get("figure"), "claim": c.get("claim")} for c in items],
        }
        out = call(
            SOURCE_SYSTEM,
            "Verify each claim below against primary sources you find yourself.\n\n"
            + json.dumps(payload, indent=2),
            search=True, label=f"source:{shown[:30]}",
        )
        if out is None:
            # An audit that could not run is a failure, never a silent pass.
            for c in items:
                verdicts[c["id"]] = {
                    "id": c["id"], "verdict": "NOT_FOUND",
                    "note": "Source audit failed to run (API error). Unchecked, therefore unverified.",
                }
            continue
        if isinstance(out, dict):
            out = out.get("results") or out.get("claims") or [out]
        for v in out:
            if isinstance(v, dict) and v.get("id"):
                verdicts[v["id"]] = v
        for c in items:
            verdicts.setdefault(c["id"], {
                "id": c["id"], "verdict": "NOT_FOUND",
                "note": "Auditor returned no verdict for this claim.",
            })

    # Internal claims are the publication's own records. No source can confirm
    # them, so they are listed for a human to check rather than counted as
    # failures. A gate that blocks on "we acknowledge within 48 hours" is a
    # gate people learn to override.
    for c in internal:
        verdicts[c["id"]] = {
            "id": c["id"], "verdict": "INTERNAL",
            "note": "Claim about this publication's own records or policy. Verify against your own files.",
        }
    return verdicts


# ---------------------------------------------------------------------------
# phase 3 — RECENCY sweep
# ---------------------------------------------------------------------------

RECENCY_SYSTEM = """You check whether a draft is out of date.

Identify every study, trial, dataset or report the draft relies on. For each,
search for the MOST RECENT readout, update, follow-up analysis or publication.
A draft citing three-year follow-up data when five-year data has been published
is wrong, even though the three-year figures were correct when written.

Return ONLY a JSON object:
{
  "studies": [
    {
      "name": "trial or study name",
      "draft_uses": "which readout the draft appears to rely on",
      "latest_known": "the most recent readout you can find, with its date",
      "status": "CURRENT" | "SUPERSEDED" | "UNKNOWN",
      "url": "source for the newer readout, or null",
      "what_changed": "which specific figures move, if superseded"
    }
  ]
}

SUPERSEDED means a newer readout exists that changes figures the draft uses.
UNKNOWN means you could not establish either way — treat as a failure, not a
pass. Do not report CURRENT merely because you found nothing; report CURRENT
only if you positively confirmed the cited readout is the latest."""


def sweep_recency(draft: str, today: str) -> dict | None:
    print("[3/6] Recency sweep...")
    out = call(
        RECENCY_SYSTEM,
        f"Today's date is {today}. Draft follows.\n\n---\n{draft}\n---",
        search=True, label="recency",
    )
    if out is None:
        return None
    studies = out.get("studies", []) if isinstance(out, dict) else []
    print(f"      {len(studies)} study/studies assessed")
    return {"studies": studies}


# ---------------------------------------------------------------------------
# phase 4 — ADVOCATE
# ---------------------------------------------------------------------------

ADVOCATE_SYSTEM = """You are the head of communications for the organisation this draft is about.
You have been sent it before publication. You are not hostile, but you are
paid to notice unfairness, and you will be quoted if you object.

Read the draft WHOLE. Your job is to find what a claim-by-claim check cannot:

  - Selective reporting. A figure that moved favourably is quoted; one that
    moved unfavourably is not. Safety data reported on the flattering measure
    only. A caveat applied to our result but not to the comparison.
  - Unsupported characterisation of anyone's conduct — ours, a regulator's,
    another publication's. "They failed to", "nobody reported", "quietly", and
    "buried" are claims about behaviour and need instances.
  - Scope error. Faulting a document for omitting something it was never
    meant to contain, or faulting one party for another's decision.
  - Framing a normal practice as suspicious without saying it is normal.
  - Any figure presented in the way that makes it sound largest.

Return ONLY a JSON array:
{
  "objection": "what you object to, in one sentence",
  "quote": "the exact sentence or phrase from the draft",
  "severity": "SERIOUS" | "MINOR",
  "why": "why it is unfair or wrong, specifically",
  "fix": "the smallest change that would satisfy you"
}

SERIOUS means you would ask for a correction and would likely get one.
MINOR means you would grumble but not escalate.

Return an empty array if you have no objection. Do not invent grievances to
appear thorough — a draft that is hard on us but accurate is not objectionable,
and saying so is more useful than a list of complaints nobody would act on."""


def advocate(draft: str) -> list[dict] | None:
    print("[4/6] Subject's advocate...")
    out = call(
        ADVOCATE_SYSTEM,
        f"Draft follows.\n\n---\n{draft}\n---",
        search=True, label="advocate",
    )
    if out is None:
        return None
    if isinstance(out, dict):
        out = out.get("objections") or out.get("results") or []
    serious = sum(1 for o in out if isinstance(o, dict) and o.get("severity") == "SERIOUS")
    print(f"      {len(out)} objection(s), {serious} serious")
    return out



# ---------------------------------------------------------------------------
# phase 5 — INFERENCE
# ---------------------------------------------------------------------------
#
# SOURCE checks whether a figure is real. ADVOCATE checks whether the draft is
# fair to its subject. Neither catches a draft in which every figure is real
# and every characterisation is fair, and the INFERENCE DRAWN FROM THEM is
# stronger than the numbers support.
#
# That is the failure mode an outside review found in issue one, and it found
# two instances a claim-by-claim check had passed:
#
#   "It is consistent with the therapy preventing five deaths in six"
#       HR 0.165 is an 84% lower HAZARD. Converting it to a count of people is
#       the exact hazard-ratio/absolute-risk conflation the same piece explains
#       correctly two paragraphs earlier.
#
#   "blinding does not eliminate the problem"
#       A criticism valid for the open-label phase 2 trial, applied to the
#       double-blind phase 3 trial whose design answers it.
#
# Both sentences are defensible in isolation. Both leave an impression the
# evidence does not carry. This role reads for that and nothing else.

INFERENCE_SYSTEM = """You are an oncology trial statistician reading a draft article
before publication. You are not checking whether its figures are real — someone
else has done that. You are checking whether the CONCLUSIONS DRAWN from them
are warranted.

Read every quantitative and methodological inference in the draft and look for:

  - A ratio converted into people. A hazard ratio is not a risk ratio and is
    not an absolute risk reduction. "HR 0.165" does NOT mean "five deaths in
    six prevented". Any sentence turning a ratio into a count of lives, or into
    an absolute percentage, is wrong unless the absolute rates are given and
    the arithmetic is shown.
  - A confidence interval described loosely. Report what the bounds mean on the
    scale they are on, in both directions.
  - A p-value quoted without its inferential framework. If the prespecified
    primary analysis was one-sided, a two-sided p-value quoted alone invites the
    reader to infer post-hoc test selection.
  - An endpoint demoted. Recurrence-free and metastasis-free survival are
    clinically meaningful outcomes, not merely surrogates for overall survival.
    Flag any phrasing implying that only mortality counts.
  - A design criticism imported across designs. A concern valid for an
    open-label trial is not automatically valid for a double-blind one. Flag any
    criticism that does not name the residual mechanism that survives the design.
  - Absence of a number reported as absence of evidence. "We do not know how
    large the effect is" and "we do not know whether it worked" are different
    claims. Flag any sentence that slides from the first to the second.
  - A relative effect quoted where the absolute one is what a reader needs, or
    an absolute benefit assumed constant across populations with different
    baseline risk.
  - The draft contradicting its own explanation. If it defines a distinction
    for the reader and then violates it, that is the most serious kind of
    finding here.

Return ONLY a JSON array:
{
  "quote": "the exact sentence or phrase from the draft",
  "problem": "what is unwarranted about the inference, in one sentence",
  "severity": "SERIOUS" | "MINOR",
  "correct_reading": "what the evidence actually supports",
  "fix": "replacement wording"
}

SERIOUS means the sentence misstates what the evidence shows, or contradicts
something the draft itself explains. MINOR means it is defensible but leaves an
impression stronger than the numbers carry.

Return an empty array if the inferences are sound. A draft that reaches a
sceptical conclusion the evidence supports is not a finding — say nothing
rather than manufacture one."""


def inference(draft: str) -> list[dict] | None:
    print("[5/6] Statistical inference...")
    out = call(
        INFERENCE_SYSTEM,
        f"Draft follows.\n\n---\n{draft}\n---",
        search=True, label="inference",
    )
    if out is None:
        return None
    if isinstance(out, dict):
        out = out.get("findings") or out.get("results") or []
    serious = sum(1 for o in out if isinstance(o, dict) and o.get("severity") == "SERIOUS")
    print(f"      {len(out)} finding(s), {serious} serious")
    return out



# ---------------------------------------------------------------------------
# phase 6 — COVERAGE
# ---------------------------------------------------------------------------
#
# Every other role reads the draft against the evidence. This one reads it
# against the best of what other people published on the same story.
#
# Issue one's framing rested on the premise that a reader meeting "49%" would
# reasonably take it for a phase 3 figure. Some readers would. A Dispatch
# reader would not: that piece attributed the 49% and 59% to the phase 2 trial
# explicitly, preserved the composite endpoints — "recurrence or death", not
# "recurrence" — and said in as many words that the companies had not released
# the phase 3 numbers. BioPharma Dive and Dermatology Times were also explicit.
#
# We had not looked. The analysis survived; the framing did not deserve to.
#
# This is the specific pull the editorial standard names: once the job is
# finding what coverage missed, there is an incentive to describe a field by
# its weakest members. The remedy is not restraint, it is a search — and a
# search is mechanisable in a way restraint is not.

COVERAGE_SYSTEM = """You are finding the BEST coverage of a story, not the worst.

You will be given a draft article (or a topic). Identify the same underlying
story and search for the most careful treatments of it published by others.

You are looking for counterexamples to the draft's implicit or explicit view of
the coverage. Search deliberately for outlets that got the hard parts right —
correct attribution of figures to the trial that produced them, composite
endpoints preserved rather than shortened, explicit statements about what has
NOT been released, appropriate caution about survival.

For each careful treatment you find, report what it got RIGHT specifically, and
what it still omitted. Both halves matter: the first tells the draft's author
that a claim of general failure is unsupportable, the second is what the draft
can legitimately add.

Then examine every statement the draft makes about the coverage, the press,
the reporting, or other outlets. Any claim that reporting missed, omitted,
failed to say, or glossed over something is CONTRADICTED if a piece you found
did say it.

Return ONLY JSON:
{
  "best_coverage": [
    {"outlet": "...", "url": "...", "got_right": "specifically what",
     "still_omitted": "what a reader still would not learn"}
  ],
  "contradictions": [
    {"quote": "the draft's exact sentence about the coverage",
     "counterexample": "outlet and what it in fact said",
     "url": "...",
     "severity": "SERIOUS" | "MINOR",
     "fix": "how to reframe so the claim is true"}
  ],
  "what_this_piece_can_add": "the layer beneath what even the careful coverage gives a reader, in one or two sentences"
}

SERIOUS means the draft asserts a failure that a piece you found did not commit.
MINOR means the characterisation is broadly right but overstated.

If the coverage really is uniformly poor on a point, say so with an empty
contradictions array — that is a finding too, and a better-supported one for
having looked. Do not manufacture counterexamples, and do not credit an outlet
for a caveat it did not actually print."""


def coverage(draft: str) -> dict | None:
    print("[6/6] Best coverage elsewhere...")
    out = call(
        COVERAGE_SYSTEM,
        f"Draft follows.\n\n---\n{draft}\n---",
        search=True, label="coverage",
    )
    if out is None:
        return None
    if isinstance(out, list):
        out = {"best_coverage": [], "contradictions": out, "what_this_piece_can_add": None}
    found = len(out.get("best_coverage") or [])
    contra = out.get("contradictions") or []
    serious = sum(1 for c in contra if isinstance(c, dict) and c.get("severity") == "SERIOUS")
    print(f"      {found} careful treatment(s) found · {len(contra)} contradiction(s), "
          f"{serious} serious")
    return out


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def render(claims, verdicts, recency, objections, inferences, cov) -> tuple[str, bool]:
    by_id = {c["id"]: c for c in claims}
    lines, failed = [], False

    internal = [v for v in verdicts.values() if v.get("verdict") == "INTERNAL"]
    bad = [v for v in verdicts.values() if v.get("verdict") not in ("VERIFIED", "INTERNAL")]
    checked = len(verdicts) - len(internal)
    lines.append("")
    lines.append("=" * 72)
    lines.append(f"CLAIMS   {checked} external · {checked - len(bad)} verified · {len(bad)} not"
                 + (f"  ({len(internal)} internal, not source-checkable)" if internal else ""))
    lines.append("=" * 72)
    for v in sorted(bad, key=lambda x: x.get("id", "")):
        c = by_id.get(v.get("id"), {})
        failed = True
        lines.append("")
        lines.append(f"  [{v.get('verdict')}] {c.get('figure') or c.get('claim') or v.get('id')}")
        if c.get("attributed_to"):
            lines.append(f"     draft credits : {c['attributed_to']}")
        if v.get("found_value"):
            lines.append(f"     source says   : {v['found_value']}")
        if v.get("actual_source"):
            lines.append(f"     really from   : {v['actual_source']}")
        if v.get("note"):
            lines.append(f"     note          : {v['note']}")
        if v.get("url"):
            lines.append(f"     checked       : {v['url']}")

    if internal:
        lines.append("")
        lines.append("  Internal claims — no external source can confirm these. Check them")
        lines.append("  against your own records before publishing:")
        for v in internal:
            c = by_id.get(v.get("id"), {})
            lines.append(f"     · {c.get('figure') or c.get('claim') or v.get('id')}")

    stale = [s for s in (recency or {}).get("studies", []) if s.get("status") != "CURRENT"]
    lines.append("")
    lines.append("=" * 72)
    lines.append(f"RECENCY  {len((recency or {}).get('studies', []))} assessed · {len(stale)} superseded or unknown")
    lines.append("=" * 72)
    for s in stale:
        failed = True
        lines.append("")
        lines.append(f"  [{s.get('status')}] {s.get('name')}")
        lines.append(f"     draft uses    : {s.get('draft_uses')}")
        lines.append(f"     latest known  : {s.get('latest_known')}")
        if s.get("what_changed"):
            lines.append(f"     changes       : {s['what_changed']}")
        if s.get("url"):
            lines.append(f"     source        : {s['url']}")

    serious = [o for o in (objections or []) if o.get("severity") == "SERIOUS"]
    lines.append("")
    lines.append("=" * 72)
    lines.append(f"FAIRNESS {len(objections or [])} objection(s) · {len(serious)} serious")
    lines.append("=" * 72)
    for o in (objections or []):
        if o.get("severity") == "SERIOUS":
            failed = True
        lines.append("")
        lines.append(f"  [{o.get('severity')}] {o.get('objection')}")
        if o.get("quote"):
            lines.append(f"     quote         : “{o['quote']}”")
        if o.get("why"):
            lines.append(f"     why           : {o['why']}")
        if o.get("fix"):
            lines.append(f"     fix           : {o['fix']}")

    serious_inf = [i for i in (inferences or []) if i.get("severity") == "SERIOUS"]
    lines.append("")
    lines.append("=" * 72)
    lines.append(f"INFERENCE {len(inferences or [])} finding(s) · {len(serious_inf)} serious")
    lines.append("=" * 72)
    for i in (inferences or []):
        if i.get("severity") == "SERIOUS":
            failed = True
        lines.append("")
        lines.append(f"  [{i.get('severity')}] {i.get('problem')}")
        if i.get("quote"):
            lines.append(f"     quote         : \u201c{i['quote']}\u201d")
        if i.get("correct_reading"):
            lines.append(f"     evidence says : {i['correct_reading']}")
        if i.get("fix"):
            lines.append(f"     fix           : {i['fix']}")

    best = (cov or {}).get("best_coverage") or []
    contra = (cov or {}).get("contradictions") or []
    serious_c = [c for c in contra if c.get("severity") == "SERIOUS"]
    lines.append("")
    lines.append("=" * 72)
    lines.append(f"COVERAGE {len(best)} careful treatment(s) elsewhere · "
                 f"{len(contra)} contradiction(s), {len(serious_c)} serious")
    lines.append("=" * 72)
    for b in best:
        lines.append("")
        lines.append(f"  {b.get('outlet', '?')}")
        if b.get("got_right"):
            lines.append(f"     got right     : {b['got_right']}")
        if b.get("still_omitted"):
            lines.append(f"     still omitted : {b['still_omitted']}")
        if b.get("url"):
            lines.append(f"     {b['url']}")
    for c in contra:
        if c.get("severity") == "SERIOUS":
            failed = True
        lines.append("")
        lines.append(f"  [{c.get('severity')}] the draft's claim about the coverage "
                     "is contradicted")
        if c.get("quote"):
            lines.append(f"     quote         : \u201c{c['quote']}\u201d")
        if c.get("counterexample"):
            lines.append(f"     but           : {c['counterexample']}")
        if c.get("url"):
            lines.append(f"     see           : {c['url']}")
        if c.get("fix"):
            lines.append(f"     fix           : {c['fix']}")
    if (cov or {}).get("what_this_piece_can_add"):
        lines.append("")
        lines.append("  What this piece can add that careful coverage does not:")
        lines.append(f"     {cov['what_this_piece_can_add']}")

    return "\n".join(lines), failed


def main():
    ap = argparse.ArgumentParser(description="Pre-publication fact-check gate.")
    ap.add_argument("draft", nargs="?", help="Path to the draft (HTML or text).")
    ap.add_argument("--report", help="Write the full JSON result here.")
    ap.add_argument("--verify", action="store_true", help="Check credentials and exit.")
    ap.add_argument("--known-errors", action="store_true",
                    help="Print the recorded error classes this gate exists to catch.")
    ap.add_argument("--today", help="Override today's date (YYYY-MM-DD) for the recency sweep.")
    ap.add_argument("--survey", metavar="TOPIC",
                    help="Run the COVERAGE role alone against a topic description, "
                         "before any draft exists. Reports who has covered the story "
                         "carefully and what a piece could add. This is the cheap "
                         "moment to learn that the coverage is better than assumed — "
                         "after drafting, the framing is already built.")
    args = ap.parse_args()

    if args.known_errors:
        if not KNOWN_ERRORS.exists():
            print(f"[ERROR] Fixture missing: {KNOWN_ERRORS}")
            sys.exit(2)
        data = json.loads(KNOWN_ERRORS.read_text())
        print(f"\n{data['what_this_is']}\n")
        # .get, not [], so an entry written without one of these fields prints
        # what it has instead of taking down the tool that reads it. A fixture
        # of recorded mistakes is a bad place for a crash on a missing key.
        for e in data["errors"]:
            print(f"  [{e.get('class', '?')}] {e.get('summary', '')}")
            print(f"      caught by : {e.get('caught_by', '—')}")
            if e.get("was"):
                print(f"      was       : {e['was']}")
            if e.get("corrected_to"):
                print(f"      corrected : {e['corrected_to']}")
            if e.get("why_it_survived"):
                print(f"      survived  : {e['why_it_survived']}")
            print()
        sys.exit(0)

    if args.verify:
        ok = bool(os.environ.get("ANTHROPIC_API_KEY"))
        print(f"ANTHROPIC_API_KEY : {'set' if ok else 'MISSING'}")
        print(f"model             : {SIGNAL_MODEL}")
        print(f"known-errors      : {'present' if KNOWN_ERRORS.exists() else 'MISSING'}")
        sys.exit(0 if ok else 2)

    if args.survey:
        cov = coverage(args.survey)
        if cov is None:
            print("\n[BLOCKED] The coverage survey did not run.")
            sys.exit(2)
        print("")
        for b in (cov.get("best_coverage") or []):
            print(f"  {b.get('outlet', '?')}")
            if b.get("got_right"):
                print(f"     got right     : {b['got_right']}")
            if b.get("still_omitted"):
                print(f"     still omitted : {b['still_omitted']}")
            if b.get("url"):
                print(f"     {b['url']}")
            print("")
        if cov.get("what_this_piece_can_add"):
            print("  What a piece could add that careful coverage does not:")
            print(f"     {cov['what_this_piece_can_add']}")
        if not (cov.get("best_coverage") or []):
            print("  No careful treatment found. That is a finding, and a "
                  "better-supported one for having looked.")
        sys.exit(0)

    if not args.draft:
        ap.error("a draft path is required (or use --verify / --known-errors / --survey)")

    warn_if_unpinned()
    path = Path(args.draft)
    draft = read_draft(path)
    today = args.today or time.strftime("%Y-%m-%d")
    print(f"\nFact-checking {path.name} ({len(draft):,} chars of prose) as of {today}\n")

    claims = extract_claims(draft)
    if claims is None:
        print("\n[BLOCKED] Could not extract claims. Nothing was checked.")
        sys.exit(2)

    verdicts = audit_sources(claims, path.stem)
    recency = sweep_recency(draft, today)
    objections = advocate(draft)
    inferences = inference(draft)
    cov = coverage(draft)

    if recency is None or objections is None or inferences is None or cov is None:
        print("\n[BLOCKED] A required check did not run. An unrun check is not a pass.")
        sys.exit(2)

    report, failed = render(claims, verdicts, recency, objections, inferences, cov)
    print(report)

    if args.report:
        Path(args.report).write_text(json.dumps({
            "draft": str(path), "checked_at": today, "model": SIGNAL_MODEL,
            "claims": claims, "verdicts": verdicts,
            "recency": recency, "objections": objections,
            "inferences": inferences, "coverage": cov,
        }, indent=2), encoding="utf-8")
        print(f"\nFull result written to {args.report}")

    print("")
    if failed:
        print("BLOCKED — resolve every item above, or record it in the piece, before publishing.")
        sys.exit(1)
    print("PASSED — every claim verified against a primary source, nothing stale, "
          "no serious objection, no unwarranted inference,")
    print("         and no claim about the coverage that a careful outlet "
          "disproves.")
    sys.exit(0)


if __name__ == "__main__":
    main()
