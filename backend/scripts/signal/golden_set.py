"""
Golden-set regression for Signal's consensus mapping.

WHY THIS EXISTS
---------------
GLP-1 'pricing' was published as "debated" from March to August 2026. The
model behind the "claude-sonnet-4-6" alias had, at some point in between,
started calling it "consensus" — correctly, as reading the 44 claims confirms.
Nothing detected the change for five months. It surfaced by accident, during
unrelated work.

This turns that class of failure into a failing test. The fixture records what
the model ACTUALLY produced across all 52 categories on 2026-08-25 — not what
was published, since several published labels were already stale. A model
upgrade, a prompt edit, or a change to the claim corpus that moves a judgment
now shows up here.

The fixture is a baseline, not a statement of truth. A drift is not
automatically a regression: three of the five drifts found in the original
sweep were the model getting BETTER. The point is that a human sees the change
and decides, rather than the site quietly serving a stale answer.

Costs one API call per category (~52). Nothing is written to the database.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/golden_set.py --verify            # credentials only, no model calls
    python scripts/signal/golden_set.py                     # check, exit 1 on drift
    python scripts/signal/golden_set.py --slug glp1-drugs   # check one topic
    python scripts/signal/golden_set.py --record            # re-baseline (deliberate!)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import map_consensus as mc
from signal_model import prompt_version, warn_if_unpinned
from topic_config import get_topic

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "signal_consensus_golden.json"

# A debated category's side counts are the least stable thing measured — the
# model may cite 8/5 one run and 7/5 the next without the judgment changing.
# Only a swing beyond this, or a side collapsing to zero, is worth a failure.
SIDE_COUNT_TOLERANCE = 3


def load_fixture() -> dict:
    if not FIXTURE.exists():
        sys.exit(f"No golden set at {FIXTURE}. Run with --record to create one.")
    return json.loads(FIXTURE.read_text())


def measure(entries: list[dict]) -> list[dict]:
    """Run each category once. Returns entries with an added 'actual' block."""
    sb = mc._get_supabase()
    by_slug: dict[str, list[dict]] = {}
    for e in entries:
        by_slug.setdefault(e["slug"], []).append(e)

    measured = []
    for slug, group in by_slug.items():
        topic = get_topic(slug)
        _issue_id, by_category = mc.load_scored_claims(sb, slug)
        system_prompt = mc._build_consensus_system_prompt(topic)

        print(f"\n{topic['title']}  ({slug})   prompt {prompt_version(system_prompt)}")

        for e in group:
            claims = by_category.get(e["category"], [])
            if not claims:
                print(f"  {e['category']:26s} NO CLAIMS — category has emptied since baseline")
                measured.append({**e, "actual": None, "note": "no claims"})
                continue

            out = mc._call_claude(system_prompt, mc._build_category_prompt(e["category"], claims))
            if not isinstance(out, dict):
                print(f"  {e['category']:26s} API FAILED")
                measured.append({**e, "actual": None, "note": "api failed"})
                continue

            status = out.get("consensus_status")
            sides = [len(out.get("for_claim_ids") or []), len(out.get("against_claim_ids") or [])]
            measured.append({
                **e,
                "actual": {"status": status, "sides": sides if status == "debated" else None},
                "claims_now": len(claims),
            })
            mark = "ok  " if status == e["expected_status"] else "DRIFT"
            print(f"  {e['category']:26s} {mark} {e['expected_status']} -> {status}")
            time.sleep(0.5)

    return measured


def judge(measured: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split into (failures, warnings)."""
    failures, warnings = [], []
    for m in measured:
        if m["actual"] is None:
            warnings.append({**m, "why": m.get("note", "not measured")})
            continue

        if m["actual"]["status"] != m["expected_status"]:
            failures.append({**m, "why": f"{m['expected_status']} -> {m['actual']['status']}"})
            continue

        want, got = m.get("expected_debated_sides"), m["actual"]["sides"]
        if want and got:
            if not got[0] or not got[1]:
                failures.append({**m, "why": f"a side collapsed to zero: {want} -> {got}"})
            elif max(abs(want[0] - got[0]), abs(want[1] - got[1])) > SIDE_COUNT_TOLERANCE:
                warnings.append({**m, "why": f"side counts moved {want} -> {got}"})
    return failures, warnings


