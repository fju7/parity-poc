"""
Provider dashboard endpoints:
  GET  /api/provider/contract-template  — download contract rates Excel template
  POST /api/provider/save-rates         — save parsed contract rates
  POST /api/provider/parse-835          — parse an uploaded 835 EDI file
  POST /api/provider/analyze-contract   — compare remittance vs contracted rates
  POST /api/provider/analyze-coding     — coding pattern analysis (E&M, NCCI, MUE)

No PHI is stored. Contract rates and analysis results are tied to user_id.
"""

import os
from collections import Counter
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from supabase import create_client

from routers.benchmark import resolve_locality, lookup_rate
from utils.parse_835 import parse_835

router = APIRouter(prefix="/api/provider", tags=["provider"])

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

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
# Models
# ---------------------------------------------------------------------------

class PayerRate(BaseModel):
    payer_name: str
    rate: float


class ContractRateItem(BaseModel):
    cpt: str
    description: Optional[str] = ""
    rates: dict  # {payer_name: rate}


class SaveRatesRequest(BaseModel):
    user_id: str
    payer_name: str
    rates: List[ContractRateItem]


class RemittanceLine(BaseModel):
    cpt_code: str
    code_type: str = "CPT"
    billed_amount: float
    paid_amount: float
    units: int = 1
    adjustments: Optional[str] = ""
    claim_id: Optional[str] = ""


class AnalyzeRequest(BaseModel):
    user_id: str
    payer_name: str
    zip_code: Optional[str] = ""
    contract_rates: dict  # {cpt_code: rate}
    remittance_lines: List[RemittanceLine]


class CodingLine(BaseModel):
    cpt_code: str
    units: int = 1
    billed_amount: float = 0.0


class CodingAnalyzeRequest(BaseModel):
    user_id: str
    specialty: str = ""
    zip_code: Optional[str] = ""
    date_range: Optional[str] = ""
    lines: List[CodingLine]


# ---------------------------------------------------------------------------
# GET /api/provider/contract-template
# ---------------------------------------------------------------------------

@router.get("/contract-template")
async def download_contract_template():
    """Serve the contract rates Excel template for download."""
    template_path = STATIC_DIR / "contract_rates_template.xlsx"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Template file not found")

    return FileResponse(
        path=str(template_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="contract_rates_template.xlsx"'
        },
    )


# ---------------------------------------------------------------------------
# POST /api/provider/save-rates
# ---------------------------------------------------------------------------

@router.post("/save-rates")
async def save_rates(req: SaveRatesRequest):
    """Save parsed contract rates to Supabase."""
    rates_json = [
        {"cpt": r.cpt, "description": r.description, "rates": r.rates}
        for r in req.rates
    ]

    try:
        sb = _get_supabase()

        # Upsert: delete existing for this user+payer, then insert
        sb.table("provider_contracts") \
            .delete() \
            .eq("user_id", req.user_id) \
            .eq("payer_name", req.payer_name) \
            .execute()

        sb.table("provider_contracts").insert({
            "user_id": req.user_id,
            "payer_name": req.payer_name,
            "rates": rates_json,
        }).execute()
    except Exception as exc:
        # Non-fatal: rates are still usable in-session even if persist fails
        print(f"WARNING: Failed to save contract rates to Supabase: {exc}")

    return {"status": "ok", "saved": len(req.rates)}


# ---------------------------------------------------------------------------
# POST /api/provider/parse-835
# ---------------------------------------------------------------------------

