#!/usr/bin/env python3
"""
load_historical_rates.py — Bulk-load a historical CMS rate CSV into
Supabase so that older bills can be benchmarked against the rates
that were in effect at time of service.

Usage:
    python scripts/load_historical_rates.py \
        --schedule PFS --year 2025 --file data/pfs_rates_2025.csv

    python scripts/load_historical_rates.py \
        --schedule CLFS --year 2025 --quarter Q2 --file data/clfs_2025q2.csv

    python scripts/load_historical_rates.py --help
"""

import argparse
import csv
import os
import sys
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        from supabase import create_client

        url = os.environ.get(
            "SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co"
        )
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not key:
            print("ERROR: SUPABASE_SERVICE_KEY environment variable not set.")
            sys.exit(1)
        _supabase = create_client(url, key)
    return _supabase


# ---------------------------------------------------------------------------
# Expected CSV columns per schedule type
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = {
    "PFS": {"cpt_code", "carrier", "locality_code", "nonfacility_amount", "facility_amount"},
    "OPPS": {"hcpcs_code", "payment_rate"},
    "CLFS": {"hcpcs_code", "payment_rate"},
}

# Column name mappings (CSV column -> Supabase column)
COLUMN_MAP = {
    "PFS": {
        "cpt_code": "hcpcs_code",
        "carrier": "carrier",
        "locality_code": "locality_code",
        "nonfacility_amount": "nonfacility_amount",
        "facility_amount": "facility_amount",
    },
    "OPPS": {
        "hcpcs_code": "hcpcs_code",
        "payment_rate": "payment_rate",
        "description": "description",
    },
    "CLFS": {
        "hcpcs_code": "hcpcs_code",
        "payment_rate": "payment_rate",
        "description": "description",
    },
}

TABLE_MAP = {
    "PFS": "pfs_rates_historical",
    "OPPS": "opps_rates_historical",
    "CLFS": "clfs_rates_historical",
}

BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def validate_file(filepath: Path, schedule_type: str) -> tuple[list[str], int]:
    """Validate that the CSV has the expected columns.

    Returns (header_list, row_count).
    """
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = [col.strip().lower() for col in next(reader)]

    expected = EXPECTED_COLUMNS[schedule_type]
    # Map expected columns through any aliases
    header_set = set(header)
    missing = expected - header_set
    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        print(f"  Found: {header}")
        sys.exit(1)

    # Count rows
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        row_count = sum(1 for _ in f) - 1  # subtract header
    return header, row_count


def create_version(
    schedule_type: str, year: int, quarter: int | None, filepath: Path, row_count: int
) -> str:
    """Insert a new rate_schedule_versions row and return the version_id."""
    sb = _get_supabase()

    # Effective date: Jan 1 of the year (or quarter start for CLFS)
    if quarter:
        month = (quarter - 1) * 3 + 1
        effective = date(year, month, 1)
    else:
        effective = date(year, 1, 1)

    row = {
        "schedule_type": schedule_type,
        "vintage_year": year,
        "vintage_quarter": quarter,
        "effective_date": effective.isoformat(),
        "expiry_date": None,
        "is_current": False,
        "source_file": filepath.name,
        "row_count": row_count,
        "notes": f"Loaded via load_historical_rates.py on {datetime.now().isoformat()}",
    }

    result = sb.table("rate_schedule_versions").insert(row).execute()
    version_id = result.data[0]["id"]
    print(f"Created version: {version_id}")
    print(f"  Schedule: {schedule_type} {year}" + (f" Q{quarter}" if quarter else ""))
    print(f"  Effective: {effective}")
    return version_id


def update_previous_expiry(schedule_type: str, year: int, quarter: int | None, new_version_id: str):
    """Set expiry_date on the previous version for the same schedule type."""
    sb = _get_supabase()

    # Get the new version's effective date
    new_ver = (
        sb.table("rate_schedule_versions")
        .select("effective_date")
        .eq("id", new_version_id)
        .limit(1)
        .execute()
    )
    if not new_ver.data:
        return

    new_effective = new_ver.data[0]["effective_date"]

    # Find the previous version (most recent effective_date before this one)
    prev = (
        sb.table("rate_schedule_versions")
        .select("id, effective_date, expiry_date")
        .eq("schedule_type", schedule_type)
        .neq("id", new_version_id)
        .lt("effective_date", new_effective)
        .order("effective_date", desc=True)
        .limit(1)
        .execute()
    )

    if prev.data:
        prev_id = prev.data[0]["id"]
        prev_expiry = prev.data[0].get("expiry_date")
        if prev_expiry is None:
            sb.table("rate_schedule_versions").update(
                {"expiry_date": new_effective}
            ).eq("id", prev_id).execute()
            print(f"Updated expiry_date on previous version {prev_id} -> {new_effective}")


