"""Parity Health consumer auth + Stripe subscription.

Individual consumer auth (not company/B2B).
Uses health_users table, otp_codes table (product='health'), sessions table.

POST /api/health/auth/send-otp          — send OTP email
POST /api/health/auth/verify-otp        — verify OTP, return session token
POST /api/health/auth/signup            — create health_user + session (after OTP verified)
GET  /api/health/auth/me                — validate token, return user + subscription
POST /api/health/auth/logout            — delete session
POST /api/health/auth/checkout          — create Stripe checkout session
POST /api/health/auth/webhook           — Stripe webhook for health subscriptions
GET  /api/health/auth/subscription-status — check subscription status
POST /api/health/auth/portal            — Stripe billing portal
"""

import os
import uuid
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from routers.employer_shared import _get_supabase
from utils.email import send_email

router = APIRouter(prefix="/api/health/auth", tags=["health-auth"])

SESSION_EXPIRY_DAYS = 30
OTP_EXPIRY_MINUTES = 10
OTP_LENGTH = 8

STRIPE_PRICE_HEALTH_MONTHLY = os.environ.get("STRIPE_PRICE_HEALTH_MONTHLY", "")
STRIPE_PRICE_HEALTH_YEARLY = os.environ.get("STRIPE_PRICE_HEALTH_YEARLY", "")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class SendOtpRequest(BaseModel):
    email: str

class VerifyOtpRequest(BaseModel):
    email: str
    code: str

class SignupRequest(BaseModel):
    email: str
    full_name: str

class CheckoutRequest(BaseModel):
    plan: str  # "monthly" | "yearly"

class UpdateProfileRequest(BaseModel):
    full_name: str

class PortalRequest(BaseModel):
    pass


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------

def _generate_otp(length=OTP_LENGTH):
    return "".join(random.choices(string.digits, k=length))


