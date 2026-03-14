"""Employer pharmacy claims analysis — upload CSV/Excel/835 and benchmark against NADAC.

POST /pharmacy/analyze — accepts multipart file upload of pharmacy claims data.
Two-stage parsing: attempt 835 EDI first (pharmacy N4 segments), then AI extraction.
Benchmarks against NADAC (National Average Drug Acquisition Cost) from Supabase.
"""

from __future__ import annotations

import io
import json
import os
import re
import time
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from routers.employer_shared import (
    _get_supabase, _call_claude, check_rate_limit,
)
from utils.parse_835 import parse_835

router = APIRouter(tags=["employer"])


# ---------------------------------------------------------------------------
# AI extraction prompt for pharmacy claims
# ---------------------------------------------------------------------------

PHARMACY_EXTRACTION_PROMPT = """You are a pharmacy claims data extraction specialist. Extract all pharmacy claim line items from this document. The document may be a CSV, Excel export, PDF remittance, or PBM report.

Return ONLY valid JSON:
{
  "plan_name": "string or null",
  "date_range": "string or null",
  "line_items": [
    {
      "ndc_code": "11-digit NDC or null",
      "hcpcs_code": "HCPCS/J-code if visible (e.g. J0185) or null",
      "drug_name": "string",
      "generic_name": "string or null",
      "brand_or_generic": "brand|generic|unknown",
      "days_supply": number or null,
      "quantity": number or null,
      "billed_amount": number,
      "plan_paid": number or null,
      "member_paid": number or null,
      "therapeutic_class": "string or null",
      "is_specialty": boolean or null,
      "fill_date": "YYYY-MM-DD or null"
    }
  ],
  "total_billed": number or null
}

Extract every line item. Use null for any field not visible."""


# ---------------------------------------------------------------------------
# Known specialty drug indicators (therapeutic classes / drug names)
# ---------------------------------------------------------------------------

SPECIALTY_KEYWORDS = [
    "biologic", "tnf", "jak inhibitor", "il-23", "il-17", "il-6",
    "bcl-2", "hepatitis c", "oncology", "hiv", "multiple sclerosis",
    "humira", "adalimumab", "enbrel", "etanercept", "remicade",
    "infliximab", "stelara", "ustekinumab", "skyrizi", "risankizumab",
    "rinvoq", "upadacitinib", "xeljanz", "tofacitinib", "keytruda",
    "pembrolizumab", "opdivo", "nivolumab", "revlimid", "lenalidomide",
    "imbruvica", "ibrutinib", "venclexta", "venetoclax", "mavyret",
    "glecaprevir", "harvoni", "sofosbuvir", "epclusa", "tecfidera",
    "ocrevus", "ocrelizumab", "tysabri", "natalizumab", "copaxone",
    "glatiramer", "ozempic", "wegovy", "semaglutide",
    "trulicity", "dulaglutide",
]


def _is_specialty(drug_name: str, generic_name: str, therapeutic_class: str, is_specialty_flag=None) -> bool:
    """Determine if a drug is specialty based on name/class heuristics."""
    if is_specialty_flag is True:
        return True
    combined = f"{drug_name} {generic_name or ''} {therapeutic_class or ''}".lower()
    return any(kw in combined for kw in SPECIALTY_KEYWORDS)


# ---------------------------------------------------------------------------
# POST /pharmacy/analyze
# ---------------------------------------------------------------------------

