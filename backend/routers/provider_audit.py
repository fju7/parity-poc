"""Provider audit endpoints — CRUD, analysis, report generation, admin management."""

from __future__ import annotations

import base64
import io
import json
import os
import zipfile
from collections import Counter
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from routers.signal_intelligence import aggregate_denial_patterns
from routers.provider_shared import (
    _get_supabase, _get_authenticated_user, _verify_admin,
    _call_claude, _call_claude_text,
    _run_analysis_for_payer, _aggregate_underpayments,
    _email_wrapper, _send_submission_confirmation, _send_delivery_email, _send_followup_email,
    STATIC_DIR, FEE_SCHEDULE_EXTRACTION_PROMPT, DENIAL_SYSTEM_PROMPT,
    EM_CODES, EM_BENCHMARKS, CPT_DENIAL_BENCHMARKS, DENIAL_BENCHMARK_DATA_NOTE,
    SaveRatesRequest, AnalyzeRequest, CodingAnalyzeRequest, AnalyzeDenialsRequest,
    ExtractFeeScheduleTextRequest, CalculateMedicarePercentageRequest,
    AuditReportRequest, SubmitAuditRequest,
    AdminArchiveBody, AdminDeleteBody, AdminRunAnalysisBody,
    AdminNotesBody, AdminDeliverBody, AdminFollowUpBody, AdminStatusBody,
    RemittanceLine,
)
from routers.benchmark import resolve_locality, lookup_rate, get_all_pfs_rates_for_locality
from utils.parse_835 import parse_835

router = APIRouter(tags=["provider"])


@router.get("/demo-835")
async def download_demo_835():
    """Serve the demo 835 file for the sample upload flow."""
    demo_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "chesapeake_835_2024.edi")
    if not os.path.exists(demo_path):
        raise HTTPException(status_code=404, detail="Demo file not found")
    return FileResponse(demo_path, media_type="text/plain", filename="Chesapeake_Family_Medicine_Sample.835")


@router.get("/demo-analysis")
async def demo_analysis():
    """Parse the Chesapeake demo 835 and return structured analysis for the demo page.

    Returns practice info, payer breakdown, denial details, underpayment
    estimates (vs 120% of Medicare for Baltimore ZIP 21201), and summary stats.
    No authentication required — this is the public demo endpoint.
    """
    demo_path = os.path.join(os.path.dirname(__file__), "..", "test_data", "chesapeake_835_2024.edi")
    if not os.path.exists(demo_path):
        raise HTTPException(status_code=404, detail="Demo file not found")

    with open(demo_path, "r") as f:
        edi_text = f.read()

    parsed = parse_835(edi_text)

    # ── Build line-item detail from the parse ──────────────────────────
    line_items = parsed.get("line_items", [])

    # Medicare rate lookup for Baltimore, MD (ZIP 21201)
    zip_code = "21201"
    carrier, locality = resolve_locality(zip_code)
    medicare_pct = 120  # demo contracted rate = 120% of Medicare
    multiplier = medicare_pct / 100.0

    # CPT description map
    CPT_LABELS = {
        "99213": "Office visit, est. low",
        "99214": "Office visit, est. moderate",
        "99215": "Office visit, est. high",
        "99396": "Preventive visit, est. 40-64",
        "36415": "Venipuncture",
        "80053": "Comprehensive metabolic panel",
        "85025": "CBC with differential",
        "93000": "ECG, 12-lead",
        "99441": "Telephone E/M, 5-10 min",
        "G0439": "Annual wellness visit, subsequent",
        "90707": "MMR vaccine",
    }

    # Classify each line item
    paid_lines = []
    denied_lines = []
    underpayments = []
    total_underpayment = 0.0

    for li in line_items:
        cpt = li.get("cpt_code", "")
        billed = li.get("billed_amount", 0) or 0
        paid = li.get("paid_amount", 0) or 0
        adjs = li.get("adjustments", [])
        denial_codes = [a["code"] for a in adjs if a.get("group_code") == "CO" and paid == 0]

        # Look up contracted rate (120% of Medicare)
        contracted = None
        if carrier and locality and cpt:
            rate_result = lookup_rate(cpt, "CPT", carrier, locality)
            medicare_rate = rate_result[0] if rate_result and rate_result[0] else None
            if medicare_rate:
                contracted = round(medicare_rate * multiplier, 2)

        if paid == 0 and denial_codes:
            denied_lines.append({
                "cpt": cpt,
                "desc": CPT_LABELS.get(cpt, cpt),
                "billed": billed,
                "reasonCode": denial_codes[0],
                "amount": billed,
                "claim_id": li.get("claim_id", ""),
            })
        else:
            paid_lines.append({
                "cpt": cpt,
                "desc": CPT_LABELS.get(cpt, cpt),
                "billed": billed,
                "paid": paid,
                "contracted": contracted,
                "claim_id": li.get("claim_id", ""),
            })
            # Detect underpayment
            if contracted and paid < contracted:
                variance = round(contracted - paid, 2)
                total_underpayment += variance
                underpayments.append({
                    "cpt": cpt,
                    "desc": CPT_LABELS.get(cpt, cpt),
                    "billed": billed,
                    "paid": paid,
                    "contracted": contracted,
                    "variance": variance,
                    "flag": "Underpaid",
                })

    total_billed = parsed.get("total_billed", 0) or 0
    total_paid = parsed.get("total_paid", 0) or 0
    denial_total = sum(d["amount"] for d in denied_lines)
    monthly_gap = round(denial_total + total_underpayment, 2)
    annualized_gap = round(monthly_gap * 12, 2)

    # Denial code summary
    denial_code_counts = Counter(d["reasonCode"] for d in denied_lines)

    # Group denied lines by code for display
    denial_code_details = {
        "CO-97": "Procedure/service bundled — payer says it should be included in another service.",
        "CO-4": "Modifier required — payer expected a modifier that was missing or incorrect.",
        "CO-50": "Non-covered service — payer says this service is not covered under the plan.",
    }

    return {
        "practice": {
            "name": parsed.get("payee_name", "Chesapeake Family Medicine"),
            "location": "Baltimore, MD",
            "providers": 4,
            "specialty": "Family Medicine",
            "zip": zip_code,
            "payer_name": parsed.get("payer_name", "BlueCross Maryland"),
            "medicare_pct": medicare_pct,
        },
        "summary": {
            "total_billed": total_billed,
            "total_paid": total_paid,
            "total_underpayment": round(total_underpayment, 2),
            "total_denied": denial_total,
            "monthly_gap": monthly_gap,
            "annualized_gap": annualized_gap,
            "claim_count": parsed.get("claim_count", 0),
            "paid_count": len(paid_lines),
            "denied_count": len(denied_lines),
            "production_date": parsed.get("production_date", ""),
            "denial_code_counts": dict(denial_code_counts),
        },
        "underpayments": underpayments,
        "denials": denied_lines,
        "denial_code_details": denial_code_details,
        "paid_lines": paid_lines,
    }


# ---------------------------------------------------------------------------
# Helper: Save anonymized benchmark observations
# ---------------------------------------------------------------------------

def _normalize_payer_category(payer_name: str) -> str:
    """Normalize payer name to a broad category."""
    lower = (payer_name or "").lower()
    if "medicare" in lower or "cms" in lower:
        return "Medicare"
    if "bcbs" in lower or "blue cross" in lower or "blue shield" in lower:
        return "BCBS"
    if "aetna" in lower:
        return "Aetna"
    if "united" in lower or "uhc" in lower:
        return "UnitedHealthcare"
    if "cigna" in lower:
        return "Cigna"
    if "humana" in lower:
        return "Humana"
    return "Commercial"


def _zip_to_region(zip_code: str) -> str:
    """Derive coarse region from ZIP code first digit."""
    if not zip_code or not zip_code.strip():
        return "Unknown"
    first = zip_code.strip()[0]
    if first in ("0", "1"):
        return "Northeast"
    if first in ("2", "3"):
        return "South"
    if first in ("4", "5", "6"):
        return "Midwest"
    if first in ("7", "8", "9"):
        return "West"
    return "Unknown"


def _save_benchmark_observations(enriched_lines: list, payer_name: str, specialty: str, zip_code: str, sb):
    """Save anonymized observations from an 835 analysis for proprietary benchmarking."""
    try:
        payer_category = _normalize_payer_category(payer_name)
        region = _zip_to_region(zip_code)
        line_count = len(enriched_lines)

        observations = []
        for line in enriched_lines:
            cpt = line.get("cpt_code", "")
            flag = line.get("flag", "")
            if not cpt or flag == "NO_CONTRACT":
                continue

            paid = line.get("paid_amount", 0)
            expected = line.get("expected_payment", 0)
            pct = round(paid / expected, 4) if expected and expected > 0 else None

            denial_code = None
            if flag == "DENIED" and line.get("adjustments"):
                denial_code = line["adjustments"].split(",")[0].strip()

            observations.append({
                "cpt_code": cpt,
                "payer_category": payer_category,
                "specialty": specialty or None,
                "was_denied": flag == "DENIED",
                "was_underpaid": flag == "UNDERPAID",
                "paid_as_pct_of_contracted": pct,
                "denial_code": denial_code,
                "region": region,
                "line_count_in_analysis": line_count,
            })

        # Batch insert (max 100 per call)
        for i in range(0, len(observations), 100):
            batch = observations[i:i + 100]
            sb.table("provider_benchmark_observations").insert(batch).execute()

        if observations:
            print(f"[Provider] Saved {len(observations)} benchmark observations")
    except Exception as exc:
        print(f"[Provider] Benchmark observation save failed: {exc}")


# ---------------------------------------------------------------------------
# GET /contract-template
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
# POST /save-rates
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
            .eq("company_id", req.user_id) \
            .eq("payer_name", req.payer_name) \
            .execute()

        sb.table("provider_contracts").insert({
            "company_id": req.user_id,
            "payer_name": req.payer_name,
            "rates": rates_json,
        }).execute()
    except Exception as exc:
        # Non-fatal: rates are still usable in-session even if persist fails
        print(f"WARNING: Failed to save contract rates to Supabase: {exc}")

    return {"status": "ok", "saved": len(req.rates)}


