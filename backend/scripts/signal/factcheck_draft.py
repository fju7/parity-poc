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
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
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

# Above this many output tokens the SDK requires streaming, because its
# estimate of how long the call will take crosses ten minutes.
STREAM_ABOVE = 8192

# The model's ceiling, used for every role that reads the whole draft.
# Confirmed accepted on 2026-08-29. Raising this costs nothing until a
# role actually generates more; lowering it costs nothing but outages.
MAX_OUTPUT_TOKENS = 64000

# ---------------------------------------------------------------------------
# what a run costs
#
# Until now a gate report recorded which model ran and not a single token, so
# the cost of publishing an issue was a feeling rather than a number. It cannot
# be priced against, and it cannot be optimised: nobody could say which of the
# six roles was expensive, or whether a role that stopped finding things was
# still worth its share.
#
# Every API response carries usage. This records it, per role, and prices it.
#
# PRICES ARE A COPY, AND COPIES GO STALE. Read from
# https://platform.claude.com/docs/en/about-claude/pricing on 2026-08-28. A
# model absent from this table is reported in tokens with cost left null rather
# than guessed — a made-up number here would be worse than no number, because
# it would be used.
# ---------------------------------------------------------------------------

PRICES_CHECKED = "2026-08-28"
PRICES = {                       # US dollars per million tokens
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00,
                          "cache_write": 3.75, "cache_read": 0.30},
    "claude-opus-4-6":   {"input": 5.00, "output": 25.00,
                          "cache_write": 6.25, "cache_read": 0.50},
}
WEB_SEARCH_PER_1000 = 10.00      # charged on top of tokens, all models

USAGE = []                       # one entry per API response, in call order
_LEDGER_ISSUE = ""               # set from the draft filename before any call


def _load_spend():
    """Load spend_ledger by PATH, never by adding backend/scripts to sys.path.

    backend/scripts/signal/ is a package literally named `signal`. Putting
    backend/scripts on sys.path makes it importable as top-level `signal` and
    it shadows the standard library -- so anyio's `from signal import Signals`
    resolves to our package and every import of anthropic dies. That is what
    the first wiring of this ledger did, and it broke the gate outright:

        ImportError: cannot import name 'Signals' from 'signal'
        (backend/scripts/signal/__init__.py)

    The rest of this repo loads siblings with spec_from_file_location for
    exactly this reason. So does this.
    """
    import importlib.util
    p = Path(__file__).resolve().parents[1] / "spend_ledger.py"
    if not p.exists():
        return None
    try:
        sp = importlib.util.spec_from_file_location("spend_ledger", p)
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        return m
    except Exception:
        return None


_spend = _load_spend()
_SPEND_RECORDED = False

_unjudged = None
try:
    import importlib.util as _ilu
    _sp = _ilu.spec_from_file_location(
        "unjudged",
        Path(__file__).resolve().parents[1] / "whatholdsup" / "unjudged.py")
    _unjudged = _ilu.module_from_spec(_sp)
    _sp.loader.exec_module(_unjudged)
except Exception:
    class _NoFP:
        @staticmethod
        def fingerprints(_t):
            return {}
    _unjudged = _NoFP()


def issue_slug_for(draft_path) -> str:
    """The case slug this draft belongs to.

    WHY THIS IS NOT Path(draft).stem.

    The page is site/whatholdsup/cdk46.html and its case is issues/WHU-002-cdk46,
    so the stem works. The EMAIL is site/whatholdsup/email/issue2-cdk46.html, and
    the stem is "issue2-cdk46", which is not a slug. Two things went wrong on
    2026-09-01 because of it:

      - registry_settle was constructed with it, case_dir raised SystemExit,
        and the email gate DIED after paying for claim extraction.
      - every email gate run this project has ever done was recorded in the
        spend ledger against an issue called "issue2-cdk46", so email spend has
        never counted toward the $40 per-issue cap. The cap was measuring less
        than it was believed to measure, which is the failure the ledger exists
        to prevent.

    Resolution is by what exists on disk, never by guessing: the case
    directories are the authority.
    """
    stem = Path(draft_path).name.split(".")[0]
    cases = Path(__file__).resolve().parents[2].parent / "issues"
    try:
        names = [p.name for p in cases.glob("WHU-*-*") if p.is_dir()]
    except Exception:
        return stem
    slugs = sorted({n.split("-", 2)[2] for n in names if n.count("-") >= 2},
                   key=len, reverse=True)
    if stem in slugs:
        return stem
    for s in slugs:                       # "issue2-cdk46" -> "cdk46"
        if stem.endswith("-" + s) or stem.endswith(s):
            return s
    return stem


def _record_usage(label, response):
    """Append what one response cost us. Never raises: this is bookkeeping."""
    try:
        u = getattr(response, "usage", None)
        if u is None:
            return
        def n(attr):
            return int(getattr(u, attr, 0) or 0)
        searches = 0
        stu = getattr(u, "server_tool_use", None)
        if stu is not None:
            searches = int(getattr(stu, "web_search_requests", 0) or 0)
        entry = {
            "label": label or "call",
            "model": getattr(response, "model", SIGNAL_MODEL),
            "input": n("input_tokens"),
            "output": n("output_tokens"),
            "cache_write": n("cache_creation_input_tokens"),
            "cache_read": n("cache_read_input_tokens"),
            "web_searches": searches,
        }
        USAGE.append(entry)
        _ledger_now(entry)
    except Exception:
        pass


def _ledger_now(entry):
    """Write this one call to the spend ledger, NOW.

    WHY NOT AT THE END OF THE RUN, WHICH IS WHERE THIS USED TO BE.
    On 2026-08-31 the email gate died partway through:

        [ERROR] source:P-VERIFY poster: Your credit balance is too low to
        access the Anthropic API.

    Eleven source calls had already succeeded and been billed. The ledger wrote
    once, at the end, inside the report-writing branch -- which that run never
    reached. So the money was spent and the ledger recorded NONE of it, and the
    issue total is now understated by an amount nobody can recover.

    A ledger that only records runs that finish is not a ledger of what was
    spent. It is a ledger of what was spent successfully, which is the figure
    least likely to matter when someone is asking why the bill is high: a run
    that fails partway is exactly the run whose cost is invisible and exactly
    the run that gets retried.

    One line per API response, at the moment of the response. record() never
    raises, so this cannot break a run, and there is no aggregate left to
    double-count -- which is the other way this went wrong, when save() ran
    twice and turned $5.20 into $10.39.
    """
    if _spend is None:
        return
    try:
        # Price it through usage_summary rather than repeating the arithmetic.
        # The first draft of this function multiplied per-million rates by raw
        # token counts and would have recorded a $0.30 call as $300,000 --
        # tripping the cap on the first API response of every run. One place
        # that knows how to turn tokens into dollars, and this is not it.
        u = usage_summary([entry])["total"]
        _spend.record(script="factcheck_draft.py", role=entry["label"],
                      issue=_LEDGER_ISSUE or "", usd=u.get("usd") or 0.0,
                      input_tokens=entry["input"], output_tokens=entry["output"],
                      web_searches=entry["web_searches"],
                      note="" if u.get("priced") else "model not in the price table")
    except Exception:
        pass


def usage_summary(entries=None):
    """Totals overall and per role, priced where the model is in the table."""
    entries = USAGE if entries is None else entries
    def blank():
        return {"calls": 0, "input": 0, "output": 0, "cache_write": 0,
                "cache_read": 0, "web_searches": 0, "usd": 0.0, "priced": True}
    total, by_role, models = blank(), {}, set()
    for e in entries:
        models.add(e["model"])
        price = PRICES.get(e["model"])
        cost = None
        if price:
            cost = (e["input"] * price["input"]
                    + e["output"] * price["output"]
                    + e["cache_write"] * price["cache_write"]
                    + e["cache_read"] * price["cache_read"]) / 1_000_000.0
            cost += e["web_searches"] * WEB_SEARCH_PER_1000 / 1000.0
        for bucket in (total, by_role.setdefault(e["label"], blank())):
            bucket["calls"] += 1
            for k in ("input", "output", "cache_write", "cache_read", "web_searches"):
                bucket[k] += e[k]
            if cost is None:
                bucket["priced"] = False
            else:
                bucket["usd"] += cost
    for bucket in [total] + list(by_role.values()):
        bucket["usd"] = round(bucket["usd"], 4) if bucket["priced"] else None
    return {"total": total, "by_role": by_role,
            "models": sorted(models), "prices_checked": PRICES_CHECKED,
            "prices_source": "https://platform.claude.com/docs/en/about-claude/pricing"}

KNOWN_ERRORS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "factcheck_known_errors.json"

# Where a cut-off answer is written so it can be read.
#
# On 2026-09-03 the INFERENCE role generated 64,368 output tokens on a draft of
# 82 sentences that the advocate had just cleared in 7,614. The run blocked, the
# text was discarded, and $1.42 bought the single word "truncated". Whether the
# role found two hundred findings or repeated itself for forty minutes are
# opposite diagnoses with opposite repairs, and nothing on disk could tell them
# apart. A cap that is hit is evidence about the role or the draft; throwing it
# away is the one response that guarantees the next run learns nothing.
#
# Gitignored: the text is model output that may quote source documents at
# length, and this repository is public.
TRUNCATED_DIR = Path(__file__).resolve().parents[2] / "data" / "signal" / "truncated"


