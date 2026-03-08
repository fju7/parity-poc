"""Employer claims-check endpoint — upload CSV/Excel/835 EDI claims and compare against CMS Medicare rates.

POST /claims-check — accepts multipart file upload + optional column mapping.
Uses Claude AI for intelligent column mapping when headers are ambiguous.
Supports 835 EDI files (parsed via parse_835) and ZIP archives of 835 files.
Reuses the existing CMS Medicare rate database from benchmark.py.
"""

from __future__ import annotations

import io
import json
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

    response = {
        "summary": summary,
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
# Helpers
# ---------------------------------------------------------------------------

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
