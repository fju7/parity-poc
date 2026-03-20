"""Provider subscription endpoints — Stripe checkout, webhooks, monitoring, admin management."""

from __future__ import annotations

import os
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from routers.provider_shared import (
    _get_supabase, _get_authenticated_user, _verify_admin,
    _run_analysis_for_payer, _email_wrapper,
    STRIPE_PRICE_PROVIDER_MONTHLY,
    AdminConvertBody, SubscriptionCheckoutBody,
)
from routers.provider_trends import _compute_trends, _compute_and_cache_trends
from routers.benchmark import resolve_locality, get_all_pfs_rates_for_locality
from utils.parse_835 import parse_835

router = APIRouter(tags=["provider"])


# ---------------------------------------------------------------------------
# Provider Subscriptions — Audit-to-Subscription Conversion
# ---------------------------------------------------------------------------

SUBSCRIPTION_STATUS_COLORS = {
    "active": "green",
    "canceled": "gray",
    "past_due": "red",
}


def _send_conversion_email(subscription: dict, audit: dict):
    """Email: Sent when audit is converted to monitoring subscription."""
    try:
        import resend
        resend_key = os.environ.get("RESEND_API_KEY")
        if not resend_key:
            print("[SubEmail] RESEND_API_KEY not configured, skipping")
            return
        resend.api_key = resend_key

        practice_name = subscription.get("practice_name", "Practice")
        contact_email = subscription.get("contact_email", "")
        frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

        # Get underpayment total from source audit
        total_underpayment = 0
        analysis_ids = audit.get("analysis_ids", []) or []
        if analysis_ids:
            try:
                sb = _get_supabase()
                for aid in analysis_ids[:10]:
                    row = sb.table("provider_analyses").select("result_json").eq("id", aid).execute()
                    if row.data:
                        rj = row.data[0].get("result_json", {})
                        total_underpayment += rj.get("summary", {}).get("total_underpayment", 0)
            except Exception:
                pass

        baseline_str = f"${total_underpayment:,.2f}" if total_underpayment > 0 else "your audit findings"

        inner = f"""
        <h2 style="color: #1E293B; margin-top: 0;">Your Parity monitoring is now active</h2>
        <p>Thank you for subscribing to Parity Provider Monitoring for <strong>{practice_name}</strong>.</p>

        <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 8px; padding: 16px; margin: 20px 0;">
            <p style="margin: 0 0 8px; font-weight: 600; color: #0D9488;">Your baseline</p>
            <p style="margin: 0; font-size: 14px; color: #475569;">
                Your audit identified <strong>{baseline_str}</strong> in recoverable revenue.
                This is your baseline. Each month, we'll analyze your new remittance data
                and alert you to new underpayments and denial patterns.
            </p>
        </div>

        <p><strong>Next step:</strong> When your next month's remittance files (835s) are ready,
        send them to <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>
        and we'll run your monthly analysis.</p>

        <div style="text-align: center; margin: 28px 0;">
            <a href="{frontend_url}/audit/account" style="
                display: inline-block; padding: 14px 32px; border-radius: 8px;
                background: #0D9488; color: #fff; font-weight: 600; font-size: 15px;
                text-decoration: none;
            ">View Your Dashboard &rarr;</a>
        </div>

        <p>Questions? Reply to this email or contact
        <a href="mailto:fred@civicscale.ai" style="color: #0D9488;">fred@civicscale.ai</a>.</p>
        """

        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": [contact_email],
            "subject": f"Parity monitoring is active — {practice_name}",
            "html": _email_wrapper(inner),
        })
        print(f"[SubEmail] Conversion email sent to {contact_email}")

        # Admin notification
        resend.Emails.send({
            "from": "Parity Provider <notifications@civicscale.ai>",
            "to": ["fred@civicscale.ai"],
            "subject": f"New Subscription: {practice_name}",
            "html": f"<p>Subscription activated for {practice_name} ({contact_email}).</p>"
                     f"<p>Source audit: {audit.get('id', 'unknown')}</p>"
                     f"<p>Baseline underpayment: {baseline_str}</p>",
        })

    except Exception as exc:
        print(f"[SubEmail] Conversion email failed: {exc}")


