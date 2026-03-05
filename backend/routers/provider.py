"""
Provider dashboard endpoints:
  GET  /api/provider/contract-template       — download contract rates Excel template
  POST /api/provider/save-rates              — save parsed contract rates
  POST /api/provider/parse-835               — parse an uploaded 835 EDI file
  POST /api/provider/parse-835-batch         — parse multiple 835 files (including zip)
  POST /api/provider/extract-fee-schedule-pdf   — extract rates from payer contract PDF (Claude vision)
  POST /api/provider/extract-fee-schedule-text  — extract rates from pasted text (Claude)
  POST /api/provider/extract-fee-schedule-image — extract rates from photo/screenshot (Claude vision)
  POST /api/provider/calculate-medicare-percentage — calculate rates as % of Medicare PFS
  POST /api/provider/analyze-contract        — compare remittance vs contracted rates
  POST /api/provider/analyze-coding          — coding pattern analysis (E&M distribution)
  POST /api/provider/analyze-denials         — AI-powered denial interpretation + appeal letters
  POST /api/provider/audit-report            — generate branded PDF audit report
  POST /api/provider/submit-audit            — submit audit + send confirmation emails

Admin endpoints (ADMIN_USER_ID or CRON_SECRET protected):
  GET  /api/provider/admin/audits            — list all audits (with optional status filter)
  POST /api/provider/admin/audits/run-analysis — run full analysis pipeline for an audit
  GET  /api/provider/admin/audits/results    — fetch analysis results for an audit
  POST /api/provider/admin/audits/notes      — add review notes to an audit
  POST /api/provider/admin/audits/status     — update audit status
  POST /api/provider/admin/audits/deliver    — deliver report + send email to practice
  POST /api/provider/admin/audits/follow-up  — send follow-up email
  GET  /api/provider/admin/audits/cron-followup — auto-send follow-ups 3 days after delivery
  POST /api/provider/admin/audits/convert-subscription — convert delivered audit to subscription
  GET  /api/provider/admin/subscriptions — list all subscriptions
  POST /api/provider/admin/subscriptions/add-month — add monthly analysis to subscription

Subscription endpoints (authenticated user):
  POST /api/provider/subscription/checkout — create Stripe checkout for monitoring subscription
  POST /api/provider/subscription/webhook — Stripe webhook for subscription events
  GET  /api/provider/my-subscription — get user's subscription data

No PHI is stored. Contract rates and analysis results are tied to user_id.
"""

import base64
import io
import json
import os
import re
import time
import zipfile
from collections import Counter
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from supabase import create_client

from routers.benchmark import resolve_locality, lookup_rate, get_all_pfs_rates_for_locality
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


ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")
STRIPE_PRICE_PROVIDER_MONTHLY = os.environ.get("STRIPE_PRICE_PROVIDER_MONTHLY", "")


async def _get_authenticated_user(request: Request):
    """Extract Bearer token and validate via Supabase auth."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ", 1)[1]
    sb = _get_supabase()

    try:
        user_response = sb.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Auth failed: {exc}")


async def _verify_admin(request: Request):
    """Verify request comes from admin (CRON_SECRET header or admin Bearer token)."""
    # Option 1: CRON_SECRET header (for server-to-server / cron jobs)
    cron_secret = os.environ.get("CRON_SECRET")
    if cron_secret and request.headers.get("X-Cron-Secret") == cron_secret:
        return

    # Option 2: Bearer token from ADMIN_USER_ID (for frontend admin dashboard)
    if ADMIN_USER_ID:
        try:
            user = await _get_authenticated_user(request)
            if str(user.id) == ADMIN_USER_ID:
                return
        except Exception:
            pass

    raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# Anthropic Claude client (lazy singleton)
# ---------------------------------------------------------------------------

_anthropic_client = None


def _get_claude():
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="AI analysis is not configured on this server.",
            )
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise HTTPException(
                status_code=503,
                detail="AI dependencies are not installed.",
            )
    return _anthropic_client


def _call_claude(system_prompt: str, user_content, max_tokens: int = 4096) -> dict:
    """Call Claude API with retry on 529, return parsed JSON.

    user_content can be a string or a list of content blocks (for multimodal).
    """
    client = _get_claude()
    backoff_delays = [2, 5, 10]
    response = None

    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[Provider AI] Claude overloaded (529), retry {attempt + 1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"[Provider AI] API error: {exc}")
            if "529" in err_str:
                return None  # Non-fatal — caller handles gracefully
            return None

    if response is None:
        return None

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[Provider AI] Invalid JSON: {raw_text[:500]}")
        return None


def _call_claude_text(system_prompt: str, user_content, max_tokens: int = 4096) -> str | None:
    """Call Claude API and return raw text (not JSON). Used for narrative sections."""
    client = _get_claude()
    backoff_delays = [2, 5, 10]
    response = None

    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                delay = backoff_delays[attempt]
                print(f"[Provider AI] Claude overloaded (529), retry {attempt + 1}/{len(backoff_delays)} in {delay}s...")
                time.sleep(delay)
                continue
            print(f"[Provider AI] API error: {exc}")
            return None

    if response is None:
        return None

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    return raw_text.strip()


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
    date_range: Optional[str] = ""
    lines: List[CodingLine]


class DenialLine(BaseModel):
    cpt_code: str
    billed_amount: float = 0.0
    adjustment_codes: str = ""
    claim_id: str = ""


class AnalyzeDenialsRequest(BaseModel):
    payer_name: str
    denied_lines: List[DenialLine]


class ExtractFeeScheduleTextRequest(BaseModel):
    text: str


class CalculateMedicarePercentageRequest(BaseModel):
    payer_name: str
    percentage: float  # e.g., 115 for 115%
    zip_code: str
    effective_date: str = ""


class AuditReportRequest(BaseModel):
    audit_id: Optional[str] = None
    analysis_data: Optional[dict] = None  # inline data for immediate report


class SubmitAuditRequest(BaseModel):
    practice_name: str
    specialty: str = ""
    num_providers: int = 1
    billing_company: str = ""
    contact_email: str
    contact_phone: str = ""
    payer_list: list = []  # [{payer_name, fee_schedule_method, code_count, fee_schedule_data}]
    remittance_data: list = []  # [{filename, payer_name, claims: [{claim_id, lines: [...]}]}]
    consent: bool = False
    user_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Fee schedule extraction prompt (shared by PDF, text, and image endpoints)
# ---------------------------------------------------------------------------

FEE_SCHEDULE_EXTRACTION_PROMPT = """You are a medical billing data extraction specialist. You will receive a document containing a payer fee schedule or contract rate table. Extract all CPT/HCPCS codes and their corresponding contracted reimbursement rates.

