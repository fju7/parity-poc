"""Gate a Signal topic's sources and claims and freeze the record. Flip nothing unless told.

    python scripts/publish_topic.py mmr-vaccine-autism            # gate + record, report; status untouched
    python scripts/publish_topic.py mmr-vaccine-autism --flip     # ALSO set signal_issues.status = 'published'

The record: backend/data/verify/published/<slug>/<publish_id>.json (and latest.json),
with the fetched documents content-addressed under backend/data/verify/docs/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from verify.publish import publish, PUBLISHED  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--flip", action="store_true", help="after the record is written, set status='published'")
    a = ap.parse_args()
    from supabase_client import supabase as sb
    if sb is None:
        sys.exit("SUPABASE_SERVICE_KEY not set")
    rec = publish(sb, a.slug, sys.argv)
    s = rec["summary"]
    print("\nSOURCES  total %d  survived %d  withheld %s" % (s["sources"]["total"], s["sources"]["survived"], s["sources"]["withheld_by_reason"]))
    print("         status of survivors:", s["sources"]["status_of_survivors"])
    print("CLAIMS   total %d  %s  identity_only_rate %.1f%%" % (s["claims"]["total"], s["claims"]["by_support"], 100 * s["claims"]["identity_only_rate"]))
    print("RECORD  ", PUBLISHED / a.slug / (rec["publish_id"] + ".json"), "|", rec.pop("_stored", ""))
    if a.flip:
        from verify.publish import store_publication
        sb.table("signal_issues").update({"status": "published"}).eq("id", rec["topic"]["issue_id"]).execute()
        rec["flipped"] = True
        (PUBLISHED / a.slug / "latest.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False))
        print("        ", store_publication(sb, rec))
        print("FLIPPED  signal_issues.status = 'published' for", a.slug, "-- record it in docs/signal-corpus-freeze.md")
    else:
        print("NOT FLIPPED (no --flip): status is", rec["topic"]["status_before"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
