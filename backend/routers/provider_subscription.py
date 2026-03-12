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
async def subscription_checkout(body: SubscriptionCheckoutBody, request: Request):
    """Create a Stripe checkout session for Provider monitoring subscription."""
    import stripe as stripe_lib

    stripe_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not stripe_key:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    stripe_lib.api_key = stripe_key

    if not STRIPE_PRICE_PROVIDER_MONTHLY:
        raise HTTPException(status_code=503, detail="Provider price not configured")

    user = _get_authenticated_user(request)
    sb = _get_supabase()

    # Block duplicate subscriptions
    active_sub = sb.table("provider_subscriptions").select("id").eq(
        "company_id", str(user.id)
    ).eq("status", "active").limit(1).execute()
    if active_sub.data:
        raise HTTPException(status_code=409, detail="You already have an active subscription.")

    # Verify audit belongs to user and is delivered
    audit_result = sb.table("provider_audits").select("*").eq("id", body.audit_id).execute()
    if not audit_result.data:
        raise HTTPException(status_code=404, detail="Audit not found")

    audit = audit_result.data[0]
    if audit.get("status") != "delivered":
        raise HTTPException(status_code=400, detail="Audit must be delivered first")

    # Verify user owns this audit (by email)
    user_email = user.email or ""
    if user_email.lower() != (audit.get("contact_email") or "").lower():
        raise HTTPException(status_code=403, detail="This audit does not belong to your account")

    # Get or create Stripe customer
    customer_id = None
    existing = sb.table("provider_subscriptions").select("stripe_customer_id").eq(
        "contact_email", user_email
    ).execute()
    if existing.data and existing.data[0].get("stripe_customer_id"):
        customer_id = existing.data[0]["stripe_customer_id"]

    if not customer_id:
        # Also check signal_subscriptions (shared Stripe customers)
        sig_result = sb.table("signal_subscriptions").select("stripe_customer_id").eq(
            "user_id", str(user.id)
        ).execute()
        if sig_result.data and sig_result.data[0].get("stripe_customer_id"):
            customer_id = sig_result.data[0]["stripe_customer_id"]

    if not customer_id:
        customer = stripe_lib.Customer.create(
            email=user_email,
            metadata={"supabase_user_id": str(user.id)},
        )
        customer_id = customer.id

    frontend_url = os.environ.get("FRONTEND_URL", "https://civicscale.ai")

    session = stripe_lib.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": STRIPE_PRICE_PROVIDER_MONTHLY, "quantity": 1}],
        payment_method_collection="always",
        subscription_data={"trial_period_days": 30},
        success_url=f"{frontend_url}/provider/account?checkout_success=1",
        cancel_url=f"{frontend_url}/provider/account",
        metadata={
            "supabase_user_id": str(user.id),
            "audit_id": body.audit_id,
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

    if event_type == "checkout.session.completed":
        metadata = obj.get("metadata", {})
        # Only handle provider_monitoring type
        if metadata.get("type") != "provider_monitoring":
            return {"status": "ok", "skipped": True}

        audit_id = metadata.get("audit_id")
        user_id = metadata.get("supabase_user_id")
        subscription_id = obj.get("subscription")
        customer_id = obj.get("customer")

        if audit_id and subscription_id:
            # Check if subscription already exists for this audit
            existing = sb.table("provider_subscriptions").select("id").eq(
                "source_audit_id", audit_id
            ).execute()

            if existing.data:
                # Update existing with Stripe IDs
                sb.table("provider_subscriptions").update({
                    "stripe_customer_id": customer_id,
                    "stripe_subscription_id": subscription_id,
                }).eq("source_audit_id", audit_id).execute()
            else:
                # Convert audit to subscription
                audit_result = sb.table("provider_audits").select("*").eq("id", audit_id).execute()
                if audit_result.data:
                    audit = audit_result.data[0]
                    subscription = _convert_audit_to_subscription(audit, sb)
                    # Update with Stripe IDs
                    sb.table("provider_subscriptions").update({
                        "stripe_customer_id": customer_id,
                        "stripe_subscription_id": subscription_id,
                    }).eq("id", subscription["id"]).execute()
                    # Send conversion email
                    _send_conversion_email(subscription, audit)

    elif event_type == "customer.subscription.deleted":
        subscription_id = obj.get("id")
        if subscription_id:
            from datetime import datetime
            sb.table("provider_subscriptions").update({
                "status": "canceled",
                "canceled_at": datetime.utcnow().isoformat(),
            }).eq("stripe_subscription_id", subscription_id).execute()

    elif event_type == "invoice.payment_failed":
        subscription_id = obj.get("subscription")
        if subscription_id:
            sb.table("provider_subscriptions").update({
                "status": "past_due",
            }).eq("stripe_subscription_id", subscription_id).execute()

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
        return_url=f"{frontend_url}/audit/account",
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
        subs.append({
            "id": sub["id"],
            "practice_name": sub.get("practice_name", ""),
            "status": sub.get("status", "active"),
            "monthly_analyses": sub.get("monthly_analyses", []),
            "source_audit_id": sub.get("source_audit_id"),
            "created_at": sub.get("created_at"),
            "stripe_subscription_id": sub.get("stripe_subscription_id"),
        })

    # Backward-compat: return first as "subscription", plus full list
    return {
        "subscription": subs[0] if subs else None,
        "subscriptions": subs,
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
