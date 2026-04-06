"""Parity Billing — Stripe subscription management endpoints."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from routers.auth import get_current_user
from routers.employer_shared import _get_supabase

router = APIRouter(prefix="/api/billing/subscription", tags=["billing-subscription"])

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

# ---------------------------------------------------------------------------
# Tier configuration
# ---------------------------------------------------------------------------

BILLING_TIERS = {
    "free":       {"practice_limit": 1,    "price_id": None},
    "starter":    {"practice_limit": 10,   "price_id": os.environ.get("STRIPE_PRICE_BILLING_STARTER")},
    "growth":     {"practice_limit": 30,   "price_id": os.environ.get("STRIPE_PRICE_BILLING_GROWTH")},
    "enterprise": {"practice_limit": None, "price_id": None},  # custom
}

# Reverse lookup: price_id → tier name
PRICE_TO_TIER = {}
for tier_name, info in BILLING_TIERS.items():
    if info["price_id"]:
        PRICE_TO_TIER[info["price_id"]] = tier_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_billing_admin(authorization: str):
    """Authenticate and return (user, bc, bc_id, sb). Admin only."""
    sb = _get_supabase()
    user = get_current_user(authorization, sb)

    if user["company"]["type"] != "billing":
        raise HTTPException(status_code=403, detail="Billing access only")

    bc_user = sb.table("billing_company_users").select(
        "billing_company_id, role"
    ).eq("email", user["email"]).eq("status", "active").limit(1).execute()

    if not bc_user.data:
        raise HTTPException(status_code=404, detail="No billing company found.")

    bc_id = bc_user.data[0]["billing_company_id"]
    bc_role = bc_user.data[0]["role"]

    if bc_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    bc = sb.table("billing_companies").select("*").eq("id", bc_id).limit(1).execute()
    if not bc.data:
        raise HTTPException(status_code=404, detail="Billing company not found.")

    return user, bc.data[0], bc_id, sb


def _ensure_stripe_customer(bc, sb):
    """Get or create Stripe customer for billing company. Returns customer_id."""
    if bc.get("stripe_customer_id"):
        return bc["stripe_customer_id"]

    try:
        customer = stripe.Customer.create(
            email=bc["contact_email"],
            name=bc["company_name"],
            metadata={"billing_company_id": str(bc["id"])},
        )
        sb.table("billing_companies").update({
            "stripe_customer_id": customer.id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", bc["id"]).execute()
        return customer.id
    except Exception as exc:
        print(f"[billing-stripe] Customer creation failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to create payment customer.")


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    tier: str  # 'starter' or 'growth'


# ---------------------------------------------------------------------------
# POST /api/billing/subscription/checkout
# ---------------------------------------------------------------------------

@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, authorization: str = Header(None)):
    user, bc, bc_id, sb = _require_billing_admin(authorization)

    tier = req.tier.strip().lower()
    if tier not in BILLING_TIERS or not BILLING_TIERS[tier]["price_id"]:
        raise HTTPException(status_code=400, detail="Invalid tier. Choose 'starter' or 'growth'.")

    price_id = BILLING_TIERS[tier]["price_id"]
    customer_id = _ensure_stripe_customer(bc, sb)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"https://billing.civicscale.ai/settings?payment=success&tier={tier}",
        cancel_url="https://billing.civicscale.ai/settings?payment=cancelled",
        metadata={
            "billing_company_id": str(bc_id),
            "tier": tier,
            "product": "billing",
        },
    )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# POST /api/billing/subscription/portal
# ---------------------------------------------------------------------------

@router.post("/portal")
async def create_portal_session(authorization: str = Header(None)):
    user, bc, bc_id, sb = _require_billing_admin(authorization)

    customer_id = _ensure_stripe_customer(bc, sb)

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url="https://billing.civicscale.ai/settings",
    )

    return {"portal_url": session.url}


# ---------------------------------------------------------------------------
# GET /api/billing/subscription/status
# ---------------------------------------------------------------------------

@router.get("/status")
async def subscription_status(authorization: str = Header(None)):
    sb = _get_supabase()
    user = get_current_user(authorization, sb)

    if user["company"]["type"] != "billing":
        raise HTTPException(status_code=403, detail="Billing access only")

    bc_user = sb.table("billing_company_users").select(
        "billing_company_id"
    ).eq("email", user["email"]).eq("status", "active").limit(1).execute()

    if not bc_user.data:
        raise HTTPException(status_code=404, detail="No billing company found.")

    bc_id = bc_user.data[0]["billing_company_id"]

    sub = sb.table("billing_company_subscriptions").select("*").eq(
        "billing_company_id", bc_id
    ).eq("status", "active").order("created_at", desc=True).limit(1).execute()

    # Also check for past_due
    if not sub.data:
        sub = sb.table("billing_company_subscriptions").select("*").eq(
            "billing_company_id", bc_id
        ).order("created_at", desc=True).limit(1).execute()

    s = sub.data[0] if sub.data else {}

    # Practice count
    count = sb.table("billing_company_practices").select(
        "id", count="exact"
    ).eq("billing_company_id", bc_id).eq("active", True).execute()

    tier = s.get("tier") or "free"
    tier_info = BILLING_TIERS.get(tier, BILLING_TIERS["free"])

    return {
        "tier": tier,
        "status": s.get("status") or "active",
        "practice_count_limit": s.get("practice_count_limit") or tier_info["practice_limit"],
        "practice_count_used": count.count or 0,
        "stripe_sub_id": s.get("stripe_sub_id"),
        "is_free_tier": tier == "free",
    }


# ---------------------------------------------------------------------------
# POST /api/billing/subscription/webhook
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def billing_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    webhook_secret = os.environ.get("STRIPE_BILLING_WEBHOOK_SECRET", "")

    if not webhook_secret:
        print("[billing-webhook] STRIPE_BILLING_WEBHOOK_SECRET not set")
        return JSONResponse({"received": True}, status_code=200)

    try:
        event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except (stripe.error.SignatureVerificationError, ValueError) as e:
        print(f"[billing-webhook] Signature verification failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    sb = _get_supabase()
    event_type = event["type"]
    obj = event["data"]["object"]

    print(f"[billing-webhook] Received: {event_type}")

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(obj, sb)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(obj, sb)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(obj, sb)
    elif event_type == "invoice.payment_succeeded":
        print(f"[billing-webhook] Payment succeeded: {obj.id}")
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(obj, sb)

    return JSONResponse({"received": True}, status_code=200)


def _resolve_billing_company(customer_id: str, sb) -> str | None:
    """Resolve billing_company_id from Stripe customer_id."""
    row = sb.table("billing_companies").select("id").eq(
        "stripe_customer_id", customer_id
    ).limit(1).execute()
    return row.data[0]["id"] if row.data else None


def _handle_checkout_completed(obj, sb):
    """Handle checkout.session.completed — activate subscription."""
    customer_id = getattr(obj, "customer", None)
    subscription_id = getattr(obj, "subscription", None)
    metadata = getattr(obj, "metadata", None) or {}

    bc_id = (metadata.get("billing_company_id") if isinstance(metadata, dict) else getattr(metadata, "billing_company_id", None)) or _resolve_billing_company(customer_id, sb)
    if not bc_id:
        print(f"[billing-webhook] Cannot resolve billing company for customer {customer_id}")
        return

    tier = (metadata.get("tier") if isinstance(metadata, dict) else getattr(metadata, "tier", None)) or "starter"
    tier_info = BILLING_TIERS.get(tier, BILLING_TIERS["starter"])
    now = datetime.now(timezone.utc).isoformat()

    # Update billing_companies
    sb.table("billing_companies").update({
        "subscription_tier": tier,
        "stripe_customer_id": customer_id,
        "updated_at": now,
    }).eq("id", bc_id).execute()

    # Update or insert subscription record
    existing = sb.table("billing_company_subscriptions").select("id").eq(
        "billing_company_id", bc_id
    ).order("created_at", desc=True).limit(1).execute()

    sub_data = {
        "tier": tier,
        "practice_count_limit": tier_info["practice_limit"],
        "status": "active",
        "stripe_sub_id": subscription_id,
        "updated_at": now,
    }

    if existing.data:
        sb.table("billing_company_subscriptions").update(sub_data).eq(
            "id", existing.data[0]["id"]
        ).execute()
    else:
        sb.table("billing_company_subscriptions").insert({
            "billing_company_id": bc_id,
            **sub_data,
        }).execute()

    print(f"[billing-webhook] Checkout complete: bc={bc_id}, tier={tier}")


def _handle_subscription_updated(obj, sb):
    """Handle customer.subscription.updated — tier/status change."""
    customer_id = getattr(obj, "customer", None)
    sub_id = obj.id
    status = obj.status  # active, past_due, canceled, etc.

    bc_id = _resolve_billing_company(customer_id, sb)
    if not bc_id:
        return

    # Determine tier from price
    try:
        items_data = obj.items.data
    except (AttributeError, KeyError):
        items_data = []
    tier = "starter"
    if items_data:
        price_id = items_data[0].price.id
        tier = PRICE_TO_TIER.get(price_id, "starter")

    tier_info = BILLING_TIERS.get(tier, BILLING_TIERS["starter"])
    now = datetime.now(timezone.utc).isoformat()

    # Map Stripe status
    db_status = "active"
    if status in ("canceled", "unpaid"):
        db_status = "cancelled"
    elif status == "past_due":
        db_status = "past_due"

    existing = sb.table("billing_company_subscriptions").select("id").eq(
        "billing_company_id", bc_id
    ).order("created_at", desc=True).limit(1).execute()

    update = {
        "tier": tier,
        "practice_count_limit": tier_info["practice_limit"],
        "status": db_status,
        "stripe_sub_id": sub_id,
        "updated_at": now,
    }

    if existing.data:
        sb.table("billing_company_subscriptions").update(update).eq(
            "id", existing.data[0]["id"]
        ).execute()

    sb.table("billing_companies").update({
        "subscription_tier": tier, "updated_at": now,
    }).eq("id", bc_id).execute()

    print(f"[billing-webhook] Subscription updated: bc={bc_id}, tier={tier}, status={db_status}")


def _handle_subscription_deleted(obj, sb):
    """Handle customer.subscription.deleted — revert to free tier."""
    customer_id = getattr(obj, "customer", None)
    bc_id = _resolve_billing_company(customer_id, sb)
    if not bc_id:
        return

    now = datetime.now(timezone.utc).isoformat()

    existing = sb.table("billing_company_subscriptions").select("id").eq(
        "billing_company_id", bc_id
    ).order("created_at", desc=True).limit(1).execute()

    if existing.data:
        sb.table("billing_company_subscriptions").update({
            "tier": "free",
            "practice_count_limit": 1,
            "status": "cancelled",
            "updated_at": now,
        }).eq("id", existing.data[0]["id"]).execute()

    sb.table("billing_companies").update({
        "subscription_tier": "free", "updated_at": now,
    }).eq("id", bc_id).execute()

    print(f"[billing-webhook] Subscription deleted: bc={bc_id}, reverted to free")


def _handle_payment_failed(obj, sb):
    """Handle invoice.payment_failed — mark as past_due."""
    customer_id = getattr(obj, "customer", None)
    bc_id = _resolve_billing_company(customer_id, sb)
    if not bc_id:
        return

    now = datetime.now(timezone.utc).isoformat()

    existing = sb.table("billing_company_subscriptions").select("id").eq(
        "billing_company_id", bc_id
    ).order("created_at", desc=True).limit(1).execute()

    if existing.data:
        sb.table("billing_company_subscriptions").update({
            "status": "past_due", "updated_at": now,
        }).eq("id", existing.data[0]["id"]).execute()

    print(f"[billing-webhook] Payment failed: bc={bc_id}")
