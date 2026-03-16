"""
/api/benchmark endpoint — looks up CMS Medicare benchmark rates
for a list of procedure codes at a given provider ZIP code.

Accepts only: zipCode + lineItems[{code, codeType, billedAmount}].
No PHI is accepted or stored.

Supports an optional serviceDate field.  When the service date falls
within the current rate period, the fast in-memory path is used.
When it falls outside (i.e. an older bill), the endpoint checks
Supabase for historical rate data and falls back to current rates
with a warning if none is loaded yet.
"""

from __future__ import annotations

import gc
import os
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from routers.coding_intelligence import run_coding_checks
from utils.rate_versioning import (
    get_version_for_date,
    is_using_current_rates,
    parse_service_date,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Data vintage constants — update these when loading new CMS data files
# ---------------------------------------------------------------------------

PFS_VINTAGE = "2026"
OPPS_VINTAGE = "2026"
CLFS_VINTAGE = "2026 Q1"

PFS_SOURCE = f"CMS Medicare Physician Fee Schedule {PFS_VINTAGE}"
OPPS_SOURCE = f"CMS Outpatient Prospective Payment System {OPPS_VINTAGE}"
CLFS_SOURCE = f"CMS Clinical Laboratory Fee Schedule {CLFS_VINTAGE}"

PFS_VINTAGE_SHORT = f"CMS PFS {PFS_VINTAGE}"
OPPS_VINTAGE_SHORT = f"CMS OPPS {OPPS_VINTAGE}"
CLFS_VINTAGE_SHORT = f"CMS CLFS {CLFS_VINTAGE}"

# ---------------------------------------------------------------------------
# Data loading (called once at import time via load_data())
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

pfs_rates: pd.DataFrame = pd.DataFrame()
zip_locality: pd.DataFrame = pd.DataFrame()
opps_rates: pd.DataFrame = pd.DataFrame()
clfs_rates: pd.DataFrame = pd.DataFrame()


def _mem_mb() -> float:
    """Return current process RSS in MB (uses psutil if available)."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def load_data():
    """Load CSVs into DataFrames. Called once at app startup.

    Memory-optimised: uses only needed columns, float32, and category dtypes.
    """
    global pfs_rates, zip_locality, opps_rates, clfs_rates

    mem_before = _mem_mb()

    pfs_path = DATA_DIR / "pfs_rates.csv"
    zip_path = DATA_DIR / "zip_locality.csv"
    opps_path = DATA_DIR / "opps_rates.csv"
    clfs_path = DATA_DIR / "clfs_rates.csv"

    # --- PFS rates (841K rows) ---
    # All 5 columns are needed; load amounts as float32 directly
    pfs_rates = pd.read_csv(
        pfs_path,
        usecols=["cpt_code", "carrier", "locality_code",
                 "nonfacility_amount", "facility_amount"],
        dtype={
            "cpt_code": "category",
            "carrier": "category",
            "locality_code": "category",
        },
    )
    pfs_rates["nonfacility_amount"] = pd.to_numeric(
        pfs_rates["nonfacility_amount"], errors="coerce"
    ).astype("float32")
    pfs_rates["facility_amount"] = pd.to_numeric(
        pfs_rates["facility_amount"], errors="coerce"
    ).astype("float32")
    pfs_rates.set_index(["cpt_code", "carrier", "locality_code"], inplace=True)
    pfs_rates.sort_index(inplace=True)

    # --- ZIP-to-locality crosswalk (43K rows) ---
    # Only need zip_code, carrier, locality_code (skip 'state')
    zip_locality = pd.read_csv(
        zip_path,
        usecols=["zip_code", "carrier", "locality_code"],
        dtype={
            "zip_code": str,
            "carrier": "category",
            "locality_code": "category",
        },
    )
    zip_locality.set_index("zip_code", inplace=True)

    # --- OPPS rates (7K rows) ---
    # Only need hcpcs_code, payment_rate, description (skip 'apc_code')
    opps_rates = pd.read_csv(
        opps_path,
        usecols=["hcpcs_code", "payment_rate", "description"],
        dtype={"hcpcs_code": str},
    )
    opps_rates["payment_rate"] = pd.to_numeric(
        opps_rates["payment_rate"], errors="coerce"
    ).astype("float32")
    opps_rates.set_index("hcpcs_code", inplace=True)
    opps_rates.sort_index(inplace=True)

    # --- CLFS rates (2K rows) ---
    clfs_rates = pd.read_csv(
        clfs_path,
        usecols=["hcpcs_code", "payment_rate", "description"],
        dtype={"hcpcs_code": str},
    )
    clfs_rates["payment_rate"] = pd.to_numeric(
        clfs_rates["payment_rate"], errors="coerce"
    ).astype("float32")
    clfs_rates.set_index("hcpcs_code", inplace=True)
    clfs_rates.sort_index(inplace=True)

    gc.collect()

    mem_after = _mem_mb()
    df_mem = (
        pfs_rates.memory_usage(deep=True).sum()
        + zip_locality.memory_usage(deep=True).sum()
        + opps_rates.memory_usage(deep=True).sum()
        + clfs_rates.memory_usage(deep=True).sum()
    ) / 1024 / 1024

    print(
        f"Loaded benchmark data: "
        f"{len(pfs_rates):,} PFS rates, "
        f"{len(zip_locality):,} ZIP mappings, "
        f"{len(opps_rates):,} OPPS rates, "
        f"{len(clfs_rates):,} CLFS rates"
    )
    print(
        f"Memory: {mem_before:.0f} MB -> {mem_after:.0f} MB "
        f"(DataFrames: {df_mem:.1f} MB)"
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
    lineItems: List[LineItemRequest]
    serviceDate: Optional[str] = None  # MM/DD/YYYY or YYYY-MM-DD


class LineItemResponse(BaseModel):
    code: str
    codeType: str
    billedAmount: float
    benchmarkRate: Optional[float]
    benchmarkSource: str
    dataVintage: Optional[str]
    localityCode: Optional[str]
    isHistorical: bool = False
    historicalDataAvailable: bool = True
    warning: Optional[str] = None


class CodingAlert(BaseModel):
    checkType: str
    codes: List[str]
    confidence: str
    severity: str
    message: str
    source: str


class BenchmarkResponse(BaseModel):
    lineItems: List[LineItemResponse]
    codingAlerts: List[CodingAlert] = []


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/api/benchmark", response_model=BenchmarkResponse)
def benchmark(req: BenchmarkRequest):
    # Look up carrier + locality for the given ZIP
    carrier, locality = resolve_locality(req.zipCode)

    # Parse service date to decide fast-path vs historical lookup
    service_date = parse_service_date(req.serviceDate) if req.serviceDate else None
    use_historical = False
    if service_date is not None:
        try:
            use_historical = not is_using_current_rates(service_date)
        except Exception:
            # Supabase unavailable — stay on fast path
            use_historical = False

    results = []
    for item in req.lineItems:
        if use_historical:
            rate, source, loc, vintage, is_hist, hist_avail, warning = (
                lookup_rate_historical(
                    item.code, item.codeType, service_date, carrier, locality
                )
            )
            results.append(
                LineItemResponse(
                    code=item.code,
                    codeType=item.codeType,
                    billedAmount=item.billedAmount,
                    benchmarkRate=rate,
                    benchmarkSource=source,
                    dataVintage=vintage,
                    localityCode=loc,
                    isHistorical=is_hist,
                    historicalDataAvailable=hist_avail,
                    warning=warning,
                )
            )
        else:
            rate, source, loc, vintage, note = lookup_rate(
                item.code, item.codeType, carrier, locality
            )
            results.append(
                LineItemResponse(
                    code=item.code,
                    codeType=item.codeType,
                    billedAmount=item.billedAmount,
                    benchmarkRate=rate,
                    benchmarkSource=source,
                    dataVintage=vintage,
                    localityCode=loc,
                    warning=note,
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
    code: str,
    code_type: str,
    carrier: Optional[str],
    locality: Optional[str],
    date_of_service=None,
) -> tuple[Optional[float], str, Optional[str], Optional[str], Optional[str]]:
    """Look up the benchmark rate for a procedure code.

    Returns (rate, source, locality_code, data_vintage, rate_note).

    If *date_of_service* is provided (date or "YYYY-MM-DD" string) and falls
    in a prior rate year, queries Supabase historical tables first.  Falls
    back to current in-memory rates with a warning note if historical data
    is not loaded.  When date_of_service is None or in the current rate year,
    uses the fast in-memory path with no Supabase call.
    """
    code = code.strip()

    # --- Resolve date_of_service to a date object ---
    svc_date = None
    if date_of_service is not None:
        if isinstance(date_of_service, str):
            svc_date = parse_service_date(date_of_service)
        else:
            svc_date = date_of_service

    # --- Historical path: prior-year dates ---
    if svc_date is not None and str(svc_date.year) != PFS_VINTAGE:
        (rate, source, loc, vintage,
         is_hist, hist_avail, warning) = lookup_rate_historical(
            code, code_type, svc_date, carrier, locality
        )
        note = None
        if warning:
            note = warning
        elif is_hist:
            note = f"Benchmarked against CMS {svc_date.year} rates — the rates in effect on your date of service."
        return rate, source, loc, vintage, note

    # --- Current-year fast path (in-memory DataFrames) ---
    if code_type in ("CPT", "UNKNOWN") and carrier and locality:
        rate = lookup_pfs(code, carrier, locality)
        if rate is not None:
            return rate, PFS_SOURCE, locality, PFS_VINTAGE_SHORT, None

    rate = lookup_opps(code)
    if rate is not None:
        return rate, OPPS_SOURCE, locality, OPPS_VINTAGE_SHORT, None

    rate = lookup_clfs(code)
    if rate is not None:
        return rate, CLFS_SOURCE, locality, CLFS_VINTAGE_SHORT, None

    return None, "NOT_FOUND", locality, None, None


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
        facility = float(row["facility_amount"])
        nonfacility = float(row["nonfacility_amount"])
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
        rate = float(row["payment_rate"])
        if rate > 0:
            return round(rate, 2)
    except KeyError:
        pass
    return None


def lookup_clfs(code: str) -> Optional[float]:
    """Look up a code in the CLFS (Clinical Laboratory Fee Schedule) rates table."""
    try:
        row = clfs_rates.loc[code]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        rate = float(row["payment_rate"])
        if rate > 0:
            return round(rate, 2)
    except KeyError:
        pass
    return None


def get_all_pfs_rates_for_locality(carrier: str, locality: str) -> List[dict]:
    """Get all PFS rates for a given carrier/locality.

    Returns list of {cpt_code, nonfacility_amount, facility_amount}.
    """
    try:
        idx = pd.IndexSlice
        subset = pfs_rates.loc[idx[:, carrier, locality], :].copy()
        subset = subset.reset_index()
        mask = (subset["nonfacility_amount"] > 0) | (subset["facility_amount"] > 0)
        subset = subset[mask]
        subset["nonfacility_amount"] = subset["nonfacility_amount"].round(2)
        subset["facility_amount"] = subset["facility_amount"].round(2)
        subset["cpt_code"] = subset["cpt_code"].astype(str)
        return subset[["cpt_code", "nonfacility_amount", "facility_amount"]].to_dict("records")
    except (KeyError, TypeError):
        return []


# ---------------------------------------------------------------------------
# Historical rate lookup (Supabase-backed)
# ---------------------------------------------------------------------------


def lookup_rate_historical(
    code: str,
    code_type: str,
    service_date,
    carrier: Optional[str],
    locality: Optional[str],
) -> tuple[Optional[float], str, Optional[str], Optional[str], bool, bool, Optional[str]]:
    """Look up benchmark rate from Supabase historical tables.

    Same PFS -> OPPS -> CLFS chain as lookup_rate(), but against the
    versioned historical tables.

    Returns (rate, source, locality_code, data_vintage,
             is_historical, historical_data_available, warning).

    If no historical data exists for the resolved version, falls back
    to in-memory current rates with appropriate warning flags.
    """
    from utils.rate_versioning import get_version_for_date

    code = code.strip()
    warning = None

    # --- Try PFS historical ---
    if code_type in ("CPT", "UNKNOWN") and carrier and locality:
        rate, found = _query_historical_pfs(code, carrier, locality, service_date)
        if rate is not None:
            return (rate, PFS_SOURCE, locality, PFS_VINTAGE_SHORT,
                    True, True, None)
        if not found:
            # Version exists but no rows — no historical data loaded yet
            pass

    # --- Try OPPS historical ---
    rate, found = _query_historical_opps(code, service_date)
    if rate is not None:
        return (rate, OPPS_SOURCE, locality, OPPS_VINTAGE_SHORT,
                True, True, None)

    # --- Try CLFS historical ---
    rate, found = _query_historical_clfs(code, service_date)
    if rate is not None:
        return (rate, CLFS_SOURCE, locality, CLFS_VINTAGE_SHORT,
                True, True, None)

    # --- Fall back to current in-memory rates ---
    rate, source, loc, vintage, _note = lookup_rate(code, code_type, carrier, locality)
    if rate is not None:
        year = service_date.year if service_date else "prior"
        warning = (
            f"Using current 2026 rates — historical {year} rates "
            f"not yet available"
        )
        return (rate, source, loc, vintage,
                False, False, warning)

    return (None, "NOT_FOUND", locality, None, False, False, None)


def _query_historical_pfs(
    code: str, carrier: str, locality: str, service_date
) -> tuple[Optional[float], bool]:
    """Query pfs_rates_historical via Supabase.

    Returns (rate, data_exists_for_version).
    """
    try:
        version_id = get_version_for_date("PFS", service_date)
        if version_id is None:
            return None, False

        from utils.rate_versioning import _get_supabase
        sb = _get_supabase()
        result = (
            sb.table("pfs_rates_historical")
            .select("facility_amount, nonfacility_amount")
            .eq("version_id", version_id)
            .eq("hcpcs_code", code)
            .eq("carrier", carrier)
            .eq("locality_code", locality)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None, False

        row = result.data[0]
        facility = float(row["facility_amount"] or 0)
        nonfacility = float(row["nonfacility_amount"] or 0)
        rate = max(facility, nonfacility)
        if rate > 0:
            return round(rate, 2), True
        return None, True
    except Exception:
        return None, False


def _query_historical_opps(code: str, service_date) -> tuple[Optional[float], bool]:
    """Query opps_rates_historical via Supabase."""
    try:
        version_id = get_version_for_date("OPPS", service_date)
        if version_id is None:
            return None, False

        from utils.rate_versioning import _get_supabase
        sb = _get_supabase()
        result = (
            sb.table("opps_rates_historical")
            .select("payment_rate")
            .eq("version_id", version_id)
            .eq("hcpcs_code", code)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None, False

        rate = float(result.data[0]["payment_rate"] or 0)
        if rate > 0:
            return round(rate, 2), True
        return None, True
    except Exception:
        return None, False


def _query_historical_clfs(code: str, service_date) -> tuple[Optional[float], bool]:
    """Query clfs_rates_historical via Supabase."""
    try:
        version_id = get_version_for_date("CLFS", service_date)
        if version_id is None:
            return None, False

        from utils.rate_versioning import _get_supabase
        sb = _get_supabase()
        result = (
            sb.table("clfs_rates_historical")
            .select("payment_rate")
            .eq("version_id", version_id)
            .eq("hcpcs_code", code)
            .limit(1)
            .execute()
        )

        if not result.data:
            return None, False

        rate = float(result.data[0]["payment_rate"] or 0)
        if rate > 0:
            return round(rate, 2), True
        return None, True
    except Exception:
        return None, False


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

    # Try CLFS (which has descriptions for lab codes)
    if code in clfs_rates.index:
        row = clfs_rates.loc[code]
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