def _dump_truncated(label: str, text: str, response) -> str:
    """Write a cut-off answer to disk. Returns the path, or "" if it could not."""
    try:
        TRUNCATED_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", label or "call").strip("-") or "call"
        out = TRUNCATED_DIR / f"{stamp}-{safe}.txt"
        usage = getattr(response, "usage", None)
        head = [
            f"# label: {label}",
            f"# stop_reason: {getattr(response, 'stop_reason', None)}",
            f"# input_tokens: {getattr(usage, 'input_tokens', None)}",
            f"# output_tokens: {getattr(usage, 'output_tokens', None)}",
            f"# text_chars: {len(text)}",
            "",
        ]
        out.write_text("\n".join(head) + text)
        return str(out)
    except Exception as exc:
        print(f"  [WARN] could not save the cut-off answer: {exc}")
        return ""


_client = None


KEY_VAR = "ANTHROPIC_API_KEY"
ENVFILE = Path(__file__).resolve().parents[2] / ".env"


def _api_key() -> str:
    """The key, from the shell or from backend/.env.

    This script read os.environ and nothing else, so it ran from a shell where
    the key had been exported and failed from one where it had not — the same
    command, the same machine, two different outcomes and no way to tell which
    you were in until it exited. Configuration that lives in a file the repo
    already has should be read from that file.

    An exported value still wins, so a different key can be forced for a run.
    Only this one variable is read; the file holds two dozen secrets and none of
    the others are this script's business. The value is never printed.
    """
    key = os.environ.get(KEY_VAR)
    if key:
        return key.strip()
    if ENVFILE.exists():
        try:
            for line in ENVFILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(KEY_VAR + "=") :
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def _get_client():
    global _client
    if _client is None:
        api_key = _api_key()
        if not api_key:
            print("[ERROR] %s is not set, and is not in %s." % (KEY_VAR, ENVFILE))
            sys.exit(2)
        import anthropic
        _client = anthropic.Anthropic(api_key=api_key)
    return _client



def format_usage(entries=None):
    """The cost of the run, for the terminal.

    usage_summary() was written into the report JSON and printed nowhere. The
    number existed but nobody saw it: to learn what an issue cost you had to
    know the report had a usage key, open the JSON and read it -- and a run
    without --report recorded no cost at all. Instrumentation you have to go
    looking for does not change behaviour. This puts it under the findings,
    where the person who just spent the money is already reading.

    Roles are listed most expensive first, because the reason to show a
    breakdown is to say which role to look at. A role with more calls than
    its share of the work took retries, and retries are charged in full, so
    the call count is printed next to the money rather than hidden behind it.
    """
    u = usage_summary(entries)
    t = u["total"]
    if not t["calls"]:
        return ""
    L = []
    L.append("=" * 72)
    money = ("$%.2f" % t["usd"]) if t["priced"] else "cost unknown"
    L.append("COST     %s - %d API call(s) - %s tokens in, %s out - %d web search(es)"
             % (money, t["calls"], "{:,}".format(t["input"]),
                "{:,}".format(t["output"]), t["web_searches"]))
    L.append("=" * 72)
    L.append("")
    rows = sorted(u["by_role"].items(), key=lambda kv: -kv[1]["usd"])
    for name, r in rows:
        flag = ("  <- %d calls; the extra one(s) were retries, charged in full"
                % r["calls"]) if r["calls"] > 1 else ""
        L.append("  %-38s %7s  %s tok  %2d search%s" %
                 (name[:38],
                  ("$%.2f" % r["usd"]) if r["priced"] else "  -  ",
                  "{:>7,}".format(r["input"] + r["output"]),
                  r["web_searches"], flag))
    L.append("")
    if not t["priced"]:
        L.append("  Some calls ran on a model absent from the price table, so the")
        L.append("  total is tokens only. Models seen: %s"
                 % ", ".join(sorted(u["models"])))
    else:
        L.append("  Priced from %s," % u["prices_source"])
        L.append("  read %s. Prices go stale; a figure here older than the"
                 % u["prices_checked"])
        L.append("  page it came from is a figure to re-check.")
    return "\n".join(L)


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
    # Block-level boundaries become NEWLINES, not spaces. Until 2026-08-30 every
    # tag became a space, so `<h2>Sources</h2><p>Every figure above traces to...`
    # arrived as one run of prose reading "Sources Every figure above traces
    # to...". Any check that works on sentences then sees the heading glued to
    # the first sentence beneath it — which is how the email/page provenance
    # comparison reported a mismatch between two sentences that were identical
    # apart from the word "Sources" in front of one of them. The text is
    # unchanged; only the line breaks are new.
    body = re.sub(r"(?is)</(h[1-6]|p|li|td|th|div|blockquote|section|tr)\s*>", "\n", body)
    body = re.sub(r"(?is)<(br|hr)\s*/?>", "\n", body)
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


def _salvage_rank(value) -> int:
    """How much a salvaged JSON value looks like a role's answer.

    Parseable is not the same as wanted. A response that opens "Per the paper
    [1], here is the result:" contains a perfectly valid JSON array before the
    real one, and returning [1] is worse than returning nothing: nothing makes
    the caller retry, while [1] is silently accepted as "the role found no
    findings" and the check reports a clean pass it never performed.

    Every role in this file returns an object, or a list of objects, or an
    empty list meaning it found nothing. Nothing else is an answer.
    """
    if isinstance(value, dict):
        return 3
    if isinstance(value, list):
        if value and all(isinstance(v, dict) for v in value):
            return 3
        if not value:
            return 1          # a real "nothing found", but so is any stray []
    return 0


def _first_json_value(text: str) -> str | None:
    """Salvage a complete JSON object or array from prose.

    The earlier version scanned for the FIRST '{' or '[' in the response and
    committed to it. Models write prose before their JSON, and that prose
    routinely contains a bracket -- a citation marker, an interval like
    [0.63, 0.93], a fenced block's language tag. When it did, the salvage
    started at the wrong character, produced something unparseable, and the
    caller burned two more API calls re-asking for output it had already been
    given. On 2026-08-28 that cost three calls on one MONALEESA-2 check whose
    response ended, verbatim, in a well-formed array followed by a code fence.

    Now: strip fences, then try every candidate start and return the first that
    actually parses. Wrong guesses are free; API calls are not.
    """
    if not text:
        return None

    # ```json ... ``` and bare ``` ... ``` fences
    fenced = re.findall(r"```(?:json|JSON)?\s*(.*?)```", text, re.S)
    candidates_text = [f.strip() for f in fenced] + [text]

    found = []
    for body in candidates_text:
        for start, ch in enumerate(body):
            if ch not in "{[":
                continue
            closer = "}" if ch == "{" else "]"
            depth, in_str, esc = 0, False, False
            for i in range(start, len(body)):
                c = body[i]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                    continue
                if c == '"':
                    in_str = True
                elif c == ch:
                    depth += 1
                elif c == closer:
                    depth -= 1
                    if depth == 0:
                        chunk = body[start:i + 1]
                        try:
                            value = json.loads(chunk)
                        except json.JSONDecodeError:
                            break          # this start is wrong; try the next
                        rank = _salvage_rank(value)
                        if rank:
                            found.append((rank, chunk))
                        break
    if not found:
        return None
    found.sort(key=lambda x: -x[0])
    return found[0][1]


def enter_issue(slug: str) -> None:
    """Declare whose budget the calls that follow are spending.

    EVERY ENTRY POINT MUST CALL THIS. See call().
    """
    global _LEDGER_ISSUE
    _LEDGER_ISSUE = (slug or "").strip()


def call(system: str, user: str, *, search: bool,
         max_tokens: int = MAX_OUTPUT_TOKENS, label: str = ""):
    """One model call, optionally with web search. Returns parsed JSON or None.

    THE CAP IS ENFORCED HERE, NOT IN main().

    It used to be enforced in main(), which set _LEDGER_ISSUE from the draft
    filename and called check_cap once before starting. Every other script in
    the repository reaches the model by IMPORTING THIS MODULE and calling this
    function -- source_advocate, counterexample, premise -- so for all of them:

      * _LEDGER_ISSUE stayed "", and their spend was written to the ledger with
        no issue, landing in a bucket called "(none)";
      * check_cap was never called at all;
      * and had it been called with "", it would have compared the WHOLE
        estate's spend against one issue's cap -- spent("") meant "no filter",
        so it returned $40.57 -- and blocked every run in the repository for a
        reason unrelated to the run. Both halves of the arithmetic were wrong;
        only the fact that nothing called it kept that invisible.

    Found on 2026-09-01 by running the source advocate on issue one: two calls,
    $0.37, recorded against no issue, against no cap. The comment in main()
    fifteen hundred lines below reads "the operator agreed to that on the
    condition the cap was real."

    So the check moves to the one function every caller goes through, and it
    FAILS CLOSED: a caller that has not declared an issue cannot spend. Per
    call rather than per run, because a cap checked once at the start does not
    stop a run that crosses it in the middle.
    """
    if not _LEDGER_ISSUE:
        raise SystemExit(
            "refusing to spend: no issue declared. Call "
            "factcheck_draft.enter_issue(<slug>) before any model call, so the "
            "spend lands against that issue's cap. An unattributed call is an "
            "uncapped call.")
    if _spend is not None:
        # A per-call estimate. Deliberately not free: the point is that a run
        # near the cap stops before the call that would cross it.
        _spend.check_cap(_LEDGER_ISSUE, about_to_spend=0.75)
    client = _get_client()
    kwargs = {}
    if search:
        kwargs["tools"] = [dict(WEB_SEARCH_TOOL, max_uses=MAX_SEARCHES_PER_CALL)]

    for json_attempt in range(JSON_RETRIES + 1):
        response = None
        for attempt in range(len(BACKOFF_DELAYS) + 1):
            try:
                # The SDK refuses a non-streaming request whose estimated
                # duration exceeds ten minutes, and a large max_tokens is what
                # triggers that estimate. Raising the extraction budget for a
                # long draft therefore broke the call outright -- the fix for
                # one limit walked into another. Stream above the threshold and
                # take the final message, which carries stop_reason and usage
                # exactly as the non-streaming response does, so nothing
                # downstream can tell the difference.
                params = dict(
                    model=SIGNAL_MODEL,
                    max_tokens=max_tokens,
                    temperature=0,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    **kwargs,
                )
                if max_tokens > STREAM_ABOVE:
                    with client.messages.stream(**params) as stream:
                        response = stream.get_final_message()
                else:
                    response = client.messages.create(**params)
                _record_usage(label, response)
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

        # A response cut off at max_tokens is not a malformed answer, it is an
        # incomplete one, and the two need different handling. On 2026-08-28 the
        # extractor hit the cap on a 27,647-character draft: the array never
        # closed, the salvage recovered the first complete object inside it, and
        # extraction reported "no claims" on a draft full of them. Retrying an
        # identical call that was cut off just spends the money again, so this
        # says what happened and gives up rather than looping.
        truncated = getattr(response, "stop_reason", None) == "max_tokens"
        text = _response_text(response)
        try:
            parsed = json.loads(text)
            if truncated:
                where = _dump_truncated(label, text, response)
                print(f"  [ERROR] {label}: the answer was cut off at max_tokens "
                      f"({max_tokens}). Raise the cap for this role; the draft has "
                      f"outgrown it.")
                if where:
                    print(f"          the cut-off answer is at {where}")
                return None
            return parsed
        except json.JSONDecodeError:
            salvaged = _first_json_value(text)
            if salvaged:
                try:
                    return json.loads(salvaged)
                except json.JSONDecodeError:
                    pass
            if truncated:
                where = _dump_truncated(label, text, response)
                print(f"  [ERROR] {label}: the answer was cut off at max_tokens "
                      f"({max_tokens}) and cannot be salvaged. Raise the cap for "
                      f"this role; the draft has outgrown it.")
                if where:
                    print(f"          the cut-off answer is at {where}")
                return None
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