def _send_health_otp_email(email: str, code: str):
    send_email(
        to=email,
        subject=f"Your Parity Health sign-in code: {code}",
        from_name="Parity Health",
        html=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
          <h2 style="color: #0d9488;">Your sign-in code</h2>
          <p>Enter this code to sign in to Parity Health:</p>
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
# Auth helper — validate health session
# ---------------------------------------------------------------------------

def get_health_user(authorization: str = None, sb=None):
    """Validate Bearer token and return health user.
    Returns dict with email, full_name, health_user_id, subscription.
    Raises 401 if invalid or expired.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not sb:
        sb = _get_supabase()

    now = datetime.now(timezone.utc).isoformat()
    session = sb.table("sessions").select("*").eq("id", token).eq(
        "product", "health"
    ).gt("expires_at", now).execute()

    if not session.data:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please sign in again.")

    s = session.data[0]

    # Refresh last_active_at
    sb.table("sessions").update({"last_active_at": now}).eq("id", token).execute()

    # Get health user
    health_user = sb.table("health_users").select("*").eq("email", s["email"]).execute()
    if not health_user.data:
        raise HTTPException(status_code=401, detail="User account not found.")

    hu = health_user.data[0]

    # Get subscription status
    sub = sb.table("health_subscriptions").select("*").eq(
        "health_user_id", hu["id"]
    ).eq("status", "active").limit(1).execute()

    subscription = None
    if sub.data:
        subscription = sub.data[0]
        # Check if trial has expired
        trial_ends = subscription.get("trial_ends_at")
        if trial_ends and subscription.get("plan") == "trial":
            ends_dt = datetime.fromisoformat(trial_ends.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > ends_dt:
                subscription["status"] = "expired"

    return {
        "email": s["email"],
        "full_name": hu.get("full_name", ""),
        "health_user_id": hu["id"],
        "session_id": token,
        "subscription": subscription,
    }


# ---------------------------------------------------------------------------
# POST /api/health/auth/send-otp
# ---------------------------------------------------------------------------

@router.post("/send-otp")
async def send_otp(req: SendOtpRequest):
    sb = _get_supabase()
    email = req.email.strip().lower()

    code = _generate_otp()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()

    # Delete existing OTP
    sb.table("otp_codes").delete().eq("email", email).eq("product", "health").execute()

    # Insert new OTP
    sb.table("otp_codes").insert({
        "email": email,
        "code": code,
        "expires_at": expires_at,
        "product": "health",
    }).execute()

    _send_health_otp_email(email, code)

    return {"sent": True, "email": email}


# ---------------------------------------------------------------------------
# POST /api/health/auth/verify-otp
# ---------------------------------------------------------------------------

@router.post("/verify-otp")
async def verify_otp(req: VerifyOtpRequest, request: Request):
    sb = _get_supabase()
    email = req.email.strip().lower()
    now = datetime.now(timezone.utc)

    # Validate OTP
    otp = sb.table("otp_codes").select("*").eq("email", email).eq(
        "code", req.code.strip()
    ).eq("product", "health").gt("expires_at", now.isoformat()).execute()

    if not otp.data:
        raise HTTPException(status_code=400, detail="Invalid or expired code. Please request a new one.")

    # Delete used OTP
    sb.table("otp_codes").delete().eq("email", email).eq("product", "health").execute()

    # Check if user exists in health_users
    existing = sb.table("health_users").select("*").eq("email", email).execute()

    if not existing.data:
        # New user — needs signup
        return {
            "verified": True,
            "needs_signup": True,
            "email": email,
            "token": None,
            "user": None,
        }

    hu = existing.data[0]

    # Update last_login_at
    sb.table("health_users").update({"last_login_at": now.isoformat()}).eq("id", hu["id"]).execute()

    # Create session
    session_id = str(uuid.uuid4())
    expires_at = (now + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

    sb.table("sessions").insert({
        "id": session_id,
        "email": email,
        "company_id": None,
        "product": "health",
        "expires_at": expires_at,
        "last_active_at": now.isoformat(),
        "ip_address": request.client.host if request.client else None,
        "user_agent": (request.headers.get("user-agent", "") or "")[:255],
    }).execute()

    # Get subscription
    sub = sb.table("health_subscriptions").select("*").eq(
        "health_user_id", hu["id"]
    ).eq("status", "active").limit(1).execute()

    return {
        "verified": True,
        "needs_signup": False,
        "token": session_id,
        "email": email,
        "user": {
            "email": email,
            "full_name": hu.get("full_name", ""),
            "health_user_id": hu["id"],
        },
        "has_subscription": bool(sub.data),
    }


# ---------------------------------------------------------------------------
# POST /api/health/auth/signup
# ---------------------------------------------------------------------------

@router.post("/signup")
async def signup(req: SignupRequest, request: Request):
    sb = _get_supabase()
    email = req.email.strip().lower()
    now = datetime.now(timezone.utc)

    # Check if user already exists
    existing = sb.table("health_users").select("id").eq("email", email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Account already exists. Please sign in.")

    # Create health user
    hu = sb.table("health_users").insert({
        "email": email,
        "full_name": req.full_name.strip(),
    }).execute()

    health_user_id = hu.data[0]["id"]

    # Create session
    session_id = str(uuid.uuid4())
    expires_at = (now + timedelta(days=SESSION_EXPIRY_DAYS)).isoformat()

    sb.table("sessions").insert({
        "id": session_id,
        "email": email,
        "company_id": None,
        "product": "health",
        "expires_at": expires_at,
        "last_active_at": now.isoformat(),
        "ip_address": request.client.host if request.client else None,
        "user_agent": (request.headers.get("user-agent", "") or "")[:255],
    }).execute()

    # Send welcome email
    send_email(
        to=email,
        subject="Welcome to Parity Health",
        from_name="Parity Health",
        html=f"""
        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
          <h2 style="color: #0d9488;">Welcome to Parity Health</h2>
          <p>Hi {req.full_name.strip().split()[0]},</p>
          <p>Your Parity Health account is ready. Upload any medical bill, EOB,
             or denial letter and we'll analyze it instantly.</p>
          <div style="background: #f0fdfa; border: 1px solid #99f6e4; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-weight: 600; color: #0d9488;">Your free trial</p>
            <p style="margin: 0; font-size: 14px; color: #475569;">
              You get <strong>3 free bill analyses</strong>. Subscribe anytime for unlimited access.
            </p>
          </div>
          <a href="https://health.civicscale.ai" style="display: inline-block; background: #0d9488; color: #fff;
              padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">
            Start Analyzing &rarr;
          </a>
          <p style="color: #999; font-size: 12px; margin-top: 24px;">CivicScale &middot; civicscale.ai</p>
        </div>
        """,
    )

    return {
        "created": True,
        "token": session_id,
        "email": email,
        "user": {
            "email": email,
            "full_name": req.full_name.strip(),
            "health_user_id": health_user_id,
        },
    }


# ---------------------------------------------------------------------------
# GET /api/health/auth/me
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_me(authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_health_user(authorization, sb)
    return user


# ---------------------------------------------------------------------------
# POST /api/health/auth/logout
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
# PATCH /api/health/auth/update-profile
# ---------------------------------------------------------------------------

@router.patch("/update-profile")
async def update_profile(req: UpdateProfileRequest, authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_health_user(authorization, sb)

    full_name = req.full_name.strip()
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required.")

    sb.table("health_users").update({
        "full_name": full_name,
    }).eq("id", user["health_user_id"]).execute()

    return {"updated": True, "full_name": full_name}


# ---------------------------------------------------------------------------
# POST /api/health/auth/checkout
# ---------------------------------------------------------------------------

@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, authorization: str = Header(None)):
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe_lib.api_key = stripe_key

    sb = _get_supabase()
    user = get_health_user(authorization, sb)

    # Select price
    if req.plan == "monthly":
        price_id = STRIPE_PRICE_HEALTH_MONTHLY
    elif req.plan == "yearly":
        price_id = STRIPE_PRICE_HEALTH_YEARLY
    else:
        raise HTTPException(status_code=400, detail="Invalid plan. Use 'monthly' or 'yearly'.")

    if not price_id:
        raise HTTPException(status_code=503, detail="Health price not configured")

    # Block duplicate active subscriptions
    active_sub = sb.table("health_subscriptions").select("id").eq(
        "health_user_id", user["health_user_id"]
    ).eq("status", "active").limit(1).execute()
    if active_sub.data:
        raise HTTPException(status_code=409, detail="You already have an active subscription.")

    # Get or create Stripe customer
    existing = sb.table("health_subscriptions").select("stripe_customer_id").eq(
        "email", user["email"]
    ).not_.is_("stripe_customer_id", "null").limit(1).execute()

    customer_id = None
    if existing.data and existing.data[0].get("stripe_customer_id"):
        customer_id = existing.data[0]["stripe_customer_id"]

    if not customer_id:
        customer = stripe_lib.Customer.create(
            email=user["email"],
            metadata={"product": "health", "health_user_id": user["health_user_id"]},
        )
        customer_id = customer.id

    frontend_url = os.environ.get("FRONTEND_URL", "https://health.civicscale.ai")

    session = stripe_lib.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        payment_method_collection="always",
        subscription_data={"trial_period_days": 30},
        success_url=f"{frontend_url}/parity-health/account?checkout=success",
        cancel_url=f"{frontend_url}/parity-health/account",
        metadata={
            "email": user["email"],
            "health_user_id": user["health_user_id"],
            "plan": req.plan,
            "type": "health_subscription",
        },
    )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# POST /api/health/auth/webhook
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def health_webhook(request: Request):
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    webhook_secret = os.environ.get("STRIPE_HEALTH_WEBHOOK_SECRET", "")

    if not stripe_key or not webhook_secret:
        return JSONResponse({"error": "Stripe not configured"}, status_code=500)

    stripe_lib.api_key = stripe_key

    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe_lib.Webhook.construct_event(payload, sig, webhook_secret)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {exc}")

    sb = _get_supabase()
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata", {})
        if metadata.get("type") != "health_subscription":
            return {"status": "ok", "skipped": True}

        email = metadata.get("email", "")
        health_user_id = metadata.get("health_user_id", "")
        plan = metadata.get("plan", "monthly")
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")

        now = datetime.now(timezone.utc)
        trial_ends = (now + timedelta(days=30)).isoformat()

        # Create health_subscriptions record
        sb.table("health_subscriptions").insert({
            "health_user_id": health_user_id,
            "email": email,
            "plan": plan,
            "status": "active",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "trial_ends_at": trial_ends,
        }).execute()

    elif event_type == "customer.subscription.deleted":
        subscription_id = obj.get("id")
        if subscription_id:
            sb.table("health_subscriptions").update({
                "status": "canceled",
            }).eq("stripe_subscription_id", subscription_id).execute()

    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        if subscription_id:
            sb.table("health_subscriptions").update({
                "status": "past_due",
            }).eq("stripe_subscription_id", subscription_id).execute()

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /api/health/auth/subscription-status
# ---------------------------------------------------------------------------

@router.get("/subscription-status")
async def subscription_status(authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_health_user(authorization, sb)

    sub = user.get("subscription")
    if not sub:
        return {"has_subscription": False, "status": None, "plan": None,
                "trial_ends_at": None, "current_period_end": None}

    result = {
        "has_subscription": True,
        "status": sub["status"],
        "plan": sub.get("plan"),
        "trial_ends_at": sub.get("trial_ends_at"),
        "stripe_subscription_id": sub.get("stripe_subscription_id"),
        "current_period_end": None,
    }

    # Fetch current_period_end from Stripe if we have a subscription ID
    stripe_sub_id = sub.get("stripe_subscription_id")
    if stripe_sub_id:
        try:
            import stripe as stripe_lib
            stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
            if stripe_lib.api_key:
                stripe_sub = stripe_lib.Subscription.retrieve(stripe_sub_id)
                if stripe_sub.current_period_end:
                    result["current_period_end"] = datetime.fromtimestamp(
                        stripe_sub.current_period_end, tz=timezone.utc
                    ).isoformat()
                # Also check if currently in trial
                if stripe_sub.status == "trialing":
                    result["status"] = "trialing"
        except Exception as exc:
            print(f"[HealthSub] Stripe fetch failed: {exc}")

    return result


# ---------------------------------------------------------------------------
# POST /api/health/auth/portal
# ---------------------------------------------------------------------------

@router.post("/portal")
async def billing_portal(authorization: str = Header(None)):
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe_lib.api_key = stripe_key

    sb = _get_supabase()
    user = get_health_user(authorization, sb)

    # Find Stripe customer ID
    sub = sb.table("health_subscriptions").select("stripe_customer_id").eq(
        "email", user["email"]
    ).not_.is_("stripe_customer_id", "null").limit(1).execute()

    if not sub.data or not sub.data[0].get("stripe_customer_id"):
        raise HTTPException(status_code=404, detail="No billing record found")

    customer_id = sub.data[0]["stripe_customer_id"]
    frontend_url = os.environ.get("FRONTEND_URL", "https://health.civicscale.ai")

    portal = stripe_lib.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{frontend_url}/parity-health/account",
    )

    return {"portal_url": portal.url}
