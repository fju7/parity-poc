"""Employer trend detection engine — PEPM drift, outlier tracking, AI narrative.

GET  /trends/{subscription_id}         — returns cached or freshly computed trends
POST /trends/{subscription_id}/refresh — forces recompute, updates cache
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from routers.employer_shared import _get_supabase
from routers.employer_claims import _generate_narrative

router = APIRouter(tags=["employer"])


# ---------------------------------------------------------------------------
# Core trend computation
# ---------------------------------------------------------------------------

def _compute_employer_trends(subscription_id: str, sb=None) -> dict:
    """Compute month-over-month trends for an employer subscription.

    Pulls the last 3 months of claims upload sessions from employer_claims_uploads,
    computes PEPM, excess, top CPTs, and month-over-month deltas.

    Returns: {monthly_summary, alerts, months_available}
    """
    if sb is None:
        sb = _get_supabase()

    # Fetch subscription for employee_count and email
    sub_result = sb.table("employer_subscriptions").select("*").eq("id", subscription_id).execute()
    if not sub_result.data:
        return {"monthly_summary": [], "alerts": [], "months_available": 0}

    sub = sub_result.data[0]
    email = sub.get("email", "")
    employee_count = sub.get("employee_count") or 1  # Avoid division by zero

    # Fetch claims uploads for this email, ordered by date
    uploads_result = sb.table("employer_claims_uploads").select("*").eq(
        "email", email
    ).order("created_at", desc=True).limit(200).execute()

    uploads = uploads_result.data or []
    if not uploads:
        return {"monthly_summary": [], "alerts": [], "months_available": 0}

    # Group uploads by month
    month_buckets = {}  # {YYYY-MM: [upload_records]}
    for u in uploads:
        ts = u.get("created_at", "")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else ts
            month_key = dt.strftime("%Y-%m")
        except Exception:
            continue
        month_buckets.setdefault(month_key, []).append(u)

    # Sort months and take last 3
    sorted_months = sorted(month_buckets.keys())[-3:]
    if not sorted_months:
        return {"monthly_summary": [], "alerts": [], "months_available": 0}

    # Build monthly_summary
    monthly_summary = []
    for month in sorted_months:
        bucket = month_buckets[month]
        total_paid = sum(float(u.get("total_paid") or 0) for u in bucket)
        claim_count = sum(int(u.get("total_claims") or 0) for u in bucket)
        excess = sum(float(u.get("total_excess_2x") or 0) for u in bucket)

        # Build top CPTs from results_json
        cpt_data = {}  # {cpt: {total_paid, count, markup_ratios}}
        for u in bucket:
            rj = u.get("results_json") or {}
            # results_json is the summary dict — top_flagged_cpt is there
            # For detailed CPT data, we'd need the full line items, but they're capped
            top_cpt = rj.get("top_flagged_cpt") or u.get("top_flagged_cpt")
            top_excess = float(rj.get("top_flagged_excess") or u.get("top_flagged_excess") or 0)
            if top_cpt:
                if top_cpt not in cpt_data:
                    cpt_data[top_cpt] = {"total_excess": 0, "count": 0}
                cpt_data[top_cpt]["total_excess"] += top_excess
                cpt_data[top_cpt]["count"] += 1

        top_cpts = sorted(cpt_data.items(), key=lambda x: x[1]["total_excess"], reverse=True)[:10]
        top_cpts_list = [
            {"cpt_code": cpt, "total_excess": round(d["total_excess"], 2), "upload_count": d["count"]}
            for cpt, d in top_cpts
        ]

        pepm = round(total_paid / employee_count, 2) if employee_count > 0 else 0

        # Month label (e.g., "Jan 2026")
        try:
            dt = datetime.strptime(month, "%Y-%m")
            label = dt.strftime("%b %Y")
        except Exception:
            label = month

        monthly_summary.append({
            "month": month,
            "label": label,
            "total_paid": round(total_paid, 2),
            "claim_count": claim_count,
            "pepm": pepm,
            "excess_vs_medicare": round(excess, 2),
            "top_cpts": top_cpts_list,
        })

    # Compute month-over-month deltas and alerts
    alerts = []
    if len(monthly_summary) >= 2:
        curr = monthly_summary[-1]
        prev = monthly_summary[-2]

        # PEPM delta
        if prev["pepm"] > 0:
            pepm_delta_pct = round((curr["pepm"] - prev["pepm"]) / prev["pepm"] * 100, 1)
            curr["pepm_delta_pct"] = pepm_delta_pct
            if abs(pepm_delta_pct) >= 5:
                direction = "increased" if pepm_delta_pct > 0 else "decreased"
                severity = "high" if pepm_delta_pct > 10 else "medium" if pepm_delta_pct > 0 else "positive"
                alerts.append({
                    "type": "pepm_shift",
                    "severity": severity,
                    "detail": f"PEPM {direction} {abs(pepm_delta_pct)}% from ${prev['pepm']:,.2f} to ${curr['pepm']:,.2f}",
                    "financial_impact": round(abs(curr["pepm"] - prev["pepm"]) * employee_count, 2),
                    "month": curr["month"],
                })

        # Excess delta
        if prev["excess_vs_medicare"] > 0:
            excess_delta_pct = round(
                (curr["excess_vs_medicare"] - prev["excess_vs_medicare"]) / prev["excess_vs_medicare"] * 100, 1
            )
            curr["excess_delta_pct"] = excess_delta_pct
            if excess_delta_pct > 10:
                alerts.append({
                    "type": "excess_increase",
                    "severity": "high",
                    "detail": f"Excess spend above 2x Medicare increased {excess_delta_pct}% to ${curr['excess_vs_medicare']:,.2f}",
                    "financial_impact": round(curr["excess_vs_medicare"] - prev["excess_vs_medicare"], 2),
                    "month": curr["month"],
                })

        # New outlier CPTs (in current top 10 but not in previous top 10)
        prev_cpt_set = {c["cpt_code"] for c in prev.get("top_cpts", [])}
        for cpt_item in curr.get("top_cpts", []):
            if cpt_item["cpt_code"] not in prev_cpt_set and cpt_item["total_excess"] > 0:
                alerts.append({
                    "type": "new_outlier",
                    "severity": "medium",
                    "detail": f"CPT {cpt_item['cpt_code']} is a new high-excess procedure this month (${cpt_item['total_excess']:,.2f} excess)",
                    "cpt_code": cpt_item["cpt_code"],
                    "financial_impact": cpt_item["total_excess"],
                    "month": curr["month"],
                })

        # Worsening outliers (excess increased >20% for same CPT)
        prev_cpt_map = {c["cpt_code"]: c for c in prev.get("top_cpts", [])}
        for cpt_item in curr.get("top_cpts", []):
            prev_item = prev_cpt_map.get(cpt_item["cpt_code"])
            if prev_item and prev_item["total_excess"] > 0:
                change_pct = (cpt_item["total_excess"] - prev_item["total_excess"]) / prev_item["total_excess"] * 100
                if change_pct > 20:
                    alerts.append({
                        "type": "worsening_outlier",
                        "severity": "high",
                        "detail": f"CPT {cpt_item['cpt_code']} excess worsened {change_pct:.0f}% (${prev_item['total_excess']:,.2f} → ${cpt_item['total_excess']:,.2f})",
                        "cpt_code": cpt_item["cpt_code"],
                        "financial_impact": round(cpt_item["total_excess"] - prev_item["total_excess"], 2),
                        "month": curr["month"],
                    })

    return {
        "monthly_summary": monthly_summary,
        "alerts": alerts,
        "months_available": len(monthly_summary),
    }


# ---------------------------------------------------------------------------
# AI narrative
# ---------------------------------------------------------------------------

def _generate_trend_narrative(sub: dict, monthly_summary: list, alerts: list) -> str:
    """Generate AI narrative summarizing month-over-month employer trends."""
    if len(monthly_summary) < 2:
        return ""

    curr = monthly_summary[-1]
    prev = monthly_summary[-2]
    company_name = sub.get("company_name", "your company")
    employee_count = sub.get("employee_count") or 0

    new_outliers = [a for a in alerts if a.get("type") == "new_outlier"]
    worsening = [a for a in alerts if a.get("type") == "worsening_outlier"]
    high_alerts = [a for a in alerts if a.get("severity") == "high"]

    top_concern = "No major concerns detected."
    if high_alerts:
        top_concern = high_alerts[0]["detail"]

    prompt = (
        "You are a healthcare benefits analyst. Write a 3-4 sentence trend summary "
        "for an HR director or CFO reviewing their monthly health spend report. "
        "Be specific about dollar amounts and percentages. Focus on the most actionable finding. "
        "Do not use jargon.\n\n"
        f"Company: {company_name}\n"
        f"Employees: {employee_count}\n"
        f"This month PEPM: ${curr['pepm']:.2f}\n"
        f"Prior month PEPM: ${prev['pepm']:.2f}\n"
        f"PEPM change: {curr.get('pepm_delta_pct', 0):+.1f}%\n"
        f"New outliers detected: {len(new_outliers)}\n"
        f"Worsening outliers: {len(worsening)}\n"
        f"Top concern: {top_concern}\n\n"
        "Write only the summary paragraph. No headers, no bullet points."
    )

    try:
        return _generate_narrative(prompt) or ""
    except Exception as exc:
        print(f"[Employer Trends] Narrative generation failed: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def _compute_and_cache_trends(subscription_id: str, sb=None) -> dict:
    """Compute trends and cache the result. Returns the full trend payload."""
    if sb is None:
        sb = _get_supabase()

    trends = _compute_employer_trends(subscription_id, sb=sb)

    # Generate narrative
    sub_result = sb.table("employer_subscriptions").select("*").eq("id", subscription_id).execute()
    sub = sub_result.data[0] if sub_result.data else {}

    narrative = _generate_trend_narrative(sub, trends["monthly_summary"], trends["alerts"])
    trends["trend_narrative"] = narrative

    # Cache to Supabase
    try:
        now = datetime.now(timezone.utc).isoformat()
        # Upsert: delete old, insert new
        sb.table("employer_trends_cache").delete().eq("subscription_id", subscription_id).execute()
        sb.table("employer_trends_cache").insert({
            "subscription_id": subscription_id,
            "trend_data": trends,
            "computed_at": now,
        }).execute()
    except Exception as exc:
        print(f"[Employer Trends] Cache write failed (non-fatal): {exc}")

    return trends


def _get_cached_trends(subscription_id: str, sb=None) -> dict | None:
    """Return cached trends if less than 24 hours old, else None."""
    if sb is None:
        sb = _get_supabase()

    try:
        result = sb.table("employer_trends_cache").select("*").eq(
            "subscription_id", subscription_id
        ).execute()
        if not result.data:
            return None

        cached = result.data[0]
        computed_at = cached.get("computed_at", "")
        if computed_at:
            dt = datetime.fromisoformat(computed_at.replace("Z", "+00:00"))
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            if age_hours < 24:
                return cached.get("trend_data")
    except Exception as exc:
        print(f"[Employer Trends] Cache read failed: {exc}")

    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/trends/{subscription_id}")
async def get_employer_trends(subscription_id: str):
    """Return cached or freshly computed employer trends."""
    sb = _get_supabase()

    # Check cache first
    cached = _get_cached_trends(subscription_id, sb=sb)
    if cached:
        return cached

    # Compute fresh
    return _compute_and_cache_trends(subscription_id, sb=sb)


@router.post("/trends/{subscription_id}/refresh")
async def refresh_employer_trends(subscription_id: str):
    """Force recompute of employer trends."""
    sb = _get_supabase()
    return _compute_and_cache_trends(subscription_id, sb=sb)