# ---------------------------------------------------------------------------
# what we have already learned
# ---------------------------------------------------------------------------
#
# KNOWN_ERRORS held twenty recorded error classes and was read by exactly two
# things: the --known-errors flag, which prints it for a human, and --verify,
# which checks the file exists. No role had ever been told one of them. The
# gate re-derived what to look for from nothing on every run, and it showed:
# MISSING_NUMBER_AS_MISSING_EVIDENCE was recorded on 26 August and rediscovered
# as a SERIOUS finding on 27 August, one day later, in a new draft.
#
# The risk of doing this is over-firing: a role told "here are mistakes we have
# made" may report them whether or not they are present, which inflates the
# false-positive rate in exactly the classes we care most about. That is what
# factcheck_recall.py exists to measure. Do not change this block without
# running it before and after.

# NOT a limit of 8 on the brief. It is applied twice, to two lists -- the
# classes a role is expected to catch, and (for instrument entries) that role's
# own recorded failure modes -- so a role can receive up to 16. On 2026-08-28
# SOURCE was receiving 12, ADVOCATE and INFERENCE 9 each, while every comment
# here said 8. Left as it is, because changing the brief is the one thing this
# block says not to do without a measurement, and the measurement of 2026-08-28
# could not resolve a change this small: see RECALL_MEASUREMENT_UNDERPOWERED.
# The comment is corrected; the behaviour is not, yet.
#
# Two other things that printing the brief made visible and neither has been
# changed for the same reason:
#   - DROPPED appears twice in SOURCE's brief, because two recorded entries
#     share that class name. The role is told one class twice, which weights it
#     against every other class, and nobody chose that.
#   - COVERAGE received no recorded classes at all until 2026-08-28. It has one
#     now. A role with an empty learning record is not being taught anything.
RECALL_BRIEF_LIMIT = 8          # per list, not per brief


