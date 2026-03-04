"""Parity Signal — Stripe subscription endpoints.

Handles checkout session creation, plan upgrades/downgrades,
customer portal access, tier lookup, and webhook processing
for subscription lifecycle.
"""

import os
from datetime import datetime, timezone, timedelta

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
    "professional_monthly": os.environ.get("STRIPE_PRICE_PROFESSIONAL_MONTHLY", ""),
    "professional_annual": os.environ.get("STRIPE_PRICE_PROFESSIONAL_ANNUAL", ""),
}

TOPIC_REQUEST_PRICE_IDS = {
    "free": os.environ.get("STRIPE_PRICE_TOPIC_REQUEST_FREE", ""),
    "standard": os.environ.get("STRIPE_PRICE_TOPIC_REQUEST_STANDARD", ""),
    "premium": os.environ.get("STRIPE_PRICE_TOPIC_REQUEST_PREMIUM", ""),
    "professional": os.environ.get("STRIPE_PRICE_TOPIC_REQUEST_PROFESSIONAL", ""),
}

TIER_RANK = {"free": 0, "standard": 1, "premium": 2, "professional": 3}

TIER_LIMITS = {
    "free":         {"topics": 3,    "qa_per_month": 5,   "topic_requests_per_month": 0},
    "standard":     {"topics": 10,   "qa_per_month": 30,  "topic_requests_per_month": 1},
    "premium":      {"topics": None, "qa_per_month": 30,  "topic_requests_per_month": 3},
    "professional": {"topics": None, "qa_per_month": 200, "topic_requests_per_month": 10},
}


