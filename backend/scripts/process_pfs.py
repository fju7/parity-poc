"""
Process CMS Physician Fee Schedule (PFS) Carrier Files and ZIP5 crosswalk
into clean lookup CSVs for the Parity benchmark API.

Reads:
  - data/cms-pfs/cy2026-carrier-files-nonqp-updated-12-29-2025.zip (pre-calculated rates)
  - data/cms-pfs/ZIP5_APR2026.xlsx (ZIP-to-locality crosswalk)

Produces:
  - backend/data/pfs_rates.csv   (cpt_code, carrier, locality_code, nonfacility_amount, facility_amount)
  - backend/data/zip_locality.csv (zip_code, carrier, locality_code, state)

Run from the backend/ directory:
  python scripts/process_pfs.py
"""

import csv
import io
import os
import zipfile
from pathlib import Path

import pandas as pd

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CARRIER_ZIP = PROJECT_ROOT / "data" / "cms-pfs" / "cy2026-carrier-files-nonqp-updated-12-29-2025.zip"
ZIP5_XLSX = PROJECT_ROOT / "data" / "cms-pfs" / "ZIP5_APR2026.xlsx"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "data"


def process_carrier_files():
    """Parse all state carrier .TXT files from the ZIP and produce pfs_rates.csv.

    Carrier file CSV fields (quoted):
      [0] year          "2026"
      [1] carrier       "09102"  (5-digit, zero-padded)
      [2] locality      "03"     (2-char)
      [3] cpt_code      "99213"
      [4] modifier      "  " or "26" etc.
      [5] nonfacility   "0000098.26"
      [6] facility      "0000060.02"
      [7..15] other fields we don't need

    We keep only rows with a blank modifier (no modifier = the base code).
    """
    print(f"Reading carrier files from {CARRIER_ZIP}")

    rows = []
    with zipfile.ZipFile(CARRIER_ZIP, "r") as zf:
        txt_files = [n for n in zf.namelist() if n.upper().endswith(".TXT")]
        print(f"  Found {len(txt_files)} carrier text files")

        for fname in txt_files:
            with zf.open(fname) as f:
                text = f.read().decode("latin-1")
                reader = csv.reader(io.StringIO(text))
                for record in reader:
                    if len(record) < 7:
                        continue
                    modifier = record[4].strip()
                    if modifier:
                        continue  # skip modified codes

                    cpt_code = record[3].strip()
                    carrier = record[1].strip()
                    locality = record[2].strip()
                    nonfacility = float(record[5])
                    facility = float(record[6])

                    rows.append({
                        "cpt_code": cpt_code,
                        "carrier": carrier,
                        "locality_code": locality,
                        "nonfacility_amount": round(nonfacility, 2),
                        "facility_amount": round(facility, 2),
                    })

    df = pd.DataFrame(rows)
    # Drop duplicates (same CPT can appear across state files for the same carrier/locality)
    df = df.drop_duplicates(subset=["cpt_code", "carrier", "locality_code"])
    df = df.sort_values(["cpt_code", "carrier", "locality_code"]).reset_index(drop=True)

    out_path = OUTPUT_DIR / "pfs_rates.csv"
    df.to_csv(out_path, index=False)
    print(f"  Wrote {len(df):,} rows to {out_path}")

    # Verification: check 99213 for a couple localities
    sample = df[df["cpt_code"] == "99213"].head(5)
    print("\n  Sample rates for CPT 99213:")
    print(sample.to_string(index=False))

    return df


def process_zip5():
    """Parse ZIP5_APR2026.xlsx and produce zip_locality.csv.

    Input columns: STATE, ZIP CODE, CARRIER, LOCALITY, ...
    CARRIER may be 4 or 5 digits (integer) — we zero-pad to 5.
    LOCALITY may be 1 or 2 digits (integer) — we zero-pad to 2.
    """
    print(f"\nReading ZIP5 crosswalk from {ZIP5_XLSX}")

    df = pd.read_excel(ZIP5_XLSX)
    print(f"  Read {len(df):,} rows")

    out = pd.DataFrame({
        "zip_code": df["ZIP CODE"].astype(str).str.zfill(5),
        "carrier": df["CARRIER"].astype(str).str.zfill(5),
        "locality_code": df["LOCALITY"].astype(str).str.zfill(2),
        "state": df["STATE"],
    })

    out_path = OUTPUT_DIR / "zip_locality.csv"
    out.to_csv(out_path, index=False)
    print(f"  Wrote {len(out):,} rows to {out_path}")

    # Verification: check zip 33701
    sample = out[out["zip_code"] == "33701"]
    print("\n  ZIP 33701 mapping:")
    print(sample.to_string(index=False))

    return out


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    process_carrier_files()
    process_zip5()
    print("\nDone.")