Return ONLY valid JSON matching this exact structure:
{
  "payer_name": "extracted payer name or empty string if not found",
  "effective_date": "YYYY-MM-DD or empty string if not found",
  "rates": [
    {"cpt": "99213", "rate": 95.50, "description": "Office visit, est. patient, level 3"}
  ]
}

Rules:
- Extract every CPT/HCPCS code visible in the document
- Rate should be the dollar amount per unit
- If multiple rates exist per code (e.g., facility/non-facility), use the non-facility rate
- If a code has no rate (N/A, blank, $0), skip it
- Description can be brief or empty string if not available
- Do not invent or estimate rates — only extract what is explicitly shown
- If no CPT codes or rates are found, return an empty rates array"""


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
# POST /api/provider/parse-835-batch
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
# POST /api/provider/extract-fee-schedule-pdf
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
# POST /api/provider/extract-fee-schedule-text
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
# POST /api/provider/extract-fee-schedule-image
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
# POST /api/provider/calculate-medicare-percentage
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
            "chargemaster_gap": chargemaster_gap,
            "adjustments": line.adjustments or "",
            "claim_id": line.claim_id or "",
            "medicare_rate": medicare_rate,
            "medicare_source": medicare_source,
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
        "scorecard": scorecard,
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
# POST /api/provider/analyze-denials  (Capability 1 — AI-powered)
# ---------------------------------------------------------------------------

DENIAL_SYSTEM_PROMPT = """You are a medical billing expert. You will receive a list of denied claims from an 835 remittance file. For each denial reason code present, explain the reason in plain language, assess whether an appeal is likely to succeed, estimate the value of attempting an appeal, and if appealable, draft a brief appeal letter template. Also identify patterns across the full denial set.

Return ONLY valid JSON matching this exact structure, with no other text:
{
  "denial_types": [
    {
      "adjustment_code": "CO-16",
      "plain_language": "explanation of what this code means",
      "is_actionable": true,
      "appeal_worthiness": "high",
      "recommended_action": "specific action to take",
      "appeal_letter_template": "Dear [Payer Name],\\n\\nWe are writing to appeal...",
      "count": 3,
      "total_value": 450.00
    }
  ],
  "pattern_summary": "summary of patterns across all denials",
  "total_recoverable_value": 1240.00,
  "preventable_denial_rate": 0.67
}

