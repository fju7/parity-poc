"""
Unified Auth — shared across all CivicScale products.

POST /api/auth/send-otp       — send OTP to email
POST /api/auth/verify-otp     — verify OTP, create session, return token
GET  /api/auth/me             — validate token, return user + company
POST /api/auth/logout         — delete session
POST /api/auth/invite         — admin invites user to company
PATCH /api/auth/users/{user_id} — admin updates role or status
DELETE /api/auth/users/{user_id} — admin removes user from company
GET  /api/auth/users          — list company users (admin/member)
POST /api/auth/accept-invite  — accept invitation via token
POST /api/auth/company        — create a new company + admin user
GET  /api/auth/company        — get company details
PATCH /api/auth/company       — update company details (admin only)
"""

import os
import uuid
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel

from routers.employer_shared import _get_supabase
from utils.email import send_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_EXPIRY_DAYS = 30
OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 8


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SendOtpRequest(BaseModel):
    email: str
    product: str  # 'employer' | 'broker' | 'provider' | 'health'

class VerifyOtpRequest(BaseModel):
    email: str
    code: str
    product: str

class CreateCompanyRequest(BaseModel):
    email: str
    full_name: str
    company_name: str
    company_type: str  # 'employer' | 'broker' | 'provider'
    industry: Optional[str] = None
    state: Optional[str] = None
    size_band: Optional[str] = None
    referral_code: Optional[str] = None

class InviteUserRequest(BaseModel):
    invited_email: str
    role: str = "member"

class UpdateUserRequest(BaseModel):
    role: Optional[str] = None
    status: Optional[str] = None

class AcceptInviteRequest(BaseModel):
    token: str
    email: str
    full_name: str

class UpdateCompanyRequest(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    state: Optional[str] = None
    size_band: Optional[str] = None

class DeletionRequestBody(BaseModel):
    confirm_company_name: str


# ---------------------------------------------------------------------------
# Auth helper — call this from any router to get current user
# ---------------------------------------------------------------------------

def get_current_user(authorization: str = None, sb=None):
    """
    Validate Bearer token from Authorization header.
    Returns dict with user, company, role.
    Raises 401 if invalid or expired.

    Usage in any router:
        from routers.auth import get_current_user
        user = get_current_user(request.headers.get("authorization"), sb)
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not sb:
        sb = _get_supabase()

    # Validate session
    now = datetime.now(timezone.utc).isoformat()
    session = sb.table("sessions").select("*").eq("id", token).gt("expires_at", now).execute()

    if not session.data:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please sign in again.")

    s = session.data[0]

    # Refresh last_active_at
    sb.table("sessions").update({"last_active_at": now}).eq("id", token).execute()

    # Get company user record
    company_user = sb.table("company_users").select("*").eq(
        "company_id", s["company_id"]
    ).eq("email", s["email"]).eq("status", "active").execute()

    if not company_user.data:
        raise HTTPException(status_code=401, detail="User account not found or suspended.")

    cu = company_user.data[0]

    # Get company
    company = sb.table("companies").select("*").eq("id", s["company_id"]).execute()
    if not company.data:
        raise HTTPException(status_code=401, detail="Company not found.")

    return {
        "email": s["email"],
        "company_id": s["company_id"],
        "company": company.data[0],
        "role": cu["role"],
        "full_name": cu.get("full_name"),
        "session_id": token,
        "product": s["product"],
    }


def require_admin(user: dict):
    """Raise 403 if user is not an admin."""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")


def get_employer_access(company: dict) -> dict:
    """
    Returns access level for an employer company.
    Used to gate features based on plan status.
    """
    plan = company.get("plan", "free")
    trial_ends_at = company.get("trial_ends_at")

    # Check if trial has expired
    if plan == "trial" and trial_ends_at:
        now = datetime.now(timezone.utc)
        ends = datetime.fromisoformat(trial_ends_at.replace("Z", "+00:00"))
        if now > ends:
            plan = "read_only"

    return {
        "plan": plan,
        "can_upload": plan in ("trial", "pro"),
        "can_analyze": plan in ("trial", "pro"),
        "can_export": plan in ("trial", "pro", "read_only"),
        "is_read_only": plan == "read_only",
        "is_active": plan in ("trial", "pro"),
        "trial_ends_at": trial_ends_at,
    }


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------

def _generate_otp(length=OTP_LENGTH):
    return "".join(random.choices(string.digits, k=length))


def _send_otp_email(email: str, code: str, product: str):
    product_names = {
        "employer": "Parity Employer",
        "broker": "Parity Broker",
        "provider": "Parity Provider",
        "health": "Parity Health",
        "signal": "Parity Signal",
    }
    product_name = product_names.get(product, "CivicScale")

    send_email(
        to=email,
        subject=f"Your {product_name} sign-in code: {code}",
        from_name=product_name,
        html=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
          <h2 style="color: #0d9488;">Your sign-in code</h2>
          <p>Enter this code to sign in to {product_name}:</p>
          <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #0d9488;
                       padding: 24px; background: #f0fdfa; border-radius: 8px; text-align: center;">
            {code}
          </div>
          <p style="color: #666; font-size: 14px; margin-top: 24px;">
            This code expires in {OTP_EXPIRY_MINUTES} minutes. If you didn't request this,
            you can safely ignore this email.
          </p>
          <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
        </div>
        """,
    )


