"""Parity Signal — Stripe subscription endpoints.

Handles checkout session creation, plan upgrades/downgrades,
customer portal access, tier lookup, and webhook processing
for subscription lifecycle.
"""

import os
from datetime import datetime, timezone

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

TIER_RANK = {"free": 0, "standard": 1, "premium": 2}


def _get_period_end(sub_obj):
    """Extract current_period_end from a Stripe subscription object.

    Newer Stripe API versions moved this field from the subscription
    to items.data[].  Check both locations.  Returns an ISO-8601 string
    suitable for Supabase timestamptz columns (not a raw Unix integer).
    """
    # Try top-level first (older API versions)
    val = sub_obj.get("current_period_end")
    if val is None:
        # Fall back to first item (newer API versions)
        items = sub_obj.get("items", {}).get("data", [])
        if items:
            val = items[0].get("current_period_end")
    if val is None:
        return None
    # Convert Unix timestamp to ISO string for Supabase
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
    return val


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
    return_path: str = "/signal/pricing"  # where to redirect after checkout


def _get_active_subscription(user_id: str):
    """Return the user's DB subscription row and live Stripe subscription, or (None, None)."""
    sb = _get_sb()
    result = sb.table("signal_subscriptions").select(
        "tier, stripe_subscription_id, current_period_end"
    ).eq("user_id", user_id).execute()

    if not result.data:
        return None, None

    row = result.data[0]
    sub_id = row.get("stripe_subscription_id")
    if not sub_id:
        return row, None

    try:
        sub = stripe.Subscription.retrieve(sub_id)
        if sub.status in ("active", "trialing"):
            return row, sub
    except Exception:
        pass

    return row, None


@router.post("/checkout")
async def create_checkout(body: CheckoutRequest, request: Request):
    """Create a Stripe Checkout session, or modify an existing subscription."""
    user = await _get_authenticated_user(request)

    price_id = PRICE_IDS.get(body.price_key)
    if not price_id:
        raise HTTPException(status_code=400, detail="Invalid price key")

    customer_id = _get_or_create_stripe_customer(user)
    new_tier = body.price_key.split("_")[0]  # "standard" or "premium"

    # Check for existing active subscription
    db_row, stripe_sub = _get_active_subscription(str(user.id))
    current_tier = (db_row or {}).get("tier", "free")

    if stripe_sub:
        # User already has an active subscription — modify it
        item_id = stripe_sub["items"]["data"][0]["id"]
        is_upgrade = TIER_RANK.get(new_tier, 0) > TIER_RANK.get(current_tier, 0)

        if is_upgrade:
            # Upgrade: apply immediately with proration
            updated_sub = stripe.Subscription.modify(
                stripe_sub.id,
                items=[{"id": item_id, "price": price_id}],
                proration_behavior="create_prorations",
            )
            # Update DB tier immediately
            sb = _get_sb()
            sb.table("signal_subscriptions").update({
                "tier": new_tier,
                "current_period_end": _get_period_end(updated_sub),
            }).eq("user_id", str(user.id)).execute()

            return {"action": "upgraded", "tier": new_tier}
        else:
            # Downgrade: change price but no proration — takes effect next invoice
            updated_sub = stripe.Subscription.modify(
                stripe_sub.id,
                items=[{"id": item_id, "price": price_id}],
                proration_behavior="none",
            )
            # Keep current tier in DB until period ends
            return {
                "action": "downgraded_scheduled",
                "tier": current_tier,
                "new_tier": new_tier,
                "effective_date": _get_period_end(updated_sub),
            }

    # No active subscription — create Checkout session for new subscribers
    return_path = body.return_path if body.return_path.startswith("/") else "/signal/pricing"
    separator = "&" if "?" in return_path else "?"

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{FRONTEND_URL}{return_path}{separator}checkout_success=1",
        cancel_url=f"{FRONTEND_URL}{return_path}",
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
            period_end = _get_period_end(sub)

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
        new_tier = _tier_from_price_id(price_id)
        period_end = _get_period_end(obj)

        # Map Stripe status to our simplified status
        if event_type == "customer.subscription.deleted" or status == "canceled":
            new_tier = "free"
            mapped_status = "canceled"
        elif status == "past_due":
            mapped_status = "past_due"
        else:
            mapped_status = "active"

        # Find user by subscription_id
        result = sb.table("signal_subscriptions").select(
            "user_id, tier, current_period_end"
        ).eq(
            "stripe_subscription_id", subscription_id
        ).execute()

        if result.data:
            current_db_tier = result.data[0].get("tier", "free")
            db_period_end = result.data[0].get("current_period_end")

            # For downgrades (new tier lower than current DB tier): only apply
            # the tier change when the billing period rolls over, so the user
            # keeps their current tier for the remainder of the paid period.
            if (mapped_status == "active"
                    and TIER_RANK.get(new_tier, 0) < TIER_RANK.get(current_db_tier, 0)
                    and db_period_end
                    and period_end == db_period_end):
                # Same period — this is the mid-cycle downgrade event.
                # Update status but keep the current (higher) tier.
                sb.table("signal_subscriptions").update({
                    "status": mapped_status,
                }).eq("stripe_subscription_id", subscription_id).execute()
            else:
                # Upgrade, cancellation, new period, or no previous period — apply fully
                sb.table("signal_subscriptions").update({
                    "tier": new_tier,
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