appeal_worthiness must be one of: "high", "medium", "low".
Group denials by adjustment code. Include count and total_value per group."""


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

    return result


# ---------------------------------------------------------------------------
# POST /api/provider/audit-report  (PDF generation with ReportLab)
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
                var_str = f"${variance:+,.2f}" if variance is not None else "—"
                rows_data.append([
                    li.get("cpt_code", ""),
                    f"${li.get('billed_amount', 0):,.2f}",
                    f"${li.get('paid_amount', 0):,.2f}",
                    f"${li.get('expected_payment', 0):,.2f}" if li.get("expected_payment") is not None else "—",
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
        ["Category", "Identified Amount", "Annualized (×12)"],
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
# POST /api/provider/submit-audit  (Submit audit + send emails)
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
            "user_id": req.user_id if req.user_id else None,
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
# Email template helpers
# ---------------------------------------------------------------------------

def _email_wrapper(inner_html: str) -> str:
    """Wrap email body in consistent branded template."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #1E293B;">
        <div style="background: #0D9488; padding: 24px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 24px;">Parity Audit</h1>
            <p style="color: #CCFBF1; margin: 4px 0 0; font-size: 14px;">by CivicScale</p>
        </div>
        <div style="padding: 32px 24px;">
            {inner_html}
        </div>
        <div style="background: #F8FAFC; padding: 16px 24px; text-align: center; border-top: 1px solid #E2E8F0;">
            <p style="color: #94A3B8; font-size: 12px; margin: 0;">
                Parity Audit by CivicScale &middot; Benchmark comparisons use publicly available CMS Medicare data.
                Not legal or financial advice. &middot; civicscale.ai
            </p>
        </div>
    </div>
    """


def _send_submission_confirmation(audit: dict):
    """Email 1: Submission confirmation — sent immediately when audit is submitted."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[AuditEmail] RESEND_API_KEY not configured, skipping")
            return
        resend.api_key = resend_key

        practice_name = audit.get("practice_name", "Practice")
        contact_email = audit.get("contact_email", "")
        audit_id = audit.get("id", "")
        payer_list = audit.get("payer_list", [])
        payer_names = ", ".join(p.get("payer_name", "Unknown") for p in payer_list) or "Not specified"
        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

        inner = f"""
        <h2 style="color: #1E293B; margin-top: 0;">Your Parity Audit has been submitted</h2>
        <p>Thank you for submitting your billing data for analysis. Your Parity Audit Report will be
        delivered to this email address within <strong>5-7 business days</strong>.</p>

        <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-weight: 600;">Audit Details:</p>
            <p style="margin: 4px 0; font-size: 14px; color: #475569;">Audit ID: <code>{audit_id}</code></p>
            <p style="margin: 4px 0; font-size: 14px; color: #475569;">Practice: {practice_name}</p>
            <p style="margin: 4px 0; font-size: 14px; color: #475569;">Payers analyzed: {payer_names}</p>
        </div>

        <p style="text-align: center; margin: 20px 0 0; font-size: 14px;">
            <a href="{frontend_url}/audit/account" style="color: #0D9488; font-weight: 600;">View your audit status &rarr;</a>
        </p>

        <p>If you have questions, reply to this email or contact
        <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>.</p>
        """

        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": [contact_email],
            "subject": f"Your Parity Audit has been submitted — {practice_name}",
            "html": _email_wrapper(inner),
        })
        print(f"[AuditEmail] Submission confirmation sent to {contact_email}")

    except Exception as exc:
        print(f"[AuditEmail] Submission confirmation failed: {exc}")