# ---------------------------------------------------------------------------
# POST /api/auth/send-otp
# ---------------------------------------------------------------------------

@router.post("/send-otp")
async def send_otp(req: SendOtpRequest, request: Request):
    sb = _get_supabase()
    email = req.email.strip().lower()
    product = req.product.strip().lower()

    if product not in ("employer", "broker", "provider", "health"):
        raise HTTPException(status_code=400, detail="Invalid product")

    code = _generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

    # Delete any existing OTP for this email+product
    sb.table("otp_codes").delete().eq("email", email).eq("product", product).execute()

    # Insert new OTP
    sb.table("otp_codes").insert({
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "product": product,
    }).execute()

    _send_otp_email(email, code, product)

    return {"sent": True, "email": email}


# ---------------------------------------------------------------------------
# POST /api/auth/verify-otp
# ---------------------------------------------------------------------------

@router.post("/verify-otp")
async def verify_otp(req: VerifyOtpRequest, request: Request):
    sb = _get_supabase()
    email = req.email.strip().lower()
    product = req.product.strip().lower()
    now = datetime.now(timezone.utc)

    # Validate OTP
    otp = sb.table("otp_codes").select("*").eq("email", email).eq(
        "code", req.code.strip()
    ).eq("product", product).gt("expires_at", now.isoformat()).execute()

    if not otp.data:
        raise HTTPException(status_code=400, detail="Invalid or expired code. Please request a new one.")

    # Delete used OTP
    sb.table("otp_codes").delete().eq("email", email).eq("product", product).execute()

    # Look up company_user record
    company_user = sb.table("company_users").select(
        "*, companies(*)"
    ).eq("email", email).eq("status", "active").execute()

    # Filter to matching product type
    matched_user = None
    matched_company = None
    for cu in (company_user.data or []):
        c = cu.get("companies")
        if c and c.get("type") == product:
            matched_user = cu
            matched_company = c
            break

    if not matched_user:
        # User exists in otp_codes but has no company account yet
        # Return a special status so frontend can redirect to company creation
        return {
            "verified": True,
            "needs_company": True,
            "email": email,
            "product": product,
            "token": None,
            "user": None,
            "company": None,
        }

    # Update last_login_at
    sb.table("company_users").update({
        "last_login_at": now.isoformat()
    }).eq("id", matched_user["id"]).execute()

    # Create session
    session_id = str(uuid.uuid4())
    expires_at = (now + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")

    sb.table("sessions").insert({
        "id": session_id,
        "email": email,
        "company_id": matched_company["id"],
        "product": product,
        "expires_at": expires_at,
        "last_active_at": now.isoformat(),
        "ip_address": ip,
        "user_agent": ua[:255] if ua else None,
    }).execute()

    return {
        "verified": True,
        "needs_company": False,
        "token": session_id,
        "email": email,
        "product": product,
        "user": {
            "email": email,
            "full_name": matched_user.get("full_name"),
            "role": matched_user["role"],
        },
        "company": {
            "id": matched_company["id"],
            "name": matched_company["name"],
            "type": matched_company["type"],
            "industry": matched_company.get("industry"),
            "state": matched_company.get("state"),
        },
    }


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_me(authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)
    return user


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------

@router.post("/logout")
async def logout(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return {"logged_out": True}
    token = authorization.split(" ", 1)[1].strip()
    sb = _get_supabase()
    sb.table("sessions").delete().eq("id", token).execute()
    return {"logged_out": True}


# ---------------------------------------------------------------------------
# POST /api/auth/company — create company + first admin user
# ---------------------------------------------------------------------------

@router.post("/company")
async def create_company(req: CreateCompanyRequest):
    sb = _get_supabase()
    email = req.email.strip().lower()
    company_type = req.company_type.strip().lower()

    if company_type not in ("employer", "broker", "provider"):
        raise HTTPException(status_code=400, detail="Invalid company type")

    # Check if user already has a company of this type
    existing = sb.table("company_users").select(
        "id, companies(type)"
    ).eq("email", email).execute()

    for eu in (existing.data or []):
        if eu.get("companies", {}).get("type") == company_type:
            raise HTTPException(
                status_code=409,
                detail="You already have an account. Please sign in."
            )

    # Create company
    now = datetime.now(timezone.utc)
    company_data = {
        "name": req.company_name.strip(),
        "type": company_type,
        "industry": req.industry,
        "state": req.state,
        "size_band": req.size_band,
        "created_by_email": email,
    }
    # Provider signups start a 30-day trial immediately
    if company_type == "provider":
        company_data["plan"] = "trial"
        company_data["trial_started_at"] = now.isoformat()
        company_data["trial_ends_at"] = (now + timedelta(days=30)).isoformat()
    company = sb.table("companies").insert(company_data).execute()

    company_id = company.data[0]["id"]

    # Create admin user
    sb.table("company_users").insert({
        "company_id": company_id,
        "email": email,
        "full_name": req.full_name.strip(),
        "role": "admin",
        "status": "active",
    }).execute()

    # Auto-create session after company creation — no second OTP needed
    session_id = str(uuid.uuid4())
    expires_at = (now + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

    sb.table("sessions").insert({
        "id": session_id,
        "email": email,
        "company_id": company_id,
        "product": company_type,
        "expires_at": expires_at,
        "last_active_at": now.isoformat(),
    }).execute()

    # Track broker referral if referral_code provided
    if req.referral_code and company_type == "broker":
        try:
            ref_row = sb.table("broker_referrals").select("id").eq(
                "referral_code", req.referral_code.strip().upper()
            ).eq("status", "pending").limit(1).execute()
            if ref_row.data:
                sb.table("broker_referrals").update({
                    "referred_company_id": company_id,
                    "referred_email": email,
                    "status": "signed_up",
                    "converted_at": now.isoformat(),
                }).eq("id", ref_row.data[0]["id"]).execute()
        except Exception as e:
            print(f"[warn] referral tracking failed: {e}")

    return {
        "created": True,
        "token": session_id,
        "email": email,
        "company_id": company_id,
        "company_name": req.company_name,
        "company_type": company_type,
        "role": "admin",
        "user": {
            "email": email,
            "full_name": req.full_name.strip(),
            "role": "admin",
        },
        "company": {
            "id": company_id,
            "name": req.company_name.strip(),
            "type": company_type,
            "industry": req.industry,
            "state": req.state,
            "size_band": req.size_band,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/auth/company
# ---------------------------------------------------------------------------

@router.get("/company")
async def get_company(authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)
    return user["company"]


# ---------------------------------------------------------------------------
# PATCH /api/auth/company
# ---------------------------------------------------------------------------

@router.patch("/company")
async def update_company(req: UpdateCompanyRequest, authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)
    require_admin(user)

    updates = {k: v for k, v in req.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    sb.table("companies").update(updates).eq("id", user["company_id"]).execute()
    return {"updated": True}


# ---------------------------------------------------------------------------
# GET /api/auth/users — list company members
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)

    users = sb.table("company_users").select(
        "id, email, full_name, role, status, created_at, last_login_at, invited_by_email"
    ).eq("company_id", user["company_id"]).order("created_at").execute()

    return {"users": users.data or []}


# ---------------------------------------------------------------------------
# POST /api/auth/invite
# ---------------------------------------------------------------------------

@router.post("/invite")
async def invite_user(req: InviteUserRequest, authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)
    require_admin(user)

    invited_email = req.invited_email.strip().lower()

    # Check not already a member
    existing = sb.table("company_users").select("id").eq(
        "company_id", user["company_id"]
    ).eq("email", invited_email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="This person is already a member of your account.")

    # Create invitation
    invite = sb.table("company_invitations").insert({
        "company_id": user["company_id"],
        "invited_email": invited_email,
        "invited_by_email": user["email"],
        "role": req.role,
    }).execute()

    token = invite.data[0]["token"]
    company_name = user["company"]["name"]
    inviter_name = user.get("full_name") or user["email"]
    product = user["company"]["type"]

    product_names = {
        "employer": "Parity Employer",
        "broker": "Parity Broker",
        "provider": "Parity Provider",
        "signal": "Parity Signal",
    }
    product_name = product_names.get(product, "CivicScale")
    accept_url = f"https://civicscale.ai/accept-invite?token={token}"

    send_email(
        to=invited_email,
        subject=f"{inviter_name} invited you to {company_name} on {product_name}",
        from_name=product_name,
        html=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
          <h2 style="color: #0d9488;">You've been invited</h2>
          <p>{inviter_name} has invited you to join <strong>{company_name}</strong>
              on {product_name} as a <strong>{req.role}</strong>.</p>
          <a href="{accept_url}" style="display: inline-block; background: #0d9488; color: white;
              padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;
              margin: 16px 0;">Accept Invitation &rarr;</a>
          <p style="color: #666; font-size: 14px;">This invitation expires in 7 days.</p>
          <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
        </div>
        """,
    )

    return {"invited": True, "email": invited_email}


# ---------------------------------------------------------------------------
# POST /api/auth/accept-invite
# ---------------------------------------------------------------------------

@router.post("/accept-invite")
async def accept_invite(req: AcceptInviteRequest, request: Request):
    sb = _get_supabase()
    email = req.email.strip().lower()
    now = datetime.now(timezone.utc)

    # Validate token
    invite = sb.table("company_invitations").select("*").eq(
        "token", req.token
    ).eq("status", "pending").gt("expires_at", now.isoformat()).execute()

    if not invite.data:
        raise HTTPException(status_code=400, detail="Invitation not found or expired.")

    inv = invite.data[0]

    if inv["invited_email"] != email:
        raise HTTPException(status_code=400, detail="This invitation was sent to a different email address.")

    # Create company_users record
    sb.table("company_users").insert({
        "company_id": inv["company_id"],
        "email": email,
        "full_name": req.full_name.strip(),
        "role": inv["role"],
        "status": "active",
        "invited_by_email": inv["invited_by_email"],
    }).execute()

    # Mark invitation accepted
    sb.table("company_invitations").update({"status": "accepted"}).eq("id", inv["id"]).execute()

    # Get company for product type
    company = sb.table("companies").select("*").eq("id", inv["company_id"]).execute()
    product = company.data[0]["type"] if company.data else "employer"

    # Create session
    session_id = str(uuid.uuid4())
    expires_at = (now + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

    sb.table("sessions").insert({
        "id": session_id,
        "email": email,
        "company_id": inv["company_id"],
        "product": product,
        "expires_at": expires_at,
        "last_active_at": now.isoformat(),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:255],
    }).execute()

    return {
        "accepted": True,
        "token": session_id,
        "email": email,
        "company": company.data[0] if company.data else None,
    }


# ---------------------------------------------------------------------------
# PATCH /api/auth/users/{user_id}
# ---------------------------------------------------------------------------

@router.patch("/users/{user_id}")
async def update_user(user_id: str, req: UpdateUserRequest, authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)
    require_admin(user)

    # Verify target user is in same company
    target = sb.table("company_users").select("id, email, role").eq(
        "id", user_id
    ).eq("company_id", user["company_id"]).execute()

    if not target.data:
        raise HTTPException(status_code=404, detail="User not found in your account.")

    # Prevent admin from demoting themselves
    if target.data[0]["email"] == user["email"] and req.role and req.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot change your own admin role.")

    updates = {k: v for k, v in req.dict().items() if v is not None}
    sb.table("company_users").update(updates).eq("id", user_id).execute()

    return {"updated": True}


# ---------------------------------------------------------------------------
# DELETE /api/auth/users/{user_id}
# ---------------------------------------------------------------------------

@router.delete("/users/{user_id}")
async def remove_user(user_id: str, authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)
    require_admin(user)

    target = sb.table("company_users").select("id, email").eq(
        "id", user_id
    ).eq("company_id", user["company_id"]).execute()

    if not target.data:
        raise HTTPException(status_code=404, detail="User not found.")

    if target.data[0]["email"] == user["email"]:
        raise HTTPException(status_code=400, detail="You cannot remove yourself.")

    # Delete all sessions for this user at this company
    sb.table("sessions").delete().eq("email", target.data[0]["email"]).eq(
        "company_id", user["company_id"]
    ).execute()

    sb.table("company_users").delete().eq("id", user_id).execute()

    return {"removed": True}


# ---------------------------------------------------------------------------
# POST /api/auth/deletion-request
# ---------------------------------------------------------------------------

@router.post("/deletion-request")
async def request_deletion(req: DeletionRequestBody, authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)
    require_admin(user)

    company_name = user["company"]["name"]
    if req.confirm_company_name.strip().lower() != company_name.strip().lower():
        raise HTTPException(
            status_code=400,
            detail="Company name does not match. Please type your company name exactly to confirm."
        )

    # Get user_id from company_users
    cu = sb.table("company_users").select("id").eq(
        "company_id", user["company_id"]
    ).eq("email", user["email"]).execute()
    cu_id = cu.data[0]["id"] if cu.data else None

    # Insert deletion request
    sb.table("deletion_requests").insert({
        "company_id": user["company_id"],
        "requested_by": cu_id,
        "status": "pending",
    }).execute()

    # Send confirmation email to user
    send_email(
        to=user["email"],
        subject="Data Deletion Request Received — CivicScale",
        html=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
          <h2 style="color: #0d9488;">Data Deletion Request Received</h2>
          <p>We've received your request to delete all data for <strong>{company_name}</strong>.</p>
          <p>Our team will process this within 30 days as required by applicable regulations.
             You'll receive a confirmation email once the deletion is complete.</p>
          <p style="color: #666; font-size: 14px;">If you did not request this, please contact us
             immediately at support@civicscale.ai.</p>
          <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
        </div>
        """,
    )

    # Send internal notification to admin
    send_email(
        to="admin@civicscale.ai",
        subject=f"Data Deletion Request: {company_name}",
        html=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
          <h2 style="color: #DC2626;">Data Deletion Request</h2>
          <p><strong>Company:</strong> {company_name}</p>
          <p><strong>Company ID:</strong> {user["company_id"]}</p>
          <p><strong>Requested by:</strong> {user["email"]}</p>
          <p><strong>Product:</strong> {user["company"].get("type", "unknown")}</p>
          <p>Please process this deletion request within 30 days.</p>
        </div>
        """,
    )

    return {"requested": True, "company_name": company_name}
