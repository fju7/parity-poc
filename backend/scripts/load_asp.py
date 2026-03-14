#!/usr/bin/env python3
"""Load Medicare Part B ASP (Average Sales Price) data into Supabase.

Downloads the CMS ASP pricing ZIP file, extracts the pricing CSV/TXT,
parses it, and upserts all records into the pharmacy_asp table.

Usage:
    SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python3 backend/scripts/load_asp.py

Requires: pip3 install requests supabase openpyxl --break-system-packages
"""

import io
import os
import re
import sys
import zipfile
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# CMS ASP download URLs — try in order
# ---------------------------------------------------------------------------

ASP_URLS = [
    ("https://www.cms.gov/files/zip/april-2026-medicare-part-b-payment-limit-files-03-10-2026-preliminary-file.zip", "2026-Q2-preliminary"),
    ("https://www.cms.gov/files/zip/january-2026-medicare-part-b-payment-limit-files-03-10-2026-final-file.zip", "2026-Q1"),
]


def get_supabase():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
        sys.exit(1)
    from supabase import create_client
    return create_client(url, key)


def download_asp_zip() -> tuple:
    """Try each CMS URL until one works. Returns (ZIP bytes, effective_quarter)."""
    for url, quarter in ASP_URLS:
        print(f"  Trying: {url}")
        try:
            resp = requests.get(url, timeout=120, stream=True)
            if resp.status_code == 200:
                data = resp.content
                print(f"  Downloaded {len(data):,} bytes from {url}")
                print(f"  Effective quarter: {quarter}")
                return data, quarter
            else:
                print(f"  HTTP {resp.status_code} — trying next URL...")
        except Exception as exc:
            print(f"  Failed: {exc} — trying next URL...")

    print("ERROR: All ASP download URLs failed.")
    sys.exit(1)


def find_pricing_file(z: zipfile.ZipFile) -> str:
    """Find the main ASP pricing file inside the ZIP.

    Looks for files with 'asp' and 'pricing' in the name, or files
    ending in .txt/.csv that contain HCPCS-like data.
    """
    names = z.namelist()
    print(f"  ZIP contains {len(names)} files:")
    for n in names:
        print(f"    {n} ({z.getinfo(n).file_size:,} bytes)")

    # Priority 1: file with "asp" and "pricing" in name
    for n in names:
        nl = n.lower()
        if ("asp" in nl and "pricing" in nl) and (nl.endswith(".txt") or nl.endswith(".csv")):
            return n

    # Priority 2: file with "asp" in name, .txt or .csv
    for n in names:
        nl = n.lower()
        if "asp" in nl and (nl.endswith(".txt") or nl.endswith(".csv")):
            return n

    # Priority 3: file with "payment" in name
    for n in names:
        nl = n.lower()
        if "payment" in nl and (nl.endswith(".txt") or nl.endswith(".csv") or nl.endswith(".xlsx")):
            return n

    # Priority 4: any .xlsx file (CMS sometimes uses Excel)
    for n in names:
        if n.lower().endswith(".xlsx"):
            return n

    # Priority 5: largest .txt or .csv file
    txt_csv = [n for n in names if n.lower().endswith((".txt", ".csv"))]
    if txt_csv:
        return max(txt_csv, key=lambda n: z.getinfo(n).file_size)

    print("ERROR: Could not find ASP pricing file in ZIP.")
    print(f"  Files found: {names}")
    sys.exit(1)


def parse_asp_file(z: zipfile.ZipFile, filename: str) -> list[dict]:
    """Parse the ASP pricing file and return list of records.

    CMS ASP files typically have columns:
    HCPCS Code | Short Description | HCPCS Code Dosage | Dosage | Payment Limit

    The format varies — may be tab-delimited, comma-delimited, or Excel.
    """
    print(f"  Parsing: {filename}")
    rows = []

    if filename.lower().endswith(".xlsx"):
        rows = _parse_xlsx(z, filename)
    else:
        rows = _parse_text(z, filename)

    return rows


def _parse_xlsx(z: zipfile.ZipFile, filename: str) -> list[dict]:
    """Parse an Excel ASP file."""
    import openpyxl

    data = z.read(filename)
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
    ws = wb.active
    rows_out = []

    # Find header row
    header_row = None
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        row_str = " ".join(str(c or "").lower() for c in row)
        if "hcpcs" in row_str and ("payment" in row_str or "limit" in row_str):
            header_row = i
            break

    if header_row is None:
        print("  WARNING: Could not find header row in Excel file, trying row 1")
        header_row = 1

    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if i <= header_row:
            continue
        if not row or len(row) < 3:
            continue

        record = _extract_record_from_cells(list(row))
        if record:
            rows_out.append(record)

    wb.close()
    return rows_out


def _parse_text(z: zipfile.ZipFile, filename: str) -> list[dict]:
    """Parse a text/CSV ASP file."""
    data = z.read(filename).decode("utf-8", errors="replace")
    lines = data.strip().split("\n")
    rows_out = []

    # Detect delimiter
    if "\t" in lines[0]:
        delimiter = "\t"
    elif "," in lines[0]:
        delimiter = ","
    else:
        delimiter = None  # fixed-width or other

    # Find header line
    header_idx = 0
    for i, line in enumerate(lines):
        ll = line.lower()
        if "hcpcs" in ll and ("payment" in ll or "limit" in ll or "description" in ll):
            header_idx = i
            break

    # Parse data lines
    for line in lines[header_idx + 1:]:
        line = line.strip()
        if not line:
            continue

        if delimiter:
            cells = line.split(delimiter)
        else:
            # Try to split on 2+ spaces (fixed-width)
            cells = re.split(r"\s{2,}", line)

        # Clean cells
        cells = [c.strip().strip('"').strip() for c in cells]

        record = _extract_record_from_cells(cells)
        if record:
            rows_out.append(record)

    return rows_out


