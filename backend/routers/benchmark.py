"""
/api/benchmark endpoint — looks up CMS Medicare benchmark rates
for a list of procedure codes at a given provider ZIP code.

Accepts only: zipCode + lineItems[{code, codeType, billedAmount}].
No PHI is accepted or stored.
"""

from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from routers.coding_intelligence import run_coding_checks

router = APIRouter()

# ---------------------------------------------------------------------------
# Data loading (called once at import time via load_data())
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

pfs_rates: pd.DataFrame = pd.DataFrame()
zip_locality: pd.DataFrame = pd.DataFrame()
opps_rates: pd.DataFrame = pd.DataFrame()


def load_data():
    """Load CSVs into DataFrames. Called once at app startup."""
    global pfs_rates, zip_locality, opps_rates

    pfs_path = DATA_DIR / "pfs_rates.csv"
    zip_path = DATA_DIR / "zip_locality.csv"
    opps_path = DATA_DIR / "opps_rates.csv"

    pfs_rates = pd.read_csv(pfs_path, dtype=str)
    pfs_rates["nonfacility_amount"] = pd.to_numeric(
        pfs_rates["nonfacility_amount"], errors="coerce"
    )
    pfs_rates["facility_amount"] = pd.to_numeric(
        pfs_rates["facility_amount"], errors="coerce"
    )
    # Index for fast lookup
    pfs_rates.set_index(["cpt_code", "carrier", "locality_code"], inplace=True)
    pfs_rates.sort_index(inplace=True)

    zip_locality = pd.read_csv(zip_path, dtype=str)
    zip_locality.set_index("zip_code", inplace=True)

    opps_rates = pd.read_csv(opps_path, dtype=str)
    opps_rates["payment_rate"] = pd.to_numeric(
        opps_rates["payment_rate"], errors="coerce"
    )
    opps_rates.set_index("hcpcs_code", inplace=True)
    opps_rates.sort_index(inplace=True)

    print(
        f"Loaded benchmark data: "
        f"{len(pfs_rates):,} PFS rates, "
        f"{len(zip_locality):,} ZIP mappings, "
        f"{len(opps_rates):,} OPPS rates"
    )


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class LineItemRequest(BaseModel):
    code: str
    codeType: str  # "CPT", "REVENUE", "UNKNOWN"
    billedAmount: float


class BenchmarkRequest(BaseModel):
    zipCode: str
    lineItems: list[LineItemRequest]


class LineItemResponse(BaseModel):
    code: str
    codeType: str
    billedAmount: float
    benchmarkRate: Optional[float]
    benchmarkSource: str
    localityCode: Optional[str]


class CodingAlert(BaseModel):
    checkType: str
    codes: list[str]
    confidence: str
    severity: str
    message: str
    source: str


class BenchmarkResponse(BaseModel):
    lineItems: list[LineItemResponse]
    codingAlerts: list[CodingAlert] = []


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/api/benchmark", response_model=BenchmarkResponse)
def benchmark(req: BenchmarkRequest):
    # Look up carrier + locality for the given ZIP
    carrier, locality = resolve_locality(req.zipCode)

    results = []
    for item in req.lineItems:
        rate, source, loc = lookup_rate(
            item.code, item.codeType, carrier, locality
        )
        results.append(
            LineItemResponse(
                code=item.code,
                codeType=item.codeType,
                billedAmount=item.billedAmount,
                benchmarkRate=rate,
                benchmarkSource=source,
                localityCode=loc,
            )
        )

    # Run coding intelligence checks
    codes = [item.code for item in req.lineItems]
    coding_alerts = run_coding_checks(codes)

    return BenchmarkResponse(lineItems=results, codingAlerts=coding_alerts)


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def resolve_locality(zip_code: str) -> tuple[Optional[str], Optional[str]]:
    """Resolve a 5-digit ZIP to (carrier, locality_code)."""
    zip_code = zip_code.strip().zfill(5)
    if zip_code in zip_locality.index:
        row = zip_locality.loc[zip_code]
        # Handle case where multiple rows match (take first)
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        return row["carrier"], row["locality_code"]
    return None, None


def lookup_rate(
    code: str, code_type: str, carrier: Optional[str], locality: Optional[str]
) -> tuple[Optional[float], str, Optional[str]]:
    """Look up the benchmark rate for a procedure code.

    Returns (rate, source, locality_code).
    """
    code = code.strip()

    # Try PFS lookup first (for CPT codes)
    if code_type in ("CPT", "UNKNOWN") and carrier and locality:
        rate = lookup_pfs(code, carrier, locality)
        if rate is not None:
            return rate, "CMS_PFS_2026", locality

    # Try OPPS lookup (for revenue codes or CPT codes not found in PFS)
    rate = lookup_opps(code)
    if rate is not None:
        return rate, "CMS_OPPS_2026", locality

    # If code_type was UNKNOWN, we already tried both
    return None, "NOT_FOUND", locality


def lookup_pfs(
    cpt_code: str, carrier: str, locality: str
) -> Optional[float]:
    """Look up a CPT code in the PFS rates table.

    Uses facility_amount (since we're comparing against hospital bills).
    Falls back to nonfacility_amount if facility is zero.
    """
    try:
        row = pfs_rates.loc[(cpt_code, carrier, locality)]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        facility = row["facility_amount"]
        nonfacility = row["nonfacility_amount"]
        # Prefer nonfacility for office visits, facility for hospital
        # For now, return the higher of the two (more conservative benchmark)
        rate = max(facility, nonfacility)
        if rate > 0:
            return round(rate, 2)
    except KeyError:
        pass
    return None


def lookup_opps(code: str) -> Optional[float]:
    """Look up a code in the OPPS rates table."""
    try:
        row = opps_rates.loc[code]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        rate = row["payment_rate"]
        if rate > 0:
            return round(rate, 2)
    except KeyError:
        pass
    return None


# ---------------------------------------------------------------------------
# CPT description lookup
# ---------------------------------------------------------------------------

class CPTDescriptionResponse(BaseModel):
    code: str
    description: str
    found: bool


@router.get("/api/cpt-description", response_model=CPTDescriptionResponse)
def cpt_description(code: str):
    """Look up a CPT/HCPCS code description from the loaded rate data."""
    code = code.strip()
    if not code:
        return CPTDescriptionResponse(code=code, description="", found=False)

    # Look up in OPPS rates (which have descriptions)
    if code in opps_rates.index:
        row = opps_rates.loc[code]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        desc = row.get("description", "")
        if desc and str(desc) != "nan":
            return CPTDescriptionResponse(code=code, description=str(desc), found=True)

    # Check if code exists in PFS (no description, but confirms it's valid)
    try:
        matches = pfs_rates.xs(code, level="cpt_code")
        if len(matches) > 0:
            return CPTDescriptionResponse(code=code, description="", found=True)
    except KeyError:
        pass

    return CPTDescriptionResponse(code=code, description="", found=False)