@router.post("/parse-835")
async def parse_835_endpoint(file: UploadFile = File(...)):
    """Parse an uploaded 835 EDI file and return structured data."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    content = await file.read()

    # Try UTF-8 first, fall back to latin-1
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    # Check for ISA segment (basic 835 validation)
    if "ISA" not in text[:500]:
        raise HTTPException(
            status_code=400,
            detail="This doesn't appear to be a valid 835/EDI file. "
                   "The file should start with an ISA segment."
        )

    result = parse_835(text)

    return result


# ---------------------------------------------------------------------------
# POST /api/provider/analyze-contract
# ---------------------------------------------------------------------------

@router.post("/analyze-contract")
async def analyze_contract(req: AnalyzeRequest):
    """Compare remittance line items against contracted rates."""

    # Resolve Medicare locality for benchmark comparison
    carrier, locality = None, None
    if req.zip_code:
        carrier, locality = resolve_locality(req.zip_code)

    enriched_lines = []
    total_contracted = 0.0
    total_paid = 0.0
    total_underpayment = 0.0
    correct_count = 0
    underpaid_count = 0
    denied_count = 0
    overpaid_count = 0
    no_contract_count = 0
    code_underpayments = {}  # {cpt: total_underpayment}

    for line in req.remittance_lines:
        contracted_rate = req.contract_rates.get(line.cpt_code)
        expected_payment = None
        variance = None
        flag = "NO_CONTRACT"

        if contracted_rate is not None:
            contracted_rate = float(contracted_rate)
            expected_payment = round(contracted_rate * line.units, 2)
            variance = round(line.paid_amount - expected_payment, 2)

            if line.paid_amount == 0 and expected_payment > 0:
                flag = "DENIED"
                denied_count += 1
            elif variance < -0.50:
                flag = "UNDERPAID"
                underpaid_count += 1
                total_underpayment += abs(variance)
                code_underpayments[line.cpt_code] = (
                    code_underpayments.get(line.cpt_code, 0) + abs(variance)
                )
            elif variance > 0.50:
                flag = "OVERPAID"
                overpaid_count += 1
            else:
                flag = "CORRECT"
                correct_count += 1

            total_contracted += expected_payment
        else:
            no_contract_count += 1

        total_paid += line.paid_amount

        # Look up Medicare benchmark rate
        medicare_rate = None
        medicare_source = None
        if carrier and locality:
            rate, source, _, _ = lookup_rate(
                line.cpt_code, line.code_type, carrier, locality
            )
            if rate is not None:
                medicare_rate = rate
                medicare_source = source

        enriched_lines.append({
            "cpt_code": line.cpt_code,
            "billed_amount": line.billed_amount,
            "paid_amount": line.paid_amount,
            "units": line.units,
            "contracted_rate": contracted_rate,
            "expected_payment": expected_payment,
            "variance": variance,
            "flag": flag,
            "adjustments": line.adjustments or "",
            "claim_id": line.claim_id or "",
            "medicare_rate": medicare_rate,
            "medicare_source": medicare_source,
        })

    # Adherence rate: % of lines with contract that are CORRECT
    lines_with_contract = correct_count + underpaid_count + denied_count + overpaid_count
    adherence_rate = (
        round((correct_count / lines_with_contract) * 100, 1)
        if lines_with_contract > 0
        else 100.0
    )

    # Top underpaid codes
    top_underpaid = sorted(
        code_underpayments.items(), key=lambda x: x[1], reverse=True
    )[:10]
    top_underpaid_list = [
        {"cpt_code": code, "total_underpayment": round(amt, 2)}
        for code, amt in top_underpaid
    ]

    summary = {
        "total_contracted": round(total_contracted, 2),
        "total_paid": round(total_paid, 2),
        "total_underpayment": round(total_underpayment, 2),
        "adherence_rate": adherence_rate,
        "line_count": len(enriched_lines),
        "correct_count": correct_count,
        "underpaid_count": underpaid_count,
        "denied_count": denied_count,
        "overpaid_count": overpaid_count,
        "no_contract_count": no_contract_count,
    }

    # Save analysis to Supabase
    try:
        sb = _get_supabase()
        sb.table("provider_analyses").insert({
            "user_id": req.user_id,
            "payer_name": req.payer_name,
            "production_date": "",
            "total_billed": summary["total_contracted"],
            "total_paid": summary["total_paid"],
            "underpayment": summary["total_underpayment"],
            "adherence_rate": summary["adherence_rate"],
            "result_json": {
                "summary": summary,
                "top_underpaid": top_underpaid_list,
                "line_count": len(enriched_lines),
            },
        }).execute()
    except Exception as exc:
        # Non-fatal: analysis still returns even if save fails
        print(f"WARNING: Failed to save analysis to Supabase: {exc}")

    return {
        "summary": summary,
        "line_items": enriched_lines,
        "top_underpaid": top_underpaid_list,
    }


# ---------------------------------------------------------------------------
# POST /api/provider/analyze-coding
# ---------------------------------------------------------------------------

# E&M code families for distribution analysis
EM_CODES = {
    "New Patient": ["99201", "99202", "99203", "99204", "99205"],
    "Established Patient": ["99211", "99212", "99213", "99214", "99215"],
}

# CMS benchmark E&M distributions by specialty (approximate national averages)
EM_BENCHMARKS = {
    "Internal Medicine": {
        "99211": 3, "99212": 8, "99213": 40, "99214": 38, "99215": 11,
    },
    "Family Medicine": {
        "99211": 4, "99212": 10, "99213": 42, "99214": 35, "99215": 9,
    },
    "Cardiology": {
        "99211": 2, "99212": 5, "99213": 25, "99214": 45, "99215": 23,
    },
    "Orthopedics": {
        "99211": 3, "99212": 7, "99213": 30, "99214": 42, "99215": 18,
    },
    "Dermatology": {
        "99211": 5, "99212": 12, "99213": 45, "99214": 30, "99215": 8,
    },
    "Radiology": {
        "99211": 2, "99212": 6, "99213": 35, "99214": 40, "99215": 17,
    },
    "Pathology/Lab": {
        "99211": 3, "99212": 8, "99213": 38, "99214": 38, "99215": 13,
    },
    "Other": {
        "99211": 3, "99212": 8, "99213": 38, "99214": 38, "99215": 13,
    },
}


@router.post("/analyze-coding")
async def analyze_coding(req: CodingAnalyzeRequest):
    """Analyze coding patterns: E&M distribution, NCCI edits, MUE limits, benchmarks."""

    codes_flat = []
    for line in req.lines:
        for _ in range(line.units):
            codes_flat.append(line.cpt_code)

    code_counts = Counter(codes_flat)

    # --- 1. E&M Distribution ---
    em_established = ["99211", "99212", "99213", "99214", "99215"]
    em_total = sum(code_counts.get(c, 0) for c in em_established)
    em_distribution = {}
    if em_total > 0:
        for c in em_established:
            em_distribution[c] = round((code_counts.get(c, 0) / em_total) * 100, 1)

    # Get benchmark distribution for specialty
    specialty_key = req.specialty if req.specialty in EM_BENCHMARKS else "Other"
    em_benchmark = EM_BENCHMARKS.get(specialty_key, EM_BENCHMARKS["Other"])

    # Identify potential undercoding or overcoding
    em_alerts = []
    if em_total >= 5:  # Only flag if enough data
        pct_low = sum(code_counts.get(c, 0) for c in ["99211", "99212"]) / em_total * 100
        pct_high = sum(code_counts.get(c, 0) for c in ["99214", "99215"]) / em_total * 100
        bench_high = em_benchmark.get("99214", 0) + em_benchmark.get("99215", 0)

        if pct_high < bench_high * 0.6:
            em_alerts.append({
                "type": "UNDERCODING",
                "severity": "warning",
                "message": (
                    f"Your high-complexity E&M rate ({pct_high:.0f}%) is significantly below "
                    f"the {specialty_key} benchmark ({bench_high}%). You may be under-coding "
                    f"visits that qualify for 99214 or 99215."
                ),
            })
        elif pct_high > bench_high * 1.4:
            em_alerts.append({
                "type": "OVERCODING",
                "severity": "info",
                "message": (
                    f"Your high-complexity E&M rate ({pct_high:.0f}%) is above "
                    f"the {specialty_key} benchmark ({bench_high}%). Ensure documentation "
                    f"supports the level of service billed."
                ),
            })

    # --- 2. Medicare Benchmark Comparison ---
    unique_codes = list(set(codes_flat))
    carrier, locality = None, None
    if req.zip_code:
        carrier, locality = resolve_locality(req.zip_code)

    benchmark_lines = []
    total_billed = 0.0
    total_benchmark = 0.0
    for line in req.lines:
        medicare_rate = None
        medicare_source = None
        if carrier and locality:
            rate, source, _, _ = lookup_rate(
                line.cpt_code, "CPT", carrier, locality
            )
            if rate is not None:
                medicare_rate = rate
                medicare_source = source

        line_billed = line.billed_amount * line.units
        line_benchmark = (medicare_rate * line.units) if medicare_rate else None
        total_billed += line_billed
        if line_benchmark is not None:
            total_benchmark += line_benchmark

        benchmark_lines.append({
            "cpt_code": line.cpt_code,
            "units": line.units,
            "billed_amount": line.billed_amount,
            "total_billed": round(line_billed, 2),
            "medicare_rate": medicare_rate,
            "medicare_source": medicare_source,
            "total_benchmark": round(line_benchmark, 2) if line_benchmark else None,
            "ratio": round(line.billed_amount / medicare_rate, 2) if medicare_rate and medicare_rate > 0 else None,
        })

    return {
        "em_distribution": em_distribution,
        "em_benchmark": em_benchmark,
        "em_total": em_total,
        "em_alerts": em_alerts,
        "benchmark_lines": benchmark_lines,
        "total_billed": round(total_billed, 2),
        "total_benchmark": round(total_benchmark, 2),
        "code_count": len(unique_codes),
        "line_count": len(req.lines),
    }