@router.get("/saved-rates")
async def get_saved_rates(user_id: str):
    """Load all saved contract rates for a provider company."""
    try:
        sb = _get_supabase()
        result = (
            sb.table("provider_contracts")
            .select("payer_name, rates, created_at")
            .eq("company_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        payers = []
        for row in result.data or []:
            rates_dict = {}
            for item in row.get("rates") or []:
                cpt = item.get("cpt")
                # Flatten multi-payer rates to first available rate value
                rate_vals = item.get("rates", {})
                if isinstance(rate_vals, dict):
                    for v in rate_vals.values():
                        if v is not None:
                            rates_dict[cpt] = v
                            break
            payers.append({
                "name": row["payer_name"],
                "rates": rates_dict,
                "codeCount": len(rates_dict),
                "saved_at": row.get("created_at"),
            })
        return {"payers": payers}
    except Exception as exc:
        print(f"[Provider] Failed to load saved rates: {exc}")
        return {"payers": []}


# ---------------------------------------------------------------------------
# POST /parse-835
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


def _parse_single_835(content: bytes, filename: str) -> dict:
    """Parse a single 835 file from raw bytes. Returns result dict or error dict."""
    try:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")

        if not text.strip():
            return {"filename": filename, "error": "File is empty"}

        if "ISA" not in text[:500]:
            return {"filename": filename, "error": "Not a valid 835/EDI file (no ISA segment)"}

        result = parse_835(text)
        result["filename"] = filename
        return result
    except Exception as exc:
        return {"filename": filename, "error": str(exc)}


# ---------------------------------------------------------------------------
# POST /parse-835-batch
# ---------------------------------------------------------------------------

@router.post("/parse-835-batch")
async def parse_835_batch(files: List[UploadFile] = File(...)):
    """Parse multiple 835 files. Accepts .835, .edi, .txt, and .zip files.
    Zip files are extracted and each contained 835 is parsed individually."""

    results = []

    for upload in files:
        content = await upload.read()
        fname = upload.filename or "unknown"
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""

        if ext == "zip":
            # Extract and parse each file in the zip
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    for name in zf.namelist():
                        # Skip directories and hidden files
                        if name.endswith("/") or name.startswith("__MACOSX"):
                            continue
                        inner_ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
                        if inner_ext not in ("835", "edi", "txt", ""):
                            continue
                        inner_content = zf.read(name)
                        results.append(_parse_single_835(inner_content, name))
            except zipfile.BadZipFile:
                results.append({"filename": fname, "error": "Invalid zip file"})
        else:
            results.append(_parse_single_835(content, fname))

    successful = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]

    return {
        "results": successful,
        "errors": failed,
        "total_files": len(results),
        "successful": len(successful),
        "failed": len(failed),
    }


# ---------------------------------------------------------------------------
# POST /extract-fee-schedule-pdf
# ---------------------------------------------------------------------------

@router.post("/extract-fee-schedule-pdf")
async def extract_fee_schedule_pdf(file: UploadFile = File(...)):
    """Extract fee schedule rates from a payer contract PDF using Claude vision."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    b64 = base64.standard_b64encode(content).decode("utf-8")

    content_blocks = [
        {
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": b64,
            },
        },
        {
            "type": "text",
            "text": "Extract all CPT/HCPCS codes and their contracted reimbursement rates from this fee schedule document.",
        },
    ]

    result = _call_claude(
        system_prompt=FEE_SCHEDULE_EXTRACTION_PROMPT,
        user_content=content_blocks,
        max_tokens=8192,
    )

    if result is None:
        raise HTTPException(
            status_code=502,
            detail="Could not extract rates from PDF. The document may not contain a recognizable fee schedule.",
        )

    return result


# ---------------------------------------------------------------------------
# POST /extract-fee-schedule-text
# ---------------------------------------------------------------------------

@router.post("/extract-fee-schedule-text")
async def extract_fee_schedule_text(req: ExtractFeeScheduleTextRequest):
    """Extract fee schedule rates from pasted text using Claude."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="No text provided")

    if len(req.text) > 50000:
        raise HTTPException(status_code=400, detail="Text too long (max 50,000 characters)")

    result = _call_claude(
        system_prompt=FEE_SCHEDULE_EXTRACTION_PROMPT,
        user_content=f"Extract all CPT/HCPCS codes and rates from this fee schedule text:\n\n{req.text}",
        max_tokens=8192,
    )

    if result is None:
        raise HTTPException(
            status_code=502,
            detail="Could not extract rates from text. Please check that the text contains CPT codes and dollar amounts.",
        )

    return result


# ---------------------------------------------------------------------------
# POST /extract-fee-schedule-image
# ---------------------------------------------------------------------------

@router.post("/extract-fee-schedule-image")
async def extract_fee_schedule_image(file: UploadFile = File(...)):
    """Extract fee schedule rates from a photo/screenshot using Claude vision."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="Image too large (max 10MB)")

    # Determine media type
    fname = (file.filename or "").lower()
    if fname.endswith(".png"):
        media_type = "image/png"
    elif fname.endswith(".gif"):
        media_type = "image/gif"
    elif fname.endswith(".webp"):
        media_type = "image/webp"
    else:
        media_type = "image/jpeg"

    b64 = base64.standard_b64encode(content).decode("utf-8")

    content_blocks = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": b64,
            },
        },
        {
            "type": "text",
            "text": "Extract all CPT/HCPCS codes and their contracted reimbursement rates from this fee schedule image.",
        },
    ]

    result = _call_claude(
        system_prompt=FEE_SCHEDULE_EXTRACTION_PROMPT,
        user_content=content_blocks,
        max_tokens=8192,
    )

    if result is None:
        raise HTTPException(
            status_code=502,
            detail="Could not extract rates from image. Please ensure the image clearly shows CPT codes and rates.",
        )

    return result


# ---------------------------------------------------------------------------
# POST /calculate-medicare-percentage
# ---------------------------------------------------------------------------

@router.post("/calculate-medicare-percentage")
async def calculate_medicare_percentage(req: CalculateMedicarePercentageRequest):
    """Calculate contracted rates as a percentage of Medicare PFS rates."""
    if req.percentage < 1 or req.percentage > 500:
        raise HTTPException(status_code=400, detail="Percentage must be between 1 and 500")

    if not req.zip_code or len(req.zip_code.strip()) < 5:
        raise HTTPException(status_code=400, detail="Valid 5-digit ZIP code required")

    carrier, locality = resolve_locality(req.zip_code.strip())
    if not carrier or not locality:
        raise HTTPException(
            status_code=404,
            detail=f"No Medicare locality found for ZIP code {req.zip_code}. Please check the ZIP code.",
        )

    all_rates = get_all_pfs_rates_for_locality(carrier, locality)
    if not all_rates:
        raise HTTPException(
            status_code=404,
            detail=f"No Medicare rates found for locality {carrier}/{locality}.",
        )

    multiplier = req.percentage / 100.0
    rates = []
    for r in all_rates:
        # Use nonfacility_amount for office-based physician practices
        medicare_rate = r["nonfacility_amount"]
        if medicare_rate and medicare_rate > 0:
            rates.append({
                "cpt": r["cpt_code"],
                "rate": round(medicare_rate * multiplier, 2),
                "description": "",
                "medicare_rate": medicare_rate,
            })

    return {
        "payer_name": req.payer_name,
        "effective_date": req.effective_date,
        "percentage": req.percentage,
        "locality": f"{carrier}/{locality}",
        "total_codes": len(rates),
        "rates": rates,
    }


# ---------------------------------------------------------------------------
# POST /analyze-contract
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
    billed_below_count = 0
    total_chargemaster_gap = 0.0
    code_underpayments = {}  # {cpt: total_underpayment}

    # Track adjustment codes for preventable denial analysis
    denial_adj_codes = []  # list of adjustment code strings for denied lines

    for line in req.remittance_lines:
        contracted_rate = req.contract_rates.get(line.cpt_code)
        expected_payment = None
        variance = None
        flag = "NO_CONTRACT"
        chargemaster_gap = None

        if contracted_rate is not None:
            contracted_rate = float(contracted_rate)
            expected_payment = round(contracted_rate * line.units, 2)
            variance = round(line.paid_amount - expected_payment, 2)

            # --- Capability 3: Billed-Below-Contract check ---
            if line.billed_amount < contracted_rate:
                chargemaster_gap = round((contracted_rate - line.billed_amount) * line.units, 2)
                billed_below_count += 1
                total_chargemaster_gap += chargemaster_gap
                flag = "BILLED_BELOW"

            elif line.paid_amount == 0 and expected_payment > 0:
                flag = "DENIED"
                denied_count += 1
                denial_adj_codes.append(line.adjustments or "")
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
            rate, source, _, _, _ = lookup_rate(
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
            "chargemaster_gap": chargemaster_gap,
            "adjustments": line.adjustments or "",
            "claim_id": line.claim_id or "",
            "medicare_rate": medicare_rate,
            "medicare_source": medicare_source,
            "date_of_service": line.date_of_service or "",
            "claim_number": line.claim_number or line.claim_id or "",
            "adjudication_date": line.adjudication_date or "",
            "modifiers": line.modifiers or [],
            "rendering_provider_npi": line.rendering_provider_npi or "",
            "place_of_service": line.place_of_service or "",
        })

    # Adherence rate: % of lines paid at or above contracted rate
    # Correct + Overpaid = adherent (payer met or exceeded obligation)
    # Underpaid + Denied = non-adherent
    lines_with_contract = (correct_count + underpaid_count + denied_count
                           + overpaid_count + billed_below_count)
    adherent_count = correct_count + overpaid_count
    adherence_rate = (
        round((adherent_count / lines_with_contract) * 100, 1)
        if lines_with_contract > 0
        else 100.0
    )

    # --- Capability 4: Performance Scorecard metrics ---
    clean_claim_rate = (
        round(((correct_count + overpaid_count) / lines_with_contract) * 100, 1)
        if lines_with_contract > 0
        else 100.0
    )
    denial_rate = (
        round((denied_count / lines_with_contract) * 100, 1)
        if lines_with_contract > 0
        else 0.0
    )

    # Preventable denials: CO-16 (missing info) and CO-97 (bundled)
    # CO-45 (contractual adjustment) is NOT preventable
    preventable_codes = {"CO-16", "CO-97", "16", "97"}
    preventable_denial_count = 0
    for adj_str in denial_adj_codes:
        codes = [c.strip() for c in adj_str.split(",")]
        if any(c in preventable_codes for c in codes):
            preventable_denial_count += 1
    preventable_denial_rate = (
        round((preventable_denial_count / denied_count) * 100, 1)
        if denied_count > 0
        else 0.0
    )

    # AI scorecard narrative
    scorecard_narrative = None
    if lines_with_contract >= 3:
        try:
            scorecard_data = _call_claude(
                system_prompt=(
                    "You are a supportive healthcare revenue cycle consultant advising "
                    "a small physician practice. Given billing performance metrics, write "
                    "a concise 3-4 sentence assessment. Lead with what the data shows "
                    "factually, not a judgment of the practice. If metrics are below "
                    "benchmark, frame as an opportunity with a specific recommended action. "
                    'Use phrases like "the data suggests" and "an opportunity to improve" '
                    'rather than words like "deficient", "alarming", or "failure". Be '
                    "direct and specific about numbers but constructive in tone. Remember "
                    "this practice may be seeing this analysis for the first time. "
                    "Return ONLY valid JSON with a "
                    'single key "narrative" containing your assessment string.'
                ),
                user_content=json.dumps({
                    "clean_claim_rate": clean_claim_rate,
                    "clean_claim_benchmark": 95.0,
                    "denial_rate": denial_rate,
                    "denial_benchmark": 5.0,
                    "payer_adherence_rate": adherence_rate,
                    "preventable_denial_rate": preventable_denial_rate,
                    "total_lines": lines_with_contract,
                    "payer_name": req.payer_name,
                }),
                max_tokens=1024,
            )
            if scorecard_data and "narrative" in scorecard_data:
                scorecard_narrative = scorecard_data["narrative"]
        except Exception as exc:
            print(f"[Provider AI] Scorecard narrative failed: {exc}")

    # Top underpaid codes
    top_underpaid = sorted(
        code_underpayments.items(), key=lambda x: x[1], reverse=True
    )[:10]
    top_underpaid_list = [
        {"cpt_code": code, "total_underpayment": round(amt, 2)}
        for code, amt in top_underpaid
    ]

    # --- CPT-level denial rate benchmarking ---
    denial_benchmarks = []
    cpt_denied_counts = {}
    cpt_total_counts = {}
    cpt_denied_value = {}
    for el in enriched_lines:
        cpt = el["cpt_code"]
        cpt_total_counts[cpt] = cpt_total_counts.get(cpt, 0) + 1
        if el["flag"] == "DENIED":
            cpt_denied_counts[cpt] = cpt_denied_counts.get(cpt, 0) + 1
            cpt_denied_value[cpt] = (
                cpt_denied_value.get(cpt, 0.0)
                + el.get("billed_amount", 0.0)
            )

    for cpt, total in cpt_total_counts.items():
        if total < 2:
            continue
        denied = cpt_denied_counts.get(cpt, 0)
        practice_rate = round((denied / total) * 100, 1)
        benchmark = CPT_DENIAL_BENCHMARKS.get(cpt)
        if benchmark:
            gap = round(practice_rate - benchmark["avg_denial_rate"], 1)
            denial_benchmarks.append({
                "cpt_code": cpt,
                "practice_denial_rate": practice_rate,
                "industry_avg_rate": benchmark["avg_denial_rate"],
                "gap": gap,
                "gap_direction": "above" if gap > 0 else "below",
                "category": benchmark["category"],
                "source": benchmark["source"],
                "note": benchmark["note"],
                "total_claims": total,
                "denied_claims": denied,
                "denied_value": round(cpt_denied_value.get(cpt, 0.0), 2),
            })

    denial_benchmarks.sort(key=lambda x: x["gap"], reverse=True)

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
        "billed_below_count": billed_below_count,
        "total_chargemaster_gap": round(total_chargemaster_gap, 2),
    }

    scorecard = {
        "clean_claim_rate": clean_claim_rate,
        "denial_rate": denial_rate,
        "payer_adherence_rate": adherence_rate,
        "preventable_denial_rate": preventable_denial_rate,
        "narrative": scorecard_narrative,
    }

    # Look up practice specialty from profile (used by coding analysis + benchmark observations)
    specialty = ""
    if req.user_id:
        try:
            sb_prof = _get_supabase()
            prof = sb_prof.table("provider_profiles").select("specialty").eq("company_id", req.user_id).execute()
            if prof.data:
                specialty = prof.data[0].get("specialty", "") or ""
        except Exception:
            pass

    # Save analysis to Supabase
    try:
        sb = _get_supabase()
        sb.table("provider_analyses").insert({
            "company_id": req.user_id,
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
                "denial_benchmarks": denial_benchmarks,
                "line_items": enriched_lines,
                "scorecard": scorecard,
            },
        }).execute()
    except Exception as exc:
        # Non-fatal: analysis still returns even if save fails
        print(f"WARNING: Failed to save analysis to Supabase: {exc}")

    # Save anonymized observations for proprietary benchmark building
    try:
        _save_benchmark_observations(
            enriched_lines=enriched_lines,
            payer_name=req.payer_name,
            specialty=specialty,
            zip_code=req.zip_code if hasattr(req, "zip_code") and req.zip_code else "",
            sb=_get_supabase(),
        )
    except Exception as exc:
        print(f"[Provider] Benchmark observation save failed (non-fatal): {exc}")

    # Auto-run coding analysis from the 835 line items
    coding_analysis = None
    try:
        # Infer date range from service dates in line items
        date_range = ""
        service_dates = [l.get("service_date") or "" for l in enriched_lines if l.get("service_date")]
        if service_dates:
            sorted_dates = sorted(d for d in service_dates if d)
            if sorted_dates:
                date_range = f"{sorted_dates[0]} to {sorted_dates[-1]}"

        coding_lines = [
            {"cpt_code": l["cpt_code"], "units": l.get("units", 1), "billed_amount": l.get("billed_amount", 0)}
            for l in enriched_lines if l.get("cpt_code")
        ]
        if coding_lines:
            coding_analysis = _run_coding_analysis_from_835(coding_lines, specialty, date_range)
    except Exception as exc:
        print(f"[Provider] Auto coding analysis failed (non-fatal): {exc}")

    return {
        "summary": summary,
        "line_items": enriched_lines,
        "top_underpaid": top_underpaid_list,
        "scorecard": scorecard,
        "coding_analysis": coding_analysis,
        "denial_benchmarks": denial_benchmarks,
        "denial_benchmark_note": DENIAL_BENCHMARK_DATA_NOTE if denial_benchmarks else "",
    }


# ---------------------------------------------------------------------------
# Helper: Run coding analysis from 835 line items
# ---------------------------------------------------------------------------

def _run_coding_analysis_from_835(line_items: list, specialty: str, date_range: str = "") -> dict:
    """Run E&M distribution + revenue gap analysis from 835 parsed line items.

    Takes the same line_items format returned by analyze-contract (with cpt_code, units, billed_amount)
    and returns the same structure as /analyze-coding.
    """
    codes_flat = []
    for item in line_items:
        cpt = item.get("cpt_code", "")
        if not cpt:
            continue
        units = item.get("units", 1) or 1
        for _ in range(units):
            codes_flat.append(cpt)

    code_counts = Counter(codes_flat)

    em_established = ["99211", "99212", "99213", "99214", "99215"]
    em_total = sum(code_counts.get(c, 0) for c in em_established)
    em_distribution = {}
    if em_total > 0:
        for c in em_established:
            em_distribution[c] = round((code_counts.get(c, 0) / em_total) * 100, 1)

    specialty_key = specialty if specialty in EM_BENCHMARKS else "Other"
    em_benchmark = EM_BENCHMARKS.get(specialty_key, EM_BENCHMARKS["Other"])

    em_alerts = []
    if em_total >= 5:
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

    revenue_gap = None
    has_undercoding = any(a["type"] == "UNDERCODING" for a in em_alerts)
    if has_undercoding and em_total > 0:
        em_medicare_rates = {
            "99211": 27.0, "99212": 59.0, "99213": 95.0,
            "99214": 135.0, "99215": 190.0,
        }

        gap_lines = []
        total_gap = 0.0
        for code in em_established:
            current_pct = em_distribution.get(code, 0)
            bench_pct = em_benchmark.get(code, 0)
            if bench_pct > current_pct:
                visit_gap = round((bench_pct - current_pct) / 100 * em_total, 1)
                rate = em_medicare_rates.get(code, 0)
                gap_value = round(visit_gap * rate, 2)
                total_gap += gap_value
                gap_lines.append({
                    "code": code,
                    "current_pct": current_pct,
                    "benchmark_pct": bench_pct,
                    "visit_gap": visit_gap,
                    "rate": rate,
                    "revenue_gap": gap_value,
                })

        weeks = 4
        if date_range:
            try:
                parts = date_range.split(" to ")
                if len(parts) == 2:
                    from datetime import datetime
                    d1 = datetime.strptime(parts[0].strip(), "%Y-%m-%d")
                    d2 = datetime.strptime(parts[1].strip(), "%Y-%m-%d")
                    weeks = max((d2 - d1).days / 7, 1)
            except Exception:
                pass

        annualized_gap = round(total_gap * (52 / max(weeks, 1)), 2)

        gap_narrative = None
        if total_gap > 0:
            try:
                gap_data = _call_claude(
                    system_prompt=(
                        "You are a medical billing analyst. Given an E&M coding gap "
                        "analysis for a physician practice, write 2-3 sentences explaining "
                        "the estimated revenue gap in plain language. Be specific about "
                        "the dollar amount and the codes driving the gap. Include one "
                        "sentence noting that the estimate assumes documentation supports "
                        "higher complexity billing. Be direct and factual, not alarming. "
                        "Return ONLY valid JSON with a single key \"narrative\"."
                    ),
                    user_content=json.dumps({
                        "specialty": specialty_key,
                        "total_gap_period": total_gap,
                        "annualized_gap": annualized_gap,
                        "weeks_of_data": round(weeks, 1),
                        "gap_by_code": gap_lines,
                        "em_total": em_total,
                    }),
                    max_tokens=512,
                )
                if gap_data and "narrative" in gap_data:
                    gap_narrative = gap_data["narrative"]
            except Exception as exc:
                print(f"[Provider AI] Revenue gap narrative failed: {exc}")

        revenue_gap = {
            "gap_lines": gap_lines,
            "total_gap_period": round(total_gap, 2),
            "annualized_gap": annualized_gap,
            "weeks_of_data": round(weeks, 1),
            "narrative": gap_narrative,
        }

    return {
        "em_distribution": em_distribution,
        "em_benchmark": em_benchmark,
        "em_total": em_total,
        "em_alerts": em_alerts,
        "revenue_gap": revenue_gap,
        "code_count": len(set(codes_flat)),
        "line_count": len(line_items),
    }


# ---------------------------------------------------------------------------
# POST /analyze-coding
# ---------------------------------------------------------------------------

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

    # --- Capability 2: Revenue Gap Estimator ---
    revenue_gap = None
    has_undercoding = any(a["type"] == "UNDERCODING" for a in em_alerts)
    if has_undercoding and em_total > 0:
        # Use Internal Medicine Medicare rates as fallback
        em_medicare_rates = {
            "99211": 27.0, "99212": 59.0, "99213": 95.0,
            "99214": 135.0, "99215": 190.0,
        }

        gap_lines = []
        total_gap = 0.0
        for code in em_established:
            current_pct = em_distribution.get(code, 0)
            bench_pct = em_benchmark.get(code, 0)
            if bench_pct > current_pct:
                visit_gap = round((bench_pct - current_pct) / 100 * em_total, 1)
                rate = em_medicare_rates.get(code, 0)
                gap_value = round(visit_gap * rate, 2)
                total_gap += gap_value
                gap_lines.append({
                    "code": code,
                    "current_pct": current_pct,
                    "benchmark_pct": bench_pct,
                    "visit_gap": visit_gap,
                    "rate": rate,
                    "revenue_gap": gap_value,
                })

        # Annualize: estimate weeks from date_range or default to 4 weeks
        weeks = 4
        if req.date_range:
            # Try to parse "YYYY-MM-DD to YYYY-MM-DD"
            try:
                parts = req.date_range.split(" to ")
                if len(parts) == 2:
                    from datetime import datetime
                    d1 = datetime.strptime(parts[0].strip(), "%Y-%m-%d")
                    d2 = datetime.strptime(parts[1].strip(), "%Y-%m-%d")
                    weeks = max((d2 - d1).days / 7, 1)
            except Exception:
                pass

        annualized_gap = round(total_gap * (52 / max(weeks, 1)), 2)

        # AI narrative for the gap
        gap_narrative = None
        if total_gap > 0:
            try:
                gap_data = _call_claude(
                    system_prompt=(
                        "You are a medical billing analyst. Given an E&M coding gap "
                        "analysis for a physician practice, write 2-3 sentences explaining "
                        "the estimated revenue gap in plain language. Be specific about "
                        "the dollar amount and the codes driving the gap. Include one "
                        "sentence noting that the estimate assumes documentation supports "
                        "higher complexity billing. Be direct and factual, not alarming. "
                        "Return ONLY valid JSON with a single key \"narrative\"."
                    ),
                    user_content=json.dumps({
                        "specialty": specialty_key,
                        "total_gap_period": total_gap,
                        "annualized_gap": annualized_gap,
                        "weeks_of_data": round(weeks, 1),
                        "gap_by_code": gap_lines,
                        "em_total": em_total,
                    }),
                    max_tokens=512,
                )
                if gap_data and "narrative" in gap_data:
                    gap_narrative = gap_data["narrative"]
            except Exception as exc:
                print(f"[Provider AI] Revenue gap narrative failed: {exc}")

        revenue_gap = {
            "gap_lines": gap_lines,
            "total_gap_period": round(total_gap, 2),
            "annualized_gap": annualized_gap,
            "weeks_of_data": round(weeks, 1),
            "narrative": gap_narrative,
        }

    return {
        "em_distribution": em_distribution,
        "em_benchmark": em_benchmark,
        "em_total": em_total,
        "em_alerts": em_alerts,
        "revenue_gap": revenue_gap,
        "code_count": len(set(codes_flat)),
        "line_count": len(req.lines),
    }


# ---------------------------------------------------------------------------
# POST /parse-837 — parse 837 EDI or CSV claim files for coding analysis
# ---------------------------------------------------------------------------

@router.post("/parse-837")
async def parse_837(file: UploadFile = File(...)):
    """Parse an 837 claim file (EDI) or CSV/tabular export to extract CPT codes.

    Tries deterministic EDI parsing first (SV1 segments).
    Falls back to AI extraction for non-EDI formats.
    """
    content = await file.read()
    text = content.decode("utf-8", errors="replace")

    # Try deterministic 837 EDI parsing
    lines = []
    service_dates = []
    has_isa = "ISA" in text[:200]
    segments = text.replace("\r\n", "\n").replace("\r", "~").replace("\n", "~").split("~")

    if has_isa:
        current_date = ""
        for seg in segments:
            seg = seg.strip()
            # DTP*472 = service date
            if seg.startswith("DTP*472*"):
                parts = seg.split("*")
                if len(parts) >= 4:
                    raw = parts[3]
                    if len(raw) == 8:
                        current_date = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
                        service_dates.append(current_date)
                    elif "-" in raw and len(raw) == 17:
                        # Date range: CCYYMMDD-CCYYMMDD
                        start = raw[:8]
                        current_date = f"{start[:4]}-{start[4:6]}-{start[6:8]}"
                        service_dates.append(current_date)

            # SV1 = professional service line
            if seg.startswith("SV1*"):
                parts = seg.split("*")
                # SV1*HC:CPT:MOD*charge*UN*units
                svc_id = parts[1] if len(parts) > 1 else ""
                charge = parts[2] if len(parts) > 2 else "0"
                units = parts[4] if len(parts) > 4 else "1"

                cpt = ""
                if ":" in svc_id:
                    cpt = svc_id.split(":")[1]
                elif svc_id.isdigit() and len(svc_id) == 5:
                    cpt = svc_id

                if cpt:
                    lines.append({
                        "cpt_code": cpt,
                        "units": int(float(units)) if units else 1,
                        "billed_amount": float(charge) if charge else 0.0,
                        "service_date": current_date,
                    })

    if lines:
        # Compute date range
        date_range = ""
        if service_dates:
            sorted_d = sorted(set(service_dates))
            date_range = f"{sorted_d[0]} to {sorted_d[-1]}" if len(sorted_d) > 1 else sorted_d[0]

        return {
            "lines": lines,
            "line_count": len(lines),
            "date_range": date_range,
            "source": "edi",
        }

    # Fallback: AI extraction for CSV/tabular formats
    try:
        # Take first 8000 chars to keep within context
        sample = text[:8000]
        result = _call_claude(
            system_prompt=(
                "You are a medical billing data parser. The user has uploaded a file "
                "that contains claim/billing data (CSV, Excel export, or other tabular "
                "format). Extract CPT codes, units, billed amounts, and service dates "
                "from whatever column structure is present. Return ONLY valid JSON: "
                '{"lines": [{"cpt_code": "99213", "units": 1, "billed_amount": 95.00, '
                '"service_date": "2025-01-15"}], "date_range": "2025-01-01 to 2025-01-31"}'
                "\nIf you cannot find CPT codes, return {\"lines\": [], \"date_range\": \"\"}."
            ),
            user_content=f"Parse this billing data file:\n\n{sample}",
            max_tokens=4096,
        )
        if result and result.get("lines"):
            return {
                "lines": result["lines"],
                "line_count": len(result["lines"]),
                "date_range": result.get("date_range", ""),
                "source": "ai",
            }
    except Exception as exc:
        print(f"[Provider] AI 837 parse failed: {exc}")

    raise HTTPException(status_code=400, detail="Could not parse file. No CPT codes found.")


# ---------------------------------------------------------------------------
# POST /analyze-denials  (Capability 1 — AI-powered)
# ---------------------------------------------------------------------------

@router.post("/analyze-denials")
async def analyze_denials(req: AnalyzeDenialsRequest):
    """AI-powered denial interpretation with appeal letter templates."""

    if not req.denied_lines:
        return {"denial_types": [], "pattern_summary": "", "total_recoverable_value": 0}

    # Build input for Claude
    lines_data = []
    for line in req.denied_lines:
        lines_data.append({
            "cpt_code": line.cpt_code,
            "billed_amount": line.billed_amount,
            "adjustment_codes": line.adjustment_codes,
            "claim_id": line.claim_id,
        })

    user_content = json.dumps({
        "payer_name": req.payer_name,
        "denied_lines": lines_data,
        "total_denied_count": len(lines_data),
    })

    result = _call_claude(
        system_prompt=DENIAL_SYSTEM_PROMPT,
        user_content=user_content,
        max_tokens=4096,
    )

    if result is None:
        return {
            "denial_types": [],
            "pattern_summary": "AI analysis is temporarily unavailable. Please try again.",
            "total_recoverable_value": 0,
            "error": True,
        }

    # Enrich result with Signal playbook evidence (batch lookup)
    try:
        sb = _get_supabase()
        cpt_codes = list({line.cpt_code for line in req.denied_lines if line.cpt_code})
        denial_codes = []
        for line in req.denied_lines:
            if line.adjustment_codes:
                denial_codes.extend(line.adjustment_codes)
        denial_codes = list(set(denial_codes))

        if cpt_codes and denial_codes:
            playbook_res = sb.table("signal_denial_playbook").select("*").in_("cpt_code", cpt_codes).in_("denial_code", denial_codes).execute()
            playbook_rows = {(r["denial_code"], r["cpt_code"]): r for r in (playbook_res.data or [])}

            if playbook_rows and result and "denial_types" in result:
                for denial_type in result["denial_types"]:
                    code = denial_type.get("adjustment_code", "")
                    affected = denial_type.get("affected_cpts", [])
                    for cpt in affected:
                        key = (code, cpt)
                        if key in playbook_rows:
                            pb = playbook_rows[key]
                            denial_type["signal_evidence"] = {
                                "appeal_strength": pb["appeal_strength"],
                                "payer_analytical_path": pb["payer_analytical_path"],
                                "challenging_evidence_summary": pb["challenging_evidence_summary"],
                                "recommended_claims": pb["recommended_claims"],
                                "topic_slug": pb["signal_topic_slug"],
                            }
                            break
    except Exception as e:
        print(f"[warn] Signal playbook lookup failed: {e}")

    # Aggregate denial patterns in background (silent)
    import asyncio
    try:
        lines_data_for_patterns = [
            {"cpt_code": line.cpt_code, "adjustment_codes": line.adjustment_codes, "billed_amount": line.billed_amount}
            for line in req.denied_lines
        ]
        asyncio.create_task(aggregate_denial_patterns(lines_data_for_patterns, req.payer_name or "Unknown"))
    except Exception:
        pass

    return result



# ---------------------------------------------------------------------------
# POST /audit-report  (PDF generation with ReportLab)
# ---------------------------------------------------------------------------

@router.post("/audit-report")
async def generate_audit_report(req: AuditReportRequest):
    """Generate a branded Parity Audit PDF report."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        PageBreak, HRFlowable,
    )
    from datetime import datetime

    # Resolve data source
    data = None
    if req.analysis_data:
        data = req.analysis_data
    elif req.audit_id:
        try:
            sb = _get_supabase()
            row = sb.table("provider_audits").select("*").eq("id", req.audit_id).single().execute()
            if row.data:
                audit = row.data
                # Fetch actual analysis results from provider_analyses
                analysis_ids = audit.get("analysis_ids", [])
                payer_results = []
                for aid in analysis_ids:
                    try:
                        arow = sb.table("provider_analyses").select("*").eq("id", aid).execute()
                        if arow.data:
                            rec = arow.data[0]
                            rj = rec.get("result_json", {})
                            payer_results.append({
                                "payer_name": rec.get("payer_name", ""),
                                "summary": rj.get("summary", {}),
                                "line_items": rj.get("line_items", []),
                                "scorecard": rj.get("scorecard", {}),
                                "denial_intel": rj.get("denial_intel"),
                                "denial_benchmarks": rj.get("denial_benchmarks", []),
                            })
                    except Exception:
                        pass

                data = {
                    "practice_name": audit.get("practice_name", ""),
                    "report_date": datetime.now().strftime("%B %d, %Y"),
                    "date_range": audit.get("date_range", ""),
                    "payer_results": payer_results,
                }
        except Exception as exc:
            print(f"[AuditReport] Failed to fetch audit: {exc}")

    if not data:
        raise HTTPException(status_code=400, detail="No audit data provided or found")

    practice_name = data.get("practice_name", "Practice")
    report_date = data.get("report_date", datetime.now().strftime("%B %d, %Y"))
    date_range = data.get("date_range", "")
    payer_results = data.get("payer_results", [])

    # --- AI-generated narrative sections ---
    # Enrich summary input with per-payer detail for tone calibration
    total_underpayment_all = sum(
        pr.get("summary", {}).get("total_underpayment", 0) for pr in payer_results
    )
    total_lines_all = sum(
        pr.get("summary", {}).get("line_count", 0) for pr in payer_results
    )
    total_underpaid_lines = sum(
        pr.get("summary", {}).get("underpaid_count", 0) for pr in payer_results
    )
    total_overpaid_lines = sum(
        pr.get("summary", {}).get("overpaid_count", 0) for pr in payer_results
    )
    total_denied_lines = sum(
        pr.get("summary", {}).get("denied_count", 0) for pr in payer_results
    )

    # Determine severity level for tone calibration
    underpaid_pct = (total_underpaid_lines / total_lines_all * 100) if total_lines_all > 0 else 0
    if total_underpayment_all > 1000 or underpaid_pct > 25:
        severity = "high"
    elif total_underpayment_all > 500 or underpaid_pct > 10:
        severity = "moderate"
    else:
        severity = "low"

    summary_input = json.dumps({
        "practice_name": practice_name,
        "date_range": date_range,
        "payer_count": len(payer_results),
        "severity": severity,
        "totals": {
            "total_lines": total_lines_all,
            "total_underpayment": round(total_underpayment_all, 2),
            "underpaid_lines": total_underpaid_lines,
            "overpaid_lines": total_overpaid_lines,
            "denied_lines": total_denied_lines,
        },
        "payers": [
            {
                "name": pr.get("payer_name", ""),
                "total_underpayment": pr.get("summary", {}).get("total_underpayment", 0),
                "denied_count": pr.get("summary", {}).get("denied_count", 0),
                "underpaid_count": pr.get("summary", {}).get("underpaid_count", 0),
                "overpaid_count": pr.get("summary", {}).get("overpaid_count", 0),
                "correct_count": pr.get("summary", {}).get("correct_count", 0),
                "adherence_rate": pr.get("summary", {}).get("adherence_rate", 0),
                "line_count": pr.get("summary", {}).get("line_count", 0),
                "scorecard": pr.get("scorecard", {}),
            }
            for pr in payer_results
        ],
    })

    exec_summary = _call_claude_text(
        system_prompt=(
            "You are a healthcare revenue cycle analyst writing an executive summary "
            "for a payer contract audit report. Write 3-4 sentences summarizing the "
            "key findings. Be specific about dollar amounts and percentages. "
            "Use a professional, factual tone. Do not use markdown formatting.\n\n"
            "CRITICAL TONE CALIBRATION based on the 'severity' field:\n"
            "- severity='low' (underpayment <$500, <10% of lines): Use measured, reassuring "
            "language. Frame overpayments positively (e.g., 'Payer is paying above contracted "
            "rates on X of Y lines, which is favorable to the practice'). Describe underpayments "
            "as 'minor' or 'isolated'. Do NOT use alarming language like 'systemic issues' or "
            "'significant revenue leakage'.\n"
            "- severity='moderate' ($500-$1000 or 10-25% of lines): Use balanced, factual language. "
            "Note both positive and concerning findings.\n"
            "- severity='high' (>$1000 or >25% of lines): Use direct, urgent language highlighting "
            "the financial impact and need for immediate action."
        ),
        user_content=summary_input,
        max_tokens=512,
    ) or "Executive summary generation unavailable. See detailed findings below."

    recommended_actions = _call_claude_text(
        system_prompt=(
            "You are a healthcare revenue cycle consultant. Given audit findings, "
            "write 4-6 prioritized recommended actions. Number each one. Be specific "
            "and actionable. Each action should be 1-2 sentences. Do not use markdown.\n\n"
            "Match urgency to the 'severity' field:\n"
            "- severity='low': Focus on monitoring and maintaining current performance. "
            "Lead with positive findings before addressing minor issues.\n"
            "- severity='moderate': Balance corrective actions with maintenance items.\n"
            "- severity='high': Lead with urgent corrective actions."
        ),
        user_content=summary_input,
        max_tokens=1024,
    ) or "1. Review underpaid claims and file payer disputes.\n2. Address denied claims with appeal letters.\n3. Update chargemaster for codes billed below contract.\n4. Schedule quarterly contract audits."

    billing_assessment = _call_claude_text(
        system_prompt=(
            "You are a healthcare billing consultant assessing a billing contractor's "
            "performance. Given audit metrics, write 2-3 sentences about the billing "
            "contractor's performance based on clean claim rate, denial rate, and "
            "preventable denial patterns. Be constructive and factual. Do not use markdown.\n\n"
            "TONE CALIBRATION based on 'severity' field:\n"
            "- severity='low': Emphasize strong performance. Frame any issues as minor "
            "optimization opportunities rather than problems.\n"
            "- severity='moderate': Acknowledge good areas while noting specific improvements.\n"
            "- severity='high': Be direct about performance gaps while remaining constructive."
        ),
        user_content=summary_input,
        max_tokens=512,
    ) or "Billing contractor assessment requires additional data."

    # --- Build PDF ---
    TEAL = colors.HexColor("#0D9488")
    NAVY = colors.HexColor("#1E293B")
    LIGHT_TEAL = colors.HexColor("#F0FDFA")
    LIGHT_GRAY = colors.HexColor("#F8FAFC")
    RED = colors.HexColor("#DC2626")
    WHITE = colors.white

    styles = getSampleStyleSheet()
    s_title = ParagraphStyle("AuditTitle", parent=styles["Title"], textColor=NAVY, fontSize=24, spaceAfter=6)
    s_subtitle = ParagraphStyle("AuditSubtitle", parent=styles["Normal"], textColor=TEAL, fontSize=14, spaceAfter=20)
    s_heading = ParagraphStyle("AuditH2", parent=styles["Heading2"], textColor=NAVY, fontSize=16, spaceBefore=20, spaceAfter=10)
    s_body = ParagraphStyle("AuditBody", parent=styles["Normal"], fontSize=11, leading=16, textColor=NAVY)
    s_small = ParagraphStyle("AuditSmall", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#64748B"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )

    story = []

    # === 1. Cover Page ===
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("PARITY AUDIT", ParagraphStyle("CoverTitle", parent=s_title, fontSize=36, textColor=TEAL)))
    story.append(Paragraph("Contract Integrity Report", ParagraphStyle("CoverSub", parent=s_subtitle, fontSize=18, textColor=NAVY)))
    story.append(Spacer(1, 0.5 * inch))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL, spaceAfter=20))
    story.append(Paragraph(f"<b>Practice:</b> {practice_name}", s_body))
    if date_range:
        story.append(Paragraph(f"<b>Period:</b> {date_range}", s_body))
    story.append(Paragraph(f"<b>Report Date:</b> {report_date}", s_body))
    story.append(Paragraph(f"<b>Payers Analyzed:</b> {len(payer_results)}", s_body))
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("Prepared by CivicScale Parity Audit", s_small))
    story.append(Paragraph("Benchmark comparisons use publicly available CMS Medicare data.", s_small))
    story.append(PageBreak())

    # === 2. Executive Summary ===
    story.append(Paragraph("Executive Summary", s_heading))
    for line in exec_summary.split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), s_body))
            story.append(Spacer(1, 6))
    story.append(Spacer(1, 12))

    # === 2b. Changes Since Last Month (only when trend_data provided) ===
    td = req.trend_data
    if td and td.get("alerts"):
        story.append(Paragraph("Changes Since Last Month", s_heading))

        # AI narrative in italics
        narrative = td.get("trend_narrative", "")
        if narrative:
            s_italic = ParagraphStyle("AuditItalic", parent=s_body, fontName="Helvetica-Oblique", textColor=colors.HexColor("#475569"))
            story.append(Paragraph(narrative, s_italic))
            story.append(Spacer(1, 10))

        trend_alerts = td.get("alerts", [])
        new_worsening = [a for a in trend_alerts if a.get("severity") == "high"]
        resolved = [a for a in trend_alerts if a.get("severity") == "positive"]

        if new_worsening:
            story.append(Paragraph("New &amp; Worsening Issues", ParagraphStyle(
                "TrendRedH", parent=s_body, fontSize=12, textColor=RED, spaceBefore=8, spaceAfter=4,
            )))
            for a in new_worsening:
                detail = a.get("detail", "")
                impact = a.get("financial_impact")
                impact_str = f" (${impact:,.2f} impact)" if impact else ""
                story.append(Paragraph(f"&#8226; {detail}{impact_str}", s_body))
                story.append(Spacer(1, 3))

        if resolved:
            s_green = ParagraphStyle("TrendGreenH", parent=s_body, fontSize=12, textColor=colors.HexColor("#059669"), spaceBefore=8, spaceAfter=4)
            story.append(Paragraph("Resolved Issues", s_green))
            for a in resolved:
                story.append(Paragraph(f"&#8226; {a.get('detail', '')}", s_body))
                story.append(Spacer(1, 3))

        # Revenue gap trajectory callout
        trajectory = next((a for a in trend_alerts if a.get("type") == "revenue_gap_trajectory"), None)
        if trajectory and trajectory.get("financial_impact"):
            projected = trajectory["financial_impact"]
            traj_style = ParagraphStyle("TrajBox", parent=s_body, textColor=WHITE, fontSize=12, leading=16)
            traj_data = [[Paragraph(f"Projected Annual Revenue Gap: <b>${projected:,.2f}</b>", traj_style)]]
            traj_table = Table(traj_data, colWidths=[6.5 * inch])
            traj_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            story.append(Spacer(1, 10))
            story.append(traj_table)

        story.append(Spacer(1, 16))

    # === 3. Contract Integrity Findings ===
    story.append(Paragraph("Contract Integrity Findings", s_heading))

    for pr in payer_results:
        payer_name = pr.get("payer_name", "Unknown")
        summary = pr.get("summary", {})
        line_items = pr.get("line_items", [])

        story.append(Paragraph(f"<b>{payer_name}</b>", ParagraphStyle("PayerH", parent=s_body, fontSize=13, spaceBefore=14, spaceAfter=6)))

        # Summary row
        summary_data = [
            ["Total Contracted", "Total Paid", "Underpayment", "Adherence Rate"],
            [
                f"${summary.get('total_contracted', 0):,.2f}",
                f"${summary.get('total_paid', 0):,.2f}",
                f"${summary.get('total_underpayment', 0):,.2f}",
                f"{summary.get('adherence_rate', 0)}%",
            ],
        ]
        st = Table(summary_data, colWidths=[1.65 * inch] * 4)
        st.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BACKGROUND", (0, 1), (-1, 1), LIGHT_TEAL),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(st)
        story.append(Spacer(1, 8))

        # Line items table (top 30 to fit)
        if line_items:
            header = ["CPT", "Billed", "Paid", "Expected", "Variance", "Flag"]
            rows_data = [header]
            for li in line_items[:30]:
                variance = li.get("variance")
                var_str = f"${variance:+,.2f}" if variance is not None else "\u2014"
                rows_data.append([
                    li.get("cpt_code", ""),
                    f"${li.get('billed_amount', 0):,.2f}",
                    f"${li.get('paid_amount', 0):,.2f}",
                    f"${li.get('expected_payment', 0):,.2f}" if li.get("expected_payment") is not None else "\u2014",
                    var_str,
                    li.get("flag", ""),
                ])
            lt = Table(rows_data, colWidths=[0.8 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch])
            row_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (-1, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
            # Highlight underpaid/denied rows
            for ri, li in enumerate(line_items[:30], start=1):
                flag = li.get("flag", "")
                if flag == "UNDERPAID":
                    row_styles.append(("BACKGROUND", (0, ri), (-1, ri), colors.HexColor("#FEF2F2")))
                elif flag == "DENIED":
                    row_styles.append(("BACKGROUND", (0, ri), (-1, ri), colors.HexColor("#FFFBEB")))
                elif ri % 2 == 0:
                    row_styles.append(("BACKGROUND", (0, ri), (-1, ri), LIGHT_GRAY))
            lt.setStyle(TableStyle(row_styles))
            story.append(lt)
            if len(line_items) > 30:
                story.append(Paragraph(f"Showing 30 of {len(line_items)} line items", s_small))
            story.append(Spacer(1, 12))

    # === 3b. Denial Rate Benchmarking ===
    all_denial_benchmarks = []
    for pr in payer_results:
        rj = pr.get("result_json") or {}
        db_list = rj.get("denial_benchmarks") or pr.get("denial_benchmarks") or []
        all_denial_benchmarks.extend(db_list)

    if all_denial_benchmarks:
        story.append(Paragraph("Denial Rate Benchmarking", s_heading))
        story.append(Paragraph(
            "Your practice's denial rates compared to published industry averages.",
            s_body,
        ))
        story.append(Spacer(1, 6))

        db_header = ["CPT Code", "Your Rate", "Industry Avg", "Gap", "Claims"]
        db_rows = [db_header]
        for db in all_denial_benchmarks[:10]:
            gap_val = db.get("gap", 0)
            gap_str = f"{gap_val:+.1f}%"
            db_rows.append([
                db.get("cpt_code", ""),
                f"{db.get('practice_denial_rate', 0):.1f}%",
                f"{db.get('industry_avg_rate', 0):.1f}%",
                gap_str,
                str(db.get("total_claims", 0)),
            ])

        db_table = Table(db_rows, colWidths=[1.0 * inch, 1.1 * inch, 1.1 * inch, 0.9 * inch, 0.9 * inch])
        db_styles = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for ri, db in enumerate(all_denial_benchmarks[:10], start=1):
            gap_val = db.get("gap", 0)
            if gap_val > 2:
                db_styles.append(("TEXTCOLOR", (3, ri), (3, ri), colors.HexColor("#DC2626")))
            elif gap_val < -2:
                db_styles.append(("TEXTCOLOR", (3, ri), (3, ri), colors.HexColor("#059669")))
            else:
                db_styles.append(("TEXTCOLOR", (3, ri), (3, ri), colors.HexColor("#6B7280")))
            if ri % 2 == 0:
                db_styles.append(("BACKGROUND", (0, ri), (-1, ri), LIGHT_GRAY))
        db_table.setStyle(TableStyle(db_styles))
        story.append(db_table)
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"<i>{DENIAL_BENCHMARK_DATA_NOTE}</i>",
            ParagraphStyle("BenchNote", parent=s_small, fontSize=7, leading=9),
        ))
        story.append(Spacer(1, 12))

    # === 4. Denial Pattern Analysis ===
    has_denials = any(pr.get("denial_intel") for pr in payer_results)
    if has_denials:
        story.append(Paragraph("Denial Pattern Analysis", s_heading))
        for pr in payer_results:
            intel = pr.get("denial_intel")
            if not intel or not intel.get("denial_types"):
                continue
            story.append(Paragraph(f"<b>{pr.get('payer_name', '')}</b>", s_body))
            for dt in intel["denial_types"][:5]:
                story.append(Paragraph(
                    f"<b>{dt.get('adjustment_code', '')}:</b> {dt.get('plain_language', '')} "
                    f"({dt.get('count', 0)} occurrences, ${dt.get('total_value', 0):,.2f})",
                    s_body,
                ))
            if intel.get("pattern_summary"):
                story.append(Paragraph(f"<i>{intel['pattern_summary']}</i>", s_small))
            story.append(Spacer(1, 10))

    # === 5. Revenue Gap Estimate ===
    story.append(Paragraph("Revenue Gap Estimate", s_heading))
    total_underpayment = sum(
        pr.get("summary", {}).get("total_underpayment", 0) for pr in payer_results
    )
    total_denied_value = sum(
        pr.get("denial_intel", {}).get("total_recoverable_value", 0)
        for pr in payer_results if pr.get("denial_intel")
    )
    monthly = total_underpayment
    annualized = monthly * 12

    gap_data = [
        ["Category", "Identified Amount", "Annualized (\u00d712)"],
        ["Underpayments", f"${total_underpayment:,.2f}", f"${annualized:,.2f}"],
        ["Estimated Denial Recovery", f"${total_denied_value:,.2f}", f"${total_denied_value * 12:,.2f}"],
        ["Total Revenue Gap", f"${total_underpayment + total_denied_value:,.2f}",
         f"${(total_underpayment + total_denied_value) * 12:,.2f}"],
    ]
    gt = Table(gap_data, colWidths=[2.2 * inch, 2.0 * inch, 2.0 * inch])
    gt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("BACKGROUND", (0, -1), (-1, -1), NAVY),
        ("TEXTCOLOR", (0, -1), (-1, -1), WHITE),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(gt)

    # Per-payer breakdown
    if len(payer_results) > 1:
        story.append(Spacer(1, 10))
        story.append(Paragraph("<b>By Payer:</b>", s_body))
        for pr in payer_results:
            s = pr.get("summary", {})
            story.append(Paragraph(
                f"  {pr.get('payer_name', '')}: ${s.get('total_underpayment', 0):,.2f} underpayment, "
                f"{s.get('denied_count', 0)} denied claims",
                s_small,
            ))
    story.append(Spacer(1, 12))

    # === 6. Billing Contractor Assessment ===
    story.append(Paragraph("Billing Contractor Assessment", s_heading))
    for line in billing_assessment.split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), s_body))
            story.append(Spacer(1, 4))

    # Scorecard metrics
    for pr in payer_results:
        sc = pr.get("scorecard", {})
        if sc.get("clean_claim_rate") is not None:
            story.append(Paragraph(f"<b>{pr.get('payer_name', '')}:</b>", s_body))
            story.append(Paragraph(
                f"Clean Claim Rate: {sc.get('clean_claim_rate', 0)}% | "
                f"Denial Rate: {sc.get('denial_rate', 0)}% | "
                f"Preventable Denials: {sc.get('preventable_denial_rate', 0)}%",
                s_small,
            ))
    story.append(Spacer(1, 12))

    # === 7. Recommended Actions ===
    story.append(Paragraph("Recommended Actions", s_heading))
    for line in recommended_actions.split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), s_body))
            story.append(Spacer(1, 4))
    story.append(Spacer(1, 12))

    # === 8. Methodology ===
    story.append(Paragraph("Methodology", s_heading))
    methodology = (
        f"This audit analyzed remittance data for {practice_name} across "
        f"{len(payer_results)} payer(s){f' for the period {date_range}' if date_range else ''}. "
        "Contract rates were compared against actual paid amounts from 835 Electronic Remittance Advice files. "
        "Medicare benchmark rates are sourced from the CMS 2026 Physician Fee Schedule, "
        "geographically adjusted using the CMS carrier/locality crosswalk. "
        "Denial patterns were analyzed using ANSI X12 adjustment reason codes. "
        "All dollar amounts are based on the data provided and should be verified against original payer contracts."
    )
    story.append(Paragraph(methodology, s_body))
    story.append(Spacer(1, 12))

    # === 9. Next Steps ===
    story.append(Paragraph("Next Steps", s_heading))
    next_steps = (
        "This report represents a point-in-time audit of your payer contracts. "
        "For ongoing revenue protection, we recommend quarterly audits as new remittance data becomes available. "
        "CivicScale Parity Audit can automate this process with monthly monitoring, "
        "real-time underpayment alerts, and automated appeal letter generation. "
        "Contact your Parity representative or visit civicscale.ai/provider to learn more."
    )
    story.append(Paragraph(next_steps, s_body))
    story.append(Spacer(1, 24))

    # Footer
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceBefore=20, spaceAfter=10))
    story.append(Paragraph(
        "Parity Audit by CivicScale. Benchmark comparisons use publicly available CMS Medicare data. "
        "This report is not legal or financial advice. Verify all findings with your payer contracts "
        "and consult a billing specialist before taking action.",
        s_small,
    ))

    doc.build(story)
    buf.seek(0)

    filename = f"Parity_Audit_{practice_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# ---------------------------------------------------------------------------
