#!/usr/bin/env python3
"""Reconcile the Resend audience with whatholdsup_subscribers.

    python3 scripts/whatholdsup/sync_subscribers.py            # report only
    python3 scripts/whatholdsup/sync_subscribers.py --apply    # write

WHY THIS EXISTS
---------------
Subscribers now live in two places on purpose: whatholdsup_subscribers is the
record of who signed up and when, and the Resend audience is the list mail
actually goes to. Two places means drift, and drift in this direction is
invisible until someone does not receive an issue:

  in Resend, not in our record   a subscriber with no history. Everyone who
                                 signed up before the table existed is here
  in our record, no contact id   recorded, receiving nothing. This is the
                                 work-queue index on the table
  contact id missing but the     the link failed after both writes succeeded;
  contact exists                 harmless, but it hides real work-queue rows

It never deletes and never unsubscribes anyone. Removing somebody is an
unsubscribe, which has its own endpoint and its own table.

Reads RESEND_WHATHOLDSUP_KEY, SUPABASE_URL and SUPABASE_SERVICE_KEY from
backend/.env. Uses the Resend SDK rather than a hand-rolled request, because
Cloudflare in front of api.resend.com blocks urllib's fingerprint with a 403
and no explanation — a lesson already recorded in send_broadcast.py and
relearned the hard way on 2026-08-28.
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
ENVFILE = ROOT / "backend" / ".env"
AUDIENCE = "bae12ea6-cbad-4b91-b250-81991bf6b4b5"
TABLE = "whatholdsup_subscribers"


def env() -> dict:
    out = {}
    if not ENVFILE.exists():
        sys.exit("[ERROR] %s is missing." % ENVFILE)
    for line in ENVFILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def mask(addr: str) -> str:
    """Addresses are printed masked. A terminal is a place things get pasted."""
    return re.sub(r"^(.).*?(@.*)$", r"\1***\2", addr or "")


def resend_contacts(key: str) -> list:
    try:
        import resend
    except ImportError:
        sys.exit("[ERROR] The resend package is missing. Run: pip install resend")
    resend.api_key = key
    r = resend.Contacts.list(audience_id=AUDIENCE)
    return (r.get("data") if isinstance(r, dict) else r) or []


def db(cfg, method, path, body=None, prefer=None):
    url = cfg["SUPABASE_URL"].rstrip("/") + path
    headers = {"apikey": cfg["SUPABASE_SERVICE_KEY"],
               "Authorization": "Bearer " + cfg["SUPABASE_SERVICE_KEY"],
               "Content-Type": "application/json"}
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip() else None)
    except urllib.error.HTTPError as e:
        sys.exit("[ERROR] %s %s -> HTTP %s: %s"
                 % (method, path, e.code, e.read().decode()[:300]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true",
                    help="write the changes; without it this only reports")
    args = ap.parse_args()
    cfg = env()
    for need in ("RESEND_WHATHOLDSUP_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        if not cfg.get(need):
            sys.exit("[ERROR] %s is not in %s" % (need, ENVFILE))

    contacts = resend_contacts(cfg["RESEND_WHATHOLDSUP_KEY"])
    by_email = {(c.get("email") or "").lower(): c for c in contacts if c.get("email")}
    _code, rows = db(cfg, "GET", "/rest/v1/%s?select=*" % TABLE)
    rows = rows or []
    recorded = {(r.get("email") or "").lower(): r for r in rows}

    missing = [e for e in by_email if e not in recorded]
    unlinked = [e for e, r in recorded.items()
                if not r.get("resend_contact_id") and e in by_email]
    orphaned = [e for e in recorded if e not in by_email]

    print()
    print("  Resend audience : %d contact(s)" % len(by_email))
    print("  our record      : %d row(s)" % len(recorded))
    print()
    print("  %d to insert (in Resend, no record)" % len(missing))
    for e in sorted(missing):
        print("      %s  signed up %s" % (mask(e), (by_email[e].get("created_at") or "?")[:19]))
    print("  %d to link (recorded, contact id missing)" % len(unlinked))
    for e in sorted(unlinked):
        print("      %s" % mask(e))
    print("  %d recorded with no Resend contact — these receive nothing" % len(orphaned))
    for e in sorted(orphaned):
        print("      %s  source=%s" % (mask(e), recorded[e].get("source")))

    if not args.apply:
        print()
        print("  Report only. Re-run with --apply to insert and link.")
        print("  Nothing is ever deleted or unsubscribed by this script.")
        print()
        return 0

    for e in sorted(missing):
        c = by_email[e]
        payload = {"email": e, "source": "import",
                   "resend_contact_id": c.get("id") or None}
        # Keep the real signup date rather than now(). When somebody joined is
        # the fact this table exists to hold; overwriting it with the migration
        # date would destroy the only history there is.
        if c.get("created_at"):
            payload["subscribed_at"] = c["created_at"]
        db(cfg, "POST", "/rest/v1/%s?on_conflict=email" % TABLE, payload,
           "resolution=ignore-duplicates,return=minimal")
        print("  inserted %s" % mask(e))

    for e in sorted(unlinked):
        db(cfg, "PATCH",
           "/rest/v1/%s?email=eq.%s" % (TABLE, urllib.parse.quote(e)),
           {"resend_contact_id": by_email[e].get("id")}, "return=minimal")
        print("  linked   %s" % mask(e))

    print()
    print("  Done. %d inserted, %d linked, %d left needing a human."
          % (len(missing), len(unlinked), len(orphaned)))
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