def verify() -> int:
    """Check that credentials and fixture are usable, without a real check run.

    Exists so that a CI misconfiguration — a secret missing, or named
    SUPABASE_SERVICE_ROLE_KEY (what Render calls it) instead of
    SUPABASE_SERVICE_KEY (what supabase_client.py reads) — is diagnosed in
    seconds for the price of a five-token call, rather than by watching 52
    category checks fail one after another with a connection error.
    """
    import os

    ok = True
    print("Credentials")
    for name in ("ANTHROPIC_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        val = os.environ.get(name, "")
        if not val:
            print(f"  {name:24s} MISSING")
            ok = False
        elif name == "SUPABASE_URL":
            print(f"  {name:24s} {val}")
        else:
            print(f"  {name:24s} set ({len(val)} chars, ...{val[-4:]})")

    if os.environ.get("SUPABASE_SERVICE_ROLE_KEY") and not os.environ.get("SUPABASE_SERVICE_KEY"):
        print("  NOTE: SUPABASE_SERVICE_ROLE_KEY is set but SUPABASE_SERVICE_KEY is not.")
        print("        supabase_client.py reads SUPABASE_SERVICE_KEY. Rename it.")

    print("\nFixture")
    try:
        fx = load_fixture()
        print(f"  {len(fx['categories'])} categories, recorded {fx.get('recorded_at')}")
    except SystemExit as exc:
        print(f"  {exc}")
        return 1

    print("\nSupabase")
    try:
        sb = mc._get_supabase()  # also sys.exits when unconfigured
        res = sb.table("signal_issues").select("slug").limit(1).execute()
        rows = res.data or []
        print(f"  reachable — signal_issues returned {len(rows)} row(s)")
        if not rows:
            print("  [WARN] no rows visible; the key may lack read access")
            ok = False
    except (Exception, SystemExit) as exc:
        why = "not configured (see message above)" if isinstance(exc, SystemExit) else exc
        print(f"  FAILED: {why}")
        ok = False

    print("\nAnthropic")
    try:
        # SystemExit as well as Exception: _get_anthropic_client calls sys.exit
        # when the key is absent, which would otherwise kill this check before
        # it printed its verdict — the one line the operator is reading for.
        client = mc._get_anthropic_client()
        r = client.messages.create(
            model=mc.SCORING_MODEL, max_tokens=5,
            messages=[{"role": "user", "content": "hi"}],
        )
        print(f"  reachable — requested {mc.SCORING_MODEL}, resolved {r.model}")
    except (Exception, SystemExit) as exc:
        why = "not configured (see message above)" if isinstance(exc, SystemExit) else exc
        print(f"  FAILED: {why}")
        ok = False

    print("\n" + ("Ready. A full check would run 52 categories." if ok else "NOT ready — fix the above."))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true",
                    help="Check credentials, fixture and connectivity, then exit. "
                         "One five-token model call; no category is measured.")
    ap.add_argument("--slug", help="Check one topic only")
    ap.add_argument("--record", action="store_true",
                    help="Overwrite the fixture with current output. Deliberate act — "
                         "never do this to silence a failure you have not understood.")
    args = ap.parse_args()

    if args.verify:
        return verify()

    fixture = load_fixture()
    entries = fixture["categories"]
    if args.slug:
        entries = [e for e in entries if e["slug"] == args.slug]
        if not entries:
            sys.exit(f"No golden-set entries for slug '{args.slug}'.")

    print(f"Golden set recorded {fixture.get('recorded_at')} on {fixture.get('model')}")
    print(f"Checking {len(entries)} categories against {mc.SCORING_MODEL}")
    warn_if_unpinned(mc.SCORING_MODEL)

    measured = measure(entries)

    if args.record:
        fixture["categories"] = [
            {
                "slug": m["slug"],
                "category": m["category"],
                "claims": m.get("claims_now", m["claims"]),
                "expected_status": m["actual"]["status"] if m["actual"] else m["expected_status"],
                "expected_debated_sides": m["actual"]["sides"] if m["actual"] else None,
            }
            for m in measured
        ]
        fixture["model"] = mc.LAST_RESOLVED_MODEL or mc.SCORING_MODEL
        FIXTURE.write_text(json.dumps(fixture, indent=2) + "\n")
        print(f"\nRe-baselined {len(measured)} categories -> {FIXTURE}")
        print("Commit this with an explanation of WHY the baseline moved.")
        return 0

    failures, warnings = judge(measured)

    print(f"\n{'=' * 70}\nGOLDEN SET\n{'=' * 70}")
    print(f"Checked:  {len(measured)}")
    print(f"Matched:  {len(measured) - len(failures) - len(warnings)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Failures: {len(failures)}")

    for label, items in (("WARNINGS", warnings), ("FAILURES", failures)):
        if items:
            print(f"\n{label}")
            for i in items:
                print(f"  {i['slug']:52s} {i['category']:26s} {i['why']}")

    if failures:
        print("\nA judgment moved. That is not automatically wrong — three of the five")
        print("drifts in the original sweep were the model improving. Read the claims,")
        print("decide, and re-baseline with --record only once you understand it.")
        return 1

    print("\nNo published judgment moved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
