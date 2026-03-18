"""
Broker Portal endpoints — unified auth + client management + freemium onboarding.

Endpoints:
  GET  /api/broker/clients           — list linked employer clients
  POST /api/broker/clients/add       — link an employer to this broker
  DELETE /api/broker/clients/{employer_email} — unlink an employer
  GET  /api/broker/clients/{employer_email}/summary — aggregated employer summary
  POST /api/broker/clients/onboard   — add client + run benchmark (no employer account required)
  GET  /api/broker/clients/{employer_email}/share-link — get/generate share link
  POST /api/broker/clients/{employer_email}/notify — send benchmark email to employer
  GET  /api/broker/clients/{employer_email}/activity — employer activity timeline
  GET  /api/broker/renewal-pipeline — renewal timeline with checklist status
  GET  /api/broker/renewal-prep/{company_name} — assembled renewal prep report data
  POST /api/broker/send-renewal-reminders — cron-triggered 90-day renewal reminders
  POST /api/broker/prospect-benchmark — preliminary benchmark for a prospect
  GET  /api/broker/prospects — list recent prospect benchmarks
  GET  /api/broker/plan — return broker plan info
  POST /api/broker/subscribe — create Stripe checkout for Pro upgrade
  POST /api/broker/cancel-subscription — cancel Pro at period end
  POST /api/broker/reactivate-subscription — undo pending cancellation
  GET  /api/broker/account — return broker account details
  PATCH /api/broker/account — update broker account details
  POST /api/broker/profile/logo — upload broker logo
  POST /api/broker/invite-employer — invite employer client (triggers commission tracking)
  POST /api/broker/clients/{employer_email}/claims-upload — broker uploads claims on behalf of client
  POST /api/broker/clients/{employer_email}/scorecard-upload — broker uploads SBC on behalf of client
"""

import base64
import io
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone, timedelta

import pandas as pd

from fastapi import APIRouter, HTTPException, Request, Header, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from routers.employer_shared import _get_supabase, _call_claude, check_rate_limit, get_benchmarks, assign_pricing_tier, EMPLOYER_PRICE_TIERS
from routers.auth import get_current_user
from utils.email import send_email

# Imports for broker claims/scorecard upload reuse
from routers.employer_claims import (
    _edi_items_to_df, _safe_float, _generate_narrative,
    _run_level2_analytics, COLUMN_MAPPING_PROMPT,
)
from routers.employer_scorecard import (
    SBC_EXTRACTION_PROMPT, SCORING_CRITERIA,
    _score_range, _score_to_grade, _grade_interpretation, _estimate_savings,
)
from routers.benchmark import resolve_locality, lookup_rate
from utils.parse_835 import parse_835

