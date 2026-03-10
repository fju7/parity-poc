"""Employer subscription endpoints — Stripe checkout, webhooks, and status.

POST /create-checkout  — create a Stripe checkout session
POST /webhook          — process Stripe webhook events
GET  /subscription-status — check subscription status by email
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from routers.employer_shared import (
    _get_supabase,
    EMPLOYER_PRICE_TIERS,
    EmployerCheckoutRequest,
)

router = APIRouter(tags=["employer"])


# ---------------------------------------------------------------------------
# POST /create-checkout
# ---------------------------------------------------------------------------

@router.post("/create-checkout")
async def employer_create_checkout(req: EmployerCheckoutRequest):
    """Create a Stripe checkout session for an employer subscription."""
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe_lib.api_key = stripe_key

    # Select price ID by value tier (starter / growth / scale)
    tier_info = EMPLOYER_PRICE_TIERS.get(req.tier)
    price_id = tier_info["stripe_price_id"] if tier_info else ""

    if not price_id:
        raise HTTPException(status_code=503, detail="Employer price not configured")

    frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")
    success_url = req.success_url or f"{frontend_url}/billing/employer/subscribe?checkout_success=1"
    cancel_url = req.cancel_url or f"{frontend_url}/billing/employer/subscribe"

    # Check for existing Stripe customer
    sb = _get_supabase()
    existing = sb.table("employer_subscriptions").select("stripe_customer_id").eq(
        "email", req.email
    ).not_.is_("stripe_customer_id", "null").limit(1).execute()

    customer_id = None
    if existing.data and existing.data[0].get("stripe_customer_id"):
        customer_id = existing.data[0]["stripe_customer_id"]

    if not customer_id:
        customer = stripe_lib.Customer.create(
            email=req.email,
            metadata={
                "company_name": req.company_name or "",
                "employee_count": str(req.employee_count or ""),
                "product": "employer",
            },
        )
        customer_id = customer.id

    session = stripe_lib.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "email": req.email,
            "company_name": req.company_name or "",
            "employee_count": str(req.employee_count or ""),
            "tier": req.tier,
            "type": "employer_subscription",
        },
    )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# POST /webhook
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def employer_webhook(request: Request):
    """Process Stripe webhook events for employer subscriptions."""
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

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

        # --- Broker Pro upgrade ---
        if metadata.get("product") == "broker_pro":
            broker_email = metadata.get("broker_email")
            subscription_id = obj.get("subscription")
            if broker_email:
                sb.table("broker_accounts").update({
                    "plan": "pro",
                    "stripe_subscription_id": subscription_id,
                }).eq("email", broker_email).execute()
            return {"status": "ok", "broker_pro": True}

        if metadata.get("type") != "employer_subscription":
            return {"status": "ok", "skipped": True}

        email = metadata.get("email", "")
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")

        if email and subscription_id:
            # Check for existing subscription for this email
            existing = sb.table("employer_subscriptions").select("id").eq("email", email).execute()

            if existing.data:
                # Update existing with Stripe IDs
                sb.table("employer_subscriptions").update({
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "status": "active",
                    "tier": metadata.get("tier", "standard"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("email", email).execute()
            else:
                # Create new subscription record
                sb.table("employer_subscriptions").insert({
                    "email": email,
                    "company_name": metadata.get("company_name"),
                    "employee_count": int(metadata.get("employee_count") or 0) or None,
                    "tier": metadata.get("tier", "standard"),
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "status": "active",
                }).execute()

    elif event_type == "customer.subscription.deleted":
        subscription_id = obj.get("id")
        if subscription_id:
            sb.table("employer_subscriptions").update({
                "status": "canceled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("stripe_subscription_id", subscription_id).execute()

    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        if subscription_id:
            sb.table("employer_subscriptions").update({
                "status": "past_due",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("stripe_subscription_id", subscription_id).execute()

    elif event_type == "customer.subscription.updated":
        subscription_id = obj.get("id")
        if subscription_id:
            # Extract current_period_end
            period_end = None
            try:
                val = obj.get("current_period_end")
                if val is None:
                    items = obj.get("items", {})
                    data = items.get("data", []) if isinstance(items, dict) else []
                    if data:
                        val = data[0].get("current_period_end")
                if isinstance(val, (int, float)):
                    period_end = datetime.fromtimestamp(val, tz=timezone.utc).isoformat()
            except Exception:
                pass

            update_data = {
                "status": obj.get("status", "active"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if period_end:
                update_data["current_period_end"] = period_end

            sb.table("employer_subscriptions").update(update_data).eq(
                "stripe_subscription_id", subscription_id
            ).execute()

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /subscription-status
# ---------------------------------------------------------------------------

@router.get("/subscription-status")
async def employer_subscription_status(email: str = Query(...)):
    """Check employer subscription status by email."""
    sb = _get_supabase()

    result = sb.table("employer_subscriptions").select("*").eq("email", email).order(
        "created_at", desc=True
    ).limit(1).execute()

    if not result.data:
        return {"active": False, "subscription": None}

    sub = result.data[0]
    return {
        "active": sub.get("status") == "active",
        "subscription": {
            "id": sub["id"],
            "tier": sub.get("tier"),
            "status": sub.get("status"),
            "company_name": sub.get("company_name"),
            "current_period_end": sub.get("current_period_end"),
            "created_at": sub.get("created_at"),
        },
    }