def _send_delivery_email(audit: dict, admin_notes: str = "", report_token: str = ""):
    """Email 2: Report delivery — sent when admin clicks 'Deliver Report'."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[AuditEmail] RESEND_API_KEY not configured, skipping")
            return
        resend.api_key = resend_key

        practice_name = audit.get("practice_name", "Practice")
        contact_email = audit.get("contact_email", "")
        audit_id = audit.get("id", "")
        payer_list = audit.get("payer_list", [])
        payer_count = len(payer_list)
        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

        # Try to get summary stats from analysis
        analysis_ids = audit.get("analysis_ids", [])
        total_underpayment = 0
        total_lines = 0
        exec_summary_line = ""

        if analysis_ids:
            try:
                sb = _get_supabase()
                for aid in analysis_ids[:10]:
                    row = sb.table("provider_analyses").select("result_json").eq("id", aid).execute()
                    if row.data:
                        rj = row.data[0].get("result_json", {})
                        s = rj.get("summary", {})
                        total_underpayment += s.get("total_underpayment", 0)
                        total_lines += s.get("line_count", 0)
            except Exception as exc:
                print(f"[AuditEmail] Failed to fetch analysis stats: {exc}")

        underpayment_str = f"${total_underpayment:,.2f}" if total_underpayment > 0 else "findings detailed in the report"

        notes_section = ""
        if admin_notes:
            notes_section = f"""
            <div style="background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 8px; padding: 16px; margin: 20px 0;">
                <p style="margin: 0 0 8px; font-weight: 600; color: #1E40AF;">Notes from our review:</p>
                <p style="margin: 0; font-size: 14px; color: #1E40AF;">{admin_notes}</p>
            </div>
            """

        inner = f"""
        <h2 style="color: #1E293B; margin-top: 0;">Your Parity Audit Report is ready</h2>
        <p>We analyzed <strong>{total_lines}</strong> transactions across <strong>{payer_count}</strong>
        payer{"s" if payer_count != 1 else ""} and identified <strong>{underpayment_str}</strong>
        in potential recoverable revenue.</p>

        <div style="text-align: center; margin: 28px 0;">
            <a href="{frontend_url}/report/{report_token}" style="
                display: inline-block; padding: 14px 32px; border-radius: 8px;
                background: #0D9488; color: #fff; font-weight: 600; font-size: 15px;
                text-decoration: none;
            ">View Report Online &rarr;</a>
        </div>
        <p style="text-align: center; margin: 8px 0 0; font-size: 13px;">
            <a href="{frontend_url}/audit/account" style="color: #0D9488;">View your account &rarr;</a>
        </p>

        {notes_section}

        <p>Want to discuss the findings? Reply to this email or contact
        <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>.</p>
        """

        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": [contact_email],
            "subject": f"Your Parity Audit Report is ready — {practice_name}",
            "html": _email_wrapper(inner),
        })
        print(f"[AuditEmail] Delivery email sent to {contact_email}")

        # Admin notification
        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": ["fred@civicscale.ai"],
            "subject": f"Audit Delivered: {practice_name}",
            "html": f"<p>Audit report delivered to {contact_email} for {practice_name}.</p>"
                     f"<p>Audit ID: {audit_id}</p>"
                     f"<p>Total underpayment: {underpayment_str}</p>",
        })

    except Exception as exc:
        print(f"[AuditEmail] Delivery email failed: {exc}")


def _send_followup_email(audit: dict):
    """Email 3: Follow-up — sent 3 days after delivery (manual or cron)."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[AuditEmail] RESEND_API_KEY not configured, skipping")
            return
        resend.api_key = resend_key

        practice_name = audit.get("practice_name", "Practice")
        contact_email = audit.get("contact_email", "")
        payer_list = audit.get("payer_list", [])
        payer_count = len(payer_list)
        report_token = audit.get("report_token", "")
        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

        # Get total underpayment for messaging
        total_underpayment = 0
        analysis_ids = audit.get("analysis_ids", [])
        if analysis_ids:
            try:
                sb = _get_supabase()
                for aid in analysis_ids[:10]:
                    row = sb.table("provider_analyses").select("result_json").eq("id", aid).execute()
                    if row.data:
                        rj = row.data[0].get("result_json", {})
                        total_underpayment += rj.get("summary", {}).get("total_underpayment", 0)
            except Exception:
                pass

        annualized = total_underpayment * 12
        underpayment_str = f"${annualized:,.2f}" if annualized > 0 else "significant potential"

        report_link_section = ""
        if report_token:
            report_link_section = f"""
            <div style="text-align: center; margin: 24px 0;">
                <a href="{frontend_url}/report/{report_token}" style="
                    display: inline-block; padding: 14px 32px; border-radius: 8px;
                    background: #0D9488; color: #fff; font-weight: 600; font-size: 15px;
                    text-decoration: none;
                ">View Your Report &rarr;</a>
            </div>
            """

        inner = f"""
        <h2 style="color: #1E293B; margin-top: 0;">Following up on your Parity Audit</h2>
        <p>We delivered your Parity Audit Report a few days ago. We identified
        <strong>{underpayment_str}</strong> in potential annual recoverable revenue across
        <strong>{payer_count}</strong> payer{"s" if payer_count != 1 else ""}.</p>

        {report_link_section}
        <p style="text-align: center; margin: 8px 0 0; font-size: 13px;">
            <a href="{frontend_url}/audit/account" style="color: #0D9488;">View your account &rarr;</a>
        </p>

        <p>Have you had a chance to review the findings? If you would like to discuss:</p>
        <ul style="color: #475569; font-size: 14px; line-height: 1.8;">
            <li>Which underpayments to appeal first</li>
            <li>How to address the denial patterns we identified</li>
            <li>What ongoing monitoring would look like for your practice</li>
        </ul>

        <p>Reply to this email or contact
        <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>.</p>

        <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-weight: 600; color: #0D9488;">Ongoing Monitoring</p>
            <p style="margin: 0; font-size: 14px; color: #475569;">
                Ongoing monitoring scans every remittance automatically and alerts you when new underpayments
                or denial patterns emerge. It costs <strong>$300/month</strong> and typically pays for itself
                within the first month.
            </p>
        </div>
        """

        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": [contact_email],
            "subject": f"Following up on your Parity Audit — {practice_name}",
            "html": _email_wrapper(inner),
        })
        print(f"[AuditEmail] Follow-up sent to {contact_email}")

        # Admin tracking
        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": ["fred@civicscale.ai"],
            "subject": f"Follow-up sent: {practice_name}",
            "html": f"<p>Follow-up email sent to {contact_email} for {practice_name}.</p>",
        })

    except Exception as exc:
        print(f"[AuditEmail] Follow-up email failed: {exc}")


# ---------------------------------------------------------------------------
# User Account — My Audits (authenticated, no admin required)
# ---------------------------------------------------------------------------

@router.get("/my-audits")
async def my_audits(request: Request):
    """Return audits belonging to the authenticated user (by email)."""
    user = await _get_authenticated_user(request)
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
                })
        except Exception as exc:
            print(f"[PublicReport] Failed to fetch analysis {aid}: {exc}")

    return {
        "practice_name": audit.get("practice_name", ""),
        "practice_specialty": audit.get("practice_specialty", ""),
        "payer_results": payer_results,
    }


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


class AdminArchiveBody(BaseModel):
    audit_id: str
    archived: bool = True


@router.post("/admin/audits/archive")
async def admin_archive_audit(body: AdminArchiveBody, request: Request):
    """Archive or unarchive an audit (admin only)."""
    await _verify_admin(request)
    sb = _get_supabase()
    sb.table("provider_audits").update({"archived": body.archived}).eq("id", body.audit_id).execute()
    return {"status": "ok", "archived": body.archived}


class AdminDeleteBody(BaseModel):
    audit_id: str


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


