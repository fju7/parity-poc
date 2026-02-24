"""
Import NCCI edits and MUE limits from CSV files into Supabase.

Usage:
    python scripts/load_coding_data.py --ncci path/to/ncci.csv --mue path/to/mue.csv

CSV expected formats:

NCCI edits CSV columns:
    column1_code, column2_code, modifier_indicator, effective_date
    (modifier_indicator: 0 = hard edit, 1 = soft/modifier allowed)

MUE limits CSV columns:
    hcpcs_code, practitioner_mue, facility_mue
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Add parent dir so we can import supabase_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabase_client import supabase as sb  # noqa: E402

BATCH_SIZE = 1000


def upsert_batches(table: str, records: list[dict], batch_size: int = BATCH_SIZE):
    """Upsert records into a Supabase table in batches."""
    total = len(records)
    for i in range(0, total, batch_size):
        batch = records[i : i + batch_size]
        sb.table(table).upsert(batch).execute()
        print(f"  {table}: upserted {min(i + batch_size, total):,}/{total:,}")


def load_ncci(csv_path: str):
    """Read NCCI edits CSV and upsert to Supabase."""
    print(f"Reading NCCI edits from {csv_path}")
    df = pd.read_csv(csv_path, dtype=str)

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"column1_code", "column2_code", "modifier_indicator"}
    if not required.issubset(set(df.columns)):
        print(f"ERROR: CSV must have columns: {required}")
        print(f"  Found: {list(df.columns)}")
        sys.exit(1)

    df = df[list(required)].dropna()
    df["column1_code"] = df["column1_code"].str.strip()
    df["column2_code"] = df["column2_code"].str.strip()
    df["modifier_indicator"] = pd.to_numeric(
        df["modifier_indicator"], errors="coerce"
    ).fillna(0).astype(int)

    records = df.to_dict(orient="records")
    print(f"  {len(records):,} NCCI edit rows to upsert")
    upsert_batches("ncci_edits", records)
    print("  NCCI edits loaded successfully")


def load_mue(csv_path: str):
    """Read MUE limits CSV and upsert to Supabase."""
    print(f"Reading MUE limits from {csv_path}")
    df = pd.read_csv(csv_path, dtype=str)

    # Normalize column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"hcpcs_code", "practitioner_mue", "facility_mue"}
    if not required.issubset(set(df.columns)):
        print(f"ERROR: CSV must have columns: {required}")
        print(f"  Found: {list(df.columns)}")
        sys.exit(1)

    df = df[list(required)].dropna()
    df["hcpcs_code"] = df["hcpcs_code"].str.strip()
    df["practitioner_mue"] = pd.to_numeric(
        df["practitioner_mue"], errors="coerce"
    ).fillna(0).astype(int)
    df["facility_mue"] = pd.to_numeric(
        df["facility_mue"], errors="coerce"
    ).fillna(0).astype(int)

    records = df.to_dict(orient="records")
    print(f"  {len(records):,} MUE limit rows to upsert")
    upsert_batches("mue_limits", records)
    print("  MUE limits loaded successfully")


def main():
    if sb is None:
        print("ERROR: SUPABASE_SERVICE_KEY not set. Cannot load data.")
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description="Load NCCI edits and MUE limits into Supabase"
    )
    parser.add_argument("--ncci", help="Path to NCCI edits CSV")
    parser.add_argument("--mue", help="Path to MUE limits CSV")
    args = parser.parse_args()

    if not args.ncci and not args.mue:
        print("Provide at least one of --ncci or --mue")
        sys.exit(1)

    if args.ncci:
        load_ncci(args.ncci)
    if args.mue:
        load_mue(args.mue)

    print("Done.")


if __name__ == "__main__":
    main()