def _extract_record_from_cells(cells: list) -> Optional[dict]:
    """Extract an ASP record from a row of cells.

    CMS ASP files typically have:
    Col 0: HCPCS Code (e.g., J0185)
    Col 1: Short Description
    Col 2: HCPCS Code Dosage (repeat of HCPCS or dosage info)
    Col 3: Dosage
    Col 4: Payment Limit (ASP + 6%)

    But column ordering can vary. We look for patterns.
    """
    if not cells or len(cells) < 3:
        return None

    # Find HCPCS code — pattern: letter followed by 4 digits (e.g., J0185, Q2043)
    hcpcs = None
    hcpcs_idx = None
    for i, c in enumerate(cells):
        val = str(c or "").strip().upper()
        if re.match(r"^[A-Z]\d{4}$", val):
            hcpcs = val
            hcpcs_idx = i
            break

    if not hcpcs:
        return None

    # Find payment limit — a numeric value, typically the last numeric column
    payment_limit = None
    for c in reversed(cells):
        val = str(c or "").strip().replace("$", "").replace(",", "")
        try:
            num = float(val)
            if num >= 0:
                payment_limit = num
                break
        except (ValueError, TypeError):
            continue

    if payment_limit is None:
        return None

    # Short description — usually the cell after the first HCPCS code
    short_desc = ""
    if hcpcs_idx is not None and hcpcs_idx + 1 < len(cells):
        candidate = str(cells[hcpcs_idx + 1] or "").strip()
        # Skip if it looks like another HCPCS code or a number
        if candidate and not re.match(r"^[A-Z]\d{4}$", candidate.upper()):
            short_desc = candidate

    # Dosage — look for cells with unit patterns
    dosage = ""
    for c in cells:
        val = str(c or "").strip()
        if re.search(r"(mg|ml|mcg|unit|vial|each|per|gm|sq cm)", val, re.IGNORECASE) and val != short_desc:
            dosage = val
            break

    return {
        "hcpcs_code": hcpcs,
        "short_description": short_desc[:200] if short_desc else None,
        "dosage": dosage[:100] if dosage else None,
        "payment_limit": payment_limit,
    }



def upsert_to_supabase(sb, rows: list[dict], quarter: str) -> int:
    """Clear existing data and insert all ASP records."""
    print(f"  Clearing existing pharmacy_asp data...")
    try:
        sb.table("pharmacy_asp").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    except Exception as exc:
        print(f"  Warning: could not clear table (may be empty): {exc}")

    batch_size = 200
    total = len(rows)
    inserted = 0

    for i in range(0, total, batch_size):
        batch = rows[i:i + batch_size]
        records = [
            {
                "hcpcs_code": r["hcpcs_code"],
                "short_description": r.get("short_description"),
                "dosage": r.get("dosage"),
                "payment_limit": r["payment_limit"],
                "effective_quarter": quarter,
            }
            for r in batch
        ]
        try:
            sb.table("pharmacy_asp").insert(records).execute()
            inserted += len(batch)
            print(f"  Inserted {inserted}/{total} rows...")
        except Exception as exc:
            print(f"  Error inserting batch at offset {i}: {exc}")
            continue

    return inserted


def main():
    print("=== Medicare Part B ASP Loader ===")

    print("1. Downloading ASP pricing file from CMS...")
    zip_bytes, quarter = download_asp_zip()

    print("2. Extracting pricing data from ZIP...")
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    pricing_file = find_pricing_file(z)
    print(f"  Selected: {pricing_file}")

    rows = parse_asp_file(z, pricing_file)
    print(f"  Parsed {len(rows)} ASP records.")

    if not rows:
        print("  ERROR: No records parsed. Check the file format.")
        sys.exit(1)

    # Show sample
    print("  Sample records:")
    for r in rows[:5]:
        print(f"    {r['hcpcs_code']} | {r.get('short_description', '')[:40]} | "
              f"${r['payment_limit']:.4f} | {r.get('dosage', '')}")
    print(f"  Effective quarter: {quarter}")

    print("3. Connecting to Supabase...")
    sb = get_supabase()

    print("4. Upserting to pharmacy_asp table...")
    count = upsert_to_supabase(sb, rows, quarter)
    print(f"   Done! {count} ASP records loaded.")

    # Summary stats
    unique_hcpcs = len(set(r["hcpcs_code"] for r in rows))
    print(f"   Unique HCPCS codes: {unique_hcpcs}")

    # Check for common drugs
    known_drugs = {
        "J0185": "Humira (adalimumab)",
        "J3490": "Unclassified drugs",
        "J7170": "Ozempic/semaglutide",
        "Q5131": "Adalimumab-adbm (biosimilar)",
        "J0881": "Darbepoetin alfa",
        "J2505": "Pegfilgrastim",
        "J9035": "Bevacizumab",
        "J9271": "Pembrolizumab (Keytruda)",
    }
    print("   Known drug check:")
    hcpcs_set = {r["hcpcs_code"] for r in rows}
    for code, name in known_drugs.items():
        status = "FOUND" if code in hcpcs_set else "not found"
        print(f"     {code} ({name}): {status}")


if __name__ == "__main__":
    main()
