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
from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel

from routers.employer_shared import (
    _get_supabase, _call_claude, check_rate_limit, assign_pricing_tier,
    EMPLOYER_PRICE_TIERS, _check_subscription,
)
from routers.benchmark import resolve_locality, lookup_rate
from utils.parse_835 import parse_835
from utils.email import send_email

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
# GET /pricing-tiers — expose tier details to frontend
# ---------------------------------------------------------------------------

@router.get("/pricing-tiers")
async def employer_pricing_tiers():
    """Return value-tiered pricing info for frontend display."""
    return {
        "tiers": {
            key: {
                "label": t["label"],
                "price_monthly": t["price_monthly"],
                "description": t["description"],
                "max_annual_excess": t["max_annual_excess"],
            }
            for key, t in EMPLOYER_PRICE_TIERS.items()
        },
        "guarantee": "If your claims analysis doesn't identify at least 3x your subscription cost in annual excess spend, we'll refund your first 3 months.",
    }


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

    # --- Free trial enforcement: unlimited use for 30 days from first upload ---
    if email:
        sub_info = _check_subscription(email)
        if not sub_info["active"]:
            sb = _get_supabase()
            from datetime import datetime, timezone, timedelta
            # Find user's earliest claims upload to determine trial start
            first_upload = (
                sb.table("employer_claims_uploads")
                .select("created_at")
                .eq("email", email)
                .order("created_at", desc=False)
                .limit(1)
                .execute()
            )
            if first_upload.data:
                trial_start = datetime.fromisoformat(first_upload.data[0]["created_at"].replace("Z", "+00:00"))
                trial_end = trial_start + timedelta(days=30)
                now = datetime.now(timezone.utc)
                if now > trial_end:
                    raise HTTPException(
                        status_code=402,
                        detail="Your 30-day free trial has ended. Subscribe to continue using claims analysis.",
                    )

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
                        "sample_rows": df.head(3).fillna("").astype(str).to_dict(orient="records"),
                        "hint": "Manual column mapping required",
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
        svc_date = str(row.get("service_date", "")).strip() or None

        # Look up CMS Medicare rate (date-aware)
        rate_val, source, _, _, rate_note = lookup_rate(cpt, "CPT", carrier, locality, date_of_service=svc_date)

        line = {
            "cpt_code": cpt,
            "paid_amount": paid,
            "billed_amount": billed,
            "medicare_rate": rate_val,
            "medicare_source": source if rate_val else None,
            "rate_note": rate_note,
            "ratio": None,
            "flag": None,
            "excess_amount": None,
        }

        if rate_val and rate_val > 0 and paid > 0:
            ratio = round(paid / rate_val, 2)
            line["ratio"] = ratio
            if ratio > 3.0:
                line["flag"] = "SEVERE"
                excess = round(paid - (rate_val * 2), 2)
                line["excess_amount"] = excess
                total_excess_2x += excess
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

    # --- Top flagged CPT (by total excess dollars) ---
    excess_by_cpt = {}
    for r in results:
        ex = r.get("excess_amount") or 0
        if ex > 0:
            excess_by_cpt[r["cpt_code"]] = excess_by_cpt.get(r["cpt_code"], 0) + ex
    top_flagged_cpt = max(excess_by_cpt, key=excess_by_cpt.get) if excess_by_cpt else None
    top_flagged_excess = round(excess_by_cpt.get(top_flagged_cpt, 0), 2) if top_flagged_cpt else 0.0

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
            "Do not recommend specific vendors. "
            "Use neutral, factual language — avoid phrases like 'your plan overpaid', 'overcharged', or 'immediately review'. "
            "Instead describe what the data shows: costs above benchmark, procedures with elevated markups, areas worth examining. "
            "End with one sentence about what this finding suggests the employer consider — framed as an opportunity, not an accusation.\n\n"
            f"Claims analyzed: {len(results)}\n"
            f"Total paid: ${total_paid:,.0f}\n"
            f"Excess vs 2x Medicare benchmark: ${total_excess_2x:,.0f}\n"
            f"Top findings:\n" + "\n".join(top_findings_lines) + "\n\n"
            "Write only the summary paragraph. No headers, no bullet points, no preamble."
        )

        narrative = _generate_narrative(narrative_prompt)
    except Exception as exc:
        print(f"[Employer Claims] Narrative generation failed (non-fatal): {exc}")

    # --- Action plan ---
    action_plan = None
    try:
        action_plan_prompt = (
            "You are a benefits advisor writing for an HR director or small business owner. "
            "Based on these claims analysis results, write a numbered action plan with exactly 3 steps. "
            "Each step must be a specific, concrete ask — either 'Ask your broker: [exact question]' "
            "or 'Before your renewal: [specific preparation task]' or 'Ask your carrier: [exact question to include in writing]'. "
            "Do not give generic advice. Reference the actual findings. "
            "Write for someone who is not a benefits expert. Plain English only. No jargon. "
            "Format: Return exactly 3 lines, each starting with a number (1., 2., 3.) followed by the action. "
            "No headers, no extra text, no preamble.\n\n"
            f"Analysis summary:\n"
            f"- Claims analyzed: {len(results)}\n"
            f"- Total paid: ${total_paid:,.0f}\n"
            f"- Excess vs 2x Medicare: ${total_excess_2x:,.0f}\n"
            f"- Flagged claims: {len([r for r in results if r.get('flag')])}\n"
            f"- Top flagged procedure: CPT {top_flagged_cpt} (${top_flagged_excess:,.0f} excess)\n"
        )
        action_result = _call_claude(
            system_prompt="You write specific, actionable guidance for HR directors reviewing their health plan claims data. Return plain text only, not JSON.",
            user_content=action_plan_prompt,
            max_tokens=400,
        )
        # _call_claude returns parsed JSON or None; for plain text we need raw
        # Since _call_claude parses JSON, try to get it from the response
        if action_result is None:
            # Try raw text approach via _generate_narrative
            raw = _generate_narrative(action_plan_prompt)
            if raw:
                lines = [l.strip() for l in raw.split("\n") if l.strip() and l.strip()[0].isdigit()]
                if lines:
                    action_plan = [l.lstrip("123456789. ").strip() for l in lines[:3]]
    except Exception as exc:
        print(f"[Claims Action Plan] Non-fatal: {exc}")

    # --- Level 2 analytics (835 EDI only) ---
    level2 = None
    try:
        level2 = _run_level2_analytics(df, results)
    except Exception as exc:
        print(f"[Employer Claims] Level 2 analytics failed (non-fatal): {exc}")

    # Assign value-based pricing tier from annualized excess
    annualized_excess = total_excess_2x * 12
    pricing_tier = assign_pricing_tier(annualized_excess)
    tier_info = EMPLOYER_PRICE_TIERS[pricing_tier]

    # Collect any rate year notes for the UI
    rate_notes = list({r["rate_note"] for r in results if r.get("rate_note")})
    rate_year_note = rate_notes[0] if len(rate_notes) == 1 else (
        "; ".join(rate_notes) if rate_notes else None
    )

    response = {
        "summary": summary,
        "narrative": narrative,
        "action_plan": action_plan,
        "line_items": results[:500],  # Cap at 500 for response size
        "column_mapping": mapping,
        "total_lines_analyzed": len(results),
        "source_format": source_format,
        "pricing_tier": pricing_tier,
        "pricing_tier_label": tier_info["label"],
        "pricing_tier_price": tier_info["price_monthly"],
        "annualized_excess": round(annualized_excess, 2),
        "level2": level2,
        "rate_year_note": rate_year_note,
    }

    # --- Persist to Supabase ---
    session_id = None
    try:
        sb = _get_supabase()
        insert_result = sb.table("employer_claims_uploads").insert({
            "email": email,
            "filename_original": filename,
            "total_claims": len(results),
            "total_paid": float(total_paid),
            "total_excess_2x": float(total_excess_2x),
            "top_flagged_cpt": top_flagged_cpt,
            "top_flagged_excess": float(top_flagged_excess),
            "column_mapping_json": mapping,
            "results_json": {**summary, "line_items": results[:500], "level2": level2},
        }).execute()
        if insert_result.data:
            session_id = insert_result.data[0].get("id")
    except Exception as exc:
        print(f"[Employer Claims] Failed to save session: {exc}")

    response["session_id"] = session_id
    return response