def recall_brief(role: str) -> str:
    """The recorded error classes this role is expected to catch, as prompt text."""
    if not KNOWN_ERRORS.exists():
        return ""
    try:
        data = json.loads(KNOWN_ERRORS.read_text())
    except Exception as exc:
        print(f"[WARN] Could not read {KNOWN_ERRORS.name}: {exc}. "
              f"{role} runs without the recorded classes.")
        return ""

    mine, mine_own = [], []
    for e in data.get("errors", []):
        # A retracted entry is a mistake about a mistake. Priming a role with
        # one would teach it to find something that was never there.
        summary = e.get("summary") or ""
        if summary.startswith("RETRACTED"):
            continue
        kind = e.get("kind", "draft")
        if kind == "process":
            # A failure of what was checked, or when. No role can find one of
            # these by reading a draft, and listing it would send them looking.
            continue
        caught = e.get("caught_by") or ""
        shipped = "nothing" in caught
        entry = (e.get("class", "?"), summary, e.get("was") or "", shipped)
        if kind == "instrument":
            if role in (e.get("owned_by") or ""):
                mine_own.append(entry)
        # Own the classes this role caught before, and every class that reached
        # a reader uncaught — those belong to whichever role reads at that
        # resolution, and being unowned is how they got out.
        elif role in caught or (shipped and role in ("SOURCE", "ADVOCATE", "INFERENCE")):
            mine.append(entry)
    if not mine and not mine_own:
        return ""

    mine.sort(key=lambda x: (not x[3], x[0]))       # errors that shipped first
    lines = []
    if mine:
        lines += [
            "",
            "RECORDED MISTAKES IN EARLIER DRAFTS.",
            "Real errors this publication has made, kept so the same kind is not",
            "made twice. They are NOT present in the draft you are reading unless",
            "you find them there. Reporting one that is not there is itself an",
            "error, and a costly one: it sends an editor to rewrite a correct",
            "sentence, which is how new errors get introduced. Use them as a",
            "checklist of what to look for, never as a list of what to report.",
            "Where one IS present, name the class.",
            "",
        ]
        for cls, summary, was, shipped in mine[:RECALL_BRIEF_LIMIT]:
            lines.append(f"- {cls}{' (this one reached readers)' if shipped else ''}: {summary}")
            if was:
                lines.append(f"    it read: \"{was[:160]}\"")
    if mine_own:
        lines += [
            "",
            "YOUR OWN RECORDED FAILURE MODES.",
            "Not errors in any draft — ways this check has itself returned a wrong",
            "answer. Read them as instructions about your own output.",
            "",
        ]
        for cls, summary, _was, _shipped in mine_own[:RECALL_BRIEF_LIMIT]:
            lines.append(f"- {cls}: {summary}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# how many times one draft may be gated
# ---------------------------------------------------------------------------
#
# Issue two was gated eighteen times on the assessment and six on the email, at
# $66.76. Roughly $27 of that bought nothing: repairs chasing repairs, phrasing
# notes, two runs that failed mid-way, and one run that put a false claim INTO
# the page. The comment on the incremental-re-run block below already described
# the trap -- "the unverified count across three passes went 7, 6, 13, the rise
# almost entirely claims introduced while fixing earlier findings" -- and it was
# read and then walked into anyway, which is the argument for a limit in code
# rather than a limit in judgment.
#
# The shape that works is: gate a complete draft, adjudicate everything in one
# pass, make every edit at once, gate once to confirm. Two runs. Then the
# outside review, which is where the expensive findings actually came from --
# all three of issue two's review findings survived fourteen gate runs, and the
# single worst error in the piece was GENERATED by the gate and could not be
# caught by running it again. One more run after the review closes the cycle.
#
# A cycle is reset by --new-cycle, which is what the outside review step does.
# --past-cap exists because a rule with no override gets worked around, and a
# reason is required so that going past it is a decision on the record.

RUNS_PER_CYCLE = 2

# THE WHOLE BUDGET FOR AN ISSUE, ACROSS EVERY CYCLE.
#
# Set by the editor on 2026-09-03: two runs, then the outside review, then one
# run to close it. Three. "If we are still finding mistakes that need to be
# corrected after those three, the answer is not to run more gates but revise
# the drafting and editing process."
#
# It needed a number because the per-cycle cap was not a budget. --new-cycle
# reset the counter, required no reason, and DELETED the run list, so there was
# no record anywhere of how many times an issue had been gated. Issue one shows
# the result: its runs file said "cycle 5, runs: []" while the spend ledger
# showed SEVEN gate runs in thirty hours for $30.53.
#
# Both of those cycles were opened by me. One followed a real outside review.
# The other did not: it was a one-sentence re-read that the cap would have
# stopped, and --new-cycle was the way past it that asks for nothing.
# --past-cap demands a written reason on the record; --new-cycle demanded
# silence. Given a priced override and a free one, the free one gets used, and
# the accountability was on the branch nobody had to take.
RUNS_PER_ISSUE = 3


def _cycle_path(report: str) -> Path:
    return Path(report + ".runs.json")


def cycle_state(report: str) -> dict:
    p = _cycle_path(report)
    if not p.exists():
        return {"cycle": 1, "runs": [], "reason": None}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {"cycle": 1, "runs": [], "reason": None}


def all_runs(st: dict) -> list[dict]:
    """Every run this draft has had, in every cycle.

    st["runs"] is the current cycle. st["closed"] is what earlier cycles held
    before --new-cycle reset the counter, kept rather than dropped: a budget
    counted per cycle is not a budget, because the thing that resets the cycle
    is a flag.
    """
    return list(st.get("closed") or []) + list(st.get("runs") or [])


def cycle_record(report: str, sha: str, past_cap: str | None) -> None:
    st = cycle_state(report)
    st["runs"].append({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                       "sha": sha, "past_cap": past_cap,
                       "cycle": st.get("cycle", 1)})
    _cycle_path(report).write_text(json.dumps(st, indent=2), encoding="utf-8")


def cycle_check(report: str, past_cap: str | None, new_cycle: bool) -> bool:
    """False means stop. Prints why."""
    if not report:
        return True
    p = _cycle_path(report)
    st = cycle_state(report)
    lifetime = len(all_runs(st))
    if new_cycle:
        # A NEW CYCLE KEEPS THE OLD RUNS. It used to drop them, which made the
        # per-cycle cap unenforceable by the one flag that asks for nothing.
        st = {"cycle": st.get("cycle", 1) + 1,
              "runs": [],
              "closed": all_runs(st),
              "reason": None}
        if lifetime >= RUNS_PER_ISSUE and not past_cap:
            print()
            print("  STOP. This draft has been gated %d times across %d cycle(s)."
                  % (lifetime, st["cycle"] - 1))
            print("  The budget for an issue is %d: two runs, the outside review, one"
                  % RUNS_PER_ISSUE)
            print("  run to close it. Opening another cycle does not create more.")
            print()
            print("  The editor set that number on 2026-09-03: \"If we are still")
            print("  finding mistakes that need to be corrected after those three, the")
            print("  answer is not to run more gates but revise the drafting and")
            print("  editing process.\" So the next move is a change to how the draft")
            print("  is written, not another pass over what was written.")
            print()
            print("  If this cycle really does follow an outside review that found")
            print("  something a run must confirm, say so on the record:")
            print("    --past-cap \"what the review found and why a run settles it\"")
            print()
            return False
        p.write_text(json.dumps(st, indent=2), encoding="utf-8")
        print("  Cycle %d. The run counter is reset; %d earlier run(s) kept."
              % (st["cycle"], len(st["closed"])))
        return True
    used = len(st.get("runs", []))
    if lifetime >= RUNS_PER_ISSUE and not past_cap:
        print()
        print("  STOP. This draft has been gated %d times, which is the whole budget."
              % lifetime)
        print("  Two runs, the outside review, one run to close it. That is three.")
        print()
        print("  What is left is not another pass. It is the drafting change that")
        print("  stops the next issue needing one.")
        print()
        print("    --past-cap \"why this run is different from the last %d\"" % lifetime)
        print()
        return False
    if used < RUNS_PER_CYCLE or past_cap:
        if past_cap:
            print("  Past the cap of %d, on the record: %s" % (RUNS_PER_CYCLE, past_cap))
        return True
    print()
    print("  STOP. This draft has been gated %d times in cycle %d, which is the cap." % (used, st["cycle"]))
    print()
    print("  The cap is %d because runs past it stop paying. On issue two, gate runs" % RUNS_PER_CYCLE)
    print("  11 onwards returned phrasing notes and rounding false positives, one run")
    print("  introduced an error into the page, and every finding that mattered after")
    print("  run 10 came from a human reading rather than from another pass.")
    print()
    print("  What to do instead, in order:")
    print("    1. Adjudicate what the last run found -- all of it, in one pass.")
    print("    2. Make every edit at once. Re-running between edits is the trap.")
    print("    3. Send it to outside review. That is where the findings are.")
    print("    4. After the review: --new-cycle, then one run.")
    print()
    print("  If you are certain another run is warranted:")
    print("    --past-cap \"why this run is different from the last two\"")
    print()
    return False


# ---------------------------------------------------------------------------
# incremental re-runs
# ---------------------------------------------------------------------------
#
# A three-word fix invalidates the report, because the guard is keyed on the
# content hash — correctly: publishing text nobody checked is the failure that
# started all of this. But it meant a full six-role sweep of a 26,000-character
# page to re-clear one sentence, and the sweep is a sampler: it draws a fresh
# handful of objections from a large space every time, so each run finds new
# things whether or not the draft got worse. That is what an endless loop feels
# like from the inside.
#
# The fix is to re-check what changed and carry forward what did not, saying so
# in the report. The roles split cleanly by what they actually depend on:
#
#   SOURCE    depends on the claim. A claim whose sentence is untouched has the
#             same verdict it had, and re-searching it is spend without signal.
#             Failed verdicts are always re-run — those are the ones we edited
#             the draft to fix.
#   RECENCY   depends on the literature, not our wording. Nothing we write
#             makes a five-year readout appear. Time-based, not edit-based.
#   COVERAGE  depends on what other people published. Same.
#   ADVOCATE  read the whole document and are where lede-versus-body drift
#   INFERENCE surfaces. These ALWAYS re-run: scoping them to the diff is what
#             would let a fixed sentence break a distant one, which is the
#             exact failure that put "both endpoints" in one file and not the
#             other.

RECENCY_FRESH_DAYS = 7
COVERAGE_FRESH_DAYS = 14


def _days_since(datestr: str | None) -> float:
    if not datestr:
        return 1e9
    try:
        then = datetime.strptime(datestr[:10], "%Y-%m-%d")
    except Exception:
        return 1e9
    return (datetime.now() - then).days


def load_prior(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        print(f"[WARN] --since {p} does not exist. Running everything.")
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as exc:
        print(f"[WARN] --since {p} unreadable ({exc}). Running everything.")
        return {}


def carry_verdicts(claims: list[dict], prior: dict) -> tuple[list[dict], dict, int]:
    """Split claims into (needs checking, carried verdicts, carried count).

    Keyed on the FIGURE and the source the draft credits, not on the claim
    sentence. The first version matched sentences and carried 12 of 43 where an
    offline test predicted 30: the extractor is a model, it rewords the claim it
    writes on every run, and matching prose across runs of a paraphraser matches
    almost nothing. The figure is lifted from the draft, so it is a string the
    draft owns and the extractor only copies.

    A figure can legitimately appear in two claims, so a key that is ambiguous
    on either side is not carried — it falls through to a fresh check, which is
    the safe direction. Claim text is kept as a fallback for claims with no
    figure at all.
    """
    def key(c):
        fig = _norm(c.get("figure") or "")
        src = _norm(c.get("attributed_to") or "")
        return (fig, src) if fig else None

    old_claims = {c["id"]: c for c in prior.get("claims", [])}
    old_verdicts = prior.get("verdicts") or {}

    by_key, by_text, seen = {}, {}, set()
    for cid, v in old_verdicts.items():
        c = old_claims.get(cid)
        if not c:
            continue
        k = key(c)
        if k:
            # Ambiguous on the old side: remember it, then refuse it.
            if k in by_key:
                seen.add(k)
            by_key[k] = v
        by_text[_norm(c.get("claim", ""))] = v
    for k in seen:
        by_key.pop(k, None)

    new_keys = {}
    for c in claims:
        k = key(c)
        if k:
            new_keys[k] = new_keys.get(k, 0) + 1

    todo, carried = [], {}
    for c in claims:
        k = key(c)
        v = None
        if k and new_keys.get(k) == 1:          # unambiguous on the new side too
            v = by_key.get(k)
        if v is None:
            v = by_text.get(_norm(c.get("claim", "")))
        if v and v.get("verdict") == "VERIFIED":
            carried[c["id"]] = {**v, "id": c["id"],
                                "carried_from": prior.get("sha256", "")[:16]}
        else:
            todo.append(c)
    return todo, carried, len(carried)


def read_budget(_draft: str = "") -> int:
    """Output tokens for a role that reads the whole draft and writes findings.

    A constant, and a large one, because MAX_TOKENS IS A CEILING AND NOT A
    RESERVATION. Billing is on tokens actually generated: a call made with a
    cap of 64,000 that answers in 400 costs the same as one capped at 500 that
    answers in 400. Verified on 2026-08-29 -- a request at max_tokens=64000
    returned four tokens and was billed for four. There is therefore no saving
    anywhere in this file that a low cap was buying, and never was.

    What the low cap bought instead was three separate failures in one day, on
    a draft that grew while the gate improved it:

      * extraction cut off at 27,647 characters; reported "no claims"
      * the raise for extraction pushed max_tokens past the SDK's ten-minute
        estimate and broke the call a different way, needing streaming
      * INFERENCE cut off at 33,000 characters, four runs later, on the same
        constant nobody had grepped for

    Each was fixed at the site of the failure and each fix was a formula with a
    new ceiling in it, which is the same bug with a longer fuse. The ceiling is
    now the model's, not ours. If a role ever hits this, the draft has a real
    problem and the truncation detector in call() will say so rather than
    returning silence that reads like a clean check.
    """
    return MAX_OUTPUT_TOKENS


def extract_claims(draft: str) -> list[dict] | None:
    """Every checkable claim in the draft.

    The output budget scales with the draft. A fixed 8,000 tokens was enough
    for an 8,000-character page and not for a 27,000-character one: the answer
    was cut off mid-array and the run blocked on "no claims" for a draft that
    had fifty-odd. The cap now tracks the input, because the one role whose
    output grows with the document should not be the one with a constant
    budget. Roughly one claim per 500 characters, a few hundred tokens each.
    """
    print("[1/6] Extracting checkable claims...")
    budget = read_budget(draft)
    out = call(
        EXTRACT_SYSTEM,
        f"Draft follows.\n\n---\n{draft}\n---",
        search=False, label="extract", max_tokens=budget,
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
NOT_FOUND    you could not reach a source containing it. This is a statement about
             what you could reach, NOT about whether the thing exists. Say so in
             plain words, and give the closest URL you did reach so a human can
             open it. On 2026-08-27 this verdict was returned for a page that
             existed, was dated, and contained the claim verbatim — another role
             in the same run had already cited it with its URL.
NOT_FOUND    you could not find this figure in any source you could reach.

NOT_FOUND is the correct verdict when you cannot reach the source. Do not
guess, and do not mark something VERIFIED because it sounds right or because
you remember it. If you could not open the document, say NOT_FOUND and explain
in the note. An unverifiable claim is a failure, not a pass.

MATCH THE ANALYSIS, NOT JUST THE TRIAL. A trial reports the same measures again
at each readout, and the numbers change. Before calling a figure wrong, check
that the source you found describes the SAME analysis the draft is describing —
same data cut, same follow-up, same timepoint. On this publication that check
has failed three times: adverse-event rates from a five-year readout were
reported as wrong against the primary analysis and then against the three-year
update, and a confidence interval was called a conflation of timepoints when
both bounds were the five-year ones. The figures returned each time were real.
They were from the wrong readout.

If the draft's figure and your source's figure differ, say which analysis each
belongs to. If you cannot establish that, the verdict is NOT_FOUND — you could
not reach the right source — and not WRONG_VALUE.

QUOTATIONS. When the draft puts words in quotation marks, find THAT sentence
before judging it. A release often says a similar thing twice in different
words; matching the paraphrase and reporting the quotation as invented is the
worst error available to you, because misquotation is the accusation this
publication can least afford to have made falsely.
"""


def audit_sources(claims: list[dict], draft_title: str,
                  settler=None) -> dict[str, dict]:
    external = [c for c in claims if c.get("scope", "external") != "internal"]
    internal = [c for c in claims if c.get("scope") == "internal"]
    if internal:
        print(f"      {len(internal)} internal claim(s) recorded, not source-checked")

    groups: dict[str, list[dict]] = {}
    for c in external:
        groups.setdefault(c.get("attributed_to") or "__UNATTRIBUTED__", []).append(c)

    print(f"[2/6] Source audit across {len(groups)} attributed source(s)...")
    verdicts: dict[str, dict] = {}

    # ASK THE REGISTRY BEFORE ASKING A MODEL.
    #
    # The 31 August run spent $0.87 and nine web searches on source:HARMONIA to
    # establish a start date, a status and an enrolment count -- three
    # structured fields the API returns in under a second, and which the board
    # had already confirmed before the run began. The deterministic tier was
    # overturning the model AFTER the spend.
    #
    # A settled claim is not a skipped claim: it gets a verdict, a reason and
    # the record behind it, and appears in the report as VERIFIED. A claim that
    # vanished because it was cheap to settle would make the report say less
    # than it knows.
    if settler is not None:
        if getattr(settler, "error", None):
            print(f"      [WARN] registry pre-check did not run, so nothing was "
                  f"settled before the model: {settler.error}")
        else:
            settled_n = 0
            for src, items in list(groups.items()):
                keep = []
                for c in items:
                    # Guarded at the CALL SITE as well as inside the settler.
                    # This is a cost optimisation sitting in the middle of the
                    # only check that protects a reader; if it throws, the
                    # correct outcome is that the claim goes to the model and
                    # the run continues, never that the run dies. On
                    # 2026-09-01 it died -- a SystemExit from a case-directory
                    # lookup, after the run had already paid for extraction.
                    try:
                        why = settler.settles(c.get("figure") or "",
                                              c.get("claim") or "",
                                              c.get("attributed_to") or "")
                    except KeyboardInterrupt:
                        raise
                    except BaseException as _e:      # noqa: BLE001
                        print("      [WARN] registry pre-check failed on %s "
                              "(%s: %s) — sending it to the model"
                              % (c.get("id"), type(_e).__name__, _e))
                        why = None
                    if not why:
                        keep.append(c)
                        continue
                    verdicts[c["id"]] = {
                        "id": c["id"], "verdict": "VERIFIED",
                        "found_value": c.get("figure") or c.get("claim"),
                        "actual_source": "ClinicalTrials.gov, read as structured "
                                         "data by registry_settle before the "
                                         "source audit",
                        "note": why + ". Settled deterministically; no model was "
                                      "asked and nothing was spent on it.",
                        "settled_by": "registry",
                    }
                    settled_n += 1
                if keep:
                    groups[src] = keep
                else:
                    del groups[src]
            if settled_n:
                print(f"      {settled_n} claim(s) settled at the registry for "
                      f"nothing, before any model call "
                      f"({len(groups)} source(s) left to check)")

    for src, items in groups.items():
        shown = "no source credited in the draft" if src == "__UNATTRIBUTED__" else src
        print(f"      checking {len(items):>2} claim(s) against: {shown[:70]}")
        payload = {
            "subject": draft_title,
            "attributed_source": None if src == "__UNATTRIBUTED__" else src,
            "claims": [{"id": c["id"], "figure": c.get("figure"), "claim": c.get("claim")} for c in items],
        }
        out = call(
            SOURCE_SYSTEM + recall_brief("SOURCE"),
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

Check the FIGURES, not just the readouts. On a seeded test draft this check
assessed nine studies and reported none superseded, while the draft quoted
three-year hazard-ratio intervals for a trial whose five-year data it also
cited by name. A newer readout existing is not the question; the question is
whether every number the draft prints is the number that readout gives. Pull
the specific hazard ratios, intervals, event rates and percentages out of the
draft and compare each against the latest publication. A draft that names the
five-year data and quotes the three-year interval is SUPERSEDED.

SUPERSEDED means a newer readout exists that changes figures the draft uses.
UNKNOWN means you could not establish either way — treat as a failure, not a
pass. Do not report CURRENT merely because you found nothing; report CURRENT
only if you positively confirmed the cited readout is the latest."""


def sweep_recency(draft: str, today: str) -> dict | None:
    print("[3/6] Recency sweep...")
    out = call(
        RECENCY_SYSTEM + recall_brief("RECENCY"),
        f"Today's date is {today}. Draft follows.\n\n---\n{draft}\n---",
        search=True, label="recency", max_tokens=read_budget(draft),
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

BEFORE YOU RETURN, DO THIS SWEEP.
List every party the draft characterises other than us — news outlets,
journals, regulators, other companies, "the coverage", "most reporting". For
each, find the sentence that characterises them and ask what evidence the
draft offers. An accusation against a third party costs us nothing, so you
will not feel it the way you feel one against us; check it anyway. On a seeded
test draft this role read past "they are being used to fill the hole where the
Phase 3's numbers should be, mostly without saying so" — an accusation against
named outlets, unevidenced and untrue — because it was not about us. That is
the objection a wronged third party would make, and nobody else here is
looking for it.

REPORT EVERY INSTANCE, NOT EVERY CLASS. If the same fault appears in three
sentences, return three objections. On the same test draft one instance of a
class was found and a second instance of it, four paragraphs later, was not —
which is how a fault gets fixed in one place and published in another.

Return an empty array if you have no objection. Do not invent grievances to
appear thorough — a draft that is hard on us but accurate is not objectionable,
and saying so is more useful than a list of complaints nobody would act on.

CLASSIFY EVERY FINDING. Add a "class" field, one of four values. The test is
one question: **if a reader found this after publication, would we have to
print a correction?**

  "FACT"          A figure, date, name, endpoint, or attribution that a source
                  contradicts. We would have to correct it.
  "CONTRADICTION" The piece disagrees with itself — the summary says one thing
                  and the body another, or it states a rule and then breaks it.
                  We would have to correct it.
  "THIRD_PARTY"   A claim about what someone else did, said, failed to do, or
                  withheld, offered without evidence. We would have to correct
                  it, and they would be right to ask.
  "CALIBRATION"   Everything else. A phrasing that could be sharper, an
                  ordering that could be fairer, a word carrying more weight
                  than it should, an omission you would have handled
                  differently. Real, worth saying, and not a correction.

CALIBRATION findings do not block publication. They are recorded and the piece
publishes. This is deliberate: there is always a defensible alternative
phrasing, so a check that blocks on phrasing never stops. Do not reach for a
blocking class to make a finding count — a CALIBRATION finding you argue well
is more useful than a FACT label that does not survive the question above.
"""


def advocate(draft: str) -> list[dict] | None:
    print("[4/6] Subject's advocate...")
    out = call(
        ADVOCATE_SYSTEM + recall_brief("ADVOCATE"),
        f"Draft follows.\n\n---\n{draft}\n---",
        search=True, label="advocate", max_tokens=read_budget(draft),
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

    JUDGE THE SENTENCE, NOT THE PARAGRAPH. A nearby qualification does not
    repair a sentence a reader will quote on its own. "The announcement reports
    no results" followed by "it does describe the trial" is still a sentence
    that says there are no results, and it is the one that will be remembered
    and repeated. On 2026-08-27 this exact construction appeared three times in
    a live piece — "reports no Phase 3 results", "has published nothing", "the
    quantitative content is nil" — and was passed by this check because each
    was qualified somewhere nearby. All three were wrong: the announcement
    reported that the trial met its prespecified endpoints, which is a result.
    What it did not report was any NUMBER.

    The repair is usually one word. Ask of every such sentence: is the missing
    thing evidence, or magnitude? If magnitude, say so in the sentence itself.
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
rather than manufacture one.

REPORT EVERY INSTANCE, NOT EVERY CLASS. If the same fault appears in three
sentences, return three findings. On a seeded test draft this role found one
instance of a class and missed a second instance of the same class four
paragraphs later, which is how a fault gets fixed in one place and published
in another.

CLASSIFY EVERY FINDING. Add a "class" field, one of four values. The test is
one question: **if a reader found this after publication, would we have to
print a correction?**

  "FACT"          A figure, date, name, endpoint, or attribution that a source
                  contradicts. We would have to correct it.
  "CONTRADICTION" The piece disagrees with itself — the summary says one thing
                  and the body another, or it states a rule and then breaks it.
                  We would have to correct it.
  "THIRD_PARTY"   A claim about what someone else did, said, failed to do, or
                  withheld, offered without evidence. We would have to correct
                  it, and they would be right to ask.
  "CALIBRATION"   Everything else. A phrasing that could be sharper, an
                  ordering that could be fairer, a word carrying more weight
                  than it should, an omission you would have handled
                  differently. Real, worth saying, and not a correction.

CALIBRATION findings do not block publication. They are recorded and the piece
publishes. This is deliberate: there is always a defensible alternative
phrasing, so a check that blocks on phrasing never stops. Do not reach for a
blocking class to make a finding count — a CALIBRATION finding you argue well
is more useful than a FACT label that does not survive the question above.
"""


def inference(draft: str) -> list[dict] | None:
    print("[5/6] Statistical inference...")
    out = call(
        INFERENCE_SYSTEM + recall_brief("INFERENCE"),
        f"Draft follows.\n\n---\n{draft}\n---",
        search=True, label="inference", max_tokens=read_budget(draft),
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
        search=True, label="coverage", max_tokens=read_budget(draft),
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
# adjudication — which findings have already been read and decided
# ---------------------------------------------------------------------------
#
# The gate is a nondeterministic instrument reading a long document. It will
# never return zero twice running, and waiting for zero means editing forever
# while each pass adds new claims that can fail. On 2026-08-27 the unverified
# count across three passes of the same piece went 7, 6, 13 — the rise was
# almost entirely claims introduced while fixing earlier findings.
#
# stability_sweep already solved this shape of problem for consensus drift:
# it reports "0 new, 5 already decided" against label_decisions.json, so a
# repeat check that repeats itself is recognisable as such. Without the same
# thing here, every run re-presents judgment calls somebody already made, and
# they are indistinguishable in the output from genuinely new problems.
#
# A decision is keyed on the QUOTE, because that is the text in the draft the
# finding is about. Change the sentence and the decision no longer applies,
# which is correct: it was a decision about that sentence.

DECISIONS = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "draft_decisions.json"


EDGE = " \t\n\"'`.,;:!?()[]{}-"


def _norm(text: str) -> str:
    """Compare quotes without being defeated by smart quotes or whitespace."""
    t = (text or "").lower()
    for a, b in (("\u201c", '"'), ("\u201d", '"'), ("\u2018", "'"), ("\u2019", "'"),
                 ("\u2014", "-"), ("\u2013", "-"), ("\u2026", "...")):
        t = t.replace(a, b)
    # Edge punctuation is stripped because one run quoted a sentence with its
    # closing full stop and the next quoted the same sentence without it, and
    # that one character was enough to report a recorded decision as NEW.
    return " ".join(t.split()).strip(EDGE)


def load_decisions(path: Path, draft: str) -> dict:
    """{(role, normalised quote): decision} for this draft."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception as exc:
        print(f"[WARN] Could not read {path}: {exc}. Every finding will read as NEW.")
        return {}
    out = {}
    for d in data.get("decisions", []):
        if Path(d.get("draft", "")).name != Path(draft).name:
            continue
        out[(d.get("role", ""), _norm(d.get("quote", "")))] = d
    return out


# The gate chooses the span it quotes afresh on every run. The same objection
# came back once as a whole sentence and once as a seven-word clause inside
# that sentence, and a recorded decision differed from the reported quote by a
# single trailing full stop — so exact keying reported both as NEW and the
# adjudication record read as empty on a run where it was not. Containment is
# the relation that actually holds between two spans of one sentence, so try
# the exact key first and fall back to it.
#
# MIN_OVERLAP stops a short quote from swallowing findings it was never about.
# Edit the sentence and neither string contains the other, which is still the
# property the whole record depends on: a decision was about that sentence.
MIN_OVERLAP = 40


def orphaned(decisions: dict, draft: str) -> list[tuple[str, str]]:
    """Decisions whose sentence is no longer anywhere in the draft.

    The fixture says a dead decision is dead weight rather than a record, but
    nothing was checking, and a hand-rolled check that missed one HTML entity
    deleted a live decision. This uses the same normalisation the matcher does,
    against the prose the roles actually see, and only reports — removing a
    decision is a human's call.

    SOURCE decisions are skipped: they are keyed on the claim sentence the
    extractor writes, which is a paraphrase and is not expected to appear in
    the draft verbatim.
    """
    body = _norm(draft)
    out = []
    for (role, q), d in decisions.items():
        if role == "SOURCE" or not q:
            continue
        if q not in body:
            out.append((role, d.get("quote", q)))
    return out


def classify(role: str, quote: str, severity: str,
             decisions: dict) -> tuple[str, dict | None, str]:
    """NEW, ADJUDICATED or STALE, plus how the decision was matched.

    STALE means a decision exists but the severity has moved since it was made.
    A judgment accepted as MINOR is not thereby accepted as SERIOUS, and the
    difference has to reach a human rather than being absorbed silently.
    """
    q = _norm(quote)
    d, how = decisions.get((role, q)), "exact"
    if not d:
        for (r, dq), cand in decisions.items():
            if r != role or min(len(dq), len(q)) < MIN_OVERLAP:
                continue
            if dq in q or q in dq:
                d, how = cand, "overlap"
                break
    if not d:
        return "NEW", None, ""
    if how == "overlap":
        # Same sentence, possibly a different fault in it. Comparing severities
        # across two objections that are not the same objection would be
        # meaningless, so this never reports STALE — it reports itself and
        # lets a human decide whether it is the finding already accepted.
        return "OVERLAP", d, how
    if (d.get("severity") or "").upper() != (severity or "").upper():
        return "STALE", d, how
    return "ADJUDICATED", d, how


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def render(claims, verdicts, recency, objections, inferences, cov,
           decisions=None) -> tuple[str, bool]:
    decisions = decisions or {}
    adjudicated = []   # findings already read and accepted
    # NOT named 'stale': render() already binds that name to the recency
    # studies further down, and the later assignment silently replaced this
    # list with a list of dicts. Unpacking those yielded their keys, six of
    # them, and the whole run died AFTER every API call had been spent.
    moved_since = []         # decided at one severity, now reported at another
    by_id = {c["id"]: c for c in claims}
    lines, failed = [], False

    internal = [v for v in verdicts.values() if v.get("verdict") == "INTERNAL"]
    bad = [v for v in verdicts.values() if v.get("verdict") not in ("VERIFIED", "INTERNAL")]
    checked = len(verdicts) - len(internal)
    # Header last: how many of the failures are already decided is not known
    # until the loop has run, and a header that says "5 not" above an empty
    # list reads as truncation rather than as adjudication.
    head, lines = lines, []
    # The claims block had no adjudication path at all: a figure the source role
    # cannot reach, or reads without the clause that attributes it, blocked
    # every run for ever. It is keyed on the claim sentence rather than the
    # figure, because the figure comes back as "49%" one run and "49% and 59%"
    # the next, and because a sentence is long enough for the overlap match.
    for v in sorted(bad, key=lambda x: x.get("id", "")):
        c = by_id.get(v.get("id"), {})
        kind, dec, how = classify("SOURCE", c.get("claim", ""), v.get("verdict", ""), decisions)
        if kind == "ADJUDICATED":
            adjudicated.append(("SOURCE", v.get("verdict"),
                                (c.get("figure") or c.get("claim") or "")[:90], dec, how))
            continue
        if kind == "STALE":
            moved_since.append(("SOURCE", v.get("verdict"),
                                (c.get("figure") or c.get("claim") or "")[:90], dec, how))
        failed = True
        lines.append("")
        lines.append(f"  [{kind} · {v.get('verdict')}] "
                     f"{c.get('figure') or c.get('claim') or v.get('id')}")
        if kind == "OVERLAP":
            lines.append(f"     already decided about this claim, on other "
                         f"grounds: {dec.get('reason', '')[:150]}")
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

    settled = sum(1 for a in adjudicated if a[0] == "SOURCE")
    head.append("")
    head.append("=" * 72)
    head.append(f"CLAIMS   {checked} external · {checked - len(bad)} verified · {len(bad)} not"
                + (f", {settled} already decided" if settled else "")
                + (f"  ({len(internal)} internal, not source-checkable)" if internal else ""))
    head.append("=" * 72)
    lines = head + lines

    unreached = [v for v in bad if v.get("verdict") == "NOT_FOUND"]
    if unreached:
        lines.append("")
        lines.append("  A NOT_FOUND means we could not REACH a source, not that none exists.")
        lines.append("  Open any URL above before treating one as a finding — and check")
        lines.append("  whether COVERAGE cited the same page, because it often has the link.")

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
    if stale:
        lines.append("")
        lines.append("  " + "!" * 68)
        lines.append("  EVERY FINDING BELOW IS A CLAIM ABOUT SOMEBODY ELSE'S DOCUMENT.")
        lines.append("  This role has not opened that document. It has read search results")
        lines.append("  about it. Do not put any of this on the page until you have opened")
        lines.append("  the source and read the sentence yourself.")
        lines.append("")
        lines.append("  On 2026-08-29 this role reported, over three runs, that a published")
        lines.append("  meta-analysis had used a superseded MONARCH 3 figure. It had not.")
        lines.append("  The claim went onto the page as a disclosure -- 'we would rather say")
        lines.append("  so than have it found' -- and an outside reviewer opened the paper's")
        lines.append("  Table 1 and corrected us. No further gate run could have caught it:")
        lines.append("  the gate wrote it, and no role here audits another role's output.")
        lines.append("  " + "!" * 68)
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
        lines.append("     BEFORE ACTING : open the source above and read the sentence.")

    serious = [o for o in (objections or []) if o.get("severity") == "SERIOUS"]
    lines.append("")
    lines.append("=" * 72)
    lines.append(f"FAIRNESS {len(objections or [])} objection(s) · {len(serious)} serious")
    lines.append("=" * 72)
    for o in (objections or []):
        kind, dec, how = classify("ADVOCATE", o.get("quote", ""), o.get("severity", ""), decisions)
        if kind == "ADJUDICATED":
            adjudicated.append(("ADVOCATE", o.get("severity"), o.get("objection"), dec, how))
            continue
        if kind == "STALE":
            moved_since.append(("ADVOCATE", o.get("severity"), o.get("objection"), dec, how))
        # Missing class means an older report, or a role that did not answer:
        # fail closed, because an unclassified finding is not a cleared one.
        if o.get("severity") == "SERIOUS" and o.get("class", "") != "CALIBRATION":
            failed = True
        lines.append("")
        lines.append(f"  [{kind} · {o.get('severity')} · "
                     f"{o.get('class', 'UNCLASSIFIED')}] {o.get('objection')}")
        if kind == "OVERLAP":
            lines.append(f"     already decided about this sentence, on other "
                         f"grounds: {dec.get('reason', '')[:150]}")
            lines.append("     If this is that same finding, it is settled. If it "
                         "is a different")
            lines.append("     fault in the same sentence, it is new and needs its "
                         "own decision.")
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
        kind, dec, how = classify("INFERENCE", i.get("quote", ""), i.get("severity", ""), decisions)
        if kind == "ADJUDICATED":
            adjudicated.append(("INFERENCE", i.get("severity"), i.get("problem"), dec, how))
            continue
        if kind == "STALE":
            moved_since.append(("INFERENCE", i.get("severity"), i.get("problem"), dec, how))
        if i.get("severity") == "SERIOUS" and i.get("class", "") != "CALIBRATION":
            failed = True
        lines.append("")
        lines.append(f"  [{kind} · {i.get('severity')} · "
                     f"{i.get('class', 'UNCLASSIFIED')}] {i.get('problem')}")
        if kind == "OVERLAP":
            lines.append(f"     already decided about this sentence, on other "
                         f"grounds: {dec.get('reason', '')[:150]}")
            lines.append("     If this is that same finding, it is settled. If it "
                         "is a different")
            lines.append("     fault in the same sentence, it is new and needs its "
                         "own decision.")
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
        kind, dec, how = classify("COVERAGE", c.get("quote", ""), c.get("severity", ""), decisions)
        if kind == "ADJUDICATED":
            adjudicated.append(("COVERAGE", c.get("severity"),
                                c.get("counterexample", "")[:90], dec, how))
            continue
        if kind == "STALE":
            moved_since.append(("COVERAGE", c.get("severity"),
                          c.get("counterexample", "")[:90], dec, how))
        if c.get("severity") == "SERIOUS":
            failed = True
        lines.append("")
        lines.append(f"  [{kind} · {c.get('severity')}] the draft's claim about the "
                     "coverage is contradicted")
        if kind == "OVERLAP":
            lines.append(f"     already decided about this sentence, on other "
                         f"grounds: {dec.get('reason', '')[:150]}")
            lines.append("     If this is that same finding, it is settled. If it "
                         "is a different")
            lines.append("     fault in the same sentence, it is new and needs its "
                         "own decision.")
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

    calib = [f for f in (objections or []) + (inferences or [])
             if isinstance(f, dict) and f.get("class") == "CALIBRATION"]
    if calib:
        lines.append("")
        lines.append("=" * 72)
        lines.append(f"CALIBRATION  {len(calib)} finding(s) recorded, none blocking")
        lines.append("=" * 72)
        lines.append("")
        lines.append("  Matters of phrasing, ordering, emphasis and degree. Real, and not")
        lines.append("  corrections. There is always a defensible alternative wording, so a")
        lines.append("  check that blocks on wording never stops. Read them; fix what you")
        lines.append("  agree with; publish either way.")
        for f in calib:
            what = f.get("objection") or f.get("problem") or ""
            lines.append("")
            lines.append(f"  [{f.get('severity')}] {what[:150]}")
            if f.get("quote"):
                lines.append(f"     quote : {f['quote'][:120]}")

    lines.append("")
    lines.append("=" * 72)
    lines.append(f"ADJUDICATION  {len(adjudicated)} already decided · {len(moved_since)} moved since")
    lines.append("=" * 72)
    if moved_since:
        failed = True
        lines.append("")
        lines.append("  Decided once, reported differently now — read these again:")
        for role, sev, what, dec, how in moved_since:
            lines.append(f"    [{role}] was {dec.get('severity')}, now {sev}: {what}")
            if how == "overlap":
                lines.append(f"        matched by overlap with: {dec.get('quote', '')[:80]}")
    if adjudicated:
        lines.append("")
        lines.append("  Read before and accepted, not repeated above:")
        for role, sev, what, dec, how in adjudicated:
            lines.append(f"    [{role} {sev}] {what}"
                         + ("  (matched by overlap)" if how == "overlap" else ""))
            lines.append(f"        {dec.get('decided', '?')}: {dec.get('reason', '')}")
    if not adjudicated and not moved_since:
        lines.append("")
        lines.append("  Nothing has been adjudicated for this draft. Every finding above")
        lines.append(f"  is new. Record the ones you accept in {DECISIONS.name} so the")
        lines.append("  next run can tell a fresh problem from a settled one.")

    return "\n".join(lines), failed


def main():
    ap = argparse.ArgumentParser(description="Pre-publication fact-check gate.")
    ap.add_argument("draft", nargs="?", help="Path to the draft (HTML or text).")
    # DEFAULTS TO <draft>.gate.json, and did not until 2026-08-30.
    #
    # Before that, omitting --report meant the run printed its findings, wrote
    # no report, bound no sha, and did not increment the per-cycle counter --
    # because save() and cycle_record() both sit behind `if not args.report`.
    # Three runs were commissioned that day without it: $23.78 of checking that
    # left no artifact, no sha binding, and a cap counter still reading one run.
    # The findings were real and were acted on; the evidence for them was not
    # written down, and publish.py went on reading a report from the original
    # draft as though it certified the current one.
    #
    # A flag whose absence silently spends money and records nothing is a trap.
    # The report path is now derived from the draft, which is the only sensible
    # place for it, and --report remains available to override.
    ap.add_argument("--report", help="Write the full JSON result here. "
                                     "Defaults to <draft>.gate.json.")
    ap.add_argument("--decisions", default=str(DECISIONS),
                    help="Record of findings already read and accepted. Findings "
                         "matching one are reported as ADJUDICATED and do not block; "
                         "a finding whose severity has moved since is STALE and does.")
    ap.add_argument("--new-cycle", action="store_true",
                    help="Start a new gate cycle. This is what happens after an outside "
                         "review: the draft has changed for a reason other than our own "
                         "findings. It resets the per-cycle counter and KEEPS the run "
                         "history, so it cannot be used to buy runs past the %d-run "
                         "budget for an issue." % RUNS_PER_ISSUE)
    ap.add_argument("--past-cap", metavar="REASON",
                    help="Run past the per-cycle cap, recording why. A cap with no "
                         "override gets worked around; one with a required reason gets "
                         "used deliberately.")
    ap.add_argument("--since", metavar="REPORT",
                    help="A previous gate report for this draft. Claims whose sentences "
                         "are unchanged keep their verdicts; RECENCY and COVERAGE are "
                         "carried if recent, because they depend on the world and not on "
                         "our wording. ADVOCATE and INFERENCE always re-run: they are the "
                         "whole-document readers and scoping them to the diff is how a "
                         "fixed sentence breaks a distant one.")
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

    # See the note on --report above. A run that writes nothing is never what
    # the caller wanted, and on 2026-08-30 it was what the caller got, three
    # times, because the flag was easy to forget when writing a command by hand.
    if args.draft and not args.report:
        args.report = str(Path(args.draft).with_suffix(
            Path(args.draft).suffix + ".gate.json"))
        print("  --report not given; writing to %s" % args.report)

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
        # --verify must answer the same question the run asks, by the same
        # route. It read os.environ while the run reads _api_key(), so on a
        # machine where the key lives in backend/.env -- the normal case, and
        # the one _api_key() was written for -- this printed MISSING and exited
        # 2 for a run that would have worked. A check that disagrees with the
        # thing it checks is worse than no check: it sends you to fix a
        # configuration that was already correct.
        key = _api_key()
        where = ("the shell" if os.environ.get(KEY_VAR)
                 else str(ENVFILE) if key else "")
        print("%-18s: %s" % (KEY_VAR, ("set, from " + where) if key else "MISSING"))
        if not key:
            print("%-18s  looked in the shell and in %s" % ("", ENVFILE))
        print("%-18s: %s" % ("model", SIGNAL_MODEL))
        print("%-18s: %s" % ("known-errors",
                             "present" if KNOWN_ERRORS.exists() else "MISSING"))
        print("%-18s: %s" % ("decisions",
                             "present" if Path(args.decisions).exists()
                             else "absent (no adjudications recorded yet)"))
        sys.exit(0 if key else 2)

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
        # Survey mode used to print only the coverage and swallow the
        # contradictions, which are the half that says the premise of the
        # question is wrong. On the first live run that hid three SERIOUS
        # findings behind a count in the header.
        contra = cov.get("contradictions") or []
        if contra:
            print("  Contradictions to the premise of this inquiry:")
            for c in contra:
                print(f"    [{c.get('severity')}] {c.get('counterexample', '')}")
                if c.get("quote"):
                    print(f"       premise : \u201c{c['quote']}\u201d")
                if c.get("url"):
                    print(f"       see     : {c['url']}")
                if c.get("fix"):
                    print(f"       fix     : {c['fix']}")
            print("")
        if not (cov.get("best_coverage") or []):
            print("  No careful treatment found. That is a finding, and a "
                  "better-supported one for having looked.")
        print("  These are search results, not verified facts. Every figure "
              "above still goes through SOURCE before it reaches a draft.")
        sys.exit(0)

    if not args.draft:
        ap.error("a draft path is required (or use --verify / --known-errors / --survey)")

    # THE CAP, ENFORCED RATHER THAN REPORTED.
    #
    # The ledger was wired to RECORD spend and nothing was wired to STOP it, so
    # for an hour the "$40 cap" existed only as a number printed on a board --
    # which is the same thing the old two-runs cap was, and it eroded because
    # nothing enforced it. A cap that reports is a gauge, not a cap.
    #
    # This matters more now that jobs can run unattended: the operator agreed to
    # that on the condition the cap was real.
    if _spend is not None:
        _issue_slug = issue_slug_for(args.draft)
        # Set BEFORE any API call, so every ledger line written during the run
        # is attributed to the right issue. _ledger_now reads this.
        enter_issue(_issue_slug)
        try:
            _spend.check_cap(_issue_slug, about_to_spend=3.0)
        except Exception as _exc:
            if type(_exc).__name__ == "OverCap":
                print("\n  STOPPED BEFORE SPENDING.\n")
                for _line in str(_exc).splitlines():
                    print("  " + _line)
                print()
                sys.exit(3)
            raise

    warn_if_unpinned()
    path = Path(args.draft)

    # Before any money is spent. The cap is checked against the report path
    # because that is what identifies the draft across runs, and the counter
    # lives beside it so it travels with the issue rather than with a machine.
    if not cycle_check(args.report, args.past_cap, args.new_cycle):
        sys.exit(3)

    draft = read_draft(path)
    today = args.today or time.strftime("%Y-%m-%d")
    print(f"\nFact-checking {path.name} ({len(draft):,} chars of prose) as of {today}\n")

    claims = extract_claims(draft)
    if claims is None:
        print("\n[BLOCKED] Could not extract claims. Nothing was checked.")
        sys.exit(2)

    prior = load_prior(args.since)
    carried_note = []

    # Ask the registry once, before anything asks a model. See registry_settle.
    _settler = None
    try:
        import importlib.util as _ilu2
        _sp = _ilu2.spec_from_file_location(
            "registry_settle",
            Path(__file__).resolve().parents[1] / "whatholdsup" / "registry_settle.py")
        _rs = _ilu2.module_from_spec(_sp)
        _sp.loader.exec_module(_rs)
        _settler = _rs.Settler(issue_slug_for(args.draft),
                               path.read_text(encoding="utf-8"))
        print("      registry pre-check: %s" % _settler.summary())
    except BaseException as _exc:      # noqa: BLE001 - see below
        # BaseException, NOT Exception. registry_settle reaches case_dir(), which
        # raises SystemExit when it cannot find a case directory -- and SystemExit
        # does not inherit from Exception. So `except Exception` did not catch it,
        # and on 2026-09-01 a COST-SAVING pre-check killed the email gate outright,
        # after it had already paid for claim extraction.
        #
        # A guard that says it never breaks a run has to actually not break the
        # run. "Never raises" is a promise about every exit path, not about the
        # ones that were anticipated.
        if isinstance(_exc, KeyboardInterrupt):
            raise
        # Loudly. A pre-check that fails silently looks exactly like a registry
        # with nothing to say, and the run would go on to buy what it could
        # have had for nothing while reporting that it had checked.
        print("      [WARN] registry pre-check unavailable (%s: %s) — every claim "
              "goes to the model, including any the registry could have settled"
              % (type(_exc).__name__, _exc))

    if prior:
        todo, carried, n = carry_verdicts(claims, prior)
        if n:
            print(f"      {n} claim(s) unchanged since {prior.get('sha256','')[:12]} — "
                  f"verdicts carried, {len(todo)} to check")
            carried_note.append(f"{n} claim verdict(s) carried forward")
        verdicts = {**carried,
                    **(audit_sources(todo, path.stem, _settler) if todo else {})}
    else:
        verdicts = audit_sources(claims, path.stem, _settler)

    age = _days_since(prior.get("checked_at")) if prior else 1e9
    if prior and prior.get("recency") and age <= RECENCY_FRESH_DAYS:
        print(f"[3/6] Recency sweep... carried ({age:.0f}d old, fresh under "
              f"{RECENCY_FRESH_DAYS}d — the literature does not move because we edited)")
        recency = prior["recency"]
        carried_note.append(f"recency carried ({age:.0f}d)")
    else:
        recency = sweep_recency(draft, today)

    objections = advocate(draft)
    inferences = inference(draft)

    if prior and prior.get("coverage") and age <= COVERAGE_FRESH_DAYS:
        print(f"[6/6] Best coverage elsewhere... carried ({age:.0f}d old, fresh under "
              f"{COVERAGE_FRESH_DAYS}d — other outlets did not republish because we edited)")
        cov = prior["coverage"]
        carried_note.append(f"coverage carried ({age:.0f}d)")
    else:
        cov = coverage(draft)

    if recency is None or objections is None or inferences is None or cov is None:
        print("\n[BLOCKED] A required check did not run. An unrun check is not a pass.")
        sys.exit(2)

    decisions = load_decisions(Path(args.decisions), str(path))
    orphans = orphaned(decisions, draft)
    if orphans:
        print(f"[WARN] {len(orphans)} decision(s) quote a sentence that is no "
              f"longer in {path.name}. They can never match again — remove them:")
        for role, q in orphans:
            print(f"       [{role}] {q[:70]}")

    # The findings are written BEFORE they are rendered.
    #
    # On 2026-08-27 a name collision inside render() raised ValueError after all
    # six roles had run and before anything was saved. Every API call in that
    # run was lost to a formatting bug — the cheapest possible failure destroying
    # the most expensive possible work. Persist first: a display problem should
    # cost a re-render, not a re-run.
    #
    # 'passed' is filled in after rendering, since only render() knows. Until
    # then it is null, and require_gate in send_broadcast.py treats a null as a
    # failure — an unfinished report must never read as a passing one.
    def save(passed):
        if not args.report:
            return
        # A fingerprint per sentence, so a later run can tell which sentences
        # this report actually examined.
        #
        # Without it, the only way to answer that is to recover the judged
        # draft from git -- and on 2026-08-31 that recovery silently proved
        # nothing for issue three, because the gate report had been committed
        # alongside the final page and `git show` handed back the same file.
        # The comparison passed by comparing the page to itself.
        #
        # The failure it exists for: issue two's board read "state ok, every
        # one of its 7 findings resolved" while the live page carried 28
        # sentences of figures, trial names and registry ids added by a later
        # correction, none of which any role had read. An absence of findings
        # about a sentence is not a verdict about that sentence.
        try:
            _fps = sorted(_unjudged.fingerprints(path.read_text(encoding="utf-8")))
        except Exception:
            _fps = []
        # Into the append-only ledger as well as the report. The report is
        # overwritten by the next run, which is why git preserved only $20.66
        # of a spend the operator experienced as roughly $100 an issue.
        # ONCE PER PROCESS, not once per save(). save() is called twice --
        # save(None) partway through and save(not failed) at the end -- so the
        # first wiring recorded every run TWICE. Issue two's re-gate cost $5.20
        # and the ledger said $10.39, which is how it was noticed: the estimate
        # was checked against the actual, and the actual was wrong.
        #
        # A ledger that overcounts is not the safe direction. It would have
        # tripped the $40 cap at real spend of $20 and stopped work for a
        # reason that was not true.
        # The end-of-run aggregate write that used to live here is GONE.
        # Every response is now recorded by _ledger_now at the moment it
        # arrives, so writing the totals again here would double every run --
        # which is precisely the bug that turned $5.20 into $10.39 when save()
        # ran twice. Recording at the end also meant a run that died partway
        # spent money and recorded none of it, which is how the 31 August email
        # gate billed eleven successful source calls and left no trace.
        Path(args.report).write_text(json.dumps({
            "draft": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sentence_fingerprints": _fps,
            "passed": passed,
            "carried": carried_note,
            "checked_at": today, "model": SIGNAL_MODEL,
            "usage": usage_summary(),
            "claims": claims, "verdicts": verdicts,
            "recency": recency, "objections": objections,
            "inferences": inferences, "coverage": cov,
        }, indent=2), encoding="utf-8")

    save(None)
    cycle_record(args.report, hashlib.sha256(path.read_bytes()).hexdigest(),
                 args.past_cap) if args.report else None

    try:
        report, failed = render(claims, verdicts, recency, objections, inferences, cov,
                                decisions)
    except Exception as exc:
        print(f"\n[ERROR] The findings were collected but could not be rendered: "
              f"{exc!r}")
        if args.report:
            print(f"        They are saved in {args.report} — nothing was lost, and")
            print("        the report is marked unpassed so nothing can be sent on it.")
        raise

    print(report)
    print(format_usage())
    save(not failed)
    if args.report:
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
