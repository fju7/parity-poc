#!/usr/bin/env python3
"""Load NADAC (National Average Drug Acquisition Cost) data into Supabase.

Downloads the current NADAC weekly file from the CMS/Medicaid.gov public API
and upserts into the pharmacy_nadac table.

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python3 backend/scripts/load_nadac.py

Requires: pip3 install requests supabase --break-system-packages
"""

import os
import sys
import json

import requests

# ---------------------------------------------------------------------------
# CMS NADAC API endpoint (Medicaid.gov data store)
# ---------------------------------------------------------------------------

NADAC_API_URL = "https://data.medicaid.gov/api/1/datastore/query/fbb83258-11c7-47f5-8b18-5f8e79f7e704/0"

# Server-side date filter: only fetch the most recent weeks of data
# instead of paginating through the entire yearly dataset (~1.9M rows).
# Update this date when re-running to fetch only the latest snapshot.
NADAC_MIN_AS_OF_DATE = "2026-03-01"

# We paginate in chunks — the API returns max 500 per request by default
PAGE_SIZE = 500
MAX_PAGES = 200  # safety cap — ~100k rows max


def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        sys.exit(1)
    from supabase import create_client
    return create_client(url, key)


def fetch_nadac_data():
    """Download NADAC data from CMS API with pagination.

    Sorted by as_of_date descending so we get the most recent entries first.
    We deduplicate by NDC, keeping only the first (most recent) entry per NDC.
    """
    seen_ndcs = set()
    all_rows = []
    offset = 0

    for page in range(MAX_PAGES):
        print(f"  Fetching page {page + 1} (offset {offset})...")
        try:
            resp = requests.get(
                NADAC_API_URL,
                params={
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "sort[0][property]": "as_of_date",
                    "sort[0][order]": "desc",
                    "conditions[0][property]": "as_of_date",
                    "conditions[0][value]": NADAC_MIN_AS_OF_DATE,
                    "conditions[0][operator]": ">",
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  API error at offset {offset}: {exc}")
            break

        results = data.get("results", [])
        if not results:
            break

        new_this_page = 0
        for row in results:
            ndc = row.get("ndc", "").replace("-", "").strip()
            if not ndc:
                continue

            # Skip if we already have a more recent entry for this NDC
            if ndc in seen_ndcs:
                continue
            seen_ndcs.add(ndc)
            new_this_page += 1

            drug_name = row.get("ndc_description", "").strip()
            nadac_str = row.get("nadac_per_unit", "")
            pricing_unit = row.get("pricing_unit", "").strip()
            otc_or_rx = row.get("otc", "").strip()
            effective_date = row.get("effective_date", "").strip()

            try:
                nadac_per_unit = float(nadac_str) if nadac_str else None
            except (ValueError, TypeError):
                nadac_per_unit = None

            # Normalize effective_date to YYYY-MM-DD if it's in a different format
            if effective_date and "T" in effective_date:
                effective_date = effective_date.split("T")[0]

            all_rows.append({
                "ndc_code": ndc,
                "drug_name": drug_name,
                "nadac_per_unit": nadac_per_unit,
                "pricing_unit": pricing_unit,
                "otc_or_rx": otc_or_rx,
                "effective_date": effective_date or None,
            })

        print(f"    {new_this_page} new NDCs this page ({len(all_rows)} total unique)")

        if len(results) < PAGE_SIZE:
            break
        # Stop early if we're getting mostly duplicates (>90% seen)
        if new_this_page < PAGE_SIZE * 0.1:
            print(f"    Mostly duplicates — stopping pagination.")
            break
        offset += PAGE_SIZE

    return all_rows


def upsert_to_supabase(sb, rows):
    """Upsert NADAC rows into Supabase in batches."""
    # Clear existing data first (full refresh)
    print(f"  Clearing existing pharmacy_nadac data...")
    sb.table("pharmacy_nadac").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    batch_size = 200
    total = len(rows)
    inserted = 0

    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        try:
            sb.table("pharmacy_nadac").insert(batch).execute()
            inserted += len(batch)
            print(f"  Inserted {inserted}/{total} rows...")
        except Exception as exc:
            print(f"  Error inserting batch at offset {i}: {exc}")
            # Continue with next batch
            continue

    return inserted


def main():
    print("=== NADAC Loader ===")
    print("1. Fetching NADAC data from CMS API...")
    rows = fetch_nadac_data()
    print(f"   Fetched {len(rows)} drug records.")

    if not rows:
        print("   No data fetched. Exiting.")
        sys.exit(1)

    print("2. Connecting to Supabase...")
    sb = get_supabase()

    print("3. Upserting to pharmacy_nadac table...")
    count = upsert_to_supabase(sb, rows)
    print(f"   Done! {count} records loaded.")


if __name__ == "__main__":
    main()