# ---------------------------------------------------------------------------
# POST /rbp-calculate — Reference-Based Pricing calculator
# ---------------------------------------------------------------------------

CPT_CATEGORIES = {
    "E&M": (99000, 99999),
    "Surgery": (10000, 69999),
    "Radiology": (70000, 79999),
    "Lab": (80000, 89999),
    "Medicine": (90000, 98999),
}


def _cpt_category(cpt_code: str) -> str:
    """Map a CPT code to a category name."""
    try:
        num = int(re.sub(r"[^0-9]", "", cpt_code))
    except (ValueError, TypeError):
        return "Other"
    for cat, (lo, hi) in CPT_CATEGORIES.items():
        if lo <= num <= hi:
            return cat
    return "Other"


class RBPRequest(BaseModel):
    claims_session_id: str
    medicare_multiplier: float = 1.40
    zip_code: Optional[str] = None


@router.post("/rbp-calculate")
async def employer_rbp_calculate(body: RBPRequest, request: Request):
    """Calculate reference-based pricing savings against a stored claims session."""
    check_rate_limit(request, max_requests=20)

    sb = _get_supabase()

    # --- Subscription required for RBP calculator ---
    session_check = sb.table("employer_claims_uploads").select("email").eq("id", body.claims_session_id).limit(1).execute()
    if session_check.data:
        session_email = session_check.data[0].get("email", "")
        if session_email:
            sub_info = _check_subscription(session_email, sb)
            if not sub_info["active"]:
                raise HTTPException(
                    status_code=402,
                    detail="RBP calculator requires an active subscription.",
                )

    # Load stored claims session
    result = sb.table("employer_claims_uploads").select("*").eq("id", body.claims_session_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Claims session not found")

    session = result.data[0]
    results_json = session.get("results_json", {})
    line_items = results_json.get("line_items", [])
    if not line_items:
        raise HTTPException(status_code=400, detail="No line items found in stored session")

    # Resolve locality — use provided zip or fall back to session locality
    zip_code = body.zip_code
    if not zip_code:
        locality_info = results_json.get("locality", {})
        zip_code = locality_info.get("zip_code")
    if not zip_code:
        raise HTTPException(status_code=400, detail="ZIP code required (not found in session)")

    carrier, locality = resolve_locality(zip_code)
    if not carrier or not locality:
        raise HTTPException(status_code=400, detail=f"Could not resolve locality for ZIP {zip_code}")

    multiplier = body.medicare_multiplier

    # Analyze each line item
    rbp_lines = []
    total_actual = 0.0
    total_rbp = 0.0
    category_data = {}  # {category: {actual, rbp, count}}

    for item in line_items:
        cpt = item.get("cpt_code", "")
        actual_paid = item.get("paid_amount") or 0
        if not cpt or actual_paid <= 0:
            continue

        medicare_rate = item.get("medicare_rate")
        if medicare_rate is None or medicare_rate <= 0:
            # Re-lookup if not stored
            rate_val, _, _, _, _ = lookup_rate(cpt, "CPT", carrier, locality)
            medicare_rate = rate_val

        if not medicare_rate or medicare_rate <= 0:
            continue

        rbp_rate = round(medicare_rate * multiplier, 2)
        savings = round(actual_paid - rbp_rate, 2)
        savings_pct = round(savings / actual_paid * 100, 1) if actual_paid > 0 else 0

        rbp_lines.append({
            "cpt_code": cpt,
            "actual_paid": actual_paid,
            "medicare_rate": medicare_rate,
            "rbp_rate": rbp_rate,
            "rbp_savings": savings,
            "savings_pct": savings_pct,
        })

        total_actual += actual_paid
        total_rbp += rbp_rate

        cat = _cpt_category(cpt)
        if cat not in category_data:
            category_data[cat] = {"actual": 0, "rbp": 0, "count": 0}
        category_data[cat]["actual"] += actual_paid
        category_data[cat]["rbp"] += rbp_rate
        category_data[cat]["count"] += 1

    total_savings = round(total_actual - total_rbp, 2)
    savings_pct_overall = round(total_savings / total_actual * 100, 1) if total_actual > 0 else 0

    # Top 10 by savings
    top_procedures = sorted(rbp_lines, key=lambda x: x["rbp_savings"], reverse=True)[:10]

    # Aggregate top procedures by CPT
    cpt_agg = {}
    for line in rbp_lines:
        cpt = line["cpt_code"]
        if cpt not in cpt_agg:
            cpt_agg[cpt] = {"total_actual": 0, "total_rbp": 0, "total_savings": 0, "count": 0, "rbp_rate": line["rbp_rate"], "medicare_rate": line["medicare_rate"]}
        cpt_agg[cpt]["total_actual"] += line["actual_paid"]
        cpt_agg[cpt]["total_rbp"] += line["rbp_rate"]
        cpt_agg[cpt]["total_savings"] += line["rbp_savings"]
        cpt_agg[cpt]["count"] += 1

    top_by_total_savings = sorted(cpt_agg.items(), key=lambda x: x[1]["total_savings"], reverse=True)[:10]
    top_procedures_agg = [
        {
            "cpt_code": cpt,
            "actual_paid_avg": round(d["total_actual"] / d["count"], 2),
            "rbp_rate": d["rbp_rate"],
            "savings_per_claim": round(d["total_savings"] / d["count"], 2),
            "claims_count": d["count"],
            "total_savings": round(d["total_savings"], 2),
        }
        for cpt, d in top_by_total_savings
    ]

    # Category breakdown
    categories = sorted(
        [
            {
                "category": cat,
                "actual_paid": round(d["actual"], 2),
                "rbp_equivalent": round(d["rbp"], 2),
                "savings": round(d["actual"] - d["rbp"], 2),
                "savings_pct": round((d["actual"] - d["rbp"]) / d["actual"] * 100, 1) if d["actual"] > 0 else 0,
                "claim_count": d["count"],
            }
            for cat, d in category_data.items()
        ],
        key=lambda x: x["savings"],
        reverse=True,
    )

    # AI narrative
    rbp_narrative = None
    try:
        multiplier_pct = int(multiplier * 100)
        top_cat = categories[0]["category"] if categories else "N/A"
        narrative_prompt = (
            f"You are a healthcare benefits consultant. Write a 3-4 sentence summary explaining "
            f"what reference-based pricing at {multiplier_pct}% of Medicare would have meant for "
            f"this employer's claims. Be specific about total savings and top categories. "
            f"End with one sentence about implementation considerations. Write for a CFO. "
            f"No jargon, no bullet points.\n\n"
            f"Total claims analyzed: {len(rbp_lines)}\n"
            f"Total actual paid: ${total_actual:,.0f}\n"
            f"Total RBP equivalent: ${total_rbp:,.0f}\n"
            f"Total potential savings: ${total_savings:,.0f} ({savings_pct_overall}%)\n"
            f"Top savings category: {top_cat}\n"
            f"Top 3 procedures by savings: "
            + ", ".join(f"CPT {p['cpt_code']} (${p['total_savings']:,.0f})" for p in top_procedures_agg[:3])
            + "\n\nWrite only the summary paragraph."
        )
        rbp_narrative = _generate_narrative(narrative_prompt)
    except Exception as exc:
        print(f"[RBP Calculate] Narrative failed (non-fatal): {exc}")

    # Eligibility assessment
    eligibility = None
    try:
        # Try to get employee count and company info from subscription
        email = session.get("email", "")
        employee_count = 0
        plan_type = ""
        company_name = ""
        if email:
            sub_result = sb.table("employer_subscriptions").select("*").eq("email", email).order(
                "created_at", desc=True
            ).limit(1).execute()
            if sub_result.data:
                sub = sub_result.data[0]
                employee_count = sub.get("employee_count") or 0
                company_name = sub.get("company_name") or ""
        state = _zip_to_state(zip_code)
        eligibility = _assess_rbp_eligibility(employee_count, state, plan_type, multiplier)
        eligibility["company_name"] = company_name
    except Exception as exc:
        print(f"[RBP Calculate] Eligibility assessment failed (non-fatal): {exc}")

    # Assign value-based pricing tier from session's annualized excess
    session_excess = session.get("total_excess_2x") or 0
    annualized_excess = session_excess * 12
    pricing_tier = assign_pricing_tier(annualized_excess)
    tier_info = EMPLOYER_PRICE_TIERS[pricing_tier]

    return {
        "total_actual_paid": round(total_actual, 2),
        "total_rbp_equivalent": round(total_rbp, 2),
        "total_potential_savings": total_savings,
        "savings_pct_overall": savings_pct_overall,
        "medicare_multiplier": multiplier,
        "claims_analyzed": len(rbp_lines),
        "top_procedures": top_procedures_agg,
        "categories": categories,
        "rbp_narrative": rbp_narrative,
        "eligibility": eligibility,
        "pricing_tier": pricing_tier,
        "pricing_tier_label": tier_info["label"],
        "pricing_tier_price": tier_info["price_monthly"],
        "annualized_excess": round(annualized_excess, 2),
    }


# ---------------------------------------------------------------------------
# RBP eligibility assessment
# ---------------------------------------------------------------------------

def _zip_to_state(zip_code: str) -> str:
    """Look up state from zip_locality.csv for a ZIP code."""
    try:
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "zip_locality.csv")
        df = pd.read_csv(csv_path, usecols=["zip_code", "state"], dtype=str, nrows=50000)
        df["zip_code"] = df["zip_code"].str.strip().str.zfill(5)
        match = df[df["zip_code"] == zip_code.strip().zfill(5)]
        if not match.empty:
            return match.iloc[0]["state"]
    except Exception:
        pass
    return ""


