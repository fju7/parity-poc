"""What did verifying this issue actually cost?

WHY THIS EXISTS
---------------
On 2026-08-31 the operator asked how roughly $100 an issue was being spent, and
the honest answer was that our own records cannot say.

    Fifteen scripts in this repo make priced model calls.
    One of them records what it spent.
    That one writes the figure into a file the next run overwrites.

So git preserves $20.66 of gate runs -- only the reports that happened to be
committed before the next run replaced them -- and everything else is gone:
counterexample hunts, source-advocate calls, premise checks, claim extraction
and scoring, the Signal golden set at 53 categories a sweep, consensus mapping
at three runs a category. None of it left a trace anyone can add up.

WHY THE CAP KEPT MOVING
-----------------------
An agreed limit of "two gate runs" is a proxy for money, not money. When the
outside review came back and the situation changed, the proxy was renegotiated
-- twice -- and nobody could see the running total that would have made the
renegotiation obviously wrong. A cap you cannot measure against is not a cap,
it is an intention.

This is the same failure as every other one this week, in a different
currency: the information exists for a moment, nothing records it, and so
nothing can act on it. The fix is the same too. Make it a state, then make the
state block.

WHAT THIS IS
------------
An append-only ledger. One line per priced call: when, which script, which
role, which issue, tokens, searches, dollars. Nothing overwrites anything.

    from spend_ledger import record, spent, check_cap

`check_cap` fails CLOSED: over budget stops the run and names the number.
Raising the cap is an edit to a file that is committed and reviewable, not a
sentence in a conversation.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "backend" / "data" / "spend" / "ledger.jsonl"
CAPS = ROOT / "backend" / "data" / "spend" / "caps.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class UnpricedModel(RuntimeError):
    """A model call whose cost cannot be established.

    An unknown price is NOT a zero. Until 2026-09-14 both meters wrote
    `usd: 0.0` with a note when the model was absent from PRICES, so spent()
    summed zero and every cap in the system silently stopped working the
    moment signal_model.MODEL resolved to a model nobody had priced. Now:
    the call refuses BEFORE spending when the requested model is unpriced;
    if the RESPONSE names an unpriced model (an alias resolving somewhere
    new), the line is written with `usd: null` -- the truth, which is that
    the spend is not established -- and the caller raises this; and
    check_cap refuses while any such line exists in its scope, because a
    cap that cannot be computed is not a cap.
    """


def record(*, script: str, role: str = "", issue: str = "", usd: float | None = 0.0,
           input_tokens: int = 0, output_tokens: int = 0, web_searches: int = 0,
           note: str = "", at: str | None = None) -> None:
    """Append one priced call. Never raises: accounting must not break a run.

    `usd=None` means NOT ESTABLISHED and is written as JSON null, never as
    0.0. See UnpricedModel.

    `at` exists for backfill only. The first backfill stamped four gate runs
    from 28 and 30 August with the moment they were imported, and the by-day
    report then showed the whole history spent on 31 August. A ledger that
    misdates its own entries answers "when did this happen" wrongly while
    looking authoritative, which is worse than not answering.
    """
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "at": at or _now(), "script": script, "role": role, "issue": issue,
                "usd": None if usd is None else round(float(usd), 6),
                "input": int(input_tokens or 0), "output": int(output_tokens or 0),
                "web_searches": int(web_searches or 0), "note": note,
            }) + "\n")
    except Exception:
        pass


def entries() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def spent(issue: str | None = None, since: str | None = None,
          script: str | None = None) -> float:
    """`issue=None` means every issue. `issue=""` means the entries that name
    NO issue, which is a real and interesting set -- not a request for all of
    them.

    It used to mean "no filter", because the test was `if issue and ...`. So
    spent("") returned the whole estate's total: $40.57 against a $40 per-issue
    cap. Anything asking about unattributed spend got an answer about
    everything, and check_cap("") would have blocked every run in the
    repository for a reason that had nothing to do with the run.
    """
    total = 0.0
    for e in entries():
        if issue is not None and (e.get("issue") or "") != issue:
            continue
        if script and e.get("script") != script:
            continue
        if since and (e.get("at") or "") < since:
            continue
        total += e.get("usd") or 0
    return round(total, 4)


def unpriced(issue: str | None = None, since: str | None = None) -> list[dict]:
    """Ledger lines whose cost is not established (`usd` is null)."""
    out = []
    for e in entries():
        if issue is not None and (e.get("issue") or "") != issue:
            continue
        if since and (e.get("at") or "") < since:
            continue
        if e.get("usd") is None:
            out.append(e)
    return out


def caps() -> dict:
    if not CAPS.exists():
        return {}
    try:
        return json.loads(CAPS.read_text(encoding="utf-8"))
    except Exception:
        return {}


class OverCap(Exception):
    pass


def check_day_cap(about_to_spend: float = 0.0) -> None:
    """Stop when today's total across EVERYTHING is past the daily cap.

    The per-issue cap cannot see Signal work, which is not attributed to an
    issue, and it cannot see a bad afternoon spread across three issues. On
    2026-08-31 roughly $100 an issue was spent with nothing counting; a daily
    ceiling is the backstop that does not depend on getting attribution right,
    and it matters most now that jobs can run unattended.
    """
    c = caps()
    limit = c.get("default_per_day")
    if not limit:
        return
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    bad = [e for e in unpriced() if (e.get("at") or "").startswith(today)]
    if bad:
        raise UnpricedModel(
            "the daily cap cannot be computed: %d ledger line(s) today have no established "
            "cost (usd null). Price the model in PRICES and reconcile those lines before "
            "spending again. First: %s" % (len(bad), bad[0]))
    spent_today = round(sum(e.get("usd") or 0 for e in entries()
                            if (e.get("at") or "").startswith(today)), 4)
    if spent_today + about_to_spend <= float(limit):
        return
    why = os.environ.get("WHU_SPEND_OVERRIDE", "").strip()
    if why:
        record(script="spend_ledger", role="override", usd=0.0,
               note="DAY cap $%.2f, today $%.2f, about to spend $%.2f — %s"
                    % (float(limit), spent_today, about_to_spend, why))
        return
    raise OverCap(
        "$%.2f has been spent today against a $%.2f daily cap, and this run would\n"
        "add about $%.2f. This ceiling covers everything, including work not\n"
        "attributed to an issue.\n"
        "Raise default_per_day in backend/data/spend/caps.json, or set\n"
        "WHU_SPEND_OVERRIDE='reason' for one run, which is recorded."
        % (spent_today, float(limit), about_to_spend))


def check_cap(issue: str, about_to_spend: float = 0.0) -> None:
    """Stop before spending past the cap. Fails closed.

    The environment variable WHU_SPEND_OVERRIDE lifts it for one run and is
    written into the ledger, so an override is a fact on the record rather than
    a decision that leaves no trace.
    """
    check_day_cap(about_to_spend)
    c = caps()
    limit = (c.get("per_issue") or {}).get(issue, c.get("default_per_issue"))
    if not limit:
        return
    bad = unpriced(issue=issue)
    if bad:
        raise UnpricedModel(
            "the cap for %r cannot be computed: %d ledger line(s) have no established "
            "cost (usd null). A cap summed over an unknown is not a cap. Price the model "
            "in PRICES and reconcile those lines before spending again. First: %s"
            % (issue, len(bad), bad[0]))
    already = spent(issue=issue)
    if already + about_to_spend <= float(limit):
        return
    why = os.environ.get("WHU_SPEND_OVERRIDE", "").strip()
    if why:
        record(script="spend_ledger", role="override", issue=issue, usd=0.0,
               note="cap $%.2f, already $%.2f, about to spend $%.2f — %s"
                    % (float(limit), already, about_to_spend, why))
        return
    raise OverCap(
        "%s has spent $%.2f of a $%.2f cap and this run would add about $%.2f.\n"
        "Raise the cap in backend/data/spend/caps.json (committed, reviewable), or set\n"
        "WHU_SPEND_OVERRIDE='reason' for one run, which is recorded in the ledger."
        % (issue, already, float(limit), about_to_spend))


def report(issue: str | None = None) -> str:
    es = [e for e in entries() if not issue or e.get("issue") == issue]
    if not es:
        return "Nothing recorded yet."
    by_issue, by_script, by_day = {}, {}, {}
    for e in es:
        u = e.get("usd") or 0
        by_issue[e.get("issue") or "(none)"] = by_issue.get(e.get("issue") or "(none)", 0) + u
        by_script[e.get("script") or "?"] = by_script.get(e.get("script") or "?", 0) + u
        by_day[(e.get("at") or "")[:10]] = by_day.get((e.get("at") or "")[:10], 0) + u
    total = sum(e.get("usd") or 0 for e in es)
    c = caps()
    lines = ["", "=" * 66, "SPEND", "=" * 66,
             "  %d priced call(s), $%.2f total" % (len(es), total), "", "  by issue:"]
    for k, v in sorted(by_issue.items(), key=lambda x: -x[1]):
        cap = (c.get("per_issue") or {}).get(k, c.get("default_per_issue"))
        tail = ("   of $%.0f cap  (%.0f%%)" % (float(cap), 100 * v / float(cap))) if cap else ""
        lines.append("    %-16s $%8.2f%s" % (k, v, tail))
    lines += ["", "  by script:"]
    for k, v in sorted(by_script.items(), key=lambda x: -x[1])[:12]:
        lines.append("    %-28s $%8.2f" % (k, v))
    lines += ["", "  by day:"]
    for k, v in sorted(by_day.items()):
        lines.append("    %-12s $%8.2f" % (k, v))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--issue")
    print(report(ap.parse_args().issue))


# ---------------------------------------------------------------------------
# Pricing, and a client that meters itself.
#
# The table used to live in factcheck_draft.py, which was the only script that
# priced anything. Eight scripts construct an Anthropic client and seven of
# them recorded nothing, so "what did this cost" had no answer and the cap
# covered the gate alone. Rather than copy the table seven times -- copies go
# stale separately, which is worse than one stale copy -- it moves here and
# factcheck_draft reads it from here too.

PRICES_CHECKED = "2026-08-28"
PRICES = {                       # US dollars per million tokens
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00,
                          "cache_write": 3.75, "cache_read": 0.30},
    "claude-opus-4-6":   {"input": 5.00, "output": 25.00,
                          "cache_write": 6.25, "cache_read": 0.50},
}
WEB_SEARCH_PER_1000 = 10.00      # charged on top of tokens, all models


def price(model: str, usage) -> tuple[float | None, dict]:
    """(usd, counts) for one API response. None when the model is not in the
    table -- an invented number would be worse than no number, because it would
    be used."""
    counts = {
        "input": int(getattr(usage, "input_tokens", 0) or 0),
        "output": int(getattr(usage, "output_tokens", 0) or 0),
        "cache_write": int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        "cache_read": int(getattr(usage, "cache_read_input_tokens", 0) or 0),
        "web_searches": 0,
    }
    stu = getattr(usage, "server_tool_use", None)
    if stu is not None:
        counts["web_searches"] = int(getattr(stu, "web_search_requests", 0) or 0)
    base = (model or "").strip()
    p = PRICES.get(base)
    if not p:
        return None, counts
    usd = (counts["input"] * p["input"] + counts["output"] * p["output"]
           + counts["cache_write"] * p["cache_write"]
           + counts["cache_read"] * p["cache_read"]) / 1_000_000.0
    usd += counts["web_searches"] * WEB_SEARCH_PER_1000 / 1000.0
    return round(usd, 6), counts


class _MeteredMessages:
    def __init__(self, inner, script, issue, role):
        self._inner, self._script, self._issue, self._role = inner, script, issue, role

    def create(self, *a, **kw):
        # BEFORE spending: a model nobody has priced is refused outright.
        requested = (kw.get("model") or "").strip()
        if requested and requested not in PRICES:
            raise UnpricedModel(
                "refusing to spend: model %r is not in spend_ledger.PRICES, so its cost "
                "could not be established. Price it (and check the gate's copy) first."
                % requested)
        r = self._inner.create(*a, **kw)
        resolved = getattr(r, "model", "") or requested
        usd, counts = price(resolved, getattr(r, "usage", None))
        try:
            record(script=self._script, role=self._role, issue=self._issue,
                   usd=usd, input_tokens=counts["input"],
                   output_tokens=counts["output"],
                   web_searches=counts["web_searches"],
                   note="" if usd is not None else
                        "UNPRICED: response model %r is not in the price table; "
                        "spend NOT ESTABLISHED" % resolved)
        except Exception:
            pass
        if usd is None:
            # AFTER spending: the money is gone and the line says so honestly.
            # Stop here rather than carry on under a cap that can no longer
            # be computed.
            raise UnpricedModel(
                "the response came back under model %r, which is not in PRICES. The "
                "call was made and recorded with no established cost; nothing further "
                "runs until it is priced." % resolved)
        return r

    def __getattr__(self, k):
        return getattr(self._inner, k)


class MeteredClient:
    """Wraps an Anthropic client so every call lands in the ledger.

    Wrapping the CLIENT rather than each call site is the point: a script with
    four `messages.create` calls needs one change, and a call added later is
    metered without anybody remembering to meter it. That is the difference
    between a control and a convention.
    """

    def __init__(self, inner, *, script: str, issue: str = "", role: str = ""):
        self._inner = inner
        self.messages = _MeteredMessages(inner.messages, script, issue, role)

    def __getattr__(self, k):
        return getattr(self._inner, k)


def metered(inner, *, script: str, issue: str = "", role: str = ""):
    """Wrap a client; on any failure return it unwrapped rather than break a run."""
    try:
        return MeteredClient(inner, script=script, issue=issue, role=role)
    except Exception:
        return inner
