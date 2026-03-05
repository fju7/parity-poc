"""
Provider dashboard endpoints:
  GET  /api/provider/contract-template  — download contract rates Excel template
  POST /api/provider/save-rates         — save parsed contract rates
  POST /api/provider/parse-835          — parse an uploaded 835 EDI file
  POST /api/provider/parse-835-batch    — parse multiple 835 files (including zip)
  POST /api/provider/analyze-contract   — compare remittance vs contracted rates
  POST /api/provider/analyze-coding     — coding pattern analysis (E&M distribution)
  POST /api/provider/analyze-denials    — AI-powered denial interpretation + appeal letters

No PHI is stored. Contract rates and analysis results are tied to user_id.
"""

import io
import json
import os
import re
import time
import zipfile
from collections import Counter
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
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


def _call_claude(system_prompt: str, user_content: str, max_tokens: int = 4096) -> dict:
    """Call Claude API with retry on 529, return parsed JSON."""
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

    # Adherence rate: % of lines with contract that are CORRECT
    lines_with_contract = (correct_count + underpaid_count + denied_count
                           + overpaid_count + billed_below_count)
    adherence_rate = (
        round((correct_count / lines_with_contract) * 100, 1)
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