def _assess_rbp_eligibility(employee_count: int, state: str, plan_type: str, multiplier: float) -> dict:
    """Assess RBP viability for this employer."""
    criteria = []

    # Criterion 1: Size
    if employee_count >= 250:
        size_status = "green"
        size_note = f"{employee_count} employees — strong fit for RBP"
    elif employee_count >= 150:
        size_status = "yellow"
        size_note = f"{employee_count} employees — viable but administrative burden is higher at this size"
    elif employee_count > 0:
        size_status = "red"
        size_note = f"{employee_count} employees — RBP is typically not cost-effective below 150 lives"
    else:
        size_status = "yellow"
        size_note = "Employee count unknown — confirm your headcount to assess RBP viability"

    criteria.append({"criterion": "Company size", "status": size_status, "note": size_note})

    # Criterion 2: Self-insured status
    if plan_type and "self" in plan_type.lower():
        ins_status = "green"
        ins_note = "Already self-insured — RBP can be implemented without changing funding structure"
    elif plan_type and any(c in plan_type.lower() for c in ["cigna", "aetna", "united", "bcbs", "anthem", "humana"]):
        ins_status = "yellow"
        ins_note = "Fully-insured plan — moving to self-insurance is a prerequisite for RBP. Most employers your size qualify."
    else:
        ins_status = "yellow"
        ins_note = "Plan funding type unknown — confirm whether you are fully-insured or self-insured with your broker"

    criteria.append({"criterion": "Plan funding type", "status": ins_status, "note": ins_note})

    # Criterion 3: Geographic concentration
    if state:
        geo_status = "green"
        geo_note = f"Employees in {state} — geographically concentrated workforce simplifies RBP vendor relationships with local hospitals"
    else:
        geo_status = "yellow"
        geo_note = "Geographic concentration unknown — RBP works best when employees are concentrated in one or two states"

    criteria.append({"criterion": "Geographic concentration", "status": geo_status, "note": geo_note})

    # Overall verdict
    reds = sum(1 for c in criteria if c["status"] == "red")
    yellows = sum(1 for c in criteria if c["status"] == "yellow")

    if reds == 0 and yellows <= 1:
        verdict = "strong_fit"
        verdict_text = "RBP looks like a strong fit based on your profile."
    elif reds == 0:
        verdict = "possible_fit"
        verdict_text = "RBP may be viable — a few factors to resolve with your broker first."
    elif reds == 1 and employee_count >= 150:
        verdict = "borderline"
        verdict_text = "RBP has meaningful barriers for your situation — review the criteria below before pursuing."
    else:
        verdict = "poor_fit"
        verdict_text = "RBP is likely not the right lever right now — see alternative savings options below."

    return {
        "verdict": verdict,
        "verdict_text": verdict_text,
        "criteria": criteria,
        "alternative_levers": [] if verdict in ("strong_fit", "possible_fit") else [
            "Pharmacy carve-out — separate your pharmacy benefit for transparent PBM pricing",
            "Reference pricing for specific high-cost procedures (imaging, labs)",
            "Center-of-excellence routing for orthopedic and cardiac procedures",
            "Plan design optimization — our scorecard identified specific gaps",
        ],
    }


