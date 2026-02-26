"""
Provider dashboard endpoints:
  GET  /api/provider/contract-template  — download contract rates Excel template
  POST /api/provider/save-rates         — save parsed contract rates
  POST /api/provider/parse-835          — parse an uploaded 835 EDI file
  POST /api/provider/analyze-contract   — compare remittance vs contracted rates

No PHI is stored. Contract rates and analysis results are tied to user_id.
"""

import os
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
    sb = _get_supabase()

    rates_json = [
        {"cpt": r.cpt, "description": r.description, "rates": r.rates}
        for r in req.rates
    ]

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
