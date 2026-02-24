"""
Process CMS OPPS (Outpatient Prospective Payment System) Addendum B
into a clean lookup CSV for the Parity benchmark API.

Reads:
  - data/cms-opps/january-2026-opps-addendum-b.zip (contains Addendum B CSV)

Produces:
  - backend/data/opps_rates.csv (apc_code, payment_rate, description)

Run from the backend/ directory:
  python scripts/process_opps.py
"""

import os
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OPPS_ZIP = PROJECT_ROOT / "data" / "cms-opps" / "january-2026-opps-addendum-b.zip"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data"


def process_opps():
    """Parse OPPS Addendum B CSV from the ZIP and produce opps_rates.csv.

    The CSV inside the ZIP has 5 header/disclaimer rows before the actual column headers.
    We need: HCPCS Code, Short Descriptor, APC, Payment Rate.
    Only rows with a non-null APC and Payment Rate are useful.
    """
    print(f"Reading OPPS Addendum B from {OPPS_ZIP}")

    # Find the CSV inside the ZIP
    with zipfile.ZipFile(OPPS_ZIP, "r") as zf:
        csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_files:
            raise FileNotFoundError("No CSV file found in OPPS ZIP")
        csv_name = csv_files[0]
        print(f"  Extracting {csv_name}")

        with zf.open(csv_name) as f:
            df = pd.read_csv(f, skiprows=5, encoding="latin-1")

    print(f"  Read {len(df):,} total rows")

    # Filter to rows with an APC assignment and payment rate
    df = df[df["APC"].notna() & df["Payment Rate"].notna()].copy()

    # Clean payment rate (remove $ and commas)
    df["Payment Rate"] = (
        df["Payment Rate"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    df["APC"] = df["APC"].astype(int).astype(str)

    out = pd.DataFrame({
        "apc_code": df["APC"],
        "hcpcs_code": df["HCPCS Code"].str.strip(),
        "payment_rate": df["Payment Rate"].round(2),
        "description": df["Short Descriptor"].str.strip(),
    })

    out = out.sort_values(["apc_code", "hcpcs_code"]).reset_index(drop=True)

    out_path = OUTPUT_DIR / "opps_rates.csv"
    out.to_csv(out_path, index=False)
    print(f"  Wrote {len(out):,} rows to {out_path}")

    # Show sample
    sample = out.head(5)
    print("\n  Sample OPPS rates:")
    print(sample.to_string(index=False))

    # Show unique APC count
    print(f"\n  Unique APC codes: {out['apc_code'].nunique()}")

    return out


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    process_opps()
    print("\nDone.")
