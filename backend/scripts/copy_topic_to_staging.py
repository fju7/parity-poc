#!/usr/bin/env python3
"""Copy a Signal topic and all related data from production to staging Supabase.

Usage:
    SUPABASE_URL=https://prod.supabase.co \
    SUPABASE_SERVICE_ROLE_KEY=... \
    STAGING_SUPABASE_URL=https://staging.supabase.co \
    STAGING_SUPABASE_SERVICE_ROLE_KEY=... \
    python3 backend/scripts/copy_topic_to_staging.py \
        --topic-id a8f26a47-69ab-4a5c-8b2a-9a305ce9d9f9

Requires: pip3 install supabase --break-system-packages
"""

import argparse
import os
import sys


def get_client(url_env, key_env, label):
    url = os.environ.get(url_env)
    key = os.environ.get(key_env)
    if not url or not key:
        print(f"ERROR: {url_env} and {key_env} must be set ({label}).")
        sys.exit(1)
    from supabase import create_client
    return create_client(url, key)


def fetch_all(client, table, column, value):
    """Fetch all rows where column == value, paginating in batches of 1000."""
    rows = []
    offset = 0
    while True:
        result = (
            client.table(table)
            .select("*")
            .eq(column, value)
            .range(offset, offset + 999)
            .execute()
        )
        batch = result.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def upsert_batch(client, table, rows, batch_size=200):
    """Upsert rows in batches. Returns count of rows upserted."""
    if not rows:
        return 0
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        client.table(table).upsert(batch).execute()
        total += len(batch)
    return total


def main():
    parser = argparse.ArgumentParser(description="Copy a Signal topic to staging")
    parser.add_argument("--topic-id", required=True, help="UUID of the signal_issues row")
    args = parser.parse_args()
    topic_id = args.topic_id

    print(f"=== Copy Topic to Staging ===")
    print(f"Topic ID: {topic_id}")
    print()

    prod = get_client("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "production")
    staging = get_client("STAGING_SUPABASE_URL", "STAGING_SUPABASE_SERVICE_ROLE_KEY", "staging")

    # 1. signal_issues
    issues = fetch_all(prod, "signal_issues", "id", topic_id)
    if not issues:
        print(f"ERROR: No issue found with id={topic_id}")
        sys.exit(1)
    print(f"  signal_issues: {len(issues)} row(s) — \"{issues[0].get('title', '?')}\"")
    upsert_batch(staging, "signal_issues", issues)

    # 2. signal_sources
    sources = fetch_all(prod, "signal_sources", "issue_id", topic_id)
    print(f"  signal_sources: {len(sources)} rows")
    upsert_batch(staging, "signal_sources", sources)
    source_ids = {s["id"] for s in sources}

    # 3. signal_claims
    claims = fetch_all(prod, "signal_claims", "issue_id", topic_id)
    print(f"  signal_claims: {len(claims)} rows")
    upsert_batch(staging, "signal_claims", claims)
    claim_ids = {c["id"] for c in claims}

    # 4. signal_claim_sources (composite PK: claim_id + source_id)
    all_claim_sources = []
    for claim_id in claim_ids:
        rows = fetch_all(prod, "signal_claim_sources", "claim_id", claim_id)
        all_claim_sources.extend(rows)
    print(f"  signal_claim_sources: {len(all_claim_sources)} rows")
    if all_claim_sources:
        # Upsert with on_conflict for composite key
        upsert_batch(staging, "signal_claim_sources", all_claim_sources)

    # 5. signal_claim_scores
    all_scores = []
    for claim_id in claim_ids:
        rows = fetch_all(prod, "signal_claim_scores", "claim_id", claim_id)
        all_scores.extend(rows)
    print(f"  signal_claim_scores: {len(all_scores)} rows")
    upsert_batch(staging, "signal_claim_scores", all_scores)

    # 6. signal_claim_composites
    all_composites = []
    for claim_id in claim_ids:
        rows = fetch_all(prod, "signal_claim_composites", "claim_id", claim_id)
        all_composites.extend(rows)
    print(f"  signal_claim_composites: {len(all_composites)} rows")
    upsert_batch(staging, "signal_claim_composites", all_composites)

    # 7. signal_summaries
    summaries = fetch_all(prod, "signal_summaries", "issue_id", topic_id)
    print(f"  signal_summaries: {len(summaries)} rows")
    upsert_batch(staging, "signal_summaries", summaries)

    # 8. signal_consensus
    consensus = fetch_all(prod, "signal_consensus", "issue_id", topic_id)
    print(f"  signal_consensus: {len(consensus)} rows")
    upsert_batch(staging, "signal_consensus", consensus)

    # 9. signal_analytical_profiles (global — not topic-specific, copy all 4)
    profiles = prod.table("signal_analytical_profiles").select("*").execute()
    profile_rows = profiles.data or []
    print(f"  signal_analytical_profiles: {len(profile_rows)} rows (global)")
    upsert_batch(staging, "signal_analytical_profiles", profile_rows)

    print()
    print("Done! Topic copied to staging.")


if __name__ == "__main__":
    main()