@router.post("/pharmacy/analyze")
async def employer_pharmacy_analyze(
    request: Request,
    file: UploadFile = File(...),
    email: Optional[str] = Form(None),
):
    """Analyze pharmacy claims file against NADAC benchmarks."""
    check_rate_limit(request, max_requests=5)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")
    filename = file.filename or "upload"
    fname = filename.lower()

    # ----- Stage 1: try 835 EDI parsing -----
    line_items = []
    plan_name = None
    date_range = None

    is_835 = fname.endswith((".835", ".edi")) or (fname.endswith(".txt") and b"ISA" in content[:200])
    if is_835:
        try:
            text = content.decode("utf-8", errors="replace")
            parsed = parse_835(text)
            # Look for pharmacy-related line items (N4 segments or NDC-like codes)
            for item in parsed.get("line_items", []):
                code = item.get("cpt_code", "")
                # NDC codes are typically 11 digits; pharmacy 835s may use N4 qualifier
                if item.get("qualifier") == "N4" or (code.isdigit() and len(code) >= 10):
                    line_items.append({
                        "ndc_code": code.zfill(11) if code.isdigit() else code,
                        "drug_name": item.get("description", code),
                        "generic_name": None,
                        "brand_or_generic": "unknown",
                        "days_supply": None,
                        "quantity": item.get("units", 1),
                        "billed_amount": item.get("billed_amount", 0),
                        "plan_paid": item.get("paid_amount", 0),
                        "member_paid": None,
                        "therapeutic_class": None,
                        "is_specialty": None,
                        "fill_date": item.get("service_date"),
                    })
            plan_name = parsed.get("payer_name")
            date_range = parsed.get("production_date")
        except Exception as exc:
            print(f"[Pharmacy] 835 parse attempt failed: {exc}")

    # ----- Stage 2: CSV/Excel direct parsing -----
    if not line_items and (fname.endswith(".csv") or fname.endswith((".xlsx", ".xls"))):
        try:
            if fname.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))

            # Normalize column names to lowercase
            df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

            # Auto-detect columns
            col_map = _auto_map_columns(df.columns.tolist())
            if col_map.get("drug_name") or col_map.get("ndc_code"):
                for _, row in df.iterrows():
                    billed = _safe_float(row.get(col_map.get("billed_amount", ""), 0))
                    line_items.append({
                        "ndc_code": (lambda v: v.zfill(11) if v and v.isdigit() else v or None)(str(row.get(col_map.get("ndc_code", ""), "")).replace("-", "").strip()),
                        "drug_name": str(row.get(col_map.get("drug_name", ""), "")).strip(),
                        "generic_name": str(row.get(col_map.get("generic_name", ""), "")).strip() or None,
                        "brand_or_generic": str(row.get(col_map.get("brand_or_generic", ""), "unknown")).strip().lower(),
                        "days_supply": _safe_int(row.get(col_map.get("days_supply", ""), None)),
                        "quantity": _safe_float(row.get(col_map.get("quantity", ""), 1)),
                        "billed_amount": billed,
                        "plan_paid": _safe_float(row.get(col_map.get("plan_paid", ""), None)),
                        "member_paid": _safe_float(row.get(col_map.get("member_paid", ""), None)),
                        "therapeutic_class": str(row.get(col_map.get("therapeutic_class", ""), "")).strip() or None,
                        "is_specialty": None,
                        "fill_date": str(row.get(col_map.get("fill_date", ""), "")).strip() or None,
                        "hcpcs_code": str(row.get(col_map.get("hcpcs_code", ""), "")).strip() or None,
                    })
        except Exception as exc:
            print(f"[Pharmacy] CSV/Excel parse failed: {exc}")

    # ----- Stage 3: AI extraction fallback -----
    if not line_items:
        text = content.decode("utf-8", errors="replace")
        # Truncate to avoid token limits
        if len(text) > 50000:
            text = text[:50000]

        ai_result = _call_claude(PHARMACY_EXTRACTION_PROMPT, text, max_tokens=8192)
        if ai_result and ai_result.get("line_items"):
            line_items = ai_result["line_items"]
            plan_name = ai_result.get("plan_name")
            date_range = ai_result.get("date_range")

    if not line_items:
        raise HTTPException(
            status_code=400,
            detail="Could not extract pharmacy claims from this file. Please ensure it contains pharmacy claims data (NDC codes, drug names, amounts).",
        )

    # ----- Benchmark against NADAC + ASP -----
    nadac_lookup = _load_nadac_lookup()
    asp_lookup = _load_asp_lookup()

    total_billed = 0.0
    total_plan_paid = 0.0
    total_member_paid = 0.0
    generic_count = 0
    brand_count = 0
    specialty_spend = 0.0
    total_spread = 0.0
    spread_count = 0

    enriched_items = []
    for item in line_items:
        billed = _safe_float(item.get("billed_amount", 0))
        plan_paid = _safe_float(item.get("plan_paid", 0))
        member_paid = _safe_float(item.get("member_paid", 0))
        quantity = _safe_float(item.get("quantity", 1)) or 1.0

        total_billed += billed
        total_plan_paid += plan_paid
        total_member_paid += member_paid

        # Brand/generic classification
        bog = str(item.get("brand_or_generic", "unknown")).lower()
        if bog in ("generic", "g"):
            generic_count += 1
        elif bog in ("brand", "b"):
            brand_count += 1

        # Specialty detection
        drug_name = str(item.get("drug_name", ""))
        generic_name = str(item.get("generic_name", ""))
        therapeutic_class = str(item.get("therapeutic_class", ""))
        is_spec = _is_specialty(drug_name, generic_name, therapeutic_class, item.get("is_specialty"))
        if is_spec:
            specialty_spend += plan_paid

        # NADAC lookup
        ndc = str(item.get("ndc_code", "")).replace("-", "").strip()
        if ndc and ndc.isdigit():
            ndc = ndc.zfill(11)
        benchmark_cost = None
        benchmark_source = None  # "NADAC" or "Medicare ASP"
        spread = None

        if ndc and ndc in nadac_lookup:
            nadac_per_unit = nadac_lookup[ndc]
            benchmark_cost = round(nadac_per_unit * quantity, 2)
            benchmark_source = "NADAC"
            if plan_paid > 0 and benchmark_cost > 0:
                spread = round(plan_paid - benchmark_cost, 2)
                total_spread += spread
                spread_count += 1

        # ASP fallback — try if no NADAC match and drug is specialty/brand
        if benchmark_cost is None and asp_lookup:
            asp_match = None
            hcpcs = str(item.get("hcpcs_code", "")).strip().upper()
            if hcpcs and hcpcs in asp_lookup:
                asp_match = asp_lookup[hcpcs]
            elif is_spec or bog in ("brand", "b"):
                # Fuzzy match by drug name against ASP short_description
                asp_match = _fuzzy_asp_match(drug_name, generic_name, asp_lookup)
            if asp_match:
                benchmark_cost = round(asp_match["payment_limit"] * quantity, 2)
                benchmark_source = "Medicare ASP"
                if plan_paid > 0 and benchmark_cost > 0:
                    spread = round(plan_paid - benchmark_cost, 2)
                    total_spread += spread
                    spread_count += 1

        # Determine benchmark label for drugs with no match
        benchmark_note = None
        if benchmark_cost is None:
            if is_spec or bog in ("brand", "b"):
                benchmark_note = "pbm_pricing"
            else:
                benchmark_note = "no_benchmark"

        enriched_items.append({
            **item,
            "is_specialty": is_spec,
            "benchmark_cost": benchmark_cost,
            "benchmark_source": benchmark_source,
            "benchmark_note": benchmark_note,
            "spread": spread,
            "spread_flagged": spread is not None and benchmark_cost and spread > (benchmark_cost * 0.20),
        })

    # ----- Build analysis sections -----
    total_claims = len(enriched_items)
    generic_rate = round((generic_count / total_claims) * 100, 1) if total_claims > 0 else 0
    specialty_pct = round((specialty_spend / total_plan_paid) * 100, 1) if total_plan_paid > 0 else 0

    # Top drugs by plan paid
    sorted_by_paid = sorted(enriched_items, key=lambda x: _safe_float(x.get("plan_paid", 0)), reverse=True)
    top_drugs = sorted_by_paid[:10]

    # Generic opportunity: brand drugs that likely have generic equivalents
    generic_opportunity = [
        item for item in enriched_items
        if str(item.get("brand_or_generic", "")).lower() == "brand"
        and item.get("generic_name")
        and not _is_specialty(
            str(item.get("drug_name", "")),
            str(item.get("generic_name", "")),
            str(item.get("therapeutic_class", "")),
        )
    ]
    # Deduplicate by drug_name and sum
    generic_opp_map = {}
    for item in generic_opportunity:
        key = str(item.get("drug_name", "")).lower()
        if key not in generic_opp_map:
            generic_opp_map[key] = {
                "drug_name": item.get("drug_name"),
                "generic_name": item.get("generic_name"),
                "total_plan_paid": 0,
                "claim_count": 0,
                "estimated_generic_savings": 0,
            }
        paid = _safe_float(item.get("plan_paid", 0))
        generic_opp_map[key]["total_plan_paid"] += paid
        generic_opp_map[key]["claim_count"] += 1
        # Estimate 70% savings switching to generic
        generic_opp_map[key]["estimated_generic_savings"] += round(paid * 0.70, 2)

    generic_opp_list = sorted(generic_opp_map.values(), key=lambda x: x["total_plan_paid"], reverse=True)

    # Specialty drugs
    specialty_drugs = [
        {
            "drug_name": item.get("drug_name"),
            "generic_name": item.get("generic_name"),
            "plan_paid": _safe_float(item.get("plan_paid", 0)),
            "billed_amount": _safe_float(item.get("billed_amount", 0)),
            "pct_of_total": round((_safe_float(item.get("plan_paid", 0)) / total_plan_paid) * 100, 1) if total_plan_paid > 0 else 0,
            "therapeutic_class": item.get("therapeutic_class"),
        }
        for item in enriched_items if item.get("is_specialty")
    ]
    specialty_drugs = sorted(specialty_drugs, key=lambda x: x["plan_paid"], reverse=True)

    # Benchmarks
    generic_benchmark = 80.0  # industry standard
    specialty_benchmark_low = 15.0
    specialty_benchmark_high = 20.0

    # PMPM estimate (assume ~250 members for mid-market employer)
    estimated_members = 250
    pmpm = round(total_plan_paid / estimated_members, 2) if total_plan_paid > 0 else 0

    analysis = {
        "summary": {
            "total_claims": total_claims,
            "total_billed": round(total_billed, 2),
            "total_plan_paid": round(total_plan_paid, 2),
            "total_member_paid": round(total_member_paid, 2),
            "generic_rate": generic_rate,
            "specialty_spend_pct": specialty_pct,
            "plan_name": plan_name,
            "date_range": date_range,
        },
        "top_drugs": [
            {
                "drug_name": d.get("drug_name"),
                "generic_name": d.get("generic_name"),
                "brand_or_generic": d.get("brand_or_generic"),
                "quantity": d.get("quantity"),
                "plan_paid": _safe_float(d.get("plan_paid", 0)),
                "benchmark_cost": d.get("benchmark_cost"),
                "benchmark_source": d.get("benchmark_source"),
                "benchmark_note": d.get("benchmark_note"),
                "spread": d.get("spread"),
                "spread_flagged": d.get("spread_flagged"),
                "is_specialty": d.get("is_specialty"),
            }
            for d in top_drugs
        ],
        "generic_opportunity": generic_opp_list[:10],
        "specialty_drugs": specialty_drugs,
        "benchmarks": {
            "generic_rate": generic_rate,
            "generic_benchmark": generic_benchmark,
            "generic_rate_status": "good" if generic_rate >= generic_benchmark else "below",
            "specialty_spend_pct": specialty_pct,
            "specialty_benchmark_low": specialty_benchmark_low,
            "specialty_benchmark_high": specialty_benchmark_high,
            "specialty_status": "good" if specialty_pct <= specialty_benchmark_high else "high",
            "pmpm_estimate": pmpm,
        },
        "pbm_spread_estimate": round(total_spread, 2) if spread_count > 0 else None,
        "therapeutic_alternatives": None,  # Future Option B hook
    }

    # ----- Save to Supabase -----
    try:
        sb = _get_supabase()
        sb.table("pharmacy_benchmarks").insert({
            "file_name": filename,
            "total_claims": total_claims,
            "total_billed": round(total_billed, 2),
            "total_plan_paid": round(total_plan_paid, 2),
            "generic_rate": generic_rate,
            "specialty_spend_pct": specialty_pct,
            "analysis_json": analysis,
            "pbm_spread": round(total_spread, 2) if spread_count > 0 else None,
        }).execute()
    except Exception as exc:
        print(f"[Pharmacy] Failed to save results: {exc}")

    return analysis


