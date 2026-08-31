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


def record(*, script: str, role: str = "", issue: str = "", usd: float = 0.0,
           input_tokens: int = 0, output_tokens: int = 0, web_searches: int = 0,
           note: str = "", at: str | None = None) -> None:
    """Append one priced call. Never raises: accounting must not break a run.

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
                "usd": round(float(usd or 0), 6),
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
    total = 0.0
    for e in entries():
        if issue and e.get("issue") != issue:
            continue
        if script and e.get("script") != script:
            continue
        if since and (e.get("at") or "") < since:
            continue
        total += e.get("usd") or 0
    return round(total, 4)


def caps() -> dict:
    if not CAPS.exists():
        return {}
    try:
        return json.loads(CAPS.read_text(encoding="utf-8"))
    except Exception:
        return {}


class OverCap(Exception):
    pass


def check_cap(issue: str, about_to_spend: float = 0.0) -> None:
    """Stop before spending past the cap. Fails closed.

    The environment variable WHU_SPEND_OVERRIDE lifts it for one run and is
    written into the ledger, so an override is a fact on the record rather than
    a decision that leaves no trace.
    """
    c = caps()
    limit = (c.get("per_issue") or {}).get(issue, c.get("default_per_issue"))
    if not limit:
        return
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