def _get_period_end(sub_obj):
    """Extract current_period_end from a Stripe subscription object.

    Newer Stripe API versions moved this field from the subscription
    to items.data[].  Check both locations.  Returns an ISO-8601 string
    suitable for Supabase timestamptz columns (not a raw Unix integer).

    Works with both raw dicts (webhook payloads) and Stripe SDK objects.
    """
    try:
        # Try top-level first (older API versions)
        val = sub_obj.get("current_period_end") if hasattr(sub_obj, "get") else None
        if val is None:
            # Fall back to first item (newer API versions)
            items_obj = sub_obj.get("items") if hasattr(sub_obj, "get") else getattr(sub_obj, "items", None)
            if items_obj is not None:
                data = getattr(items_obj, "data", None) or (items_obj.get("data") if hasattr(items_obj, "get") else [])
                if data:
                    item = data[0]
                    val = item.get("current_period_end") if hasattr(item, "get") else getattr(item, "current_period_end", None)
        if val is None:
            return None
        # Convert Unix timestamp to ISO string for Supabase
        if isinstance(val, (int, float)):
            return datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
        return val
    except Exception as exc:
        print(f"[Stripe] Error extracting period_end: {exc}")
        return None


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
        print(f"[Stripe] _get_active_subscription: no DB row for user {user_id}")
        return None, None

    row = result.data[0]
    sub_id = row.get("stripe_subscription_id")
    print(f"[Stripe] _get_active_subscription: db_tier={row.get('tier')}, sub_id={sub_id}")
    if not sub_id:
        return row, None

    try:
        sub = stripe.Subscription.retrieve(sub_id)
        if sub.status in ("active", "trialing"):
            return row, sub
    except Exception as exc:
        print(f"[Stripe] _get_active_subscription: retrieve failed: {exc}")

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
        if not stripe_sub["items"]["data"]:
            raise HTTPException(status_code=500, detail="Subscription has no items")
        item_id = stripe_sub["items"]["data"][0]["id"]
        if new_tier == current_tier:
            raise HTTPException(status_code=400, detail="Already on this plan")

        is_upgrade = TIER_RANK.get(new_tier, 0) > TIER_RANK.get(current_tier, 0)

        if is_upgrade:
            # Upgrade: apply immediately with proration
            updated_sub = stripe.Subscription.modify(
                stripe_sub.id,
                items=[{"id": item_id, "price": price_id}],
                proration_behavior="create_prorations",
            )
            print(f"[Stripe] Upgrade modify succeeded: {updated_sub.id}")

            # Update DB — wrapped in try/except so Stripe change isn't lost
            try:
                period_end = _get_period_end(updated_sub)
                print(f"[Stripe] period_end={period_end}")
                sb = _get_sb()
                update_data = {"tier": new_tier}
                if period_end:
                    update_data["current_period_end"] = period_end
                sb.table("signal_subscriptions").update(
                    update_data
                ).eq("user_id", str(user.id)).execute()
            except Exception as exc:
                print(f"[Stripe] DB update after upgrade failed: {exc}")
                # Still return success — the Stripe subscription was changed

            return {"action": "upgraded", "tier": new_tier}
        else:
            # Downgrade: change price but no proration — takes effect next invoice
            updated_sub = stripe.Subscription.modify(
                stripe_sub.id,
                items=[{"id": item_id, "price": price_id}],
                proration_behavior="none",
            )
            print(f"[Stripe] Downgrade modify succeeded: {updated_sub.id}")
            effective = None
            try:
                effective = _get_period_end(updated_sub)
            except Exception as exc:
                print(f"[Stripe] period_end extraction failed: {exc}")

            # Keep current tier in DB until period ends
            return {
                "action": "downgraded_scheduled",
                "tier": current_tier,
                "new_tier": new_tier,
                "effective_date": effective,
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


def _first_of_next_month():
    """Return an ISO-8601 timestamp for the 1st of next month at midnight UTC."""
    now = datetime.now(timezone.utc)
    if now.month == 12:
        first = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        first = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return first.isoformat()


def _maybe_reset_counters(sb, user_id: str, row: dict) -> dict:
    """Check if usage counters need resetting (monthly). Mutates and returns row."""
    now = datetime.now(timezone.utc)
    updates = {}

    qa_reset = row.get("qa_reset_at")
    if qa_reset:
        if isinstance(qa_reset, str):
            try:
                qa_reset = datetime.fromisoformat(qa_reset.replace("Z", "+00:00"))
            except Exception:
                qa_reset = None
    if qa_reset and now >= qa_reset:
        updates["qa_questions_used"] = 0
        updates["qa_reset_at"] = _first_of_next_month()
        row["qa_questions_used"] = 0
        row["qa_reset_at"] = updates["qa_reset_at"]

    tr_reset = row.get("topic_requests_reset_at")
    if tr_reset:
        if isinstance(tr_reset, str):
            try:
                tr_reset = datetime.fromisoformat(tr_reset.replace("Z", "+00:00"))
            except Exception:
                tr_reset = None
    if tr_reset and now >= tr_reset:
        updates["topic_requests_used"] = 0
        updates["topic_requests_reset_at"] = _first_of_next_month()
        row["topic_requests_used"] = 0
        row["topic_requests_reset_at"] = updates["topic_requests_reset_at"]

    if updates:
        sb.table("signal_subscriptions").update(updates).eq("user_id", user_id).execute()

    return row


@router.get("/tier")
async def get_tier(request: Request):
    """Return the current user's subscription tier, limits, and usage."""
    user = await _get_authenticated_user(request)

    sb = _get_sb()
    result = sb.table("signal_subscriptions").select(
        "tier, status, current_period_end, "
        "qa_questions_used, qa_reset_at, "
        "topic_requests_used, topic_requests_reset_at"
    ).eq("user_id", str(user.id)).execute()

    if not result.data:
        tier = "free"
        limits = TIER_LIMITS[tier]
        return {
            "tier": tier,
            "status": "active",
            "current_period_end": None,
            "limits": limits,
            "usage": {
                "qa_questions_used": 0,
                "qa_reset_at": _first_of_next_month(),
                "topic_requests_used": 0,
                "topic_requests_reset_at": _first_of_next_month(),
            },
        }

    row = result.data[0]
    row = _maybe_reset_counters(sb, str(user.id), row)
    tier = row.get("tier", "free")
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])

    return {
        "tier": tier,
        "status": row.get("status", "active"),
        "current_period_end": row.get("current_period_end"),
        "limits": limits,
        "usage": {
            "qa_questions_used": row.get("qa_questions_used", 0),
            "qa_reset_at": row.get("qa_reset_at"),
            "topic_requests_used": row.get("topic_requests_used", 0),
            "topic_requests_reset_at": row.get("topic_requests_reset_at"),
        },
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
        mode = obj.get("mode")
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")

        # One-time payment (e.g. additional topic request purchase)
        if user_id and mode == "payment":
            payment_type = obj.get("metadata", {}).get("type")
            if payment_type == "topic_request":
                # Grant one additional topic request by decrementing used count
                result = sb.table("signal_subscriptions").select(
                    "topic_requests_used"
                ).eq("user_id", user_id).execute()
                if result.data:
                    current = result.data[0].get("topic_requests_used", 0)
                    new_count = max(current - 1, 0)
                    sb.table("signal_subscriptions").update(
                        {"topic_requests_used": new_count}
                    ).eq("user_id", user_id).execute()

        elif user_id and subscription_id:
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