# POST /submit-audit  (Submit audit + send emails)
# ---------------------------------------------------------------------------

@router.post("/submit-audit")
async def submit_audit(req: SubmitAuditRequest):
    """Submit a new Parity Audit request and send confirmation emails."""
    if not req.consent:
        raise HTTPException(status_code=400, detail="Consent is required to submit an audit")

    if not req.contact_email or "@" not in req.contact_email:
        raise HTTPException(status_code=400, detail="Valid contact email required")

    if not req.practice_name.strip():
        raise HTTPException(status_code=400, detail="Practice name required")

    # Save to Supabase
    audit_id = None
    try:
        sb = _get_supabase()
        row = sb.table("provider_audits").insert({
            "company_id": req.user_id if req.user_id else None,
            "practice_name": req.practice_name.strip(),
            "practice_specialty": req.specialty,
            "num_providers": req.num_providers,
            "billing_company": req.billing_company,
            "contact_email": req.contact_email.strip(),
            "payer_list": req.payer_list,
            "remittance_data": req.remittance_data,
            "status": "submitted",
        }).execute()

        if row.data and len(row.data) > 0:
            audit_id = row.data[0].get("id")
    except Exception as exc:
        print(f"[SubmitAudit] Failed to save to Supabase: {exc}")
        # Continue — email is more important than DB save

    # Send confirmation emails
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[SubmitAudit] RESEND_API_KEY not configured, skipping emails")
        else:
            resend.api_key = resend_key

            payer_names = ", ".join(
                p.get("payer_name", "Unknown") for p in req.payer_list
            ) or "None specified"

            # Email to practice
            practice_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: #0D9488; padding: 24px; text-align: center;">
                    <h1 style="color: #fff; margin: 0; font-size: 24px;">Parity Audit</h1>
                    <p style="color: #CCFBF1; margin: 4px 0 0; font-size: 14px;">by CivicScale</p>
                </div>
                <div style="padding: 32px 24px;">
                    <h2 style="color: #1E293B; margin-top: 0;">Your audit has been submitted</h2>
                    <p style="color: #475569;">Thank you for submitting your Parity Audit for <strong>{req.practice_name}</strong>.</p>
                    <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 16px; margin: 20px 0;">
                        <p style="margin: 0 0 8px; color: #1E293B;"><strong>Audit Details:</strong></p>
                        <p style="margin: 4px 0; color: #475569; font-size: 14px;">Payers: {payer_names}</p>
                        {f'<p style="margin: 4px 0; color: #475569; font-size: 14px;">Audit ID: {audit_id}</p>' if audit_id else ''}
                    </div>
                    <p style="color: #475569;"><strong>What happens next:</strong></p>
                    <ul style="color: #475569; font-size: 14px;">
                        <li>Our team will review your submitted data within 1-2 business days</li>
                        <li>We'll run a full contract integrity analysis across all payers</li>
                        <li>You'll receive your complete audit report within 5-7 business days</li>
                    </ul>
                    <p style="color: #475569; font-size: 14px;">
                        Questions? Reply to this email or contact us at support@civicscale.ai.
                    </p>
                </div>
                <div style="background: #F8FAFC; padding: 16px 24px; text-align: center; border-top: 1px solid #E2E8F0;">
                    <p style="color: #94A3B8; font-size: 12px; margin: 0;">
                        Parity Audit by CivicScale &middot; civicscale.ai
                    </p>
                </div>
            </div>
            """
            resend.Emails.send({
                "from": "Parity Provider <notifications@civicscale.ai>",
                "to": [req.contact_email.strip()],
                "subject": f"Your Parity Audit has been submitted — {req.practice_name}",
                "html": practice_html,
            })
            print(f"[SubmitAudit] Confirmation email sent to {req.contact_email}")

            # Email to admin
            admin_html = f"""
            <h2>New Parity Audit Submitted</h2>
            <p><strong>Practice:</strong> {req.practice_name}</p>
            <p><strong>Specialty:</strong> {req.specialty or 'Not specified'}</p>
            <p><strong>Providers:</strong> {req.num_providers}</p>
            <p><strong>Billing Company:</strong> {req.billing_company or 'Not specified'}</p>
            <p><strong>Contact:</strong> {req.contact_email} {f'/ {req.contact_phone}' if req.contact_phone else ''}</p>
            <p><strong>Payers:</strong> {payer_names}</p>
            {f'<p><strong>Audit ID:</strong> {audit_id}</p>' if audit_id else ''}
            <hr>
            <p style="color:#666;font-size:12px;">Parity Audit by CivicScale</p>
            """
            resend.Emails.send({
                "from": "Parity Provider <notifications@civicscale.ai>",
                "to": ["fred@civicscale.ai"],
                "subject": f"New Parity Audit: {req.practice_name}",
                "html": admin_html,
            })
            print(f"[SubmitAudit] Admin notification sent")

    except Exception as exc:
        print(f"[SubmitAudit] Failed to send emails: {exc}")

    return {
        "audit_id": audit_id or "pending",
        "status": "submitted",
        "message": f"Audit submitted for {req.practice_name}. Confirmation sent to {req.contact_email}.",
    }


# ---------------------------------------------------------------------------
# User Account — My Audits (authenticated, no admin required)
# ---------------------------------------------------------------------------

@router.get("/my-audits")
async def my_audits(request: Request):
    """Return audits belonging to the authenticated user (by email)."""
    user = _get_authenticated_user(request)
    email = user.email
    if not email:
        raise HTTPException(status_code=400, detail="No email on account")

    sb = _get_supabase()
    result = sb.table("provider_audits") \
        .select("id, practice_name, status, created_at, report_token, analysis_ids") \
        .eq("contact_email", email) \
        .eq("archived", False) \
        .order("created_at", desc=True) \
        .execute()

    # Compute total underpayment for delivered audits (for monitoring CTA)
    audits_out = []
    for audit in (result.data or []):
        a = {**audit}
        if audit.get("status") == "delivered" and audit.get("analysis_ids"):
            total = 0
            for aid in audit["analysis_ids"][:10]:
                try:
                    row = sb.table("provider_analyses").select("result_json").eq("id", aid).execute()
                    if row.data:
                        total += row.data[0].get("result_json", {}).get("summary", {}).get("total_underpayment", 0)
                except Exception:
                    pass
            a["total_underpayment"] = total
        a.pop("analysis_ids", None)
        audits_out.append(a)

    return {"audits": audits_out}


# ---------------------------------------------------------------------------
# User Account — Profile (unified auth)
# ---------------------------------------------------------------------------

@router.get("/my-profile")
async def my_profile(request: Request):
    """Return provider profile for the authenticated user's company."""
    user = _get_authenticated_user(request)
    sb = _get_supabase()

    result = sb.table("provider_profiles") \
        .select("*") \
        .eq("company_id", str(user.id)) \
        .execute()

    profile = result.data[0] if result.data else None
    return {"profile": profile}