# ---------------------------------------------------------------------------
# POST /rbp-pdf — Generate broker summary PDF
# ---------------------------------------------------------------------------

class RBPPdfRequest(BaseModel):
    total_actual_paid: float
    total_rbp_equivalent: float
    total_potential_savings: float
    savings_pct_overall: float
    medicare_multiplier: float
    claims_analyzed: int
    top_procedures: list = []
    categories: list = []
    rbp_narrative: Optional[str] = None
    eligibility: Optional[dict] = None
    company_name: Optional[str] = None


@router.post("/rbp-pdf")
async def employer_rbp_pdf(body: RBPPdfRequest, request: Request):
    """Generate a one-page broker summary PDF from RBP results."""
    check_rate_limit(request, max_requests=20)

    from datetime import date
    from fastapi.responses import Response

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        raise HTTPException(status_code=500, detail="PDF generation library not available")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch)

    styles = getSampleStyleSheet()
    navy = HexColor("#1B3A5C")
    teal = HexColor("#0D7377")
    light_gray = HexColor("#f7f9fc")

    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, textColor=navy, spaceAfter=4)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], fontSize=9, textColor=HexColor("#64748b"), spaceAfter=12)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=12, textColor=navy, spaceAfter=6, spaceBefore=14)
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, textColor=HexColor("#1e293b"), leading=14, spaceAfter=4)
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=8, textColor=HexColor("#64748b"), leading=10)
    bold_style = ParagraphStyle("Bold", parent=styles["Normal"], fontSize=10, textColor=navy, leading=14, spaceAfter=2)

    elements = []

    # Header
    company = body.company_name or "Employer"
    multiplier_pct = int(body.medicare_multiplier * 100)
    elements.append(Paragraph("Parity Employer — Reference-Based Pricing Analysis", title_style))
    elements.append(Paragraph(
        f"{company}  |  Generated {date.today().strftime('%B %d, %Y')}  |  CONFIDENTIAL — For Broker Discussion",
        subtitle_style
    ))

    # Section 1: Savings Summary
    elements.append(Paragraph("Savings Summary", section_style))
    annual_actual = body.total_actual_paid * 12
    annual_rbp = body.total_rbp_equivalent * 12
    annual_savings = body.total_potential_savings * 12

    summary_data = [
        ["Current annual spend (est.)", f"${annual_actual:,.0f}"],
        [f"RBP equivalent at {multiplier_pct}% of Medicare", f"${annual_rbp:,.0f}"],
        ["Potential annual savings", f"${annual_savings:,.0f} ({body.savings_pct_overall}%)"],
    ]
    summary_table = Table(summary_data, colWidths=[3.5 * inch, 2.5 * inch])
    summary_table.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (-1, -1), navy),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("TEXTCOLOR", (1, 2), (1, 2), teal),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, navy),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8))

    # Section 2: Top 3 categories
    top_cats = (body.categories or [])[:3]
    if top_cats:
        elements.append(Paragraph("Top Categories by Savings", section_style))
        cat_data = [["Category", "Actual", "RBP Equivalent", "Savings"]]
        for c in top_cats:
            cat_data.append([
                c.get("category", ""),
                f"${c.get('actual_paid', 0):,.0f}",
                f"${c.get('rbp_equivalent', 0):,.0f}",
                f"${c.get('savings', 0):,.0f}",
            ])
        cat_table = Table(cat_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e2e8f0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), navy),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.25, HexColor("#e2e8f0")),
        ]))
        elements.append(cat_table)
        elements.append(Spacer(1, 8))

    # Section 3: Eligibility Assessment
    elig = body.eligibility
    if elig and elig.get("criteria"):
        elements.append(Paragraph("Eligibility Assessment", section_style))
        elements.append(Paragraph(elig.get("verdict_text", ""), bold_style))
        for c in elig["criteria"]:
            status = c.get("status", "yellow")
            symbol = {"green": "\u2713", "yellow": "\u26A0", "red": "\u2717"}.get(status, "?")
            elements.append(Paragraph(f"{symbol}  <b>{c['criterion']}</b>: {c['note']}", body_style))
        elements.append(Spacer(1, 8))

    # Section 4: Next Steps
    elements.append(Paragraph("Suggested Next Steps", section_style))
    steps = [
        "1. Share this analysis with your benefits broker",
        "2. Ask your broker: Are we currently self-insured or fully-insured?",
        "3. Request quotes from RBP-specialized TPAs (Imagine360, Firsthand, or your broker's preferred vendor)",
        "4. Request a full Parity Employer monitoring subscription to track savings over time",
    ]
    for s in steps:
        elements.append(Paragraph(s, body_style))
    elements.append(Spacer(1, 16))

    # Footer
    elements.append(Paragraph(
        f"Generated by Parity Employer · civicscale.ai · Data based on {body.claims_analyzed} claims",
        small_style
    ))
    elements.append(Paragraph(
        "This analysis is for informational purposes. Actual savings depend on plan design, employee behavior, and vendor implementation.",
        small_style
    ))

    doc.build(elements)
    pdf_bytes = buf.getvalue()
    buf.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="parity_rbp_analysis.pdf"'},
    )


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
    email: Optional[str] = Form(None),
):
    """Parse a carrier contract PDF and compare rates against CMS Medicare benchmarks."""
    check_rate_limit(request, max_requests=20)

    # --- Subscription required for contract parser ---
    if email:
        sub_info = _check_subscription(email)
        if not sub_info["active"]:
            raise HTTPException(
                status_code=402,
                detail="Contract parser requires an active subscription.",
            )

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
            rate_val, source, _, _, _ = lookup_rate(item["cpt_code"], "CPT", carrier, locality)
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
            rate_val, source, _, _, _ = lookup_rate(cpt, "CPT", carrier, locality)
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
        system="You are a concise healthcare benefits analyst. Use neutral, factual language. Never imply fraud or wrongdoing. Describe findings as benchmarking observations, not accusations.",
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
            "rendering_provider_name": item.get("rendering_provider_name", ""),
            "rendering_provider_npi": item.get("rendering_provider_npi", ""),
            "service_facility_name": item.get("service_facility_name", ""),
            "place_of_service": item.get("place_of_service", ""),
            "place_of_service_label": item.get("place_of_service_label", ""),
            "allowed_amount": item.get("allowed_amount", 0),
        })
    return pd.DataFrame(rows)