# ---------------------------------------------------------------------------
# NADAC lookup helper
# ---------------------------------------------------------------------------

def _load_nadac_lookup() -> dict:
    """Load NADAC per-unit costs from Supabase into a dict keyed by NDC.

    Supabase defaults to 1,000 rows per query, so we paginate in batches
    to ensure we load the full dataset (~30k rows).
    """
    try:
        sb = _get_supabase()
        lookup = {}
        offset = 0
        batch_size = 1000
        while True:
            result = sb.table("pharmacy_nadac").select("ndc_code, nadac_per_unit").range(offset, offset + batch_size - 1).execute()
            if not result.data:
                break
            for row in result.data:
                ndc = str(row.get("ndc_code", "")).replace("-", "").strip()
                if ndc and ndc.isdigit():
                    ndc = ndc.zfill(11)
                val = row.get("nadac_per_unit")
                if ndc and val is not None:
                    lookup[ndc] = float(val)
            offset += batch_size
        print(f"[Pharmacy] NADAC lookup loaded {len(lookup)} entries")
        return lookup
    except Exception as exc:
        print(f"[Pharmacy] NADAC lookup failed: {exc}")
        return {}


# ---------------------------------------------------------------------------
# ASP lookup helper
# ---------------------------------------------------------------------------

def _load_asp_lookup() -> dict:
    """Load Medicare Part B ASP payment limits from Supabase.

    Returns dict keyed by HCPCS code, with value containing
    payment_limit and short_description for fuzzy matching.
    Paginates in batches of 1000 (same as NADAC).
    """
    try:
        sb = _get_supabase()
        lookup = {}
        offset = 0
        batch_size = 1000
        while True:
            result = sb.table("pharmacy_asp").select(
                "hcpcs_code, short_description, dosage, payment_limit"
            ).range(offset, offset + batch_size - 1).execute()
            if not result.data:
                break
            for row in result.data:
                code = str(row.get("hcpcs_code", "")).strip().upper()
                limit_val = row.get("payment_limit")
                if code and limit_val is not None:
                    lookup[code] = {
                        "hcpcs_code": code,
                        "short_description": str(row.get("short_description", "") or "").lower(),
                        "dosage": row.get("dosage"),
                        "payment_limit": float(limit_val),
                    }
            offset += batch_size
        print(f"[Pharmacy] ASP lookup loaded {len(lookup)} entries")
        return lookup
    except Exception as exc:
        print(f"[Pharmacy] ASP lookup failed (table may not exist yet): {exc}")
        return {}


