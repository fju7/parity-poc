#!/usr/bin/env python3
"""
load_opps_clfs_from_cms.py — Download and load current CMS OPPS and CLFS
rates directly from cms.gov into Supabase.

What it does:
    1. Downloads the CMS OPPS Addendum B ZIP from a known direct URL
    2. Parses the CSV in memory, loads into opps_rates_historical
    3. Downloads the CMS CLFS ZIP from a known direct URL
    4. Parses the CSV in memory, loads into clfs_rates_historical
    5. Deletes existing rows for the rate_year being loaded before inserting (safe reload)

How to run:
    cd backend
    python3 scripts/load_opps_clfs_from_cms.py

Environment variables:
    SUPABASE_URL          — defaults to https://kfxxpscdwoemtzylhhhb.supabase.co
    SUPABASE_SERVICE_KEY  — required, no default

URL maintenance:
    CMS direct ZIP URLs are stable even when cms.gov page structure changes.
    Update the OPPS_ZIP_URL and CLFS_ZIP_URL constants below when CMS
    releases new quarterly files. See comments above the constants for schedule.

Note: Add as Render cron job in Session Z.
"""

from __future__ import annotations

import csv
import io
import os
import re
import sys
import zipfile
from urllib.request import Request, urlopen
from urllib.error import URLError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# QUARTERLY MAINTENANCE: Update these URLs when CMS releases new rate files.
# CMS releases OPPS updates in January, April, July, October.
# CMS releases CLFS updates quarterly. Check cms.gov for new filenames.
# Direct ZIP URLs are reliable — CMS page structure changes but file URLs are stable.
OPPS_ZIP_URL = "https://www.cms.gov/files/zip/january-2026-opps-addendum-b.zip"
CLFS_ZIP_URL = "https://www.cms.gov/files/zip/26clabq1.zip"

BATCH_SIZE = 500

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

USER_AGENT = "Mozilla/5.0 (Parity CivicScale CMS Loader)"


# ---------------------------------------------------------------------------
# Supabase client
# ---------------------------------------------------------------------------

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        if not SUPABASE_SERVICE_KEY:
            print("ERROR: SUPABASE_SERVICE_KEY environment variable not set.")
            sys.exit(1)
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _supabase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _download_zip(url: str) -> bytes:
    """Download a ZIP file and return raw bytes."""
    print(f"  Downloading: {url}")
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=120) as resp:
        return resp.read()


def _extract_csv_from_zip(zip_bytes: bytes) -> io.StringIO:
    """Find and extract the first CSV file from a ZIP archive in memory."""
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if not csv_files:
        raise FileNotFoundError("No CSV file found in ZIP archive")
    csv_name = csv_files[0]
    print(f"  Extracting CSV: {csv_name}")
    raw = zf.read(csv_name)
    return io.StringIO(raw.decode("utf-8", errors="replace"))


def _extract_year_from_url(url: str, default: int = 2026) -> int:
    """Try to extract a 4-digit year from the URL or filename."""
    m = re.search(r"20(2[4-9]|3[0-9])", url)
    if m:
        return int(m.group(0))
    # Look for 2-digit year prefix like "26clabq1"
    m = re.search(r"/(\d{2})[a-zA-Z]", url)
    if m:
        yr = int(m.group(1))
        return 2000 + yr if yr < 50 else 1900 + yr
    return default


# ---------------------------------------------------------------------------
# OPPS loader
# ---------------------------------------------------------------------------

