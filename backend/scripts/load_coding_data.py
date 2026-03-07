"""
Import CMS NCCI PTP edits and MUE limits into Supabase.

Usage:
    python scripts/load_coding_data.py --ncci-dir /path/to/ncci_data/ --mue-dir /path/to/ncci_data/

PTP files: tab-delimited .txt with 6 header lines.
  Columns: Column1, Column2, PriorTo1996, EffectiveDate, DeletionDate, Modifier, Rationale
  - Filter out rows where DeletionDate != "*" (expired edits)
  - Filter out Modifier == 9 (not applicable)

MUE files: CSV with ~9-line copyright header.
  Columns: HCPCS/CPT Code, MUE Value, MUE Adjudication Indicator, MUE Rationale
  - Practitioner and Facility files merged into one table.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path
from typing import List

import pandas as pd

# Add parent dir so we can import supabase_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabase_client import supabase as sb  # noqa: E402

BATCH_SIZE = 500


def upsert_batches(table: str, records: List[dict], batch_size: int = BATCH_SIZE):
    """Upsert records into a Supabase table in batches."""
    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i : i + batch_size]
        sb.table(table).upsert(batch).execute()
        done = min(i + batch_size, total)
        if done % 5000 < batch_size or done == total:
            print(f"  {table}: upserted {done:,}/{total:,}")


# ---------------------------------------------------------------------------
# PTP (NCCI) edits
# ---------------------------------------------------------------------------

def load_ncci_dir(ncci_dir: str):
    """Load all PTP edit files from a directory into Supabase."""
    base = Path(ncci_dir)

    # Find all .txt PTP files in subdirectories
    hospital_files = sorted(base.glob("ccioph-*/ccioph-*.txt"))
    practitioner_files = sorted(base.glob("ccipra-*/ccipra-*.txt"))

    print(f"Found {len(hospital_files)} hospital PTP files, {len(practitioner_files)} practitioner PTP files")

    all_records = []

    for txt_path in hospital_files:
        records = parse_ptp_file(txt_path, source="hospital")
        all_records.extend(records)
        print(f"  {txt_path.name}: {len(records):,} active edits")

    for txt_path in practitioner_files:
        records = parse_ptp_file(txt_path, source="practitioner")
        all_records.extend(records)
        print(f"  {txt_path.name}: {len(records):,} active edits")

    # Deduplicate: keep one row per (column1, column2, source).
    # If a pair appears in multiple files, take the stricter modifier (lower value).
    dedup = {}
    for r in all_records:
        key = (r["column1_code"], r["column2_code"], r["source"])
        existing = dedup.get(key)
        if existing is None or r["modifier_indicator"] < existing["modifier_indicator"]:
            dedup[key] = r
    records = list(dedup.values())

    print(f"\nTotal unique NCCI edits to upsert: {len(records):,}")
    upsert_batches("ncci_edits", records)
    print("NCCI edits loaded successfully\n")


def parse_ptp_file(txt_path: Path, source: str) -> List[dict]:
    """Parse a single CMS PTP edit .txt file (tab-delimited, 6 header lines)."""
    df = pd.read_csv(
        txt_path,
        sep="\t",
        skiprows=6,
        header=None,
        names=["column1", "column2", "prior_1996", "effective_date", "deletion_date", "modifier", "rationale"],
        dtype=str,
    )

    # Drop rows with missing key columns
    df = df.dropna(subset=["column1", "column2", "modifier"])

    # Strip whitespace
    df["column1"] = df["column1"].str.strip()
    df["column2"] = df["column2"].str.strip()
    df["deletion_date"] = df["deletion_date"].str.strip()
    df["modifier"] = df["modifier"].str.strip()

    # Filter: keep only active edits (deletion_date == "*" means no deletion)
    df = df[df["deletion_date"] == "*"]

    # Filter: exclude modifier 9 (not applicable)
    df = df[df["modifier"] != "9"]

    # Convert modifier to int
    df["modifier"] = pd.to_numeric(df["modifier"], errors="coerce").fillna(0).astype(int)

    records = []
    for _, row in df.iterrows():
        records.append({
            "column1_code": row["column1"],
            "column2_code": row["column2"],
            "modifier_indicator": row["modifier"],
            "effective_date": row.get("effective_date", "").strip() if pd.notna(row.get("effective_date")) else None,
            "rationale": row.get("rationale", "").strip() if pd.notna(row.get("rationale")) else None,
            "source": source,
        })

    return records


# ---------------------------------------------------------------------------
# MUE limits
# ---------------------------------------------------------------------------

def load_mue_dir(mue_dir: str):
    """Load MUE practitioner + facility files and merge into one table."""
    base = Path(mue_dir)

    prac_files = list(base.glob("practitioner*/MCR_MUE_Practitioner*.csv"))
    fac_files = list(base.glob("facility*/MCR_MUE_Outpatient*.csv"))

    if not prac_files:
        print("ERROR: No practitioner MUE CSV found")
        sys.exit(1)
    if not fac_files:
        print("ERROR: No facility MUE CSV found")
        sys.exit(1)

    prac_path = prac_files[0]
    fac_path = fac_files[0]

    print(f"Practitioner MUE: {prac_path.name}")
    print(f"Facility MUE:     {fac_path.name}")

    prac_df = parse_mue_file(prac_path)
    fac_df = parse_mue_file(fac_path)

    print(f"  Practitioner codes: {len(prac_df):,}")
    print(f"  Facility codes:     {len(fac_df):,}")

    # Merge on code — outer join so we keep codes that appear in only one file
    merged = pd.merge(
        prac_df.rename(columns={"mue_value": "practitioner_mue", "rationale": "practitioner_rationale"}),
        fac_df.rename(columns={"mue_value": "facility_mue", "rationale": "facility_rationale"}),
        on="hcpcs_code",
        how="outer",
    )
    merged["practitioner_mue"] = merged["practitioner_mue"].fillna(0).astype(int)
    merged["facility_mue"] = merged["facility_mue"].fillna(0).astype(int)
    merged["practitioner_rationale"] = merged["practitioner_rationale"].fillna("")
    merged["facility_rationale"] = merged["facility_rationale"].fillna("")

    records = merged.to_dict(orient="records")
    print(f"\nTotal unique MUE codes to upsert: {len(records):,}")
    upsert_batches("mue_limits", records)
    print("MUE limits loaded successfully\n")


def parse_mue_file(csv_path: Path) -> pd.DataFrame:
    """Parse a CMS MUE CSV file (copyright header, then data).

    The header row contains a multi-line quoted field "HCPCS/\\nCPT Code"
    so we find the first data row (starts with a code like 0001U) and
    tell pandas to skip everything before the header line above it.
    """
    # Find the first data row — a line starting with an alphanumeric code
    header_line = None
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            stripped = line.strip()
            # Data rows start with a code like "0001U," or "99213,"
            if stripped and stripped[0].isdigit() and "," in stripped:
                # The header is 2 lines above (multi-line quoted field spans 2 lines)
                header_line = i - 2
                break

    if header_line is None or header_line < 0:
        print(f"ERROR: Could not find data rows in {csv_path}")
        sys.exit(1)

    df = pd.read_csv(csv_path, skiprows=header_line, dtype=str, encoding="latin-1")

    # Columns: "HCPCS/\nCPT Code", MUE Values, Adjudication Indicator, Rationale
    col0 = df.columns[0]
    col1 = df.columns[1]
    col3 = df.columns[3] if len(df.columns) > 3 else None

    result = pd.DataFrame()
    result["hcpcs_code"] = df[col0].str.strip()
    result["mue_value"] = pd.to_numeric(df[col1], errors="coerce").fillna(0).astype(int)
    result["rationale"] = df[col3].str.strip() if col3 else ""

    # Drop rows where code is missing or not a valid code
    result = result.dropna(subset=["hcpcs_code"])
    result = result[result["hcpcs_code"].str.len() > 0]

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if sb is None:
        print("ERROR: SUPABASE_SERVICE_KEY not set. Cannot load data.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Load CMS NCCI edits and MUE limits into Supabase"
    )
    parser.add_argument("--ncci-dir", help="Directory containing PTP edit files (ccioph/ccipra subdirs)")
    parser.add_argument("--mue-dir", help="Directory containing MUE CSV files (practitioner/facility subdirs)")
    args = parser.parse_args()

    if not args.ncci_dir and not args.mue_dir:
        print("Provide at least one of --ncci-dir or --mue-dir")
        sys.exit(1)

    if args.ncci_dir:
        load_ncci_dir(args.ncci_dir)
    if args.mue_dir:
        load_mue_dir(args.mue_dir)

    print("Done.")


if __name__ == "__main__":
    main()