class SaveProfileRequest(BaseModel):
    practice_name: str
    specialty: str = ""
    npi: str = ""
    zip_code: str = ""
    practice_address: str = ""
    billing_contact: str = ""


@router.post("/save-profile")
async def save_profile(body: SaveProfileRequest, request: Request):
    """Create or update provider profile."""
    user = _get_authenticated_user(request)
    sb = _get_supabase()

    # Check if profile already exists
    existing_result = sb.table("provider_profiles") \
        .select("id") \
        .eq("company_id", str(user.id)) \
        .execute()
    existing_profile = existing_result.data[0] if existing_result.data else None

    profile_data = {
        "company_id": str(user.id),
        "practice_name": body.practice_name,
        "specialty": body.specialty or None,
        "npi": body.npi or None,
        "zip_code": body.zip_code or None,
        "practice_address": body.practice_address or None,
        "billing_contact": body.billing_contact or None,
    }

    if existing_profile:
        result = sb.table("provider_profiles") \
            .update(profile_data) \
            .eq("id", existing_profile["id"]) \
            .execute()
    else:
        result = sb.table("provider_profiles") \
            .insert(profile_data) \
            .execute()

    saved = result.data[0] if result.data else None
    if not saved:
        raise HTTPException(status_code=500, detail="Failed to save profile")

    return {"profile": saved}