class AdminRunAnalysisBody(BaseModel):
    audit_id: str
    zip_code: str = ""       # optional override for Medicare locality
    percentage: float = 0    # optional override for medicare-pct method


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
        user_id = audit.get("user_id")
        if user_id:
            try:
                prof = sb.table("provider_profiles").select("zip_code").eq("user_id", user_id).maybeSingle().execute()
                if prof.data:
                    fallback_zip = prof.data.get("zip_code", "")
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
            # Auto-regenerate rates from Medicare PFS × percentage
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
    user_id = audit.get("user_id")
    if not zip_code and user_id:
        try:
            prof = sb.table("provider_profiles").select("zip_code").eq("user_id", user_id).maybeSingle().execute()
            if prof.data:
                zip_code = prof.data.get("zip_code", "")
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

        # Run contract integrity analysis (inline — mirrors analyze-contract logic)
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
        denial_adj_codes = []

        for line in lines:
            contracted_rate = rates.get(line["cpt_code"])
            expected_payment = None
            variance = None
            flag = "NO_CONTRACT"
            chargemaster_gap = None

            if contracted_rate is not None:
                contracted_rate = float(contracted_rate)
                expected_payment = round(contracted_rate * line["units"], 2)
                variance = round(line["paid_amount"] - expected_payment, 2)

                if line["billed_amount"] < contracted_rate:
                    chargemaster_gap = round((contracted_rate - line["billed_amount"]) * line["units"], 2)
                    billed_below_count += 1
                    total_chargemaster_gap += chargemaster_gap
                    flag = "BILLED_BELOW"
                elif line["paid_amount"] == 0 and expected_payment > 0:
                    flag = "DENIED"
                    denied_count += 1
                    denial_adj_codes.append(line.get("adjustments", ""))
                elif variance < -0.50:
                    flag = "UNDERPAID"
                    underpaid_count += 1
                    total_underpayment += abs(variance)
                elif variance > 0.50:
                    flag = "OVERPAID"
                    overpaid_count += 1
                else:
                    flag = "CORRECT"
                    correct_count += 1

                total_contracted += expected_payment
            else:
                no_contract_count += 1

            total_paid += line["paid_amount"]

            # Medicare benchmark
            medicare_rate = None
            medicare_source = None
            if carrier and locality:
                rate, source, _, _ = lookup_rate(line["cpt_code"], "CPT", carrier, locality)
                if rate is not None:
                    medicare_rate = rate
                    medicare_source = source

            enriched_lines.append({
                "cpt_code": line["cpt_code"],
                "billed_amount": line["billed_amount"],
                "paid_amount": line["paid_amount"],
                "units": line["units"],
                "contracted_rate": contracted_rate,
                "expected_payment": expected_payment,
                "variance": variance,
                "flag": flag,
                "chargemaster_gap": chargemaster_gap,
                "adjustments": line.get("adjustments", ""),
                "claim_id": line.get("claim_id", ""),
                "medicare_rate": medicare_rate,
                "medicare_source": medicare_source,
            })

        lines_with_contract = correct_count + underpaid_count + denied_count + overpaid_count + billed_below_count
        # Adherence = paid at or above contracted rate (correct + overpaid)
        adherent_count = correct_count + overpaid_count
        adherence_rate = round((adherent_count / lines_with_contract) * 100, 1) if lines_with_contract > 0 else 100.0

        # Scorecard
        clean_claim_rate = round(((correct_count + overpaid_count) / lines_with_contract) * 100, 1) if lines_with_contract > 0 else 100.0
        denial_rate = round((denied_count / lines_with_contract) * 100, 1) if lines_with_contract > 0 else 0.0
        preventable_codes = {"CO-16", "CO-97", "16", "97"}
        preventable_denial_count = 0
        for adj_str in denial_adj_codes:
            codes = [c.strip() for c in adj_str.split(",")]
            if any(c in preventable_codes for c in codes):
                preventable_denial_count += 1
        preventable_denial_rate = round((preventable_denial_count / denied_count) * 100, 1) if denied_count > 0 else 0.0

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
            "narrative": None,
        }

        # Run denial intelligence for denied lines
        denial_intel = None
        denied_lines_data = [
            {"cpt_code": l["cpt_code"], "billed_amount": l["billed_amount"],
             "adjustment_codes": l["adjustments"], "claim_id": l.get("claim_id", "")}
            for l in enriched_lines if l["flag"] == "DENIED"
        ]
        if denied_lines_data:
            denial_input = json.dumps({
                "payer_name": payer_name,
                "denied_lines": denied_lines_data,
                "total_denied_count": len(denied_lines_data),
            })
            denial_intel = _call_claude(
                system_prompt=DENIAL_SYSTEM_PROMPT,
                user_content=denial_input,
                max_tokens=4096,
            )

        # Save analysis to provider_analyses
        analysis_record = {
            "user_id": audit.get("user_id"),
            "payer_name": payer_name,
            "production_date": "",
            "total_billed": summary["total_contracted"],
            "total_paid": summary["total_paid"],
            "underpayment": summary["total_underpayment"],
            "adherence_rate": summary["adherence_rate"],
            "result_json": {
                "summary": summary,
                "scorecard": scorecard,
                "line_items": enriched_lines,
                "top_underpaid": sorted(
                    [
                        {"cpt_code": cpt, "total_underpayment": round(amt, 2)}
                        for cpt, amt in _aggregate_underpayments(enriched_lines).items()
                    ],
                    key=lambda x: x["total_underpayment"],
                    reverse=True,
                )[:10],
                "denial_intel": denial_intel,
            },
        }

        try:
            ins = sb.table("provider_analyses").insert(analysis_record).execute()
            if ins.data and len(ins.data) > 0:
                analysis_ids.append(ins.data[0]["id"])
        except Exception as exc:
            print(f"[RunAnalysis] Failed to save analysis for {payer_name}: {exc}")

        payer_results.append({
            "payer_name": payer_name,
            "summary": summary,
            "line_count": len(enriched_lines),
            "underpayment": summary["total_underpayment"],
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


def _aggregate_underpayments(enriched_lines: list) -> dict:
    """Aggregate underpayment amounts by CPT code."""
    result = {}
    for line in enriched_lines:
        if line.get("flag") == "UNDERPAID" and line.get("variance") is not None:
            cpt = line["cpt_code"]
            result[cpt] = result.get(cpt, 0) + abs(line["variance"])
    return result


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
                })
        except Exception as exc:
            print(f"[AdminResults] Failed to fetch analysis {aid}: {exc}")

    return {
        "audit": audit,
        "payer_results": payer_results,
        "has_results": len(payer_results) > 0,
    }


