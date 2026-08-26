"""
Measure how far Signal's PUBLISHED consensus labels have drifted from what the
current model produces on the SAME evidence.

Why this exists
---------------
GLP-1 'pricing' has been published as "debated" since March. Re-running the
identical prompt against the identical claims now returns "consensus", and
reading the 44 claims confirms the current answer is the correct one — there is
no opposing evidence in that category. Nothing detected that for five months.

Meanwhile social-media 'depression_anxiety' returns "debated" under three
different prompt variants, so the model is not simply flattening everything.
Borderline judgments move; well-separated ones hold.

Two data points is not a measurement. This runs every category of every
approved topic once and reports how many published labels the current model
still agrees with — so the size of the problem is known before anything is
rebuilt to fix it.

STRICTLY READ-ONLY. No consensus rows are created, updated or deleted. The only
thing written is a local JSON report.

Cost: one API call per category (~53 for nine topics). Results are appended to
the report file as they arrive, so an interrupted run loses nothing — re-run
with --resume to skip categories already done.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/stability_sweep.py                    # all approved topics
    python scripts/signal/stability_sweep.py --issue-slug glp1-drugs
    python scripts/signal/stability_sweep.py --resume           # continue an interrupted run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import map_consensus as mc
from topic_config import get_topic

REPORT_PATH = Path(__file__).resolve().parents[2] / "data" / "signal" / "stability_sweep.json"


def approved_slugs(sb) -> list[str]:
    """Slugs of every quality-approved topic, oldest first."""
    res = (
        sb.table("signal_issues")
        .select("slug, quality_review_status")
        .eq("quality_review_status", "approved")
        .execute()
    )
    return sorted(r["slug"] for r in (res.data or []) if r.get("slug"))


def published_consensus(sb, issue_id: str) -> dict[str, dict]:
    """Currently published consensus rows, keyed by category."""
    res = (
        sb.table("signal_consensus")
        .select("category, consensus_status, mapped_at")
        .eq("issue_id", issue_id)
        .execute()
    )
    return {r["category"]: r for r in (res.data or [])}


def load_report() -> dict:
    if REPORT_PATH.exists():
        try:
            return json.loads(REPORT_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"model": mc.SCORING_MODEL, "results": []}


def save_report(report: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--issue-slug", help="Sweep one topic instead of all approved topics")
    ap.add_argument("--resume", action="store_true", help="Skip categories already in the report")
    args = ap.parse_args()

    sb = mc._get_supabase()
    slugs = [args.issue_slug] if args.issue_slug else approved_slugs(sb)

    report = load_report() if args.resume else {"model": mc.SCORING_MODEL, "results": []}
    done = {(r["slug"], r["category"]) for r in report["results"]}

    print(f"\nModel: {mc.SCORING_MODEL} (temperature 0)")
    print(f"Topics: {len(slugs)}")
    print("READ-ONLY — no consensus rows will be written.\n")

    for slug in slugs:
        topic = get_topic(slug)
        issue_id, by_category = mc.load_scored_claims(sb, slug)
        pub = published_consensus(sb, issue_id)
        system_prompt = mc._build_consensus_system_prompt(topic)

        print(f"\n{'=' * 70}\n{topic['title']}  ({slug})\n{'=' * 70}")

        for category in topic["categories"]:
            claims = by_category.get(category, [])
            if not claims:
                print(f"  {category:22s} no claims, skipped")
                continue
            if args.resume and (slug, category) in done:
                print(f"  {category:22s} already done, skipped")
                continue

            was = (pub.get(category) or {}).get("consensus_status")
            print(f"  {category:22s} published={str(was):10s} ...", end=" ", flush=True)

            out = mc._call_claude(system_prompt, mc._build_category_prompt(category, claims))
            if not isinstance(out, dict):
                print("API FAILED")
                continue

            now = out.get("consensus_status")
            n_for = len(out.get("for_claim_ids") or [])
            n_against = len(out.get("against_claim_ids") or [])
            agrees = (was == now)

            sides = f"  sides {n_for}/{n_against}" if now == "debated" else ""
            print(f"now={now:10s} {'OK' if agrees else 'DRIFT'}{sides}")

            report["results"].append({
                "slug": slug,
                "category": category,
                "claims": len(claims),
                "published": was,
                "current": now,
                "agrees": agrees,
                "mapped_at": (pub.get(category) or {}).get("mapped_at"),
                "for_claim_count": n_for,
                "against_claim_count": n_against,
            })
            save_report(report)
            time.sleep(0.5)

    summarise(report)


def summarise(report: dict) -> None:
    rows = report["results"]
    if not rows:
        print("\nNothing measured.")
        return

    agree = [r for r in rows if r["agrees"]]
    drift = [r for r in rows if not r["agrees"]]

    print(f"\n\n{'=' * 70}")
    print("STABILITY SWEEP")
    print(f"{'=' * 70}")
    print(f"Model measured:      {report.get('model')}")
    print(f"Categories measured: {len(rows)}")
    print(f"Still agree:         {len(agree)}  ({len(agree) / len(rows):.0%})")
    print(f"Drifted:             {len(drift)}  ({len(drift) / len(rows):.0%})")

    if drift:
        transitions = Counter(f"{r['published']} -> {r['current']}" for r in drift)
        print("\nHow they moved:")
        for t, n in transitions.most_common():
            print(f"  {n:3d}  {t}")

        lost = [r for r in drift if r["published"] == "debated" and r["current"] != "debated"]
        gained = [r for r in drift if r["published"] != "debated" and r["current"] == "debated"]
        print(f"\nDebates lost:   {len(lost)}")
        print(f"Debates gained: {len(gained)}")

        print("\nEvery drifted category:")
        for r in sorted(drift, key=lambda r: (r["slug"], r["category"])):
            print(f"  {r['slug']:52s} {r['category']:22s} {r['published']} -> {r['current']}")

    debated_now = [r for r in rows if r["current"] == "debated"]
    if debated_now:
        empty = [r for r in debated_now if not r["for_claim_count"] and not r["against_claim_count"]]
        print(f"\nDebated under the current model: {len(debated_now)}")
        print(f"  with side attribution:    {len(debated_now) - len(empty)}")
        print(f"  WITHOUT side attribution: {len(empty)}")
        if empty:
            print("  (a debate the model cannot cite evidence for is worth inspecting)")

    print(f"\nFull report: {REPORT_PATH}")
    print("No consensus rows were written.")


if __name__ == "__main__":
    main()