# ---------------------------------------------------------------------------
# User Account — Analyses (unified auth)
# ---------------------------------------------------------------------------

@router.get("/my-analyses")
async def my_analyses(request: Request, limit: int = 5):
    """Return recent analyses for the authenticated user."""
    user = _get_authenticated_user(request)
    sb = _get_supabase()

    result = sb.table("provider_analyses") \
        .select("id, payer_name, production_date, total_billed, total_paid, underpayment, adherence_rate") \
        .eq("company_id", str(user.id)) \
        .order("production_date", desc=True) \
        .limit(limit) \
        .execute()

    return {"analyses": result.data or []}


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str, request: Request):
    """Return a single analysis by ID."""
    user = _get_authenticated_user(request)
    sb = _get_supabase()

    result = sb.table("provider_analyses") \
        .select("*") \
        .eq("id", analysis_id) \
        .eq("company_id", str(user.id)) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return result.data[0]


# ---------------------------------------------------------------------------
# Public Report Access (token-based, no auth required)
# ---------------------------------------------------------------------------

@router.get("/report/{token}")
async def public_report(token: str):
    """Public report viewer — accessed via signed token link in delivery email."""
    from uuid import UUID

    # Validate token format
    try:
        UUID(token)
    except ValueError:
        raise HTTPException(status_code=404, detail="Report not found")

    sb = _get_supabase()

    # Lookup audit by report_token
    result = sb.table("provider_audits").select("*").eq("report_token", token).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Report not found")

    audit = result.data[0]

    if audit.get("status") != "delivered":
        raise HTTPException(status_code=404, detail="Report not found")

    analysis_ids = audit.get("analysis_ids", [])
    if not analysis_ids:
        raise HTTPException(status_code=404, detail="Report not found")

    # Fetch analysis results (same logic as admin_get_results)
    payer_results = []
    for aid in analysis_ids:
        try:
            row = sb.table("provider_analyses").select("*").eq("id", aid).execute()
            if row.data:
                rec = row.data[0]
                rj = rec.get("result_json", {})
                payer_results.append({
                    "payer_name": rec.get("payer_name", ""),
                    "result": {
                        "summary": rj.get("summary", {}),
                        "scorecard": rj.get("scorecard", {}),
                        "line_items": rj.get("line_items", []),
                        "top_underpaid": rj.get("top_underpaid", []),
                    },
                    "denial_intel": rj.get("denial_intel"),
                    "denial_benchmarks": rj.get("denial_benchmarks", []),
                })
        except Exception as exc:
            print(f"[PublicReport] Failed to fetch analysis {aid}: {exc}")

    return {
        "practice_name": audit.get("practice_name", ""),
        "practice_specialty": audit.get("practice_specialty", ""),
        "payer_results": payer_results,
    }


