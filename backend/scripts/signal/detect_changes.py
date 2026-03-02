"""
Parity Signal: Evidence Change Detection.

Compares current pipeline state (claims, composites, consensus, sources) against
a locally stored snapshot from the previous run. Detects four types of changes
and writes them to signal_evidence_updates.

Change types:
  score_shift       — A claim's composite score changed by >= threshold (default 0.5)
  consensus_change  — A category's consensus_status changed
  new_claim         — A claim exists that wasn't in the previous snapshot
  new_source        — A source was added since last detection

On first run (no snapshot), saves the current state as baseline and detects nothing.
On subsequent runs, compares current vs snapshot, writes changes, saves new snapshot.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/detect_changes.py --dry-run
    python scripts/signal/detect_changes.py
    python scripts/signal/detect_changes.py --threshold 1.0
    python scripts/signal/detect_changes.py --force
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Add backend/ to sys.path so we can import supabase_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "signal" / "pipeline_snapshot.json"
DEFAULT_THRESHOLD = 0.5

EVIDENCE_CATEGORIES = [
    (4.0, "strong"),
    (3.0, "moderate"),
    (2.0, "mixed"),
    (0.0, "weak"),
]


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _get_supabase():
    """Import and return the Supabase client, or exit with message."""
    from supabase_client import supabase as sb
    if sb is None:
        print("ERROR: Supabase client not initialized.")
        print("Set SUPABASE_SERVICE_KEY environment variable before running.")
        sys.exit(1)
    return sb


def _score_to_category(score: float) -> str:
    """Map a composite score to an evidence category."""
    for threshold, cat in EVIDENCE_CATEGORIES:
        if score >= threshold:
            return cat
    return "weak"


# ---------------------------------------------------------------------------
# Load current state from Supabase
# ---------------------------------------------------------------------------

def load_current_state(sb) -> dict:
    """Read current claims, composites, consensus, and sources from Supabase.

    Returns a dict matching the snapshot schema.
    """
    # Get the GLP-1 issue
    resp = sb.table("signal_issues").select("id").eq("slug", "glp1-drugs").execute()
    if not resp.data:
        print("ERROR: No 'glp1-drugs' issue found. Run earlier pipeline steps first.")
        sys.exit(1)
    issue_id = resp.data[0]["id"]

    # Claims
    resp = (
        sb.table("signal_claims")
        .select("id")
        .eq("issue_id", issue_id)
        .execute()
    )
    claim_ids = [r["id"] for r in (resp.data or [])]

    # Composites
    claim_composites: dict[str, dict] = {}
    chunk_size = 50
    for i in range(0, len(claim_ids), chunk_size):
        chunk = claim_ids[i:i + chunk_size]
        resp = (
            sb.table("signal_claim_composites")
            .select("claim_id, composite_score, evidence_category")
            .in_("claim_id", chunk)
            .execute()
        )
        for row in (resp.data or []):
            claim_composites[row["claim_id"]] = {
                "score": float(row["composite_score"]),
                "category": row["evidence_category"],
            }

    # Consensus
    resp = (
        sb.table("signal_consensus")
        .select("category, consensus_status")
        .eq("issue_id", issue_id)
        .execute()
    )
    consensus = {row["category"]: row["consensus_status"] for row in (resp.data or [])}

    # Sources
    resp = (
        sb.table("signal_sources")
        .select("id")
        .eq("issue_id", issue_id)
        .execute()
    )
    source_ids = [r["id"] for r in (resp.data or [])]

    state = {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "issue_id": issue_id,
        "claim_composites": claim_composites,
        "consensus": consensus,
        "claim_ids": claim_ids,
        "source_ids": source_ids,
    }

    print(f"Loaded current state:")
    print(f"  Issue: {issue_id}")
    print(f"  Claims: {len(claim_ids)} ({len(claim_composites)} with composites)")
    print(f"  Consensus mappings: {len(consensus)}")
    print(f"  Sources: {len(source_ids)}")

    return state


# ---------------------------------------------------------------------------
# Snapshot I/O
# ---------------------------------------------------------------------------

def load_snapshot() -> dict | None:
    """Read previous snapshot from JSON file. Returns None if first run."""
    if not SNAPSHOT_PATH.exists():
        return None
    try:
        with open(SNAPSHOT_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [WARN] Could not read snapshot: {exc}")
        return None


def save_snapshot(state: dict) -> None:
    """Write current state as the new snapshot."""
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOT_PATH, "w") as f:
        json.dump(state, f, indent=2)
    print(f"Snapshot saved to {SNAPSHOT_PATH}")


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------

def detect_score_shifts(current: dict, previous: dict, threshold: float) -> list[dict]:
    """Compare composite scores, flag shifts >= threshold."""
    changes = []
    prev_composites = previous.get("claim_composites", {})
    curr_composites = current.get("claim_composites", {})

    for claim_id, curr in curr_composites.items():
        prev = prev_composites.get(claim_id)
        if prev is None:
            continue  # new claim — handled by detect_new_claims

        score_delta = abs(curr["score"] - prev["score"])
        if score_delta >= threshold:
            changes.append({
                "issue_id": current["issue_id"],
                "change_type": "score_shift",
                "claim_id": claim_id,
                "details": {
                    "previous_score": prev["score"],
                    "new_score": curr["score"],
                    "previous_category": prev["category"],
                    "new_category": curr["category"],
                    "delta": round(score_delta, 2),
                },
            })

    return changes


def detect_consensus_changes(current: dict, previous: dict) -> list[dict]:
    """Compare consensus statuses per category."""
    changes = []
    prev_consensus = previous.get("consensus", {})
    curr_consensus = current.get("consensus", {})

    for category, curr_status in curr_consensus.items():
        prev_status = prev_consensus.get(category)
        if prev_status is not None and prev_status != curr_status:
            changes.append({
                "issue_id": current["issue_id"],
                "change_type": "consensus_change",
                "details": {
                    "category": category,
                    "previous_status": prev_status,
                    "new_status": curr_status,
                },
            })

    return changes


def detect_new_claims(current: dict, previous: dict) -> list[dict]:
    """Set difference on claim IDs."""
    prev_ids = set(previous.get("claim_ids", []))
    curr_ids = set(current.get("claim_ids", []))
    new_ids = curr_ids - prev_ids

    changes = []
    for claim_id in sorted(new_ids):
        changes.append({
            "issue_id": current["issue_id"],
            "change_type": "new_claim",
            "claim_id": claim_id,
            "details": {
                "claim_id": claim_id,
            },
        })

    return changes


def detect_new_sources(current: dict, previous: dict) -> list[dict]:
    """Set difference on source IDs."""
    prev_ids = set(previous.get("source_ids", []))
    curr_ids = set(current.get("source_ids", []))
    new_ids = curr_ids - prev_ids

    changes = []
    for source_id in sorted(new_ids):
        changes.append({
            "issue_id": current["issue_id"],
            "change_type": "new_source",
            "details": {
                "source_id": source_id,
            },
        })

    return changes


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def store_updates(sb, updates: list[dict]) -> int:
    """Insert change records into signal_evidence_updates. Returns count inserted."""
    inserted = 0
    for update in updates:
        row = {
            "issue_id": update["issue_id"],
            "change_type": update["change_type"],
            "details": update.get("details", {}),
        }
        # Attach claim_id if present
        if update.get("claim_id"):
            row["claim_id"] = update["claim_id"]

        try:
            sb.table("signal_evidence_updates").insert(row).execute()
            inserted += 1
        except Exception as exc:
            print(f"  [ERROR] Failed to insert update ({update['change_type']}): {exc}")

    return inserted


# ---------------------------------------------------------------------------
# CLI orchestrator
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Detect evidence changes by comparing current state against previous snapshot."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be detected without DB writes or snapshot update",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-detect even if no snapshot change (overwrites snapshot)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Score shift threshold (default: {DEFAULT_THRESHOLD})",
    )
    args = parser.parse_args()

    sb = _get_supabase()
    current = load_current_state(sb)

    # Load previous snapshot
    previous = load_snapshot()

    if previous is None:
        print(f"\nNo previous snapshot found — this is the first run (baseline).")
        if args.dry_run:
            print("  [DRY RUN] Would save baseline snapshot. No changes to detect.")
            return
        save_snapshot(current)
        print("Baseline snapshot saved. No changes to detect on first run.")
        return

    # Compare
    print(f"\nPrevious snapshot from: {previous.get('snapshot_at', 'unknown')}")
    print(f"Score shift threshold: {args.threshold}")

    all_changes: list[dict] = []

    score_shifts = detect_score_shifts(current, previous, args.threshold)
    all_changes.extend(score_shifts)

    consensus_changes = detect_consensus_changes(current, previous)
    all_changes.extend(consensus_changes)

    new_claims = detect_new_claims(current, previous)
    all_changes.extend(new_claims)

    new_sources = detect_new_sources(current, previous)
    all_changes.extend(new_sources)

    # --- Dry run ---
    if args.dry_run:
        print(f"\n--- DRY RUN MODE (no DB writes, no snapshot update) ---\n")
        print(f"Changes detected: {len(all_changes)}")
        print(f"  Score shifts (>={args.threshold}): {len(score_shifts)}")
        print(f"  Consensus changes: {len(consensus_changes)}")
        print(f"  New claims: {len(new_claims)}")
        print(f"  New sources: {len(new_sources)}")

        if score_shifts:
            print(f"\nScore shifts:")
            for c in score_shifts:
                d = c["details"]
                print(f"  {c['claim_id'][:8]}... "
                      f"{d['previous_score']:.2f} ({d['previous_category']}) -> "
                      f"{d['new_score']:.2f} ({d['new_category']}) "
                      f"[delta: {d['delta']}]")

        if consensus_changes:
            print(f"\nConsensus changes:")
            for c in consensus_changes:
                d = c["details"]
                print(f"  {d['category']}: {d['previous_status']} -> {d['new_status']}")

        print(f"\nWould write {len(all_changes)} rows to signal_evidence_updates")
        print(f"Would NOT update snapshot")
        return

    # --- Store changes ---
    if not all_changes:
        print(f"\nNo changes detected.")
        save_snapshot(current)
        return

    print(f"\nDetected {len(all_changes)} changes. Storing...")
    inserted = store_updates(sb, all_changes)

    # Update snapshot
    save_snapshot(current)

    # --- Summary ---
    print(f"\n{'='*60}")
    print("CHANGE DETECTION COMPLETE")
    print(f"{'='*60}")
    print(f"Changes detected: {len(all_changes)}")
    print(f"  Score shifts (>={args.threshold}): {len(score_shifts)}")
    print(f"  Consensus changes: {len(consensus_changes)}")
    print(f"  New claims: {len(new_claims)}")
    print(f"  New sources: {len(new_sources)}")
    print(f"Rows inserted to signal_evidence_updates: {inserted}")


if __name__ == "__main__":
    main()
