"""Employer subscription endpoints — Stripe checkout, webhooks, and status.

POST /create-checkout  — create a Stripe checkout session
POST /webhook          — process Stripe webhook events
GET  /subscription-status — check subscription status by email
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Header, Query, Request
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

    sb = _get_supabase()

    # Block duplicate subscriptions
    active_sub = sb.table("employer_subscriptions").select("id").eq(
        "email", req.email
    ).eq("status", "active").limit(1).execute()
    if active_sub.data:
        raise HTTPException(status_code=409, detail="You already have an active subscription.")

    # Check for existing Stripe customer
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
        payment_method_collection="always",
        subscription_data={"trial_period_days": 30},
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
    webhook_secret = os.environ.get("STRIPE_EMPLOYER_WEBHOOK_SECRET") or os.environ.get("STRIPE_WEBHOOK_SECRET", "")

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

        # --- Employer Pro trial ---
        if metadata.get("product") == "employer_pro":
            company_id = metadata.get("company_id")
            email = metadata.get("email")
            subscription_id = obj.get("subscription")

            if company_id:
                from datetime import timedelta
                now = datetime.now(timezone.utc)
                trial_ends = (now + timedelta(days=30)).isoformat()
                locked_until = (now + timedelta(days=730)).isoformat()  # 24 months

                sb.table("companies").update({
                    "plan": "trial",
                    "trial_started_at": now.isoformat(),
                    "trial_ends_at": trial_ends,
                    "stripe_subscription_id": subscription_id,
                    "plan_locked_until": locked_until,
                }).eq("id", company_id).execute()

                # Welcome email
                try:
                    from utils.email import send_email
                    send_email(
                        to=email,
                        subject="Your 30-day Parity Employer trial has started",
                        html=f"""
                        <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
                          <h2 style="color: #0d9488;">Your trial is active</h2>
                          <p>You have full access to Parity Employer for the next 30 days &mdash;
                              claims analysis, benchmarking, plan grading, and Level 2 analytics.</p>
                          <p>After your trial, you'll be charged $99/mo. This introductory price
                              is locked for 24 months.</p>
                          <p>Cancel anytime before your trial ends &mdash; no charge.</p>
                          <a href="https://employer.civicscale.ai/dashboard"
                             style="display: inline-block; background: #0d9488; color: white;
                                    padding: 12px 24px; border-radius: 8px; text-decoration: none;
                                    font-weight: bold; margin: 16px 0;">
                            Go to Dashboard &rarr;
                          </a>
                          <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
                        </div>
                        """,
                    )
                except Exception as exc:
                    print(f"WARNING: Failed to send employer trial email: {exc}")

            # Check for broker referral — activate commission if found
            if company_id and email:
                try:
                    referral = sb.table("company_invitations").select(
                        "referring_company_id"
                    ).eq("invited_email", email).eq(
                        "invitation_type", "employer_referral"
                    ).limit(1).execute()

                    if referral.data and referral.data[0].get("referring_company_id"):
                        broker_company_id = referral.data[0]["referring_company_id"]
                        # Find or create the commission record
                        existing_commission = sb.table("broker_commissions").select("id").eq(
                            "broker_company_id", broker_company_id
                        ).eq("employer_company_id", company_id).limit(1).execute()

                        now_ts = datetime.now(timezone.utc).isoformat()
                        if existing_commission.data:
                            sb.table("broker_commissions").update({
                                "status": "active",
                                "first_paid_month": now_ts,
                                "employer_company_id": company_id,
                            }).eq("id", existing_commission.data[0]["id"]).execute()
                        else:
                            sb.table("broker_commissions").insert({
                                "broker_company_id": broker_company_id,
                                "employer_company_id": company_id,
                                "status": "active",
                                "first_paid_month": now_ts,
                            }).execute()
                except Exception as exc:
                    print(f"WARNING: Failed to activate broker commission: {exc}")

            return {"status": "ok", "employer_pro": True}

        # --- Broker Pro upgrade ---
        if metadata.get("product") == "broker_pro":
            company_id = metadata.get("company_id")
            subscription_id = obj.get("subscription")
            if company_id:
                sb.table("companies").update({
                    "plan": "pro",
                    "stripe_subscription_id": subscription_id,
                }).eq("id", company_id).execute()
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

            # Send welcome email with dashboard link
            employer_email = email
            tier = metadata.get("tier", "standard")
            try:
                from utils.email import send_email
                send_email(
                    to=employer_email,
                    subject="Your Parity Employer subscription is active",
                    html=f"""
                    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 32px;">
                      <h2 style="color: #0d9488;">Welcome to Parity Employer</h2>
                      <p>Your {tier} subscription is now active.</p>
                      <p>Sign in to your dashboard to upload claims, run benchmarks, and track your savings opportunities:</p>
                      <a href="https://employer.civicscale.ai/dashboard"
                          style="display: inline-block; background: #0d9488; color: white; padding: 12px 24px;
                                 border-radius: 8px; text-decoration: none; font-weight: bold; margin: 16px 0;">
                        Go to Dashboard &rarr;
                      </a>
                      <p style="color: #999; font-size: 12px;">CivicScale &middot; civicscale.ai</p>
                    </div>
                    """,
                )
            except Exception as exc:
                print(f"WARNING: Failed to send employer welcome email: {exc}")

    elif event_type == "customer.subscription.deleted":
        subscription_id = obj.get("id")
        if subscription_id:
            # Check if this is an employer pro subscription (companies table)
            company_result = sb.table("companies").select("id, plan").eq(
                "stripe_subscription_id", subscription_id
            ).execute()
            if company_result.data:
                c = company_result.data[0]
                # Broker companies revert to starter; employer companies to read_only
                if c.get("plan") in ("pro", "pro_cancelling"):
                    # Check company type to determine revert plan
                    company_full = sb.table("companies").select("type").eq("id", c["id"]).execute()
                    company_type = company_full.data[0].get("type") if company_full.data else "employer"
                    revert_plan = "starter" if company_type == "broker" else "read_only"
                    sb.table("companies").update({
                        "plan": revert_plan,
                        "stripe_subscription_id": None,
                    }).eq("id", c["id"]).execute()
                else:
                    sb.table("companies").update({
                        "plan": "read_only",
                        "stripe_subscription_id": None,
                    }).eq("id", c["id"]).execute()
            else:
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
        status = obj.get("status")
        if subscription_id:
            # Check if this is an employer pro subscription (companies table)
            company_result = sb.table("companies").select("id").eq(
                "stripe_subscription_id", subscription_id
            ).execute()
            if company_result.data and status == "active":
                # Trial converted to paid
                sb.table("companies").update({
                    "plan": "pro"
                }).eq("id", company_result.data[0]["id"]).execute()

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
# POST /billing-portal
# ---------------------------------------------------------------------------

@router.post("/billing-portal")
async def employer_billing_portal(email: str = Query(...)):
    import stripe as stripe_lib
    stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY")
    sb = _get_supabase()

    result = sb.table("employer_subscriptions").select(
        "stripe_customer_id"
    ).eq("email", email.strip().lower()).order("created_at", desc=True).limit(1).execute()

    if not result.data or not result.data[0].get("stripe_customer_id"):
        raise HTTPException(status_code=404, detail="No billing account found")

    session = stripe_lib.billing_portal.Session.create(
        customer=result.data[0]["stripe_customer_id"],
        return_url="https://employer.civicscale.ai/account",
    )
    return {"portal_url": session.url}


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


# ---------------------------------------------------------------------------
# POST /start-trial
# ---------------------------------------------------------------------------

@router.post("/start-trial")
async def employer_start_trial(authorization: str = Header(None)):
    """Create Stripe checkout session with 30-day free trial."""
    import stripe as stripe_lib
    from routers.auth import get_current_user
    stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY")
    price_id = os.environ.get("STRIPE_PRICE_EMPLOYER_PRO")

    sb = _get_supabase()
    user = get_current_user(authorization, sb)

    company = user["company"]
    email = user["email"]
    company_id = user["company_id"]

    # Check not already on trial or pro
    if company.get("plan") in ("trial", "pro"):
        return {"already_active": True}

    # Get or create Stripe customer
    customer_id = company.get("stripe_customer_id")
    if not customer_id:
        customer = stripe_lib.Customer.create(
            email=email,
            name=company.get("name", ""),
            metadata={"company_id": company_id}
        )
        customer_id = customer.id
        sb.table("companies").update({
            "stripe_customer_id": customer_id
        }).eq("id", company_id).execute()

    session = stripe_lib.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        subscription_data={
            "trial_period_days": 30,
            "metadata": {
                "company_id": company_id,
                "product": "employer_pro",
                "email": email,
            }
        },
        success_url="https://employer.civicscale.ai/dashboard?trial_started=true",
        cancel_url="https://employer.civicscale.ai/dashboard",
        metadata={
            "company_id": company_id,
            "product": "employer_pro",
            "email": email,
        },
    )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# POST /cancel-trial
# ---------------------------------------------------------------------------

@router.post("/cancel-trial")
async def employer_cancel_trial(authorization: str = Header(None)):
    """Cancel employer trial or subscription at period end."""
    import stripe as stripe_lib
    from routers.auth import get_current_user
    stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY")

    sb = _get_supabase()
    user = get_current_user(authorization, sb)
    company_id = user["company_id"]

    company = sb.table("companies").select(
        "stripe_subscription_id, plan"
    ).eq("id", company_id).execute()

    if not company.data:
        raise HTTPException(status_code=404, detail="Company not found")

    c = company.data[0]
    sub_id = c.get("stripe_subscription_id")

    if sub_id:
        stripe_lib.Subscription.modify(sub_id, cancel_at_period_end=True)

    sb.table("companies").update({
        "plan": "cancelled"
    }).eq("id", company_id).execute()

    return {"cancelled": True}