class AdminNotesBody(BaseModel):
    audit_id: str
    notes: str


@router.post("/admin/audits/notes")
async def admin_add_notes(body: AdminNotesBody, request: Request):
    """Add review notes to an audit (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()
    sb.table("provider_audits").update({
        "admin_notes": body.notes,
    }).eq("id", body.audit_id).execute()

    return {"status": "ok"}


class AdminDeliverBody(BaseModel):
    audit_id: str


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


class AdminFollowUpBody(BaseModel):
    audit_id: str


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


class AdminStatusBody(BaseModel):
    audit_id: str
    status: str


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


# ---------------------------------------------------------------------------
# Provider Subscriptions — Audit-to-Subscription Conversion
# ---------------------------------------------------------------------------

SUBSCRIPTION_STATUS_COLORS = {
    "active": "green",
    "canceled": "gray",
    "past_due": "red",
}


def _send_conversion_email(subscription: dict, audit: dict):
    """Email: Sent when audit is converted to monitoring subscription."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[SubEmail] RESEND_API_KEY not configured, skipping")
            return
        resend.api_key = resend_key

        practice_name = subscription.get("practice_name", "Practice")
        contact_email = subscription.get("contact_email", "")
        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

        # Get underpayment total from source audit
        total_underpayment = 0
        analysis_ids = audit.get("analysis_ids", []) or []
        if analysis_ids:
            try:
                sb = _get_supabase()
                for aid in analysis_ids[:10]:
                    row = sb.table("provider_analyses").select("result_json").eq("id", aid).execute()
                    if row.data:
                        rj = row.data[0].get("result_json", {})
                        total_underpayment += rj.get("summary", {}).get("total_underpayment", 0)
            except Exception:
                pass

        baseline_str = f"${total_underpayment:,.2f}" if total_underpayment > 0 else "your audit findings"

        inner = f"""
        <h2 style="color: #1E293B; margin-top: 0;">Your Parity monitoring is now active</h2>
        <p>Thank you for subscribing to Parity Provider Monitoring for <strong>{practice_name}</strong>.</p>

        <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-weight: 600; color: #0D9488;">Your baseline</p>
            <p style="margin: 0; font-size: 14px; color: #475569;">
                Your audit identified <strong>{baseline_str}</strong> in recoverable revenue.
                This is your baseline. Each month, we'll analyze your new remittance data
                and alert you to new underpayments and denial patterns.
            </p>
        </div>

        <p><strong>Next step:</strong> When your next month's remittance files (835s) are ready,
        send them to <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>
        and we'll run your monthly analysis.</p>

        <div style="text-align: center; margin: 28px 0;">
            <a href="{frontend_url}/audit/account" style="
                display: inline-block; padding: 14px 32px; border-radius: 8px;
                background: #0D9488; color: #fff; font-weight: 600; font-size: 15px;
                text-decoration: none;
            ">View Your Dashboard &rarr;</a>
        </div>

        <p>Questions? Reply to this email or contact
        <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>.</p>
        """

        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": [contact_email],
            "subject": f"Parity monitoring is active — {practice_name}",
            "html": _email_wrapper(inner),
        })
        print(f"[SubEmail] Conversion email sent to {contact_email}")

        # Admin notification
        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": ["fred@civicscale.ai"],
            "subject": f"New Subscription: {practice_name}",
            "html": f"<p>Subscription activated for {practice_name} ({contact_email}).</p>"
                     f"<p>Source audit: {audit.get('id', 'unknown')}</p>"
                     f"<p>Baseline underpayment: {baseline_str}</p>",
        })

    except Exception as exc:
        print(f"[SubEmail] Conversion email failed: {exc}")


