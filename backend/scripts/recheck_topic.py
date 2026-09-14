"""Re-check a published topic against its frozen record. Never edits the record, never flips status.

    python scripts/recheck_topic.py mmr-vaccine-autism --kind status     # weekly: the fifth check
    python scripts/recheck_topic.py mmr-vaccine-autism --kind bindings   # monthly: re-fetch and re-bind
    python scripts/recheck_topic.py --all --kind status                  # every topic with a record

Exit 1 on any binding_lost or status_changed, so the scheduled job fails where the operator is told.
Writes backend/data/verify/rechecks/<slug>/<run_id>-<kind>.json and, when the topic_rechecks
table exists, a row the page renders from.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from verify.recheck import recheck, PUBLISHED  # noqa: E402


def _store(sb, out: dict) -> str:
    if sb is None:
        return "no service key: not stored"
    try:
        sb.table("topic_rechecks").upsert({
            "slug": out["slug"], "run_id": out["run_id"], "run_at": out["run_at"], "kind": out["kind"],
            "outcomes": out["summary"], "flags": out["flags"], "exit_ok": out["exit_ok"],
        }, on_conflict="slug,run_id").execute()
        return "stored in topic_rechecks"
    except Exception as e:  # noqa: BLE001
        return f"NOT stored ({type(e).__name__}: {str(e)[:80]}) -- is migration 080 applied?"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--kind", choices=["status", "bindings"], default="status")
    a = ap.parse_args()
    slugs = [p.name for p in PUBLISHED.iterdir() if (p / "latest.json").exists()] if a.all else [a.slug]
    if not slugs or slugs == [None]:
        ap.error("a slug or --all")
    try:
        from supabase_client import supabase as sb
    except Exception:
        sb = None
    ok = True
    for slug in slugs:
        out = recheck(slug, a.kind)
        ok &= out["exit_ok"]
        print(f"{slug} [{a.kind}] sources {out['summary']['sources']} claims {out['summary']['claims']} "
              f"flags {out['summary']['flags']} -> {'ok' if out['exit_ok'] else 'ALERT'}; {_store(sb, out)}")
        for f in out["flags"]:
            print(f"   {f['scope']:6} {f['outcome']:15} {f.get('source_id') or f.get('claim_id')} {f.get('verdict') or f.get('detail','')[:70]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
