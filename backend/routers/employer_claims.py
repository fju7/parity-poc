"""Employer claims-check endpoint — upload CSV/Excel/835 EDI claims and compare against CMS Medicare rates.

POST /claims-check — accepts multipart file upload + optional column mapping.
POST /contract-parse — accepts carrier contract PDF, extracts rates, compares to Medicare.
Uses Claude AI for intelligent column mapping when headers are ambiguous.
Supports 835 EDI files (parsed via parse_835) and ZIP archives of 835 files.
Reuses the existing CMS Medicare rate database from benchmark.py.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
import zipfile
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from routers.employer_shared import (
    _get_supabase, _call_claude, check_rate_limit,
)
from routers.benchmark import resolve_locality, lookup_rate
from utils.parse_835 import parse_835

router = APIRouter(tags=["employer"])


# ---------------------------------------------------------------------------
# Column mapping AI prompt
# ---------------------------------------------------------------------------

COLUMN_MAPPING_PROMPT = """You are a medical claims data specialist. You will receive a list of column headers from an employer's claims file (CSV or Excel). Map each relevant column to our standard field names.

Required fields to map:
- cpt_code: The CPT/HCPCS procedure code column
- paid_amount: The amount the plan/insurer paid
- billed_amount: The amount billed by the provider (optional but preferred)

Optional fields:
- provider_name: Provider/physician name
- service_date: Date of service
- diagnosis_code: ICD-10 diagnosis code
- member_id: Member/employee identifier (we will NOT store this)
- place_of_service: Facility type indicator

Return ONLY valid JSON matching this exact structure:
{
  "mappings": {
    "cpt_code": "exact column header name",
    "paid_amount": "exact column header name",
    "billed_amount": "exact column header name or null",
    "provider_name": "exact column header name or null",
    "service_date": "exact column header name or null"
  },
  "confidence": "high" | "medium" | "low",
  "unmapped_required": ["list of required fields that could not be mapped"],
  "notes": "any relevant notes about the mapping"
}

