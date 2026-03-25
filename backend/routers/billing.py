"""Parity Billing endpoints — multi-practice billing company management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Header, Request, UploadFile
from pydantic import BaseModel

from routers.auth import get_current_user, _generate_otp, _send_otp_email, OTP_EXPIRY_MINUTES, SESSION_EXPIRY_DAYS
from routers.employer_shared import _get_supabase
from utils.email import send_email

router = APIRouter(prefix="/api/billing", tags=["billing"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: str
    full_name: str
    company_name: str

class PracticeCreateRequest(BaseModel):
    practice_name: str
    contact_email: str

class UserInviteRequest(BaseModel):
    email: str
    role: str = "analyst"

class SendOtpRequest(BaseModel):
    email: str

class VerifyOtpRequest(BaseModel):
    email: str
    code: str


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _require_billing(authorization: str, sb=None):
    """Validate auth and ensure user belongs to a billing company."""
    if not sb:
        sb = _get_supabase()
    user = get_current_user(authorization, sb)
    if user["company"]["type"] != "billing":
        raise HTTPException(status_code=403, detail="Billing access only")
    return user, sb


def _get_billing_company(user: dict, sb):
    """Look up the billing_companies record linked to this user's company."""
    email = user["email"]
    billing_user = sb.table("billing_company_users").select(
        "billing_company_id, role"
    ).eq("email", email).eq("status", "active").limit(1).execute()

    if not billing_user.data:
        raise HTTPException(status_code=404, detail="No billing company found for this user.")

    bc_id = billing_user.data[0]["billing_company_id"]
    bc_role = billing_user.data[0]["role"]

    bc = sb.table("billing_companies").select("*").eq("id", bc_id).limit(1).execute()
    if not bc.data:
        raise HTTPException(status_code=404, detail="Billing company not found.")

    return bc.data[0], bc_role


# ---------------------------------------------------------------------------
# POST /api/billing/send-otp — thin wrapper around auth OTP
# ---------------------------------------------------------------------------

@router.post("/send-otp")
async def billing_send_otp(req: SendOtpRequest):
    sb = _get_supabase()
    email = req.email.strip().lower()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")

    code = _generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

    # Delete any existing OTP for this email + product
    sb.table("otp_codes").delete().eq("email", email).eq("product", "billing").execute()
    sb.table("otp_codes").insert({
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "product": "billing",
    }).execute()

    _send_otp_email(email, code, "billing")
    return {"sent": True, "email": email}


# ---------------------------------------------------------------------------
# POST /api/billing/verify-otp — thin wrapper around auth OTP
# ---------------------------------------------------------------------------

@router.post("/verify-otp")
async def billing_verify_otp(req: VerifyOtpRequest, request: Request):
    sb = _get_supabase()
    email = req.email.strip().lower()
    now = datetime.now(timezone.utc)

    # Validate OTP
    otp = sb.table("otp_codes").select("*").eq("email", email).eq(
        "code", req.code.strip()
    ).eq("product", "billing").gt("expires_at", now.isoformat()).execute()

    if not otp.data:
        raise HTTPException(status_code=400, detail="Invalid or expired code. Please request a new one.")

    # Delete used OTP
    sb.table("otp_codes").delete().eq("email", email).eq("product", "billing").execute()

    # Look up company_users record for billing
    company_user = sb.table("company_users").select(
        "id, company_id, email, full_name, role, status"
    ).eq("email", email).eq("status", "active").execute()

    matched_user = None
    matched_company = None
    for cu in (company_user.data or []):
        cid = cu.get("company_id")
        if not cid:
            continue
        comp = sb.table("companies").select("*").eq("id", cid).eq("type", "billing").limit(1).execute()
        if comp.data:
            matched_user = cu
            matched_company = comp.data[0]
            break

    if not matched_user:
        return {
            "verified": True,
            "needs_company": True,
            "email": email,
            "product": "billing",
            "token": None,
            "user": None,
            "company": None,
        }

    # Update last login
    sb.table("company_users").update({
        "last_login_at": now.isoformat()
    }).eq("id", matched_user["id"]).execute()

    # Create session
    session_id = str(uuid.uuid4())
    expires_at = (now + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

    sb.table("sessions").insert({
        "id": session_id,
        "email": email,
        "company_id": matched_company["id"],
        "product": "billing",
        "expires_at": expires_at,
        "last_active_at": now.isoformat(),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:255],
    }).execute()

    # Also look up billing company info
    billing_user = sb.table("billing_company_users").select(
        "billing_company_id, role"
    ).eq("email", email).eq("status", "active").limit(1).execute()

    billing_company = None
    if billing_user.data:
        bc = sb.table("billing_companies").select("*").eq(
            "id", billing_user.data[0]["billing_company_id"]
        ).limit(1).execute()
        if bc.data:
            billing_company = bc.data[0]

    return {
        "verified": True,
        "needs_company": False,
        "token": session_id,
        "email": email,
        "product": "billing",
        "user": {
            "email": email,
            "full_name": matched_user.get("full_name"),
            "role": matched_user["role"],
        },
        "company": {
            "id": matched_company["id"],
            "name": matched_company["name"],
            "type": matched_company["type"],
        },
        "billing_company": billing_company,
    }