def load_rows(filepath: Path, schedule_type: str, version_id: str) -> int:
    """Read CSV and bulk-insert into the appropriate historical table."""
    sb = _get_supabase()
    table = TABLE_MAP[schedule_type]
    col_map = COLUMN_MAP[schedule_type]

    loaded = 0
    batch = []

    with open(filepath, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            row = {"version_id": version_id}
            for csv_col, db_col in col_map.items():
                val = raw_row.get(csv_col, "").strip()
                if db_col in ("nonfacility_amount", "facility_amount", "payment_rate"):
                    try:
                        val = float(val) if val else None
                    except ValueError:
                        val = None
                row[db_col] = val
            batch.append(row)

            if len(batch) >= BATCH_SIZE:
                sb.table(table).insert(batch).execute()
                loaded += len(batch)
                if loaded % 5000 == 0:
                    print(f"  ... {loaded:,} rows loaded")
                batch = []

    if batch:
        sb.table(table).insert(batch).execute()
        loaded += len(batch)

    return loaded


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Load historical CMS rate data into Supabase for versioned benchmarking.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/load_historical_rates.py --schedule PFS --year 2025 --file data/pfs_rates_2025.csv
  python scripts/load_historical_rates.py --schedule CLFS --year 2025 --quarter Q2 --file data/clfs_2025q2.csv
  python scripts/load_historical_rates.py --schedule OPPS --year 2024 --file data/opps_rates_2024.csv
        """,
    )
    parser.add_argument(
        "--schedule",
        required=True,
        choices=["PFS", "OPPS", "CLFS"],
        help="Rate schedule type",
    )
    parser.add_argument("--year", required=True, type=int, help="Vintage year (e.g. 2025)")
    parser.add_argument(
        "--quarter",
        type=str,
        default=None,
        help="Quarter (Q1-Q4), required for CLFS",
    )
    parser.add_argument("--file", required=True, type=str, help="Path to CSV file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate file only, don't load",
    )

    args = parser.parse_args()

    # Validate schedule + quarter
    quarter_int = None
    if args.quarter:
        q = args.quarter.upper().replace("Q", "")
        try:
            quarter_int = int(q)
            if quarter_int not in (1, 2, 3, 4):
                raise ValueError
        except ValueError:
            print(f"ERROR: Invalid quarter '{args.quarter}'. Use Q1, Q2, Q3, or Q4.")
            sys.exit(1)

    if args.schedule == "CLFS" and quarter_int is None:
        print("ERROR: --quarter is required for CLFS schedule.")
        sys.exit(1)

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    # Validate CSV
    print(f"Validating {filepath}...")
    header, row_count = validate_file(filepath, args.schedule)
    print(f"  Columns: {', '.join(header)}")
    print(f"  Rows: {row_count:,}")

    if args.dry_run:
        print("\n[DRY RUN] File is valid. No data loaded.")
        return

    # Create version
    print(f"\nCreating version entry...")
    version_id = create_version(args.schedule, args.year, quarter_int, filepath, row_count)

    # Load rows
    print(f"\nLoading {row_count:,} rows into {TABLE_MAP[args.schedule]}...")
    loaded = load_rows(filepath, args.schedule, version_id)
    print(f"\nLoaded {loaded:,} rows.")

    # Update previous version expiry
    print("\nUpdating previous version expiry...")
    update_previous_expiry(args.schedule, args.year, quarter_int, version_id)

    # Summary
    print(f"\n{'='*50}")
    print(f"Done!")
    print(f"  Schedule:   {args.schedule} {args.year}" + (f" Q{quarter_int}" if quarter_int else ""))
    print(f"  Version ID: {version_id}")
    print(f"  Rows:       {loaded:,}")
    print(f"  Table:      {TABLE_MAP[args.schedule]}")

    # Check for potential duplicates
    sb = _get_supabase()
    existing = (
        sb.table("rate_schedule_versions")
        .select("id, vintage_year, vintage_quarter")
        .eq("schedule_type", args.schedule)
        .eq("vintage_year", args.year)
        .execute()
    )
    if existing.data and len(existing.data) > 1:
        print(f"\n  WARNING: Multiple versions exist for {args.schedule} {args.year}:")
        for v in existing.data:
            q = v.get("vintage_quarter")
            print(f"    - {v['id']}" + (f" Q{q}" if q else ""))


if __name__ == "__main__":
    main()