Rules:
- Match column headers case-insensitively
- Common aliases: "Proc Code" = cpt_code, "Allowed Amount" = paid_amount, "Charge Amount" = billed_amount
- If a required field cannot be mapped, include it in unmapped_required
- Do not guess — only map when you are confident"""


# ---------------------------------------------------------------------------
# POST /claims-check
# ---------------------------------------------------------------------------

@router.post("/claims-check")
async def employer_claims_check(
    request: Request,
    file: UploadFile = File(...),
    zip_code: str = Form(...),
    email: Optional[str] = Form(None),
    column_mapping: Optional[str] = Form(None),  # JSON string
):
    """Analyze an employer claims file against CMS Medicare benchmarks."""
    check_rate_limit(request, max_requests=5)

    # --- Parse file ---
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")
    filename = file.filename or "upload"

    # Detect file type
    fname = filename.lower()
    is_835 = fname.endswith((".835", ".edi")) or (fname.endswith(".txt") and b"ISA" in content[:200])
    is_zip = fname.endswith(".zip")

    source_format = "csv_excel"
    mapping = None

    if is_835:
        # --- 835 EDI file ---
        source_format = "835_edi"
        text = content.decode("utf-8", errors="replace")
        if "ISA" not in text[:200]:
            raise HTTPException(status_code=400, detail="File does not appear to be a valid 835 EDI file (missing ISA segment)")
        parsed = parse_835(text)
        if not parsed.get("line_items"):
            raise HTTPException(status_code=400, detail="No line items found in 835 EDI file")
        df = _edi_items_to_df(parsed["line_items"], parsed.get("payee_name", ""))

    elif is_zip:
        # --- ZIP archive of 835/EDI files ---
        source_format = "835_zip"
        all_items = []
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                edi_names = [n for n in zf.namelist() if n.lower().endswith((".835", ".edi"))]
                if not edi_names:
                    raise HTTPException(status_code=400, detail="ZIP file contains no .835 or .edi files")
                for name in edi_names:
                    raw = zf.read(name).decode("utf-8", errors="replace")
                    if "ISA" not in raw[:200]:
                        continue
                    parsed = parse_835(raw)
                    for item in parsed.get("line_items", []):
                        item["_provider"] = parsed.get("payee_name", "")
                    all_items.extend(parsed.get("line_items", []))
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
        if not all_items:
            raise HTTPException(status_code=400, detail="No valid 835 line items found in ZIP archive")
        df = _edi_items_to_df(all_items)

    else:
        # --- CSV / Excel (existing behavior) ---
        try:
            if fname.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(content))
            else:
                df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="File contains no data")

    # --- Column mapping (only for CSV/Excel — 835 columns are already standard) ---
    if source_format == "csv_excel":
        columns = list(df.columns)

        if column_mapping:
            try:
                mapping = json.loads(column_mapping)
            except json.JSONDecodeError:
                pass

        if not mapping:
            # Use Claude AI to map columns
            mapping_result = _call_claude(
                system_prompt=COLUMN_MAPPING_PROMPT,
                user_content=json.dumps({
                    "columns": columns,
                    "sample_rows": df.head(5).to_dict(orient="records"),
                }),
                max_tokens=1024,
            )
            if mapping_result and mapping_result.get("mappings"):
                mapping = mapping_result["mappings"]
            else:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "Could not auto-map columns",
                        "columns": columns,
                        "hint": "Please provide a column_mapping JSON with keys: cpt_code, paid_amount",
                    },
                )

        # Validate required mappings
        cpt_col = mapping.get("cpt_code")
        paid_col = mapping.get("paid_amount")
        billed_col = mapping.get("billed_amount")

        if not cpt_col or cpt_col not in df.columns:
            raise HTTPException(status_code=422, detail=f"CPT code column '{cpt_col}' not found in file")
        if not paid_col or paid_col not in df.columns:
            raise HTTPException(status_code=422, detail=f"Paid amount column '{paid_col}' not found in file")
    else:
        # 835/ZIP: columns are already standardized
        cpt_col = "cpt_code"
        paid_col = "paid_amount"
        billed_col = "billed_amount"
        mapping = {"cpt_code": "cpt_code", "paid_amount": "paid_amount", "billed_amount": "billed_amount"}

    # --- Resolve locality for Medicare rate lookup ---
    carrier, locality = resolve_locality(zip_code)
    if not carrier or not locality:
        raise HTTPException(status_code=400, detail=f"Could not resolve locality for ZIP {zip_code}")

    # --- Analyze each claim line ---
    results = []
    total_paid = 0.0
    total_excess_2x = 0.0
    flag_counts = {}

    for _, row in df.iterrows():
        cpt = str(row.get(cpt_col, "")).strip()
        if not cpt:
            continue

        paid = _safe_float(row.get(paid_col, 0))
        billed = _safe_float(row.get(billed_col, 0)) if billed_col and billed_col in df.columns else None

        # Look up CMS Medicare rate
        rate_val, source, _, _ = lookup_rate(cpt, "CPT", carrier, locality)

        line = {
            "cpt_code": cpt,
            "paid_amount": paid,
            "billed_amount": billed,
            "medicare_rate": rate_val,
            "medicare_source": source if rate_val else None,
            "ratio": None,
            "flag": None,
            "excess_amount": None,
        }

        if rate_val and rate_val > 0 and paid > 0:
            ratio = round(paid / rate_val, 2)
            line["ratio"] = ratio
            if ratio > 3.0:
                line["flag"] = "SEVERE"
            elif ratio > 2.0:
                line["flag"] = "HIGH"
                excess = round(paid - (rate_val * 2), 2)
                line["excess_amount"] = excess
                total_excess_2x += excess
            elif ratio > 1.5:
                line["flag"] = "ELEVATED"
            elif ratio < 0.5:
                line["flag"] = "LOW"

            if line["flag"]:
                flag_counts[cpt] = flag_counts.get(cpt, 0) + 1

        total_paid += paid
        results.append(line)

    # --- Top flagged CPT ---
    top_flagged_cpt = max(flag_counts, key=flag_counts.get) if flag_counts else None
    top_flagged_excess = 0.0
    if top_flagged_cpt:
        top_flagged_excess = sum(
            r.get("excess_amount", 0) or 0
            for r in results
            if r["cpt_code"] == top_flagged_cpt
        )

    # --- Summary ---
    flagged_lines = [r for r in results if r.get("flag")]
    summary = {
        "total_claims": len(results),
        "total_paid": round(total_paid, 2),
        "total_excess_2x": round(total_excess_2x, 2),
        "flagged_count": len(flagged_lines),
        "severe_count": len([r for r in results if r.get("flag") == "SEVERE"]),
        "high_count": len([r for r in results if r.get("flag") == "HIGH"]),
        "elevated_count": len([r for r in results if r.get("flag") == "ELEVATED"]),
        "top_flagged_cpt": top_flagged_cpt,
        "top_flagged_excess": round(top_flagged_excess, 2),
        "locality": {"carrier": carrier, "locality_code": locality, "zip_code": zip_code},
    }

    # --- AI narrative executive summary ---
    narrative = None
    try:
        # Build top 5 flagged procedures for the prompt
        top_findings_lines = []
        flagged_sorted = sorted(
            [r for r in results if r.get("flag")],
            key=lambda r: r.get("ratio") or 0,
            reverse=True,
        )
        seen_cpts = set()
        for r in flagged_sorted:
            cpt = r["cpt_code"]
            if cpt in seen_cpts:
                continue
            seen_cpts.add(cpt)
            count = sum(1 for x in results if x["cpt_code"] == cpt and x.get("flag"))
            avg_paid = sum(x["paid_amount"] for x in results if x["cpt_code"] == cpt) / max(count, 1)
            top_findings_lines.append(
                f"CPT {cpt}: avg paid ${avg_paid:,.0f}, Medicare rate ${r.get('medicare_rate', 0) or 0:,.0f}, "
                f"markup {r.get('ratio', 0)}x, {count} claim(s), flag={r.get('flag')}"
            )
            if len(top_findings_lines) >= 5:
                break

        narrative_prompt = (
            "You are a healthcare benefits analyst writing for a CFO or HR director. "
            "Based on this claims analysis, write a 3-4 sentence executive summary. "
            "Be specific about dollar amounts and procedure names. Do not use jargon. "
            "Do not recommend specific vendors. End with one sentence about what action "
            "this finding suggests.\n\n"
            f"Claims analyzed: {len(results)}\n"
            f"Total paid: ${total_paid:,.0f}\n"
            f"Excess vs 2x Medicare benchmark: ${total_excess_2x:,.0f}\n"
            f"Top findings:\n" + "\n".join(top_findings_lines) + "\n\n"
            "Write only the summary paragraph. No headers, no bullet points, no preamble."
        )

        narrative = _generate_narrative(narrative_prompt)
    except Exception as exc:
        print(f"[Employer Claims] Narrative generation failed (non-fatal): {exc}")

    response = {
        "summary": summary,
        "narrative": narrative,
        "line_items": results[:500],  # Cap at 500 for response size
        "column_mapping": mapping,
        "total_lines_analyzed": len(results),
        "source_format": source_format,
    }

    # --- Persist to Supabase ---
    try:
        sb = _get_supabase()
        sb.table("employer_claims_uploads").insert({
            "email": email,
            "filename_original": filename,
            "total_claims": len(results),
            "total_paid": float(total_paid),
            "total_excess_2x": float(total_excess_2x),
            "top_flagged_cpt": top_flagged_cpt,
            "top_flagged_excess": float(top_flagged_excess),
            "column_mapping_json": mapping,
            "results_json": summary,
        }).execute()
    except Exception as exc:
        print(f"[Employer Claims] Failed to save session: {exc}")

    return response


# ---------------------------------------------------------------------------
# Contract parsing prompt
# ---------------------------------------------------------------------------

CONTRACT_PARSE_PROMPT = """You are a healthcare contract analyst. Extract all negotiated rate information from this carrier contract or fee schedule. For each procedure or rate category found, identify:
- CPT code or procedure category name
- Negotiated rate (dollar amount or percentage of Medicare)
- Any modifiers or conditions

