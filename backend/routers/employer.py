"""
Employer endpoints — thin router that includes all sub-routers.

All endpoint implementations are in:
  - employer.py (this file)    — legacy dashboard (verify-code, contribute, dashboard)
  - employer_benchmark.py     — PEPM benchmarking tool
  - employer_claims.py        — claims file analysis
  - employer_scorecard.py     — plan grading / scorecard
  - employer_subscription.py  — Stripe checkout, webhook, subscription status
  - employer_trends.py        — month-over-month trend engine
  - employer_shared.py        — shared helpers, constants, Pydantic models

No PHI is stored. User IDs are SHA-256 hashed before persistence.
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from supabase import create_client
import os

from routers.employer_benchmark import router as benchmark_router
from routers.employer_claims import router as claims_router
from routers.employer_scorecard import router as scorecard_router
from routers.employer_subscription import router as subscription_router
from routers.employer_trends import router as trends_router
from routers.employer_pharmacy import router as pharmacy_router

router = APIRouter(prefix="/api/employer", tags=["employer"])

# Include all sub-routers — they have no prefix, so all endpoints
# retain their original URLs under /api/employer/...
router.include_router(benchmark_router)
router.include_router(claims_router)
router.include_router(scorecard_router)
router.include_router(subscription_router)
router.include_router(trends_router)
router.include_router(pharmacy_router)

# ---------------------------------------------------------------------------
# Supabase client (service role for server-side access)
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
# Models (legacy dashboard)
# ---------------------------------------------------------------------------

class VerifyCodeRequest(BaseModel):
    code: str


class ContributionLineItem(BaseModel):
    code: str
    description: Optional[str] = None
    billedAmount: float
    benchmarkRate: Optional[float] = None
    anomalyScore: Optional[float] = None
    flagged: bool = False
    flagReason: Optional[str] = None
    codingFlags: Optional[list] = None


class ContributeRequest(BaseModel):
    user_id: str
    employer_code: str
    provider_name: Optional[str] = None
    line_items: List[ContributionLineItem]


# ---------------------------------------------------------------------------
# POST /api/employer/verify-code
# ---------------------------------------------------------------------------

@router.post("/verify-code")
async def verify_code(req: VerifyCodeRequest):
    sb = _get_supabase()
    result = sb.table("employer_accounts").select("company_name, is_active").eq("employer_code", req.code).execute()

    if result.data and len(result.data) > 0 and result.data[0].get("is_active", True):
        return {"valid": True, "company_name": result.data[0]["company_name"]}
    return {"valid": False}


# ---------------------------------------------------------------------------
# POST /api/employer/contribute
# ---------------------------------------------------------------------------

@router.post("/contribute")
async def contribute(req: ContributeRequest):
    sb = _get_supabase()

    # Look up employer
    emp_result = sb.table("employer_accounts").select("id").eq("employer_code", req.employer_code).execute()
    if not emp_result.data or len(emp_result.data) == 0:
        raise HTTPException(status_code=404, detail="Employer code not found")

    employer_id = emp_result.data[0]["id"]

    # Hash the user_id — never store raw
    user_hash = hashlib.sha256(req.user_id.encode()).hexdigest()

    # Build rows
    rows = []
    for item in req.line_items:
        rows.append({
            "employer_id": employer_id,
            "source_user_hash": user_hash,
            "provider_name": req.provider_name,
            "cpt_code": item.code,
            "cpt_description": item.description,
            "billed_amount": item.billedAmount,
            "benchmark_rate": item.benchmarkRate,
            "anomaly_score": item.anomalyScore,
            "flagged": item.flagged,
            "flag_reason": item.flagReason,
            "coding_flags": item.codingFlags or [],
        })

    if rows:
        sb.table("employer_contributions").insert(rows).execute()

    return {"status": "ok", "contributed": len(rows)}


# ---------------------------------------------------------------------------
# GET /api/employer/dashboard
# ---------------------------------------------------------------------------

@router.get("/dashboard")
async def dashboard(employer_id: str = Query(...)):
    sb = _get_supabase()

    # Fetch all contributions for this employer
    result = sb.table("employer_contributions").select("*").eq("employer_id", employer_id).execute()
    rows = result.data or []

    if not rows:
        return {
            "empty": True,
            "overview": None,
            "topProviders": [],
            "scoreDistribution": [],
            "codingIntelligence": None,
            "cptHotspots": [],
            "monthlyTrend": [],
        }

    # --- Panel 1: Portfolio Overview ---
    total_claims = len(rows)
    total_billed = sum(r.get("billed_amount") or 0 for r in rows)
    total_benchmark = sum(r.get("benchmark_rate") or 0 for r in rows if r.get("benchmark_rate"))
    total_discrepancy = total_billed - total_benchmark
    scores = [r.get("anomaly_score") or 0 for r in rows if r.get("anomaly_score")]
    avg_score = sum(scores) / len(scores) if scores else 0

    flagged_providers = set()
    for r in rows:
        if (r.get("anomaly_score") or 0) > 2.0 and r.get("provider_name"):
            flagged_providers.add(r["provider_name"])

    overview = {
        "totalClaims": total_claims,
        "totalBilled": round(total_billed, 2),
        "totalBenchmark": round(total_benchmark, 2),
        "totalDiscrepancy": round(total_discrepancy, 2),
        "avgScore": round(avg_score, 2),
        "providersFlagged": len(flagged_providers),
    }

    # --- Panel 2: Top Flagged Providers ---
    provider_map = {}
    for r in rows:
        name = r.get("provider_name") or "Unknown"
        if name not in provider_map:
            provider_map[name] = {"scores": [], "count": 0, "discrepancy": 0, "cpts": {}}
        provider_map[name]["scores"].append(r.get("anomaly_score") or 0)
        provider_map[name]["count"] += 1
        billed = r.get("billed_amount") or 0
        bench = r.get("benchmark_rate") or 0
        provider_map[name]["discrepancy"] += billed - bench
        cpt = r.get("cpt_code") or ""
        if cpt:
            provider_map[name]["cpts"][cpt] = provider_map[name]["cpts"].get(cpt, 0) + 1

    top_providers = []
    for name, data in provider_map.items():
        if data["count"] < 3:
            continue
        avg = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        most_common_cpt = max(data["cpts"], key=data["cpts"].get) if data["cpts"] else ""
        top_providers.append({
            "providerName": name,
            "avgScore": round(avg, 2),
            "claimCount": data["count"],
            "totalDiscrepancy": round(data["discrepancy"], 2),
            "mostCommonCpt": most_common_cpt,
        })
    top_providers.sort(key=lambda x: x["avgScore"], reverse=True)
    top_providers = top_providers[:10]

    # --- Panel 3: Score Distribution ---
    buckets = {"0-1": 0, "1-2": 0, "2-3": 0, "3-5": 0, "5+": 0}
    for r in rows:
        s = r.get("anomaly_score") or 0
        if s < 1:
            buckets["0-1"] += 1
        elif s < 2:
            buckets["1-2"] += 1
        elif s < 3:
            buckets["2-3"] += 1
        elif s < 5:
            buckets["3-5"] += 1
        else:
            buckets["5+"] += 1

    score_distribution = [{"range": k, "count": v} for k, v in buckets.items()]

    # --- Panel 4: Coding Intelligence ---
    ncci_count = 0
    mue_count = 0
    sos_count = 0
    em_count = 0
    for r in rows:
        flags = r.get("coding_flags") or []
        for f in flags:
            ftype = f.get("type", "") if isinstance(f, dict) else str(f)
            if "ncci" in ftype.lower():
                ncci_count += 1
            elif "mue" in ftype.lower():
                mue_count += 1
            elif "site" in ftype.lower() or "sos" in ftype.lower():
                sos_count += 1
            elif "e&m" in ftype.lower() or "em_" in ftype.lower() or "level" in ftype.lower():
                em_count += 1

    coding_intelligence = {
        "ncciFlags": ncci_count,
        "mueFlags": mue_count,
        "siteOfServiceFlags": sos_count,
        "emFlags": em_count,
        "totalFlags": ncci_count + mue_count + sos_count + em_count,
    }

    # --- Panel 5: CPT Code Hotspots ---
    cpt_map = {}
    for r in rows:
        code = r.get("cpt_code") or ""
        if not code:
            continue
        if code not in cpt_map:
            cpt_map[code] = {"description": r.get("cpt_description") or "", "count": 0, "scores": [], "discrepancy": 0}
        cpt_map[code]["count"] += 1
        cpt_map[code]["scores"].append(r.get("anomaly_score") or 0)
        billed = r.get("billed_amount") or 0
        bench = r.get("benchmark_rate") or 0
        cpt_map[code]["discrepancy"] += billed - bench

    cpt_hotspots = []
    for code, data in cpt_map.items():
        avg = sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0
        cpt_hotspots.append({
            "cptCode": code,
            "description": data["description"],
            "occurrences": data["count"],
            "avgScore": round(avg, 2),
            "totalDiscrepancy": round(data["discrepancy"], 2),
        })
    cpt_hotspots.sort(key=lambda x: x["totalDiscrepancy"], reverse=True)
    cpt_hotspots = cpt_hotspots[:10]

    # --- Panel 6: Monthly Trend ---
    month_map = {}
    for r in rows:
        ts = r.get("contributed_at") or ""
        if not ts:
            continue
        # Parse ISO timestamp to month key
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            else:
                dt = ts
            month_key = dt.strftime("%Y-%m")
        except Exception:
            continue
        if month_key not in month_map:
            month_map[month_key] = {"discrepancy": 0, "claims": 0}
        billed = r.get("billed_amount") or 0
        bench = r.get("benchmark_rate") or 0
        month_map[month_key]["discrepancy"] += billed - bench
        month_map[month_key]["claims"] += 1

    monthly_trend = []
    for month, data in sorted(month_map.items()):
        monthly_trend.append({
            "month": month,
            "totalDiscrepancy": round(data["discrepancy"], 2),
            "claimCount": data["claims"],
        })

    return {
        "empty": False,
        "overview": overview,
        "topProviders": top_providers,
        "scoreDistribution": score_distribution,
        "codingIntelligence": coding_intelligence,
        "cptHotspots": cpt_hotspots,
        "monthlyTrend": monthly_trend,
    }