def _fuzzy_asp_match(drug_name: str, generic_name: str, asp_lookup: dict) -> Optional[dict]:
    """Try to match a drug name against ASP short_description.

    Returns the ASP entry if a reasonable match is found, else None.
    Uses simple substring matching on normalized drug names.
    """
    if not drug_name and not generic_name:
        return None

    # Normalize search terms
    names_to_try = []
    if drug_name:
        # Extract the first word (brand name) — e.g. "Humira 40mg" → "humira"
        first_word = drug_name.strip().split()[0].lower() if drug_name.strip() else ""
        if first_word and len(first_word) >= 3:
            names_to_try.append(first_word)
        names_to_try.append(drug_name.strip().lower())
    if generic_name:
        first_word = generic_name.strip().split()[0].lower() if generic_name.strip() else ""
        if first_word and len(first_word) >= 3:
            names_to_try.append(first_word)

    # Search ASP entries
    for name in names_to_try:
        for entry in asp_lookup.values():
            desc = entry["short_description"]
            if name in desc or desc in name:
                return entry

    return None


# ---------------------------------------------------------------------------
# Column auto-mapping for CSV/Excel
# ---------------------------------------------------------------------------

COLUMN_ALIASES = {
    "ndc_code": ["ndc_code", "ndc", "ndc_number", "national_drug_code"],
    "hcpcs_code": ["hcpcs_code", "hcpcs", "j_code", "jcode", "procedure_code"],
    "drug_name": ["drug_name", "medication", "medication_name", "drug", "product_name", "brand_name"],
    "generic_name": ["generic_name", "generic", "generic_drug_name"],
    "brand_or_generic": ["brand_or_generic", "brand_generic", "type", "drug_type", "brand/generic"],
    "days_supply": ["days_supply", "days", "supply_days", "day_supply"],
    "quantity": ["quantity", "qty", "units", "count"],
    "billed_amount": ["billed_amount", "billed", "charge", "charge_amount", "total_charge"],
    "plan_paid": ["plan_paid", "paid_amount", "plan_pay", "insurance_paid", "amount_paid", "paid"],
    "member_paid": ["member_paid", "patient_paid", "copay", "patient_pay", "member_cost", "member_responsibility"],
    "therapeutic_class": ["therapeutic_class", "drug_class", "class", "therapy_class", "category"],
    "fill_date": ["fill_date", "date_filled", "service_date", "date", "dispense_date", "rx_date"],
}


def _auto_map_columns(columns: list) -> dict:
    """Auto-map incoming column names to standard field names."""
    mapping = {}
    col_lower = {c: c for c in columns}

    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            for orig_col in columns:
                if orig_col.lower().replace(" ", "_") == alias:
                    mapping[field] = orig_col
                    break
            if field in mapping:
                break

    return mapping


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _safe_float(value) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def _safe_int(value):
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None