def _run_level2_analytics(df: pd.DataFrame, flagged_results: list) -> dict:
    """Run Level 2 analytics: provider variation, site of care, carrier rates, network leakage, denials.

    Requires 835 EDI data with rendering_provider_name field populated.
    Returns has_level2: False if provider data is missing (CSV uploads).
    """
    # Check if we have provider data (835 EDI only)
    has_provider_data = (
        "rendering_provider_name" in df.columns
        and df["rendering_provider_name"].notna().any()
        and (df["rendering_provider_name"] != "").any()
    )

    if not has_provider_data:
        return {
            "has_level2": False,
            "message": "Level 2 analysis requires 835 EDI format with provider data. CSV uploads support Level 1 Medicare benchmarking only.",
        }

    # --- A. Provider price variation ---
    provider_variation = {"flagged_cpts": [], "total_variation_opportunity": 0.0, "providers_analyzed": 0}
    try:
        providers_with_data = df[df["rendering_provider_name"] != ""]
        provider_variation["providers_analyzed"] = providers_with_data["rendering_provider_name"].nunique()

        # Group by CPT + provider, compute avg paid
        cpt_provider = (
            providers_with_data.groupby(["cpt_code", "rendering_provider_name"])
            .agg(avg_paid=("paid_amount", "mean"), claim_count=("paid_amount", "count"))
            .reset_index()
        )

        # Find CPTs with 2+ distinct providers
        cpt_provider_counts = cpt_provider.groupby("cpt_code")["rendering_provider_name"].nunique()
        multi_provider_cpts = cpt_provider_counts[cpt_provider_counts >= 2].index

        variations = []
        for cpt in multi_provider_cpts:
            cpt_data = cpt_provider[cpt_provider["cpt_code"] == cpt]
            min_row = cpt_data.loc[cpt_data["avg_paid"].idxmin()]
            max_row = cpt_data.loc[cpt_data["avg_paid"].idxmax()]

            if min_row["avg_paid"] > 0:
                ratio = round(max_row["avg_paid"] / min_row["avg_paid"], 2)
                if ratio > 1.5:
                    # Potential savings if all claims went to low-cost provider
                    total_at_high = providers_with_data[
                        (providers_with_data["cpt_code"] == cpt)
                        & (providers_with_data["rendering_provider_name"] == max_row["rendering_provider_name"])
                    ]["paid_amount"].sum()
                    count_at_high = len(providers_with_data[
                        (providers_with_data["cpt_code"] == cpt)
                        & (providers_with_data["rendering_provider_name"] == max_row["rendering_provider_name"])
                    ])
                    potential_savings = round(total_at_high - (min_row["avg_paid"] * count_at_high), 2)

                    variations.append({
                        "cpt_code": cpt,
                        "low_provider": {"name": min_row["rendering_provider_name"], "avg_paid": round(min_row["avg_paid"], 2)},
                        "high_provider": {"name": max_row["rendering_provider_name"], "avg_paid": round(max_row["avg_paid"], 2)},
                        "variation_ratio": ratio,
                        "potential_savings": max(potential_savings, 0),
                    })

        variations.sort(key=lambda x: x["potential_savings"], reverse=True)
        provider_variation["flagged_cpts"] = variations[:5]
        provider_variation["total_variation_opportunity"] = round(
            sum(v["potential_savings"] for v in variations), 2
        )
    except Exception as exc:
        print(f"[Level2] Provider variation analysis failed: {exc}")

    # --- B. Site of care analysis ---
    site_of_care = {"flagged_cpts": [], "total_site_opportunity": 0.0, "has_hospital_outpatient": False}
    try:
        if "place_of_service" in df.columns:
            hospital_pos = {"19", "22"}
            non_hospital_pos = {"11", "24"}

            df_with_pos = df[df["place_of_service"] != ""]
            if not df_with_pos.empty:
                df_hosp = df_with_pos[df_with_pos["place_of_service"].isin(hospital_pos)]
                df_non_hosp = df_with_pos[df_with_pos["place_of_service"].isin(non_hospital_pos)]

                site_of_care["has_hospital_outpatient"] = len(df_hosp) > 0

                if not df_hosp.empty and not df_non_hosp.empty:
                    hosp_cpts = set(df_hosp["cpt_code"].unique())
                    non_hosp_cpts = set(df_non_hosp["cpt_code"].unique())
                    shared_cpts = hosp_cpts & non_hosp_cpts

                    site_findings = []
                    for cpt in shared_cpts:
                        hosp_avg = df_hosp[df_hosp["cpt_code"] == cpt]["paid_amount"].mean()
                        non_hosp_avg = df_non_hosp[df_non_hosp["cpt_code"] == cpt]["paid_amount"].mean()

                        if non_hosp_avg > 0:
                            ratio = round(hosp_avg / non_hosp_avg, 2)
                            if ratio > 1.5:
                                hosp_count = len(df_hosp[df_hosp["cpt_code"] == cpt])
                                savings = round((hosp_avg - non_hosp_avg) * hosp_count, 2)
                                site_findings.append({
                                    "cpt_code": cpt,
                                    "hospital_avg": round(hosp_avg, 2),
                                    "non_hospital_avg": round(non_hosp_avg, 2),
                                    "ratio": ratio,
                                    "hospital_claims": hosp_count,
                                    "potential_savings": max(savings, 0),
                                })

                    site_findings.sort(key=lambda x: x["potential_savings"], reverse=True)
                    site_of_care["flagged_cpts"] = site_findings[:5]
                    site_of_care["total_site_opportunity"] = round(
                        sum(f["potential_savings"] for f in site_findings), 2
                    )
    except Exception as exc:
        print(f"[Level2] Site of care analysis failed: {exc}")

    # --- C. Carrier rate reconstruction ---
    carrier_rates = {"top_cpts": [], "avg_multiple_vs_medicare": 0.0}
    try:
        if "allowed_amount" in df.columns:
            # Use flagged_results which already have medicare_rate
            rate_lookup = {}
            for r in flagged_results:
                if r.get("medicare_rate") and r["medicare_rate"] > 0:
                    rate_lookup[r["cpt_code"]] = r["medicare_rate"]

            cpt_counts = df["cpt_code"].value_counts()
            high_volume_cpts = cpt_counts[cpt_counts >= 3].index

            rate_comparisons = []
            for cpt in high_volume_cpts:
                if cpt not in rate_lookup:
                    continue
                medicare_rate = rate_lookup[cpt]
                cpt_data = df[df["cpt_code"] == cpt]
                avg_allowed = cpt_data["allowed_amount"].mean()
                units = cpt_data.get("units", pd.Series([1] * len(cpt_data))).mean() if "units" in cpt_data.columns else 1
                effective_rate = avg_allowed / max(units, 1) if units else avg_allowed
                multiple = round(effective_rate / medicare_rate, 2) if medicare_rate > 0 else 0

                rate_comparisons.append({
                    "cpt_code": cpt,
                    "claim_count": int(cpt_counts[cpt]),
                    "avg_allowed": round(avg_allowed, 2),
                    "medicare_rate": round(medicare_rate, 2),
                    "multiple": multiple,
                })

            rate_comparisons.sort(key=lambda x: x["claim_count"], reverse=True)
            carrier_rates["top_cpts"] = rate_comparisons[:10]
            if rate_comparisons:
                carrier_rates["avg_multiple_vs_medicare"] = round(
                    sum(r["multiple"] for r in rate_comparisons) / len(rate_comparisons), 2
                )
    except Exception as exc:
        print(f"[Level2] Carrier rate analysis failed: {exc}")

    # --- D. Network leakage detection ---
    network_leakage = {"out_of_network_pct": 0.0, "out_of_network_paid": 0.0, "out_of_network_count": 0, "flag": "LOW"}
    try:
        total_paid = df["paid_amount"].sum()
        if total_paid > 0 and "billed_amount" in df.columns:
            # Out-of-network indicator: CO adjustment is zero or very small (< 5% of billed)
            # AND billed > $500
            high_billed = df[df["billed_amount"] > 500].copy()
            if not high_billed.empty:
                high_billed["discount_pct"] = (
                    (high_billed["billed_amount"] - high_billed["paid_amount"]) / high_billed["billed_amount"]
                ).clip(lower=0)
                oon_claims = high_billed[high_billed["discount_pct"] < 0.05]
                oon_paid = oon_claims["paid_amount"].sum()
                oon_pct = round(oon_paid / total_paid * 100, 1)

                network_leakage["out_of_network_count"] = len(oon_claims)
                network_leakage["out_of_network_paid"] = round(oon_paid, 2)
                network_leakage["out_of_network_pct"] = oon_pct

                if oon_pct > 10:
                    network_leakage["flag"] = "HIGH"
                elif oon_pct > 5:
                    network_leakage["flag"] = "MODERATE"
                else:
                    network_leakage["flag"] = "LOW"
    except Exception as exc:
        print(f"[Level2] Network leakage analysis failed: {exc}")

    # --- E. Denial analysis ---
    denial_rate = {"rate_pct": 0.0, "denial_count": 0, "flag": "NORMAL"}
    try:
        # Use claims data from the original results to check status
        # We check claim-level status from the parsed 835 data
        # For now, check if any claims have very low paid vs billed ratio (proxy for denials)
        total_claims = len(df)
        if total_claims > 0:
            denied = df[df["paid_amount"] == 0]
            denial_count = len(denied)
            denial_pct = round(denial_count / total_claims * 100, 1)
            denial_rate["denial_count"] = denial_count
            denial_rate["rate_pct"] = denial_pct
            if denial_pct > 5:
                denial_rate["flag"] = "ELEVATED"
    except Exception as exc:
        print(f"[Level2] Denial analysis failed: {exc}")

    return {
        "has_level2": True,
        "provider_variation": provider_variation,
        "site_of_care": site_of_care,
        "carrier_rates": carrier_rates,
        "network_leakage": network_leakage,
        "denial_rate": denial_rate,
    }


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


