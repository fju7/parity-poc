#!/usr/bin/env python3
"""
What Holds Up: the reader-corrections register.

WHY THIS EXISTS
---------------
Every page on this site ends with the same promise:

    Think we got something wrong? corrections@whatholdsup.org --
    acknowledged in 48 hours, resolved or explained within 10 business days.

Nothing anywhere kept that promise. There was no register, no clock, no route
from a reader's email to a change on the page, and no record of a correction
we *declined* -- which is the half that matters most, because a publication
that only records the corrections it accepted has not published a correction
history, it has published a list of things it already agreed with.

The register is deliberately dumber than it could be. It does not read email.
Somebody pastes in what a reader said, and from that moment there is a clock
and a row that cannot be quietly closed.

THE FOUR STATES
---------------
    received     logged, clock started
    acknowledged we told the reader we had it, within 48 hours
    adjudicated  we decided: upheld, partly upheld, or declined -- with reasons
    closed       the reader has been told what we did, and if we changed the
                 page, corrections.md carries it

A row is not closed by being fixed. It is closed by the reader being told. The
distinction is the whole point: issue two's own corrections came from a reader
who had no way of knowing whether anything happened to them.

WHAT BLOCKS A PUBLISH
---------------------
An overdue acknowledgement, or an adjudicated correction against an issue that
is publishing again without the correction recorded. Not an open item in
itself -- ten business days is a real amount of time and blocking on day two
would just teach everyone to waive.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTER = ROOT / "backend" / "data" / "whatholdsup" / "corrections.json"
CASES = ROOT / "issues"

OK, BAD, WARN = "ok", "BLOCKED", "warn"

ACK_HOURS = 48
RESOLVE_BUSINESS_DAYS = 10

STATES = ("received", "acknowledged", "adjudicated", "closed")
VERDICTS = ("upheld", "partly_upheld", "declined")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load() -> dict:
    if not REGISTER.exists():
        return {"_what_this_is": __doc__.strip().splitlines()[1], "items": []}
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def save(d: dict) -> None:
    REGISTER.parent.mkdir(parents=True, exist_ok=True)
    REGISTER.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")


def next_id(items: list[dict]) -> str:
    n = 0
    for it in items:
        m = re.match(r"COR-(\d+)", it.get("id", ""))
        if m:
            n = max(n, int(m.group(1)))
    return f"COR-{n + 1:03d}"


def business_days_since(iso: str) -> int:
    try:
        d0 = datetime.fromisoformat(iso).date()
    except Exception:
        return 0
    d, n = d0, 0
    today = date.today()
    while d < today:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def hours_since(iso: str) -> float:
    try:
        t = datetime.fromisoformat(iso)
    except Exception:
        return 0.0
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds() / 3600


# ---------------------------------------------------------------------------

def cmd_log(args) -> int:
    d = load()
    item = {
        "id": next_id(d["items"]),
        "received": args.on or _now(),
        "from": args.sender,
        "issue": args.issue,
        "claim": args.claim,
        "state": "received",
        "acknowledged": None,
        "adjudication": None,
        "closed": None,
        "history": [{"at": _now(), "by": args.by, "what": "logged"}],
    }
    d["items"].append(item)
    save(d)
    print(f"  {item['id']}  logged against {args.issue}")
    print(f"  Acknowledge within {ACK_HOURS} hours — the site promises it in writing.")
    return 0


def cmd_ack(args) -> int:
    d = load()
    for it in d["items"]:
        if it["id"] == args.id:
            it["acknowledged"] = {"at": _now(), "by": args.by, "note": args.note or ""}
            it["state"] = "acknowledged"
            it["history"].append({"at": _now(), "by": args.by, "what": "acknowledged"})
            save(d)
            print(f"  {args.id} acknowledged after "
                  f"{hours_since(it['received']):.1f}h")
            return 0
    print(f"no item {args.id}"); return 1


def cmd_adjudicate(args) -> int:
    d = load()
    for it in d["items"]:
        if it["id"] != args.id:
            continue
        it["adjudication"] = {
            "at": _now(), "by": args.by, "verdict": args.verdict,
            "reason": args.reason,
            "checked": args.checked or "",
        }
        it["state"] = "adjudicated"
        it["history"].append({"at": _now(), "by": args.by,
                              "what": f"adjudicated {args.verdict}"})
        save(d)
        print(f"  {args.id}: {args.verdict}")
        if args.verdict != "declined":
            print("  Now: change the page, add the corrections.md entry, then close "
                  "this by telling the reader what you did.")
        else:
            print("  Declined corrections are published too. The reason above is "
                  "what a reader sees if they ask.")
        return 0
    print(f"no item {args.id}"); return 1


def cmd_close(args) -> int:
    d = load()
    for it in d["items"]:
        if it["id"] != args.id:
            continue
        if not it.get("adjudication"):
            print(f"  {args.id} has no adjudication. A correction is not closed by "
                  f"being fixed; it is closed by the reader being told what we "
                  f"decided, and nothing has been decided.")
            return 1
        it["closed"] = {"at": _now(), "by": args.by,
                        "told_the_reader": args.told,
                        "recorded_in": args.recorded or ""}
        it["state"] = "closed"
        it["history"].append({"at": _now(), "by": args.by, "what": "closed"})
        save(d)
        print(f"  {args.id} closed after {business_days_since(it['received'])} "
              f"business day(s)")
        return 0
    print(f"no item {args.id}"); return 1


# ---------------------------------------------------------------------------

def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    d = load()
    mine = [i for i in d["items"] if i.get("issue") == slug]
    if not mine:
        return [("reader corrections", OK, "none logged against this issue")]

    overdue_ack = [i for i in mine
                   if not i.get("acknowledged")
                   and hours_since(i["received"]) > ACK_HOURS]
    open_ = [i for i in mine if i["state"] != "closed"]
    overdue_res = [i for i in open_
                   if business_days_since(i["received"]) > RESOLVE_BUSINESS_DAYS]

    rows = [("reader corrections", OK if not open_ else WARN,
             f"{len(mine)} logged, {len(open_)} open"
             + ("" if not open_ else ": " + ", ".join(i["id"] for i in open_[:5])))]

    rows.append(("acknowledged in 48h", OK if not overdue_ack else BAD,
                 "every correction acknowledged inside the promised window"
                 if not overdue_ack else
                 f"{len(overdue_ack)} past {ACK_HOURS}h with no acknowledgement — "
                 f"who-pays-for-this promises this in writing: "
                 + ", ".join(i["id"] for i in overdue_ack)))

    rows.append(("resolved in 10 business days", OK if not overdue_res else BAD,
                 "nothing past the promised window"
                 if not overdue_res else
                 f"{len(overdue_res)} past {RESOLVE_BUSINESS_DAYS} business days: "
                 + ", ".join(i["id"] for i in overdue_res)))

    # An upheld correction that has not reached the public history.
    upheld = [i for i in mine
              if (i.get("adjudication") or {}).get("verdict") in ("upheld", "partly_upheld")]
    case = sorted(CASES.glob(f"WHU-*-{slug}"))
    cm = (case[0] / "corrections.md") if case else None
    text = cm.read_text(encoding="utf-8") if (cm and cm.exists()) else ""
    unrecorded = [i["id"] for i in upheld
                  if i.get("closed") and not (i["closed"].get("recorded_in") or "").strip()
                  and i["id"] not in text]
    rows.append(("upheld corrections published", OK if not unrecorded else BAD,
                 "every upheld correction reached corrections.md"
                 if not unrecorded else
                 f"{len(unrecorded)} upheld and not in the public history: "
                 + ", ".join(unrecorded)))
    return rows


def cmd_status(args) -> int:
    d = load()
    items = [i for i in d["items"] if not args.issue or i.get("issue") == args.issue]
    print()
    if not items:
        print("  nothing logged")
        return 0
    print(f"  {'id':9} {'issue':10} {'state':13} {'age':>10}  from")
    print("  " + "-" * 64)
    for i in items:
        age = f"{business_days_since(i['received'])}bd"
        print(f"  {i['id']:9} {i.get('issue',''):10} {i['state']:13} {age:>10}  "
              f"{i.get('from','')[:24]}")
        print(f"      {str(i.get('claim',''))[:88]}")
        adj = i.get("adjudication")
        if adj:
            print(f"      -> {adj['verdict']}: {str(adj.get('reason',''))[:70]}")
    print()
    if args.issue:
        for label, st, detail in preflight_rows(args.issue):
            print(f"{ {OK:'  ok ', BAD:' STOP', WARN:' warn'}[st]:>7}  {label:30} {detail}")
        print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="the reader-corrections register")
    sub = ap.add_subparsers(dest="cmd", required=True)

    l = sub.add_parser("log", help="a reader wrote in")
    l.add_argument("--issue", required=True)
    l.add_argument("--sender", required=True, help="who wrote, as they signed it")
    l.add_argument("--claim", required=True, help="what they say is wrong, in their terms")
    l.add_argument("--on", help="ISO timestamp the email arrived; defaults to now")
    l.add_argument("--by", default="operator")
    l.set_defaults(fn=cmd_log)

    a = sub.add_parser("ack", help="we replied to say we have it")
    a.add_argument("id"); a.add_argument("--by", default="operator"); a.add_argument("--note")
    a.set_defaults(fn=cmd_ack)

    j = sub.add_parser("adjudicate", help="we decided, with reasons")
    j.add_argument("id")
    j.add_argument("--verdict", choices=VERDICTS, required=True)
    j.add_argument("--reason", required=True,
                   help="why. This is what a reader sees if they ask, including "
                        "when we decline.")
    j.add_argument("--checked", help="what we opened to decide — a source, a section")
    j.add_argument("--by", default="operator")
    j.set_defaults(fn=cmd_adjudicate)

    c = sub.add_parser("close", help="the reader has been told what we did")
    c.add_argument("id")
    c.add_argument("--told", required=True, help="what we told them, in one line")
    c.add_argument("--recorded", help="where it reached readers — a corrections.md heading")
    c.add_argument("--by", default="operator")
    c.set_defaults(fn=cmd_close)

    s = sub.add_parser("status"); s.add_argument("--issue"); s.set_defaults(fn=cmd_status)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
