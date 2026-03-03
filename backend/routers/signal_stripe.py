"""Parity Signal — Stripe subscription endpoints.

Handles checkout session creation, customer portal access,
tier lookup, and webhook processing for subscription lifecycle.
"""

import os
import stripe
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/signal/stripe", tags=["signal-stripe"])

# Stripe config — loaded from env
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# Price IDs from env (set after creating products in Stripe dashboard)
PRICE_IDS = {
    "standard_monthly": os.environ.get("STRIPE_PRICE_STANDARD_MONTHLY", ""),
    "standard_annual": os.environ.get("STRIPE_PRICE_STANDARD_ANNUAL", ""),
    "premium_monthly": os.environ.get("STRIPE_PRICE_PREMIUM_MONTHLY", ""),
    "premium_annual": os.environ.get("STRIPE_PRICE_PREMIUM_ANNUAL", ""),
}

# Lazy Supabase client
_sb = None


def _get_sb():
    global _sb
    if _sb is None:
        from supabase_client import supabase
        _sb = supabase
    return _sb


async def _get_authenticated_user(request: Request):
    """Extract Bearer token and validate via Supabase auth."""
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ", 1)[1]
    sb = _get_sb()
    if not sb:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    try:
        user_response = sb.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Auth failed: {exc}")


def _get_or_create_stripe_customer(user):
    """Look up existing Stripe customer for this user, or create one."""
    sb = _get_sb()
    email = user.email or ""
    phone = getattr(user, "phone", None) or ""

    # Check if we already have a stripe_customer_id stored
    result = sb.table("signal_subscriptions").select("stripe_customer_id").eq(
        "user_id", str(user.id)
    ).execute()

    if result.data and result.data[0].get("stripe_customer_id"):
        return result.data[0]["stripe_customer_id"]

    # Create new Stripe customer
    customer = stripe.Customer.create(
        email=email if email else None,
        phone=phone if phone else None,
        metadata={"supabase_user_id": str(user.id)},
    )

    # Upsert into signal_subscriptions
    sb.table("signal_subscriptions").upsert({
        "user_id": str(user.id),
        "stripe_customer_id": customer.id,
        "tier": "free",
        "status": "active",
    }, on_conflict="user_id").execute()

    return customer.id


class CheckoutRequest(BaseModel):
    price_key: str  # e.g. "standard_monthly", "premium_annual"


@router.post("/checkout")
async def create_checkout(body: CheckoutRequest, request: Request):
    """Create a Stripe Checkout session and return the URL."""
    user = await _get_authenticated_user(request)

    price_id = PRICE_IDS.get(body.price_key)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid price key")

    customer_id = _get_or_create_stripe_customer(user)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{FRONTEND_URL}/signal/pricing?success=1",
        cancel_url=f"{FRONTEND_URL}/signal/pricing?canceled=1",
        metadata={"supabase_user_id": str(user.id)},
    )

    return {"checkout_url": session.url}


@router.post("/portal")
async def create_portal(request: Request):
    """Create a Stripe Customer Portal session for billing management."""
    user = await _get_authenticated_user(request)

    customer_id = _get_or_create_stripe_customer(user)

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{FRONTEND_URL}/signal/account",
    )

    return {"portal_url": portal_session.url}


@router.get("/tier")
async def get_tier(request: Request):
    """Return the current user's subscription tier and status."""
    user = await _get_authenticated_user(request)

    sb = _get_sb()
    result = sb.table("signal_subscriptions").select(
        "tier, status, current_period_end"
    ).eq("user_id", str(user.id)).execute()

    if not result.data:
        return {"tier": "free", "status": "active", "current_period_end": None}

    row = result.data[0]
    return {
        "tier": row.get("tier", "free"),
        "status": row.get("status", "active"),
        "current_period_end": row.get("current_period_end"),
    }


def _tier_from_price_id(price_id: str) -> str:
    """Map a Stripe price ID back to a tier name."""
    for key, pid in PRICE_IDS.items():
        if pid == price_id:
            return key.split("_")[0]  # "standard_monthly" -> "standard"
    return "free"


@router.post("/webhooks")
async def stripe_webhook(request: Request):
    """Process Stripe webhook events to sync subscription state."""
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    if not STRIPE_WEBHOOK_SECRET:
        return JSONResponse({"error": "Webhook secret not configured"}, status_code=500)

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    sb = _get_sb()
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = obj.get("metadata", {}).get("supabase_user_id")
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")

        if user_id and subscription_id:
            # Fetch the subscription to get price/tier info
            sub = stripe.Subscription.retrieve(subscription_id)
            price_id = sub["items"]["data"][0]["price"]["id"] if sub["items"]["data"] else ""
            tier = _tier_from_price_id(price_id)
            period_end = sub.get("current_period_end")

            sb.table("signal_subscriptions").upsert({
                "user_id": user_id,
                "stripe_customer_id": customer_id,
                "stripe_subscription_id": subscription_id,
                "tier": tier,
                "status": "active",
                "current_period_end": period_end,
            }, on_conflict="user_id").execute()

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        subscription_id = obj.get("id")
        status = obj.get("status")  # active, past_due, canceled, etc.
        price_id = obj["items"]["data"][0]["price"]["id"] if obj.get("items", {}).get("data") else ""
        tier = _tier_from_price_id(price_id)
        period_end = obj.get("current_period_end")

        # Map Stripe status to our simplified status
        if event_type == "customer.subscription.deleted" or status == "canceled":
            tier = "free"
            mapped_status = "canceled"
        elif status == "past_due":
            mapped_status = "past_due"
        else:
            mapped_status = "active"

        # Find user by subscription_id
        result = sb.table("signal_subscriptions").select("user_id").eq(
            "stripe_subscription_id", subscription_id
        ).execute()

        if result.data:
            sb.table("signal_subscriptions").update({
                "tier": tier,
                "status": mapped_status,
                "current_period_end": period_end,
            }).eq("stripe_subscription_id", subscription_id).execute()

    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        if subscription_id:
            sb.table("signal_subscriptions").update({
                "status": "past_due",
            }).eq("stripe_subscription_id", subscription_id).execute()

    return {"status": "ok"}