# ---------------------------------------------------------------------------
# POST /summary-report  (One-page summary PDF)
# GET  /summary-report/{analysis_id}  (convenience wrapper)
# ---------------------------------------------------------------------------

class SummaryReportRequest(BaseModel):
    practice_name: str
    payer_name: str = "Multiple Payers"
    report_date: Optional[str] = None
    date_range: Optional[str] = None
    headline_underpayment: float = 0
    adherence_rate: float = 0
    denial_rate: float = 0
    total_claims_analyzed: int = 0
    top_issues: list = []        # max 3: {title, detail, dollar_impact}
    top_denials: list = []       # max 3: {cpt_code, denial_code, count, recoverable_value}
    priority_actions: list = []  # max 3 strings
    denial_benchmarks: list = []
    coding_gap: float = 0
    data_note: str = ""


def _build_summary_pdf(req: SummaryReportRequest) -> bytes:
    """Build a one-page summary PDF from SummaryReportRequest data."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter as LETTER
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, HRFlowable,
    )
    from datetime import datetime

    TEAL = colors.HexColor("#0D9488")
    NAVY = colors.HexColor("#1E293B")
    WHITE = colors.white
    AMBER = colors.HexColor("#D97706")
    SLATE = colors.HexColor("#64748B")
    LIGHT_GRAY = colors.HexColor("#F8FAFC")

    styles = getSampleStyleSheet()
    s_body = ParagraphStyle("SBody", parent=styles["Normal"], fontSize=10, leading=14, textColor=NAVY)
    s_small = ParagraphStyle("SSmall", parent=styles["Normal"], fontSize=8, leading=10, textColor=SLATE)
    s_heading = ParagraphStyle("SHeading", parent=styles["Normal"], fontSize=12, leading=15, textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)

    report_date = req.report_date or datetime.now().strftime("%B %d, %Y")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
    )

    story = []
    page_w = LETTER[0] - 1.2 * inch  # usable width with current margins

    # === HEADER BAR ===
    header_data = [[
        Paragraph("<b>PARITY PROVIDER</b><br/><font size=10>Revenue Recovery Summary</font>", ParagraphStyle("HdrL", fontSize=16, textColor=WHITE, fontName="Helvetica-Bold", leading=20)),
        Paragraph(f"{req.practice_name}<br/><font size=9>{report_date}</font>", ParagraphStyle("HdrR", fontSize=11, textColor=WHITE, alignment=2, leading=14)),
    ]]
    ht = Table(header_data, colWidths=[page_w * 0.55, page_w * 0.45])
    ht.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TEAL),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(ht)
    story.append(Spacer(1, 16))

    # === HERO ROW — three stat boxes ===
    def _stat_box(value_str, label, subtext, bg_color):
        return Paragraph(
            f"<font size=20><b>{value_str}</b></font><br/>"
            f"<font size=9>{label}</font><br/>"
            f"<font size=7 color='#E2E8F0'>{subtext}</font>",
            ParagraphStyle("StatBox", textColor=WHITE, alignment=1, leading=14),
        )

    underpayment_str = f"${req.headline_underpayment:,.0f}"
    adherence_str = f"{req.adherence_rate:.0f}%"

    box1 = _stat_box(underpayment_str, "Underpayments Identified", "in this remittance period", NAVY)
    box2 = _stat_box(adherence_str, "Payer Adherence Rate", "Industry target: 95%+", TEAL)

    if req.coding_gap and req.coding_gap > 0:
        box3_val = f"${req.coding_gap:,.0f}"
        box3_label = "Est. Coding Gap / Year"
        box3_sub = "Based on E&M distribution"
        box3_bg = AMBER
    else:
        box3_val = f"{req.denial_rate:.1f}%"
        box3_label = "Denial Rate"
        box3_sub = f"{req.total_claims_analyzed} claims analyzed"
        box3_bg = colors.HexColor("#7C3AED")

    box3 = _stat_box(box3_val, box3_label, box3_sub, box3_bg)

    hero_data = [[box1, box2, box3]]
    hero_table = Table(hero_data, colWidths=[page_w / 3] * 3)
    hero_styles = [
        ("BACKGROUND", (0, 0), (0, 0), NAVY),
        ("BACKGROUND", (1, 0), (1, 0), TEAL),
        ("BACKGROUND", (2, 0), (2, 0), box3_bg),
        ("TOPPADDING", (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    hero_table.setStyle(TableStyle(hero_styles))
    story.append(hero_table)
    story.append(Spacer(1, 16))

    # === WHAT WE FOUND ===
    if req.top_issues:
        story.append(Paragraph("What We Found", s_heading))
        for i, issue in enumerate(req.top_issues[:3], 1):
            title = issue.get("title", "")
            detail = issue.get("detail", "")
            impact = issue.get("dollar_impact", 0)
            impact_str = f"<font color='#0D9488'><b>${impact:,.0f}</b></font>" if impact > 0 else ""
            story.append(Paragraph(
                f"<b>{i}. {title}</b> {impact_str}<br/>"
                f"<font size=9 color='#64748B'>{detail}</font>",
                s_body,
            ))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    # === DENIAL BENCHMARK TABLE ===
    worse_benchmarks = [db for db in req.denial_benchmarks if db.get("gap", 0) > 2]
    if worse_benchmarks:
        story.append(Paragraph("Your Denial Rates vs. Industry Average", s_heading))
        db_header = ["CPT", "Your Rate", "Industry Avg", "Gap"]
        db_rows = [db_header]
        for db in sorted(worse_benchmarks, key=lambda x: x.get("gap", 0), reverse=True)[:5]:
            db_rows.append([
                db.get("cpt_code", ""),
                f"{db.get('practice_denial_rate', 0):.1f}%",
                f"{db.get('industry_avg_rate', 0):.1f}%",
                f"{db.get('gap', 0):+.1f}%",
            ])
        dbt = Table(db_rows, colWidths=[page_w * 0.2, page_w * 0.27, page_w * 0.27, page_w * 0.2])
        db_styles_list = [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        for ri in range(1, len(db_rows)):
            db_styles_list.append(("TEXTCOLOR", (3, ri), (3, ri), colors.HexColor("#DC2626")))
            if ri % 2 == 0:
                db_styles_list.append(("BACKGROUND", (0, ri), (-1, ri), LIGHT_GRAY))
        dbt.setStyle(TableStyle(db_styles_list))
        story.append(dbt)
        if req.data_note:
            story.append(Paragraph(f"<i>Source: {req.data_note}</i>", ParagraphStyle("DBNote", parent=s_small, fontSize=7)))
        story.append(Spacer(1, 12))

    # === RECOMMENDED ACTIONS ===
    if req.priority_actions:
        story.append(Paragraph("Recommended Actions", s_heading))
        for i, action in enumerate(req.priority_actions[:3], 1):
            story.append(Paragraph(f"<b>{i}.</b> {action}", s_body))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 12))

    # === FOOTER ===
    story.append(HRFlowable(width="100%", thickness=1, color=TEAL, spaceAfter=8, spaceBefore=16))
    story.append(Paragraph(
        "Prepared by Parity Provider &middot; CivicScale &middot; civicscale.ai",
        ParagraphStyle("Footer1", parent=s_small, alignment=1),
    ))
    story.append(Paragraph(
        "Benchmark comparisons use CMS Medicare Physician Fee Schedule data. "
        "This report does not constitute legal or financial advice.",
        ParagraphStyle("Footer2", parent=s_small, alignment=1, fontSize=7),
    ))

    doc.build(story)
    return buf.getvalue()


@router.post("/summary-report")
async def summary_report(req: SummaryReportRequest, request: Request):
    """Generate a one-page summary PDF for practice owner handout."""
    _get_authenticated_user(request)

    pdf_bytes = _build_summary_pdf(req)

    from datetime import datetime
    safe_name = req.practice_name.replace(" ", "_").replace("/", "_")[:30]
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"Parity_Summary_{safe_name}_{date_str}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/summary-report/{analysis_id}")
async def summary_report_from_analysis(analysis_id: str, request: Request):
    """Convenience wrapper: build summary PDF from a stored analysis."""
    user = _get_authenticated_user(request)

    sb = _get_supabase()
    row = sb.table("provider_analyses").select("*").eq("id", analysis_id).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    rec = row.data[0]
    rj = rec.get("result_json", {})
    summary = rj.get("summary", {})
    scorecard = rj.get("scorecard", {})
    denial_benchmarks = rj.get("denial_benchmarks", [])
    top_underpaid = rj.get("top_underpaid", [])

    # Build top issues from top_underpaid
    top_issues = []
    for tu in top_underpaid[:3]:
        top_issues.append({
            "title": f"CPT {tu.get('cpt_code', '')} Underpayment",
            "detail": f"Systematic underpayment detected for this procedure code.",
            "dollar_impact": tu.get("total_underpayment", 0),
        })

    # Build priority actions
    priority_actions = []
    if summary.get("total_underpayment", 0) > 0:
        priority_actions.append(f"File appeals for ${summary['total_underpayment']:,.0f} in identified underpayments.")
    if summary.get("denied_count", 0) > 0:
        priority_actions.append(f"Review {summary['denied_count']} denied claims for appeal eligibility.")
    if scorecard.get("denial_rate", 0) > 10:
        priority_actions.append("Investigate root causes of above-average denial rates — consider coding audit.")
    if not priority_actions:
        priority_actions.append("Continue monitoring payer adherence to contracted rates.")

    # Look up practice name from profile
    practice_name = rec.get("payer_name", "Practice")
    try:
        prof = sb.table("provider_profiles").select("practice_name").eq("company_id", rec.get("company_id")).execute()
        if prof.data and prof.data[0].get("practice_name"):
            practice_name = prof.data[0]["practice_name"]
    except Exception:
        pass

    summary_req = SummaryReportRequest(
        practice_name=practice_name,
        payer_name=rec.get("payer_name", ""),
        headline_underpayment=summary.get("total_underpayment", 0),
        adherence_rate=summary.get("adherence_rate", 0),
        denial_rate=scorecard.get("denial_rate", 0),
        total_claims_analyzed=summary.get("line_count", 0),
        top_issues=top_issues,
        priority_actions=priority_actions,
        denial_benchmarks=denial_benchmarks,
        data_note=DENIAL_BENCHMARK_DATA_NOTE if denial_benchmarks else "",
    )

    pdf_bytes = _build_summary_pdf(summary_req)

    from datetime import datetime
    safe_name = practice_name.replace(" ", "_").replace("/", "_")[:30]
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"Parity_Summary_{safe_name}_{date_str}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Admin Audit Endpoints (protected by ADMIN_USER_ID / CRON_SECRET)
# ---------------------------------------------------------------------------

@router.get("/admin/audits")
async def admin_list_audits(request: Request, status: Optional[str] = None, archived: Optional[str] = None):
    """List all audits (admin only). Use archived=true to show archived, archived=false (default) to hide them."""
    await _verify_admin(request)

    sb = _get_supabase()
    query = sb.table("provider_audits").select("*").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    if archived == "true":
        query = query.eq("archived", True)
    elif archived != "all":
        # Default: hide archived
        query = query.eq("archived", False)

    result = query.execute()
    return {"audits": result.data or []}


@router.post("/admin/audits/archive")
async def admin_archive_audit(body: AdminArchiveBody, request: Request):
    """Archive or unarchive an audit (admin only)."""
    await _verify_admin(request)
    sb = _get_supabase()
    sb.table("provider_audits").update({"archived": body.archived}).eq("id", body.audit_id).execute()
    return {"status": "ok", "archived": body.archived}


@router.post("/admin/audits/delete")
async def admin_delete_audit(body: AdminDeleteBody, request: Request):
    """Permanently delete an audit and associated analyses (admin only)."""
    await _verify_admin(request)
    sb = _get_supabase()

    # Fetch audit to get analysis_ids
    row = sb.table("provider_audits").select("analysis_ids, archived").eq("id", body.audit_id).execute()
    if not row.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = row.data[0]
    if not audit.get("archived"):
        raise HTTPException(status_code=400, detail="Audit must be archived before deletion")

    # Delete associated analyses
    analysis_ids = audit.get("analysis_ids", []) or []
    for aid in analysis_ids:
        try:
            sb.table("provider_analyses").delete().eq("id", aid).execute()
        except Exception:
            pass

    # Delete the audit
    sb.table("provider_audits").delete().eq("id", body.audit_id).execute()
    return {"status": "deleted", "audit_id": body.audit_id}


@router.post("/admin/audits/upload-835")
async def admin_upload_835(
    request: Request,
    audit_id: str = "",
    payer_name: str = "",
    file: UploadFile = File(...),
):
    """Upload an 835 file to backfill remittance_data on an existing audit (admin only)."""
    await _verify_admin(request)
    if not audit_id:
        raise HTTPException(status_code=400, detail="audit_id required")

    sb = _get_supabase()
    audit_row = sb.table("provider_audits").select("*").eq("id", audit_id).execute()
    if not audit_row.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    content = await file.read()
    raw = content.decode("utf-8", errors="replace")
    parsed = parse_835(raw)  # Returns dict with "claims", "payer_name", etc.
    claims_list = parsed.get("claims", [])

    # Auto-detect payer from 835 if not provided
    if not payer_name and parsed.get("payer_name"):
        payer_name = parsed["payer_name"]

    # Build remittance entry
    entry = {
        "filename": file.filename or "uploaded.835",
        "payer_name": payer_name or "",
        "claims": [
            {
                "claim_id": c.get("claim_id", ""),
                "lines": [
                    {
                        "cpt_code": li.get("cpt_code") or li.get("procedure_code", ""),
                        "billed_amount": li.get("billed_amount") or li.get("charge_amount", 0),
                        "paid_amount": li.get("paid_amount", 0),
                        "units": li.get("units", 1),
                        "adjustments": li.get("adjustments") or li.get("adjustment_codes", ""),
                    }
                    for li in c.get("line_items", [])
                ],
            }
            for c in claims_list
        ],
    }

    # Append to existing remittance_data
    existing = audit_row.data[0].get("remittance_data", []) or []
    existing.append(entry)
    sb.table("provider_audits").update({"remittance_data": existing}).eq("id", audit_id).execute()

    total_lines = sum(len(cl.get("lines", [])) for cl in entry["claims"])
    return {
        "status": "ok",
        "filename": entry["filename"],
        "claims_parsed": len(claims_list),
        "total_lines": total_lines,
        "payer_name": payer_name or entry["payer_name"],
    }


@router.post("/admin/audits/run-analysis")
async def admin_run_analysis(body: AdminRunAnalysisBody, request: Request):
    """Run the full analysis pipeline for an audit (admin only).

    Reads stored fee schedules + 835 data from the audit record, runs
    analyze-contract for each payer, runs denial intelligence, stores results
    as provider_analyses records, and links analysis_ids back to the audit.

    If fee_schedule_data is missing but fee_schedule_method is 'medicare-pct',
    auto-regenerates rates using the percentage and zip_code (from body or audit).
    """
    await _verify_admin(request)

    sb = _get_supabase()

    # Fetch audit
    result = sb.table("provider_audits").select("*").eq("id", body.audit_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = result.data[0]
    payer_list = audit.get("payer_list", [])
    remittance_data = audit.get("remittance_data", [])

    if not payer_list:
        raise HTTPException(status_code=400, detail="No payers in this audit")
    if not remittance_data:
        raise HTTPException(
            status_code=400,
            detail="No remittance (835) data on this audit. Upload 835 files first via /admin/audits/upload-835.",
        )

    # Update status to processing
    sb.table("provider_audits").update({"status": "processing"}).eq("id", body.audit_id).execute()

    # Resolve ZIP for Medicare percentage fallback
    fallback_zip = body.zip_code or audit.get("zip_code", "") or ""
    if not fallback_zip:
        # Try user profile
        cid = audit.get("company_id")
        if cid:
            try:
                prof = sb.table("provider_profiles").select("zip_code").eq("company_id", cid).execute()
                if prof.data:
                    fallback_zip = prof.data[0].get("zip_code", "")
            except Exception:
                pass

    # Build payer rates lookup: {payer_name: {cpt: rate}}
    payer_rates = {}
    for p in payer_list:
        payer_name = p.get("payer_name", "")
        rates = p.get("fee_schedule_data", {})
        if rates:
            payer_rates[payer_name] = {str(k): float(v) for k, v in rates.items()}
        elif p.get("fee_schedule_method") == "medicare-pct" and fallback_zip:
            # Auto-regenerate rates from Medicare PFS x percentage
            pct = body.percentage or 120  # default 120% if not specified
            carrier, loc = resolve_locality(fallback_zip)
            if carrier and loc:
                all_rates = get_all_pfs_rates_for_locality(carrier, loc)
                multiplier = pct / 100.0
                regenerated = {}
                for r in all_rates:
                    med_rate = r.get("nonfacility_amount")
                    if med_rate and med_rate > 0:
                        regenerated[str(r["cpt_code"])] = round(float(med_rate) * multiplier, 2)
                if regenerated:
                    payer_rates[payer_name] = regenerated
                    print(f"[RunAnalysis] Auto-regenerated {len(regenerated)} rates for {payer_name} at {pct}% Medicare (ZIP {fallback_zip})")

    # Build remittance lines per payer
    payer_lines = {}  # {payer_name: [RemittanceLine-like dicts]}
    for rem_file in remittance_data:
        assigned_payer = rem_file.get("payer_name", "")
        if not assigned_payer:
            continue

        for claim in rem_file.get("claims", []):
            claim_id = claim.get("claim_id", "")
            # Support both "lines" (wizard-submitted) and "line_items" (raw parse_835 format)
            claim_lines = claim.get("lines") or claim.get("line_items") or []
            for line in claim_lines:
                cpt = line.get("cpt_code", "")
                if not cpt:
                    continue

                # Build adjustment string from list or use string directly
                adj = line.get("adjustments", "")
                if isinstance(adj, list):
                    adj_parts = []
                    for a in adj:
                        if isinstance(a, dict):
                            gc = a.get("group_code", "")
                            rc = a.get("reason_code", "")
                            adj_parts.append(f"{gc}-{rc}" if gc else rc)
                        else:
                            adj_parts.append(str(a))
                    adj = ", ".join(adj_parts)

                payer_lines.setdefault(assigned_payer, []).append({
                    "cpt_code": cpt,
                    "code_type": "CPT",
                    "billed_amount": float(line.get("billed_amount", 0)),
                    "paid_amount": float(line.get("paid_amount", 0)),
                    "units": int(line.get("units", 1)),
                    "adjustments": adj,
                    "claim_id": claim_id,
                })

    # Resolve locality from practice ZIP (for Medicare benchmarks)
    zip_code = audit.get("zip_code", "") or ""
    # Try to find ZIP from user profile
    cid = audit.get("company_id")
    if not zip_code and cid:
        try:
            prof = sb.table("provider_profiles").select("zip_code").eq("company_id", cid).execute()
            if prof.data:
                zip_code = prof.data[0].get("zip_code", "")
        except Exception:
            pass

    carrier, locality = None, None
    if zip_code:
        carrier, locality = resolve_locality(zip_code)

    # Run analysis per payer
    analysis_ids = []
    payer_results = []

    for payer_name, rates in payer_rates.items():
        lines = payer_lines.get(payer_name, [])
        if not lines:
            # Try case-insensitive match
            for rp, rl in payer_lines.items():
                if rp.lower() == payer_name.lower():
                    lines = rl
                    break

        if not lines:
            continue

        result = _run_analysis_for_payer(
            payer_name=payer_name,
            rates=rates,
            lines=lines,
            user_id=audit.get("company_id"),
            carrier=carrier,
            locality=locality,
            sb=sb,
        )

        if result["analysis_id"]:
            analysis_ids.append(result["analysis_id"])

        payer_results.append({
            "payer_name": payer_name,
            "summary": result["summary"],
            "line_count": result["summary"]["line_count"],
            "underpayment": result["summary"]["total_underpayment"],
        })

    # Update audit with analysis_ids and status
    sb.table("provider_audits").update({
        "analysis_ids": analysis_ids,
        "status": "review",
    }).eq("id", body.audit_id).execute()

    return {
        "status": "review",
        "audit_id": body.audit_id,
        "payer_count": len(payer_results),
        "payer_results": payer_results,
        "analysis_ids": analysis_ids,
    }


@router.get("/admin/audits/results")
async def admin_get_results(request: Request, audit_id: str):
    """Fetch analysis results for an audit (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()

    # Fetch audit
    audit_row = sb.table("provider_audits").select("*").eq("id", audit_id).execute()
    if not audit_row.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = audit_row.data[0]
    analysis_ids = audit.get("analysis_ids", [])

    if not analysis_ids:
        return {"audit": audit, "payer_results": [], "has_results": False}

    # Fetch all analyses
    payer_results = []
    for aid in analysis_ids:
        try:
            row = sb.table("provider_analyses").select("*").eq("id", aid).execute()
            if row.data:
                rec = row.data[0]
                rj = rec.get("result_json", {})
                payer_results.append({
                    "payer_name": rec.get("payer_name", ""),
                    "result": {
                        "summary": rj.get("summary", {}),
                        "scorecard": rj.get("scorecard", {}),
                        "line_items": rj.get("line_items", []),
                        "top_underpaid": rj.get("top_underpaid", []),
                    },
                    "denial_intel": rj.get("denial_intel"),
                    "denial_benchmarks": rj.get("denial_benchmarks", []),
                })
        except Exception as exc:
            print(f"[AdminResults] Failed to fetch analysis {aid}: {exc}")

    return {
        "audit": audit,
        "payer_results": payer_results,
        "has_results": len(payer_results) > 0,
    }


@router.post("/admin/audits/notes")
async def admin_add_notes(body: AdminNotesBody, request: Request):
    """Add review notes to an audit (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()
    sb.table("provider_audits").update({
        "admin_notes": body.notes,
    }).eq("id", body.audit_id).execute()

    return {"status": "ok"}


@router.post("/admin/audits/deliver")
async def admin_deliver_report(body: AdminDeliverBody, request: Request):
    """Deliver audit report — updates status + sends delivery email (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()
    from datetime import datetime
    from uuid import uuid4

    # Fetch audit
    result = sb.table("provider_audits").select("*").eq("id", body.audit_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = result.data[0]

    # Generate report token for public access link
    report_token = str(uuid4())

    # Update status
    sb.table("provider_audits").update({
        "status": "delivered",
        "delivered_at": datetime.utcnow().isoformat(),
        "report_token": report_token,
    }).eq("id", body.audit_id).execute()

    # Send delivery email (Email 2)
    _send_delivery_email(audit, admin_notes=audit.get("admin_notes", ""), report_token=report_token)

    return {"status": "delivered", "audit_id": body.audit_id}


@router.post("/admin/audits/follow-up")
async def admin_send_followup(body: AdminFollowUpBody, request: Request):
    """Manually send follow-up email for an audit (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()

    result = sb.table("provider_audits").select("*").eq("id", body.audit_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = result.data[0]

    # Send follow-up email (Email 3)
    _send_followup_email(audit)

    # Mark follow-up sent
    sb.table("provider_audits").update({
        "follow_up_sent": True,
    }).eq("id", body.audit_id).execute()

    return {"status": "follow_up_sent", "audit_id": body.audit_id}


@router.post("/admin/audits/status")
async def admin_update_status(body: AdminStatusBody, request: Request):
    """Update audit status (admin only)."""
    await _verify_admin(request)

    valid_statuses = {"submitted", "processing", "review", "delivered"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    sb = _get_supabase()
    sb.table("provider_audits").update({
        "status": body.status,
    }).eq("id", body.audit_id).execute()

    return {"status": body.status, "audit_id": body.audit_id}


@router.get("/admin/audits/cron-followup")
async def admin_cron_followup(request: Request):
    """Auto-send follow-up emails for audits delivered 3+ days ago (cron endpoint)."""
    await _verify_admin(request)

    from datetime import datetime, timedelta

    sb = _get_supabase()
    cutoff = (datetime.utcnow() - timedelta(days=3)).isoformat()

    # Find delivered audits where follow_up_sent is false and delivered_at < cutoff
    result = sb.table("provider_audits") \
        .select("*") \
        .eq("status", "delivered") \
        .eq("follow_up_sent", False) \
        .lt("delivered_at", cutoff) \
        .execute()

    sent = 0
    for audit in (result.data or []):
        _send_followup_email(audit)
        sb.table("provider_audits").update({
            "follow_up_sent": True,
        }).eq("id", audit["id"]).execute()
        sent += 1

    return {"follow_ups_sent": sent}