# ---------------------------------------------------------------------------
# GET /claims-history
# ---------------------------------------------------------------------------

@router.get("/claims-history")
async def employer_claims_history(email: str = Query(...)):
    sb = _get_supabase()
    result = sb.table("employer_claims_uploads").select(
        "id, created_at, filename_original, total_claims, total_excess_2x"
    ).eq("email", email.strip().lower()).order("created_at", desc=True).limit(10).execute()
    return {"uploads": result.data or []}


# ---------------------------------------------------------------------------
# POST /broker-connect — employer requests broker connection
# ---------------------------------------------------------------------------

class BrokerConnectRequest(BaseModel):
    employer_email: str
    requester_name: Optional[str] = None
    company_name: Optional[str] = None
    employee_count_range: Optional[str] = None
    industry: Optional[str] = None
    state: Optional[str] = None
    pepm: Optional[float] = None
    percentile: Optional[float] = None
    annual_gap: Optional[float] = None
    excess_amount: Optional[float] = None
    message: Optional[str] = None


@router.post("/broker-connect")
async def broker_connect(req: BrokerConnectRequest):
    """Employer requests to be connected with a broker."""
    employer_email = req.employer_email.strip().lower()
    company_label = req.company_name or employer_email

    # Notify admin
    admin_body = f"""
    <h2>New Broker Connection Request</h2>
    <p><strong>Name:</strong> {req.requester_name or 'Not provided'}</p>
    <p><strong>Email:</strong> {employer_email}</p>
    <p><strong>Company:</strong> {req.company_name or 'Not provided'}</p>
    <p><strong>Industry:</strong> {req.industry or 'N/A'} | <strong>State:</strong> {req.state or 'N/A'} | <strong>Size:</strong> {req.employee_count_range or 'N/A'}</p>
    <p><strong>PEPM:</strong> {'$' + str(round(req.pepm)) if req.pepm else 'N/A'} | <strong>Percentile:</strong> {str(round(req.percentile, 1)) + 'th' if req.percentile else 'N/A'}</p>
    <p><strong>Annual Gap:</strong> {'$' + str(round(req.annual_gap)) if req.annual_gap else 'N/A'} | <strong>Excess:</strong> {'$' + str(round(req.excess_amount)) if req.excess_amount else 'N/A'}</p>
    <p><strong>Message:</strong> {req.message or 'None'}</p>
    """
    try:
        send_email(
            to="admin@civicscale.ai",
            subject=f"New broker connection request — {company_label}",
            html=admin_body,
        )
    except Exception as exc:
        print(f"[Broker Connect] Admin email failed: {exc}")

    # Confirm to employer
    try:
        send_email(
            to=employer_email,
            subject="We received your request — we'll connect you with a broker",
            html="""
            <div style="font-family: -apple-system, sans-serif; max-width: 520px; color: #1e293b;">
              <p>Thanks for reaching out.</p>
              <p>A member of the CivicScale team will follow up within 1 business day to connect you
              with a benefits broker in our network who works with employers your size in your area.</p>
              <p>In the meantime, your benchmark and claims results are saved and ready to share.</p>
              <p style="color: #64748b; margin-top: 24px;">— The CivicScale Team</p>
            </div>
            """,
        )
    except Exception as exc:
        print(f"[Broker Connect] Employer email failed: {exc}")

    # Best-effort log
    try:
        sb = _get_supabase()
        sb.table("employer_benchmark_sessions").insert({
            "email": employer_email,
            "industry": req.industry,
            "state": req.state,
            "pepm_input": float(req.pepm) if req.pepm else 0,
            "result_json": {
                "source": "broker_connect_request",
                "company_name": req.company_name,
                "employee_count_range": req.employee_count_range,
                "percentile": req.percentile,
                "annual_gap": req.annual_gap,
                "excess_amount": req.excess_amount,
                "message": req.message,
            },
        }).execute()
    except Exception as exc:
        print(f"[Broker Connect] Log failed: {exc}")

    return {"submitted": True}
