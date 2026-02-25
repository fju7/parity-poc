"""
Process CMS CLFS (Clinical Laboratory Fee Schedule) data
into a clean lookup CSV for the Parity benchmark API.

Reads:
  - data/cms-clfs/26clabq1.zip (CY 2026 Q1, contains CSV)

Produces:
  - backend/data/clfs_rates.csv (hcpcs_code, payment_rate, description)

Run from the backend/ directory:
  python scripts/process_clfs.py
"""

import os
import zipfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLFS_ZIP = PROJECT_ROOT / "data" / "cms-clfs" / "26clabq1.zip"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data"


def process_clfs():
    """Parse CLFS CSV from the ZIP and produce clfs_rates.csv.

    The CSV has 4 header/disclaimer rows before the column headers.
    Columns: YEAR, HCPCS, MOD, EFF_DATE, INDICATOR, RATE, SHORTDESC, LONGDESC, EXTENDEDLONGDESC
    Some codes appear multiple times with different modifiers (e.g. QW for CLIA-waived).
    We keep only the base row (no modifier) to avoid duplicates.
    """
    print(f"Reading CLFS data from {CLFS_ZIP}")

    with zipfile.ZipFile(CLFS_ZIP, "r") as zf:
        csv_files = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_files:
            raise FileNotFoundError("No CSV file found in CLFS ZIP")
        csv_name = csv_files[0]
        print(f"  Extracting {csv_name}")

        with zf.open(csv_name) as f:
            df = pd.read_csv(f, skiprows=4, encoding="latin-1")

    print(f"  Read {len(df):,} total rows")

    # Keep only base rows (no modifier) to get one rate per code
    base = df[df["MOD"].isna()].copy()
    print(f"  {len(base):,} rows after filtering to base (no modifier)")

    # Clean RATE — stored as float already but with leading zeros (e.g. 00720.00)
    base["RATE"] = pd.to_numeric(base["RATE"], errors="coerce")

    # Drop rows with no rate
    base = base[base["RATE"].notna() & (base["RATE"] > 0)]

    out = pd.DataFrame({
        "hcpcs_code": base["HCPCS"].astype(str).str.strip(),
        "payment_rate": base["RATE"].round(2),
        "description": base["SHORTDESC"].astype(str).str.strip(),
    })

    out = out.sort_values("hcpcs_code").reset_index(drop=True)

    out_path = OUTPUT_DIR / "clfs_rates.csv"
    out.to_csv(out_path, index=False)
    print(f"  Wrote {len(out):,} rows to {out_path}")

    # Show sample
    print("\n  Sample CLFS rates:")
    print(out.head(5).to_string(index=False))

    # Validate target codes
    target_codes = ["36415", "80053", "83036", "84443", "85025"]
    print("\n  Target code validation:")
    for code in target_codes:
        match = out[out["hcpcs_code"] == code]
        if len(match) > 0:
            rate = match.iloc[0]["payment_rate"]
            desc = match.iloc[0]["description"]
            print(f"    {code}: ${rate:.2f} — {desc}")
        else:
            print(f"    {code}: NOT FOUND")

    return out


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    process_clfs()
    print("\nDone.")