def load_opps():
    """Download and load CMS OPPS Addendum B rates."""
    print("\n=== OPPS (Outpatient Prospective Payment System) ===")

    try:
        zip_bytes = _download_zip(OPPS_ZIP_URL)
    except (URLError, OSError) as e:
        print(f"  ERROR: Failed to download OPPS ZIP: {e}")
        return

    csv_io = _extract_csv_from_zip(zip_bytes)
    rate_year = _extract_year_from_url(OPPS_ZIP_URL)
    print(f"  Rate year: {rate_year}")

    # Find the header row (contains "HCPCS" or "CPT")
    lines = csv_io.readlines()
    header_idx = 0
    for i, line in enumerate(lines):
        if re.search(r"HCPCS|CPT", line, re.IGNORECASE):
            header_idx = i
            break

    # Re-parse from header row
    csv_io = io.StringIO("".join(lines[header_idx:]))
    reader = csv.DictReader(csv_io)

    if reader.fieldnames is None:
        print("  ERROR: Could not parse CSV headers")
        return

    # Find the right columns (CMS uses varying names)
    col_map = {}
    for col in reader.fieldnames:
        col_lower = col.strip().lower()
        if "hcpcs" in col_lower or "cpt" in col_lower:
            col_map["hcpcs_code"] = col
        elif "payment" in col_lower and "rate" in col_lower:
            col_map["payment_rate"] = col
        elif "short" in col_lower and "desc" in col_lower:
            col_map["description"] = col

    if "hcpcs_code" not in col_map or "payment_rate" not in col_map:
        print(f"  ERROR: Required columns not found. Available: {reader.fieldnames}")
        return

    print(f"  Column mapping: {col_map}")

    rows = []
    for row in reader:
        try:
            code = row.get(col_map["hcpcs_code"], "").strip()
            rate_str = row.get(col_map["payment_rate"], "").strip()
            desc = row.get(col_map.get("description", ""), "").strip() if "description" in col_map else ""

            if not code or not rate_str:
                continue

            # Clean rate: remove $, commas
            rate_str = rate_str.replace("$", "").replace(",", "").strip()
            if not rate_str or rate_str == "*":
                continue

            rate = float(rate_str)
            if rate <= 0:
                continue

            rows.append({
                "hcpcs_code": code,
                "payment_rate": rate,
                "description": desc[:500] if desc else None,
                "rate_year": rate_year,
                "schedule_type": "OPPS",
            })
        except (ValueError, KeyError):
            continue

    print(f"  Parsed {len(rows)} OPPS rates")

    if not rows:
        print("  No rows to load — skipping.")
        return

    # Load into Supabase
    sb = _get_supabase()
    table = "opps_rates_historical"

    # Delete existing rows for this year
    print(f"  Deleting existing {table} rows for year {rate_year}...")
    try:
        sb.table(table).delete().eq("rate_year", rate_year).execute()
    except Exception as e:
        print(f"  [warn] Delete failed (table may be empty): {e}")

    # Batch insert
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        try:
            sb.table(table).insert(batch).execute()
            inserted += len(batch)
            if (i // BATCH_SIZE) % 10 == 0:
                print(f"  Inserted {inserted}/{len(rows)}...")
        except Exception as e:
            print(f"  [error] Batch {i}-{i + len(batch)} failed: {e}")

    print(f"  OPPS complete: {inserted} rows loaded into {table}")


# ---------------------------------------------------------------------------
# CLFS loader
# ---------------------------------------------------------------------------

def load_clfs():
    """Download and load CMS CLFS (Clinical Laboratory Fee Schedule) rates."""
    print("\n=== CLFS (Clinical Laboratory Fee Schedule) ===")

    try:
        zip_bytes = _download_zip(CLFS_ZIP_URL)
    except (URLError, OSError) as e:
        print(f"  ERROR: Failed to download CLFS ZIP: {e}")
        return

    csv_io = _extract_csv_from_zip(zip_bytes)
    rate_year = _extract_year_from_url(CLFS_ZIP_URL)
    print(f"  Rate year: {rate_year}")

    # CLFS CSV has header/disclaimer rows before the column headers
    lines = csv_io.readlines()

    # Find header row containing "HCPCS" or "RATE"
    header_idx = 0
    for i, line in enumerate(lines):
        if re.search(r"HCPCS|RATE", line, re.IGNORECASE):
            header_idx = i
            break

    csv_io = io.StringIO("".join(lines[header_idx:]))
    reader = csv.DictReader(csv_io)

    if reader.fieldnames is None:
        print("  ERROR: Could not parse CSV headers")
        return

    # Find the right columns
    col_map = {}
    for col in reader.fieldnames:
        col_lower = col.strip().lower()
        if "hcpcs" in col_lower:
            col_map["hcpcs_code"] = col
        elif col_lower == "rate":
            col_map["payment_rate"] = col
        elif "mod" in col_lower:
            col_map["mod"] = col
        elif "shortdesc" in col_lower or "short" in col_lower:
            col_map["description"] = col
        elif "year" == col_lower:
            col_map["year"] = col

    # Fallback: if "rate" not found, try any column with "rate" in name
    if "payment_rate" not in col_map:
        for col in reader.fieldnames:
            if "rate" in col.strip().lower():
                col_map["payment_rate"] = col
                break

    if "hcpcs_code" not in col_map or "payment_rate" not in col_map:
        print(f"  ERROR: Required columns not found. Available: {reader.fieldnames}")
        return

    print(f"  Column mapping: {col_map}")

    rows = []
    for row in reader:
        try:
            # Filter to base rows only (no modifier) to avoid duplicates
            mod = row.get(col_map.get("mod", ""), "").strip()
            if mod:
                continue

            code = row.get(col_map["hcpcs_code"], "").strip()
            rate_str = row.get(col_map["payment_rate"], "").strip()
            desc = row.get(col_map.get("description", ""), "").strip() if "description" in col_map else ""

            if not code or not rate_str:
                continue

            rate_str = rate_str.replace("$", "").replace(",", "").strip()
            if not rate_str or rate_str == "*":
                continue

            rate = float(rate_str)
            if rate <= 0:
                continue

            # Use year from CSV row if available, else from URL
            row_year = rate_year
            if "year" in col_map:
                try:
                    row_year = int(row.get(col_map["year"], "").strip())
                except (ValueError, TypeError):
                    pass

            rows.append({
                "hcpcs_code": code,
                "payment_rate": rate,
                "description": desc[:500] if desc else None,
                "rate_year": row_year,
                "schedule_type": "CLFS",
            })
        except (ValueError, KeyError):
            continue

    print(f"  Parsed {len(rows)} CLFS rates")

    if not rows:
        print("  No rows to load — skipping.")
        return

    # Load into Supabase
    sb = _get_supabase()
    table = "clfs_rates_historical"

    # Delete existing rows for this year
    print(f"  Deleting existing {table} rows for year {rate_year}...")
    try:
        sb.table(table).delete().eq("rate_year", rate_year).execute()
    except Exception as e:
        print(f"  [warn] Delete failed (table may be empty): {e}")

    # Batch insert
    inserted = 0
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        try:
            sb.table(table).insert(batch).execute()
            inserted += len(batch)
            if (i // BATCH_SIZE) % 10 == 0:
                print(f"  Inserted {inserted}/{len(rows)}...")
        except Exception as e:
            print(f"  [error] Batch {i}-{i + len(batch)} failed: {e}")

    print(f"  CLFS complete: {inserted} rows loaded into {table}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("CMS Rate Loader — OPPS + CLFS")
    print(f"Supabase URL: {SUPABASE_URL}")
    print(f"Service key: {'set' if SUPABASE_SERVICE_KEY else 'NOT SET'}")

    load_opps()
    load_clfs()

    print("\nDone.")
