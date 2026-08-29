#!/usr/bin/env python3
"""
What Holds Up: the lead scanner.

WHY THIS EXISTS
---------------
Issue two was selected backwards. A Signal inquiry asked which breast cancer
drug worked best; we answered it, found something interesting, and then went
looking for a public claim the finding corrected. There wasn't one, so we wrote
the sentence ourselves -- and the sentence we wrote is the one that turned out
to be false.

This publication is for claims already in circulation whose evidentiary basis
is not circulating with them. That means the subject has to exist before the
reporting does. This file is the front of that pipeline: it looks at what is
actually being covered and read, so that a candidate arrives as an observation
about the world rather than as a conclusion looking for a hook.

WHY IT RUNS ON THE OPERATOR'S MACHINE
-------------------------------------
Both data sources are unreachable from the assistant's cloud container --
GDELT's robots.txt is not fetchable from there, and the Wikimedia REST API is
cache-only. Neither restriction applies to an ordinary machine on an ordinary
connection. So this runs where the operator is, on a schedule, and deposits its
output in the repository for whoever looks next.

WHAT IT MEASURES, AND WHY TWO SOURCES
-------------------------------------
    GDELT               what is being PUBLISHED. Volume of coverage across
                        tens of thousands of outlets, by query, over time.
    Wikipedia pageviews what is being READ. Public attention, which moves for
                        different reasons than press volume does.

Either alone is misleading. High publication volume with no reading is a press
release being echoed. High reading with no publication is an old story people
keep looking up. A subject worth our attention usually spikes in both, and the
gap between them is itself informative: a story the press is pushing harder
than the public is pulling is exactly where a claim travels without its
evidence.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not decide whether something is a story. It cannot: the test is whether
a claim in circulation outruns its evidence, and that needs reading. This
produces the shortlist a person or the funnel then works through, and it is
honest about being a volume instrument.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "issues" / "leads"
UA = "WhatHoldsUp-lead-scanner/1.0 (corrections@whatholdsup.org)"
MIN_GAP_SECONDS = 5.0
_LAST_CALL = 0.0

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
PAGEVIEWS_TOP = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/top/"
                 "en.wikipedia/all-access/{y}/{m:02d}/{d:02d}")

# Pageview noise: perennial lookups, site furniture, and the long tail of
# entertainment that spikes for reasons no assessment can address.
SKIP = re.compile(
    r"^(Main_Page|Special:|Wikipedia:|Portal:|Help:|File:|Category:|Talk:)"
    r"|^(Deaths_in_|List_of_|Index_of_)"
    r"|^(Cleopatra|United_States|India|YouTube|Google|Facebook|ChatGPT)$",
    re.I)


def _get(url: str, timeout: int = 45, tries: int = 3):
    """GDELT times out under load often enough that one attempt is not a reading.

    A scanner that reports "no coverage" when the API was busy would be the
    volume equivalent of every failure in this repository: an unrun check that
    looks exactly like a clean one. So a transport failure raises rather than
    returning empty, and the caller records the error in the report.
    """
    import time
    global _LAST_CALL
    # GDELT rate-limits, and being rate-limited looks exactly like finding
    # nothing. On 2026-08-29 an interactive session ran the scanner hard enough
    # to earn a 429 within a few minutes. A minimum gap between calls costs
    # nothing on a weekly schedule and is the difference between a scan and a
    # silence.
    gap = time.time() - _LAST_CALL
    if gap < MIN_GAP_SECONDS:
        time.sleep(MIN_GAP_SECONDS - gap)
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                _LAST_CALL = time.time()
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:           # noqa: PERF203
            last = e
            _LAST_CALL = time.time()
            if e.code == 429:
                time.sleep(30 * (n + 1))              # back off hard, not politely
            elif n < tries - 1:
                time.sleep(2 + 3 * n)
        except Exception as e:                        # noqa: BLE001
            last = e
            _LAST_CALL = time.time()
            if n < tries - 1:
                time.sleep(2 + 3 * n)
    raise last


# ---------------------------------------------------------------------------

def coverage_volume(query: str, timespan: str = "14d") -> dict:
    """How heavily a claim is being carried, and by whom.

    GDELT's timeline mode is markedly slower than its article list and times out
    under load on broad queries. It gets one short attempt; if it fails, the scan
    continues on outlet spread alone rather than hanging, and the report says the
    volume reading is missing rather than reporting zero. A scanner that reports
    "no coverage" because an API was busy is the volume equivalent of every
    failure in this repository.
    """
    q = urllib.parse.urlencode({
        "query": query, "mode": "timelinevolinfo",
        "timespan": timespan, "format": "json"})
    try:
        d = _get(f"{GDELT}?{q}", timeout=25, tries=1)
    except Exception as e:
        return {"query": query, "volume_unavailable": str(e)[:80]}
    series = (d.get("timeline") or [{}])[0].get("data", [])
    vals = [p.get("value", 0) for p in series]
    peak = max(vals) if vals else 0
    recent = vals[-3:] if len(vals) >= 3 else vals
    base = sorted(vals)[:max(1, len(vals) // 2)]
    baseline = sum(base) / len(base) if base else 0
    return {
        "query": query,
        "points": len(vals),
        "peak": round(peak, 4),
        "recent_mean": round(sum(recent) / len(recent), 4) if recent else 0,
        "baseline": round(baseline, 4),
        "spike_ratio": round((sum(recent) / len(recent)) / baseline, 2)
                       if recent and baseline else None,
        "top_articles": [{"title": a.get("title"), "domain": a.get("domain"),
                          "url": a.get("url"), "seendate": a.get("seendate")}
                         for a in (d.get("articles") or [])[:12]],
    }


def outlet_spread(query: str, timespan: str = "14d") -> dict:
    """How many DISTINCT outlets carried it.

    Volume from one wire service reproduced everywhere is one source. This is
    the crude version of the independence problem the source ledger handles
    downstream, applied at selection time: forty outlets running the same
    agency copy is not forty carriers.
    """
    q = urllib.parse.urlencode({
        "query": query, "mode": "artlist", "maxrecords": 250,
        "timespan": timespan, "format": "json", "sort": "hybridrel"})
    try:
        d = _get(f"{GDELT}?{q}")
    except Exception as e:
        return {"query": query, "error": str(e)}
    arts = d.get("articles") or []
    domains: dict[str, int] = {}
    for a in arts:
        domains[a.get("domain", "?")] = domains.get(a.get("domain", "?"), 0) + 1
    ranked = sorted(domains.items(), key=lambda kv: -kv[1])

    # Deduplicate on the opening of the headline: syndicated copy is the same
    # story in forty outlets, and forty outlets running one wire is one carrier,
    # not forty. What we want is the distinct CLAIMS in circulation.
    seen, titles = set(), []
    for a in arts:
        t = (a.get("title") or "").strip()
        k = t.lower()[:55]
        if t and k not in seen:
            seen.add(k)
            titles.append({"title": t, "domain": a.get("domain"),
                           "url": a.get("url"), "seendate": a.get("seendate")})
    return {"query": query, "articles": len(arts), "distinct_outlets": len(domains),
            "distinct_headlines": len(titles),
            "top_outlets": ranked[:15], "headlines": titles[:40]}


def attention(day: date | None = None, limit: int = 40) -> list[dict]:
    """What the public looked up, as a check on what the press pushed."""
    day = day or (datetime.now(timezone.utc).date() - timedelta(days=2))
    url = PAGEVIEWS_TOP.format(y=day.year, m=day.month, d=day.day)
    try:
        d = _get(url)
    except Exception as e:
        return [{"error": str(e), "day": day.isoformat()}]
    items = ((d.get("items") or [{}])[0]).get("articles", [])
    out = []
    for a in items:
        t = a.get("article", "")
        if SKIP.search(t):
            continue
        out.append({"article": t.replace("_", " "), "views": a.get("views"),
                    "rank": a.get("rank")})
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------

def cmd_scan(args) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    day = date.today().isoformat()
    report = {"_what_this_is": ("A volume reading, not a judgement. High coverage is a "
                               "necessary condition for a What Holds Up subject and nowhere "
                               "near a sufficient one: the test is whether a claim in "
                               "circulation outruns its evidence, and that needs reading."),
              "scanned": day, "timespan": args.timespan, "queries": [], "attention": []}

    for q in args.query:
        spread = outlet_spread(q, args.timespan)
        if spread.get("error"):
            report["queries"].append({"query": q, "error": spread["error"]})
            print("  %-40s ERROR %s" % (q[:40], spread["error"][:50]))
            continue
        row = dict(spread)
        row.update(coverage_volume(q, args.timespan) if not args.fast else
                   {"volume_unavailable": "--fast"})
        report["queries"].append(row)
        print("  %-38s %3s outlet(s) / %3s distinct headline(s)   spike %s"
              % (q[:38], row.get("distinct_outlets"), row.get("distinct_headlines"),
                 row.get("spike_ratio") or str(row.get("volume_unavailable", "-"))[:18]))
        for dom, n in (row.get("top_outlets") or [])[:5]:
            print("        %-34s %d" % (dom[:34], n))
        for a in (row.get("headlines") or [])[:8]:
            print("        \u2022 %-72s %s" % (str(a.get("title"))[:72],
                                                str(a.get("domain"))[:22]))

    if not args.no_attention:
        report["attention"] = attention()
        if report["attention"] and report["attention"][0].get("error"):
            print("\n  pageviews unavailable: %s" % report["attention"][0]["error"][:70])
        else:
            print("\n  most-read on en.wikipedia:")
            for a in report["attention"][:12]:
                print("    %-42s %s" % (a["article"][:42], f"{a['views']:,}"))

    p = OUT / f"{day}-scan.json"
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n  wrote %s" % p.relative_to(ROOT))
    print("  Nothing here is a subject yet. Run the funnel on anything that looks live:")
    print("    publish.py funnel <query>")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="what is being covered, and what is being read")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("query", nargs="+", help="one or more GDELT queries, quoted")
    s.add_argument("--timespan", default="14d")
    s.add_argument("--no-attention", action="store_true")
    s.add_argument("--fast", action="store_true",
                   help="skip the slow timeline call; outlet spread only")
    s.set_defaults(fn=cmd_scan)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