# ---------------------------------------------------------------------------
# POST /api/billing/register — create billing company (no auth)
# ---------------------------------------------------------------------------

@router.post("/register")
async def register_billing_company(req: RegisterRequest, request: Request):
    sb = _get_supabase()
    email = req.email.strip().lower()
    company_name = req.company_name.strip()
    full_name = req.full_name.strip()
    now = datetime.now(timezone.utc)

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name required")

    # Check if user already has a billing company
    existing = sb.table("company_users").select(
        "id, company_id"
    ).eq("email", email).eq("status", "active").execute()

    for eu in (existing.data or []):
        comp = sb.table("companies").select("type").eq("id", eu["company_id"]).limit(1).execute()
        if comp.data and comp.data[0].get("type") == "billing":
            raise HTTPException(status_code=409, detail="You already have a billing account. Please sign in.")

    # 1. Create companies record (type='billing') — enables standard OTP flow
    company_row = sb.table("companies").insert({
        "name": company_name,
        "type": "billing",
        "created_by_email": email,
    }).execute()
    company_id = company_row.data[0]["id"]

    # 2. Create company_users record (admin) — enables standard auth flow
    sb.table("company_users").insert({
        "company_id": company_id,
        "email": email,
        "full_name": full_name,
        "role": "admin",
        "status": "active",
    }).execute()

    # 3. Create billing_companies record
    bc_row = sb.table("billing_companies").insert({
        "company_name": company_name,
        "contact_email": email,
        "subscription_tier": "trial",
    }).execute()
    billing_company_id = bc_row.data[0]["id"]

    # 4. Create billing_company_users record (admin)
    sb.table("billing_company_users").insert({
        "billing_company_id": billing_company_id,
        "email": email,
        "full_name": full_name,
        "role": "admin",
        "status": "active",
    }).execute()

    # 5. Create billing_company_subscriptions (trial, 30 days, 10 practices)
    trial_ends = (now + timedelta(days=30)).isoformat()
    sb.table("billing_company_subscriptions").insert({
        "billing_company_id": billing_company_id,
        "tier": "trial",
        "practice_count_limit": 10,
        "status": "active",
        "trial_ends_at": trial_ends,
    }).execute()

    # 6. Create session — no second OTP needed
    session_id = str(uuid.uuid4())
    expires_at = (now + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

    sb.table("sessions").insert({
        "id": session_id,
        "email": email,
        "company_id": company_id,
        "product": "billing",
        "expires_at": expires_at,
        "last_active_at": now.isoformat(),
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent", "")[:255],
    }).execute()

    # 7. Send welcome email
    try:
        send_email(
            to=email,
            subject="Welcome to Parity Billing — your 30-day free trial has started",
            from_name="Parity Billing",
            html=f"""
            <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
              <h2 style="color: #0d9488;">Welcome to Parity Billing</h2>
              <p>Hi {full_name},</p>
              <p>Your billing company <strong>{company_name}</strong> has been created
                 with a 30-day free trial. You can manage up to 10 practices during your trial.</p>
              <p>Get started by adding your first practice:</p>
              <a href="https://billing.civicscale.ai/dashboard"
                 style="display: inline-block; background: linear-gradient(135deg, #0d9488, #14b8a6);
                        color: white; padding: 12px 24px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; margin: 16px 0;">
                Go to Dashboard &rarr;
              </a>
              <p style="color: #666; font-size: 14px; margin-top: 24px;">
                Questions? Reply to this email or contact us at support@civicscale.ai.
              </p>
              <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
            </div>
            """,
        )
    except Exception as e:
        print(f"[billing] Welcome email failed (non-fatal): {e}")

    return {
        "created": True,
        "token": session_id,
        "email": email,
        "company_id": company_id,
        "billing_company_id": billing_company_id,
        "company_name": company_name,
        "role": "admin",
        "user": {
            "email": email,
            "full_name": full_name,
            "role": "admin",
        },
        "company": {
            "id": company_id,
            "name": company_name,
            "type": "billing",
        },
        "billing_company": {
            "id": billing_company_id,
            "company_name": company_name,
            "subscription_tier": "trial",
            "trial_ends_at": trial_ends,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/billing/me — current user + billing company + subscription
# ---------------------------------------------------------------------------

@router.get("/me")
async def billing_me(authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, bc_role = _get_billing_company(user, sb)

    # Get subscription
    sub = sb.table("billing_company_subscriptions").select("*").eq(
        "billing_company_id", bc["id"]
    ).eq("status", "active").order("created_at", desc=True).limit(1).execute()

    return {
        "email": user["email"],
        "full_name": user.get("full_name"),
        "role": bc_role,
        "company": user["company"],
        "billing_company": bc,
        "subscription": sub.data[0] if sub.data else None,
    }


# ---------------------------------------------------------------------------
# GET /api/billing/practices — list practices for this billing company
# ---------------------------------------------------------------------------

@router.get("/practices")
async def list_practices(authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, _ = _get_billing_company(user, sb)

    links = sb.table("billing_company_practices").select(
        "id, practice_id, active, added_at, companies(id, name, type, created_by_email)"
    ).eq("billing_company_id", bc["id"]).order("added_at").execute()

    practices = []
    for link in (links.data or []):
        practice = link.get("companies") or {}
        practices.append({
            "link_id": link["id"],
            "practice_id": link["practice_id"],
            "practice_name": practice.get("name", "Unknown"),
            "contact_email": practice.get("created_by_email", ""),
            "active": link["active"],
            "added_at": link["added_at"],
        })

    return {"practices": practices}


# ---------------------------------------------------------------------------
# POST /api/billing/practices — add a practice (admin only)
# ---------------------------------------------------------------------------

@router.post("/practices")
async def add_practice(req: PracticeCreateRequest, authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, bc_role = _get_billing_company(user, sb)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    practice_name = req.practice_name.strip()
    contact_email = req.contact_email.strip().lower()

    if not practice_name:
        raise HTTPException(status_code=400, detail="Practice name required")
    if not contact_email or "@" not in contact_email:
        raise HTTPException(status_code=400, detail="Valid contact email required")

    # Check practice count limit
    sub = sb.table("billing_company_subscriptions").select(
        "practice_count_limit"
    ).eq("billing_company_id", bc["id"]).eq("status", "active").order(
        "created_at", desc=True
    ).limit(1).execute()

    limit = 10
    if sub.data:
        limit = sub.data[0].get("practice_count_limit", 10)

    current_count = sb.table("billing_company_practices").select(
        "id", count="exact"
    ).eq("billing_company_id", bc["id"]).eq("active", True).execute()

    if (current_count.count or 0) >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Practice limit reached ({limit}). Upgrade your plan to add more practices."
        )

    # Check if a companies record exists for this contact email
    existing_company = sb.table("companies").select("id, name").eq(
        "created_by_email", contact_email
    ).eq("account_type", "practice").limit(1).execute()

    if existing_company.data:
        practice_id = existing_company.data[0]["id"]
        # Update name if different
        if existing_company.data[0]["name"] != practice_name:
            sb.table("companies").update({"name": practice_name}).eq("id", practice_id).execute()
    else:
        # Create new companies record (account_type='practice')
        new_company = sb.table("companies").insert({
            "name": practice_name,
            "type": "provider",
            "account_type": "practice",
            "created_by_email": contact_email,
        }).execute()
        practice_id = new_company.data[0]["id"]

    # Check for duplicate link
    dup = sb.table("billing_company_practices").select("id, active").eq(
        "billing_company_id", bc["id"]
    ).eq("practice_id", practice_id).limit(1).execute()

    if dup.data:
        if dup.data[0]["active"]:
            raise HTTPException(status_code=409, detail="This practice is already linked to your company.")
        # Reactivate
        sb.table("billing_company_practices").update({
            "active": True, "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", dup.data[0]["id"]).execute()
        return {"added": True, "practice_id": practice_id, "reactivated": True}

    # Create link
    sb.table("billing_company_practices").insert({
        "billing_company_id": bc["id"],
        "practice_id": practice_id,
        "active": True,
    }).execute()

    return {"added": True, "practice_id": practice_id, "practice_name": practice_name}


# ---------------------------------------------------------------------------
# PATCH /api/billing/practices/{practice_id} — deactivate practice (admin)
# ---------------------------------------------------------------------------

@router.patch("/practices/{practice_id}")
async def deactivate_practice(practice_id: str, authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, bc_role = _get_billing_company(user, sb)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    link = sb.table("billing_company_practices").select("id").eq(
        "billing_company_id", bc["id"]
    ).eq("practice_id", practice_id).limit(1).execute()

    if not link.data:
        raise HTTPException(status_code=404, detail="Practice not found in your company.")

    sb.table("billing_company_practices").update({
        "active": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", link.data[0]["id"]).execute()

    return {"deactivated": True, "practice_id": practice_id}


# ---------------------------------------------------------------------------
# POST /api/billing/users/invite — invite user (admin only)
# ---------------------------------------------------------------------------

@router.post("/users/invite")
async def invite_billing_user(req: UserInviteRequest, authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, bc_role = _get_billing_company(user, sb)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    invited_email = req.email.strip().lower()
    role = req.role.strip().lower()

    if role not in ("admin", "analyst", "viewer"):
        raise HTTPException(status_code=400, detail="Role must be admin, analyst, or viewer")

    if not invited_email or "@" not in invited_email:
        raise HTTPException(status_code=400, detail="Valid email required")

    # Check not already a member
    existing = sb.table("billing_company_users").select("id").eq(
        "billing_company_id", bc["id"]
    ).eq("email", invited_email).eq("status", "active").limit(1).execute()

    if existing.data:
        raise HTTPException(status_code=409, detail="This person is already a member of your billing company.")

    # Create billing_company_users record
    sb.table("billing_company_users").insert({
        "billing_company_id": bc["id"],
        "email": invited_email,
        "role": role,
        "status": "invited",
    }).execute()

    # Also create company_users record so OTP login works
    sb.table("company_users").upsert({
        "company_id": user["company_id"],
        "email": invited_email,
        "role": role,
        "status": "active",
        "invited_by_email": user["email"],
    }, on_conflict="company_id,email").execute()

    # Send invite email
    inviter_name = user.get("full_name") or user["email"]
    try:
        send_email(
            to=invited_email,
            subject=f"{inviter_name} invited you to {bc['company_name']} on Parity Billing",
            from_name="Parity Billing",
            html=f"""
            <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
              <h2 style="color: #0d9488;">You've been invited</h2>
              <p>{inviter_name} has invited you to join <strong>{bc['company_name']}</strong>
                  on Parity Billing as a <strong>{role}</strong>.</p>
              <a href="https://billing.civicscale.ai/login"
                 style="display: inline-block; background: linear-gradient(135deg, #0d9488, #14b8a6);
                        color: white; padding: 12px 24px; border-radius: 8px;
                        text-decoration: none; font-weight: bold; margin: 16px 0;">
                Sign In &rarr;
              </a>
              <p style="color: #666; font-size: 14px;">
                Sign in with your email ({invited_email}) to access the billing dashboard.
              </p>
              <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
            </div>
            """,
        )
    except Exception as e:
        print(f"[billing] Invite email failed (non-fatal): {e}")

    return {"invited": True, "email": invited_email, "role": role}


# ---------------------------------------------------------------------------
# GET /api/billing/users — list users (admin only)
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_billing_users(authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, bc_role = _get_billing_company(user, sb)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    users = sb.table("billing_company_users").select(
        "id, email, full_name, role, status, created_at"
    ).eq("billing_company_id", bc["id"]).order("created_at").execute()

    return {"users": users.data or []}


# ---------------------------------------------------------------------------
# PUT /api/billing/settings — update company profile and/or user name
# ---------------------------------------------------------------------------

class SettingsUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    contact_email: Optional[str] = None
    user_full_name: Optional[str] = None

@router.put("/settings")
async def update_billing_settings(req: SettingsUpdateRequest, authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, bc_role = _get_billing_company(user, sb)

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    now = datetime.now(timezone.utc).isoformat()

    # Update billing_companies fields
    bc_updates = {}
    if req.company_name is not None and req.company_name.strip():
        bc_updates["company_name"] = req.company_name.strip()
    if req.contact_email is not None and req.contact_email.strip():
        bc_updates["contact_email"] = req.contact_email.strip().lower()
    if bc_updates:
        bc_updates["updated_at"] = now
        sb.table("billing_companies").update(bc_updates).eq("id", bc["id"]).execute()
        # Also sync name to companies table
        if "company_name" in bc_updates:
            sb.table("companies").update({
                "name": bc_updates["company_name"]
            }).eq("id", user["company_id"]).execute()

    # Update user full_name
    if req.user_full_name is not None and req.user_full_name.strip():
        new_name = req.user_full_name.strip()
        sb.table("billing_company_users").update({
            "full_name": new_name, "updated_at": now
        }).eq("billing_company_id", bc["id"]).eq("email", user["email"]).execute()
        sb.table("company_users").update({
            "full_name": new_name
        }).eq("company_id", user["company_id"]).eq("email", user["email"]).execute()

    return {"updated": True}


# ===========================================================================
# 835 Ingestion endpoints
# ===========================================================================


# ---------------------------------------------------------------------------
# POST /api/billing/ingest/upload — upload 835 files and queue jobs
# ---------------------------------------------------------------------------

@router.post("/ingest/upload")
async def ingest_upload(
    practice_id: str = Form(...),
    files: List[UploadFile] = File(...),
    authorization: str = Header(None),
):
    user, sb = _require_billing(authorization)
    bc, bc_role = _get_billing_company(user, sb)

    if len(files) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 files per upload.")

    # Validate practice belongs to this billing company
    link = sb.table("billing_company_practices").select("id").eq(
        "billing_company_id", bc["id"]
    ).eq("practice_id", practice_id).eq("active", True).limit(1).execute()

    if not link.data:
        raise HTTPException(status_code=403, detail="Practice not found or not linked to your company.")

    job_ids = []
    for f in files:
        content_bytes = await f.read()
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = content_bytes.decode("latin-1")

        filename = f.filename or "unknown.835"

        row = sb.table("billing_835_jobs").insert({
            "billing_company_id": bc["id"],
            "practice_id": practice_id,
            "filename": filename,
            "status": "queued",
            "file_content": text,
            "uploaded_by_email": user["email"],
        }).execute()

        job_ids.append(row.data[0]["id"])

    return {"queued": len(job_ids), "job_ids": job_ids}


# ---------------------------------------------------------------------------
# POST /api/billing/ingest/process/{job_id} — process a single queued job
# ---------------------------------------------------------------------------

@router.post("/ingest/process/{job_id}")
async def ingest_process_one(job_id: str, authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, _ = _get_billing_company(user, sb)

    job = sb.table("billing_835_jobs").select("*").eq("id", job_id).eq(
        "billing_company_id", bc["id"]
    ).limit(1).execute()

    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found.")

    j = job.data[0]

    if j["status"] not in ("queued", "error"):
        return {"job_id": job_id, "status": j["status"], "message": "Already processed."}

    return _process_job(j, sb)


def _process_job(j: dict, sb) -> dict:
    """Process a single 835 job. Never raises — returns status dict."""
    from utils.parse_835 import parse_835

    job_id = j["id"]
    now = datetime.now(timezone.utc).isoformat()

    # Set processing
    sb.table("billing_835_jobs").update({
        "status": "processing", "updated_at": now,
    }).eq("id", job_id).execute()

    try:
        text = j.get("file_content", "")
        if not text or not text.strip():
            raise ValueError("File content is empty")

        if "ISA" not in text[:500]:
            raise ValueError("Not a valid 835/EDI file (no ISA segment)")

        parsed = parse_835(text)

        line_items = parsed.get("line_items", [])
        line_count = len(line_items)
        total_billed = float(parsed.get("total_billed", 0) or 0)
        total_paid = float(parsed.get("total_paid", 0) or 0)

        # Compute denial rate
        denied = sum(
            1 for li in line_items
            if (li.get("paid_amount") or 0) == 0
            and any(
                a.get("group_code") == "CO"
                for a in (li.get("adjustments") or [])
                if isinstance(a, dict)
            )
        )
        denial_rate = round((denied / line_count * 100), 2) if line_count > 0 else 0.0

        # Build result_json
        result = {
            "payer_name": parsed.get("payer_name", ""),
            "payee_name": parsed.get("payee_name", ""),
            "production_date": parsed.get("production_date", ""),
            "total_billed": total_billed,
            "total_paid": total_paid,
            "claim_count": parsed.get("claim_count", 0),
            "line_count": line_count,
            "denial_rate": denial_rate,
            "denied_lines": denied,
            "claims": parsed.get("claims", []),
            "line_items": line_items,
        }

        # Insert provider_analyses row with billing_company_id for BL-4 rollup
        analysis_id = None
        try:
            ins = sb.table("provider_analyses").insert({
                "company_id": j["practice_id"],
                "billing_company_id": j["billing_company_id"],
                "payer_name": parsed.get("payer_name", ""),
                "production_date": parsed.get("production_date", ""),
                "total_billed": total_billed,
                "total_paid": total_paid,
                "underpayment": 0,
                "adherence_rate": 100.0 - denial_rate,
                "result_json": result,
            }).execute()
            if ins.data:
                analysis_id = ins.data[0].get("id")
        except Exception as exc:
            print(f"[billing-ingest] provider_analyses insert failed (non-fatal): {exc}")

        if analysis_id:
            result["analysis_id"] = analysis_id

        # Update job as complete
        sb.table("billing_835_jobs").update({
            "status": "complete",
            "result_json": result,
            "line_count": line_count,
            "denial_rate": denial_rate,
            "total_billed": total_billed,
            "file_content": None,  # Clear raw content to save space
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        return {"job_id": job_id, "status": "complete", "line_count": line_count,
                "denial_rate": denial_rate, "total_billed": total_billed}

    except Exception as exc:
        sb.table("billing_835_jobs").update({
            "status": "error",
            "error_message": str(exc)[:500],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        return {"job_id": job_id, "status": "error", "error_message": str(exc)[:500]}


# ---------------------------------------------------------------------------
# POST /api/billing/ingest/process-all — process all queued jobs
# ---------------------------------------------------------------------------

@router.post("/ingest/process-all")
async def ingest_process_all(authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, _ = _get_billing_company(user, sb)

    queued = sb.table("billing_835_jobs").select("*").eq(
        "billing_company_id", bc["id"]
    ).eq("status", "queued").order("created_at").execute()

    processed = 0
    errors = 0

    for j in (queued.data or []):
        result = _process_job(j, sb)
        if result.get("status") == "complete":
            processed += 1
        else:
            errors += 1

    return {"processed": processed, "errors": errors}


# ---------------------------------------------------------------------------
# GET /api/billing/ingest/jobs — list all jobs for this billing company
# ---------------------------------------------------------------------------

@router.get("/ingest/jobs")
async def list_ingest_jobs(authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, _ = _get_billing_company(user, sb)

    jobs = sb.table("billing_835_jobs").select(
        "id, practice_id, filename, status, line_count, denial_rate, "
        "total_billed, error_message, uploaded_by_email, created_at, updated_at, "
        "companies(name)"
    ).eq("billing_company_id", bc["id"]).order("created_at", desc=True).execute()

    result = []
    for j in (jobs.data or []):
        practice = j.pop("companies", None) or {}
        result.append({
            **j,
            "practice_name": practice.get("name", "Unknown"),
        })

    return {"jobs": result}


# ---------------------------------------------------------------------------
# GET /api/billing/ingest/jobs/{job_id} — single job with result_json
# ---------------------------------------------------------------------------

@router.get("/ingest/jobs/{job_id}")
async def get_ingest_job(job_id: str, authorization: str = Header(None)):
    user, sb = _require_billing(authorization)
    bc, _ = _get_billing_company(user, sb)

    job = sb.table("billing_835_jobs").select(
        "*, companies(name)"
    ).eq("id", job_id).eq("billing_company_id", bc["id"]).limit(1).execute()

    if not job.data:
        raise HTTPException(status_code=404, detail="Job not found.")

    j = job.data[0]
    practice = j.pop("companies", None) or {}
    j["practice_name"] = practice.get("name", "Unknown")

    return j


# ---------------------------------------------------------------------------
# GET /api/billing/health — health check
# ---------------------------------------------------------------------------

@router.get("/health")
async def billing_health(request: Request):
    """Health check endpoint — confirms router is wired and auth works."""
    auth_header = request.headers.get("authorization", "")
    get_current_user(auth_header)
    return {"status": "ok", "product": "parity-billing"}
