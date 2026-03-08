"""
Broker Portal endpoints — custom OTP auth + client management.

Endpoints:
  POST /api/broker/auth/send-otp     — send 6-digit OTP to broker email
  POST /api/broker/auth/verify-otp   — verify OTP, return broker session
  GET  /api/broker/clients           — list linked employer clients
  POST /api/broker/clients/add       — link an employer to this broker
  DELETE /api/broker/clients/{employer_email} — unlink an employer
  GET  /api/broker/clients/{employer_email}/summary — aggregated employer summary
"""

import os
import random
import string
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from routers.employer_shared import _get_supabase, check_rate_limit

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
    broker = sb.table("broker_accounts").select("id, email, firm_name, contact_name").eq("email", email).single().execute()

    return {
        "verified": True,
        "broker": broker.data,
    }


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
        .select("employer_email, linked_at")
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
        clients.append({
            "employer_email": emp_email,
            "company_name": sub_data.get("company_name", emp_email),
            "employee_count": sub_data.get("employee_count"),
            "tier": sub_data.get("tier", "none"),
            "subscription_status": sub_data.get("status", "none"),
            "claims_uploads": uploads.count if uploads.count is not None else 0,
            "linked_at": link["linked_at"],
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