router = APIRouter(prefix="/api/broker", tags=["broker"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class BrokerOnboardRequest(BaseModel):
    company_name: str
    employee_count_range: Optional[str] = None  # "<100", "100-250", "250-500", "500-1000", "1000+"
    employee_count: Optional[str] = None  # alias accepted from frontend
    industry: str
    state: str
    carrier: Optional[str] = None
    employer_email: Optional[str] = None
    estimated_pepm: Optional[float] = None
    estimated_annual_spend: Optional[float] = None
    renewal_month: Optional[str] = None  # ISO date string, e.g. "2026-01-01"

    @property
    def resolved_employee_count_range(self) -> str:
        return self.employee_count_range or self.employee_count or "<100"


class NotifyClientRequest(BaseModel):
    message_type: Optional[str] = "benchmark"  # "benchmark" or "upgrade"


class UpdateBrokerAccountRequest(BaseModel):
    contact_name: Optional[str] = None
    firm_name: Optional[str] = None
    phone: Optional[str] = None


class BulkOnboardRow(BaseModel):
    company_name: str
    employee_count_range: str
    industry: str
    state: str
    carrier: Optional[str] = None
    estimated_pepm: Optional[float] = None
    renewal_month: Optional[str] = None  # format: "YYYY-MM"


class BulkOnboardRequest(BaseModel):
    clients: list[BulkOnboardRow]


class ProspectBenchmarkRequest(BaseModel):
    company_name: str
    employee_count_range: str
    industry: str
    state: str
    carrier: Optional[str] = None


class InviteEmployerRequest(BaseModel):
    email: str


# ---------------------------------------------------------------------------
# Auth helper — validates Bearer token and ensures broker company type
# ---------------------------------------------------------------------------

def _require_broker(authorization: str, sb=None):
    """Validate auth and ensure user belongs to a broker company."""
    if not sb:
        sb = _get_supabase()
    user = get_current_user(authorization, sb)
    if user["company"]["type"] != "broker":
        raise HTTPException(status_code=403, detail="Broker access only")
    return user, sb


# ---------------------------------------------------------------------------
# Plan helpers — Starter (free, 10 clients) / Pro ($99/mo, unlimited)
# ---------------------------------------------------------------------------

STARTER_LIMIT = 10


def _get_broker_plan(sb, company_id: str) -> dict:
    """Returns broker plan info: plan, client_count, at_limit, subscription_period_end, stripe_status, trial_ends_at."""
    import stripe as stripe_lib
    stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

    company = sb.table("companies").select("plan, stripe_subscription_id").eq("id", company_id).execute()
    plan = company.data[0].get("plan", "starter") if company.data else "starter"

    # Get broker email(s) for this company to count clients
    users = sb.table("company_users").select("email").eq("company_id", company_id).eq("status", "active").execute()
    broker_emails = [u["email"] for u in (users.data or [])]

    # Count clients across all broker users in this firm
    client_count = 0
    for be in broker_emails:
        count_result = sb.table("broker_employer_links").select("id", count="exact").eq("broker_email", be).execute()
        client_count += count_result.count or 0

    # pro_cancelling still has Pro access until period end
    effective_plan = "pro" if plan == "pro_cancelling" else plan
    at_limit = effective_plan == "starter" and client_count >= STARTER_LIMIT

    # Fetch subscription details from Stripe (trial status, period end)
    period_end = None
    stripe_status = None
    trial_ends_at = None
    stripe_sub_id = company.data[0].get("stripe_subscription_id") if company.data else None
    if stripe_sub_id and plan in ("pro", "pro_cancelling"):
        try:
            stripe_sub = stripe_lib.Subscription.retrieve(stripe_sub_id)
            stripe_status = stripe_sub.status  # "trialing", "active", "canceled", etc.
            if stripe_sub.current_period_end:
                period_end = datetime.fromtimestamp(
                    stripe_sub.current_period_end, tz=timezone.utc
                ).isoformat()
            if stripe_sub.trial_end:
                trial_ends_at = datetime.fromtimestamp(
                    stripe_sub.trial_end, tz=timezone.utc
                ).isoformat()
        except Exception as exc:
            print(f"[BrokerPlan] Stripe fetch failed for sub_id={stripe_sub_id}: {type(exc).__name__}: {exc}")

    return {
        "plan": plan,
        "client_count": client_count,
        "client_limit": STARTER_LIMIT if effective_plan == "starter" else None,
        "at_limit": at_limit,
        "subscription_period_end": period_end,
        "stripe_status": stripe_status,
        "trial_ends_at": trial_ends_at,
    }


# ---------------------------------------------------------------------------
# GET /api/broker/plan — return broker plan info
# ---------------------------------------------------------------------------

@router.get("/plan")
async def get_broker_plan_endpoint(authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    return _get_broker_plan(sb, user["company_id"])


# ---------------------------------------------------------------------------
# POST /api/broker/subscribe — create Stripe checkout for broker Pro upgrade
# ---------------------------------------------------------------------------

@router.post("/subscribe")
async def broker_subscribe(request: Request, authorization: str = Header(None)):
    """Create Stripe checkout session for broker Pro upgrade."""
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
    price_id = os.environ.get("STRIPE_PRICE_BROKER_PRO")

    user, sb = _require_broker(authorization)
    company = user["company"]
    company_id = user["company_id"]
    email = user["email"]

    if company.get("plan") == "pro":
        raise HTTPException(status_code=409, detail="You already have an active subscription.")

    # Derive frontend URL from Origin header (supports staging subdomains)
    origin = request.headers.get("origin", "")
    base_url = origin if origin.startswith("https://") else "https://broker.civicscale.ai"

    # Get or create Stripe customer
    customer_id = company.get("stripe_customer_id")
    if not customer_id:
        customer = stripe.Customer.create(email=email, name=company.get("name", ""))
        customer_id = customer.id
        sb.table("companies").update({"stripe_customer_id": customer_id}).eq("id", company_id).execute()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        payment_method_collection="always",
        subscription_data={"trial_period_days": 30},
        success_url=f"{base_url}/dashboard?upgraded=true",
        cancel_url=f"{base_url}/dashboard?upgrade_cancelled=true",
        metadata={"company_id": company_id, "broker_email": email, "product": "broker_pro"},
    )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# POST /api/broker/cancel-subscription — cancel Pro at period end
# ---------------------------------------------------------------------------

@router.post("/cancel-subscription")
async def broker_cancel_subscription(authorization: str = Header(None)):
    """Cancel broker Pro subscription at end of current billing period."""
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

    user, sb = _require_broker(authorization)
    company = user["company"]
    company_id = user["company_id"]

    if company.get("plan") not in ("pro", "pro_cancelling"):
        raise HTTPException(status_code=400, detail="No active Pro subscription to cancel")

    sub_id = company.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No Stripe subscription found")

    # Cancel at period end (not immediately)
    sub = stripe.Subscription.modify(sub_id, cancel_at_period_end=True)
    period_end = datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc).isoformat()

    sb.table("companies").update({
        "plan": "pro_cancelling",
    }).eq("id", company_id).execute()

    return {"status": "cancelled", "period_end": period_end}


# ---------------------------------------------------------------------------
# POST /api/broker/reactivate-subscription — undo pending cancellation
# ---------------------------------------------------------------------------

@router.post("/reactivate-subscription")
async def broker_reactivate_subscription(authorization: str = Header(None)):
    """Reactivate a Pro subscription that was set to cancel at period end."""
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

    user, sb = _require_broker(authorization)
    company = user["company"]
    company_id = user["company_id"]

    if company.get("plan") != "pro_cancelling":
        raise HTTPException(status_code=400, detail="Subscription is not pending cancellation")

    sub_id = company.get("stripe_subscription_id")
    if not sub_id:
        raise HTTPException(status_code=400, detail="No Stripe subscription found")

    stripe.Subscription.modify(sub_id, cancel_at_period_end=False)

    sb.table("companies").update({
        "plan": "pro",
    }).eq("id", company_id).execute()

    return {"status": "reactivated"}


# ---------------------------------------------------------------------------
# POST /api/broker/portal — open Stripe billing portal
# ---------------------------------------------------------------------------

@router.post("/portal")
async def broker_billing_portal(authorization: str = Header(None)):
    """Create a Stripe billing portal session for broker."""
    import stripe as stripe_lib
    stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY")

    user, sb = _require_broker(authorization)
    company = user["company"]

    customer_id = company.get("stripe_customer_id")
    if not customer_id:
        raise HTTPException(status_code=404, detail="No billing account found")

    session = stripe_lib.billing_portal.Session.create(
        customer=customer_id,
        return_url="https://broker.civicscale.ai/account",
    )
    return {"portal_url": session.url}


# ---------------------------------------------------------------------------
# GET /api/broker/account — return broker account details
# ---------------------------------------------------------------------------

@router.get("/account")
async def get_broker_account(authorization: str = Header(None)):
    """Return broker account info for the account page."""
    user, sb = _require_broker(authorization)
    company = user["company"]
    company_id = user["company_id"]

    plan_info = _get_broker_plan(sb, company_id)

    return {
        "email": user["email"],
        "contact_name": user.get("full_name", ""),
        "firm_name": company.get("name", ""),
        "phone": company.get("phone", ""),
        "plan": plan_info["plan"],
        "client_count": plan_info["client_count"],
        "client_limit": plan_info["client_limit"],
        "subscription_period_end": plan_info.get("subscription_period_end"),
        "created_at": company.get("created_at"),
    }


# ---------------------------------------------------------------------------
# PATCH /api/broker/account — update broker account details
# ---------------------------------------------------------------------------

@router.patch("/account")
async def update_broker_account(req: UpdateBrokerAccountRequest, authorization: str = Header(None)):
    """Update broker account info (name, firm, phone)."""
    user, sb = _require_broker(authorization)
    company_id = user["company_id"]

    company_updates = {}
    user_updates = {}

    if req.firm_name is not None:
        company_updates["name"] = req.firm_name.strip()
    if req.phone is not None:
        company_updates["phone"] = req.phone.strip()
    if req.contact_name is not None:
        user_updates["full_name"] = req.contact_name.strip()

    if not company_updates and not user_updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    if company_updates:
        sb.table("companies").update(company_updates).eq("id", company_id).execute()

    if user_updates:
        # Update the company_user's full_name
        sb.table("company_users").update(user_updates).eq(
            "company_id", company_id
        ).eq("email", user["email"]).execute()

    return {"status": "updated", "updated_fields": list(company_updates.keys()) + list(user_updates.keys())}


# ---------------------------------------------------------------------------
# GET /api/broker/clients
# ---------------------------------------------------------------------------

@router.get("/clients")
async def list_clients(authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]

    # Get linked employers
    links = (
        sb.table("broker_employer_links")
        .select("employer_email, linked_at, status, company_name, employee_count_range, industry, state, carrier")
        .eq("broker_email", broker_email)
        .order("linked_at", desc=True)
        .execute()
    )

    clients = []
    for link in (links.data or []):
        emp_email = link["employer_email"]

        # Look up employer subscription for company name and status
        sub = (
            sb.table("employer_subscriptions")
            .select("id, company_name, employee_count, tier, status")
            .eq("email", emp_email)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        # Count claims uploads
        uploads = (
            sb.table("employer_claims_uploads")
            .select("id", count="exact")
            .eq("email", emp_email)
            .execute()
        )

        sub_data = sub.data[0] if sub.data else {}

        # Check for broker-run benchmark
        bench = (
            sb.table("broker_client_benchmarks")
            .select("id, share_token, view_count, created_at")
            .eq("broker_email", broker_email)
            .eq("employer_email", emp_email)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        bench_data = bench.data[0] if bench.data else None

        # Determine activity status
        uploads_count = uploads.count if uploads.count is not None else 0
        sub_status = sub_data.get("status", "none")
        has_viewed = bench_data and bench_data.get("view_count", 0) > 0

        if sub_status == "active":
            activity_status = "subscriber"
        elif uploads_count > 0:
            activity_status = "uploaded"
        elif has_viewed:
            activity_status = "viewed"
        else:
            activity_status = "benchmark_only"

        clients.append({
            "employer_email": emp_email,
            "company_name": sub_data.get("company_name") or link.get("company_name") or emp_email,
            "employee_count": sub_data.get("employee_count"),
            "tier": sub_data.get("tier", "none"),
            "subscription_status": sub_status,
            "claims_uploads": uploads_count,
            "linked_at": link["linked_at"],
            "onboard_status": link.get("status", "linked"),
            "activity_status": activity_status,
            "has_benchmark": bench_data is not None,
            "share_token": bench_data.get("share_token") if bench_data else None,
        })

    return {"clients": clients}


# ---------------------------------------------------------------------------
# POST /api/broker/clients/add
# ---------------------------------------------------------------------------

class AddClientRequest(BaseModel):
    employer_email: str


@router.post("/clients/add")
async def add_client(req: AddClientRequest, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    employer_email = req.employer_email.strip().lower()

    # Check plan limit
    plan_info = _get_broker_plan(sb, user["company_id"])
    if plan_info["at_limit"]:
        raise HTTPException(status_code=403, detail="CLIENT_LIMIT_REACHED")

    # Verify employer has a subscription or claims upload (they exist in the system)
    emp_sub = sb.table("employer_subscriptions").select("id").eq("email", employer_email).limit(1).execute()
    emp_claims = sb.table("employer_claims_uploads").select("id").eq("email", employer_email).limit(1).execute()

    if not emp_sub.data and not emp_claims.data:
        raise HTTPException(
            status_code=404,
            detail="No employer found with that email. The employer must have an active subscription or claims history.",
        )

    # Check for existing link
    existing = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", broker_email)
        .eq("employer_email", employer_email)
        .execute()
    )
    if existing.data:
        return {"added": False, "message": "This employer is already linked to your account."}

    # Create link
    sb.table("broker_employer_links").insert({
        "broker_email": broker_email,
        "employer_email": employer_email,
    }).execute()

    return {"added": True}


# ---------------------------------------------------------------------------
# DELETE /api/broker/clients/{employer_email}
# ---------------------------------------------------------------------------

@router.delete("/clients/{employer_email}")
async def remove_client(employer_email: str, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    e_email = employer_email.strip().lower()

    result = (
        sb.table("broker_employer_links")
        .delete()
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .execute()
    )

    removed = len(result.data) > 0 if result.data else False
    return {"removed": removed}


# ---------------------------------------------------------------------------
# GET /api/broker/clients/{employer_email}/summary
# ---------------------------------------------------------------------------

@router.get("/clients/{employer_email}/summary")
async def client_summary(employer_email: str, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    e_email = employer_email.strip().lower()

    # Verify broker-employer link exists
    link = (
        sb.table("broker_employer_links")
        .select("id, company_name")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="You do not have access to this employer's data.")

    link_data = link.data[0]

    # Subscription info
    sub = (
        sb.table("employer_subscriptions")
        .select("*")
        .eq("email", e_email)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    sub_data = sub.data[0] if sub.data else None

    # Claims uploads (most recent 12)
    uploads = (
        sb.table("employer_claims_uploads")
        .select("id, filename_original, total_claims, total_paid, total_excess_2x, top_flagged_cpt, top_flagged_excess, results_json, created_at")
        .eq("email", e_email)
        .order("created_at", desc=True)
        .limit(12)
        .execute()
    )

    # Aggregate claims stats
    upload_rows = uploads.data or []
    total_claims = sum(u.get("total_claims") or 0 for u in upload_rows)
    total_paid = sum(u.get("total_paid") or 0 for u in upload_rows)
    total_excess = sum(u.get("total_excess_2x") or 0 for u in upload_rows)

    # Extract level2 from most recent upload's results_json
    latest_level2 = None
    if upload_rows:
        latest_results = upload_rows[0].get("results_json") or {}
        latest_level2 = latest_results.get("level2")

    # Trends cache if available
    if sub_data:
        trends = (
            sb.table("employer_trends_cache")
            .select("trend_data, computed_at")
            .eq("subscription_id", sub_data["id"])
            .limit(1)
            .execute()
        )
        trends_data = trends.data[0] if trends.data else None
    else:
        trends_data = None

    # Fetch latest benchmark for this client
    benchmark_row = (
        sb.table("broker_client_benchmarks")
        .select("benchmark_result, share_token, created_at")
        .eq("employer_email", e_email)
        .eq("broker_email", broker_email)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    benchmark_data = benchmark_row.data[0] if benchmark_row.data else None

    # Build upload timeline (without full results_json to keep response small)
    upload_timeline = []
    for u in upload_rows:
        upload_timeline.append({
            "id": u["id"],
            "filename": u.get("filename_original", ""),
            "total_claims": u.get("total_claims", 0),
            "total_paid": u.get("total_paid", 0),
            "total_excess_2x": u.get("total_excess_2x", 0),
            "top_flagged_cpt": u.get("top_flagged_cpt", ""),
            "top_flagged_excess": u.get("top_flagged_excess", 0),
            "created_at": u.get("created_at", ""),
        })

    return {
        "employer_email": e_email,
        "company_name": (sub_data.get("company_name") if sub_data else None) or link_data.get("company_name") or (e_email if not e_email.startswith("pending-") else "Unknown Company"),
        "subscription": {
            "tier": sub_data.get("tier", "none") if sub_data else "none",
            "status": sub_data.get("status", "none") if sub_data else "none",
            "employee_count": sub_data.get("employee_count") if sub_data else None,
        },
        "claims_summary": {
            "total_uploads": len(upload_rows),
            "total_claims": total_claims,
            "total_paid": round(total_paid, 2),
            "total_excess_2x": round(total_excess, 2),
            "level2": latest_level2,
        },
        "upload_timeline": upload_timeline,
        "trends": trends_data.get("trend_data") if trends_data else None,
        "trends_computed_at": trends_data.get("computed_at") if trends_data else None,
        "benchmark": benchmark_data.get("benchmark_result") if benchmark_data else None,
        "benchmark_date": benchmark_data.get("created_at") if benchmark_data else None,
    }


# ---------------------------------------------------------------------------
# Benchmark computation helper (reuses employer_benchmark logic)
# ---------------------------------------------------------------------------

def _employee_range_midpoint(range_str: str) -> int:
    """Convert employee count range to a midpoint integer."""
    mapping = {
        "<100": 50,
        "100-250": 175,
        "250-500": 375,
        "500-1000": 750,
        "1000+": 1500,
    }
    return mapping.get(range_str, 200)


def _range_to_size_band(range_str: str) -> str:
    """Map employee range to benchmark company_size band."""
    mapping = {
        "<100": "10-49",
        "100-250": "50-199",
        "250-500": "200-999",
        "500-1000": "200-999",
        "1000+": "1000+",
    }
    return mapping.get(range_str, "50-199")


def _run_benchmark(industry: str, company_size: str, state: str, pepm_input: float) -> dict:
    """Run benchmark computation inline — same logic as employer_benchmark.py."""
    from routers.employer_benchmark import _estimate_percentile, _interpret_percentile
    from data.employer_benchmarks.industry_mapping import resolve_industry

    benchmarks = get_benchmarks()
    if not benchmarks:
        return {"error": "Benchmark data not loaded"}

    national = benchmarks.get("national_averages", {})
    by_industry = benchmarks.get("by_industry", {})
    by_size = benchmarks.get("by_company_size", {})
    by_state = benchmarks.get("by_state", {})

    meps_industry = resolve_industry(industry)
    industry_data = by_industry.get(meps_industry, {})
    industry_median = industry_data.get("employer_single_pepm") or national.get("employer_single_monthly_pepm", 558)

    size_data = by_size.get(company_size, {})
    size_median = size_data.get("employer_single_pepm") or industry_median

    state_data = by_state.get(state, {})
    state_factor = state_data.get("cost_index", 1.0)

    adjusted_median = round(industry_median * state_factor, 2)

    # Prefer industry-specific percentiles; fall back to national
    has_industry_pctiles = bool(industry_data.get("p10_pepm"))
    if has_industry_pctiles:
        p10 = industry_data["p10_pepm"] * state_factor
        p25 = industry_data["p25_pepm"] * state_factor
        p50 = industry_data["p50_pepm"] * state_factor
        p75 = industry_data["p75_pepm"] * state_factor
        p90 = industry_data["p90_pepm"] * state_factor
        percentile_source = "industry"
    else:
        p10 = national.get("p10_pepm", 342) * state_factor
        p25 = national.get("p25_pepm", 441) * state_factor
        p50 = national.get("p50_pepm", 552) * state_factor
        p75 = national.get("p75_pepm", 658) * state_factor
        p90 = national.get("p90_pepm", 789) * state_factor
        percentile_source = "national"

    percentile = _estimate_percentile(pepm_input, p10, p25, p50, p75, p90)
    dollar_gap_monthly = round(pepm_input - adjusted_median, 2)
    dollar_gap_annual = round(dollar_gap_monthly * 12, 2)

    return {
        "input": {
            "industry": industry,
            "company_size": company_size,
            "state": state,
            "pepm_input": pepm_input,
        },
        "benchmarks": {
            "national_median_pepm": round(p50, 2),
            "industry_median_pepm": round(industry_median, 2),
            "adjusted_median_pepm": adjusted_median,
            "size_band_median_pepm": round(size_median, 2),
            "state_cost_index": state_factor,
        },
        "result": {
            "percentile": round(percentile, 1),
            "dollar_gap_monthly": dollar_gap_monthly,
            "dollar_gap_annual": dollar_gap_annual,
            "interpretation": _interpret_percentile(percentile),
            "percentile_source": percentile_source,
        },
        "distribution": {
            "p10": round(p10, 2),
            "p25": round(p25, 2),
            "p50": round(p50, 2),
            "p75": round(p75, 2),
            "p90": round(p90, 2),
        },
    }


# ---------------------------------------------------------------------------
# POST /api/broker/clients/onboard — add client + run benchmark immediately
# ---------------------------------------------------------------------------

@router.post("/clients/onboard")
async def onboard_client(req: BrokerOnboardRequest, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    employer_email = (req.employer_email or "").strip().lower() or None
    firm_name = user["company"].get("name", "")

    # Check plan limit
    plan_info = _get_broker_plan(sb, user["company_id"])
    if plan_info["at_limit"]:
        raise HTTPException(status_code=403, detail="CLIENT_LIMIT_REACHED")

    # Create or update broker-employer link (no employer account required)
    link_email = employer_email or f"pending-{uuid.uuid4().hex[:8]}@broker-onboarded"
    existing = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", broker_email)
        .eq("employer_email", link_email)
        .execute()
    )

    ecr = req.resolved_employee_count_range
    link_data = {
        "broker_email": broker_email,
        "employer_email": link_email,
        "status": "onboarded",
        "company_name": req.company_name,
        "employee_count_range": ecr,
        "industry": req.industry,
        "state": req.state,
        "carrier": req.carrier or "",
    }
    if req.renewal_month:
        link_data["renewal_month"] = req.renewal_month

    if existing.data:
        sb.table("broker_employer_links").update(link_data).eq("id", existing.data[0]["id"]).execute()
    else:
        sb.table("broker_employer_links").insert(link_data).execute()

    # Compute PEPM estimate
    employee_count = _employee_range_midpoint(ecr)
    pepm = req.estimated_pepm
    if not pepm and req.estimated_annual_spend:
        pepm = round(req.estimated_annual_spend / (employee_count * 12), 2)
    if not pepm:
        # Use national median as fallback
        benchmarks = get_benchmarks() or {}
        national = benchmarks.get("national_averages", {})
        pepm = national.get("employer_single_monthly_pepm", 558)

    # Run benchmark
    size_band = _range_to_size_band(ecr)
    benchmark_result = _run_benchmark(req.industry, size_band, req.state, pepm)

    # Store in broker_client_benchmarks
    share_token = str(uuid.uuid4())
    insert_data = {
        "broker_email": broker_email,
        "employer_email": link_email,
        "company_name": req.company_name,
        "employee_count": employee_count,
        "industry": req.industry,
        "state": req.state,
        "carrier": req.carrier or "",
        "estimated_pepm": pepm,
        "benchmark_result": benchmark_result,
        "share_token": share_token,
    }

    result = sb.table("broker_client_benchmarks").insert(insert_data).execute()
    benchmark_id = result.data[0]["id"] if result.data else None

    site_url = os.environ.get("VITE_SITE_URL", "https://civicscale.ai")
    share_url = f"{site_url}/employer/shared-report/{share_token}"

    return {
        "benchmark_id": benchmark_id,
        "benchmark_result": benchmark_result,
        "share_token": share_token,
        "share_url": share_url,
        "employer_email": link_email,
        "company_name": req.company_name,
        "firm_name": firm_name,
    }


# ---------------------------------------------------------------------------
# POST /api/broker/clients/bulk-onboard — add multiple clients at once
# ---------------------------------------------------------------------------

@router.post("/clients/bulk-onboard")
async def bulk_onboard(req: BulkOnboardRequest, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    firm_name = user["company"].get("name", "")

    if len(req.clients) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 clients per bulk upload.")

    # Validate all rows first
    row_errors = []
    for i, row in enumerate(req.clients):
        missing = []
        if not row.company_name.strip():
            missing.append("company_name")
        if not row.employee_count_range.strip():
            missing.append("employee_count_range")
        if not row.industry.strip():
            missing.append("industry")
        if not row.state.strip():
            missing.append("state")
        if missing:
            row_errors.append({"row": i, "company_name": row.company_name, "missing_fields": missing})

    if row_errors:
        raise HTTPException(status_code=400, detail={"message": "Validation failed", "errors": row_errors})

    site_url = os.environ.get("VITE_SITE_URL", "https://civicscale.ai")
    results = []

    for row in req.clients:
        try:
            link_email = f"pending-{uuid.uuid4().hex[:8]}@broker-onboarded"

            link_data = {
                "broker_email": broker_email,
                "employer_email": link_email,
                "status": "onboarded",
                "company_name": row.company_name.strip(),
                "employee_count_range": row.employee_count_range,
                "industry": row.industry,
                "state": row.state,
                "carrier": row.carrier or "",
            }
            if row.renewal_month:
                link_data["renewal_month"] = f"{row.renewal_month}-01"

            sb.table("broker_employer_links").insert(link_data).execute()

            # Compute PEPM
            employee_count = _employee_range_midpoint(row.employee_count_range)
            pepm = row.estimated_pepm
            if not pepm:
                benchmarks = get_benchmarks() or {}
                national = benchmarks.get("national_averages", {})
                pepm = national.get("employer_single_monthly_pepm", 558)

            # Run benchmark
            size_band = _range_to_size_band(row.employee_count_range)
            benchmark_result = _run_benchmark(row.industry, size_band, row.state, pepm)

            # Store benchmark
            share_token = str(uuid.uuid4())
            insert_data = {
                "broker_email": broker_email,
                "employer_email": link_email,
                "company_name": row.company_name.strip(),
                "employee_count": employee_count,
                "industry": row.industry,
                "state": row.state,
                "carrier": row.carrier or "",
                "estimated_pepm": pepm,
                "benchmark_result": benchmark_result,
                "share_token": share_token,
            }
            sb.table("broker_client_benchmarks").insert(insert_data).execute()

            share_url = f"{site_url}/employer/shared-report/{share_token}"
            results.append({
                "company_name": row.company_name.strip(),
                "success": True,
                "share_url": share_url,
                "benchmark_result": benchmark_result,
                "error": None,
            })
        except Exception as exc:
            results.append({
                "company_name": row.company_name.strip(),
                "success": False,
                "share_url": None,
                "benchmark_result": None,
                "error": str(exc),
            })

    succeeded = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])

    # Send bulk onboard summary email
    b_name = user.get("full_name") or "there"
    failed_line = f"<br/>{failed} failed" if failed > 0 else ""
    send_email(
        to=broker_email,
        subject=f"Your bulk benchmark is ready \u2014 {succeeded} client{'s' if succeeded != 1 else ''} analyzed",
        html=f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px;">
            <h2 style="color: #1B3A5C; margin-bottom: 16px;">Bulk Benchmark Complete</h2>
            <p style="color: #475569; font-size: 15px; line-height: 1.8;">Hi {b_name},</p>
            <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                Your bulk benchmark job is complete.
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                {succeeded} client{'s' if succeeded != 1 else ''} benchmarked successfully{failed_line}
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                View your book of business: <a href="https://broker.civicscale.ai/dashboard" style="color: #0D7377;">broker.civicscale.ai/dashboard</a>
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                &mdash; CivicScale
            </p>
        </div>
        """,
    )

    return {"results": results, "total": len(results), "succeeded": succeeded, "failed": failed, "firm_name": firm_name}


# ---------------------------------------------------------------------------
# GET /api/broker/clients/{employer_email}/share-link
# ---------------------------------------------------------------------------

@router.get("/clients/{employer_email}/share-link")
async def get_share_link(employer_email: str, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="No access to this employer.")

    # Find most recent benchmark
    bench = (
        sb.table("broker_client_benchmarks")
        .select("id, share_token, share_token_created_at")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if bench.data:
        token = bench.data[0]["share_token"]
    else:
        raise HTTPException(status_code=404, detail="No benchmark found for this client. Run a benchmark first.")

    site_url = os.environ.get("VITE_SITE_URL", "https://civicscale.ai")
    return {
        "share_token": token,
        "share_url": f"{site_url}/employer/shared-report/{token}",
    }


# ---------------------------------------------------------------------------
# POST /api/broker/clients/{employer_email}/notify
# ---------------------------------------------------------------------------

@router.post("/clients/{employer_email}/notify")
async def notify_client(employer_email: str, req: NotifyClientRequest, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("id, company_name")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="No access to this employer.")

    firm_name = user["company"].get("name", "your broker")

    # Get share token
    bench = (
        sb.table("broker_client_benchmarks")
        .select("share_token, company_name")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not bench.data:
        raise HTTPException(status_code=404, detail="No benchmark found. Run a benchmark first.")

    share_token = bench.data[0]["share_token"]
    company_name = bench.data[0].get("company_name") or link.data[0].get("company_name") or "your company"
    site_url = os.environ.get("VITE_SITE_URL", "https://civicscale.ai")
    share_url = f"{site_url}/employer/shared-report/{share_token}"
    subscribe_url = f"{site_url}/billing/employer/subscribe"

    # Send email via Resend
    if e_email.endswith("@broker-onboarded"):
        return {"sent": False, "reason": "No real employer email on file."}

    message_type = req.message_type or "benchmark"

    if message_type == "upgrade":
        subject = f"{firm_name} recommends upgrading your Parity Employer plan"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px;">
            <h2 style="color: #1B3A5C; margin-bottom: 8px;">Unlock Deeper Savings Insights</h2>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                Hi — {firm_name} has been reviewing your benefits data on the Parity Employer
                platform and recommends upgrading to get access to advanced analytics that
                could help {company_name} identify significant cost savings.
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                With a subscription, you'll unlock:
            </p>
            <ul style="color: #475569; font-size: 14px; line-height: 1.8; padding-left: 20px;">
                <li>Unlimited claims analysis</li>
                <li>Reference-based pricing calculator</li>
                <li>Contract rate parser</li>
                <li>Monthly trend monitoring with AI alerts</li>
            </ul>
            <div style="text-align: center; margin: 28px 0;">
                <a href="{subscribe_url}" style="display: inline-block; background: #0D7377; color: #fff;
                   padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;
                   font-size: 15px;">
                    View Plans &amp; Subscribe
                </a>
            </div>
            <p style="color: #64748b; font-size: 13px;">
                Plans start at $99/month with a 30-day free trial.
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
            <p style="color: #94a3b8; font-size: 12px;">
                This recommendation was sent by {firm_name} via the Parity Employer platform
                by CivicScale. Questions? Reply to your broker directly.
            </p>
        </div>
        """
    else:
        subject = f"{firm_name} prepared a benefits benchmark for {company_name}"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px;">
            <h2 style="color: #1B3A5C; margin-bottom: 8px;">Your Benefits Benchmark is Ready</h2>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                Hi — {firm_name} prepared a benefits benchmark for {company_name} to help
                identify opportunities heading into your next renewal cycle. This report compares
                your health plan costs to similar employers in your industry and region using
                national survey data.
            </p>
            <p style="color: #475569; font-size: 14px; line-height: 1.7; background: #fffbeb;
               border: 1px solid #fde68a; border-radius: 8px; padding: 14px 16px;">
                This is a starting point for your renewal conversation, not a report card on your current plan.
                Costs above median are common and driven by many factors — your broker can walk you through
                the details and next steps.
            </p>
            <div style="text-align: center; margin: 28px 0;">
                <a href="{share_url}" style="display: inline-block; background: #0D7377; color: #fff;
                   padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600;
                   font-size: 15px;">
                    View Your Benchmark Report
                </a>
            </div>
            <p style="color: #64748b; font-size: 13px;">
                No login required — click the link above to see your results.
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
            <p style="color: #94a3b8; font-size: 12px;">
                This report was prepared by {firm_name} using the Parity Employer
                benchmarking platform by CivicScale. Questions about this report?
                Contact {firm_name} directly — they can walk you through the findings
                and discuss next steps for your renewal.
            </p>
        </div>
        """

    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print(f"[BrokerNotify] RESEND_API_KEY not set, would send to {e_email}")
            return {"sent": False, "reason": "Email service not configured."}

        resend.api_key = resend_key
        resend.Emails.send({
            "from": "Parity Employer <notifications@civicscale.ai>",
            "to": [e_email],
            "subject": subject,
            "html": html_body,
        })
        print(f"[BrokerNotify] Sent {message_type} email to {e_email}")
        return {"sent": True}
    except Exception as exc:
        print(f"[BrokerNotify] Email send failed: {exc}")
        return {"sent": False, "reason": str(exc)}


# ---------------------------------------------------------------------------
# GET /api/broker/clients/{employer_email}/activity
# ---------------------------------------------------------------------------

@router.get("/clients/{employer_email}/activity")
async def client_activity(employer_email: str, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="No access to this employer.")

    events = []

    # Broker benchmarks
    benchmarks = (
        sb.table("broker_client_benchmarks")
        .select("id, created_at, view_count, first_viewed_at")
        .eq("employer_email", e_email)
        .order("created_at", desc=True)
        .execute()
    )
    for b in (benchmarks.data or []):
        events.append({
            "type": "benchmark_created",
            "label": "Broker benchmark created",
            "timestamp": b["created_at"],
        })
        if b.get("first_viewed_at"):
            events.append({
                "type": "report_viewed",
                "label": f"Shared report viewed ({b.get('view_count', 1)}x)",
                "timestamp": b["first_viewed_at"],
            })

    # Claims uploads
    claims = (
        sb.table("employer_claims_uploads")
        .select("id, filename_original, created_at")
        .eq("email", e_email)
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    for c in (claims.data or []):
        events.append({
            "type": "claims_uploaded",
            "label": f"Claims uploaded: {c.get('filename_original', 'file')}",
            "timestamp": c["created_at"],
        })

    # Scorecard sessions
    try:
        scorecards = (
            sb.table("employer_scorecard_sessions")
            .select("id, created_at")
            .eq("email", e_email)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        for s in (scorecards.data or []):
            events.append({
                "type": "scorecard_run",
                "label": "Plan scorecard generated",
                "timestamp": s["created_at"],
            })
    except Exception:
        pass  # Table may not exist

    # Subscriptions
    subs = (
        sb.table("employer_subscriptions")
        .select("id, tier, status, created_at")
        .eq("email", e_email)
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    for s in (subs.data or []):
        events.append({
            "type": "subscribed",
            "label": f"Subscribed: {s.get('tier', 'unknown')} ({s.get('status', 'unknown')})",
            "timestamp": s["created_at"],
        })

    # Sort all events by timestamp descending
    events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    return {"events": events}


# ---------------------------------------------------------------------------
# GET /api/broker/portfolio
# ---------------------------------------------------------------------------

@router.get("/portfolio")
async def broker_portfolio(authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]

    # Get all linked clients
    links = (
        sb.table("broker_employer_links")
        .select("employer_email, company_name, employee_count_range, industry, state, carrier, renewal_month, linked_at")
        .eq("broker_email", broker_email)
        .order("linked_at", desc=True)
        .execute()
    )

    clients = []
    total_annual_excess = 0
    subscribers_count = 0
    now = datetime.now(timezone.utc)
    ninety_days = now + timedelta(days=90)
    clients_renewing_90 = 0

    for link in (links.data or []):
        emp_email = link["employer_email"]

        # Most recent benchmark
        bench = (
            sb.table("broker_client_benchmarks")
            .select("benchmark_result, share_token, view_count, created_at")
            .eq("broker_email", broker_email)
            .eq("employer_email", emp_email)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        bench_data = bench.data[0] if bench.data else None

        # Subscription status
        sub = (
            sb.table("employer_subscriptions")
            .select("status")
            .eq("email", emp_email)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        sub_status = sub.data[0].get("status") if sub.data else "none"

        # Claims uploads count
        uploads = (
            sb.table("employer_claims_uploads")
            .select("id", count="exact")
            .eq("email", emp_email)
            .execute()
        )
        uploads_count = uploads.count if uploads.count is not None else 0

        # Determine activity status
        has_viewed = bench_data and bench_data.get("view_count", 0) > 0
        if sub_status == "active":
            activity_status = "subscriber"
            subscribers_count += 1
        elif uploads_count > 0:
            activity_status = "uploaded"
        elif has_viewed:
            activity_status = "viewed"
        else:
            activity_status = "benchmark_only"

        # Extract benchmark result data
        pepm = None
        percentile = None
        gap_per_employee = None
        annual_gap = None
        if bench_data and bench_data.get("benchmark_result"):
            br = bench_data["benchmark_result"]
            br_input = br.get("input", {})
            br_result = br.get("result", {})
            pepm = br_input.get("pepm_input")
            percentile = br_result.get("percentile")
            gap_per_employee = br_result.get("dollar_gap_monthly")
            annual_gap = br_result.get("dollar_gap_annual")
            if annual_gap and annual_gap > 0:
                total_annual_excess += annual_gap

        # Renewal check
        renewal_month = link.get("renewal_month")
        if renewal_month:
            try:
                rd = datetime.fromisoformat(renewal_month.replace("Z", "+00:00")) if isinstance(renewal_month, str) else renewal_month
                if hasattr(rd, 'tzinfo') and rd.tzinfo is None:
                    from datetime import timezone as tz
                    rd = rd.replace(tzinfo=tz.utc)
                if now <= rd <= ninety_days:
                    clients_renewing_90 += 1
            except (ValueError, TypeError):
                pass

        # Last activity timestamp
        last_activity = bench_data.get("created_at") if bench_data else link.get("linked_at")

        clients.append({
            "employer_email": emp_email,
            "company_name": link.get("company_name") or emp_email,
            "employee_count_range": link.get("employee_count_range"),
            "industry": link.get("industry"),
            "state": link.get("state"),
            "carrier": link.get("carrier"),
            "renewal_month": renewal_month,
            "pepm": pepm,
            "percentile": percentile,
            "gap_per_employee": gap_per_employee,
            "annual_gap": annual_gap,
            "activity_status": activity_status,
            "share_token": bench_data.get("share_token") if bench_data else None,
            "last_activity_at": last_activity,
        })

    return {
        "clients": clients,
        "summary": {
            "total_clients": len(clients),
            "total_annual_excess": round(total_annual_excess, 2),
            "clients_renewing_90_days": clients_renewing_90,
            "subscribers_count": subscribers_count,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/broker/renewal-pipeline — renewal timeline with checklist status
# ---------------------------------------------------------------------------

@router.get("/renewal-pipeline")
async def renewal_pipeline(authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]

    # Get all linked clients
    links = (
        sb.table("broker_employer_links")
        .select("employer_email, company_name, employee_count_range, industry, state, carrier, renewal_month")
        .eq("broker_email", broker_email)
        .order("renewal_month")
        .execute()
    )

    now = datetime.now(timezone.utc)

    renewing_soon = []      # <=90 days
    renewing_upcoming = []  # 91-180 days
    renewing_later = []     # >180 days
    no_renewal_date = []

    for link in (links.data or []):
        emp_email = link["employer_email"]

        # Check benchmark exists
        bench = (
            sb.table("broker_client_benchmarks")
            .select("id")
            .eq("broker_email", broker_email)
            .eq("employer_email", emp_email)
            .limit(1)
            .execute()
        )
        has_benchmark = bool(bench.data)

        # Check claims upload exists
        claims = (
            sb.table("employer_claims_uploads")
            .select("id")
            .eq("email", emp_email)
            .limit(1)
            .execute()
        )
        has_claims = bool(claims.data)

        # Check scorecard exists
        try:
            scorecard = (
                sb.table("employer_scorecard_sessions")
                .select("id")
                .eq("email", emp_email)
                .limit(1)
                .execute()
            )
            has_scorecard = bool(scorecard.data)
        except Exception:
            has_scorecard = False

        client_entry = {
            "employer_email": emp_email,
            "company_name": link.get("company_name") or emp_email,
            "employee_count_range": link.get("employee_count_range"),
            "renewal_month": link.get("renewal_month"),
            "checklist": {
                "benchmark_run": has_benchmark,
                "claims_check": has_claims,
                "scorecard_graded": has_scorecard,
                "renewal_prep_report": False,
            },
        }

        renewal_month = link.get("renewal_month")
        if not renewal_month:
            no_renewal_date.append(client_entry)
            continue

        try:
            rd = datetime.fromisoformat(renewal_month.replace("Z", "+00:00")) if isinstance(renewal_month, str) else renewal_month
            if hasattr(rd, "tzinfo") and rd.tzinfo is None:
                rd = rd.replace(tzinfo=timezone.utc)
            days_until = (rd - now).days
            client_entry["days_until_renewal"] = days_until

            if days_until <= 90:
                renewing_soon.append(client_entry)
            elif days_until <= 180:
                renewing_upcoming.append(client_entry)
            else:
                renewing_later.append(client_entry)
        except (ValueError, TypeError):
            no_renewal_date.append(client_entry)

    # Sort each bucket by days_until_renewal ascending
    renewing_soon.sort(key=lambda c: c.get("days_until_renewal", 9999))
    renewing_upcoming.sort(key=lambda c: c.get("days_until_renewal", 9999))
    renewing_later.sort(key=lambda c: c.get("days_until_renewal", 9999))

    return {
        "renewing_soon": renewing_soon,
        "renewing_upcoming": renewing_upcoming,
        "renewing_later": renewing_later,
        "no_renewal_date": no_renewal_date,
    }


# ---------------------------------------------------------------------------
# GET /api/broker/renewal-prep/{company_name} — assembled renewal prep data
# ---------------------------------------------------------------------------

@router.get("/renewal-prep/{company_name}")
async def renewal_prep(company_name: str, authorization: str = Header(None)):
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    decoded_name = company_name.replace("-", " ")

    broker_info = {
        "firm_name": user["company"].get("name", ""),
        "contact_name": user.get("full_name", ""),
    }

    # Find matching client link (case-insensitive match on company name)
    links = (
        sb.table("broker_employer_links")
        .select("employer_email, company_name, employee_count_range, industry, state, carrier, renewal_month")
        .eq("broker_email", broker_email)
        .execute()
    )

    link = None
    for l in (links.data or []):
        if (l.get("company_name") or "").lower() == decoded_name.lower():
            link = l
            break

    if not link:
        raise HTTPException(status_code=404, detail=f"Client '{decoded_name}' not found in your book of business.")

    emp_email = link["employer_email"]

    # Most recent benchmark
    bench = (
        sb.table("broker_client_benchmarks")
        .select("benchmark_result, estimated_pepm, share_token, created_at")
        .eq("broker_email", broker_email)
        .eq("employer_email", emp_email)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    bench_data = bench.data[0] if bench.data else None

    # Build benchmark section
    benchmark_section = {"available": False}
    if bench_data and bench_data.get("benchmark_result"):
        br = bench_data["benchmark_result"]
        br_result = br.get("result", {})
        br_input = br.get("input", {})
        br_benchmarks = br.get("benchmarks", {})
        br_dist = br.get("distribution", {})

        site_url = os.environ.get("VITE_SITE_URL", "https://civicscale.ai")
        benchmark_section = {
            "available": True,
            "pepm": br_input.get("pepm_input") or bench_data.get("estimated_pepm"),
            "percentile": br_result.get("percentile"),
            "adjusted_median": br_benchmarks.get("adjusted_median_pepm"),
            "annual_gap": br_result.get("dollar_gap_annual"),
            "monthly_gap": br_result.get("dollar_gap_monthly"),
            "interpretation": br_result.get("interpretation"),
            "share_url": f"{site_url}/employer/shared-report/{bench_data.get('share_token', '')}",
            "distribution": br_dist,
        }

    # Most recent claims upload
    claims_upload = (
        sb.table("employer_claims_uploads")
        .select("total_claims, total_paid, total_excess_2x, top_flagged_cpt, top_flagged_excess, created_at")
        .eq("email", emp_email)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    claims_section = {"available": False}
    if claims_upload.data:
        cu = claims_upload.data[0]
        results_json = cu.get("results_json") or {}
        claims_section = {
            "available": True,
            "total_claims": cu.get("total_claims", 0),
            "total_paid": cu.get("total_paid", 0),
            "excess_amount": cu.get("total_excess_2x", 0),
            "top_cpt": cu.get("top_flagged_cpt", ""),
            "level2": results_json.get("level2"),
        }

    # Most recent scorecard
    scorecard_section = {"available": False}
    try:
        scorecard = (
            sb.table("employer_scorecard_sessions")
            .select("results_json, created_at")
            .eq("email", emp_email)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if scorecard.data and scorecard.data[0].get("results_json"):
            sc = scorecard.data[0]["results_json"]
            scorecard_section = {
                "available": True,
                "grade": sc.get("grade", ""),
                "score": sc.get("score"),
                "savings_potential": sc.get("savings_potential_pepm"),
            }
    except Exception:
        pass

    return {
        "broker": broker_info,
        "client": {
            "company_name": link.get("company_name") or decoded_name,
            "industry": link.get("industry", ""),
            "state": link.get("state", ""),
            "employee_count_range": link.get("employee_count_range", ""),
            "carrier": link.get("carrier", ""),
            "renewal_month": link.get("renewal_month"),
            "employer_email": emp_email,
        },
        "benchmark": benchmark_section,
        "claims": claims_section,
        "scorecard": scorecard_section,
        "generated_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------------------
# POST /api/broker/profile/logo — upload broker logo to Supabase storage
# ---------------------------------------------------------------------------

@router.post("/profile/logo")
async def upload_broker_logo(
    file: UploadFile = File(...),
    authorization: str = Header(None),
):
    user, sb = _require_broker(authorization)
    company_id = user["company_id"]

    # Validate file type
    allowed = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PNG, JPG, GIF, or WebP image.")

    # Read file content
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 2MB.")

    # Determine extension
    ext_map = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp", "image/svg+xml": "svg"}
    ext = ext_map.get(file.content_type, "png")
    storage_path = f"broker-logos/{company_id}/logo.{ext}"

    try:
        # Upload to Supabase storage (upsert)
        try:
            sb.storage.from_("broker-assets").remove([storage_path])
        except Exception:
            pass
        sb.storage.from_("broker-assets").upload(storage_path, content, {"content-type": file.content_type})

        # Get public URL
        public_url = sb.storage.from_("broker-assets").get_public_url(storage_path)

        # Update companies table
        sb.table("companies").update({"logo_url": public_url}).eq("id", company_id).execute()

        return {"logo_url": public_url}
    except Exception as exc:
        print(f"[BrokerLogo] Upload failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to upload logo: {str(exc)}")


# ---------------------------------------------------------------------------
# POST /api/broker/send-renewal-reminders — cron-triggered 90-day reminders
# ---------------------------------------------------------------------------

@router.post("/send-renewal-reminders")
async def send_renewal_reminders(request: Request):
    """Send 90-day renewal reminder emails. Protected by X-Cron-Secret header."""
    cron_secret = os.environ.get("CRON_SECRET")
    if not cron_secret or request.headers.get("X-Cron-Secret") != cron_secret:
        raise HTTPException(status_code=403, detail="Unauthorized.")

    sb = _get_supabase()
    now = datetime.now(timezone.utc)
    target_date = now + timedelta(days=90)

    # Find all links with renewal_month ~90 days from now (within a 7-day window)
    window_start = (target_date - timedelta(days=3)).strftime("%Y-%m-%d")
    window_end = (target_date + timedelta(days=4)).strftime("%Y-%m-%d")

    links = (
        sb.table("broker_employer_links")
        .select("id, broker_email, employer_email, company_name, renewal_month, reminder_sent_90d")
        .gte("renewal_month", window_start)
        .lte("renewal_month", window_end)
        .execute()
    )

    sent_count = 0
    for link in (links.data or []):
        if link.get("reminder_sent_90d"):
            continue

        broker_email = link.get("broker_email", "")
        emp_email = link.get("employer_email", "")
        company = link.get("company_name") or emp_email
        renewal_month = link.get("renewal_month", "")

        # Get broker name from company_users
        cu = sb.table("company_users").select("full_name").eq("email", broker_email).limit(1).execute()
        broker_name = cu.data[0].get("full_name", "there") if cu.data else "there"

        # Build checklist status
        has_benchmark = bool(
            sb.table("broker_client_benchmarks").select("id").eq("broker_email", broker_email).eq("employer_email", emp_email).limit(1).execute().data
        )
        has_claims = bool(
            sb.table("employer_claims_uploads").select("id").eq("email", emp_email).limit(1).execute().data
        )
        try:
            has_scorecard = bool(
                sb.table("employer_scorecard_sessions").select("id").eq("email", emp_email).limit(1).execute().data
            )
        except Exception:
            has_scorecard = False

        check = lambda done: "\u2713" if done else "\u25CB"
        slug = company.lower().replace(" ", "-")
        renewal_display = ""
        try:
            rd = datetime.fromisoformat(renewal_month.replace("Z", "+00:00")) if isinstance(renewal_month, str) else renewal_month
            renewal_display = rd.strftime("%B %Y")
        except (ValueError, TypeError, AttributeError):
            renewal_display = renewal_month or "upcoming"

        send_email(
            to=broker_email,
            subject=f"{company} renews in 90 days \u2014 are you ready?",
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 520px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #1B3A5C; margin-bottom: 16px;">Renewal Reminder</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">Hi {broker_name},</p>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                    <strong>{company}</strong>'s health plan renews in approximately 90 days ({renewal_display}).
                </p>
                <p style="color: #475569; font-size: 15px; line-height: 1.8; font-weight: 600;">
                    Renewal prep checklist:
                </p>
                <p style="color: #475569; font-size: 15px; line-height: 2.0; margin: 0;">
                    {check(has_benchmark)} Benchmark run<br/>
                    {check(has_claims)} Claims data analyzed<br/>
                    {check(has_scorecard)} Plan scorecard graded<br/>
                    \u25CB Renewal prep report generated
                </p>
                <p style="margin-top: 16px;">
                    <a href="https://broker.civicscale.ai/renewal-prep/{slug}?broker_email={broker_email}"
                       style="color: #0D7377; font-weight: 600; text-decoration: none;">
                        View renewal prep report &rarr;
                    </a>
                </p>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                    Brokers who arrive at renewal with independent data get better outcomes for their clients.
                </p>
                <p style="color: #475569; font-size: 15px; line-height: 1.8;">
                    &mdash; CivicScale
                </p>
            </div>
            """,
        )

        # Mark as sent
        sb.table("broker_employer_links").update({"reminder_sent_90d": True}).eq("id", link["id"]).execute()
        sent_count += 1

    return {"sent": sent_count}


# ---------------------------------------------------------------------------
# Prospect benchmarking — preliminary assessments for potential clients
# ---------------------------------------------------------------------------

@router.post("/prospect-benchmark")
async def prospect_benchmark(req: ProspectBenchmarkRequest, authorization: str = Header(None)):
    """Run a preliminary benchmark for a prospect using only segment data (no PEPM)."""
    user, sb = _require_broker(authorization)
    broker_email = user["email"]

    # Build segment distribution
    from routers.employer_benchmark import _interpret_percentile
    from data.employer_benchmarks.industry_mapping import resolve_industry

    benchmarks = get_benchmarks()
    if not benchmarks:
        raise HTTPException(status_code=500, detail="Benchmark data not loaded.")

    national = benchmarks.get("national_averages", {})
    by_industry = benchmarks.get("by_industry", {})
    by_state = benchmarks.get("by_state", {})

    meps_industry = resolve_industry(req.industry)
    industry_data = by_industry.get(meps_industry, {})
    industry_median = industry_data.get("employer_single_pepm") or national.get("employer_single_monthly_pepm", 558)

    state_data = by_state.get(req.state, {})
    state_factor = state_data.get("cost_index", 1.0)

    # Build percentile distribution
    has_industry_pctiles = bool(industry_data.get("p10_pepm"))
    if has_industry_pctiles:
        p10 = round(industry_data["p10_pepm"] * state_factor, 2)
        p25 = round(industry_data["p25_pepm"] * state_factor, 2)
        p50 = round(industry_data["p50_pepm"] * state_factor, 2)
        p75 = round(industry_data["p75_pepm"] * state_factor, 2)
        p90 = round(industry_data["p90_pepm"] * state_factor, 2)
    else:
        p10 = round(national.get("p10_pepm", 342) * state_factor, 2)
        p25 = round(national.get("p25_pepm", 441) * state_factor, 2)
        p50 = round(national.get("p50_pepm", 552) * state_factor, 2)
        p75 = round(national.get("p75_pepm", 658) * state_factor, 2)
        p90 = round(national.get("p90_pepm", 789) * state_factor, 2)

    size_band = _range_to_size_band(req.employee_count_range)
    segment = f"{req.industry} \u00B7 {size_band} \u00B7 {req.state}"

    # Talking points
    talking_points = [
        f"Employers in {req.industry} in {req.state} typically spend between ${int(p25)} and ${int(p75)} per employee per month on health coverage.",
    ]

    if req.industry in ("Construction", "Manufacturing"):
        talking_points.append(
            "Physical labor industries tend to have higher-than-average orthopedic and injury-related costs \u2014 procedure-level analysis often identifies significant savings opportunities."
        )
    elif req.industry in ("Professional Services", "Finance / Real Estate / Insurance"):
        talking_points.append(
            "White-collar employers often have higher specialty and mental health utilization \u2014 pharmacy costs are frequently the fastest-growing line item."
        )

    if req.employee_count_range in ("250-500", "500-1000", "1000+"):
        talking_points.append(
            "Employers your size are typically self-insured or could benefit from self-funding analysis \u2014 reference-based pricing programs have shown 15\u201325% savings in this segment."
        )

    talking_points.append(
        "Without seeing your actual claims data, we can\u2019t confirm where you fall in this range \u2014 but this gives us a starting point for your renewal conversation."
    )

    result_json = {
        "company_name": req.company_name,
        "segment": segment,
        "typical_range": {"p25": p25, "p50": p50, "p75": p75},
        "full_distribution": {"p10": p10, "p25": p25, "p50": p50, "p75": p75, "p90": p90},
        "industry_median": round(industry_median, 2),
        "state_cost_index": state_factor,
        "talking_points": talking_points,
        "disclaimer": "This is a preliminary assessment based on industry benchmarks for similar employers. Actual costs require plan data to confirm.",
    }

    # Persist
    try:
        sb.table("broker_prospect_benchmarks").insert({
            "broker_email": broker_email,
            "company_name": req.company_name,
            "employee_count_range": req.employee_count_range,
            "industry": req.industry,
            "state": req.state,
            "carrier": req.carrier or "",
            "result_json": result_json,
        }).execute()
    except Exception as exc:
        print(f"[ProspectBenchmark] Failed to save: {exc}")

    return result_json


@router.get("/prospects")
async def list_prospects(authorization: str = Header(None)):
    """Return recent prospect benchmarks for a broker."""
    user, sb = _require_broker(authorization)
    broker_email = user["email"]

    prospects = (
        sb.table("broker_prospect_benchmarks")
        .select("id, company_name, employee_count_range, industry, state, carrier, result_json, created_at")
        .eq("broker_email", broker_email)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    return {"prospects": prospects.data or []}


# ---------------------------------------------------------------------------
# POST /api/broker/invite-employer — invite employer client (commission tracking)
# ---------------------------------------------------------------------------

@router.post("/invite-employer")
async def invite_employer(req: InviteEmployerRequest, authorization: str = Header(None)):
    """Invite an employer client. Creates invitation + commission tracking record."""
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    company_id = user["company_id"]
    employer_email = req.email.strip().lower()

    firm_name = user["company"].get("name", "your broker")
    inviter_name = user.get("full_name") or broker_email

    # Check if already invited
    existing = sb.table("company_invitations").select("id").eq(
        "invited_email", employer_email
    ).eq("referring_company_id", company_id).eq("status", "pending").execute()

    if existing.data:
        return {"invited": False, "reason": "This employer has already been invited."}

    # Create company_invitation with employer_referral type
    invite = sb.table("company_invitations").insert({
        "company_id": company_id,  # broker's company
        "invited_email": employer_email,
        "invited_by_email": broker_email,
        "role": "admin",  # employer will be admin of their own company
        "invitation_type": "employer_referral",
        "referring_company_id": company_id,
    }).execute()

    # Create pending commission record
    sb.table("broker_commissions").insert({
        "broker_company_id": company_id,
        "commission_rate": user["company"].get("broker_commission_rate", 0.20),
        "status": "pending",
    }).execute()

    # Send invitation email
    signup_url = "https://employer.civicscale.ai/signup"
    send_email(
        to=employer_email,
        subject=f"{inviter_name} from {firm_name} invites you to Parity Employer",
        html=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
            <h2 style="color: #0d9488;">You've been invited to Parity Employer</h2>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                {inviter_name} from {firm_name} is inviting you to try Parity Employer — a platform
                that helps self-insured employers identify excess health plan spend through
                claims analysis, benchmarking, and plan grading.
            </p>
            <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                Get started with a 30-day free trial — no credit card required to explore.
            </p>
            <a href="{signup_url}" style="display: inline-block; background: #0d9488; color: white;
                padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: bold;
                font-size: 15px; margin: 16px 0;">
                Start Free Trial &rarr;
            </a>
            <p style="color: #64748b; font-size: 13px; margin-top: 16px;">
                Questions about this invitation? Contact {firm_name} directly — they can
                walk you through the platform.
            </p>
            <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
        </div>
        """,
    )

    return {"invited": True, "email": employer_email}


# ---------------------------------------------------------------------------
# POST /api/broker/clients/{employer_email}/claims-upload
# ---------------------------------------------------------------------------

@router.post("/clients/{employer_email}/claims-upload")
async def broker_claims_upload(
    employer_email: str,
    request: Request,
    file: UploadFile = File(...),
    zip_code: str = Form(...),
    column_mapping: Optional[str] = Form(None),
    authorization: str = Header(None),
):
    """Broker uploads claims file on behalf of an employer client.
    Reuses employer_claims analysis logic. Stores results tagged with employer_email."""
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="You do not have access to this employer's data.")

    check_rate_limit(request, max_requests=10)

    # --- Parse file ---
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 10 MB limit")
    filename = file.filename or "upload"

    fname = filename.lower()
    is_835 = fname.endswith((".835", ".edi")) or (fname.endswith(".txt") and b"ISA" in content[:200])
    is_zip = fname.endswith(".zip")

    source_format = "csv_excel"
    mapping = None

    if is_835:
        source_format = "835_edi"
        text = content.decode("utf-8", errors="replace")
        if "ISA" not in text[:200]:
            raise HTTPException(status_code=400, detail="File does not appear to be a valid 835 EDI file")
        parsed = parse_835(text)
        if not parsed.get("line_items"):
            raise HTTPException(status_code=400, detail="No line items found in 835 EDI file")
        df = _edi_items_to_df(parsed["line_items"], parsed.get("payee_name", ""))

    elif is_zip:
        source_format = "835_zip"
        all_items = []
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                edi_names = [n for n in zf.namelist() if n.lower().endswith((".835", ".edi"))]
                if not edi_names:
                    raise HTTPException(status_code=400, detail="ZIP contains no .835 or .edi files")
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
            raise HTTPException(status_code=400, detail="No valid 835 line items found in ZIP")
        df = _edi_items_to_df(all_items)

    else:
        try:
            if fname.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(content))
            else:
                df = pd.read_csv(io.BytesIO(content))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Could not parse file: {exc}")

    if df.empty:
        raise HTTPException(status_code=400, detail="File contains no data")

    # --- Column mapping (CSV/Excel only) ---
    if source_format == "csv_excel":
        columns = list(df.columns)
        if column_mapping:
            try:
                mapping = json.loads(column_mapping)
            except json.JSONDecodeError:
                pass
        if not mapping:
            mapping_result = _call_claude(
                system_prompt=COLUMN_MAPPING_PROMPT,
                user_content=json.dumps({"columns": columns, "sample_rows": df.head(5).to_dict(orient="records")}),
                max_tokens=1024,
            )
            if mapping_result and mapping_result.get("mappings"):
                mapping = mapping_result["mappings"]
            else:
                raise HTTPException(status_code=422, detail={"error": "Could not auto-map columns", "columns": columns})
        cpt_col = mapping.get("cpt_code")
        paid_col = mapping.get("paid_amount")
        billed_col = mapping.get("billed_amount")
        if not cpt_col or cpt_col not in df.columns:
            raise HTTPException(status_code=422, detail=f"CPT code column '{cpt_col}' not found")
        if not paid_col or paid_col not in df.columns:
            raise HTTPException(status_code=422, detail=f"Paid amount column '{paid_col}' not found")
    else:
        cpt_col = "cpt_code"
        paid_col = "paid_amount"
        billed_col = "billed_amount"
        mapping = {"cpt_code": "cpt_code", "paid_amount": "paid_amount", "billed_amount": "billed_amount"}

    # --- Resolve locality ---
    carrier, locality = resolve_locality(zip_code)
    if not carrier or not locality:
        raise HTTPException(status_code=400, detail=f"Could not resolve locality for ZIP {zip_code}")

    # --- Analyze each claim ---
    results = []
    total_paid = 0.0
    total_excess_2x = 0.0

    for _, row in df.iterrows():
        cpt = str(row.get(cpt_col, "")).strip()
        if not cpt:
            continue
        paid = _safe_float(row.get(paid_col, 0))
        billed = _safe_float(row.get(billed_col, 0)) if billed_col and billed_col in df.columns else None
        svc_date = str(row.get("service_date", "")).strip() or None
        rate_val, source, _, _, rate_note = lookup_rate(cpt, "CPT", carrier, locality, date_of_service=svc_date)

        line = {
            "cpt_code": cpt, "paid_amount": paid, "billed_amount": billed,
            "medicare_rate": rate_val, "medicare_source": source if rate_val else None,
            "rate_note": rate_note,
            "ratio": None, "flag": None, "excess_amount": None,
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

        total_paid += paid
        results.append(line)

    # --- Summary ---
    excess_by_cpt = {}
    for r in results:
        ex = r.get("excess_amount") or 0
        if ex > 0:
            excess_by_cpt[r["cpt_code"]] = excess_by_cpt.get(r["cpt_code"], 0) + ex
    top_flagged_cpt = max(excess_by_cpt, key=excess_by_cpt.get) if excess_by_cpt else None
    top_flagged_excess = round(excess_by_cpt.get(top_flagged_cpt, 0), 2) if top_flagged_cpt else 0.0

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

    # --- AI narrative ---
    narrative = None
    try:
        top_findings_lines = []
        flagged_sorted = sorted([r for r in results if r.get("flag")], key=lambda r: r.get("ratio") or 0, reverse=True)
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
            "Use neutral, factual language.\n\n"
            f"Claims analyzed: {len(results)}\nTotal paid: ${total_paid:,.0f}\n"
            f"Excess vs 2x Medicare benchmark: ${total_excess_2x:,.0f}\n"
            f"Top findings:\n" + "\n".join(top_findings_lines) + "\n\n"
            "Write only the summary paragraph."
        )
        narrative = _generate_narrative(narrative_prompt)
    except Exception as exc:
        print(f"[Broker Claims Upload] Narrative generation failed (non-fatal): {exc}")

    # --- Level 2 analytics ---
    level2 = None
    try:
        level2 = _run_level2_analytics(df, results)
    except Exception as exc:
        print(f"[Broker Claims Upload] Level 2 analytics failed (non-fatal): {exc}")

    # Pricing tier
    annualized_excess = total_excess_2x * 12
    pricing_tier = assign_pricing_tier(annualized_excess)
    tier_info = EMPLOYER_PRICE_TIERS[pricing_tier]

    rate_notes = list({r["rate_note"] for r in results if r.get("rate_note")})
    rate_year_note = rate_notes[0] if len(rate_notes) == 1 else (
        "; ".join(rate_notes) if rate_notes else None
    )

    response = {
        "summary": summary,
        "narrative": narrative,
        "line_items": results[:500],
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

    # --- Persist ---
    session_id = None
    try:
        insert_result = sb.table("employer_claims_uploads").insert({
            "email": e_email,
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
        print(f"[Broker Claims Upload] Failed to save session: {exc}")

    response["session_id"] = session_id
    response["uploaded_by_broker"] = broker_email
    return response


# ---------------------------------------------------------------------------
# POST /api/broker/clients/{employer_email}/scorecard-upload
# ---------------------------------------------------------------------------

@router.post("/clients/{employer_email}/scorecard-upload")
async def broker_scorecard_upload(
    employer_email: str,
    request: Request,
    file: UploadFile = File(...),
    plan_name: Optional[str] = Form(None),
    network_type: Optional[str] = Form(None),
    authorization: str = Header(None),
):
    """Broker uploads SBC PDF on behalf of an employer client.
    Reuses employer_scorecard scoring logic. Stores results tagged with employer_email."""
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="You do not have access to this employer's data.")

    check_rate_limit(request, max_requests=20)

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    # Encode PDF for Claude vision
    b64_content = base64.b64encode(content).decode("utf-8")

    parsed = _call_claude(
        system_prompt=SBC_EXTRACTION_PROMPT,
        user_content=[
            {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64_content},
            },
            {
                "type": "text",
                "text": "Please extract the plan details from this Summary of Benefits and Coverage document.",
            },
        ],
        max_tokens=2048,
    )

    if not parsed:
        raise HTTPException(status_code=422, detail="Could not parse the SBC document. Please try a clearer PDF.")

    if plan_name:
        parsed["plan_name"] = plan_name
    if network_type:
        parsed["network_type"] = network_type

    # --- Score the plan ---
    scored_criteria = []
    total_weighted_score = 0.0
    total_weight = 0

    for criterion in SCORING_CRITERIA:
        try:
            score = criterion["evaluate"](parsed)
        except Exception:
            score = 50
        if score is None:
            score = 50
        weighted = score * criterion["weight"] / 100
        total_weighted_score += weighted
        total_weight += criterion["weight"]
        scored_criteria.append({
            "id": criterion["id"],
            "label": criterion["label"],
            "weight": criterion["weight"],
            "score": round(score, 1),
            "weighted_score": round(weighted, 2),
        })

    overall_score = round((total_weighted_score / total_weight) * 100, 1) if total_weight > 0 else 50.0
    grade = _score_to_grade(overall_score)
    interpretation = _grade_interpretation(grade, overall_score)
    savings_per_ee = _estimate_savings(parsed, overall_score)

    result = {
        "plan_name": parsed.get("plan_name", plan_name or "Unknown Plan"),
        "network_type": parsed.get("network_type", network_type or "Unknown"),
        "grade": grade,
        "score": overall_score,
        "savings_estimate_per_ee": savings_per_ee,
        "parsed_plan": parsed,
        "scored_criteria": scored_criteria,
        "interpretation": interpretation,
        "uploaded_by_broker": broker_email,
    }

    # --- Persist ---
    try:
        sb.table("employer_scorecard_sessions").insert({
            "email": e_email,
            "plan_name": result["plan_name"],
            "network_type": result["network_type"],
            "grade": grade,
            "score": float(overall_score),
            "savings_estimate_per_ee": float(savings_per_ee) if savings_per_ee else None,
            "parsed_plan_json": parsed,
            "scored_criteria_json": scored_criteria,
        }).execute()
    except Exception as exc:
        print(f"[Broker Scorecard Upload] Failed to save session: {exc}")

    return result


# ---------------------------------------------------------------------------
# POST /api/broker/clients/{employer_email}/caa-letter — AI-generated CAA letter
# ---------------------------------------------------------------------------

CAA_LETTER_SYSTEM_PROMPT = """You are a healthcare benefits compliance attorney drafting a formal data request letter under the Consolidated Appropriations Act (CAA) of 2021.

Write a professional, attorney-quality CAA Section 204 data request letter. The letter must:

1. Use the exact statutory citation: Section 204 of Division BB of the Consolidated Appropriations Act, 2021 (CAA 2021), codified at 29 U.S.C. § 1185i
2. Reference ERISA § 404(a)(1) fiduciary duty obligations
3. Reference DOL guidance from November 2021 and EBSA Field Assistance Bulletin 2021-04
4. Request the following specific data:
   (a) Complete 835 EDI remittance files for the current and prior plan year
   (b) Pharmacy claims data including NDC codes and any rebate credits applied
   (c) Monthly per-employee-per-month (PEPM) cost breakdown by medical, pharmacy, and administrative components
   (d) Stop-loss premiums and specific/aggregate attachment points
   (e) Network access fees and any other fees not included in the PEPM breakdown
5. Include a 30-business-day response deadline citing the carrier's contractual obligation
6. Include a firm but professional closing that references the broker's status as broker of record
7. Use [DATE] as the date placeholder
8. Fill in all provided data: broker name, firm name, company name, carrier name, state, approximate employee count, plan year

Return ONLY valid JSON with a single key:
{"letter": "<the full letter text with newlines as \\n>"}

No preamble, no commentary, no markdown formatting outside the JSON."""


@router.post("/clients/{employer_email}/caa-letter")
async def generate_caa_letter(employer_email: str, authorization: str = Header(None)):
    """Generate an AI-powered CAA Section 204 data request letter for a client."""
    user, sb = _require_broker(authorization)
    broker_email = user["email"]
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("company_name, carrier, state, employee_count_range, renewal_month, industry")
        .eq("broker_email", broker_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="No access to this employer.")

    client = link.data[0]
    company_name = client.get("company_name", "")
    carrier = client.get("carrier", "")
    state = client.get("state", "")
    employee_range = client.get("employee_count_range", "")
    renewal_month = client.get("renewal_month")
    broker_name = user.get("full_name", "")
    firm_name = user["company"].get("name", "")

    # Estimate employee count from range
    range_map = {"1-50": 25, "51-100": 75, "101-250": 175, "251-500": 375, "501-1000": 750, "1001-5000": 3000, "5001+": 7500}
    approx_employees = range_map.get(employee_range, 100)

    # Compute plan year from renewal_month
    now = datetime.now(timezone.utc)
    if renewal_month:
        try:
            # renewal_month is an ISO date string like "2026-04-01"
            rm_date = datetime.fromisoformat(str(renewal_month).replace("Z", "+00:00"))
            plan_year = f"{now.year - 1}-{now.year}" if rm_date.month > now.month else f"{now.year}-{now.year + 1}"
        except (ValueError, TypeError):
            plan_year = str(now.year)
    else:
        plan_year = str(now.year)

    prompt_data = json.dumps({
        "broker_name": broker_name or "Broker of Record",
        "firm_name": firm_name or "Benefits Advisory Firm",
        "company_name": company_name,
        "carrier": carrier or "the plan carrier",
        "state": state or "",
        "approximate_employees": approx_employees,
        "plan_year": plan_year,
    })

    # Try AI generation
    letter_text = None
    try:
        ai_result = _call_claude(
            system_prompt=CAA_LETTER_SYSTEM_PROMPT,
            user_content=prompt_data,
            max_tokens=4096,
        )
        if ai_result and isinstance(ai_result, dict) and ai_result.get("letter"):
            letter_text = ai_result["letter"]
    except Exception as exc:
        print(f"[Broker CAA] AI generation failed: {exc}")

    # Fallback to static template
    if not letter_text:
        letter_text = f"""[DATE]

{carrier or "[Carrier Name]"}
Claims Data Department
[Carrier Address]

RE: Request for Claims Data and Cost Information Pursuant to CAA Section 204
Plan Sponsor: {company_name}
Approximate Covered Lives: {approx_employees}
Plan Year: {plan_year}

Dear Claims Department:

This letter constitutes a formal request for plan-level claims data and cost information pursuant to Section 204 of Division BB of the Consolidated Appropriations Act, 2021 (CAA 2021), codified at 29 U.S.C. § 1185i, and consistent with the fiduciary obligations under ERISA § 404(a)(1).

As the broker of record for {company_name}, I am acting on behalf of the plan fiduciaries to fulfill their statutory obligation to obtain and review this information. The Department of Labor's November 2021 guidance and EBSA Field Assistance Bulletin 2021-04 make clear that plan fiduciaries must obtain sufficient information to assess the reasonableness of compensation and services provided.

We hereby request the following data for the current and prior plan year:

1. Complete 835 EDI electronic remittance files for all medical claims
2. Pharmacy claims data including NDC codes, quantities, days supply, and any rebate credits or retained rebates
3. Monthly per-employee-per-month (PEPM) cost breakdown by medical claims, pharmacy claims, and administrative fees
4. Stop-loss premiums, specific and aggregate attachment points, and any claims exceeding attachment points
5. Network access fees, clinical program fees, and any other fees not included in the base PEPM

Please provide this data within 30 business days of receipt of this letter, consistent with your contractual obligations and the requirements of applicable{' ' + state if state else ''} law.

This information is essential for the plan fiduciary to fulfill its duty of prudence under ERISA and to comply with the transparency requirements of the CAA. Failure to provide this data in a timely manner may constitute a breach of your administrative services agreement.

Please direct all data deliverables and correspondence to the undersigned.

Sincerely,

{broker_name or "[Broker Name]"}
{firm_name or "[Firm Name]"}
Broker of Record — {company_name}"""

    return {
        "letter": letter_text,
        "client_name": company_name,
        "carrier": carrier,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Broker Referral endpoints
# ---------------------------------------------------------------------------

class ReferralSendRequest(BaseModel):
    colleague_email: str
    colleague_name: Optional[str] = ""


@router.get("/referral")
async def get_or_create_referral(authorization: str = Header(None)):
    """Get or create referral code for this broker."""
    user, sb = _require_broker(authorization)
    company_id = user.get("company_id")
    broker_email = user.get("email", "")

    # Check existing referral code
    existing = sb.table("broker_referrals").select("referral_code").eq(
        "referrer_company_id", company_id
    ).limit(1).execute()

    if existing.data:
        code = existing.data[0]["referral_code"]
    else:
        code = uuid.uuid4().hex[:8].upper()
        sb.table("broker_referrals").insert({
            "referrer_company_id": company_id,
            "referrer_email": broker_email,
            "referral_code": code,
            "status": "pending",
        }).execute()

    # Stats
    all_referrals = sb.table("broker_referrals").select("status").eq(
        "referrer_company_id", company_id
    ).execute()
    referral_count = sum(1 for r in all_referrals.data if r["status"] != "pending")
    converted_count = sum(1 for r in all_referrals.data if r["status"] == "active")

    return {
        "referral_code": code,
        "referral_url": f"https://broker.civicscale.ai/signup?ref={code}",
        "referral_count": referral_count,
        "converted_count": converted_count,
    }


@router.post("/referral/send")
async def send_referral_email(body: ReferralSendRequest, authorization: str = Header(None)):
    """Send referral email to a colleague."""
    user, sb = _require_broker(authorization)
    company_id = user.get("company_id")
    broker_email = user.get("email", "")

    colleague_email = body.colleague_email.strip()
    if "@" not in colleague_email or "." not in colleague_email:
        raise HTTPException(status_code=400, detail="Invalid email address.")

    # Get referrer info
    referrer_name = user.get("full_name") or broker_email
    company_row = sb.table("companies").select("name").eq("id", company_id).single().execute()
    firm_name = company_row.data.get("name", "") if company_row.data else ""

    # Check already referred
    already = sb.table("broker_referrals").select("id").eq(
        "referrer_company_id", company_id
    ).eq("referred_email", colleague_email).execute()
    if already.data:
        return {"sent": False, "reason": "already_referred"}

    # Get referral code
    code_row = sb.table("broker_referrals").select("referral_code").eq(
        "referrer_company_id", company_id
    ).is_("referred_email", "null").limit(1).execute()

    if code_row.data:
        code = code_row.data[0]["referral_code"]
    else:
        code = uuid.uuid4().hex[:8].upper()

    # Insert referral record for this colleague
    sb.table("broker_referrals").insert({
        "referrer_company_id": company_id,
        "referrer_email": broker_email,
        "referral_code": code,
        "referred_email": colleague_email,
        "status": "pending",
    }).execute()

    # Send email
    colleague_first = body.colleague_name.strip() if body.colleague_name else ""
    greeting = f"Hi{' ' + colleague_first if colleague_first else ''},"
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 560px; margin: 0 auto; color: #1e293b;">
      <p>{greeting}</p>
      <p>{referrer_name} at {firm_name} asked us to send you a quick note.</p>
      <p>They've been using <strong>Parity Broker</strong> to benchmark their book of business against MEPS-IC data
      and generate CAA data request letters — and thought it might be useful for your practice too.</p>
      <p>It benchmarks any client against industry/region/size peers in about 60 seconds.
      The CAA letter generator alone saves about an hour per renewal.</p>
      <p style="margin: 24px 0;">
        <a href="https://broker.civicscale.ai/demo" style="display: inline-block; background: #0D7377; color: #fff;
        padding: 12px 28px; border-radius: 8px; font-weight: 600; text-decoration: none;">
          See a 4-step demo first &rarr;
        </a>
      </p>
      <p>Or <a href="https://broker.civicscale.ai/signup?ref={code}" style="color: #0D7377;">sign up free at broker.civicscale.ai</a></p>
      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
      <p style="font-size: 12px; color: #94a3b8;">
        You received this because {referrer_name} thought you'd find it useful.
        No opt-in required to visit — this is the only email you'll receive unless you sign up.
      </p>
    </div>
    """

    send_email(
        to=colleague_email,
        subject=f"{referrer_name} thinks you should see this benefits platform",
        html=html,
    )

    return {"sent": True, "colleague_email": colleague_email}


@router.get("/referral/stats")
async def referral_stats(authorization: str = Header(None)):
    """Return full list of referrals made by this broker."""
    user, sb = _require_broker(authorization)
    company_id = user.get("company_id")

    rows = sb.table("broker_referrals").select(
        "referred_email, status, created_at"
    ).eq("referrer_company_id", company_id).not_.is_("referred_email", "null").order(
        "created_at", desc=True
    ).execute()

    referrals = [
        {"referred_email": r["referred_email"], "status": r["status"], "created_at": r["created_at"]}
        for r in rows.data
    ]
    total = len(referrals)
    converted = sum(1 for r in referrals if r["status"] == "active")

    return {"referrals": referrals, "total": total, "converted": converted}