def _convert_audit_to_subscription(audit: dict, sb=None) -> dict:
    """Core conversion logic: create provider_subscriptions row from a delivered audit."""
    if sb is None:
        sb = _get_supabase()

    from datetime import datetime

    # Build first monthly_analyses entry from audit's analysis_ids
    first_month = {
        "month": datetime.utcnow().strftime("%Y-%m"),
        "label": "Baseline (from audit)",
        "analysis_ids": audit.get("analysis_ids", []) or [],
        "added_at": datetime.utcnow().isoformat(),
    }

    sub_data = {
        "practice_name": audit.get("practice_name", ""),
        "practice_specialty": audit.get("practice_specialty", ""),
        "num_providers": audit.get("num_providers", 1),
        "billing_company": audit.get("billing_company", ""),
        "contact_email": audit.get("contact_email", ""),
        "user_id": audit.get("user_id"),
        "payer_data": audit.get("payer_list", []),
        "remittance_data": audit.get("remittance_data", []),
        "source_audit_id": audit.get("id"),
        "status": "active",
        "monthly_analyses": [first_month],
    }

    result = sb.table("provider_subscriptions").insert(sub_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create subscription")

    return result.data[0]


class AdminConvertBody(BaseModel):
    audit_id: str


@router.post("/admin/audits/convert-subscription")
async def admin_convert_to_subscription(body: AdminConvertBody, request: Request):
    """Convert a delivered audit to an active monitoring subscription (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()

    # Fetch audit
    result = sb.table("provider_audits").select("*").eq("id", body.audit_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = result.data[0]
    if audit.get("status") != "delivered":
        raise HTTPException(status_code=400, detail="Audit must be delivered before converting to subscription")

    # Check for existing subscription from this audit
    existing = sb.table("provider_subscriptions").select("id").eq("source_audit_id", body.audit_id).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Subscription already exists for this audit")

    subscription = _convert_audit_to_subscription(audit, sb)

    # Send conversion email
    _send_conversion_email(subscription, audit)

    return {"status": "ok", "subscription_id": subscription["id"]}


# ---------------------------------------------------------------------------
# Subscription Checkout (Stripe) — Authenticated User
# ---------------------------------------------------------------------------

class SubscriptionCheckoutBody(BaseModel):
    audit_id: str


@router.post("/subscription/checkout")
async def subscription_checkout(body: SubscriptionCheckoutBody, request: Request):
    """Create a Stripe checkout session for Provider monitoring subscription."""
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe_lib.api_key = stripe_key

    if not STRIPE_PRICE_PROVIDER_MONTHLY:
        raise HTTPException(status_code=503, detail="Provider price not configured")

    user = await _get_authenticated_user(request)
    sb = _get_supabase()

    # Verify audit belongs to user and is delivered
    audit_result = sb.table("provider_audits").select("*").eq("id", body.audit_id).execute()
    if not audit_result.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = audit_result.data[0]
    if audit.get("status") != "delivered":
        raise HTTPException(status_code=400, detail="Audit must be delivered first")

    # Verify user owns this audit (by email)
    user_email = user.email or ""
    if user_email.lower() != (audit.get("contact_email") or "").lower():
        raise HTTPException(status_code=403, detail="This audit does not belong to your account")

    # Get or create Stripe customer
    customer_id = None
    existing = sb.table("provider_subscriptions").select("stripe_customer_id").eq(
        "contact_email", user_email
    ).execute()
    if existing.data and existing.data[0].get("stripe_customer_id"):
        customer_id = existing.data[0]["stripe_customer_id"]

    if not customer_id:
        # Also check signal_subscriptions (shared Stripe customers)
        sig_result = sb.table("signal_subscriptions").select("stripe_customer_id").eq(
            "user_id", str(user.id)
        ).execute()
        if sig_result.data and sig_result.data[0].get("stripe_customer_id"):
            customer_id = sig_result.data[0]["stripe_customer_id"]

    if not customer_id:
        customer = stripe_lib.Customer.create(
            email=user_email,
            metadata={"supabase_user_id": str(user.id)},
        )
        customer_id = customer.id

    frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

    session = stripe_lib.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": STRIPE_PRICE_PROVIDER_MONTHLY, "quantity": 1}],
        success_url=f"{frontend_url}/audit/account?checkout_success=1",
        cancel_url=f"{frontend_url}/audit/account",
        metadata={
            "supabase_user_id": str(user.id),
            "audit_id": body.audit_id,
            "type": "provider_monitoring",
        },
    )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# Subscription Webhook (Stripe)
# ---------------------------------------------------------------------------

@router.post("/subscription/webhook")
async def subscription_webhook(request: Request):
    """Process Stripe webhook events for Provider monitoring subscriptions."""
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    if not stripe_key or not webhook_secret:
        return JSONResponse({"error": "Stripe not configured"}, status_code=500)

    stripe_lib.api_key = stripe_key

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe_lib.Webhook.construct_event(payload, sig, webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {exc}")

    sb = _get_supabase()
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata", {})
        # Only handle provider_monitoring type
        if metadata.get("type") != "provider_monitoring":
            return {"status": "ok", "skipped": True}

        audit_id = metadata.get("audit_id")
        user_id = metadata.get("supabase_user_id")
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")

        if audit_id and subscription_id:
            # Check if subscription already exists for this audit
            existing = sb.table("provider_subscriptions").select("id").eq(
                "source_audit_id", audit_id
            ).execute()

            if existing.data:
                # Update existing with Stripe IDs
                sb.table("provider_subscriptions").update({
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                }).eq("source_audit_id", audit_id).execute()
            else:
                # Convert audit to subscription
                audit_result = sb.table("provider_audits").select("*").eq("id", audit_id).execute()
                if audit_result.data:
                    audit = audit_result.data[0]
                    subscription = _convert_audit_to_subscription(audit, sb)
                    # Update with Stripe IDs
                    sb.table("provider_subscriptions").update({
                        "stripe_customer_id": customer_id,
                        "stripe_subscription_id": subscription_id,
                    }).eq("id", subscription["id"]).execute()
                    # Send conversion email
                    _send_conversion_email(subscription, audit)

    elif event_type == "customer.subscription.deleted":
        subscription_id = obj.get("id")
        if subscription_id:
            from datetime import datetime
            sb.table("provider_subscriptions").update({
                "status": "canceled",
                "canceled_at": datetime.utcnow().isoformat(),
            }).eq("stripe_subscription_id", subscription_id).execute()

    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        if subscription_id:
            sb.table("provider_subscriptions").update({
                "status": "past_due",
            }).eq("stripe_subscription_id", subscription_id).execute()

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Admin: Add Monthly Analysis to Subscription
# ---------------------------------------------------------------------------

class AdminAddMonthBody(BaseModel):
    subscription_id: str


@router.post("/admin/subscriptions/add-month")
async def admin_add_month(
    request: Request,
    subscription_id: str = "",
    file: UploadFile = File(...),
):
    """Upload 835 files and run monthly analysis for a subscription (admin only)."""
    await _verify_admin(request)

    if not subscription_id:
        raise HTTPException(status_code=400, detail="subscription_id required")

    sb = _get_supabase()

    # Fetch subscription
    sub_result = sb.table("provider_subscriptions").select("*").eq("id", subscription_id).execute()
    if not sub_result.data:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub = sub_result.data[0]

    # Parse 835
    content = await file.read()
    raw = content.decode("utf-8", errors="replace")
    parsed = parse_835(raw)
    claims_list = parsed.get("claims", [])
    payer_name = parsed.get("payer_name", "")

    # Build remittance entry
    entry = {
        "filename": file.filename or "uploaded.835",
        "payer_name": payer_name,
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

    # Append to remittance_data
    existing_rem = sub.get("remittance_data", []) or []
    existing_rem.append(entry)
    sb.table("provider_subscriptions").update({"remittance_data": existing_rem}).eq("id", subscription_id).execute()

    # Add monthly_analyses entry
    from datetime import datetime
    monthly = sub.get("monthly_analyses", []) or []
    month_label = datetime.utcnow().strftime("%Y-%m")
    new_month = {
        "month": month_label,
        "label": f"Month {len(monthly) + 1}",
        "filename": file.filename or "uploaded.835",
        "payer_name": payer_name,
        "claims_count": len(claims_list),
        "lines_count": sum(len(c.get("line_items", [])) for c in claims_list),
        "added_at": datetime.utcnow().isoformat(),
    }
    monthly.append(new_month)
    sb.table("provider_subscriptions").update({"monthly_analyses": monthly}).eq("id", subscription_id).execute()

    return {
        "status": "ok",
        "month": month_label,
        "claims_parsed": len(claims_list),
        "total_lines": new_month["lines_count"],
        "payer_name": payer_name,
    }


# ---------------------------------------------------------------------------
# User: My Subscription
# ---------------------------------------------------------------------------

@router.get("/my-subscription")
async def my_subscription(request: Request):
    """Return the authenticated user's Provider monitoring subscription."""
    user = await _get_authenticated_user(request)
    email = user.email
    if not email:
        raise HTTPException(status_code=400, detail="No email on account")

    sb = _get_supabase()
    result = sb.table("provider_subscriptions") \
        .select("*") \
        .eq("contact_email", email) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()

    if not result.data:
        return {"subscription": None}

    sub = result.data[0]
    return {
        "subscription": {
            "id": sub["id"],
            "practice_name": sub.get("practice_name", ""),
            "status": sub.get("status", "active"),
            "monthly_analyses": sub.get("monthly_analyses", []),
            "source_audit_id": sub.get("source_audit_id"),
            "created_at": sub.get("created_at"),
            "stripe_subscription_id": sub.get("stripe_subscription_id"),
        },
    }


# ---------------------------------------------------------------------------
# Admin: List Subscriptions
# ---------------------------------------------------------------------------

@router.get("/admin/subscriptions")
async def admin_list_subscriptions(request: Request):
    """List all provider subscriptions (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()
    result = sb.table("provider_subscriptions") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()

    return {"subscriptions": result.data or []}
