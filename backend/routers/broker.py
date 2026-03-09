"""
Broker Portal endpoints — custom OTP auth + client management + freemium onboarding.

Endpoints:
  POST /api/broker/auth/send-otp     — send 6-digit OTP to broker email
  POST /api/broker/auth/verify-otp   — verify OTP, return broker session
  GET  /api/broker/clients           — list linked employer clients
  POST /api/broker/clients/add       — link an employer to this broker
  DELETE /api/broker/clients/{employer_email} — unlink an employer
  GET  /api/broker/clients/{employer_email}/summary — aggregated employer summary
  POST /api/broker/clients/onboard   — add client + run benchmark (no employer account required)
  GET  /api/broker/clients/{employer_email}/share-link — get/generate share link
  POST /api/broker/clients/{employer_email}/notify — send benchmark email to employer
  GET  /api/broker/clients/{employer_email}/activity — employer activity timeline
"""

import os
import random
import string
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional

from routers.employer_shared import _get_supabase, check_rate_limit, get_benchmarks

router = APIRouter(prefix="/api/broker", tags=["broker"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SendOtpRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    code: str


class AddClientRequest(BaseModel):
    broker_email: str
    employer_email: str


class ClientsListRequest(BaseModel):
    broker_email: str


class BrokerOnboardRequest(BaseModel):
    broker_email: str
    company_name: str
    employee_count_range: str  # "<100", "100-250", "250-500", "500-1000", "1000+"
    industry: str
    state: str
    carrier: str
    employer_email: Optional[str] = None
    estimated_pepm: Optional[float] = None
    estimated_annual_spend: Optional[float] = None
    renewal_month: Optional[str] = None  # ISO date string, e.g. "2026-01-01"


class NotifyClientRequest(BaseModel):
    broker_email: str
    message_type: Optional[str] = "benchmark"  # "benchmark" or "upgrade"


class BrokerSignupRequest(BaseModel):
    email: str
    name: str
    firm_name: str
    phone: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP code."""
    return "".join(random.choices(string.digits, k=length))


def _send_otp_email(email: str, code: str):
    """Send OTP code via Resend."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print(f"[BrokerOTP] RESEND_API_KEY not set, code for {email}: {code}")
            return
        resend.api_key = resend_key

        resend.Emails.send({
            "from": "Parity Employer <notifications@civicscale.ai>",
            "to": [email],
            "subject": f"Your Parity Broker login code: {code}",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #1B3A5C; margin-bottom: 8px;">Broker Portal Login</h2>
                <p style="color: #64748b; font-size: 15px;">
                    Use the code below to sign in to your Parity broker dashboard.
                </p>
                <div style="background: #f0fdfa; border: 2px solid #0D7377; border-radius: 12px;
                            padding: 24px; text-align: center; margin: 24px 0;">
                    <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1B3A5C;">
                        {code}
                    </span>
                </div>
                <p style="color: #94a3b8; font-size: 13px;">
                    This code expires in 10 minutes. If you didn't request this, you can ignore this email.
                </p>
            </div>
            """,
        })
        print(f"[BrokerOTP] Code sent to {email}")
    except Exception as exc:
        print(f"[BrokerOTP] Email send failed: {exc}")


def _send_signup_otp_email(email: str, name: str, firm_name: str, code: str):
    """Send welcome + OTP verification email via Resend."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print(f"[BrokerSignup] RESEND_API_KEY not set, code for {email}: {code}")
            return
        resend.api_key = resend_key

        resend.Emails.send({
            "from": "Parity Employer <notifications@civicscale.ai>",
            "to": [email],
            "subject": "Welcome to Parity Employer — verify your email",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
                <h2 style="color: #1B3A5C; margin-bottom: 8px;">Welcome {name} from {firm_name}</h2>
                <p style="color: #475569; font-size: 15px; line-height: 1.7;">
                    Thanks for creating a Parity Employer broker account. Enter the code below
                    to verify your email and get started.
                </p>
                <div style="background: #f0fdfa; border: 2px solid #0D7377; border-radius: 12px;
                            padding: 24px; text-align: center; margin: 24px 0;">
                    <p style="color: #475569; font-size: 13px; margin: 0 0 8px;">Your verification code is:</p>
                    <span style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1B3A5C;">
                        {code}
                    </span>
                </div>
                <p style="color: #94a3b8; font-size: 13px;">
                    This code expires in 10 minutes.
                </p>
                <p style="color: #475569; font-size: 14px; line-height: 1.7;">
                    After verifying, you can start adding clients and running benchmarks immediately.
                </p>
            </div>
            """,
        })
        print(f"[BrokerSignup] Welcome + OTP sent to {email}")
    except Exception as exc:
        print(f"[BrokerSignup] Email send failed: {exc}")


# ---------------------------------------------------------------------------
# POST /api/broker/auth/send-otp
# ---------------------------------------------------------------------------

@router.post("/auth/send-otp")
async def send_otp(req: SendOtpRequest, request: Request):
    check_rate_limit(request, max_requests=10, window_seconds=3600)

    sb = _get_supabase()
    email = req.email.strip().lower()

    # Verify broker account exists and is active
    result = sb.table("broker_accounts").select("id, firm_name, is_active").eq("email", email).execute()
    if not result.data or not result.data[0].get("is_active", True):
        raise HTTPException(status_code=403, detail="This email is not registered as a broker account.")

    # Generate and store OTP
    code = _generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    # Invalidate any previous unused codes for this email
    sb.table("otp_codes").update({"used": True}).eq("email", email).eq("used", False).execute()

    # Insert new code
    sb.table("otp_codes").insert({
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "used": False,
    }).execute()

    # Send email
    _send_otp_email(email, code)

    return {"sent": True}


# ---------------------------------------------------------------------------
# POST /api/broker/auth/verify-otp
# ---------------------------------------------------------------------------

@router.post("/auth/verify-otp")
async def verify_otp(req: VerifyOtpRequest, request: Request):
    check_rate_limit(request, max_requests=20, window_seconds=3600)

    sb = _get_supabase()
    email = req.email.strip().lower()
    code = req.code.strip()

    # Look up the OTP
    result = (
        sb.table("otp_codes")
        .select("id, expires_at, used")
        .eq("email", email)
        .eq("code", code)
        .eq("used", False)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid or expired code.")

    otp_row = result.data[0]

    # Check expiry
    expires_at = datetime.fromisoformat(otp_row["expires_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires_at:
        sb.table("otp_codes").update({"used": True}).eq("id", otp_row["id"]).execute()
        raise HTTPException(status_code=401, detail="Code has expired. Please request a new one.")

    # Mark used
    sb.table("otp_codes").update({"used": True}).eq("id", otp_row["id"]).execute()

    # Fetch broker info
    broker = sb.table("broker_accounts").select("id, email, firm_name, contact_name, status").eq("email", email).single().execute()

    # If broker was pending verification, activate them
    if broker.data and broker.data.get("status") == "pending_verification":
        sb.table("broker_accounts").update({"status": "active"}).eq("id", broker.data["id"]).execute()

    return {
        "verified": True,
        "broker": broker.data,
    }


# ---------------------------------------------------------------------------
# POST /api/broker/auth/signup
# ---------------------------------------------------------------------------

@router.post("/auth/signup")
async def broker_signup(req: BrokerSignupRequest, request: Request):
    check_rate_limit(request, max_requests=10, window_seconds=3600)

    sb = _get_supabase()
    email = req.email.strip().lower()
    name = req.name.strip()
    firm_name = req.firm_name.strip()
    phone = (req.phone or "").strip() or None

    # Check if email already exists
    existing = sb.table("broker_accounts").select("id").eq("email", email).execute()
    if existing.data:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Use the login page to sign in.",
        )

    # Insert new broker account
    sb.table("broker_accounts").insert({
        "email": email,
        "contact_name": name,
        "firm_name": firm_name,
        "phone": phone,
        "status": "pending_verification",
        "is_active": True,
    }).execute()

    # Generate and store OTP (8-digit)
    code = _generate_otp(length=8)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    sb.table("otp_codes").insert({
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "used": False,
    }).execute()

    # Send welcome + OTP email
    _send_signup_otp_email(email, name, firm_name, code)

    return {"message": "Verification code sent", "email": email}


# ---------------------------------------------------------------------------
# POST /api/broker/auth/resend-otp
# ---------------------------------------------------------------------------

@router.post("/auth/resend-otp")
async def resend_otp(req: SendOtpRequest, request: Request):
    check_rate_limit(request, max_requests=10, window_seconds=3600)

    sb = _get_supabase()
    email = req.email.strip().lower()

    # Verify broker account exists
    result = sb.table("broker_accounts").select("id, contact_name, firm_name").eq("email", email).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No account found with this email.")

    # Invalidate previous codes
    sb.table("otp_codes").update({"used": True}).eq("email", email).eq("used", False).execute()

    # Generate and store new OTP (8-digit)
    code = _generate_otp(length=8)
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    sb.table("otp_codes").insert({
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "used": False,
    }).execute()

    # Send OTP email
    _send_otp_email(email, code)

    return {"sent": True}


# ---------------------------------------------------------------------------
# GET /api/broker/clients?broker_email=...
# ---------------------------------------------------------------------------

@router.get("/clients")
async def list_clients(broker_email: str):
    sb = _get_supabase()
    email = broker_email.strip().lower()

    # Verify broker exists
    broker = sb.table("broker_accounts").select("id").eq("email", email).execute()
    if not broker.data:
        raise HTTPException(status_code=403, detail="Broker account not found.")

    # Get linked employers
    links = (
        sb.table("broker_employer_links")
        .select("employer_email, linked_at, status, company_name, employee_count_range, industry, state, carrier")
        .eq("broker_email", email)
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
            .eq("broker_email", email)
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

@router.post("/clients/add")
async def add_client(req: AddClientRequest):
    sb = _get_supabase()
    broker_email = req.broker_email.strip().lower()
    employer_email = req.employer_email.strip().lower()

    # Verify broker exists
    broker = sb.table("broker_accounts").select("id").eq("email", broker_email).execute()
    if not broker.data:
        raise HTTPException(status_code=403, detail="Broker account not found.")

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
# DELETE /api/broker/clients/{employer_email}?broker_email=...
# ---------------------------------------------------------------------------

@router.delete("/clients/{employer_email}")
async def remove_client(employer_email: str, broker_email: str):
    sb = _get_supabase()
    b_email = broker_email.strip().lower()
    e_email = employer_email.strip().lower()

    result = (
        sb.table("broker_employer_links")
        .delete()
        .eq("broker_email", b_email)
        .eq("employer_email", e_email)
        .execute()
    )

    removed = len(result.data) > 0 if result.data else False
    return {"removed": removed}


# ---------------------------------------------------------------------------
# GET /api/broker/clients/{employer_email}/summary?broker_email=...
# ---------------------------------------------------------------------------

@router.get("/clients/{employer_email}/summary")
async def client_summary(employer_email: str, broker_email: str):
    sb = _get_supabase()
    b_email = broker_email.strip().lower()
    e_email = employer_email.strip().lower()

    # Verify broker-employer link exists
    link = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", b_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="You do not have access to this employer's data.")

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
        "company_name": sub_data.get("company_name", e_email) if sub_data else e_email,
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
        },
        "upload_timeline": upload_timeline,
        "trends": trends_data.get("trend_data") if trends_data else None,
        "trends_computed_at": trends_data.get("computed_at") if trends_data else None,
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
async def onboard_client(req: BrokerOnboardRequest, request: Request):
    check_rate_limit(request, max_requests=10)

    sb = _get_supabase()
    broker_email = req.broker_email.strip().lower()
    employer_email = (req.employer_email or "").strip().lower() or None

    # Verify broker exists
    broker = sb.table("broker_accounts").select("id, firm_name").eq("email", broker_email).execute()
    if not broker.data:
        raise HTTPException(status_code=403, detail="Broker account not found.")

    firm_name = broker.data[0].get("firm_name", "")

    # Create or update broker-employer link (no employer account required)
    link_email = employer_email or f"pending-{uuid.uuid4().hex[:8]}@broker-onboarded"
    existing = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", broker_email)
        .eq("employer_email", link_email)
        .execute()
    )

    link_data = {
        "broker_email": broker_email,
        "employer_email": link_email,
        "status": "onboarded",
        "company_name": req.company_name,
        "employee_count_range": req.employee_count_range,
        "industry": req.industry,
        "state": req.state,
        "carrier": req.carrier,
    }
    if req.renewal_month:
        link_data["renewal_month"] = req.renewal_month

    if existing.data:
        sb.table("broker_employer_links").update(link_data).eq("id", existing.data[0]["id"]).execute()
    else:
        sb.table("broker_employer_links").insert(link_data).execute()

    # Compute PEPM estimate
    employee_count = _employee_range_midpoint(req.employee_count_range)
    pepm = req.estimated_pepm
    if not pepm and req.estimated_annual_spend:
        pepm = round(req.estimated_annual_spend / (employee_count * 12), 2)
    if not pepm:
        # Use national median as fallback
        benchmarks = get_benchmarks() or {}
        national = benchmarks.get("national_averages", {})
        pepm = national.get("employer_single_monthly_pepm", 558)

    # Run benchmark
    size_band = _range_to_size_band(req.employee_count_range)
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
        "carrier": req.carrier,
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

class BulkOnboardRow(BaseModel):
    company_name: str
    employee_count_range: str
    industry: str
    state: str
    carrier: Optional[str] = None
    estimated_pepm: Optional[float] = None
    renewal_month: Optional[str] = None  # format: "YYYY-MM"


class BulkOnboardRequest(BaseModel):
    broker_email: str
    clients: list[BulkOnboardRow]


@router.post("/clients/bulk-onboard")
async def bulk_onboard(req: BulkOnboardRequest, request: Request):
    check_rate_limit(request, max_requests=5)

    sb = _get_supabase()
    broker_email = req.broker_email.strip().lower()

    # Verify broker exists
    broker = sb.table("broker_accounts").select("id, firm_name").eq("email", broker_email).execute()
    if not broker.data:
        raise HTTPException(status_code=403, detail="Broker account not found.")

    firm_name = broker.data[0].get("firm_name", "")

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
    return {"results": results, "total": len(results), "succeeded": succeeded, "failed": failed, "firm_name": firm_name}


# ---------------------------------------------------------------------------
# GET /api/broker/clients/{employer_email}/share-link?broker_email=...
# ---------------------------------------------------------------------------

@router.get("/clients/{employer_email}/share-link")
async def get_share_link(employer_email: str, broker_email: str):
    sb = _get_supabase()
    b_email = broker_email.strip().lower()
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", b_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="No access to this employer.")

    # Find most recent benchmark
    bench = (
        sb.table("broker_client_benchmarks")
        .select("id, share_token, share_token_created_at")
        .eq("broker_email", b_email)
        .eq("employer_email", e_email)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if bench.data:
        token = bench.data[0]["share_token"]
    else:
        # No benchmark exists — generate a placeholder (shouldn't happen in normal flow)
        raise HTTPException(status_code=404, detail="No benchmark found for this client. Run a benchmark first.")

    site_url = os.environ.get("VITE_SITE_URL", "https://civicscale.ai")
    return {
        "share_token": token,
        "share_url": f"{site_url}/employer/shared-report/{token}",
    }


# ---------------------------------------------------------------------------
# POST /api/broker/clients/{employer_email}/notify?broker_email=...
# ---------------------------------------------------------------------------

@router.post("/clients/{employer_email}/notify")
async def notify_client(employer_email: str, req: NotifyClientRequest, request: Request):
    check_rate_limit(request, max_requests=10)

    sb = _get_supabase()
    b_email = req.broker_email.strip().lower()
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("id, company_name")
        .eq("broker_email", b_email)
        .eq("employer_email", e_email)
        .execute()
    )
    if not link.data:
        raise HTTPException(status_code=403, detail="No access to this employer.")

    # Get broker info
    broker = sb.table("broker_accounts").select("firm_name, contact_name").eq("email", b_email).execute()
    firm_name = broker.data[0].get("firm_name", "your broker") if broker.data else "your broker"

    # Get share token
    bench = (
        sb.table("broker_client_benchmarks")
        .select("share_token, company_name")
        .eq("broker_email", b_email)
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
                Plans start at $149/month with a 3x savings guarantee.
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
# GET /api/broker/clients/{employer_email}/activity?broker_email=...
# ---------------------------------------------------------------------------

@router.get("/clients/{employer_email}/activity")
async def client_activity(employer_email: str, broker_email: str):
    sb = _get_supabase()
    b_email = broker_email.strip().lower()
    e_email = employer_email.strip().lower()

    # Verify broker-employer link
    link = (
        sb.table("broker_employer_links")
        .select("id")
        .eq("broker_email", b_email)
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
# GET /api/broker/portfolio?broker_email=...
# ---------------------------------------------------------------------------

@router.get("/portfolio")
async def broker_portfolio(broker_email: str):
    sb = _get_supabase()
    email = broker_email.strip().lower()

    # Verify broker exists
    broker = sb.table("broker_accounts").select("id").eq("email", email).execute()
    if not broker.data:
        raise HTTPException(status_code=403, detail="Broker account not found.")

    # Get all linked clients
    links = (
        sb.table("broker_employer_links")
        .select("employer_email, company_name, employee_count_range, industry, state, carrier, renewal_month, linked_at")
        .eq("broker_email", email)
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
            .eq("broker_email", email)
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
# POST /api/broker/profile/logo — upload broker logo to Supabase storage
# ---------------------------------------------------------------------------

@router.post("/profile/logo")
async def upload_broker_logo(
    broker_email: str = Form(...),
    file: UploadFile = File(...),
):
    sb = _get_supabase()
    email = broker_email.strip().lower()

    # Verify broker exists
    broker = sb.table("broker_accounts").select("id").eq("email", email).execute()
    if not broker.data:
        raise HTTPException(status_code=403, detail="Broker account not found.")

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
    safe_email = email.replace("@", "_at_").replace(".", "_")
    storage_path = f"broker-logos/{safe_email}/logo.{ext}"

    try:
        # Upload to Supabase storage (upsert)
        try:
            sb.storage.from_("broker-assets").remove([storage_path])
        except Exception:
            pass
        sb.storage.from_("broker-assets").upload(storage_path, content, {"content-type": file.content_type})

        # Get public URL
        public_url = sb.storage.from_("broker-assets").get_public_url(storage_path)

        # Update broker_accounts
        sb.table("broker_accounts").update({"logo_url": public_url}).eq("id", broker.data[0]["id"]).execute()

        return {"logo_url": public_url}
    except Exception as exc:
        print(f"[BrokerLogo] Upload failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Failed to upload logo: {str(exc)}")
