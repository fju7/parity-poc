"""
Benchmark Observations: Crowdsourced Commercial Rate Database

POST /api/benchmark-observations  — save anonymized billing observations

Stores anonymized data points from completed bill analyses. No user_id,
no patient info, no provider names, no exact dates, no full ZIP codes.
"""

import os
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from supabase import create_client

router = APIRouter(prefix="/api", tags=["benchmark-observations"])

# ---------------------------------------------------------------------------
# Supabase client (lazy singleton)
# ---------------------------------------------------------------------------

_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is None:
        url = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if not key:
            raise RuntimeError("SUPABASE_SERVICE_KEY not set")
        _supabase = create_client(url, key)
    return _supabase


# ---------------------------------------------------------------------------
# Insurer Normalization
# ---------------------------------------------------------------------------

INSURER_ALIASES = {
    "cigna": ["cigna", "cigna healthcare", "cigna health", "evernorth"],
    "aetna": ["aetna", "aetna health", "cvs health", "cvs/aetna"],
    "uhc": ["united", "unitedhealthcare", "united healthcare", "uhc", "optum"],
    "bcbs": [
        "blue cross", "blue shield", "bcbs", "anthem", "carefirst",
        "highmark", "premera", "regence", "horizon", "independence",
        "excellus", "wellmark", "florida blue", "blue cross blue shield",
    ],
    "humana": ["humana"],
    "kaiser": ["kaiser", "kaiser permanente"],
    "tricare": ["tricare"],
    "medicare_advantage": ["medicare advantage", "ma plan"],
    "medicaid_managed": ["medicaid", "managed medicaid"],
}


def normalize_insurer(raw_text: str) -> tuple[str, str]:
    """Returns (normalized_key, raw_text)."""
    lower = raw_text.lower().strip()
    for key, aliases in INSURER_ALIASES.items():
        for alias in aliases:
            if alias in lower:
                return key, raw_text
    return "other", raw_text


# ---------------------------------------------------------------------------
# Provider Specialty Inference
# ---------------------------------------------------------------------------

CPT_SPECIALTY_MAP = {
    # Dermatology
    "11102": "dermatology", "11103": "dermatology", "11104": "dermatology",
    "17000": "dermatology", "17003": "dermatology", "17004": "dermatology",
    # Cardiology
    "93000": "cardiology", "93010": "cardiology", "93306": "cardiology",
    "93307": "cardiology", "93308": "cardiology", "93320": "cardiology",
    # Orthopedics
    "27447": "orthopedics", "27130": "orthopedics", "29881": "orthopedics",
    # Primary Care / E&M
    "99213": "primary_care", "99214": "primary_care", "99215": "primary_care",
    "99203": "primary_care", "99204": "primary_care", "99205": "primary_care",
    # Imaging
    "70553": "radiology", "73721": "radiology", "74177": "radiology",
    # Lab
    "80053": "laboratory", "85025": "laboratory", "36415": "laboratory",
}


def infer_specialty(cpt_codes: list[str]) -> str:
    """Infer provider specialty from the most common specialty across CPT codes."""
    specialties = [CPT_SPECIALTY_MAP.get(code, "unknown") for code in cpt_codes]
    specialties = [s for s in specialties if s != "unknown"]
    if not specialties:
        return "unknown"
    return Counter(specialties).most_common(1)[0][0]


# ---------------------------------------------------------------------------
# Region Derivation
# ---------------------------------------------------------------------------

ZIP3_TO_REGION = {
    "600": "chicago_suburbs_il", "606": "chicago_il",
    "100": "manhattan_ny", "101": "manhattan_ny", "104": "bronx_ny",
    "110": "queens_ny", "112": "brooklyn_ny",
    "900": "los_angeles_ca", "902": "los_angeles_ca", "910": "pasadena_ca",
    "941": "san_francisco_ca", "945": "oakland_ca", "950": "san_jose_ca",
    "770": "houston_tx", "750": "dallas_tx", "730": "oklahoma_city_ok",
    "331": "miami_fl", "327": "orlando_fl", "336": "tampa_fl", "334": "west_palm_fl",
    "200": "washington_dc", "201": "washington_dc", "209": "silver_spring_md",
    "021": "boston_ma", "060": "hartford_ct",
    "191": "philadelphia_pa", "150": "pittsburgh_pa",
    "300": "atlanta_ga", "303": "atlanta_ga",
    "480": "detroit_mi", "481": "detroit_mi",
    "551": "minneapolis_mn", "553": "minneapolis_mn",
    "631": "st_louis_mo",
    "802": "denver_co", "803": "denver_co",
    "850": "phoenix_az", "852": "phoenix_az",
    "981": "seattle_wa", "980": "seattle_wa",
}