Return ONLY valid JSON in this exact structure:
{
  "carrier_name": "name of insurance carrier if found",
  "contract_effective_date": "date if found, else null",
  "rate_basis": "fee_schedule" | "percent_medicare" | "mixed" | "unknown",
  "medicare_percentage": 110,
  "line_items": [
    {
      "cpt_code": "99213",
      "description": "Office visit, established patient",
      "negotiated_rate": 125.00,
      "rate_type": "fixed" | "percent_medicare"
    }
  ],
  "notes": "any relevant observations about the contract structure"
}

If the document is not a carrier contract or fee schedule, return:
{"error": "Not a carrier contract or fee schedule"}"""

# Top 20 common CPT codes for percent-of-Medicare benchmark comparison
COMMON_CPT_CODES = [
    "99213", "99214", "99215", "99212", "99211",
    "99203", "99204", "99205", "99232", "99233",
    "99291", "99223", "99222", "99221", "99238",
    "36415", "85025", "80053", "93000", "71046",
]


# ---------------------------------------------------------------------------
# POST /contract-parse
# ---------------------------------------------------------------------------

@router.post("/contract-parse")
async def employer_contract_parse(
    request: Request,
    file: UploadFile = File(...),
    zip_code: str = Form(...),
):
    """Parse a carrier contract PDF and compare rates against CMS Medicare benchmarks."""
    check_rate_limit(request, max_requests=3)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")

    filename = (file.filename or "upload").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Validate it looks like a PDF
    if not content[:5] == b"%PDF-":
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF")

    # Resolve locality for Medicare rate lookups
    carrier, locality = resolve_locality(zip_code)
    if not carrier or not locality:
        raise HTTPException(status_code=400, detail=f"Could not resolve locality for ZIP {zip_code}")

    # --- Send PDF to Claude for contract extraction ---
    try:
        parsed = _parse_contract_pdf(content)
    except Exception as exc:
        print(f"[Contract Parse] AI extraction failed: {exc}")
        raise HTTPException(status_code=400, detail="Could not extract rate information from this document. Please ensure it is a carrier contract or fee schedule.")

    if parsed.get("error"):
        raise HTTPException(status_code=400, detail=parsed["error"])

    rate_basis = parsed.get("rate_basis", "unknown")
    line_items = parsed.get("line_items", [])
    medicare_percentage = parsed.get("medicare_percentage")

    # --- Benchmark comparison for fixed-rate line items ---
    for item in line_items:
        if item.get("rate_type") == "fixed" and item.get("cpt_code"):
            rate_val, source, _, _ = lookup_rate(item["cpt_code"], "CPT", carrier, locality)
            item["medicare_rate"] = rate_val
            item["medicare_source"] = source if rate_val else None
            if rate_val and rate_val > 0 and item.get("negotiated_rate", 0) > 0:
                item["markup_ratio"] = round(item["negotiated_rate"] / rate_val, 2)
                item["variance_pct"] = round((item["negotiated_rate"] - rate_val) / rate_val * 100, 1)
            else:
                item["markup_ratio"] = None
                item["variance_pct"] = None

    # --- Benchmark comparison for percent-of-Medicare contracts ---
    benchmark_comparison = []
    if rate_basis == "percent_medicare" and medicare_percentage:
        for cpt in COMMON_CPT_CODES:
            rate_val, source, _, _ = lookup_rate(cpt, "CPT", carrier, locality)
            if rate_val and rate_val > 0:
                contracted_rate = round(rate_val * medicare_percentage / 100, 2)
                benchmark_comparison.append({
                    "cpt_code": cpt,
                    "medicare_rate": rate_val,
                    "contracted_rate": contracted_rate,
                    "percentage": medicare_percentage,
                })

    # --- Contract narrative ---
    contract_narrative = None
    try:
        rate_items_with_benchmark = [i for i in line_items if i.get("markup_ratio")]
        if rate_items_with_benchmark:
            avg_markup = sum(i["markup_ratio"] for i in rate_items_with_benchmark) / len(rate_items_with_benchmark)
            worst_items = sorted(rate_items_with_benchmark, key=lambda x: x.get("markup_ratio", 0), reverse=True)[:3]
            worst_summary = "; ".join(
                f"CPT {i['cpt_code']} ({i.get('description', 'N/A')}): {i['markup_ratio']}x Medicare"
                for i in worst_items
            )
            narrative_prompt = (
                "You are a healthcare benefits analyst writing for a CFO or HR director. "
                "Based on this carrier contract analysis, write a 2-3 sentence observation about "
                "contract competitiveness. Be specific about percentages. Do not use jargon. "
                "Do not recommend specific vendors.\n\n"
                f"Rate basis: {rate_basis}\n"
                f"Carrier: {parsed.get('carrier_name', 'Unknown')}\n"
                f"Total rates extracted: {len(line_items)}\n"
                f"Average markup vs Medicare: {avg_markup:.1f}x\n"
                f"Highest markup rates: {worst_summary}\n\n"
                "Write only the summary paragraph. No headers, no bullet points, no preamble."
            )
            contract_narrative = _generate_narrative(narrative_prompt)
        elif rate_basis == "percent_medicare" and medicare_percentage:
            narrative_prompt = (
                "You are a healthcare benefits analyst writing for a CFO or HR director. "
                "Based on this carrier contract analysis, write a 2-3 sentence observation. "
                "Do not use jargon. Do not recommend specific vendors.\n\n"
                f"Carrier: {parsed.get('carrier_name', 'Unknown')}\n"
                f"Rate basis: Percentage of Medicare at {medicare_percentage}%\n\n"
                "Write only the summary paragraph. No headers, no bullet points, no preamble."
            )
            contract_narrative = _generate_narrative(narrative_prompt)
    except Exception as exc:
        print(f"[Contract Parse] Narrative generation failed (non-fatal): {exc}")

    return {
        "carrier_name": parsed.get("carrier_name"),
        "contract_effective_date": parsed.get("contract_effective_date"),
        "rate_basis": rate_basis,
        "medicare_percentage": medicare_percentage,
        "line_items": line_items,
        "benchmark_comparison": benchmark_comparison,
        "contract_narrative": contract_narrative,
        "notes": parsed.get("notes"),
        "locality": {"carrier": carrier, "locality_code": locality, "zip_code": zip_code},
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_contract_pdf(content: bytes) -> dict:
    """Send PDF to Claude document API and extract contract rate data."""
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    b64_data = base64.b64encode(content).decode("utf-8")
    client = anthropic.Anthropic(api_key=api_key)

    backoff_delays = [2, 5, 10]
    response = None
    for attempt in range(len(backoff_delays) + 1):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                temperature=0,
                system=CONTRACT_PARSE_PROMPT,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": b64_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "Extract all negotiated rate information from this carrier contract or fee schedule.",
                        },
                    ],
                }],
            )
            break
        except Exception as exc:
            err_str = str(exc)
            if "529" in err_str and attempt < len(backoff_delays):
                time.sleep(backoff_delays[attempt])
                continue
            raise

    raw_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw_text += block.text

    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```\s*$", "", raw_text)
    raw_text = raw_text.strip()

    return json.loads(raw_text)


def _generate_narrative(prompt: str) -> str | None:
    """Call Claude API and return raw text (not JSON-parsed). Returns None on failure."""
    import os
    try:
        import anthropic
    except ImportError:
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        temperature=0,
        system="You are a concise healthcare benefits analyst.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = ""
    for block in response.content:
        if hasattr(block, "text"):
            text += block.text
    return text.strip() or None


def _edi_items_to_df(line_items: list, default_provider: str = "") -> pd.DataFrame:
    """Convert parse_835 line_items into a standardized DataFrame."""
    rows = []
    for item in line_items:
        rows.append({
            "cpt_code": item.get("cpt_code", ""),
            "paid_amount": item.get("paid_amount", 0),
            "billed_amount": item.get("billed_amount", 0),
            "provider_name": item.get("_provider", default_provider),
            "service_date": item.get("service_date", ""),
        })
    return pd.DataFrame(rows)


def _safe_float(val) -> float:
    """Convert a value to float, handling currency strings and NaN."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        import math
        return 0.0 if math.isnan(val) else float(val)
    s = str(val).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0