def _convert_audit_to_subscription(audit: dict, sb=None) -> dict:
    """Core conversion logic: create provider_subscriptions row from a delivered audit."""
    if sb is None:
        sb = _get_supabase()

    from datetime import datetime

    # Build first monthly_analyses entry from audit's analysis_ids
    first_month = {
        "month": datetime.utcnow().strftime("%Y-%m"),
        "label": "Baseline (from audit)",
        "analysis_ids": audit.get("analysis_ids", []) or [],
        "added_at": datetime.utcnow().isoformat(),
    }

    sub_data = {
        "practice_name": audit.get("practice_name", ""),
        "practice_specialty": audit.get("practice_specialty", ""),
        "num_providers": audit.get("num_providers", 1),
        "billing_company": audit.get("billing_company", ""),
        "contact_email": audit.get("contact_email", ""),
        "company_id": audit.get("company_id"),
        "payer_data": audit.get("payer_list", []),
        "remittance_data": audit.get("remittance_data", []),
        "source_audit_id": audit.get("id"),
        "status": "active",
        "monthly_analyses": [first_month],
    }

    result = sb.table("provider_subscriptions").insert(sub_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create subscription")

    return result.data[0]


@router.post("/admin/audits/convert-subscription")
async def admin_convert_to_subscription(body: AdminConvertBody, request: Request):
    """Convert a delivered audit to an active monitoring subscription (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()

    # Fetch audit
    result = sb.table("provider_audits").select("*").eq("id", body.audit_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = result.data[0]
    if audit.get("status") != "delivered":
        raise HTTPException(status_code=400, detail="Audit must be delivered before converting to subscription")

    # Check for existing subscription from this audit
    existing = sb.table("provider_subscriptions").select("id").eq("source_audit_id", body.audit_id).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Subscription already exists for this audit")

    subscription = _convert_audit_to_subscription(audit, sb)

    # Send conversion email
    _send_conversion_email(subscription, audit)

    return {"status": "ok", "subscription_id": subscription["id"]}


# ---------------------------------------------------------------------------
# Subscription Checkout (Stripe) — Authenticated User
# ---------------------------------------------------------------------------

@router.post("/subscription/checkout")
async def subscription_checkout(request: Request):
    """Create a Stripe checkout session for Provider subscription."""
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe_lib.api_key = stripe_key

    if not STRIPE_PRICE_PROVIDER_MONTHLY:
        raise HTTPException(status_code=503, detail="Provider price not configured")

    user = _get_authenticated_user(request)
    user_email = (user.email or "").lower()
    sb = _get_supabase()

    # Find user's provider company
    cu = sb.table("company_users").select("company_id").eq(
        "email", user_email
    ).execute()
    company_id = None
    for row in (cu.data or []):
        cid = row.get("company_id")
        if cid:
            c = sb.table("companies").select("id").eq(
                "id", cid
            ).eq("type", "provider").limit(1).execute()
            if c.data:
                company_id = cid
                break

    if not company_id:
        raise HTTPException(status_code=404, detail="No provider account found")

    # Block duplicate subscriptions
    active_sub = sb.table("provider_subscriptions").select("id").eq(
        "company_id", str(company_id)
    ).eq("status", "active").limit(1).execute()
    if active_sub.data:
        raise HTTPException(status_code=409, detail="You already have an active subscription.")

    # Get or create Stripe customer
    customer_id = None
    existing = sb.table("provider_subscriptions").select("stripe_customer_id").eq(
        "contact_email", user_email
    ).not_.is_("stripe_customer_id", "null").limit(1).execute()
    if existing.data and existing.data[0].get("stripe_customer_id"):
        customer_id = existing.data[0]["stripe_customer_id"]

    if not customer_id:
        customer = stripe_lib.Customer.create(
            email=user_email,
            metadata={"company_id": str(company_id)},
        )
        customer_id = customer.id

    session = stripe_lib.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": STRIPE_PRICE_PROVIDER_MONTHLY, "quantity": 1}],
        payment_method_collection="always",
        success_url="https://provider.civicscale.ai/account?checkout_success=1",
        cancel_url="https://provider.civicscale.ai/dashboard",
        metadata={
            "company_id": str(company_id),
            "user_email": user_email,
            "type": "provider_monitoring",
        },
    )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# Subscription Webhook (Stripe)
# ---------------------------------------------------------------------------

@router.post("/subscription/webhook")
async def subscription_webhook(request: Request):
    """Process Stripe webhook events for Provider monitoring subscriptions."""
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

    print(f"[ProviderWebhook] Received event: {event_type}")

    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata", {})
        print(f"[ProviderWebhook] checkout.session.completed metadata={metadata}")

        # Only handle provider_monitoring type
        if metadata.get("type") != "provider_monitoring":
            print(f"[ProviderWebhook] Skipping — type={metadata.get('type')}")
            return {"status": "ok", "skipped": True}

        company_id = metadata.get("company_id")
        user_email = metadata.get("user_email", "")
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")

        print(f"[ProviderWebhook] company_id={company_id} user_email={user_email} "
              f"subscription_id={subscription_id} customer_id={customer_id}")

        if not subscription_id:
            print("[ProviderWebhook] WARNING: subscription_id is None/empty")

        if company_id and subscription_id:
            # Upsert provider_subscriptions row
            existing = sb.table("provider_subscriptions").select("id").eq(
                "company_id", company_id
            ).limit(1).execute()

            if existing.data:
                result = sb.table("provider_subscriptions").update({
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "status": "active",
                    "contact_email": user_email,
                }).eq("company_id", company_id).execute()
                print(f"[ProviderWebhook] Updated existing: {len(result.data or [])} rows")
            else:
                # Fetch practice name from company
                comp = sb.table("companies").select("name").eq(
                    "id", company_id
                ).limit(1).execute()
                practice_name = comp.data[0]["name"] if comp.data else ""

                result = sb.table("provider_subscriptions").insert({
                    "company_id": company_id,
                    "contact_email": user_email,
                    "practice_name": practice_name,
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                    "status": "active",
                }).execute()
                print(f"[ProviderWebhook] Created subscription: {result.data}")

            # Update companies table
            sb.table("companies").update({
                "plan": "pro",
                "stripe_subscription_id": subscription_id,
                "stripe_customer_id": customer_id,
            }).eq("id", company_id).execute()
            print(f"[ProviderWebhook] Updated companies.plan to 'pro' for {company_id}")
        else:
            print(f"[ProviderWebhook] WARNING: Missing company_id={company_id} or "
                  f"subscription_id={subscription_id}, skipping DB write")

    elif event_type == "customer.subscription.deleted":
        subscription_id = obj.get("id")
        print(f"[ProviderWebhook] subscription.deleted sub_id={subscription_id}")
        if subscription_id:
            # Mark subscription as canceled
            result = sb.table("provider_subscriptions").update({
                "status": "canceled",
                "canceled_at": datetime.utcnow().isoformat(),
            }).eq("stripe_subscription_id", subscription_id).execute()
            print(f"[ProviderWebhook] Canceled rows: {len(result.data or [])}")

            # Revert company plan to expired
            sb.table("companies").update({
                "plan": "expired",
            }).eq("stripe_subscription_id", subscription_id).eq(
                "type", "provider"
            ).execute()

    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        print(f"[ProviderWebhook] payment_failed sub_id={subscription_id}")
        if subscription_id:
            result = sb.table("provider_subscriptions").update({
                "status": "past_due",
            }).eq("stripe_subscription_id", subscription_id).execute()
            print(f"[ProviderWebhook] Past-due rows: {len(result.data or [])}")

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Admin: Add Monthly Analysis to Subscription
# ---------------------------------------------------------------------------

@router.post("/admin/subscriptions/add-month")
async def admin_add_month(
    request: Request,
    subscription_id: str = "",
    file: UploadFile = File(...),
):
    """Upload 835 files and run monthly analysis for a subscription (admin only)."""
    await _verify_admin(request)

    if not subscription_id:
        raise HTTPException(status_code=400, detail="subscription_id required")

    sb = _get_supabase()

    # Fetch subscription
    sub_result = sb.table("provider_subscriptions").select("*").eq("id", subscription_id).execute()
    if not sub_result.data:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub = sub_result.data[0]

    # Parse 835
    content = await file.read()
    raw = content.decode("utf-8", errors="replace")
    parsed = parse_835(raw)
    claims_list = parsed.get("claims", [])
    payer_name = parsed.get("payer_name", "")

    # Build remittance entry
    entry = {
        "filename": file.filename or "uploaded.835",
        "payer_name": payer_name,
        "claims": [
            {
                "claim_id": c.get("claim_id", ""),
                "lines": [
                    {
                        "cpt_code": li.get("cpt_code") or li.get("procedure_code", ""),
                        "billed_amount": li.get("billed_amount") or li.get("charge_amount", 0),
                        "paid_amount": li.get("paid_amount", 0),
                        "units": li.get("units", 1),
                        "adjustments": li.get("adjustments") or li.get("adjustment_codes", ""),
                    }
                    for li in c.get("line_items", [])
                ],
            }
            for c in claims_list
        ],
    }

    # Append to remittance_data
    existing_rem = sub.get("remittance_data", []) or []
    existing_rem.append(entry)
    sb.table("provider_subscriptions").update({"remittance_data": existing_rem}).eq("id", subscription_id).execute()

    # Add monthly_analyses entry
    from datetime import datetime
    monthly = sub.get("monthly_analyses", []) or []
    month_label = datetime.utcnow().strftime("%Y-%m")
    new_month = {
        "month": month_label,
        "label": f"Month {len(monthly) + 1}",
        "filename": file.filename or "uploaded.835",
        "payer_name": payer_name,
        "claims_count": len(claims_list),
        "lines_count": sum(len(c.get("line_items", [])) for c in claims_list),
        "added_at": datetime.utcnow().isoformat(),
    }

    # --- Run analysis pipeline for this month's data ---
    payer_data = sub.get("payer_data", []) or []
    user_id = sub.get("company_id", "")

    # Build payer_rates from subscription's payer_data
    payer_rates = {}
    fallback_zip = ""
    # Try to resolve ZIP from user profile
    if user_id:
        try:
            prof = sb.table("provider_profiles").select("zip_code").eq("company_id", user_id).execute()
            if prof.data:
                fallback_zip = prof.data[0].get("zip_code", "")
        except Exception:
            pass

    for p in payer_data:
        pn = p.get("payer_name", "")
        rates = p.get("fee_schedule_data", {})
        if rates:
            payer_rates[pn] = {str(k): float(v) for k, v in rates.items()}
        elif p.get("fee_schedule_method") == "medicare-pct" and fallback_zip:
            pct = p.get("medicare_percentage") or 120
            c, l = resolve_locality(fallback_zip)
            if c and l:
                all_rates = get_all_pfs_rates_for_locality(c, l)
                multiplier = float(pct) / 100.0
                regenerated = {}
                for r in all_rates:
                    med_rate = r.get("nonfacility_amount")
                    if med_rate and med_rate > 0:
                        regenerated[str(r["cpt_code"])] = round(float(med_rate) * multiplier, 2)
                if regenerated:
                    payer_rates[pn] = regenerated

    # Build payer_lines from the newly-parsed 835 only
    month_payer_lines = {}
    for claim in entry.get("claims", []):
        for line in claim.get("lines", []):
            cpt = line.get("cpt_code", "")
            if not cpt:
                continue
            adj = line.get("adjustments", "")
            if isinstance(adj, list):
                adj_parts = []
                for a in adj:
                    if isinstance(a, dict):
                        gc = a.get("group_code", "")
                        rc = a.get("reason_code", "")
                        adj_parts.append(f"{gc}-{rc}" if gc else rc)
                    else:
                        adj_parts.append(str(a))
                adj = ", ".join(adj_parts)
            # Use the 835 payer_name as key
            month_payer_lines.setdefault(payer_name, []).append({
                "cpt_code": cpt,
                "code_type": "CPT",
                "billed_amount": float(line.get("billed_amount", 0)),
                "paid_amount": float(line.get("paid_amount", 0)),
                "units": int(line.get("units", 1)),
                "adjustments": adj,
                "claim_id": claim.get("claim_id", ""),
            })

    # Resolve carrier/locality for Medicare benchmarks
    carrier, locality = None, None
    if fallback_zip:
        carrier, locality = resolve_locality(fallback_zip)

    # Run analysis for each payer with both rates and lines
    month_analysis_ids = []
    for pn, rates in payer_rates.items():
        lines = month_payer_lines.get(pn, [])
        if not lines:
            # Try case-insensitive match
            for rp, rl in month_payer_lines.items():
                if rp.lower() == pn.lower():
                    lines = rl
                    break
        if not lines:
            continue

        result = _run_analysis_for_payer(
            payer_name=pn,
            rates=rates,
            lines=lines,
            user_id=user_id,
            carrier=carrier,
            locality=locality,
            sb=sb,
        )
        if result["analysis_id"]:
            month_analysis_ids.append(result["analysis_id"])

    new_month["analysis_ids"] = month_analysis_ids
    monthly.append(new_month)
    sb.table("provider_subscriptions").update({"monthly_analyses": monthly}).eq("id", subscription_id).execute()

    # Compute trends and cache AI narrative if we have 2+ months
    if len(monthly) >= 2:
        try:
            _compute_and_cache_trends(subscription_id, sb=sb)
        except Exception as exc:
            print(f"[AddMonth] Trend computation failed: {exc}")

    return {
        "status": "ok",
        "month": month_label,
        "claims_parsed": len(claims_list),
        "total_lines": new_month["lines_count"],
        "payer_name": payer_name,
        "analysis_ids": month_analysis_ids,
    }


# ---------------------------------------------------------------------------
# Subscription Trends
# ---------------------------------------------------------------------------

@router.get("/subscription/{subscription_id}/trends")
async def subscription_trends(subscription_id: str, request: Request):
    """Get month-over-month trend data for a subscription.

    Auth: Admin (via _verify_admin) OR authenticated user whose ID matches subscription's user_id.
    """
    sb = _get_supabase()

    # Try admin auth first
    is_admin = False
    try:
        await _verify_admin(request)
        is_admin = True
    except Exception:
        pass

    if not is_admin:
        # Fall back to user auth — user_id must match subscription
        user = _get_authenticated_user(request)
        sub_check = sb.table("provider_subscriptions").select("company_id").eq("id", subscription_id).execute()
        if not sub_check.data:
            raise HTTPException(status_code=404, detail="Subscription not found")
        if sub_check.data[0].get("company_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view this subscription")

    # Compute trends
    trends = _compute_trends(subscription_id, sb=sb)

    # Get cached narrative
    sub_result = sb.table("provider_subscriptions").select("trend_narrative, monthly_analyses").eq("id", subscription_id).execute()
    narrative = ""
    months_analyzed = 0
    if sub_result.data:
        narrative = sub_result.data[0].get("trend_narrative") or ""
        months_analyzed = len(sub_result.data[0].get("monthly_analyses", []) or [])

    return {
        "subscription_id": subscription_id,
        "months_analyzed": months_analyzed,
        "trend_narrative": narrative,
        "monthly_summary": trends["monthly_summary"],
        "per_payer_trends": trends["per_payer_trends"],
        "alerts": trends["alerts"],
    }


# ---------------------------------------------------------------------------
# Subscription Portal (Stripe) — Authenticated User
# ---------------------------------------------------------------------------

@router.post("/subscription/portal")
async def subscription_portal(request: Request):
    """Create a Stripe Customer Portal session for Provider subscription management."""
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe_lib.api_key = stripe_key

    user = _get_authenticated_user(request)
    email = user.email
    if not email:
        raise HTTPException(status_code=400, detail="No email on account")

    sb = _get_supabase()

    # Find the user's stripe_customer_id from their subscription
    result = sb.table("provider_subscriptions") \
        .select("stripe_customer_id") \
        .eq("contact_email", email) \
        .not_.is_("stripe_customer_id", "null") \
        .limit(1) \
        .execute()

    if not result.data or not result.data[0].get("stripe_customer_id"):
        raise HTTPException(status_code=404, detail="No billing record found")

    customer_id = result.data[0]["stripe_customer_id"]
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")

    portal_session = stripe_lib.billing_portal.Session.create(
        customer=customer_id,
        return_url="https://provider.civicscale.ai/account",
    )

    return {"portal_url": portal_session.url}


# ---------------------------------------------------------------------------
# User: My Subscription
# ---------------------------------------------------------------------------

@router.get("/my-subscription")
async def my_subscription(request: Request):
    """Return the authenticated user's Provider monitoring subscriptions."""
    user = _get_authenticated_user(request)
    email = user.email
    if not email:
        raise HTTPException(status_code=400, detail="No email on account")

    sb = _get_supabase()
    result = sb.table("provider_subscriptions") \
        .select("*") \
        .eq("contact_email", email) \
        .order("created_at", desc=True) \
        .execute()

    subs = []
    for sub in (result.data or []):
        entry = {
            "id": sub["id"],
            "practice_name": sub.get("practice_name", ""),
            "status": sub.get("status", "active"),
            "monthly_analyses": sub.get("monthly_analyses", []),
            "source_audit_id": sub.get("source_audit_id"),
            "created_at": sub.get("created_at"),
            "stripe_subscription_id": sub.get("stripe_subscription_id"),
        }
        # Fetch trial status and period end from Stripe
        stripe_sub_id = sub.get("stripe_subscription_id")
        if stripe_sub_id:
            try:
                import stripe as stripe_lib
                stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
                stripe_sub = stripe_lib.Subscription.retrieve(stripe_sub_id)
                entry["stripe_status"] = stripe_sub.status
                if stripe_sub.current_period_end:
                    from datetime import datetime, timezone
                    entry["current_period_end"] = datetime.fromtimestamp(
                        stripe_sub.current_period_end, tz=timezone.utc
                    ).isoformat()
                if stripe_sub.trial_end:
                    from datetime import datetime, timezone
                    entry["trial_ends_at"] = datetime.fromtimestamp(
                        stripe_sub.trial_end, tz=timezone.utc
                    ).isoformat()
            except Exception as exc:
                print(f"[ProviderSub] Stripe fetch failed for sub_id={stripe_sub_id}: {type(exc).__name__}: {exc}")
        subs.append(entry)

    # Backward-compat: return first as "subscription", plus full list
    return {
        "subscription": subs[0] if subs else None,
        "subscriptions": subs,
    }


# ---------------------------------------------------------------------------
# Trial Status
# ---------------------------------------------------------------------------

@router.get("/trial-status")
async def trial_status(request: Request):
    """Return trial/subscription status for the authenticated provider user."""
    from datetime import timezone, timedelta

    user = _get_authenticated_user(request)
    sb = _get_supabase()

    # Find the user's company
    cu = sb.table("company_users").select(
        "company_id"
    ).eq("email", user.email).execute()

    company_id = None
    company = None
    for row in (cu.data or []):
        cid = row.get("company_id")
        if cid:
            c = sb.table("companies").select(
                "id, type, plan, trial_started_at, trial_ends_at"
            ).eq("id", cid).eq("type", "provider").execute()
            if c.data:
                company = c.data[0]
                company_id = cid
                break

    if not company:
        return {
            "status": "expired",
            "days_remaining": 0,
            "trial_ends_at": None,
            "subscription_active": False,
        }

    # Check for active Stripe subscription in provider_subscriptions
    sub = sb.table("provider_subscriptions").select(
        "id, status, stripe_subscription_id"
    ).eq("company_id", str(company_id)).in_(
        "status", ["active"]
    ).limit(1).execute()

    subscription_active = False
    stripe_status = None
    if sub.data and sub.data[0].get("stripe_subscription_id"):
        # Fetch live status from Stripe
        try:
            import stripe as stripe_lib
            stripe_lib.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
            stripe_sub = stripe_lib.Subscription.retrieve(
                sub.data[0]["stripe_subscription_id"]
            )
            stripe_status = stripe_sub.status  # trialing, active, past_due, etc.
            if stripe_status in ("trialing", "active"):
                subscription_active = True
        except Exception as exc:
            print(f"[TrialStatus] Stripe fetch failed: {exc}")

    if subscription_active:
        return {
            "status": "active",
            "days_remaining": None,
            "trial_ends_at": company.get("trial_ends_at"),
            "subscription_active": True,
            "stripe_status": stripe_status,
        }

    # No active subscription — check trial window
    trial_ends_at = company.get("trial_ends_at")
    if trial_ends_at:
        trial_end = datetime.fromisoformat(
            trial_ends_at.replace("Z", "+00:00")
        )
        now = datetime.now(timezone.utc)
        if now < trial_end:
            days_remaining = max(0, (trial_end - now).days)
            return {
                "status": "trial",
                "days_remaining": days_remaining,
                "trial_ends_at": trial_ends_at,
                "subscription_active": False,
            }

    return {
        "status": "expired",
        "days_remaining": 0,
        "trial_ends_at": trial_ends_at,
        "subscription_active": False,
    }


# ---------------------------------------------------------------------------
# Admin: List Subscriptions
# ---------------------------------------------------------------------------

@router.get("/admin/subscriptions")
async def admin_list_subscriptions(request: Request):
    """List all provider subscriptions (admin only)."""
    await _verify_admin(request)

    sb = _get_supabase()
    result = sb.table("provider_subscriptions") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()

    return {"subscriptions": result.data or []}