ZIP3_TO_STATE = {
    "600": "IL", "606": "IL",
    "100": "NY", "101": "NY", "104": "NY", "110": "NY", "112": "NY",
    "900": "CA", "902": "CA", "910": "CA", "941": "CA", "945": "CA", "950": "CA",
    "770": "TX", "750": "TX",
    "730": "OK",
    "331": "FL", "327": "FL", "336": "FL", "334": "FL",
    "200": "DC", "201": "MD", "209": "MD",
    "021": "MA",
    "060": "CT",
    "191": "PA", "150": "PA",
    "300": "GA", "303": "GA",
    "480": "MI", "481": "MI",
    "551": "MN", "553": "MN",
    "631": "MO",
    "802": "CO", "803": "CO",
    "850": "AZ", "852": "AZ",
    "981": "WA", "980": "WA",
}


def derive_region(zip_code: str) -> tuple[str, str, str]:
    """Returns (region_name, state_code, zip3)."""
    zip3 = zip_code[:3]
    region = ZIP3_TO_REGION.get(zip3, f"region_{zip3}")
    state = ZIP3_TO_STATE.get(zip3, "unknown")
    return region, state, zip3


# ---------------------------------------------------------------------------
# Outlier Detection
# ---------------------------------------------------------------------------

CPT_AMOUNT_RANGES = {
    "99213": (50, 500),
    "99214": (75, 700),
    "99215": (100, 900),
    "99203": (75, 600),
    "99204": (100, 800),
    "99205": (125, 1000),
    "11102": (80, 800),
    "11103": (50, 600),
    "17000": (50, 500),
    "93000": (30, 400),
    "93306": (100, 1500),
    "93307": (80, 1200),
    "27447": (1500, 50000),
    "27130": (1500, 50000),
    "29881": (500, 15000),
    "70553": (200, 5000),
    "73721": (150, 3000),
    "74177": (200, 4000),
    "80053": (10, 300),
    "85025": (5, 150),
    "36415": (3, 50),
}

DEFAULT_RANGE = (1, 100000)


def check_outlier(cpt_code: str, amount: float) -> bool:
    """Returns True if the amount is likely an outlier."""
    low, high = CPT_AMOUNT_RANGES.get(cpt_code, DEFAULT_RANGE)
    return amount < low or amount > high


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class ObservationLineItem(BaseModel):
    cpt_code: Optional[str] = None
    amount: Optional[float] = None
    amount_type: str = "billed_amount"
    cpt_confidence: Optional[str] = "medium"
    facility_type: Optional[str] = "unknown"


class SaveObservationsRequest(BaseModel):
    line_items: List[ObservationLineItem]
    insurer: Optional[str] = None
    zip_code: str
    network_status: Optional[str] = "unknown"
    input_method: str
    service_date: Optional[str] = None
    provider_specialty: Optional[str] = None


class SaveObservationsResponse(BaseModel):
    saved: int
    message: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/benchmark-observations", response_model=SaveObservationsResponse)
async def save_benchmark_observations(req: SaveObservationsRequest):
    """Anonymize and store benchmark observations from a completed bill analysis."""
    # Normalize insurer
    if req.insurer:
        insurer_normalized, insurer_raw = normalize_insurer(req.insurer)
    else:
        insurer_normalized, insurer_raw = "unknown", None

    # Derive region from ZIP
    region, state_code, zip3 = derive_region(req.zip_code)

    # Only store month/year
    service_month = req.service_date[:7] if req.service_date and len(req.service_date) >= 7 else None

    # Infer specialty if not provided
    provider_specialty = req.provider_specialty
    if not provider_specialty:
        cpt_codes = [item.cpt_code for item in req.line_items if item.cpt_code]
        provider_specialty = infer_specialty(cpt_codes)

    observations = []
    for item in req.line_items:
        if not item.cpt_code or item.amount is None:
            continue

        amount = float(item.amount)
        is_outlier = check_outlier(item.cpt_code, amount)

        # Determine confidence
        confidence = item.cpt_confidence or "medium"
        if confidence == "inferred":
            confidence = "low"
        if is_outlier:
            confidence = "low"

        observations.append({
            "cpt_code": item.cpt_code,
            "amount": amount,
            "amount_type": item.amount_type,
            "insurer": insurer_normalized,
            "insurer_raw": insurer_raw,
            "region": region,
            "state_code": state_code,
            "zip3": zip3,
            "provider_specialty": provider_specialty,
            "network_status": req.network_status or "unknown",
            "facility_type": item.facility_type or "unknown",
            "service_month": service_month,
            "confidence": confidence,
            "input_method": req.input_method,
            "is_outlier": is_outlier,
        })

    if observations:
        try:
            sb = _get_supabase()
            sb.table("benchmark_observations").insert(observations).execute()
        except Exception as exc:
            # Fire-and-forget pattern — log but don't fail the user's request
            print(f"WARNING: Failed to save benchmark observations: {exc}")
            return SaveObservationsResponse(saved=0, message="Observations could not be saved.")

    return SaveObservationsResponse(
        saved=len(observations),
        message=f"{len(observations)} anonymized observation(s) added to benchmark database.",
    )
